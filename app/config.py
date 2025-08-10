from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "obs-ws-server"
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "info"

    # OBS WebSocket v5 connection
    obs_host: str = "127.0.0.1"
    obs_port: int = 4455
    obs_password: str = ""
    obs_heartbeat: float = 15.0

    # Auto bootstrap OBS layout on startup
    auto_bootstrap: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

