import json

data = json.load(open('viz_data.json'))
DATA = json.dumps(data, separators=(',', ':'))

HTML = r'''<title>Superswim: ESS pumps vs reboosts (200k)</title>
<meta name="description" content="Frame-timeline A/B of two Wind Waker superswim plans to 200,000 units — where reboosts and ESS pumps fire, and why pumps save 6 frames.">
<style>
  :root{
    --sea:#0b151b; --sea2:#0e1d25; --panel:#11222c; --panel2:#0d1a22;
    --line:#1d3540; --line2:#27444f;
    --ink:#eaf3f4; --mut:#8aa3ac; --mut2:#5f7a84;
    --build:#5e7079; --ess:#2fc6a4; --reboost:#ff9d3c; --pump:#ffd23f;
    --dash:#a07add; --speed:#79e6ff;
    --mono:"Cascadia Code","Cascadia Mono",Consolas,"SFMono-Regular",ui-monospace,monospace;
    --sans:"Segoe UI",system-ui,-apple-system,Roboto,sans-serif;
  }
  *{box-sizing:border-box}
  body{margin:0}
  .wrap{
    max-width:1180px;margin:0 auto;padding:40px 28px 64px;
    background:
      radial-gradient(1200px 460px at 78% -8%, #123140 0%, rgba(18,49,64,0) 60%),
      linear-gradient(180deg,#0b151b 0%, #0a1318 100%);
    min-height:100%;
    color:var(--ink);font-family:var(--sans);
    font-size:15px;line-height:1.6;
  }
  .eyebrow{
    font-family:var(--mono);font-size:11.5px;letter-spacing:.28em;text-transform:uppercase;
    color:var(--ess);margin:0 0 14px;
  }
  h1{
    font-family:var(--mono);font-weight:700;font-size:clamp(26px,4.4vw,42px);
    line-height:1.08;letter-spacing:-.01em;margin:0;text-wrap:balance;color:var(--ink);
  }
  h1 .x{color:var(--mut2);font-weight:400}
  .lede{max-width:62ch;color:var(--mut);margin:16px 0 0;font-size:16px}
  .lede b{color:var(--ink);font-weight:600}

  .stats{display:flex;flex-wrap:wrap;gap:14px;margin:30px 0 8px}
  .stat{
    flex:1 1 180px;background:linear-gradient(180deg,var(--panel),var(--panel2));
    border:1px solid var(--line);border-radius:11px;padding:16px 18px;position:relative;overflow:hidden;
  }
  .stat .k{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut2);margin:0 0 8px}
  .stat .v{font-family:var(--mono);font-size:30px;font-weight:700;line-height:1;font-variant-numeric:tabular-nums}
  .stat .u{font-family:var(--mono);font-size:13px;color:var(--mut);font-weight:400}
  .stat .sub{font-size:12.5px;color:var(--mut);margin-top:9px}
  .stat.delta{border-color:#3a5e3f}
  .stat.delta .v{color:#7ee08a}
  .stat .rail{position:absolute;left:0;top:0;bottom:0;width:3px}
  .stat.base .rail{background:var(--mut2)} .stat.pump .rail{background:var(--pump)} .stat.delta .rail{background:#7ee08a}

  .chart{
    margin-top:26px;background:linear-gradient(180deg,#0d1a22,#0b161d);
    border:1px solid var(--line);border-radius:14px;padding:18px 18px 10px;
  }
  .chart-head{display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap;margin-bottom:6px}
  .chart-head h2{font-family:var(--mono);font-size:13px;font-weight:600;letter-spacing:.04em;margin:0;color:var(--mut)}
  .readout{
    font-family:var(--mono);font-size:12.5px;color:var(--mut);font-variant-numeric:tabular-nums;
    min-height:18px;white-space:nowrap
  }
  .readout b{color:var(--speed);font-weight:600}
  .readout .rb{color:var(--reboost)} .readout .pu{color:var(--pump)}
  .svgbox{position:relative;width:100%;overflow-x:auto}
  svg{display:block;width:100%;height:auto;touch-action:none}
  text{font-family:var(--mono)}

  .legend{display:flex;flex-wrap:wrap;gap:7px 20px;margin:16px 2px 2px;font-family:var(--mono);font-size:12px;color:var(--mut)}
  .lg{display:inline-flex;align-items:center;gap:8px}
  .sw{width:13px;height:13px;border-radius:3px;flex:none}
  .sw.line{height:3px;border-radius:2px;width:18px}
  .sw.tri{width:0;height:0;border-radius:0;border-left:7px solid transparent;border-right:7px solid transparent;border-top:10px solid var(--reboost)}
  .sw.tick{width:3px;height:14px;border-radius:1px;background:var(--pump)}

  .notes{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:26px}
  @media(max-width:680px){.notes{grid-template-columns:1fr}}
  .note{background:var(--panel2);border:1px solid var(--line);border-radius:11px;padding:16px 18px}
  .note h3{font-family:var(--mono);font-size:12px;letter-spacing:.1em;text-transform:uppercase;margin:0 0 9px}
  .note.rb h3{color:var(--reboost)} .note.pu h3{color:var(--pump)}
  .note p{margin:0;color:var(--mut);font-size:13.5px}
  .note p b{color:var(--ink);font-weight:600}
  .foot{margin-top:26px;color:var(--mut2);font-family:var(--mono);font-size:11.5px;line-height:1.7}
  .foot b{color:var(--mut)}
</style>

<div class="wrap">
  <p class="eyebrow">Wind Waker · Superswim TAS · slot-10 cold start</p>
  <h1>ESS pumps <span class="x">vs.</span> stroboscopic reboosts</h1>
  <p class="lede">Two minimum-frame plans to swim <b>200,000 units</b>, both replayed live on the
  emulator. They share an identical charge build and both cruise in strobo <b>band&nbsp;1 (v&nbsp;≈&nbsp;−790)</b>.
  The only difference is how each <em>maintains</em> the cruise: the baseline fires a few
  <b style="color:var(--reboost)">up-down reboosts</b>; the pump plan replaces them with many cheap
  <b style="color:var(--pump)">ESS pumps</b> — and reaches the target <b>6 frames sooner</b>.</p>

  <div class="stats">
    <div class="stat base"><span class="rail"></span>
      <p class="k">No-pump baseline</p>
      <div class="v">561<span class="u"> fr</span></div>
      <p class="sub">5 reboosts · live net 200,583</p>
    </div>
    <div class="stat pump"><span class="rail"></span>
      <p class="k">Pump plan (live-synced)</p>
      <div class="v">555<span class="u"> fr</span></div>
      <p class="sub">34 pumps · live net 200,128</p>
    </div>
    <div class="stat delta"><span class="rail"></span>
      <p class="k">Pumps save</p>
      <div class="v">−6<span class="u"> fr</span></div>
      <p class="sub">bit-exact end-state, first candidate synced</p>
    </div>
  </div>

  <div class="chart">
    <div class="chart-head">
      <h2>FRAME TIMELINE — speed |v| with technique markers</h2>
      <div class="readout" id="readout">hover the timeline to inspect any frame</div>
    </div>
    <div class="svgbox" id="svgbox"></div>
  </div>

  <div class="legend">
    <span class="lg"><span class="sw" style="background:var(--build)"></span>charge build</span>
    <span class="lg"><span class="sw" style="background:var(--ess)"></span>ESS cruise (band 1)</span>
    <span class="lg"><span class="sw" style="background:var(--dash)"></span>neutral dash</span>
    <span class="lg"><span class="sw line" style="background:var(--speed)"></span>speed |v|</span>
    <span class="lg"><span class="sw tri"></span>reboost (up-down charge)</span>
    <span class="lg"><span class="sw tick"></span>ESS pump (neutral→ESS)</span>
  </div>

  <div class="notes">
    <div class="note rb">
      <h3>Reboost — the baseline's tool</h3>
      <p>A <b>minimal up-down charge</b> (2 frames) fired when the head-bob animation drifts off
      the |cos|=1 peak. It nudges potential speed up so the strobo phase climbs back to the peak,
      keeping ESS true-speed near 100%. The baseline does this <b>5 times</b>, ~49 frames apart.</p>
    </div>
    <div class="note pu">
      <h3>ESS pump — the pump plan's tool</h3>
      <p>From neutral, tap back into <b>ESS for a frame or two</b> on a good animation phase: you keep
      speed at the cheap −1/6 decay instead of neutral's −2, while air is high enough that true speed
      ≈ full |v|. Many small pumps let the plan cruise longer and finish with a <b>shorter neutral dash</b>.</p>
    </div>
  </div>

  <p class="foot">
    <b>Method.</b> Both plans generated by the unified-DP planner (superswim_plan.py) from the live
    cold start (loadstate 10, air 900, v 0, no air-refill), then replayed via one race-free
    advanceseq each. The single A*-best pump plan dies live (chaotic pump-transition timing); the
    plan shown is the first equal-frame candidate that <b>synced bit-exact</b> via the multi-solution
    live filter (validate_plans.py). Speed curve is the bit-exact sim (v matches live across all pumps).
  </p>
</div>

<script>
const DATA = __DATA__;
const C = {build:'#5e7079',ess:'#2fc6a4',reboost:'#ff9d3c',pump:'#ffd23f',dash:'#a07add',speed:'#79e6ff'};
const order = ['nopump','pump'];
const MAXF = Math.max(...order.map(k=>DATA[k].frames));   // shared frame scale
const VMAX = 840;

// geometry
const W=1140, PADL=92, PADR=22, TOP=20, TRK=128, GAP=40, AXIS=30;
const PLOTW = W-PADL-PADR;
const H = TOP + TRK*2 + GAP + AXIS;
const fx = f => PADL + (f/MAXF)*PLOTW;
const trackTop = i => TOP + i*(TRK+GAP);
const vy = (top,v) => top + TRK - 14 - (Math.min(v,VMAX)/VMAX)*(TRK-26);

const esc = s => s;
let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Frame timeline comparison of two superswim plans">`;

// defs: faint grid + area gradients
svg += `<defs>`;
order.forEach((k,i)=>{ svg += `<linearGradient id="sp${i}" x1="0" x2="0" y1="0" y2="1">
  <stop offset="0" stop-color="${C.speed}" stop-opacity="0.30"/>
  <stop offset="1" stop-color="${C.speed}" stop-opacity="0.02"/></linearGradient>`; });
svg += `</defs>`;

function region(top,a,b,color,op){ return `<rect x="${fx(a).toFixed(1)}" y="${top}" width="${(fx(b)-fx(a)).toFixed(1)}" height="${TRK}" fill="${color}" fill-opacity="${op}"/>`; }

order.forEach((k,i)=>{
  const d=DATA[k], top=trackTop(i);
  // frame for track box
  svg += `<rect x="${PADL}" y="${top}" width="${PLOTW}" height="${TRK}" fill="#0a141a" stroke="${'#1d3540'}" rx="6"/>`;
  // macro-phase background bands
  svg += region(top,0,d.build_end,C.build,0.22);
  svg += region(top,d.build_end,d.dash_start,C.ess,0.13);
  svg += region(top,d.dash_start,d.frames,C.dash,0.22);
  // speed gridlines (v=400,800)
  [200,400,600,800].forEach(g=>{ const y=vy(top,g);
    svg += `<line x1="${PADL}" y1="${y.toFixed(1)}" x2="${PADL+PLOTW}" y2="${y.toFixed(1)}" stroke="#162a33" stroke-width="1"/>`;
    if(i===0) svg += `<text x="${PADL-8}" y="${(y+3).toFixed(1)}" fill="#456069" font-size="9.5" text-anchor="end">${g}</text>`;
  });
  // phase labels inside bands
  const lbl=(a,b,t,col)=>{ const cx=(fx(a)+fx(b))/2; if(fx(b)-fx(a)<46)return'';
    return `<text x="${cx.toFixed(1)}" y="${top+15}" fill="${col}" font-size="9.5" letter-spacing="1.5" text-anchor="middle" opacity="0.85">${t}</text>`; };
  svg += lbl(0,d.build_end,'BUILD','#9fb0b8');
  svg += lbl(d.build_end,d.dash_start,'ESS CRUISE',C.ess);
  svg += lbl(d.dash_start,d.frames,'DASH',C.dash);

  // speed area + line
  let area=`M ${fx(0).toFixed(1)} ${(top+TRK).toFixed(1)} `;
  let ln='';
  d.v.forEach((v,f)=>{ const x=fx(f).toFixed(1), y=vy(top,Math.abs(v)).toFixed(1);
    area+=`L ${x} ${y} `; ln+=(f?'L':'M')+x+' '+y+' '; });
  area+=`L ${fx(d.frames-1).toFixed(1)} ${(top+TRK).toFixed(1)} Z`;
  svg += `<path d="${area}" fill="url(#sp${i})"/>`;
  svg += `<path d="${ln}" fill="none" stroke="${C.speed}" stroke-width="1.6" stroke-linejoin="round"/>`;

  // pump markers (gold ticks rising from baseline)
  (d.pumps||[]).forEach(([s,l])=>{ const x=fx(s+ (l-1)/2).toFixed(1); const yb=top+TRK-2;
    svg += `<line x1="${x}" y1="${yb}" x2="${x}" y2="${(yb-26).toFixed(1)}" stroke="${C.pump}" stroke-width="2"/>`;
    svg += `<circle cx="${x}" cy="${(yb-28).toFixed(1)}" r="2.6" fill="${C.pump}"/>`;
  });
  // reboost markers (amber pennants above track top)
  (d.reboosts||[]).forEach(([s,l])=>{ const x=fx(s+(l-1)/2); const yt=top-2;
    svg += `<path d="M ${(x-6).toFixed(1)} ${(yt-12).toFixed(1)} L ${(x+6).toFixed(1)} ${(yt-12).toFixed(1)} L ${x.toFixed(1)} ${yt.toFixed(1)} Z" fill="${C.reboost}"/>`;
  });

  // track label
  svg += `<text x="${PADL}" y="${top-7}" fill="${i? C.pump : '#aebcc3'}" font-size="12" font-weight="700">${d.label}</text>`;
  svg += `<text x="${PADL+PLOTW}" y="${top-7}" fill="#6f8891" font-size="11" text-anchor="end">${d.frames} frames · live net ${d.live_net.toLocaleString()}</text>`;
});

// shared frame axis
const ay = TOP+TRK*2+GAP+6;
svg += `<line x1="${PADL}" y1="${ay}" x2="${PADL+PLOTW}" y2="${ay}" stroke="#27444f"/>`;
for(let f=0; f<=MAXF; f+=50){ const x=fx(f).toFixed(1);
  svg += `<line x1="${x}" y1="${ay}" x2="${x}" y2="${ay+5}" stroke="#27444f"/>`;
  svg += `<text x="${x}" y="${ay+18}" fill="#6f8891" font-size="10" text-anchor="middle">${f}</text>`;
}
svg += `<text x="${PADL+PLOTW}" y="${ay+18}" fill="#6f8891" font-size="10" text-anchor="end">frame →</text>`;

// hover crosshair (one per track) + scrubber line
svg += `<g id="hover" style="opacity:0">
  <line id="hx" x1="0" y1="${TOP}" x2="0" y2="${TOP+TRK*2+GAP}" stroke="#79e6ff" stroke-opacity="0.5" stroke-width="1" stroke-dasharray="3 3"/>
  <circle id="hd0" r="3.2" fill="#79e6ff"/><circle id="hd1" r="3.2" fill="#79e6ff"/></g>`;
svg += `</svg>`;

const box=document.getElementById('svgbox');
box.innerHTML = svg;
const svgEl=box.querySelector('svg');
const hover=document.getElementById('hover');
const hx=document.getElementById('hx'), hd0=document.getElementById('hd0'), hd1=document.getElementById('hd1');
const readout=document.getElementById('readout');
const ACT={chg:'charge',ess:'ESS',neu:'neutral'};

function phaseTag(k,f){const p=DATA[k].phase[f];
  if(p==='reboost')return '<span class="rb">REBOOST</span>';
  if(p==='pump')return '<span class="pu">PUMP</span>';
  return p.toUpperCase();}

function move(ev){
  const r=svgEl.getBoundingClientRect();
  const sx=(ev.clientX-r.left)/r.width*W;
  let f=Math.round((sx-PADL)/PLOTW*MAXF);
  f=Math.max(0,Math.min(MAXF,f));
  const x=fx(f);
  hover.style.opacity=1; hx.setAttribute('x1',x); hx.setAttribute('x2',x);
  order.forEach((k,i)=>{ const d=DATA[k]; const ff=Math.min(f,d.frames-1);
    const y=vy(trackTop(i),Math.abs(d.v[ff]));
    const dd=i?hd1:hd0; dd.setAttribute('cx',x); dd.setAttribute('cy',y);
    dd.style.opacity = f<d.frames?1:0.2;
  });
  const parts=order.map((k,i)=>{const d=DATA[k];const ff=Math.min(f,d.frames-1);
    const a=f<d.frames?ACT[d.acts[ff]]:'—';
    return `${i?'pump':'base'} <b>|v| ${Math.abs(d.v[ff]).toFixed(0)}</b> · ${a} · ${phaseTag(k,ff)}`;});
  readout.innerHTML=`<b>f${f}</b>   —   ${parts.join('     ')}`;
}
svgEl.addEventListener('mousemove',move);
svgEl.addEventListener('touchmove',e=>{if(e.touches[0])move(e.touches[0]);},{passive:true});
svgEl.addEventListener('mouseleave',()=>{hover.style.opacity=0;readout.textContent='hover the timeline to inspect any frame';});
</script>'''

out = HTML.replace('__DATA__', DATA)
open('superswim_ab.html', 'w', encoding='utf-8').write(out)
print('wrote superswim_ab.html', len(out), 'bytes')
