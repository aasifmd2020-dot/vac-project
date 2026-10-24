# AI Project Builder

A full-stack starter application for generating project codebases from a topic/specification, previewing files, downloading ZIPs, and publishing to GitHub after OAuth authorization.

## Stack
- Frontend: React + Vite + JavaScript
- Backend: FastAPI
- AI: configurable OpenAI-compatible chat-completions API (server-side only)
- GitHub: OAuth web flow + GitHub REST API
- Documents: PDF, DOCX, TXT, and common image OCR (Tesseract optional)

## Requirements
- Python 3.11+
- Node.js 20+
- An AI provider API key and compatible endpoint/model (for real generation)
- GitHub OAuth App credentials for GitHub connection/publishing

## Quick start

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set APP_SECRET_KEY, AI_API_KEY, and GitHub OAuth values
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend
In another terminal:
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Open http://localhost:5173. The frontend proxies `/api` to FastAPI.

## Configuration

Backend `.env`:
- `APP_SECRET_KEY`: long random secret for signing sessions and OAuth state.
- `AI_API_KEY`: AI provider key. Never put this in frontend `.env`.
- `AI_BASE_URL`: OpenAI-compatible base URL, default `https://api.openai.com/v1`.
- `AI_MODEL`: provider model identifier.
- `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`: OAuth App credentials.
- `FRONTEND_URL`: URL users return to after OAuth, default `http://localhost:5173`.
- `BACKEND_PUBLIC_URL`: backend callback base URL, default `http://localhost:8000`.
- `COOKIE_SECURE`: set `true` behind HTTPS in production.
- `MAX_UPLOAD_MB`: upload limit.

Create a GitHub OAuth App at GitHub Settings → Developer settings → OAuth Apps. Set its callback URL to `http://localhost:8000/api/github/callback` for local development. Configure `repo` scope only if you need private repository access and file pushes; GitHub OAuth scopes are broader than fine-grained GitHub App permissions. For production, prefer a GitHub App with minimal repository permissions and HTTPS.

## Features and behavior
- `POST /api/projects/analyze`: extracts document text and returns a short requirements analysis.
- `POST /api/projects/generate`: generates a file manifest using the configured AI provider, validates paths, stores it in memory, and returns the project ID.
- `GET /api/projects/{project_id}/files`: returns generated files for the current session.
- `GET /api/projects/{project_id}/download`: downloads a safe ZIP, excluding secrets and generated/dependency folders.
- `GET /api/github/login`: starts OAuth and sets a signed session cookie.
- `GET /api/github/callback`: validates OAuth state and exchanges the code for a token.
- `GET /api/github/repositories`: lists accessible repositories after OAuth.
- `POST /api/github/publish`: creates a repository if requested, then creates/updates files and commits them to the selected branch. A user confirmation boolean is required.

## Important implementation notes
- Projects and OAuth tokens are stored in process memory for this starter; restart loses them. Use Redis/database-backed sessions and encrypted token storage before production or multi-worker deployment.
- Generated files are treated as untrusted data and path-validated. Generated code is not executed by this server.
- ZIP creation excludes `.env`, credential files, `.git`, dependency directories, caches, and build outputs.
- Publishing is an external side effect and requires `confirmed: true`. The API returns success only after GitHub API calls complete.
- OAuth cookies are HttpOnly, SameSite=Lax; set `COOKIE_SECURE=true` in HTTPS production.
- Add CSRF/origin protection, rate limiting, audit logs, persistent storage, and a GitHub App installation flow before public production deployment.
- Image OCR requires the optional `pytesseract` Python package and a locally installed Tesseract executable. PDF OCR is not performed on scanned PDFs by default.
- AI generation requires valid provider credentials. Without them, generation returns a clear configuration error rather than fake results.

## API smoke test
```bash
curl http://localhost:8000/health
```
The interactive API docs are at http://localhost:8000/docs.

## Tests
```bash
cd backend
pytest
```
