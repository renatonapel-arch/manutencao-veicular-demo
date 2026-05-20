"""Configurações via env (Pydantic Settings)."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Clavis · Manutenção Veicular"
    APP_VERSION: str = "0.1.0-demo"

    DATABASE_URL: str = "postgresql://manut:manut@db:5432/manutencao"
    REDIS_URL: str = "redis://redis:6379/0"

    JWT_SECRET: str = "demo-secret-trocar-em-prod-minimo-32-caracteres-aaaa"
    JWT_ALGORITHM: str = "HS256"
    JWT_TTL_HOURS: int = 24

    EVOLUTION_ENABLED: bool = False
    FEATURE_SIGE_ENABLED: bool = False
    FEATURE_EVOLUTION_ALERTS: bool = False

    # Integrações reais (Fase C — apps já no ar na VPS Napel)
    FROTA_BASE_URL: str = "https://frota.demos.napel.com.br"
    FROTA_TOKEN: str = "1234"
    OLEO_BASE_URL: str = "https://troca-oleo.demos.napel.com.br"
    OLEO_PIN: str = "9999"

    # Notifier central da Napel (event-driven · respeita janela 22-06 BRT)
    NOTIFIER_URL: str = "http://195.35.19.31:18200"
    RENATO_WHATSAPP: str = "5544999413366"

    STAGE: str = "demo"  # demo | staging | prod
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8765,https://manutencao.demos.napel.com.br"
    UPLOAD_DIR: str = "/app/data/uploads"
    MAX_UPLOAD_MB_FOTO: int = 5
    MAX_UPLOAD_MB_DOC: int = 20

    SERVE_FRONTEND: bool = True
    LOG_LEVEL: str = "INFO"
    TZ: str = "UTC"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

ROLES = {
    "admin": "Hudson — vê todas as filiais",
    "filial_responsavel": "Responsável de filial — escopo da própria filial",
    "motorista": "Motorista PWA mobile — anexa foto e NF",
    "admin_oficinas": "Gestão do catálogo de oficinas",
}

FILIAIS = {
    1: {"codigo": 100, "nome": "Maringá", "uf": "PR"},
    2: {"codigo": 700, "nome": "Ponta Grossa", "uf": "PR"},
    3: {"codigo": 900, "nome": "Luís Eduardo Magalhães", "uf": "BA"},
}
