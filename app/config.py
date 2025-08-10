from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "obs-ws-server"
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "info"
    log_json: bool = True
    # File logging options
    log_file_enabled: bool = False
    log_dir: str = "logs"
    log_file_name: str = "server.log"
    log_max_bytes: int = 10_000_000
    log_backup_count: int = 5

    # OBS WebSocket v5 connection
    obs_host: str = "127.0.0.1"
    obs_port: int = 4455
    obs_password: str = ""
    obs_heartbeat: float = 15.0

    # Auto bootstrap OBS layout on startup
    auto_bootstrap: bool = True

    # Optional diagnostics/token protection
    diag_token: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

