from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from .config import settings
from .documents import extract_upload
from .ai import generate_manifest, analyze_spec
from .security import safe_path
from .store import PROJECTS, Project, new_id
from .github import router as github_router

app = FastAPI(title="AI Project Builder API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_url], allow_credentials=True, allow_methods=["GET","POST","OPTIONS"], allow_headers=["Content-Type"])
app.include_router(github_router)

@app.get("/health")
async def health():
    return {"status":"ok","ai_configured":bool(settings.ai_api_key),"github_configured":bool(settings.github_client_id and settings.github_client_secret)}

class AnalyzeRequest(BaseModel):
    specification: str = Field(min_length=1, max_length=50000)

class GenerateRequest(BaseModel):
    specification: str = Field(min_length=10, max_length=50000)
    language: str = "Python"
    framework: str = "FastAPI"
    project_name: str = ""

@app.post("/api/projects/analyze")
async def analyze(body: AnalyzeRequest):
    try:
        return await analyze_spec(body.specification)
    except Exception as exc:
        raise HTTPException(502, f"Analysis failed: {str(exc)[:300]}") from exc

@app.post("/api/projects/analyze-upload")
async def analyze_upload(file: UploadFile = File(...)):
    text = await extract_upload(file)
    if not text.strip():
        raise HTTPException(422, "No text was extracted from this document.")
    return {"filename":file.filename,"specification":text,"characters":len(text)}

@app.post("/api/projects/generate")
async def generate(body: GenerateRequest):
    try:
        manifest = await generate_manifest(body.specification, body.language, body.framework, body.project_name)
        name = str(manifest.get("name") or body.project_name or "generated-project").strip().lower().replace(" ", "-")[:80]
        result_files = {}
        for item in manifest["files"]:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("content"), str):
                continue
            try:
                path = safe_path(item["path"])
            except ValueError:
                continue
            if len(item["content"].encode("utf-8")) > 1_000_000:
                continue
            result_files[path] = item["content"]
        if not result_files:
            raise HTTPException(502, "AI returned no valid files.")
        # Ensure baseline project documentation exists.
        result_files.setdefault("README.md", f"# {name}\n\n{manifest.get('summary','Generated project')}\n\nGenerated with AI Project Builder.\n")
        project_id = new_id()
        PROJECTS[project_id] = Project(project_id, name, result_files, body.specification, body.language, body.framework)
        return {"project_id":project_id,"name":name,"summary":manifest.get("summary",""),"files":[{"path":p,"size":len(c.encode("utf-8"))} for p,c in sorted(result_files.items())],"file_count":len(result_files)}
    except HTTPException:
        raise
    except Exception as exc:
        message = str(exc)
        if "AI_API_KEY is not configured" in message:
            raise HTTPException(503, message) from exc
        raise HTTPException(502, f"Project generation failed: {message[:400]}") from exc

@app.get("/api/projects/{project_id}/files")
async def project_files(project_id: str):
    project = PROJECTS.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found or server restarted. Generate it again.")
    return {"project_id":project_id,"name":project.name,"files":[{"path":p,"content":c,"size":len(c.encode('utf-8'))} for p,c in sorted(project.files.items())]}

@app.get("/api/projects/{project_id}/download")
async def download(project_id: str):
    project = PROJECTS.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found or server restarted. Generate it again.")
    memory = BytesIO()
    with ZipFile(memory, "w", ZIP_DEFLATED) as archive:
        for path, content in project.files.items():
            try:
                safe = safe_path(path)
            except ValueError:
                continue
            archive.writestr(f"{project.name}/{safe}", content)
    memory.seek(0)
    return StreamingResponse(memory, media_type="application/zip", headers={"Content-Disposition":f'attachment; filename="{project.name}.zip"'})

@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    # FastAPI's default exception handlers handle HTTPException; this avoids leaking internals for unexpected failures.
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"detail":"Unexpected server error. Check backend logs."})
