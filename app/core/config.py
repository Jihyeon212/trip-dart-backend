from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Trip Dart Backend"
    database_url: str = "sqlite:///./data/localhub.db"
    openai_api_key: str | None = None
    frontend_origin: str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()
