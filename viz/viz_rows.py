"""Row-layout (small-multiples) animated viewer: each swim in its OWN horizontal strip,
stacked vertically and sharing one timeline. Progress (=-x, west) maps left->right on a
common scale so the swims are directly comparable; the cross-axis (z) is amplified within
each strip. A shared play/scrub drives all rows; each row shows live v/air and the frame it
finishes. Standalone -- does not touch superswim_sim.emit_viz (the overlay viewer).

build_rows(path_html, traces, dest) where traces = [{name,color,rows}], rows have x/z/v/air/tag.
"""
import json


def build_rows(path_html, traces, dest):
    payload = json.dumps([{"name": t["name"], "color": t["color"],
                           "rows": [{"x": r["x"], "z": r["z"], "v": r["v"],
                                     "air": r["air"], "tag": r["tag"]} for r in t["rows"]]}
                          for t in traces])
    html = _TMPL.replace("__DATA__", payload).replace("__DEST__", str(float(dest)))
    with open(path_html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {path_html}")


_TMPL = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>superswim rows</title>
<style>
 body{margin:0;background:#0d1117;color:#c9d1d9;font:13px system-ui,sans-serif}
 #wrap{display:flex;flex-direction:column;height:100vh}
 #rows{flex:1;overflow:auto;padding:6px 10px}
 .swim{margin:8px 0;border:1px solid #21262d;border-radius:8px;background:#11161d}
 .hd{display:flex;justify-content:space-between;align-items:baseline;padding:5px 10px 0}
 .nm{font-weight:600}
 .st{font-variant-numeric:tabular-nums;color:#8b949e}
 canvas{display:block;width:100%;height:84px}
 #hud{padding:8px 12px;background:#161b22;border-top:1px solid #30363d}
 .ctl{display:flex;gap:14px;align-items:center}
 button{background:#21262d;color:#c9d1d9;border:1px solid #30363d;border-radius:6px;padding:4px 10px;cursor:pointer}
 input[type=range]{flex:1;vertical-align:middle}
 .legend{margin-top:6px;color:#8b949e}
 .leg{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 4px -1px 10px}
</style></head>
<body><div id="wrap">
 <div id="rows"></div>
 <div id="hud">
   <div class="ctl">
     <button id="play">⏸ pause</button>
     <input id="scrub" type="range" min="0" max="100" value="0">
     <span id="fnum" class="st">f 0</span>
     <label>speed <select id="rate"><option>0.5</option><option selected>1</option><option>2</option><option>4</option></select>×</label>
   </div>
   <div class="legend"><span class="leg" style="background:#f0883e"></span>charge frame
     &nbsp;&nbsp;<span class="leg" style="background:#3fb950"></span>neutral dash
     &nbsp;&nbsp;dashed line = target (__DEST__ units)</div>
 </div>
</div>
<script>
const DATA = __DATA__, DEST = __DEST__;
const N = Math.max(...DATA.map(t=>t.rows.length));
// common progress scale across all swims (progress = -x, west = forward)
let maxP=0; for(const t of DATA) for(const r of t.rows) maxP=Math.max(maxP,-r.x);
maxP=Math.max(maxP,DEST);
// per-row z range (amplified within the strip)
const zr=DATA.map(t=>{let lo=1e18,hi=-1e18;for(const r of t.rows){lo=Math.min(lo,r.z);hi=Math.max(hi,r.z);}return [lo,hi];});

const rowsDiv=document.getElementById('rows');
const cv=[], hdEl=[];
DATA.forEach((t,i)=>{
  const d=document.createElement('div');d.className='swim';
  d.innerHTML=`<div class="hd"><span class="nm" style="color:${t.color}">${t.name}</span>`+
              `<span class="st" id="st${i}"></span></div><canvas id="cv${i}"></canvas>`;
  rowsDiv.appendChild(d);
  cv.push(document.getElementById('cv'+i)); hdEl.push(document.getElementById('st'+i));
});
function resize(){cv.forEach(c=>{c.width=c.clientWidth*devicePixelRatio;c.height=c.clientHeight*devicePixelRatio;});}
window.addEventListener('resize',resize);resize();

let frame=0,playing=true,t0=null;
function drawRow(i){
  const c=cv[i],ctx=c.getContext('2d'),t=DATA[i],rows=t.rows;
  const W=c.width,H=c.height,m=10*devicePixelRatio;
  ctx.clearRect(0,0,W,H);
  const [zlo,zhi]=zr[i], zsp=(zhi-zlo)||1;
  const X=p=>m+(p/maxP)*(W-2*m);
  const Y=z=>H/2 - ((z-(zlo+zhi)/2)/zsp)*(H*0.7);
  // target line
  ctx.strokeStyle='#30363d';ctx.lineWidth=1.5*devicePixelRatio;ctx.setLineDash([5,4]);
  ctx.beginPath();ctx.moveTo(X(DEST),0);ctx.lineTo(X(DEST),H);ctx.stroke();ctx.setLineDash([]);
  // baseline
  ctx.strokeStyle='#1b2129';ctx.beginPath();ctx.moveTo(m,H/2);ctx.lineTo(W-m,H/2);ctx.stroke();
  const upto=Math.min(frame,rows.length-1);
  // trail
  ctx.lineWidth=2.2*devicePixelRatio;ctx.strokeStyle=t.color;ctx.globalAlpha=.85;ctx.beginPath();
  for(let k=0;k<=upto;k++){const px=X(-rows[k].x),py=Y(rows[k].z);k?ctx.lineTo(px,py):ctx.moveTo(px,py);}
  ctx.stroke();ctx.globalAlpha=1;
  // charge + neutral markers
  for(let k=0;k<=upto;k++){const tg=rows[k].tag;
    if(tg==='CHG'||tg==='chg'){ctx.fillStyle='#f0883e';ctx.beginPath();ctx.arc(X(-rows[k].x),Y(rows[k].z),2*devicePixelRatio,0,7);ctx.fill();}
    else if(tg==='neu'||tg==='NEU'){ctx.fillStyle='#3fb950';ctx.fillRect(X(-rows[k].x),H/2-1*devicePixelRatio,1.4*devicePixelRatio,2*devicePixelRatio);}}
  // head
  const hx=X(-rows[upto].x),hy=Y(rows[upto].z);
  ctx.fillStyle=t.color;ctx.beginPath();ctx.arc(hx,hy,5.5*devicePixelRatio,0,7);ctx.fill();
  ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(hx,hy,2*devicePixelRatio,0,7);ctx.fill();
  // stats
  const r=rows[upto];
  const done=frame>=rows.length-1;
  const reachF=rows.findIndex(rr=>-rr.x>=DEST);
  hdEl[i].innerHTML=`prog ${(-r.x).toFixed(0)} &nbsp; v ${r.v.toFixed(0)} &nbsp; air ${r.air}`+
    (reachF>=0?` &nbsp; <b style="color:${t.color}">✓ ${reachF+1} fr</b>`:` &nbsp; ${rows.length} fr`);
}
function draw(){for(let i=0;i<DATA.length;i++)drawRow(i);
  document.getElementById('fnum').textContent='f '+frame;
  document.getElementById('scrub').value=(frame/(N-1)*100)||0;}
function tick(ts){if(t0===null)t0=ts;
  if(playing){const rate=parseFloat(document.getElementById('rate').value);
    frame=Math.min(N-1,Math.floor((ts-t0)/1000*30*rate));
    if(frame>=N-1){playing=false;document.getElementById('play').textContent='↻ replay';}}
  draw();requestAnimationFrame(tick);}
document.getElementById('play').onclick=()=>{if(frame>=N-1){frame=0;t0=null;}
  playing=!playing;document.getElementById('play').textContent=playing?'⏸ pause':'▶ play';if(playing)t0=null;};
document.getElementById('scrub').oninput=e=>{playing=false;frame=Math.round(e.target.value/100*(N-1));
  document.getElementById('play').textContent='▶ play';draw();};
requestAnimationFrame(tick);
</script></body></html>"""
