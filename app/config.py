from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar, Literal
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import USDT_MAINNET_MASTER
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
    APP_PORT: int = Field(
        default=8_000,
        ge=1,
        le=65_535,
        validation_alias=AliasChoices("PORT", "APP_PORT"),
    )
    APP_BASE_URL: str = ""
    RENDER_EXTERNAL_URL: str = ""
    RENDER_KEEPALIVE_ENABLED: bool = True
    RENDER_KEEPALIVE_INTERVAL_SECONDS: int = Field(default=840, ge=60)
    RENDER_KEEPALIVE_TIMEOUT_SECONDS: int = Field(default=10, ge=1, le=60)

    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_BOT_USERNAME: str = ""
    TELEGRAM_USE_POLLING: bool = True
    TELEGRAM_WEBHOOK_PATH: str = "/telegram/webhook"
    TELEGRAM_WEBHOOK_SECRET: str = ""
    SUPPORT_USERNAME: str = "@not_jammm"
    ADMIN_IDS: str = "786080766"

    SUPABASE_URL: str
    SUPABASE_KEY: str

    TON_API_ENDPOINT: str = "https://tonapi.io/v2"
    TON_API_KEY: str = ""
    TON_MNEMONIC: str
    TON_GUARANT_ADDRESS: str
    TON_NETWORK: TonNetwork = TonNetwork.MAINNET
    TON_WORKCHAIN: int = 0
    TON_REQUEST_TIMEOUT_MS: int = Field(default=15_000, ge=1_000)
    TON_TRANSFER_TTL_SECONDS: int = Field(default=60, ge=30)
    TON_TRACE_GRACE_SECONDS: int = Field(default=120, ge=0)
    TON_TRANSACTION_SCAN_LIMIT: int = Field(default=50, ge=1, le=1_000)
    SERVICE_FEE_WALLET: str
    SERVICE_FEE_COMMENT: str = Field(default="Service fee", min_length=1, max_length=120)
    TON_PAYOUT_FEE_RESERVE: Decimal = Field(default=Decimal("0.01"), gt=0)
    TON_GUARANT_PAYOUT_GAS_RESERVE: Decimal = Field(default=Decimal("0.003"), gt=0)
    USDT_MASTER_ADDRESS: Literal["EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs"] = USDT_MAINNET_MASTER
    USDT_JETTON_TRANSFER_TON: Decimal = Field(default=Decimal("0.05"), gt=0)

    DEAL_POLL_INTERVAL_SECONDS: int = Field(default=15, ge=5)
    READ_ONLY_FAILURE_THRESHOLD_SECONDS: int = Field(default=900, ge=300, le=3600)
    MIN_DEAL_AMOUNT: ClassVar[Decimal] = Decimal(1)
    MIN_USDT_DEAL_AMOUNT: ClassVar[Decimal] = Decimal(1)
    FAILED_DEAL_RETENTION_DAYS: int = Field(default=30, ge=1, le=30)
    RETENTION_CLEANUP_INTERVAL_SECONDS: int = Field(default=86_400, ge=3_600)
    ESCROW_FEE_RATE: ClassVar[Decimal] = Decimal("0.015")
    DEALS_PAGE_SIZE: ClassVar[int] = 5

    DEFAULT_LANGUAGE: Language = Language.RU
    DEFAULT_CURRENCY: Currency = Currency.TON
    CHANNEL_PASSWORD_WARNING: str = (
        "Убедитесь, что у канала включён облачный пароль, и добавьте бота "
        "администратором перед созданием сделки."
    )

    @field_validator(
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_BOT_USERNAME",
        "TELEGRAM_WEBHOOK_SECRET",
        "SUPPORT_USERNAME",
        "SUPABASE_KEY",
        "TON_API_KEY",
        "TON_MNEMONIC",
        "TON_GUARANT_ADDRESS",
        "SERVICE_FEE_WALLET",
        "SERVICE_FEE_COMMENT",
        "ADMIN_IDS",
        "USDT_MASTER_ADDRESS",
        mode="before",
    )
    @classmethod
    def strip_dashboard_quotes(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if (
            len(normalized) >= 2
            and normalized[0] == normalized[-1]
            and normalized[0] in {"'", '"'}
        ):
            return normalized[1:-1].strip()
        return normalized

    @property
    def admin_ids(self) -> frozenset[int]:
        try:
            values = frozenset(int(item.strip()) for item in self.ADMIN_IDS.split(",") if item.strip())
        except ValueError as exc:
            raise ValueError("ADMIN_IDS must be a comma-separated list of Telegram IDs") from exc
        if not values:
            raise ValueError("ADMIN_IDS must contain at least one Telegram ID")
        return values

    @field_validator("TON_MNEMONIC")
    @classmethod
    def validate_mnemonic_length(cls, value: str) -> str:
        if len(value.split()) != 24:
            raise ValueError("TON_MNEMONIC must contain exactly 24 words")
        return value

    @field_validator(
        "APP_BASE_URL",
        "RENDER_EXTERNAL_URL",
        "SUPABASE_URL",
        "TON_API_ENDPOINT",
        mode="before",
    )
    @classmethod
    def validate_http_url(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            return normalized
        if normalized.startswith("[") or "](" in normalized:
            raise ValueError("URL must be plain text, not a Markdown link")
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("URL must be an absolute HTTP(S) URL")
        return normalized.rstrip("/")

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
