from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.enums import Currency, Language, TonNetwork

PROJECT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Gift Guarant"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = Field(default=8_000, ge=1, le=65_535)
    APP_BASE_URL: str = ""

    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_BOT_USERNAME: str = ""
    TELEGRAM_USE_POLLING: bool = True
    TELEGRAM_WEBHOOK_PATH: str = "/telegram/webhook"
    TELEGRAM_WEBHOOK_SECRET: str = ""
    SUPPORT_USERNAME: str = "@msk_deputat"

    SUPABASE_URL: str
    SUPABASE_KEY: str

    TON_API_ENDPOINT: str = "https://tonapi.io/v2"
    TON_API_KEY: str = ""
    TON_MNEMONIC: str
    TON_NETWORK: TonNetwork = TonNetwork.MAINNET
    TON_WORKCHAIN: int = 0
    TON_REQUEST_TIMEOUT_MS: int = Field(default=15_000, ge=1_000)
    TON_TRANSFER_TTL_SECONDS: int = Field(default=60, ge=30)
    TON_TRACE_GRACE_SECONDS: int = Field(default=120, ge=0)
    TON_TRANSACTION_SCAN_LIMIT: int = Field(default=50, ge=1, le=1_000)

    DEAL_POLL_INTERVAL_SECONDS: int = Field(default=15, ge=5)
    DEAL_PAYMENT_TIMEOUT_SECONDS: int = Field(default=900, ge=60)
    FAILED_DEAL_RETENTION_DAYS: int = Field(default=30, ge=1, le=30)
    RETENTION_CLEANUP_INTERVAL_SECONDS: int = Field(default=86_400, ge=3_600)
    ESCROW_FEE_RATE: Decimal = Field(default=Decimal("0.03"), ge=0, lt=1)
    REFERRAL_FEE_SHARE: Decimal = Field(default=Decimal("0.01"), ge=0, le=1)
    AUTO_PAYOUT_AFTER_PAYMENT: bool = True
    DEALS_PAGE_SIZE: int = Field(default=8, ge=1, le=20)

    DEFAULT_LANGUAGE: Language = Language.RU
    DEFAULT_CURRENCY: Currency = Currency.TON
    CHANNEL_PASSWORD_WARNING: str = (
        "Убедитесь, что у канала включён облачный пароль, и добавьте бота "
        "администратором перед созданием сделки."
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

