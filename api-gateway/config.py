"""API Gateway 設定"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """API Gateway 設定"""

    # 環境
    environment: str = "development"

    # CORS
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # GCP
    gcp_project_id: str = "sales-ai-automation-v2"
    firestore_database: str = "(default)"

    class Config:
        env_file = ".env"


settings = Settings()
