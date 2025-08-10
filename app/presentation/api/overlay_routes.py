from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from app.infrastructure.overlay.notification_service_impl import overlay_notifications
from app.config import settings
import json


router = APIRouter(prefix="/overlay")


@router.get("/", response_class=HTMLResponse)
async def overlay_index() -> HTMLResponse:
    legion = (settings.legion or "").strip().upper()
    show_header = legion == "KOREA"
    brand_text = (settings.overlay_brand or "MIRRORLESS").strip()
    brand_color = (settings.overlay_brand_color or "#ffffff").strip()
    clock_enabled = bool(settings.overlay_clock_enabled)
    # Build static HTML, inject dynamic flags via JS
    html = """<!doctype html><html><head><meta charset='utf-8'/><title>Overlay</title>
<meta name='viewport' content='width=device-width,initial-scale=1'/>
<style>
:root{
  --radius:12px; --gap:10px;
  --glass-bg: rgba(20,20,20,.55);
  --glass-border: rgba(255,255,255,.14);
  --shadow: 0 12px 30px rgba(0,0,0,.35);
  --fg: #fff; --fg-dark: #111;
  --info: #2b7de9; --success:#34a853; --warning:#fbbc05; --error:#ea4335;
  --header-pad-y: 10px; --header-pad-x: 14px;
}
html,body{height:100%}
body{margin:0;background:transparent;overflow:hidden}
#header{position:fixed;left:16px;right:16px;top:10px;display:none;align-items:center;z-index:2147483646;pointer-events:none;
  padding: var(--header-pad-y) var(--header-pad-x);
  border-radius: var(--radius);
  background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02)), var(--glass-bg);
  border: 1px solid var(--glass-border);
  backdrop-filter: blur(8px) saturate(120%);
  box-shadow: var(--shadow);
}
#brand{font:700 28px/1.2 'Segoe UI',system-ui,-apple-system,Arial;color:#fff;letter-spacing:.8px;text-shadow:0 2px 10px rgba(0,0,0,.35)}
#clock{margin-left:auto;font:600 20px/1.2 'Segoe UI',system-ui,-apple-system,Arial;color:#fff;opacity:.95;text-shadow:0 2px 10px rgba(0,0,0,.35)}
#toasts{position:fixed;inset:auto 16px 16px auto;top:16px;right:16px;display:flex;flex-direction:column;gap:var(--gap);z-index:2147483647;pointer-events:none}
.toast{pointer-events:auto;display:flex;align-items:flex-start;gap:10px; min-width:260px; max-width:460px; border-radius:var(--radius); padding:12px 14px; color:var(--fg); font: 14px/1.35 'Segoe UI',system-ui,-apple-system,Arial; box-shadow:var(--shadow); position:relative; isolation:isolate;
  background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02)), var(--glass-bg);
  border: 1px solid var(--glass-border);
  backdrop-filter: blur(8px) saturate(120%);
}
.toast::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;border-radius:var(--radius) 0 0 var(--radius);background: var(--accent, rgba(255,255,255,.25));opacity:.95}
.toast .icon{width:18px;height:18px;margin-top:1px;flex:0 0 auto;opacity:.95;color: var(--accent, currentColor)}
.toast .content{flex:1 1 auto;min-width:0}
.toast .msg{white-space:pre-wrap;word-break:break-word}
.toast .close{appearance:none;border:0;background:transparent;color:inherit;opacity:.8;cursor:pointer;font-size:16px;line-height:1;padding:2px 4px;border-radius:6px}
.toast .close:hover{opacity:1;background:rgba(255,255,255,.08)}
.toast .progress{position:absolute;left:8px;right:8px;bottom:6px;height:2px;border-radius:2px;overflow:hidden;background:rgba(255,255,255,.12)}
.toast .bar{height:100%;transform-origin:left center;animation:shrink var(--dur) linear forwards}
.toast.info .bar{background:var(--info)}
.toast.success .bar{background:var(--success)}
.toast.warning .bar{background:var(--warning)}
.toast.error .bar{background:var(--error)}

/* Level accents */
.toast.info{--accent: var(--info); box-shadow:0 10px 26px rgba(43,125,233,.35), var(--shadow); background: linear-gradient(180deg, rgba(43,125,233,.15), rgba(43,125,233,.08)), var(--glass-bg)}
.toast.success{--accent: var(--success); box-shadow:0 10px 26px rgba(52,168,83,.35), var(--shadow); background: linear-gradient(180deg, rgba(52,168,83,.15), rgba(52,168,83,.08)), var(--glass-bg)}
.toast.warning{--accent: var(--warning); color:var(--fg-dark); box-shadow:0 10px 26px rgba(251,188,5,.35), var(--shadow); background:linear-gradient(180deg, rgba(251,188,5,.35), rgba(251,188,5,.2)), rgba(255,255,255,.92)}
.toast.error{--accent: var(--error); box-shadow:0 10px 26px rgba(234,67,53,.35), var(--shadow); background: linear-gradient(180deg, rgba(234,67,53,.18), rgba(234,67,53,.08)), var(--glass-bg)}

/* Motion */
@keyframes enter{0%{opacity:0;transform:translateY(-12px) scale(.98)} 100%{opacity:1;transform:none}}
@keyframes exit{100%{opacity:0;transform:translateY(-10px) scale(.98)}}
@keyframes shrink{from{transform:scaleX(1)} to{transform:scaleX(0)}}
.toast.entering{animation:enter .24s cubic-bezier(.2,.7,.2,1) both}
.toast.closing{animation:exit .22s ease both}
.toast.paused .bar{animation-play-state:paused}

/* Position presets via query param 'pos' (tr, tl, br, bl) */
body.pos-tl #toasts{left:16px;right:auto;top:16px;bottom:auto}
body.pos-br #toasts{left:auto;right:16px;top:auto;bottom:16px}
body.pos-bl #toasts{left:16px;right:auto;top:auto;bottom:16px}
</style></head><body>
<div id='header'><div id='brand'></div><div id='clock'></div></div>
<div id='toasts'></div>
<script>
"""
    html += (
        f"const showHeader = {'true' if show_header else 'false'}; "
        f"const legion = {json.dumps(legion)}; "
        f"const brandText = {json.dumps(brand_text)}; "
        f"const brandColor = {json.dumps(brand_color)}; "
        f"const clockEnabled = {'true' if clock_enabled else 'false'};\n"
    )
    html += """
const q = new URLSearchParams(location.search);
const endpoint = (q.get('ws')||'').trim() || (location.origin.replace(/^http/,'ws') + '/overlay/ws');
const pos = (q.get('pos')||'tr').toLowerCase();
document.body.classList.add('pos-'+(['tl','tr','bl','br'].includes(pos)?pos:'tr'));
const maxToasts = Math.max(1, Math.min(6, +(q.get('max')||4)));
const toasts = document.getElementById('toasts');

// Apply header visibility and toasts offset only when at top positions
try{
  const header = document.getElementById('header');
  const brand = document.getElementById('brand');
  const clock = document.getElementById('clock');
  header.style.display = showHeader ? 'flex' : 'none';
  // brand content/color
  if(brand){ brand.textContent = brandText || 'MIRRORLESS'; brand.style.color = brandColor || '#ffffff'; }
  // clock toggle
  clock.style.display = clockEnabled ? 'block' : 'none';
  // After layout, compute actual height to set offset precisely
  requestAnimationFrame(()=>{
    if(pos === 'tr' || pos === 'tl'){
      const h = showHeader ? Math.ceil((header.getBoundingClientRect?.().height || 0) + 12) : 16;
      toasts.style.top = h + 'px';
    }
  });
}catch(e){}

const ICONS = {
  info: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2a10 10 0 100 20 10 10 0 000-20z" fill="currentColor" opacity=".18"/><path d="M11 10h2v7h-2v-7zm0-3h2v2h-2V7z" fill="currentColor"/></svg>`,
  success: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2a10 10 0 100 20 10 10 0 000-20z" fill="currentColor" opacity=".18"/><path d="M17 9l-6.5 6L7 11.5l1.4-1.4L10.5 12l5.1-5 1.4 2z" fill="currentColor"/></svg>`,
  warning: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2l10 18H2L12 2z" fill="currentColor" opacity=".2"/><path d="M11 10h2v4h-2v-4zm0 6h2v2h-2v-2z" fill="currentColor"/></svg>`,
  error: `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" fill="currentColor" opacity=".2"/><path d="M15.5 8.5L8.5 15.5m0-7l7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`
};

function clamp(n, a, b){ return Math.max(a, Math.min(b, n)); }

function removeToast(el){
  if(!el) return;
  el.classList.add('closing');
  el.addEventListener('animationend', ()=>{ el.remove(); }, {once:true});
}

function showToast(msg, level='info', timeoutMs=2000){
  const L = (level||'info').toLowerCase();
  const dur = clamp(~~(timeoutMs||2000), 600, 10000);

  const d = document.createElement('div');
  d.className = 'toast entering '+L;
  d.style.setProperty('--dur', dur+'ms');

  const icon = document.createElement('div'); icon.className='icon'; icon.innerHTML = ICONS[L] || ICONS.info;
  const content = document.createElement('div'); content.className='content';
  const msgEl = document.createElement('div'); msgEl.className='msg'; msgEl.textContent = String(msg ?? '');
  content.appendChild(msgEl);
  const close = document.createElement('button'); close.className='close'; close.setAttribute('aria-label','Close'); close.textContent='×';
  const progress = document.createElement('div'); progress.className='progress';
  const bar = document.createElement('div'); bar.className='bar'; progress.appendChild(bar);

  d.appendChild(icon); d.appendChild(content); d.appendChild(close); d.appendChild(progress);
  toasts.appendChild(d);

  requestAnimationFrame(()=> d.classList.remove('entering'));

  let timer = setTimeout(()=> removeToast(d), dur + 80);
  function pause(){ if(timer){ clearTimeout(timer); timer=null; } d.classList.add('paused'); }
  function resume(){ if(!timer){ d.classList.remove('paused'); timer = setTimeout(()=> removeToast(d), Math.max(300, dur/2)); } }
  d.addEventListener('mouseenter', pause);
  d.addEventListener('mouseleave', resume);
  close.addEventListener('click', ()=> removeToast(d));

  while(toasts.children.length > maxToasts){ removeToast(toasts.firstElementChild); break; }
}

let sock;
function connect(){
  try{ sock = new WebSocket(endpoint); }catch(e){ setTimeout(connect, 1500); return; }
  sock.onopen = ()=>{};
  sock.onclose = ()=>{ setTimeout(connect, 1000); };
  sock.onmessage = (ev)=>{
    try{
      const data = JSON.parse(ev.data);
      if(data?.type==='toast'){ showToast(data.message, data.level, data.timeout_ms); }
    }catch(e){}
  };
}
connect();

// Clock rendering (locale based on legion)
if(showHeader && clockEnabled){
  try{
    const clockEl = document.getElementById('clock');
    const locale = legion === 'KOREA' ? 'ko-KR' : undefined;
    const opts = legion === 'KOREA'
      ? { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }
      : { hour: '2-digit', minute: '2-digit', second: '2-digit' };
    function tick(){
      const now = new Date();
      clockEl.textContent = now.toLocaleTimeString(locale, opts);
    }
    tick();
    setInterval(tick, 1000);
  }catch(e){}
}

if(q.get('demo')==='1'){
  setTimeout(()=>{
    showToast('Connected to overlay', 'success', 1400);
    setTimeout(()=>showToast('Info message with more details', 'info', 2200), 300);
    setTimeout(()=>showToast('Warning: check your input source', 'warning', 2600), 650);
    setTimeout(()=>showToast('Error: failed to save', 'error', 2600), 1100);
  }, 300);
}
</script>
</body></html>"""
    return HTMLResponse(content=html)


@router.get("/youtube", response_class=HTMLResponse)
async def overlay_youtube(
    video_id: str | None = None,
    start: int = 0,
    muted: bool = False,
    controls: bool = False,
    loop: bool = False,
    resume_on_show: bool = False,
    restore: bool = True,
) -> HTMLResponse:
    if not video_id:
        return HTMLResponse(
            "<!doctype html><html><head><meta charset='utf-8'/><meta name='viewport' content='width=device-width,initial-scale=1'/>"
            "<title>YouTube Overlay</title><style>html,body{height:100%;margin:0;background:#000;color:#ccc;display:grid;place-items:center;font:14px/1.4 Segoe UI,Arial}</style></head>"
            "<body><div>Missing parameter: <code>video_id</code>. Example: <code>/overlay/youtube?video_id=dQw4w9WgXcQ&controls=0&muted=0</code></div></body></html>"
        )

    cfg = {
        "videoId": video_id,
        "start": max(0, int(start)),
        "controls": bool(controls),
        "muted": bool(muted),
        "loop": bool(loop),
        "resumeOnShow": bool(resume_on_show),
        "restore": bool(restore),
    }
    cfg_json = json.dumps(cfg)

    html = (
        "<!doctype html><html><head><meta charset='utf-8'/><meta name='viewport' content='width=device-width,initial-scale=1'/>"
        "<title>YouTube Overlay</title>"
        "<style>"
        "html,body,#player{height:100%;width:100%;margin:0;background:#000;overflow:hidden}"
        "#player iframe{position:absolute;inset:0; width:100%; height:100%;}"
        ".mask{position:fixed;inset:0;}"
        "</style></head><body>"
        "<script id='cfg' type='application/json'>" + cfg_json + "</script>"
        "<div id='player'></div>"
        "<script>"
        "function getCfg(){ try{ return JSON.parse(document.getElementById('cfg').textContent||'{}'); }catch(_){ return {}; } }"
        "const CFG = getCfg();"
        "const VIDEO_ID = CFG.videoId;"
        "const START = Math.max(0, ~~(CFG.start||0));"
        "const WANT_CONTROLS = !!CFG.controls;"
        "const WANT_MUTED = !!CFG.muted;"
        "const WANT_LOOP = !!CFG.loop;"
        "const RESUME_ON_SHOW = !!CFG.resumeOnShow;"
        "const RESTORE = !!CFG.restore;"
        "let player; let ready=false; let lastSaved=0;"
        "function loadYT(){ const tag=document.createElement('script'); tag.src='https://www.youtube.com/iframe_api'; document.head.appendChild(tag); }"
        "function onYouTubeIframeAPIReady(){"
        "  const opts={"
        "    videoId: VIDEO_ID,"
        "    playerVars:{autoplay:0,controls:(WANT_CONTROLS?1:0),disablekb:0,modestbranding:1,rel:0,playsinline:1,fs:0,iv_load_policy:3,loop:(WANT_LOOP?1:0),playlist:(WANT_LOOP?VIDEO_ID:undefined),start:(START>0?START:0),enablejsapi:1,origin:location.origin},"
        "    events:{"
        "      onReady:(ev)=>{"
        "        ready=true;"
        "        try{ if(WANT_MUTED) ev.target.mute(); else ev.target.unMute(); }catch(_){ }"
        "        if(RESTORE){ try{ const key='yt:'+VIDEO_ID; const pos=+(localStorage.getItem(key)||'0'); if(pos>2) ev.target.seekTo(pos,true); }catch(_){ } }"
        "      },"
        "      onStateChange:(_ev)=>{ }"
        "    }"
        "  };"
        "  player=new YT.Player('player',opts);"
        "}"
        "window.onYouTubeIframeAPIReady=onYouTubeIframeAPIReady;"
        "loadYT();"
        "document.addEventListener('visibilitychange',()=>{ if(!player||!ready) return; try{ if(document.hidden){player.pauseVideo();} else if(RESUME_ON_SHOW){player.playVideo();} }catch(_){ } });"
        "setInterval(()=>{ if(!player||!ready) return; try{ const t=Math.floor(player.getCurrentTime?.()||0); if(!Number.isFinite(t)) return; if(Math.abs(t-lastSaved)>=2){ localStorage.setItem('yt:'+VIDEO_ID,String(t)); lastSaved=t; } }catch(_){ } },2000);"
        "</script></body></html>"
    )
    return HTMLResponse(content=html)

@router.websocket("/ws")
async def overlay_ws(ws: WebSocket) -> None:
    await ws.accept()
    await overlay_notifications.register(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await overlay_notifications.unregister(ws)


