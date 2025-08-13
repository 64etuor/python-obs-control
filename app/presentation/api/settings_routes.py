from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(prefix="/settings")


@router.get("/ui", response_class=HTMLResponse)
async def settings_ui() -> HTMLResponse:
    html = """<!doctype html><html><head><meta charset='utf-8'/>
<meta name='viewport' content='width=device-width,initial-scale=1'/>
<title>Settings</title>
<style>
:root{
  --bg:#0f1115; --bg-soft:#12151b; --panel:#161a22; --border:#252a36; --muted:#8b93a7; --fg:#e8ecf3;
  --accent:#3b82f6; --accent-2:#22c55e; --warn:#f59e0b; --danger:#ef4444; --radius:12px; --shadow:0 12px 36px rgba(0,0,0,.45);
}
html,body{height:100%}
body{margin:0; background: radial-gradient(1200px 800px at 10% -10%, #1b2030 0%, transparent 60%),
      radial-gradient(1200px 800px at 90% 110%, #1a1f2a 0%, transparent 60%), var(--bg); color:var(--fg);
      font: 14px/1.4 "Segoe UI", system-ui, -apple-system, Arial}
.container{max-width:1180px;margin:0 auto;padding:20px}

.toolbar{display:flex;gap:10px;align-items:center;justify-content:space-between;margin:12px 0 10px}
.title{font:700 22px/1.2 "Segoe UI",system-ui,-apple-system,Arial;letter-spacing:.2px}
.note{color:var(--muted);font-size:12px}
.status{min-height:18px}

.tabs{display:flex;gap:8px;margin:10px 0 16px}
.tab{appearance:none;border:1px solid var(--border);background:var(--bg-soft);color:var(--fg);border-radius:10px;padding:8px 12px;cursor:pointer}
.tab.active{background:var(--accent);border-color:var(--accent);color:#fff}

.section{margin:16px 0;padding:16px;border:1px solid var(--border);border-radius:var(--radius);
  background: linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,.01)), var(--panel); box-shadow: var(--shadow);}
.section h3{margin:0 0 10px;font:600 16px/1.2 "Segoe UI",system-ui; color:#fff}

.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.row-inline{display:flex;gap:8px;align-items:center}

label{display:block;margin:2px 0 6px;color:#cbd5e1;font-size:12px}
input,textarea{width:100%;box-sizing:border-box;color:var(--fg);background:var(--bg-soft);
  border:1px solid var(--border);border-radius:10px;padding:10px 12px;outline:none}
input:focus,textarea:focus{border-color:var(--accent); box-shadow:0 0 0 3px rgba(59,130,246,.15)}
textarea{min-height:120px;resize:vertical}

.btn{appearance:none;border:1px solid var(--border);background:var(--bg-soft);color:var(--fg);border-radius:10px;padding:8px 12px;cursor:pointer}
.btn:hover{border-color:#344155}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn.primary:hover{filter:brightness(1.05)}
.btn.ghost{background:transparent}
.btn.outline{background:transparent;border-color:#3f4758}
.btn.danger{border-color:var(--danger);color:#fff;background:linear-gradient(180deg, rgba(239,68,68,.95), rgba(239,68,68,.85))}
.btn.small{padding:6px 8px;font-size:12px;border-radius:8px}

.mask{position:fixed;inset:0;background:rgba(3,7,18,.7);backdrop-filter: blur(2px);display:none;align-items:center;justify-content:center;z-index:99999}
.mask .card{background:var(--panel);color:var(--fg);border:1px solid var(--border);border-radius:14px;min-width:320px;max-width:90vw;padding:18px 16px;box-shadow:var(--shadow);text-align:center}

.hidden{display:none}
</style></head><body>
<div class='container'>
  <div class='toolbar'>
    <div class='title'>Settings</div>
    <div class='actions'>
      <button id='btn_reload' class='btn ghost'>Reload</button>
      <button id='btn_reset' class='btn outline'>Reset</button>
      <button id='btn_save' class='btn primary'>Save</button>
    </div>
  </div>
  <div class='status note' id='status'></div>

  <div class='tabs'>
    <button id='tab_hotkeys' class='tab active'>Hotkeys</button>
    <button id='tab_cameras' class='tab'>Cameras</button>
    <button id='tab_ws' class='tab'>WebSocket</button>
  </div>

  <div id='view_hotkeys'>

    <div class='section'>
      <h3>Per-Scene Hotkeys</h3>
      <div id='scenes_grid' class='grid-3'></div>
    </div>

    <div class='section'>
      <h3>Procedure Before (Front / Side / Rear)</h3>
      <div class='grid-3'>
        <div><label>Front Key</label><div class='row-inline'><input id='pb_front_key' placeholder='F5'/><button type='button' class='btn small ghost' onclick="capture('pb_front_key')">Capture</button><button type='button' class='btn small ghost' onclick="clearVal('pb_front_key')">Clear</button></div></div>
        <div><label>Front Source</label><input id='pb_front_source' placeholder='cam_front'/></div>
        <div><label>Front Update</label><input id='pb_front_update' placeholder='img_before_front'/></div>
      </div>
      <div class='grid-2'>
        <div><label>Front Width</label><input id='pb_front_w' type='number' placeholder='1080'/></div>
        <div><label>Front Height</label><input id='pb_front_h' type='number' placeholder='1920'/></div>
      </div>
      <div class='grid-3'>
        <div><label>Side Key</label><div class='row-inline'><input id='pb_side_key' placeholder='F6'/><button type='button' class='btn small ghost' onclick="capture('pb_side_key')">Capture</button><button type='button' class='btn small ghost' onclick="clearVal('pb_side_key')">Clear</button></div></div>
        <div><label>Side Source</label><input id='pb_side_source' placeholder='cam_side'/></div>
        <div><label>Side Update</label><input id='pb_side_update' placeholder='img_before_side'/></div>
      </div>
      <div class='grid-2'>
        <div><label>Side Width</label><input id='pb_side_w' type='number' placeholder='1080'/></div>
        <div><label>Side Height</label><input id='pb_side_h' type='number' placeholder='1920'/></div>
      </div>
      <div class='grid-3'>
        <div><label>Rear Key</label><div class='row-inline'><input id='pb_rear_key' placeholder='F7'/><button type='button' class='btn small ghost' onclick="capture('pb_rear_key')">Capture</button><button type='button' class='btn small ghost' onclick="clearVal('pb_rear_key')">Clear</button></div></div>
        <div><label>Rear Source</label><input id='pb_rear_source' placeholder='cam_rear'/></div>
        <div><label>Rear Update</label><input id='pb_rear_update' placeholder='img_before_rear'/></div>
      </div>
      <div class='grid-2'>
        <div><label>Rear Width</label><input id='pb_rear_w' type='number' placeholder='1080'/></div>
        <div><label>Rear Height</label><input id='pb_rear_h' type='number' placeholder='1920'/></div>
      </div>
    </div>

    <div class='section'>
      <h3>Procedure After (Front / Side / Rear)</h3>
      <div class='grid-3'>
        <div><label>Front After Key</label><div class='row-inline'><input id='pa_front_key' placeholder='shift+F5'/><button type='button' class='btn small ghost' onclick="capture('pa_front_key')">Capture</button><button type='button' class='btn small ghost' onclick="clearVal('pa_front_key')">Clear</button></div></div>
        <div><label>Front After Source</label><input id='pa_front_source' placeholder='cam_front'/></div>
        <div><label>Front After Update</label><input id='pa_front_update' placeholder='img_after_front'/></div>
      </div>
      <div class='grid-2'>
        <div><label>Front After Width</label><input id='pa_front_w' type='number' placeholder='1080'/></div>
        <div><label>Front After Height</label><input id='pa_front_h' type='number' placeholder='1920'/></div>
      </div>
      <div class='grid-3'>
        <div><label>Side After Key</label><div class='row-inline'><input id='pa_side_key' placeholder='shift+F6'/><button type='button' class='btn small ghost' onclick="capture('pa_side_key')">Capture</button><button type='button' class='btn small ghost' onclick="clearVal('pa_side_key')">Clear</button></div></div>
        <div><label>Side After Source</label><input id='pa_side_source' placeholder='cam_side'/></div>
        <div><label>Side After Update</label><input id='pa_side_update' placeholder='img_after_side'/></div>
      </div>
      <div class='grid-2'>
        <div><label>Side After Width</label><input id='pa_side_w' type='number' placeholder='1080'/></div>
        <div><label>Side After Height</label><input id='pa_side_h' type='number' placeholder='1920'/></div>
      </div>
      <div class='grid-3'>
        <div><label>Rear After Key</label><div class='row-inline'><input id='pa_rear_key' placeholder='shift+F7'/><button type='button' class='btn small ghost' onclick="capture('pa_rear_key')">Capture</button><button type='button' class='btn small ghost' onclick="clearVal('pa_rear_key')">Clear</button></div></div>
        <div><label>Rear After Source</label><input id='pa_rear_source' placeholder='cam_rear'/></div>
        <div><label>Rear After Update</label><input id='pa_rear_update' placeholder='img_after_rear'/></div>
      </div>
      <div class='grid-2'>
        <div><label>Rear After Width</label><input id='pa_rear_w' type='number' placeholder='1080'/></div>
        <div><label>Rear After Height</label><input id='pa_rear_h' type='number' placeholder='1920'/></div>
      </div>
    </div>

    <div class='section'>
      <h3>Hair Style Reference</h3>
      <div class='grid-3'>
        <div><label>Hair Key</label><div class='row-inline'><input id='sc_hair_key' placeholder='F8'/><button type='button' class='btn small ghost' onclick="capture('sc_hair_key')">Capture</button><button type='button' class='btn small ghost' onclick="clearVal('sc_hair_key')">Clear</button></div></div>
        <div><label>Hair Source</label><input id='sc_hair_source' placeholder='window_capture'/></div>
        <div><label>Hair Update</label><input id='sc_hair_update' placeholder='img_hair_reference'/></div>
      </div>
      <div class='grid-2'>
        <div><label>Hair Width</label><input id='sc_hair_w' type='number' placeholder='1920'/></div>
        <div><label>Hair Height</label><input id='sc_hair_h' type='number' placeholder='1080'/></div>
      </div>
    </div>

    <div class='section'>
      <h3>Reset Images / Stream Toggle</h3>
      <div class='grid-3'>
        <div><label>Reset Key</label><div class='row-inline'><input id='reset_key' placeholder='ctrl+F8'/><button type='button' class='btn small ghost' onclick="capture('reset_key')">Capture</button><button type='button' class='btn small ghost' onclick="clearVal('reset_key')">Clear</button></div></div>
        <div><label>Reset Targets</label><input id='reset_targets' placeholder='comma separated...'/></div>
        <div><label>Confirm Window (sec)</label><input id='reset_win' type='number' placeholder='5'/></div>
      </div>
      <div class='grid-2'>
        <div><label>Stream Toggle Key</label><div class='row-inline'><input id='stream_toggle' placeholder='F9'/><button type='button' class='btn small ghost' onclick="capture('stream_toggle')">Capture</button><button type='button' class='btn small ghost' onclick="clearVal('stream_toggle')">Clear</button></div></div>
      </div>
    </div>
  </div>

  <div id='view_cameras' class='hidden'>
    <div class='section'>
      <h3>Camera Setup</h3>
      <div class='grid-3'>
        <div><label>Front</label><select id='front'></select></div>
        <div><label>Side</label><select id='side'></select></div>
        <div><label>Rear</label><select id='rear'></select></div>
      </div>
      <div class='row-inline' style='margin-top:10px'>
        <button id='cams_reload' class='btn ghost'>Reload Devices</button>
        <button id='cams_save' class='btn primary'>Apply</button>
        <span id='cams_status' class='note'></span>
      </div>
      <div class='note' id='detail_block' style='margin-top:10px'></div>
    </div>

    <div class='section'>
      <h3>Preview</h3>
      <div class='grid-3'>
        <div><div class='note'>Preview Front <span class='note' id='f_info'></span></div><video id='f_v' autoplay muted playsinline style='width:100%;background:#0b0e14;border-radius:10px;'></video></div>
        <div><div class='note'>Preview Side <span class='note' id='s_info'></span></div><video id='s_v' autoplay muted playsinline style='width:100%;background:#0b0e14;border-radius:10px;'></video></div>
        <div><div class='note'>Preview Rear <span class='note' id='r_info'></span></div><video id='r_v' autoplay muted playsinline style='width:100%;background:#0b0e14;border-radius:10px;'></video></div>
      </div>
    </div>

    <div class='section'>
      <h3>OBS DirectShow (debug)</h3>
      <pre id='obs_dump' class='note' style='background:var(--bg-soft);padding:10px;border-radius:10px;overflow:auto'>(loading...)</pre>
    </div>
  </div>

  <div id='view_ws' class='hidden'>
    <div class='section'>
      <h3>OBS WebSocket Settings</h3>
      <div class='grid-3'>
        <div><label>Host</label><input id='ws_host' placeholder='127.0.0.1'/></div>
        <div><label>Port</label><input id='ws_port' type='number' placeholder='4455'/></div>
        <div><label>Password</label><div class='row-inline'><input id='ws_password' type='password' placeholder='(empty allowed)'/><button type='button' id='ws_pwd_toggle' class='btn small ghost' title='Show/Hide' style='display:flex;align-items:center;gap:6px'><img id='ws_pwd_icon' alt='toggle' width='16' height='16' src='/assets/icons/eye.svg'/></button></div></div>
      </div>
      <div class='row-inline' style='margin-top:10px'>
        <button id='ws_reload' class='btn ghost'>Reload</button>
        <button id='ws_save' class='btn primary'>Save</button>
        <span id='ws_status' class='note'></span>
      </div>
    </div>
  </div>

</div>

<div id='capture_mask' class='mask'>
  <div class='card'>
    <div style='font-size:18px;margin-bottom:8px'>Press keys to bind</div>
    <div class='note' id='capture_hint'>Waiting for input...</div>
    <div style='margin-top:12px'><button id='cancel_capture' class='btn small outline'>Cancel</button></div>
  </div>
 </div>

<script>
function $(id){ return document.getElementById(id); }
function safe(v, d){ return (v===undefined||v===null)?d:v; }

// Tabs
function setTab(name){
  const hot=$('view_hotkeys'), cam=$('view_cameras'), ws=$('view_ws');
  const th=$('tab_hotkeys'), tc=$('tab_cameras'), tw=$('tab_ws');
  const isHot=name==='hotkeys', isCam=name==='cameras', isWs=name==='ws';
  hot.classList.toggle('hidden', !isHot);
  cam.classList.toggle('hidden', !isCam);
  ws.classList.toggle('hidden', !isWs);
  th.classList.toggle('active', isHot);
  tc.classList.toggle('active', isCam);
  tw.classList.toggle('active', isWs);
}
$('tab_hotkeys').onclick=()=>setTab('hotkeys');
$('tab_cameras').onclick=()=>setTab('cameras');
  $('tab_ws').onclick=()=>setTab('ws');

// ---------------- Hotkeys ----------------
async function loadHotkeys(){
  const res = await fetch('/api/hotkeys');
  const data = await res.json();
  const cfg = data.hotkeys || {};
  const sc = cfg.screenshot || {}; const pb = sc.procedure_before || {}; const pa = sc.procedure_after || {};
  const pbf = pb.front || {}; $('pb_front_key').value = safe(pbf.key,'F5'); $('pb_front_source').value = safe(pbf.source,'cam_front'); $('pb_front_update').value = safe(pbf.update_input,'img_before_front'); $('pb_front_w').value = safe(pbf.width,1080); $('pb_front_h').value = safe(pbf.height,1920);
  const pbs = pb.side || {}; $('pb_side_key').value = safe(pbs.key,'F6'); $('pb_side_source').value = safe(pbs.source,'cam_side'); $('pb_side_update').value = safe(pbs.update_input,'img_before_side'); $('pb_side_w').value = safe(pbs.width,1080); $('pb_side_h').value = safe(pbs.height,1920);
  const pbr = pb.rear || {}; $('pb_rear_key').value = safe(pbr.key,'F7'); $('pb_rear_source').value = safe(pbr.source,'cam_rear'); $('pb_rear_update').value = safe(pbr.update_input,'img_before_rear'); $('pb_rear_w').value = safe(pbr.width,1080); $('pb_rear_h').value = safe(pbr.height,1920);
  const paf = pa.front || {}; $('pa_front_key').value = safe(paf.key,'shift+F5'); $('pa_front_source').value = safe(paf.source,'cam_front'); $('pa_front_update').value = safe(paf.update_input,'img_after_front'); $('pa_front_w').value = safe(paf.width,1080); $('pa_front_h').value = safe(paf.height,1920);
  const pas = pa.side || {}; $('pa_side_key').value = safe(pas.key,'shift+F6'); $('pa_side_source').value = safe(pas.source,'cam_side'); $('pa_side_update').value = safe(pas.update_input,'img_after_side'); $('pa_side_w').value = safe(pas.width,1080); $('pa_side_h').value = safe(pas.height,1920);
  const par = pa.rear || {}; $('pa_rear_key').value = safe(par.key,'shift+F7'); $('pa_rear_source').value = safe(par.source,'cam_rear'); $('pa_rear_update').value = safe(par.update_input,'img_after_rear'); $('pa_rear_w').value = safe(par.width,1080); $('pa_rear_h').value = safe(par.height,1920);
  const h = sc.hair_reference || {}; $('sc_hair_key').value = safe(h.key,'F8'); $('sc_hair_source').value = safe(h.source,'window_capture'); $('sc_hair_update').value = safe(h.update_input,'img_hair_reference'); $('sc_hair_w').value = safe(h.width,1920); $('sc_hair_h').value = safe(h.height,1080);
  // scenes
  // dynamic per-scene grid
  try{
    const resp = await fetch('/api/hotkeys/scenes'); const j = await resp.json(); const scenes = j.scenes||[];
    const grid = $('scenes_grid'); grid.innerHTML='';
    for(const name of scenes){
      const id = 'scn_'+name.replace(/[^A-Za-z0-9_]/g,'_');
      const wrap = document.createElement('div');
      wrap.innerHTML = `<label>${name}</label><div class='row-inline'><input id='${id}' placeholder=''><button class='btn small ghost' onclick="capture('${id}')">Capture</button><button class='btn small ghost' onclick="clearVal('${id}')">Clear</button></div>`;
      grid.appendChild(wrap);
      const el = document.getElementById(id); el.value = safe((cfg.scene_hotkeys||{})[name], '');
    }
  }catch(e){}
}

function gatherHotkeys(){
  const out = {
    screenshot: {
      procedure_before: {
        front: { key: $('pb_front_key').value.trim(), source: $('pb_front_source').value.trim(), update_input: $('pb_front_update').value.trim(), width: +$('pb_front_w').value||1080, height: +$('pb_front_h').value||1920 },
        side: { key: $('pb_side_key').value.trim(), source: $('pb_side_source').value.trim(), update_input: $('pb_side_update').value.trim(), width: +$('pb_side_w').value||1080, height: +$('pb_side_h').value||1920 },
        rear: { key: $('pb_rear_key').value.trim(), source: $('pb_rear_source').value.trim(), update_input: $('pb_rear_update').value.trim(), width: +$('pb_rear_w').value||1080, height: +$('pb_rear_h').value||1920 }
      },
      procedure_after: {
        front: { key: $('pa_front_key').value.trim(), source: $('pa_front_source').value.trim(), update_input: $('pa_front_update').value.trim(), width: +$('pa_front_w').value||1080, height: +$('pa_front_h').value||1920 },
        side: { key: $('pa_side_key').value.trim(), source: $('pa_side_source').value.trim(), update_input: $('pa_side_update').value.trim(), width: +$('pa_side_w').value||1080, height: +$('pa_side_h').value||1920 },
        rear: { key: $('pa_rear_key').value.trim(), source: $('pa_rear_source').value.trim(), update_input: $('pa_rear_update').value.trim(), width: +$('pa_rear_w').value||1080, height: +$('pa_rear_h').value||1920 }
      },
      hair_reference: { key: $('sc_hair_key').value.trim(), source: $('sc_hair_source').value.trim(), update_input: $('sc_hair_update').value.trim(), width: +$('sc_hair_w').value||1920, height: +$('sc_hair_h').value||1080 }
    }
  };
  // scene hotkeys
  out.scene_hotkeys = {};
  const grid = document.getElementById('scenes_grid');
  for(const child of Array.from(grid.children)){
    const label = child.querySelector('label')?.textContent || '';
    const input = child.querySelector('input');
    if(label && input){ const v = (input.value||'').trim(); if(v) out.scene_hotkeys[label]=v; }
  }
  return out;
}

function detectDupKeys(hk){
  const keys=[];
  const pb = hk.screenshot.procedure_before, pa = hk.screenshot.procedure_after;
  keys.push(pb.front.key,pb.side.key,pb.rear.key, pa.front.key, pa.side.key, pa.rear.key, hk.screenshot.hair_reference.key);
  for(const v of Object.values(hk.scene_hotkeys||{})){ keys.push(String(v||'')); }
  const norm = k => String(k||'').trim().toLowerCase();
  const seen = new Map(); const dups=new Set();
  for(const k of keys){ const n=norm(k); if(!n) continue; if(seen.has(n)) dups.add(n); else seen.set(n,true); }
  return [...dups];
}

async function saveHotkeys(){
  const hk = gatherHotkeys();
  const dups = detectDupKeys(hk);
  if(dups.length){
    $('status').textContent = 'Duplicate hotkeys: '+dups.join(', ');
    $('status').style.color = '#fbbf24';
    return;
  }
  const res = await fetch('/api/hotkeys', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(hk)});
  $('status').textContent = res.ok ? 'Hotkeys saved' : ('Error: '+await res.text());
  $('status').style.color = res.ok ? '' : '#f87171';
}

// press-to-bind
let CAPTURE_TARGET=null; const MASK=$('capture_mask');
function capture(id){ CAPTURE_TARGET=id; MASK.style.display='flex'; }
function clearVal(id){ $(id).value=''; }
document.addEventListener('keydown', function(e){
  if(!CAPTURE_TARGET) return; e.preventDefault(); e.stopPropagation();
  const k=e.key;
  const isMod = (k==='Shift' || k==='Control' || k==='Alt' || k==='Meta');
  const parts=[];
  if(e.ctrlKey) parts.push('ctrl');
  if(e.altKey) parts.push('alt');
  if(e.shiftKey) parts.push('shift');
  if(e.metaKey) parts.push('meta');
  if(isMod){
    // Show preview but don't finalize on pure modifier
    $('capture_hint').textContent = 'Pressed: ' + (parts.join('+')||'(modifiers)');
    return;
  }
  const main = (/^F\d{1,2}$/.test(k) ? k : (k.length===1? k.toUpperCase() : k.toUpperCase()));
  parts.push(main);
  $(CAPTURE_TARGET).value = parts.join('+');
  CAPTURE_TARGET=null; MASK.style.display='none';
}, true);
$('cancel_capture').onclick = ()=>{ CAPTURE_TARGET=null; MASK.style.display='none'; };

// ---------------- Cameras ----------------
function fillSelect(id, devices){
  const sel=$(id); sel.innerHTML=''; const none=document.createElement('option'); none.value=''; none.textContent='(none)'; sel.appendChild(none);
  const seen=new Set(); for(const d of devices||[]){ if(!d || seen.has(d)) continue; seen.add(d); const o=document.createElement('option'); o.value=d; o.textContent=d; sel.appendChild(o); }
}
function fillSelectPairs(id, pairs){
  const sel=$(id); sel.innerHTML=''; const none=document.createElement('option'); none.value=''; none.textContent='(none)'; sel.appendChild(none);
  const seen=new Set(); for(const p of pairs||[]){ const v=p?.value ?? p?.path ?? p?.id ?? ''; const t=p?.label ?? p?.name ?? String(v||''); if(!v || seen.has(v)) continue; seen.add(v); const o=document.createElement('option'); o.value=String(v); o.textContent=String(t); sel.appendChild(o); }
}
async function loadCameras(){
  const cfg = await fetch('/api/cams/config').then(r=>r.json()).catch(()=>({}));
  // Try server detailed list
  let ok=false;
  try{
    const dev = await fetch('/api/cams/devices').then(r=>r.json());
    if(dev && dev.detail && Array.isArray(dev.detail.devices) && dev.detail.devices.length){
      const pairs = dev.detail.devices.map(d=>({label: d.name, value: d.path || d.value || d.name}));
      fillSelectPairs('front', pairs); fillSelectPairs('side', pairs); fillSelectPairs('rear', pairs);
      const detail = dev.detail.devices.map(d=>`<div><code>${d.name}</code> — <code>${d.path}</code></div>`).join('');
      $('detail_block').innerHTML = detail || '(no detail)'; ok=true;
    }
  }catch(e){}
  if(!ok){
    try{
      const obs = await fetch('/api/cams/devices/obs').then(r=>r.json());
      const items = Array.isArray(obs?.obs)? obs.obs: [];
      if(items.length){ fillSelectPairs('front', items); fillSelectPairs('side', items); fillSelectPairs('rear', items); ok=true; }
    }catch(e){}
  }
  if(!ok){
    try{ await navigator.mediaDevices.getUserMedia({video:true, audio:false}); }catch(e){}
    try{
      const devs = await navigator.mediaDevices.enumerateDevices(); const vids = devs.filter(d=>d.kind==='videoinput'); const labels = vids.map(v=>v.label).filter(Boolean);
      if(labels.length){ fillSelect('front', labels); fillSelect('side', labels); fillSelect('rear', labels); }
    }catch(e){}
  }
  // set selected
  try{ if(cfg.front) $('front').value = cfg.front; if(cfg.side) $('side').value = cfg.side; if(cfg.rear) $('rear').value = cfg.rear; }catch(e){}
  // previews
  updatePreviews();
  try{ const dump = await fetch('/api/cams/devices/obs').then(r=>r.json()); $('obs_dump').textContent = JSON.stringify(dump, null, 2); }catch(e){ $('obs_dump').textContent='(unavailable)'; }
}

function stopAllPreviews(){ for(const id of ['f_v','s_v','r_v']){ const el=$(id); try{ (el.srcObject?.getTracks?.()||[]).forEach(t=>t.stop()); el.srcObject=null; }catch(_){} } }
async function updatePreviews(){
  const map={front:'f', side:'s', rear:'r'}; const devices = await navigator.mediaDevices.enumerateDevices(); const vids = devices.filter(d=>d.kind==='videoinput');
  for(const [k,p] of Object.entries(map)){
    const wanted = $(k).value; const labelMatch = vids.find(v=>v.label===wanted) || vids[0]; const id = labelMatch ? labelMatch.deviceId : undefined;
    try{ const stream = await navigator.mediaDevices.getUserMedia({video: id?{deviceId:{exact:id}}:true, audio:false}); const el=$(p+'_v'); if(el.srcObject){ try{ (el.srcObject.getTracks()||[]).forEach(t=>t.stop()); }catch(_){} } el.srcObject=stream; $(p+'_info').textContent = labelMatch?(' '+(labelMatch.label||'')) : ''; }catch(e){}
  }
}

$('cams_reload').onclick = loadCameras;
$('cams_save').onclick = async function(){
  stopAllPreviews();
  const body = new URLSearchParams(); for(const id of ['front','side','rear']){ const v=$(id).value; if(v) body.append(id, v); }
  const res = await fetch('/api/cams/config', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body});
  $('cams_status').textContent = res.ok? 'Saved' : ('Error: '+await res.text());
  setTimeout(updatePreviews, 500);
};

// global toolbar actions
$('btn_reload').onclick = ()=>{ const t = document.querySelector('.tab.active')?.id || 'tab_hotkeys'; if(t==='tab_hotkeys') loadHotkeys(); else loadCameras(); };
  $('btn_reset').onclick = async ()=>{ const res = await fetch('/api/hotkeys', {method:'POST', headers:{'Content-Type':'application/json'}, body: '{}'}); $('status').textContent = res.ok? 'Hotkeys reset' : ('Error: '+await res.text()); if(res.ok) loadHotkeys(); };
  $('btn_save').onclick = async ()=>{ const id=document.querySelector('.tab.active')?.id; if(id==='tab_hotkeys'){ await saveHotkeys(); } else if(id==='tab_cameras'){ $('cams_save').click(); } else if(id==='tab_ws'){ $('ws_save').click(); } };
  // ---------------- WebSocket ----------------
  async function loadWS(){
    try{
      const res = await fetch('/api/ws/config'); const j = await res.json();
      $('ws_host').value = j.host || '127.0.0.1';
      $('ws_port').value = j.port || 4455;
      $('ws_password').value = j.password || '';
      $('ws_status').textContent = '';
    }catch(e){ $('ws_status').textContent = 'Load failed'; }
  }
  async function saveWS(){
    const body = {host: $('ws_host').value.trim(), port: +$('ws_port').value||4455, password: $('ws_password').value};
    const res = await fetch('/api/ws/config', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    $('ws_status').textContent = res.ok? 'Saved' : ('Error: '+await res.text());
    if(res.ok){ try{ await fetch('/api/ws/reconnect', {method:'POST'}); }catch(e){} }
  }
  $('ws_reload').onclick = loadWS;
  $('ws_save').onclick = saveWS;
  // show/hide password
  (function(){ const i=$('ws_password'), b=$('ws_pwd_toggle'), ic=$('ws_pwd_icon'); if(b&&i&&ic){ b.onclick=()=>{ const isPass=i.getAttribute('type')==='password'; i.setAttribute('type', isPass?'text':'password'); ic.src = isPass?'/assets/icons/eye-off.svg':'/assets/icons/eye.svg'; }; } })();

// init
setTab('hotkeys');
loadHotkeys();
  loadCameras();
  loadWS();
</script>
</body></html>"""
    return HTMLResponse(content=html)


