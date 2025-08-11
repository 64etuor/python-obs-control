## 개요

OBS(WebSocket v5) 제어용 FastAPI 서버. 윈도우에서 OBS 자동 실행/가디언, 장면 전환, 소스 스크린샷 저장/이미지 소스 갱신, 웹 오버레이(토스트/YouTube/Shorts), 카메라 입력 구성(UI), 프로메테우스 메트릭, ELK 기반 로그 뷰를 제공합니다.

### 주요 기능
- OBS 자동 실행/가디언: 프로세스 감시·재기동, WS 준비 대기
- 부트스트랩: 표준 장면 생성(`Home`, `LiveFront`, `YouTube` 등)
- 단축키: 장면 전환/스트림 토글/스크린샷(전·후, 앞/옆/뒤, 참조)
- 카메라 입력 구성: UI(`/settings/ui`) + API로 DirectShow 디바이스 바인딩
- 스크린샷 API: 저장 후 이미지 소스 즉시 갱신 지원
- 오버레이: `/overlay` 토스트, `/overlay/youtube`, `/overlay/shorts`
- 메트릭: `/metrics` (Prometheus)
- 진단: `/api/diagnostics`, 로그 버퍼, 스레드/프로세스/서비스 보기, 로그 레벨 변경
- ELK: JSON 파일 로그 수집, Kibana 대시보드

## 빠른 시작 (Windows)
1) 필수
- Python 3.11+
- OBS Studio 30+ (obs-websocket v5 내장)
- (선택) Docker Desktop: ELK 사용 시

2) 설치
```powershell
cd C:\git_projects\python-obs-control
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r requirements.txt
Copy-Item .env_example .env -Force
```

3) 서버 실행
- 권장: PowerShell 스크립트(환경 로드/핫리로드 포함)
```powershell
./run_server.ps1 -Port 8080 -Bind 0.0.0.0
```
- 직접 실행
```powershell
uvicorn app.presentation.app_factory:app --host 0.0.0.0 --port 8080 --reload
```

4) 기본 동작
- 첫 요청 전 서버 스타트업에서: 로깅 초기화 → (옵션) OBS 자동 실행 및 WS 대기 → (옵션) 표준 장면 부트스트랩 → 단축키 리스너 시작 → 스크린샷 보존 루프 시작

## 환경변수(.env)
`.env_example`를 복사해 사용. 주요 항목:
- OBS_PORT, OBS_PASSWORD, OBS_AUTO_DISMISS_SAFEMODE, AUTO_BOOTSTRAP
- APP_NAME, ENV
- LOG_FILE_ENABLED, LOG_DIR, LOG_FILE_NAME, LOG_ROTATION(=time|size), LOG_DAILY_SPLIT, LOG_INTERVAL, LOG_BACKUP_COUNT, LOG_UTC
- LEGION(지역/브랜드 헤더 제어), OVERLAY_BRAND, OVERLAY_BRAND_COLOR, OVERLAY_CLOCK_ENABLED
- DIAG_TOKEN(진단 엔드포인트 토큰)
- SCREENSHOT_DIR(기본: `%USERPROFILE%/Pictures/OBS-Screenshots`)

추가 설정(코드 기본값):
- `obs_autostart=True`, `obs_ws_autoconfigure=True`, `obs_guardian_enabled=True`
- `screenshot_dir`는 `app/config.py`의 `Settings`로도 제어 가능

## API 요약
- 헬스체크: `GET /api/health`
- 장면/버전
  - `GET /api/obs/version`
  - `GET /api/obs/scenes`
  - `POST /api/obs/scene/{scene_name}`
- 스크린샷
  - `POST /api/obs/screenshot` (쿼리/폼 파라미터)
    - `source_name`, `image_file_path`, `image_format=png`, `image_width`, `image_height`, `image_compression_quality=100`, `image_input_update`
  - 단축 엔드포인트: `POST /api/obs/screenshot/(front|side|rear)[/after]`
- 핫키 설정
  - `GET /api/hotkeys`
  - `POST /api/hotkeys` (JSON 저장, 즉시 핫리로드 시도)
  - 씬 목록(핫키 UI용): `GET /api/hotkeys/scenes`
- 카메라 설정
  - `GET /api/cams/devices` (로컬 열거 + 상세)
  - `GET /api/cams/devices/obs` (OBS 기준 DirectShow 리스트)
  - `GET /api/cams/config` / `POST /api/cams/config` (폼: `front`,`side`,`rear`)
  - UI: `GET /settings/ui`
- 오버레이
  - 페이지: `GET /overlay`
  - YouTube: `GET /overlay/youtube?video_id=...&muted=0&controls=1&loop=0&resume_on_show=0&restore=1`
  - Shorts: `GET /overlay/shorts?ids=ID1,ID2...` 또는 `?playlist=...`/`?channel=UC...`
  - WS: `GET /overlay/ws` (서버가 토스트/제어 이벤트 브로드캐스트)
- 진단(헤더 `x-diag-token: <DIAG_TOKEN>` 필요)
  - `GET /api/diagnostics`
  - `GET /api/logs?limit=200`
  - `GET /api/diagnostics/log-level` / `POST /api/diagnostics/log-level?level=INFO`
  - `GET /api/diagnostics/threads`
  - `GET /api/diagnostics/processes?limit=10`
  - `GET /api/diagnostics/services` (Windows)
- 메트릭: `GET /metrics`

### 예시(curl)
```bash
curl http://localhost:8080/api/health
curl "http://localhost:8080/api/obs/scene/LiveFront"
curl -X POST "http://localhost:8080/api/obs/screenshot/front"
curl -H "x-diag-token: please-change-me" http://localhost:8080/api/diagnostics
```

## 단축키(기본값/구성)
- 파일: `config/hotkeys.json` (없으면 자동 생성/병합)
- 주요 기본값
  - 장면: `Home=F10`, `ReferenceSearch=F11`, `LiveFront=ctrl+1`, `YouTube=shift+F12` 등
  - 스크린샷: 전(앞/옆/뒤)=`F5/F6/F7`, 후(앞/옆/뒤)=`shift+F5/F6/F7`
  - 참조(헤어): `F8` → `window_capture`를 `img_hair_reference`에 갱신
  - 이미지 리셋: `ctrl+F8` 두 번(확인창 개념)
  - 스트림 토글: `F9`
- 실행 시 핫키 리스너가 자동 시작하며, `POST /api/hotkeys`로 저장 후 즉시 재적용 시도
- 관리자 권한 필요할 수 있음(키보드 후킹 실패 시 로그 경고)

## 카메라 입력 구성
- UI: `GET /settings/ui`
  - 서버의 상세 열거 → 실패 시 OBS/브라우저 열거로 폴백
  - 선택값은 가능한 경우 DirectShow Moniker(Path)로 저장해 안정적 바인딩
- API: `GET/POST /api/cams/config`
  - 내부적으로 입력 미존재/종류불일치 시 재생성 시도

## 스크린샷 동작
- 저장 경로 기본 규칙: `screenshot_dir/YYYY/MM/DD/yyyymmdd_hhmmss_<source>.png`
- 최소 해상도 제약(OBS): `width/height >= 8`
- 오류 가이드(HTTP 400 변환)
  - 디렉터리 없음(code 600): 경로 유효성 확인
  - 렌더 불가/소스명 오타(code 702 등): 소스 활성/정확성 확인

## 오버레이
- `/overlay`는 투명 배경 웹 페이지. WS(`/overlay/ws`)를 통해 서버에서 토스트 이벤트 수신
- `LEGION=KOREA`일 때 헤더/시계 표시, 브랜드 색상/텍스트는 `OVERLAY_*`로 커스터마이즈
- 장면 전환 시(`POST /api/obs/scene/...`) `YouTube`/`Shorts`면 오버레이에 `resume`, 그 외에는 `pause` 제어 이벤트 브로드캐스트

## 로깅/메트릭/ELK
### 로그
- 콘솔: 텍스트, 파일: JSON(옵션 `LOG_FILE_ENABLED=1`)
- 경로: `logs/<YYYY-MM-DD>/server.log` (time-rotation+daily split 시)

### 메트릭
- `prometheus-fastapi-instrumentator` + psutil 샘플러
- 시스템: `system_cpu_percent`, `system_memory_*`
- 프로세스: `process_cpu_percent`, `process_memory_*`, `app_process_open_handles`

### ELK 로컬 스택
1) `.env_example`에서 `LOG_FILE_ENABLED=1` 설정 후 `.env` 준비, 서버 한 번 실행해 `logs/` 생성
2) 실행
```powershell
scripts/elk_up.ps1
# 또는
docker compose -f elk/docker-compose.yml up -d
```
3) Kibana 접속: `http://localhost:5601`
   - 인덱스 패턴: `python-obs-control-*`
4) 종료: `scripts/elk_down.ps1`

비고
- Filebeat: `logs/**/*.log` JSON 수집, `time` 필드를 `@timestamp`로 사용
- 인덱스: `python-obs-control-<env>-YYYY.MM.DD`

## 스크린샷 보존(자동 청소)
- 설정 파일: `config/screenshot_retention.json`
- 기본값: enabled=true, days=30, interval_sec=3600
- 서버 시작 시 백그라운드로 주기적 삭제 수행(대상 루트: `screenshot_dir`)

## OBS 관련 참고
- 첫 실행 시 `%APPDATA%/obs-studio/global.ini`에 WebSocket 설정을 자동 적용(포트/비번)
- 안전 모드/크래시 다이얼로그 자동 비활성화 시도
- 포터블 설치일 경우 `OBS_DATA_PATH` 자동 해석 시도

## 트러블슈팅
- 핫키가 안 먹힘: PowerShell/터미널을 관리자 권한으로 실행, `keyboard` 모듈 경고 확인
- OBS 연결 실패: `OBS_PORT/OBS_PASSWORD` 확인, 방화벽/WS 포트 점검, `obs_guardian_enabled` 유지 권장
- 스크린샷 400: 경로 생성 실패(디렉터리 권한/드라이브 확인), 최소 해상도, 소스명 체크

## 라이선스
- 파일에 명시 없으면 내부 사용 목적으로 가정. 필요 시 명시 추가하세요.
