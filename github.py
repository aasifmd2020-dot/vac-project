import secrets
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from pydantic import BaseModel, Field
from .config import settings
from .store import SESSIONS, PROJECTS
from .security import safe_path, is_publishable

router = APIRouter(prefix="/api/github", tags=["GitHub"])
serializer = URLSafeTimedSerializer(settings.app_secret_key, salt="github-oauth-state")
COOKIE = "apb_session"

def session_for(request: Request) -> dict:
    sid = request.cookies.get(COOKIE)
    if not sid or sid not in SESSIONS:
        raise HTTPException(401, "Connect GitHub first; session is missing or expired.")
    return SESSIONS[sid]

@router.get("/login")
async def login(request: Request):
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(503, "GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.")
    state = secrets.token_urlsafe(24)
    signed_state = serializer.dumps(state)
    redirect_uri = settings.backend_public_url.rstrip("/") + "/api/github/callback"
    url = "https://github.com/login/oauth/authorize"
    response = RedirectResponse(f"{url}?client_id={settings.github_client_id}&redirect_uri={redirect_uri}&scope=repo&state={state}")
    response.set_cookie("apb_oauth_state", signed_state, httponly=True, secure=settings.cookie_secure, samesite="lax", max_age=600)
    return response

@router.get("/callback")
async def callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        return RedirectResponse(settings.frontend_url + "/?github_error=authorization_denied")
    signed = request.cookies.get("apb_oauth_state")
    try:
        expected = serializer.loads(signed, max_age=600) if signed else None
    except (BadSignature, SignatureExpired):
        expected = None
    if not expected or not secrets.compare_digest(str(expected), str(state)):
        raise HTTPException(400, "OAuth state validation failed. Please restart GitHub connection.")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post("https://github.com/login/oauth/access_token",
            headers={"Accept":"application/json"},
            json={"client_id":settings.github_client_id,"client_secret":settings.github_client_secret,"code":code})
        if r.is_error:
            raise HTTPException(502, "GitHub token exchange failed.")
        token_data = r.json()
    token = token_data.get("access_token")
    if not token:
        raise HTTPException(401, "GitHub did not return an access token.")
    async with httpx.AsyncClient(timeout=30) as client:
        user_response = await client.get("https://api.github.com/user", headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json"})
        if user_response.is_error:
            raise HTTPException(502, "Could not verify GitHub account.")
        user = user_response.json()
    sid = secrets.token_urlsafe(32)
    SESSIONS[sid] = {"token":token, "user":user.get("login"), "user_id":user.get("id")}
    response = RedirectResponse(settings.frontend_url + "/?github_connected=1")
    response.set_cookie(COOKIE, sid, httponly=True, secure=settings.cookie_secure, samesite="lax", max_age=3600*8)
    response.delete_cookie("apb_oauth_state")
    return response

@router.get("/status")
async def status(request: Request):
    sid = request.cookies.get(COOKIE)
    session = SESSIONS.get(sid, {}) if sid else {}
    return {"connected": bool(session.get("token")), "username": session.get("user")}

@router.get("/repositories")
async def repositories(request: Request):
    session = session_for(request)
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get("https://api.github.com/user/repos?sort=updated&per_page=100",
            headers={"Authorization":f"Bearer {session['token']}","Accept":"application/vnd.github+json"})
    if r.status_code == 401:
        raise HTTPException(401, "GitHub authorization expired. Connect again.")
    if r.status_code == 403:
        raise HTTPException(403, "GitHub API rate limit or permissions error.")
    if r.is_error:
        raise HTTPException(502, f"GitHub repository listing failed ({r.status_code}).")
    return [{"id":x["id"],"name":x["name"],"full_name":x["full_name"],"private":x["private"],"default_branch":x.get("default_branch","main"),"html_url":x["html_url"]} for x in r.json()]

class PublishRequest(BaseModel):
    project_id: str
    mode: str = Field(pattern="^(create|existing)$")
    repository: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=350)
    private: bool = True
    branch: str = Field(default="main", min_length=1, max_length=100)
    confirmed: bool = False

@router.post("/publish")
async def publish(body: PublishRequest, request: Request):
    session = session_for(request)
    if not body.confirmed:
        raise HTTPException(400, "Review the files and set confirmed=true before publishing.")
    project = PROJECTS.get(body.project_id)
    if not project:
        raise HTTPException(404, "Project not found or server restarted. Generate it again.")
    repo_name = body.repository.strip()
    if "/" in repo_name or repo_name in {".", ".."}:
        raise HTTPException(400, "Enter a repository name, not an owner/repository path.")
    files = {}
    for path, content in project.files.items():
        try:
            path = safe_path(path)
        except ValueError:
            continue
        if is_publishable(path, content):
            files[path] = content
    if not files:
        raise HTTPException(400, "No publishable files remain after security filtering.")
    headers = {"Authorization":f"Bearer {session['token']}","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
    async with httpx.AsyncClient(timeout=60) as client:
        if body.mode == "create":
            r = await client.post("https://api.github.com/user/repos", headers=headers,
                json={"name":repo_name,"description":body.description,"private":body.private,"auto_init":True})
            if r.status_code == 422:
                raise HTTPException(409, "Repository already exists or repository name is invalid. Choose existing mode or another name.")
            if r.status_code == 401:
                raise HTTPException(401, "GitHub authorization expired.")
            if r.status_code == 403:
                raise HTTPException(403, "GitHub cannot create this repository (permissions or rate limit).")
            if r.is_error:
                raise HTTPException(502, f"Repository creation failed ({r.status_code}): {r.text[:300]}")
            repo = r.json()
        else:
            r = await client.get(f"https://api.github.com/repos/{session['user']}/{repo_name}", headers=headers)
            if r.status_code == 404:
                raise HTTPException(404, "Repository not found or not accessible.")
            if r.is_error:
                raise HTTPException(502, f"Repository lookup failed ({r.status_code}).")
            repo = r.json()
        owner, name = repo["owner"]["login"], repo["name"]
        # Ensure target branch exists. New repositories may need a short propagation retry.
        branch_r = await client.get(f"https://api.github.com/repos/{owner}/{name}/branches/{body.branch}", headers=headers)
        if branch_r.status_code == 404:
            if body.mode == "create":
                branch_r = await client.get(f"https://api.github.com/repos/{owner}/{name}/branches/{repo.get('default_branch','main')}", headers=headers)
            if branch_r.status_code == 404:
                raise HTTPException(404, f"Target branch '{body.branch}' does not exist.")
        if branch_r.is_error:
            raise HTTPException(502, f"Could not inspect target branch ({branch_r.status_code}).")
        branch_data = branch_r.json()
        base_sha = branch_data["commit"]["sha"]
        base_tree_r = await client.get(f"https://api.github.com/repos/{owner}/{name}/git/trees/{base_sha}?recursive=1", headers=headers)
        if base_tree_r.is_error:
            raise HTTPException(502, "Could not read target repository tree.")
        existing = {x["path"]:x["sha"] for x in base_tree_r.json().get("tree",[]) if x.get("type")=="blob"}
        blobs = []
        for path, content in files.items():
            br = await client.post(f"https://api.github.com/repos/{owner}/{name}/git/blobs", headers=headers,
                json={"content":content,"encoding":"utf-8"})
            if br.is_error:
                raise HTTPException(502, f"Could not upload file {path} ({br.status_code}).")
            blobs.append({"path":path,"mode":"100644","type":"blob","sha":br.json()["sha"]})
        tree_r = await client.post(f"https://api.github.com/repos/{owner}/{name}/git/trees", headers=headers,
            json={"base_tree":base_sha,"tree":blobs})
        if tree_r.is_error:
            raise HTTPException(502, "Could not create Git tree.")
        commit_r = await client.post(f"https://api.github.com/repos/{owner}/{name}/git/commits", headers=headers,
            json={"message":f"Publish AI Project Builder project: {project.name}","tree":tree_r.json()["sha"],"parents":[base_sha]})
        if commit_r.is_error:
            raise HTTPException(502, "Could not create commit.")
        ref_r = await client.patch(f"https://api.github.com/repos/{owner}/{name}/git/refs/heads/{body.branch}", headers=headers,
            json={"sha":commit_r.json()["sha"],"force":False})
        if ref_r.is_error:
            raise HTTPException(502, f"Commit created but branch update failed ({ref_r.status_code}). Check repository history before retrying.")
    return {"success":True,"repository_url":repo["html_url"],"branch":body.branch,"files_published":len(files),"commit_sha":commit_r.json()["sha"]}
