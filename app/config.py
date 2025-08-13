from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    # pydantic v2: ignore unknown env vars (e.g., ENV), load from .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
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
    # Rotation policy: 'size' or 'time'
    log_rotation: str = "size"
    # If time-based rotation
    log_when: str = "midnight"  # 'S','M','H','D','midnight','W0'-'W6'
    log_interval: int = 1
    log_utc: bool = True
    # Split file by day into subdirectories logs/YYYY-MM-DD/filename
    log_daily_split: bool = True

    # OBS WebSocket v5 connection
    obs_host: str = "127.0.0.1"
    obs_port: int = 4455
    obs_password: str = ""
    obs_heartbeat: float = 15.0

    # OBS autostart/guardian
    obs_autostart: bool = True
    obs_exe_path: str | None = None
    obs_launch_args: str = "--minimize-to-tray" # "--minimize-to-tray" or ""
    obs_launch_timeout: int = 45
    obs_guardian_enabled: bool = True
    obs_guardian_interval: int = 5
    # If running inside container, skip launching desktop OBS by default
    obs_skip_autostart_in_docker: bool = True
    # Autoconfigure OBS WebSocket settings in global.ini before first launch
    obs_ws_autoconfigure: bool = True
    obs_config_dir: str | None = None  # default: %APPDATA%/obs-studio
    # Override OBS data directory if non-standard layout (portable 등)
    obs_data_path: str | None = None
    # Auto-dismiss Safe Mode / previous session warning dialogs
    obs_auto_dismiss_safemode: bool = True
    obs_safemode_dismiss_timeout: int = 25

    # Auto bootstrap OBS layout on startup
    auto_bootstrap: bool = True

    # ELK / Kibana
    elk_auto_import: bool = True
    kibana_url: str = "http://localhost:5601"
    kibana_import_timeout_sec: int = 300

    # Optional diagnostics/token protection
    diag_token: str | None = None

    # Legion/Region flag to customize overlay behaviors (e.g., clock locale)
    legion: str | None = None

    # Overlay customization
    overlay_brand: str = "MIRRORLESS"  # env: OVERLAY_BRAND
    overlay_clock_enabled: bool = True  # env: OVERLAY_CLOCK_ENABLED
    overlay_brand_color: str = "#ffffff"  # env: OVERLAY_BRAND_COLOR

    # Screenshot root directory (unified location)
    screenshot_dir: str = str(Path.home() / "Pictures" / "OBS-Screenshots")

settings = Settings()

