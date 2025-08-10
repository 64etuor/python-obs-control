from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from app.infrastructure.overlay.notification_service_impl import overlay_notifications


router = APIRouter(prefix="/overlay")


@router.get("/", response_class=HTMLResponse)
async def overlay_index() -> HTMLResponse:
    html = """<!doctype html><html><head><meta charset='utf-8'/><title>Overlay</title>
<style>
body{margin:0;background:transparent;overflow:hidden}
#toasts{position:fixed;top:16px;right:16px;display:flex;flex-direction:column;gap:8px;z-index:999999}
.toast{min-width:200px;max-width:480px;padding:10px 12px;border-radius:8px;color:#fff;font-family:Segoe UI,Arial;box-shadow:0 4px 16px rgba(0,0,0,.3);opacity:.95}
.toast.info{background:#2b7de9}
.toast.success{background:#34a853}
.toast.warning{background:#fbbc05;color:#222}
.toast.error{background:#ea4335}
@keyframes slidein{from{transform:translateY(-10px);opacity:0}to{transform:translateY(0);opacity:1}}
@keyframes fadeout{to{opacity:0;transform:translateY(-10px)}}
.toast{animation:slidein .2s ease-out}
</style></head><body>
<div id='toasts'></div>
<script>
const q = new URLSearchParams(location.search);
const endpoint = (q.get('ws')||'').trim() || (location.origin.replace(/^http/,'ws') + '/overlay/ws');
const toasts = document.getElementById('toasts');
let sock;
function showToast(msg, level='info', timeoutMs=2000){
  const d = document.createElement('div');
  d.className = 'toast '+(level||'info');
  d.textContent = String(msg??'');
  toasts.appendChild(d);
  const t = setTimeout(()=>{ d.style.animation='fadeout .25s ease-in forwards'; setTimeout(()=>d.remove(), 260); }, Math.max(500, timeoutMs||2000));
  d.onclick = ()=>{ clearTimeout(t); d.remove(); };
}
function connect(){
  sock = new WebSocket(endpoint);
  sock.onopen = ()=>{};
  sock.onclose = ()=>{ setTimeout(connect, 1000); };
  sock.onmessage = (ev)=>{
    try{ const data = JSON.parse(ev.data); if(data?.type==='toast'){ showToast(data.message, data.level, data.timeout_ms); } }
    catch(e){ /* ignore */ }
  };
}
connect();
</script>
</body></html>"""
    return HTMLResponse(content=html)


@router.websocket("/ws")
async def overlay_ws(ws: WebSocket) -> None:
    await ws.accept()
    await overlay_notifications.register(ws)
    try:
        while True:
            # We don't expect incoming messages now; keepalive by awaiting receive_text
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await overlay_notifications.unregister(ws)


