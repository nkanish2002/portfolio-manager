"""Application settings via pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Portfolio Manager"
    debug: bool = True
    database_url: str = "sqlite+aiosqlite:///./portfolio.db"
    template_dir: str = "src/portfolio_manager/templates"
    yfinance_enabled: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
