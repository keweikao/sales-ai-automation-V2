"""
Application settings with environment-based configuration.

Usage:
    from core.config import get_settings
    settings = get_settings()
    print(settings.gcp_project_id)
"""

from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment variables take precedence over .env file.
    """

    # Environment
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # GCP
    gcp_project_id: str = Field(default="", alias="GCP_PROJECT_ID")
    gcp_region: str = Field(default="asia-east1", alias="GCP_REGION")

    # Slack
    slack_bot_token: str = Field(default="", alias="SLACK_BOT_TOKEN")
    slack_signing_secret: str = Field(default="", alias="SLACK_SIGNING_SECRET")
    slack_app_token: str = Field(default="", alias="SLACK_APP_TOKEN")

    # LLM APIs
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")

    # Storage
    slack_audio_bucket: str = Field(default="", alias="SLACK_AUDIO_BUCKET")
    gcs_transcripts_bucket: str = Field(default="", alias="GCS_TRANSCRIPTS_BUCKET")

    # Firestore
    firestore_database: str = Field(default="(default)", alias="FIRESTORE_DATABASE")

    # Cloud Tasks
    transcription_task_queue: str = Field(default="", alias="TRANSCRIPTION_TASK_QUEUE")
    transcription_task_location: str = Field(default="asia-east1", alias="TRANSCRIPTION_TASK_LOCATION")
    transcription_task_handler_url: str = Field(default="", alias="TRANSCRIPTION_TASK_HANDLER_URL")

    # Salesforce
    salesforce_instance_url: Optional[str] = Field(default=None, alias="SALESFORCE_INSTANCE_URL")
    salesforce_client_id: Optional[str] = Field(default=None, alias="SALESFORCE_CLIENT_ID")
    salesforce_client_secret: Optional[str] = Field(default=None, alias="SALESFORCE_CLIENT_SECRET")

    # Twilio (SMS)
    twilio_account_sid: Optional[str] = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(default=None, alias="TWILIO_AUTH_TOKEN")

    # Feature flags
    enable_salesforce_sync: bool = Field(default=False, alias="ENABLE_SALESFORCE_SYNC")
    enable_sms_notifications: bool = Field(default=False, alias="ENABLE_SMS_NOTIFICATIONS")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to avoid re-reading environment on every call.
    """
    return Settings()
