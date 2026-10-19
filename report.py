"""Informe HTML del backtest: indicadores, curva de capital, drawdown y operaciones.

Se genera desde backtest.py con --html informe.html. Es un único archivo que funciona
sin internet: ábrelo con doble clic en el navegador.
"""
import html
import json

from strategy import describe

MAX_POINTS = 800   # se reduce la curva a ~800 puntos para que el archivo sea ligero


def _downsample(series):
    step = max(1, len(series) // MAX_POINTS)
    s = series.iloc[::step]
    if s.index[-1] != series.index[-1]:
        s = series.iloc[list(range(0, len(series), step)) + [len(series) - 1]]
    return s


def write_html(r: dict, path: str):
    cfg = r["cfg"]
    eq = _downsample(r["equity"])
    bh = r["buy_hold"].loc[eq.index]
    dd = (r["equity"] / r["equity"].cummax() - 1).loc[eq.index]
    data = {
        "t": [f"{t:%Y-%m-%d %H:%M}" for t in eq.index],
        "eq": [round(v, 2) for v in eq],
        "bh": [round(v, 2) for v in bh],
        "dd": [round(v * 100, 2) for v in dd],
    }
    tr = r["trades"]
    rows = "".join(
        f"<tr><td>{x.entrada:%Y-%m-%d %H:%M}</td><td>{x.salida:%Y-%m-%d %H:%M}</td>"
        f"<td class=n>{x.entrada_precio:,.2f}</td><td class=n>{x.salida_precio:,.2f}</td>"
        f"<td>{html.escape(x.motivo)}</td>"
        f"<td class='n {'pos' if x.pnl_pct > 0 else 'neg'}'>{x.pnl_pct:+.2%}</td></tr>"
        for x in tr.itertuples()
    ) if len(tr) else "<tr><td colspan=6>Sin operaciones</td></tr>"

    def tile(label, value, note=""):
        return f"<div class=tile><div class=lbl>{label}</div><div class=val>{value}</div><div class=note>{note}</div></div>"

    beat = r["rentabilidad"] > r["buy_and_hold"]
    tiles = "".join([
        tile("Rentabilidad", f"{r['rentabilidad']:+.1%}",
             f"{'▲ supera' if beat else '▼ no supera'} a comprar y mantener ({r['buy_and_hold']:+.1%})"),
        tile("Máx. drawdown", f"{r['max_drawdown']:.1%}", "peor caída desde un máximo"),
        tile("Operaciones", f"{r['operaciones']}", f"acierto {r['acierto']:.0%} · media {r['media_operacion']:+.2%}"),
        tile("Profit factor", f"{r['profit_factor']:.2f}", f"tiempo invertido {r['exposicion']:.0%}"),
    ])
    reasons = (" · ".join(f"{k}: {v}" for k, v in tr.motivo.value_counts().items())) if len(tr) else ""

    page = TEMPLATE.replace("__TITLE__", html.escape(f"Backtest {r['symbol']} {cfg.timeframe}")) \
        .replace("__SUB__", html.escape(f"{describe(cfg)} · {r['periodo']} · capital inicial {r['initial']:.0f} USDT")) \
        .replace("__TILES__", tiles).replace("__ROWS__", rows).replace("__REASONS__", html.escape(reasons)) \
        .replace("__DATA__", json.dumps(data))
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)


TEMPLATE = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{color-scheme:light;--bg:#f4f3f0;--surface:#fcfcfb;--text:#0b0b0b;--text2:#52514e;--muted:#8a8984;
--grid:#e6e5e0;--s1:#2a78d6;--s2:#eb6834;--neg:#c2352f;--pos:#0f7a3a;--dd:#e34948}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){color-scheme:dark;--bg:#111110;--surface:#1a1a19;
--text:#f0efec;--text2:#c3c2b7;--muted:#8f8e86;--grid:#2c2c2a;--s1:#3987e5;--s2:#d95926;--neg:#ef7b77;--pos:#5cc98a;--dd:#e66767}}
:root[data-theme=dark]{color-scheme:dark;--bg:#111110;--surface:#1a1a19;--text:#f0efec;--text2:#c3c2b7;--muted:#8f8e86;
--grid:#2c2c2a;--s1:#3987e5;--s2:#d95926;--neg:#ef7b77;--pos:#5cc98a;--dd:#e66767}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:15px;margin:0 0 2px}.sub{color:var(--text2);margin:0 0 20px;font-size:13px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:16px}
.tile,.card{background:var(--surface);border:1px solid var(--grid);border-radius:10px;padding:14px 16px}
.lbl{color:var(--text2);font-size:12px;text-transform:uppercase;letter-spacing:.04em}.val{font-size:26px;font-weight:650;font-variant-numeric:tabular-nums}
.note{color:var(--muted);font-size:12px}.card{margin-bottom:16px}.cap{color:var(--text2);font-size:12px;margin:0 0 8px}
.legend{display:flex;gap:16px;font-size:12px;color:var(--text2);margin-bottom:6px}.legend i{display:inline-block;width:14px;height:2px;vertical-align:middle;margin-right:6px}
svg{display:block;width:100%;height:auto;overflow:visible}.ax{fill:var(--muted);font-size:11px}
.tip{position:fixed;pointer-events:none;background:var(--surface);border:1px solid var(--grid);border-radius:8px;padding:8px 10px;font-size:12px;
box-shadow:0 4px 16px rgba(0,0,0,.12);display:none;font-variant-numeric:tabular-nums;z-index:9}
.wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--grid);white-space:nowrap}
th{color:var(--text2);font-weight:600;position:sticky;top:0;background:var(--surface)}td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.pos{color:var(--pos)}.neg{color:var(--neg)}.scroll{max-height:420px;overflow:auto}
</style></head><body><main>
<h1>__TITLE__</h1><p class=sub>__SUB__</p>
<div class=tiles>__TILES__</div>
<div class=card><h2>Capital (USDT)</h2><p class=cap>Estrategia frente a comprar al inicio y mantener</p>
<div class=legend><span><i style="background:var(--s1)"></i>Estrategia</span><span><i style="background:var(--s2)"></i>Comprar y mantener</span></div>
<svg id=c1 viewBox="0 0 1000 320"></svg></div>
<div class=card><h2>Drawdown de la estrategia (%)</h2><p class=cap>Caída respecto al máximo anterior del capital</p>
<svg id=c2 viewBox="0 0 1000 160"></svg></div>
<div class=card><h2>Operaciones</h2><p class=cap>__REASONS__</p><div class="wrap scroll"><table>
<thead><tr><th>Entrada</th><th>Salida</th><th class=n>Precio entrada</th><th class=n>Precio salida</th><th>Motivo</th><th class=n>Resultado</th></tr></thead>
<tbody>__ROWS__</tbody></table></div></div>
<p class=note>Resultados pasados no garantizan resultados futuros. Incluye comisiones; no incluye deslizamiento.</p>
</main><div class=tip id=tip></div>
<script>
const D=__DATA__, NS="http://www.w3.org/2000/svg", tip=document.getElementById("tip");
const fmt=v=>v.toLocaleString("es-ES",{maximumFractionDigits:2});
function el(t,a,p){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);p&&p.appendChild(e);return e}
function nice(lo,hi,n){const span=hi-lo||1,step0=span/n,mag=10**Math.floor(Math.log10(step0)),f=step0/mag,
 step=(f<1.5?1:f<3?2:f<7?5:10)*mag,ticks=[];for(let v=Math.ceil(lo/step)*step;v<=hi+1e-9;v+=step)ticks.push(+v.toFixed(10));return ticks}
function chart(id,series,H,opts){
 const svg=document.getElementById(id),W=1000,L=64,R=12,T=10,B=26,n=D.t.length;
 let lo=Math.min(...series.flatMap(s=>s.v)),hi=Math.max(...series.flatMap(s=>s.v));
 if(opts.zeroTop)hi=0; const pad=(hi-lo)*.05||1; lo-=opts.zeroTop?pad:pad; hi+=opts.zeroTop?0:pad;
 const x=i=>L+(W-L-R)*i/(n-1), y=v=>T+(H-T-B)*(hi-v)/(hi-lo);
 for(const t of nice(lo,hi,4)){el("line",{x1:L,x2:W-R,y1:y(t),y2:y(t),stroke:"var(--grid)","stroke-width":1},svg);
  el("text",{x:L-8,y:y(t)+4,"text-anchor":"end",class:"ax"},svg).textContent=fmt(t)+(opts.unit||"")}
 const nt=Math.min(6,n);for(let k=0;k<nt;k++){const i=Math.round(k*(n-1)/(nt-1));
  el("text",{x:x(i),y:H-6,"text-anchor":k==0?"start":k==nt-1?"end":"middle",class:"ax"},svg).textContent=D.t[i].slice(0,10)}
 for(const s of series){const d=s.v.map((v,i)=>(i?"L":"M")+x(i).toFixed(1)+","+y(v).toFixed(1)).join("");
  if(s.area)el("path",{d:d+`L${x(n-1)},${y(0)}L${x(0)},${y(0)}Z`,fill:s.c,"fill-opacity":.18},svg);
  el("path",{d,fill:"none",stroke:s.c,"stroke-width":2,"stroke-linejoin":"round"},svg)}
 const vl=el("line",{y1:T,y2:H-B,stroke:"var(--muted)","stroke-width":1,"stroke-dasharray":"3 3",visibility:"hidden"},svg);
 const dots=series.map(s=>el("circle",{r:4.5,fill:s.c,stroke:"var(--surface)","stroke-width":2,visibility:"hidden"},svg));
 const hit=el("rect",{x:L,y:0,width:W-L-R,height:H,fill:"transparent"},svg);
 hit.addEventListener("mousemove",e=>{const r=svg.getBoundingClientRect(),px=(e.clientX-r.left)*W/r.width,
  i=Math.max(0,Math.min(n-1,Math.round((px-L)/(W-L-R)*(n-1))));
  vl.setAttribute("x1",x(i));vl.setAttribute("x2",x(i));vl.setAttribute("visibility","visible");
  dots.forEach((d,k)=>{d.setAttribute("cx",x(i));d.setAttribute("cy",y(series[k].v[i]));d.setAttribute("visibility","visible")});
  tip.innerHTML=`<div style="color:var(--text2)">${D.t[i]}</div>`+series.map(s=>
   `<div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${s.c};margin-right:6px"></span>${s.n}: <b>${fmt(s.v[i])}${opts.unit||""}</b></div>`).join("");
  tip.style.display="block";const tx=e.clientX+14+180>innerWidth?e.clientX-194:e.clientX+14;tip.style.left=tx+"px";tip.style.top=(e.clientY+14)+"px"});
 hit.addEventListener("mouseleave",()=>{tip.style.display="none";vl.setAttribute("visibility","hidden");dots.forEach(d=>d.setAttribute("visibility","hidden"))});
}
chart("c1",[{n:"Comprar y mantener",v:D.bh,c:"var(--s2)"},{n:"Estrategia",v:D.eq,c:"var(--s1)"}],320,{});
chart("c2",[{n:"Drawdown",v:D.dd,c:"var(--dd)",area:true}],160,{unit:" %",zeroTop:true});
</script></body></html>
"""
