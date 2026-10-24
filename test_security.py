import pytest
from app.security import safe_path, is_publishable

def test_safe_path_accepts_normal_path():
    assert safe_path("src/main.py") == "src/main.py"

@pytest.mark.parametrize("path", ["../secret.txt", "/etc/passwd", ".env", "node_modules/a.js", "src/../../x"])
def test_safe_path_rejects_unsafe(path):
    with pytest.raises(ValueError):
        safe_path(path)

def test_secret_filter():
    assert not is_publishable("config.txt", "ghp_abcdefghijklmnopqrstuvwxyz123456")
