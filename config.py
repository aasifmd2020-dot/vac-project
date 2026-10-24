from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_secret_key: str = "dev-only-change-me"
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4.1-mini"
    github_client_id: str = ""
    github_client_secret: str = ""
    frontend_url: str = "http://localhost:5173"
    backend_public_url: str = "http://localhost:8000"
    cookie_secure: bool = False
    max_upload_mb: int = 10
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
