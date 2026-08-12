#!/usr/bin/env python
"""Dibuja un trozo del grafo en una página HTML autocontenida.

El grafo completo tiene 33.330 entidades y 333.332 relaciones: ningún visor lo
dibuja de forma legible, y forzarlo solo produce una bola de pelo. Así que se
extrae un subgrafo y se dibuja ese.

Dos formas de recortar:
  --entidad X   vecindad de una entidad concreta (lo interesante para explorar)
  --top N       las N entidades más conectadas (para ver la forma general)

La página no depende de internet: la simulación de fuerzas van incrustadas, así
que el archivo funciona con doble clic y sin servidor.

Uso:
    python scripts/15_grafo_html.py --entidad "Clan del Golfo"
    python scripts/15_grafo_html.py --top 120
    python scripts/15_grafo_html.py --entidad ELN --saltos 2 --max-nodos 150
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402

COLORES = {
    "ORGANIZACION": "#4c8dd8", "PERSONA": "#e0803a", "LUGAR": "#4caf82",
    "MUNICIPIO": "#8fbc5a", "GRUPO_ARMADO": "#d0455c", "MARCO_JURIDICO": "#9b6bc4",
    "ECONOMIA_ILICITA": "#c4562a", "TECNOLOGIA": "#3fa9b5", "EVENTO": "#c9a227",
    "OTRO": "#8a8f98",
}


def subgrafo(g, entidad: str | None, saltos: int, top: int, max_nodos: int):
    import networkx as nx

    if entidad:
        if entidad not in g:
            parecidas = [n for n in g.nodes if entidad.lower() in n.lower()]
            if not parecidas:
                raise SystemExit(f"No hay ninguna entidad que contenga «{entidad}».")
            entidad = max(parecidas, key=lambda n: g.degree(n))
            print(f"  usando «{entidad}»")
        vistos = {entidad}
        frontera = {entidad}
        for _ in range(saltos):
            siguiente = set()
            for nodo in frontera:
                siguiente |= set(g.successors(nodo)) | set(g.predecessors(nodo))
            vistos |= siguiente
            frontera = siguiente
        # Si la vecindad se dispara, se conservan los vecinos mejor conectados
        # con la semilla, no los primeros que salgan del recorrido.
        if len(vistos) > max_nodos:
            def fuerza(n):
                # La semilla siempre se conserva; el resto ordena por el peso de
                # su arista con ella y desempata por grado. Ambas ramas tienen
                # que devolver el mismo tipo o `sorted` no puede compararlas.
                if n == entidad:
                    return (float("inf"), 0)
                e = g.get_edge_data(entidad, n) or g.get_edge_data(n, entidad) or {}
                return (float(e.get("peso", 0)), g.degree(n))
            vistos = set(sorted(vistos, key=fuerza, reverse=True)[:max_nodos])
        return g.subgraph(vistos).copy(), entidad

    orden = sorted(g.degree, key=lambda kv: -kv[1])[:top]
    return g.subgraph([n for n, _ in orden]).copy(), None


def podar_aristas(sub, por_nodo: int):
    """Deja solo las relaciones más fuertes de cada entidad.

    Las entidades del corpus co-ocurren masivamente: una vecindad de 90 nodos
    trae 2.532 aristas, grado medio 56. Eso es a la vez ilegible —una bola de
    pelo— y numéricamente inestable, porque la suma de los muelles aplasta la
    repulsión y colapsa el grafo a un punto. Conservando las `por_nodo` más
    pesadas de cada entidad se mantiene la estructura y desaparecen las dos
    patologías.
    """
    conservar = set()
    for n in sub.nodes:
        vecinas = [(o, d, da) for o, d, da in sub.out_edges(n, data=True)]
        vecinas += [(o, d, da) for o, d, da in sub.in_edges(n, data=True)]
        vecinas.sort(key=lambda x: -int(x[2].get("peso", 0)))
        for o, d, _ in vecinas[:por_nodo]:
            conservar.add((o, d))
    return sub.edge_subgraph(conservar).copy()


PLANTILLA = """<!doctype html>
<meta charset="utf-8">
<title>Grafo — CODEFEST AD ASTRA 2026</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ margin:0; font:14px/1.5 system-ui,-apple-system,sans-serif;
         background:#fbfbfc; color:#1a1c20; }}
  @media (prefers-color-scheme: dark) {{ body {{ background:#14161a; color:#e7e9ee; }} }}
  header {{ padding:14px 20px; border-bottom:1px solid #8884; }}
  h1 {{ margin:0 0 4px; font-size:16px; }}
  .sub {{ opacity:.65; font-size:13px; }}
  #lienzo {{ display:block; width:100vw; height:calc(100vh - 132px); cursor:grab; }}
  #lienzo:active {{ cursor:grabbing; }}
  #leyenda {{ padding:8px 20px; display:flex; flex-wrap:wrap; gap:14px;
              border-top:1px solid #8884; font-size:12px; }}
  .chip {{ display:flex; align-items:center; gap:6px; }}
  .punto {{ width:10px; height:10px; border-radius:50%; }}
  #info {{ position:fixed; right:16px; top:70px; width:290px; padding:12px 14px;
           background:#fffe; border:1px solid #8886; border-radius:8px;
           font-size:13px; display:none; box-shadow:0 4px 16px #0002; }}
  @media (prefers-color-scheme: dark) {{ #info {{ background:#1e2128ee; }} }}
  #info b {{ display:block; margin-bottom:6px; font-size:14px; }}
  #info .ev {{ opacity:.6; font-size:11px; word-break:break-all; margin-top:6px; }}
</style>
<header>
  <h1>{titulo}</h1>
  <div class="sub">{n_nodos} entidades · {n_aristas} relaciones ·
    arrastra para mover, rueda para acercar, <b>F</b> para reencuadrar,
    pasa el ratón por encima para ver detalles</div>
</header>
<canvas id="lienzo"></canvas>
<div id="info"></div>
<div id="leyenda">{leyenda}</div>
<script>
const DATOS = {datos};
const cv = document.getElementById('lienzo'), cx = cv.getContext('2d');
const info = document.getElementById('info');
let W, H, esc = 1, offX = 0, offY = 0;

function medir() {{
  const r = cv.getBoundingClientRect(), d = window.devicePixelRatio || 1;
  cv.width = r.width * d; cv.height = r.height * d; cx.setTransform(d,0,0,d,0,0);
  W = r.width; H = r.height;
}}
medir(); addEventListener('resize', () => {{ medir(); dibujar(); }});

const N = DATOS.nodos, A = DATOS.aristas;
// Arranque en círculo: desde posiciones aleatorias la simulación tarda mucho
// más en desenredarse y a veces queda atrapada en un nudo.
N.forEach((n,i) => {{
  const a = 2*Math.PI*i/N.length, r = Math.min(W,H)*0.32;
  n.x = W/2 + r*Math.cos(a); n.y = H/2 + r*Math.sin(a); n.vx = n.vy = 0;
  n.rad = 4 + Math.min(13, Math.sqrt(n.freq || 1));
}});
const idx = new Map(N.map((n,i) => [n.id, i]));
N.forEach(n => n.grado = 1);
for (const e of A) {{ N[idx.get(e.o)].grado++; N[idx.get(e.d)].grado++; }}

function paso() {{
  // Repulsión entre todos los pares. Con unos cientos de nodos el coste
  // cuadrático es irrelevante y evita montar un quadtree.
  for (let i=0;i<N.length;i++) for (let j=i+1;j<N.length;j++) {{
    const a=N[i], b=N[j]; let dx=b.x-a.x, dy=b.y-a.y;
    // Si dos nodos coinciden exactamente, dx=dy=0 y la repulsión saldría nula:
    // se quedarían pegados para siempre. Un empujón mínimo rompe la simetría.
    if (dx === 0 && dy === 0) {{ dx = (Math.random()-0.5)*0.1; dy = (Math.random()-0.5)*0.1; }}
    const d2 = Math.max(dx*dx+dy*dy, 4), d = Math.sqrt(d2);
    if (d > 420) continue;
    const f = 5200/d2, fx = f*dx/d, fy = f*dy/d;
    a.vx -= fx; a.vy -= fy; b.vx += fx; b.vy += fy;
  }}
  for (const e of A) {{
    const a=N[idx.get(e.o)], b=N[idx.get(e.d)];
    const dx=b.x-a.x, dy=b.y-a.y, d=Math.hypot(dx,dy)||0.01;
    // Se divide por el grado: sin esto, un nodo muy conectado recibe la suma de
    // decenas de muelles y arrastra el grafo entero hacia sí.
    const f = (d-110)*0.02/Math.sqrt(Math.min(a.grado, b.grado));
    const fx=f*dx/d, fy=f*dy/d;
    a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
  }}
  for (const n of N) {{
    n.vx += (W/2-n.x)*0.0022; n.vy += (H/2-n.y)*0.0022;
    if (n.fijo) {{ n.vx = n.vy = 0; continue; }}
    n.vx *= 0.82; n.vy *= 0.82; n.x += n.vx; n.y += n.vy;
  }}
}}

const T = (n) => [n.x*esc+offX, n.y*esc+offY];
function dibujar() {{
  cx.clearRect(0,0,W,H);
  cx.lineWidth = 1;
  for (const e of A) {{
    const [x1,y1]=T(N[idx.get(e.o)]), [x2,y2]=T(N[idx.get(e.d)]);
    cx.strokeStyle = e === activa ? '#e0803acc' : '#8888883a';
    cx.beginPath(); cx.moveTo(x1,y1); cx.lineTo(x2,y2); cx.stroke();
  }}
  for (const n of N) {{
    const [x,y]=T(n), r=n.rad*esc;
    cx.beginPath(); cx.arc(x,y,r,0,7); cx.fillStyle = n.color; cx.fill();
    if (n.semilla) {{ cx.lineWidth=2.5; cx.strokeStyle='#111'; cx.stroke(); cx.lineWidth=1; }}
    if (r > 6 || n.semilla) {{
      cx.fillStyle = getComputedStyle(document.body).color;
      cx.font = `${{n.semilla?'bold ':''}}${{Math.min(13,10+r/5)}}px system-ui`;
      cx.fillText(n.id.slice(0,26), x+r+3, y+4);
    }}
  }}
}}

let activa = null, arrastrando = null, panX=0, panY=0, paneando=false;
cv.addEventListener('mousemove', ev => {{
  const r=cv.getBoundingClientRect(), mx=ev.clientX-r.left, my=ev.clientY-r.top;
  if (arrastrando) {{
    arrastrando.x = (mx-offX)/esc; arrastrando.y = (my-offY)/esc; return;
  }}
  if (paneando) {{ offX += mx-panX; offY += my-panY; panX=mx; panY=my; return; }}
  let cerca = null;
  for (const n of N) {{ const [x,y]=T(n); if (Math.hypot(x-mx,y-my) < n.rad*esc+4) cerca=n; }}
  if (cerca) {{
    const rel = A.filter(e => e.o===cerca.id || e.d===cerca.id)
                 .sort((a,b)=>b.peso-a.peso).slice(0,6);
    info.style.display='block'; info.style.top=(ev.clientY+14)+'px';
    info.innerHTML = `<b>${{cerca.id}}</b><span style="opacity:.7">${{cerca.tipo}} · `
      + `${{cerca.freq}} fragmentos</span>` + rel.map(e =>
        `<div style="margin-top:5px">${{e.o===cerca.id?'→':'←'}} <i>${{e.rel}}</i> `
        + `<b>${{e.o===cerca.id?e.d:e.o}}</b> <span style="opacity:.6">(${{e.peso}})</span>`
        + `<div class="ev">${{e.ev||''}}</div></div>`).join('');
  }} else info.style.display='none';
}});
cv.addEventListener('mousedown', ev => {{
  const r=cv.getBoundingClientRect(), mx=ev.clientX-r.left, my=ev.clientY-r.top;
  for (const n of N) {{ const [x,y]=T(n);
    if (Math.hypot(x-mx,y-my) < n.rad*esc+4) {{ arrastrando=n; n.fijo=true; return; }} }}
  paneando=true; panX=mx; panY=my;
}});
addEventListener('mouseup', () => {{
  if (arrastrando) arrastrando.fijo=false;
  arrastrando=null; paneando=false;
}});
cv.addEventListener('wheel', ev => {{
  ev.preventDefault();
  const r=cv.getBoundingClientRect(), mx=ev.clientX-r.left, my=ev.clientY-r.top;
  const k = ev.deltaY<0 ? 1.1 : 0.9;
  offX = mx-(mx-offX)*k; offY = my-(my-offY)*k; esc *= k;
}}, {{passive:false}});

// Encuadre automático: la simulación no sabe de antemano cuánto se va a
// extender el grafo, así que se reajusta mientras se asienta y luego se deja
// quieto para no pelearse con el zoom del usuario.
let frames = 0;
function encuadrar() {{
  let x0=1e9, y0=1e9, x1=-1e9, y1=-1e9;
  for (const n of N) {{
    x0=Math.min(x0,n.x-n.rad); y0=Math.min(y0,n.y-n.rad);
    x1=Math.max(x1,n.x+n.rad); y1=Math.max(y1,n.y+n.rad);
  }}
  const m = 90;  // hueco para que quepan las etiquetas
  esc = Math.min((W-2*m)/Math.max(x1-x0,1), (H-2*m)/Math.max(y1-y0,1), 1.6);
  offX = (W - (x0+x1)*esc)/2; offY = (H - (y0+y1)*esc)/2;
}}
addEventListener('keydown', e => {{ if (e.key === 'f' || e.key === 'F') encuadrar(); }});

(function bucle() {{
  for (let i=0;i<2;i++) paso();
  if (++frames < 400) encuadrar();
  dibujar();
  requestAnimationFrame(bucle);
}})();
</script>
"""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--entidad")
    p.add_argument("--top", type=int, default=120)
    p.add_argument("--saltos", type=int, default=1)
    p.add_argument("--max-nodos", type=int, default=130)
    p.add_argument("--aristas-por-nodo", type=int, default=5,
                   help="relaciones más fuertes que se conservan de cada entidad")
    p.add_argument("--salida")
    args = p.parse_args()

    import networkx as nx

    ruta = config.GRAFO_DIR / "grafo.graphml"
    if not ruta.exists():
        print(f"No existe {ruta}")
        return 1
    print("cargando el grafo…")
    g = nx.read_graphml(ruta)
    print(f"  {g.number_of_nodes():,} entidades, {g.number_of_edges():,} relaciones")

    sub, semilla = subgrafo(g, args.entidad, args.saltos, args.top, args.max_nodos)
    print(f"  subgrafo: {sub.number_of_nodes()} entidades, {sub.number_of_edges()} relaciones")
    sub = podar_aristas(sub, args.aristas_por_nodo)
    print(f"  tras podar a las {args.aristas_por_nodo} más fuertes por entidad: "
          f"{sub.number_of_nodes()} entidades, {sub.number_of_edges()} relaciones")

    nodos = [{
        "id": n,
        "tipo": d.get("tipo", "OTRO"),
        "freq": int(d.get("frecuencia", 1)),
        "color": COLORES.get(d.get("tipo", "OTRO"), COLORES["OTRO"]),
        "semilla": n == semilla,
    } for n, d in sub.nodes(data=True)]

    aristas = [{
        "o": o, "d": dd,
        "rel": da.get("relacion", "?"),
        "peso": int(da.get("peso", 1)),
        "ev": (da.get("evidencia_chunks") or "").split(",")[0],
    } for o, dd, da in sub.edges(data=True)]

    tipos = sorted({n["tipo"] for n in nodos})
    leyenda = "".join(
        f'<div class="chip"><span class="punto" style="background:'
        f'{COLORES.get(t, COLORES["OTRO"])}"></span>{t.lower()}</div>' for t in tipos)

    titulo = (f"Vecindad de «{semilla}» a {args.saltos} salto(s)" if semilla
              else f"Las {sub.number_of_nodes()} entidades más conectadas del grafo")

    html = PLANTILLA.format(
        titulo=titulo,
        n_nodos=f"{sub.number_of_nodes():,}".replace(",", "."),
        n_aristas=f"{sub.number_of_edges():,}".replace(",", "."),
        leyenda=leyenda,
        datos=json.dumps({"nodos": nodos, "aristas": aristas}, ensure_ascii=False),
    )

    nombre = args.salida or (
        config.REPORTS_DIR / (f"grafo_{semilla[:28].replace(' ', '_')}.html" if semilla
                              else f"grafo_top{sub.number_of_nodes()}.html"))
    with open(nombre, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"\n-> {nombre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
