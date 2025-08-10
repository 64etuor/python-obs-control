import asyncio
from typing import Optional, Any

from obsws_python import ReqClient
from obsws_python.error import OBSSDKRequestError

from .config import settings


class OBSConnectionManager:
    """OBS WebSocket v5 manager using ReqClient.

    Blocking calls are offloaded to a thread.
    """

    def __init__(self) -> None:
        self._client: Optional[ReqClient] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> ReqClient:
        async with self._lock:
            if self._client is not None:
                return self._client
            try:
                self._client = ReqClient(
                    host=settings.obs_host,
                    port=settings.obs_port,
                    password=settings.obs_password,
                    timeout=10,
                )
                return self._client
            except Exception as exc:  # noqa: BLE001
                self._client = None
                raise RuntimeError(
                    f"OBS WebSocket 연결 실패: {settings.obs_host}:{settings.obs_port} — {exc}"
                )

    async def disconnect(self) -> None:
        async with self._lock:
            self._client = None

    async def _to_thread(self, func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    # Helpers
    @staticmethod
    def _jsonable(obj: Any) -> Any:
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        if isinstance(obj, dict):
            return {k: OBSConnectionManager._jsonable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [OBSConnectionManager._jsonable(v) for v in obj]
        data = getattr(obj, "datain", None)
        if data is not None:
            return OBSConnectionManager._jsonable(data)
        try:
            return {k: OBSConnectionManager._jsonable(v) for k, v in vars(obj).items() if not k.startswith("_")}
        except Exception:
            return str(obj)

    # Public convenience methods (examples)
    async def get_version(self) -> dict:
        client = await self.connect()
        resp = await self._to_thread(client.get_version)
        return self._jsonable(resp)

    async def get_scenes(self) -> list[dict]:
        client = await self.connect()
        resp = await self._to_thread(client.get_scene_list)
        scenes = getattr(resp, "scenes", None)
        if scenes is None:
            data = getattr(resp, "datain", {}) or {}
            scenes = data.get("scenes", [])
        return self._jsonable(scenes)

    async def set_current_scene(self, scene_name: str) -> None:
        client = await self.connect()
        # 일부 버전에서 키워드 인자를 허용하지 않으므로 위치 인자로 호출
        await self._to_thread(client.set_current_program_scene, scene_name)

    async def start_streaming(self) -> None:
        client = await self.connect()
        await self._to_thread(client.start_stream)

    async def stop_streaming(self) -> None:
        client = await self.connect()
        await self._to_thread(client.stop_stream)


    async def get_stream_status(self) -> dict:
        client = await self.connect()
        resp = await self._to_thread(getattr(client, "get_stream_status"))
        return self._jsonable(resp)

    async def toggle_streaming(self) -> None:
        status = await self.get_stream_status()
        is_active = bool(status.get("outputActive") or status.get("active") or status.get("output_active"))
        if is_active:
            await self.stop_streaming()
        else:
            await self.start_streaming()

    async def save_source_screenshot(
        self,
        source_name: str,
        image_file_path: str,
        image_format: str = "png",
        image_width: int | None = None,
        image_height: int | None = None,
        image_compression_quality: int = 100,
    ) -> str:
        client = await self.connect()

        # Ensure parent directory exists to avoid OBS 600 error
        try:
            from pathlib import Path

            Path(image_file_path).parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        # Normalize optional dims: omit if not provided (pass None)
        width = int(image_width) if image_width else None
        height = int(image_height) if image_height else None

        # Prefer save to file if available; on failure, fallback to base64 API
        save_fn = getattr(client, "save_source_screenshot", None)
        if save_fn is not None:
            try:
                await self._to_thread(
                    save_fn,
                    source_name,
                    image_format,
                    image_file_path,
                    width,
                    height,
                    int(image_compression_quality),
                )
                return image_file_path
            except (OBSSDKRequestError, Exception):  # noqa: BLE001
                # Fallback below
                pass

        # Fallback: get base64 and write ourselves
        import base64
        get_fn = getattr(client, "get_source_screenshot", None)
        if get_fn is None:
            raise RuntimeError("OBS client does not support screenshots on this version")
        resp = await self._to_thread(
            get_fn,
            source_name,
            image_format,
            width,
            height,
            int(image_compression_quality),
        )
        data = (
            getattr(resp, "image_data", None)
            or getattr(resp, "imageData", None)
            or getattr(resp, "datain", {}).get("image_data")
            or getattr(resp, "datain", {}).get("imageData")
        )
        if not data:
            raise RuntimeError("No imageData returned from OBS")
        raw = base64.b64decode(data)
        with open(image_file_path, "wb") as f:
            f.write(raw)
        return image_file_path

    async def set_input_settings(self, input_name: str, input_settings: dict, overlay: bool = False) -> None:
        client = await self.connect()
        await self._to_thread(client.set_input_settings, input_name, input_settings, overlay)

    async def update_image_source_file(self, image_input_name: str, new_file_path: str) -> None:
        await self.set_input_settings(image_input_name, {"file": new_file_path}, False)

obs_manager = OBSConnectionManager()

