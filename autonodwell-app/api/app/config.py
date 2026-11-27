"""Runtime configuration. Every value comes from environment variables (12-factor),
so the same container image runs locally, in staging and in production."""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["local", "staging", "production"] = "local"

    # Postgres. On Cloud Run this points at Cloud SQL through the unix socket, e.g.
    # postgresql+psycopg://app:PASS@/autonodwell?host=/cloudsql/PROJECT:REGION:INSTANCE
    database_url: str = "postgresql+psycopg://postgres@localhost:5432/autonodwell"

    # Auth. "firebase" verifies real Firebase / Identity Platform ID tokens.
    # "dev" accepts tokens of the form  dev:<uid>:<email>  — local development and tests ONLY.
    auth_mode: Literal["firebase", "dev"] = "dev"
    firebase_project_id: str | None = None

    # Comma-separated emails that are promoted to admin on first sign-in (bootstrap only).
    admin_emails: str = ""

    # Browser origins allowed to call the API (not needed when the web app is served
    # from the same origin via Firebase Hosting rewrites).
    cors_origins: str = "http://localhost:5173"

    # CRM sync. "ghl" = GoHighLevel, "webhook" = generic JSON webhook (Zapier/Make/n8n), "none" = off.
    crm_provider: Literal["ghl", "webhook", "none"] = "none"
    ghl_api_base: str = "https://services.leadconnectorhq.com"
    ghl_api_version: str = "2021-07-28"
    ghl_private_token: str | None = None  # GHL Private Integration token (keep in Secret Manager)
    ghl_location_id: str | None = None
    ghl_pipeline_id: str | None = None  # optional: also create an opportunity
    ghl_pipeline_stage_id: str | None = None
    crm_webhook_url: str | None = None
    crm_webhook_secret: str | None = None

    # Lead alert emails through Resend (same account as the website's inquiry form).
    # Off unless RESEND_API_KEY and LEAD_NOTIFY_TO are set. LEAD_NOTIFY_FROM must be on a
    # domain verified in Resend (autonodwell.com, the same as the website).
    resend_api_key: str | None = None
    lead_notify_to: str | None = None  # comma-separated; keep in Secret Manager, never in code
    lead_notify_from: str = "Autonodwell <inquiries@autonodwell.com>"

    # Public URL of the web app, used for deep links sent to the CRM.
    app_base_url: str = "http://localhost:5173"

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    @property
    def lead_notify_list(self) -> list[str]:
        return [e.strip() for e in (self.lead_notify_to or "").split(",") if e.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.env == "production" and s.auth_mode != "firebase":
        raise RuntimeError("AUTH_MODE must be 'firebase' in production")
    return s
