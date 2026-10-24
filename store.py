from dataclasses import dataclass, field
from typing import Dict, Any
import secrets

@dataclass
class Project:
    id: str
    name: str
    files: Dict[str, str]
    spec: str
    language: str
    framework: str

PROJECTS: dict[str, Project] = {}
SESSIONS: dict[str, dict[str, Any]] = {}

def new_id() -> str:
    return secrets.token_urlsafe(16)
