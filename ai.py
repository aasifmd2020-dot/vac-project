import json
import httpx
from .config import settings

SYSTEM_PROMPT = '''You are a senior software engineer. Generate a usable project codebase from the user specification.
Return ONLY valid JSON with this schema:
{"name":"short-kebab-case-name","summary":"one sentence","files":[{"path":"relative/path","content":"complete file contents"}]}
Requirements:
- Include all source files, README.md, .gitignore, dependency manifests, and .env.example when relevant.
- Do not include real credentials or secret values.
- Keep file paths relative and safe. Do not include node_modules, build outputs, binaries, or lockfiles.
- Prefer a small but genuinely functional implementation. Include setup and test instructions.
- The chosen language/framework should be followed. Do not use markdown fences around JSON.
'''

async def generate_manifest(spec: str, language: str, framework: str, project_name: str) -> dict:
    if not settings.ai_api_key:
        raise RuntimeError("AI_API_KEY is not configured. Add it to backend/.env to enable real code generation.")
    url = settings.ai_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.ai_model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Project name preference: {project_name or 'infer from topic'}\nLanguage: {language}\nFramework: {framework}\nSpecification:\n{spec[:50000]}"}
        ],
        "response_format": {"type": "json_object"}
    }
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(url, json=payload, headers={"Authorization": f"Bearer {settings.ai_api_key}"})
        response.raise_for_status()
        data = response.json()
    content = data["choices"][0]["message"]["content"]
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError("The AI provider returned invalid JSON. Try generating again.") from exc
    if not isinstance(result, dict) or not isinstance(result.get("files"), list):
        raise RuntimeError("AI response did not contain a valid file manifest.")
    return result

async def analyze_spec(spec: str) -> dict:
    if not settings.ai_api_key:
        # Honest, useful local analysis; generation itself still requires provider credentials.
        lines = [x.strip(" -\t") for x in spec.splitlines() if x.strip()]
        return {"summary": (spec.strip().splitlines()[0][:240] if spec.strip() else "No specification supplied"),
                "requirements": lines[:12], "provider_analysis": False,
                "message": "Basic local analysis only. Configure AI_API_KEY for AI-assisted analysis and generation."}
    url = settings.ai_base_url.rstrip("/") + "/chat/completions"
    payload = {"model": settings.ai_model, "temperature": 0.1,
               "messages": [{"role":"system","content":"Analyze software project requirements. Return JSON with keys summary, requirements (array), suggested_modules (array), risks (array)."},
                            {"role":"user","content":spec[:30000]}],
               "response_format":{"type":"json_object"}}
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(url, json=payload, headers={"Authorization":f"Bearer {settings.ai_api_key}"})
        r.raise_for_status()
        return json.loads(r.json()["choices"][0]["message"]["content"])
