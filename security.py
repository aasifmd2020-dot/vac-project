import re
from pathlib import PurePosixPath

BLOCKED_PARTS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next"}
BLOCKED_NAMES = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519", "credentials.json"}
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*['\"]?[\w\-./+=]{12,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
]

def safe_path(path: str) -> str:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("File path must be a non-empty string")
    normalized = path.replace("\\", "/")
    p = PurePosixPath(normalized)
    if p.is_absolute() or any(part in ("..", "") for part in p.parts):
        raise ValueError(f"Unsafe file path: {path}")
    if any(part in BLOCKED_PARTS for part in p.parts) or p.name.lower() in BLOCKED_NAMES:
        raise ValueError(f"Blocked file path: {path}")
    if p.name.lower().startswith(".env.") and p.name.lower() != ".env.example":
        raise ValueError(f"Environment files must not be published: {path}")
    if len(normalized) > 240:
        raise ValueError("File path is too long")
    return str(p)

def is_publishable(path: str, content: str) -> bool:
    try:
        safe_path(path)
    except ValueError:
        return False
    if any(p.search(content or "") for p in SECRET_PATTERNS):
        return False
    return True
