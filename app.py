from flask import Flask, request, Response
import csv, io, html
from collections import Counter

app = Flask(__name__)
DATA_FILE = "base_classificada_por_ciclo.csv"


def load_rows():
    with open(DATA_FILE, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def pct(n, d):
    return round(n * 100 / d, 2) if d else 0


def unique(rows, col):
    return sorted({r.get(col, "") for r in rows if r.get(col, "")})


def filter_rows(rows):
    for col, param in [
        ("Ciclo", "ciclo"),
        ("Produto", "produto"),
        ("Status executivo", "status"),
        ("Categoria problema", "categoria"),
        ("Equipe sugerida", "equipe"),
        ("Responsável", "responsavel"),
    ]:
        val = request.args.get(param, "Todos")
        if val and val != "Todos":
            rows = [r for r in rows if r.get(col) == val]
    q = request.args.get("q", "").strip().lower()
    if q:
        rows = [r for r in rows if q in (" ".join(r.values()).lower())]
    return rows


def top_table(rows, col, limit=10):
    total = len(rows)
    out = ""
    for k, v in Counter(r.get(col, "") for r in rows).most_common(limit):
        out += f"<tr><td>{html.escape(k)}</td><td>{v}</td><td>{pct(v,total)}%</td></tr>"
    return out or "<tr><td colspan='3'>Sem dados</td></tr>"


@app.route("/download")
def download():
    rows = filter_rows(load_rows())
    if not rows:
        return Response("sem dados", mimetype="text/plain")
    output = io.StringIO()
    w = csv.DictWriter(output, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=jiras_filtrados.csv"},
    )


@app.route("/")
def index():
    all_rows = load_rows()
    rows = filter_rows(all_rows)
    total = len(rows)
    alto = sum(1 for r in rows if r.get("Impacto") == "Alto")
    final = sum(1 for r in rows if r.get("Status executivo") == "Finalizado")
    backlog = sum(1 for r in rows if r.get("Status executivo") == "Backlog")
    plataforma = sum(1 for r in rows if r.get("Categoria problema") == "Configuração de plataforma")

    def opts(col, param):
        cur = request.args.get(param, "Todos")
        s = f"<option {'selected' if cur == 'Todos' else ''}>Todos</option>"
        for v in unique(all_rows, col):
            s += f"<option value='{html.escape(v)}' {'selected' if cur == v else ''}>{html.escape(v)}</option>"
        return s

    sample = "".join(
        [
            f"<tr><td>{html.escape(r.get('Chave Jira',''))}</td>"
            f"<td>{html.escape(r.get('Ciclo',''))}</td>"
            f"<td>{html.escape(r.get('Resumo',''))}</td>"
            f"<td>{html.escape(r.get('Categoria problema',''))}</td>"
            f"<td>{html.escape(r.get('Equipe sugerida',''))}</td>"
            f"<td>{html.escape(r.get('Responsável',''))}</td>"
            f"<td>{html.escape(r.get('Status executivo',''))}</td>"
            f"<td>{html.escape(r.get('Impacto',''))}</td></tr>"
            for r in rows[:200]
        ]
    )

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Dashboard Jiras MEC</title>
<style>
body{{font-family:Arial,sans-serif;background:#f4f7fb;margin:0;color:#152033}}
.hero{{background:linear-gradient(135deg,#0B1F33,#1F4E78);color:white;padding:28px 34px}}
.wrap{{padding:24px 34px}}
.cards{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:18px}}
.card{{background:white;border-radius:16px;padding:18px;box-shadow:0 8px 24px #0001}}
.num{{font-size:30px;font-weight:800}}
.label{{color:#607086;font-size:13px}}
form{{background:white;border-radius:16px;padding:16px;display:grid;grid-template-columns:repeat(4,1fr);gap:12px;box-shadow:0 8px 24px #0001}}
select,input{{width:100%;padding:10px;border:1px solid #d7e0ea;border-radius:10px}}
button,.btn{{background:#1F4E78;color:white;border:0;padding:11px 14px;border-radius:10px;text-decoration:none;text-align:center}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:18px}}
table{{width:100%;border-collapse:collapse;background:white;border-radius:14px;overflow:hidden;box-shadow:0 8px 24px #0001}}
th{{background:#0B1F33;color:white;text-align:left;padding:10px}}
td{{border-bottom:1px solid #eef2f6;padding:9px;font-size:13px;vertical-align:top}}
.full{{margin-top:18px;overflow:auto}}
@media(max-width:900px){{.cards,.grid,form{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="hero"><h1>Dashboard Jiras MEC por Ciclos</h1><p>Análise por ciclo, equipe, responsável, status, impacto e configuração de plataforma.</p></div>
<div class="wrap">
<form>
<div><label>Ciclo</label><select name="ciclo">{opts('Ciclo','ciclo')}</select></div>
<div><label>Produto</label><select name="produto">{opts('Produto','produto')}</select></div>
<div><label>Status</label><select name="status">{opts('Status executivo','status')}</select></div>
<div><label>Categoria</label><select name="categoria">{opts('Categoria problema','categoria')}</select></div>
<div><label>Equipe</label><select name="equipe">{opts('Equipe sugerida','equipe')}</select></div>
<div><label>Responsável</label><select name="responsavel">{opts('Responsável','responsavel')}</select></div>
<div><label>Busca livre</label><input name="q" value="{html.escape(request.args.get('q',''))}" placeholder="aluno, resultado, upload..."></div>
<div style="display:flex;gap:8px;align-items:end"><button>Filtrar</button><a class="btn" href="/download?{html.escape(request.query_string.decode())}">Baixar CSV</a></div>
</form>
<div class="cards"><div class="card"><div class="num">{total}</div><div class="label">Total</div></div><div class="card"><div class="num">{alto}</div><div class="label">Alto impacto</div></div><div class="card"><div class="num">{final}</div><div class="label">Finalizados</div></div><div class="card"><div class="num">{backlog}</div><div class="label">Backlog</div></div><div class="card"><div class="num">{plataforma}</div><div class="label">Configuração Plataforma</div></div></div>
<div class="grid"><div><h2>Top problemas</h2><table><tr><th>Categoria</th><th>Qtd</th><th>%</th></tr>{top_table(rows,'Categoria problema')}</table></div><div><h2>Equipes sugeridas</h2><table><tr><th>Equipe</th><th>Qtd</th><th>%</th></tr>{top_table(rows,'Equipe sugerida')}</table></div></div>
<div class="grid"><div><h2>Responsáveis</h2><table><tr><th>Responsável</th><th>Qtd</th><th>%</th></tr>{top_table(rows,'Responsável')}</table></div><div><h2>Status</h2><table><tr><th>Status</th><th>Qtd</th><th>%</th></tr>{top_table(rows,'Status executivo')}</table></div></div>
<div class="full"><h2>Registros filtrados</h2><table><tr><th>Jira</th><th>Ciclo</th><th>Resumo</th><th>Problema</th><th>Equipe</th><th>Responsável</th><th>Status</th><th>Impacto</th></tr>{sample}</table></div>
</div></body></html>"""


if __name__ == "__main__":
    app.run(debug=True)
