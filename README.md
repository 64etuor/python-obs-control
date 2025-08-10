## OBS WebSocket FastAPI 서버

### 설치

```powershell
cd "C:\Program Files\obs-studio"
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r python\requirements.txt
```

### 실행

```powershell
cd "C:\Program Files\obs-studio\python"
./run_server.ps1 -Port 8080 -Bind 0.0.0.0
```

OBS WebSocket(v5)는 기본 포트 4455, 비밀번호는 OBS 설정에 따릅니다. 필요 시 `python/app/config.py`에 정의된 환경 변수를 `.env`에 설정하세요.

### 엔드포인트
- GET `/api/health`
- GET `/api/obs/version`
- GET `/api/obs/scenes`
- POST `/api/obs/scene/{scene_name}`
- POST `/api/obs/stream/start`
- POST `/api/obs/stream/stop`

