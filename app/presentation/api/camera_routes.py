from __future__ import annotations

from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from app.container import list_camera_devices, get_camera_config, apply_camera_config
from app.infrastructure.obs.camera_config import list_dshow_devices_via_obs

router = APIRouter(prefix="/api/cams")


@router.get("/devices")
async def devices() -> dict:
    return await list_camera_devices()()


@router.get("/devices/obs")
async def devices_obs() -> JSONResponse:
    items = await list_dshow_devices_via_obs()
    return JSONResponse(content={"obs": items})


@router.get("/config")
async def config_get() -> dict:
    return await get_camera_config()()


@router.post("/config")
async def config_set(
    front: str | None = Form(default=None),
    side: str | None = Form(default=None),
    rear: str | None = Form(default=None),
) -> dict:
    try:
        return await apply_camera_config()(front=front, side=side, rear=rear)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))


# UI page

@router.get("/ui", response_class=HTMLResponse)
async def camera_ui() -> HTMLResponse:
    html = """<!doctype html><html><head><meta charset='utf-8'/><title>Camera Setup</title>
<style>
body{font-family:Segoe UI,Arial;margin:20px}
label{display:block;margin:12px 0 6px}
select,input,button{padding:8px;font-size:14px}
.container{max-width:980px}
.row{display:flex;gap:12px;align-items:center;margin:8px 0}
.row>label{min-width:90px}
.note{color:#666;margin-top:12px}
.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:12px}
video{background:#111;width:100%;aspect-ratio:16/9}
.small{font-size:12px;color:#777}
.spacer{flex:1}
pre{background:#f4f4f4;padding:8px;overflow:auto}
code{background:#eee;padding:2px 4px;border-radius:4px}
</style></head><body>
<div class='container'>
  <h2>Camera Setup</h2>
  <div class='row'>
    <label>Front</label><select id='front'></select>
    <label>Side</label><select id='side'></select>
    <label>Rear</label><select id='rear'></select>
    <span class='spacer'></span>
    <button id='reload'>Reload</button>
    <button id='save'>Apply</button><span id='status'></span>
  </div>
  <div class='note'>장치명이 동일할 때는 상세 경로(Path)를 복사해 드롭다운에 그대로 붙여넣어 설정하세요.</div>
  <div id='detail_block' class='note'></div>
  <div class='grid'>
    <div><div>Preview Front <span class='small' id='f_info'></span></div><video id='f_v' autoplay muted playsinline></video></div>
    <div><div>Preview Side <span class='small' id='s_info'></span></div><video id='s_v' autoplay muted playsinline></video></div>
    <div><div>Preview Rear <span class='small' id='r_info'></span></div><video id='r_v' autoplay muted playsinline></video></div>
  </div>
  <div class='note'>OBS 내부에서 읽은 DirectShow 항목(디버그):</div>
  <pre id='obs_dump'>(loading...)</pre>
</div>
<script>
function stopAllPreviews(){
  for(const id of ['f_v','s_v','r_v']){
    const el = document.getElementById(id);
    try{ (el.srcObject?.getTracks?.()||[]).forEach(t=>t.stop()); el.srcObject=null; }catch(_){}
  }
}

async function populateFromServer(selectIds){
  try{
    const dev = await fetch('/api/cams/devices').then(r=>r.json());
    if(dev && dev.detail && Array.isArray(dev.detail.devices) && dev.detail.devices.length){
      const pairs = dev.detail.devices.map(d=>({label: d.name, value: d.path || d.value || d.name}));
      for(const id of selectIds){ fillSelectPairs(id, pairs); }
      const detail = dev.detail.devices.map(d=>`<div><code>${d.name}</code> — <code>${d.path}</code></div>`).join('');
      document.getElementById('detail_block').innerHTML = detail || '(no detail)';
      return true;
    }
    if(dev && Array.isArray(dev.devices) && dev.devices.length){
      for(const id of selectIds){ fillSelect(id, dev.devices); }
      return true;
    }
  }catch(e){}

  // Fallback: fill from OBS dshow property list (name/value)
  try{
    const obs = await fetch('/api/cams/devices/obs').then(r=>r.json());
    const items = Array.isArray(obs?.obs) ? obs.obs : [];
    if(items.length){
      const pairs = items.map(it=>({label: it.name, value: it.value}));
      for(const id of selectIds){ fillSelectPairs(id, pairs); }
      document.getElementById('detail_block').innerHTML = items.map(d=>`<div><code>${d.name}</code> — <code>${d.value}</code></div>`).join('');
      return true;
    }
  }catch(e){}
  return false;
}

function fillSelect(id, devices){
  const sel = document.getElementById(id);
  sel.innerHTML = '';
  const none = document.createElement('option'); none.value=''; none.textContent='(none)'; sel.appendChild(none);
  const seen = new Set();
  for(const d of devices){
    if(!d || seen.has(d)) continue; seen.add(d);
    const o = document.createElement('option'); o.value=d; o.textContent=d; sel.appendChild(o);
  }
}

function fillSelectPairs(id, pairs){
  const sel = document.getElementById(id);
  sel.innerHTML = '';
  const none = document.createElement('option'); none.value=''; none.textContent='(none)'; sel.appendChild(none);
  const seen = new Set();
  for(const p of pairs||[]){
    const v = p?.value ?? p?.path ?? p?.id ?? '';
    const t = p?.label ?? p?.name ?? String(v||'');
    if(!v || seen.has(v)) continue; seen.add(v);
    const o = document.createElement('option'); o.value=String(v); o.textContent=String(t); sel.appendChild(o);
  }
}

async function populateFromBrowser(selectIds){
  try{
    const devs = await navigator.mediaDevices.enumerateDevices();
    const vids = devs.filter(d=>d.kind==='videoinput');
    const labels = vids.map(v=>v.label).filter(Boolean);
    if(labels.length){
      for(const id of selectIds){ fillSelect(id, labels); }
      return true;
    }
  }catch(e){}
  return false;
}

async function load(){
  const selectIds=['front','side','rear'];
  const cfg = await fetch('/api/cams/config').then(r=>r.json()).catch(()=>({}));
  let ok = await populateFromServer(selectIds);
  if(!ok){ try{ await navigator.mediaDevices.getUserMedia({video:true, audio:false}); }catch(e){}; ok = await populateFromBrowser(selectIds); }
  for(const id of selectIds){ const sel = document.getElementById(id); if(cfg[id]) sel.value = cfg[id]; sel.onchange = updatePreviews; }
  await updatePreviews();
  try{ const dump = await fetch('/api/cams/devices/obs').then(r=>r.json()); document.getElementById('obs_dump').textContent = JSON.stringify(dump, null, 2); }catch(e){ document.getElementById('obs_dump').textContent = '(unavailable)'; }
}

async function updatePreviews(){
  const map = {front:'f', side:'s', rear:'r'};
  const devices = await navigator.mediaDevices.enumerateDevices();
  const vids = devices.filter(d=>d.kind==='videoinput');
  for(const [k,p] of Object.entries(map)){
    const wanted = document.getElementById(k).value;
    const labelMatch = vids.find(v=>v.label===wanted) || vids[0];
    const id = labelMatch ? labelMatch.deviceId : undefined;
    try{
      const stream = await navigator.mediaDevices.getUserMedia({video: id?{deviceId:{exact:id}}:true, audio:false});
      const el = document.getElementById(p+'_v');
      if(el.srcObject){ try{ (el.srcObject.getTracks()||[]).forEach(t=>t.stop()); }catch(_){} }
      el.srcObject = stream;
      document.getElementById(p+'_info').textContent = labelMatch?(' '+(labelMatch.label||'')) : '';
    }catch(e){ console.warn('preview failed', e); }
  }
}

async function save(){
  stopAllPreviews();
  const body = new URLSearchParams();
  for(const id of ['front','side','rear']){
    const v = document.getElementById(id).value; if(v) body.append(id, v);
  }
  const res = await fetch('/api/cams/config', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body});
  const txt = await res.text();
  document.getElementById('status').textContent = res.ok ? 'Saved' : 'Error: '+txt;
  setTimeout(updatePreviews, 500);
}

document.getElementById('save').onclick = save;
document.getElementById('reload').onclick = load;
load();
</script>
</body></html>"""
    return HTMLResponse(content=html)
