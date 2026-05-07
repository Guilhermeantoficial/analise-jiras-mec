from __future__ import annotations

import html
import unicodedata
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
from flask import Flask, Response, request

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE_NAME = "base_classificada_por_ciclo.csv"
DATA_FILE = BASE_DIR / DATA_FILE_NAME

FILTERS = [
    ("ano", "Ano", "Ano"),
    ("ciclo", "Ciclo", "Ciclo de análise"),
    ("produto", "Produto", "Frente / Produto MEC"),
    ("status", "Status executivo", "Situação executiva"),
    ("categoria", "Categoria problema", "Natureza do problema"),
    ("equipe", "Equipe sugerida", "Equipe indicada"),
    ("responsavel", "Responsável", "Responsável pelo Jira"),
    ("impacto", "Impacto", "Impacto operacional"),
]

SEARCH_COLUMNS = [
    "Chave Jira",
    "Resumo",
    "Ciclo",
    "Produto",
    "Status executivo",
    "Categoria problema",
    "Subtipo configuração/plataforma",
    "Equipe sugerida",
    "Responsável",
    "Relator",
    "Impacto",
    "Causa provável",
    "Solução recomendada",
    "Descrição curta",
]

REQUIRED_COLUMNS = [
    "Chave Jira",
    "Resumo",
    "Ano",
    "Mês",
    "Ciclo",
    "Data criação",
    "Status original",
    "Status executivo",
    "Prioridade",
    "Resolução",
    "Responsável",
    "Relator",
    "Produto",
    "Categoria problema",
    "Subtipo configuração/plataforma",
    "Equipe sugerida",
    "Impacto",
    "Causa provável",
    "Solução recomendada",
    "Tempo resolução",
    "Descrição curta",
]


def strip_accents(value: str) -> str:
    text = str(value or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def escape(value) -> str:
    return html.escape(str(value if value is not None else ""))


def fmt_int(value: int | float) -> str:
    try:
        return f"{int(value):,}".replace(",", ".")
    except Exception:
        return "0"


def fmt_pct(value: int | float, total: int | float) -> str:
    if not total:
        return "0,0%"
    return f"{(float(value) * 100 / float(total)):.1f}%".replace(".", ",")


def load_dataframe() -> pd.DataFrame:
    """Carrega sempre o CSV localizado na mesma pasta do app.py."""
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Arquivo {DATA_FILE_NAME} não encontrado. Caminho esperado: {DATA_FILE}"
        )

    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig", dtype=str).fillna("")
    df.columns = [str(col).strip() for col in df.columns]

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # Normalizações leves para evitar filtros vazios por espaço ou número como texto quebrado.
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    return df


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()

    for param, col, _label in FILTERS:
        selected = request.args.get(param, "Todos")
        if selected and selected != "Todos" and col in filtered.columns:
            filtered = filtered[filtered[col].astype(str) == str(selected)]

    query = request.args.get("q", "").strip()
    if query:
        query_norm = strip_accents(query)
        available_cols = [col for col in SEARCH_COLUMNS if col in filtered.columns]
        search_text = filtered[available_cols].astype(str).agg(" ".join, axis=1).map(strip_accents)
        filtered = filtered[search_text.str.contains(query_norm, na=False, regex=False)]

    return filtered


def option_values(df: pd.DataFrame, col: str) -> list[str]:
    if col not in df.columns:
        return []
    values = [v for v in df[col].dropna().astype(str).str.strip().unique().tolist() if v]
    if col in {"Ano", "Mês"}:
        return sorted(values, key=lambda x: int(x) if x.isdigit() else 9999)
    if col == "Ciclo":
        roman_order = {"I": 1, "II": 2, "III": 3}

        def cycle_key(value: str):
            parts = value.split()
            year = 9999
            cycle = 9999
            for p in parts:
                if p.isdigit():
                    year = int(p)
                elif p in roman_order:
                    cycle = roman_order[p]
            return (year, cycle, value)

        return sorted(values, key=cycle_key)
    return sorted(values, key=lambda x: strip_accents(x))


def select_html(df: pd.DataFrame, param: str, col: str, label: str) -> str:
    current = request.args.get(param, "Todos")
    options = [f'<option value="Todos" {"selected" if current == "Todos" else ""}>Todos</option>']
    for value in option_values(df, col):
        selected = "selected" if current == value else ""
        options.append(f'<option value="{escape(value)}" {selected}>{escape(value)}</option>')
    return f"""
    <div class="field">
        <label for="{escape(param)}">{escape(label)}</label>
        <select id="{escape(param)}" name="{escape(param)}">{''.join(options)}</select>
    </div>
    """


def count_contains(df: pd.DataFrame, col: str, value: str) -> int:
    if col not in df.columns or df.empty:
        return 0
    target = strip_accents(value)
    return int(df[col].astype(str).map(strip_accents).str.contains(target, na=False, regex=False).sum())


def is_platform_config(row: pd.Series) -> bool:
    categoria = strip_accents(row.get("Categoria problema", ""))
    subtipo = strip_accents(row.get("Subtipo configuração/plataforma", ""))
    texto = " ".join(
        [
            categoria,
            subtipo,
            strip_accents(row.get("Resumo", "")),
            strip_accents(row.get("Descrição curta", "")),
        ]
    )
    keys = [
        "configuracao",
        "plataforma",
        "perfil",
        "permissao",
        "acesso",
        "usuario",
        "upload",
        "download",
        "formulario",
        "campo",
        "grid",
        "select",
    ]
    return any(key in texto for key in keys)


def metric_card(title: str, value: int | str, subtitle: str, tone: str = "") -> str:
    return f"""
    <article class="metric {escape(tone)}">
        <span>{escape(title)}</span>
        <strong>{escape(value)}</strong>
        <small>{escape(subtitle)}</small>
    </article>
    """


def ranking_table(df: pd.DataFrame, col: str, title_col: str, limit: int = 10) -> str:
    total = len(df)
    if df.empty or col not in df.columns:
        return '<tr><td colspan="4" class="empty">Sem dados para os filtros selecionados.</td></tr>'

    counts = (
        df[col]
        .replace("", "Não informado")
        .value_counts(dropna=False)
        .head(limit)
        .reset_index()
    )
    counts.columns = [title_col, "Qtd"]

    rows = []
    max_value = int(counts["Qtd"].max()) if not counts.empty else 0
    for _, row in counts.iterrows():
        label = row[title_col]
        qtd = int(row["Qtd"])
        percent = fmt_pct(qtd, total)
        width = round(qtd * 100 / max_value, 1) if max_value else 0
        rows.append(
            f"""
            <tr>
                <td>{escape(label)}</td>
                <td class="num-cell">{fmt_int(qtd)}</td>
                <td class="num-cell">{percent}</td>
                <td><div class="bar"><i style="width:{width}%"></i></div></td>
            </tr>
            """
        )
    return "".join(rows)


def responsible_table(df: pd.DataFrame, limit: int = 12) -> str:
    total = len(df)
    if df.empty or "Responsável" not in df.columns:
        return '<tr><td colspan="7" class="empty">Sem dados para os filtros selecionados.</td></tr>'

    work = df.copy()
    work["Responsável"] = work["Responsável"].replace("", "Não informado")
    rows = []
    for responsavel, group in work.groupby("Responsável", dropna=False):
        qtd = len(group)
        finalizados = count_contains(group, "Status executivo", "Finalizado")
        backlog = count_contains(group, "Status executivo", "Backlog")
        alto = count_contains(group, "Impacto", "Alto")
        principal_categoria = (
            group["Categoria problema"].replace("", "Não informado").value_counts().index[0]
            if "Categoria problema" in group.columns and not group.empty
            else "Não informado"
        )
        resolucao = (
            group["Resolução"].replace("", "Não informado").value_counts().index[0]
            if "Resolução" in group.columns and not group.empty
            else "Não informado"
        )
        rows.append(
            {
                "Responsável": responsavel,
                "Qtd": qtd,
                "%": fmt_pct(qtd, total),
                "Finalizados": finalizados,
                "Taxa": fmt_pct(finalizados, qtd),
                "Backlog": backlog,
                "Alto": alto,
                "Categoria": principal_categoria,
                "Resolução": resolucao,
            }
        )

    rows = sorted(rows, key=lambda x: x["Qtd"], reverse=True)[:limit]
    return "".join(
        f"""
        <tr>
            <td>{escape(row['Responsável'])}</td>
            <td class="num-cell">{fmt_int(row['Qtd'])}</td>
            <td class="num-cell">{escape(row['%'])}</td>
            <td class="num-cell">{fmt_int(row['Finalizados'])}</td>
            <td class="num-cell">{escape(row['Taxa'])}</td>
            <td class="num-cell">{fmt_int(row['Alto'])}</td>
            <td>{escape(row['Categoria'])}</td>
            <td>{escape(row['Resolução'])}</td>
        </tr>
        """
        for row in rows
    )


def platform_matrix(df: pd.DataFrame) -> str:
    if df.empty:
        return '<tr><td colspan="5" class="empty">Sem dados para os filtros selecionados.</td></tr>'

    work = df[df.apply(is_platform_config, axis=1)].copy()
    if work.empty:
        return '<tr><td colspan="5" class="empty">Nenhum problema de configuração/plataforma encontrado para os filtros selecionados.</td></tr>'

    if "Subtipo configuração/plataforma" not in work.columns:
        work["Subtipo configuração/plataforma"] = "Não informado"
    work["Subtipo configuração/plataforma"] = work["Subtipo configuração/plataforma"].replace("", "Configuração/Plataforma geral")

    rows = []
    grouped = work.groupby("Subtipo configuração/plataforma", dropna=False)
    for subtipo, group in sorted(grouped, key=lambda item: len(item[1]), reverse=True)[:10]:
        qtd = len(group)
        equipe = (
            group["Equipe sugerida"].replace("", "Não informado").value_counts().index[0]
            if "Equipe sugerida" in group.columns and not group.empty
            else "Não informado"
        )
        impacto = (
            group["Impacto"].replace("", "Não informado").value_counts().index[0]
            if "Impacto" in group.columns and not group.empty
            else "Não informado"
        )
        solucao = (
            group["Solução recomendada"].replace("", "Validar configuração, evidência, permissão e regra aplicada.").value_counts().index[0]
            if "Solução recomendada" in group.columns and not group.empty
            else "Validar configuração, evidência, permissão e regra aplicada."
        )
        rows.append(
            f"""
            <tr>
                <td>{escape(subtipo)}</td>
                <td class="num-cell">{fmt_int(qtd)}</td>
                <td>{escape(equipe)}</td>
                <td>{escape(impacto)}</td>
                <td>{escape(solucao)}</td>
            </tr>
            """
        )
    return "".join(rows)


def records_table(df: pd.DataFrame, limit: int = 250) -> str:
    if df.empty:
        return '<tr><td colspan="9" class="empty">Nenhum Jira encontrado para os filtros selecionados.</td></tr>'

    rows = []
    for _, r in df.head(limit).iterrows():
        rows.append(
            f"""
            <tr>
                <td><strong>{escape(r.get('Chave Jira', ''))}</strong></td>
                <td>{escape(r.get('Ciclo', ''))}</td>
                <td>{escape(r.get('Produto', ''))}</td>
                <td>{escape(r.get('Resumo', ''))}</td>
                <td>{escape(r.get('Categoria problema', ''))}</td>
                <td>{escape(r.get('Equipe sugerida', ''))}</td>
                <td>{escape(r.get('Responsável', ''))}</td>
                <td><span class="pill">{escape(r.get('Status executivo', ''))}</span></td>
                <td><span class="pill impact">{escape(r.get('Impacto', ''))}</span></td>
            </tr>
            """
        )
    return "".join(rows)


def current_query_without_empty() -> str:
    pairs = [(k, v) for k, v in request.args.items() if v and v != "Todos"]
    return urlencode(pairs)


def render_error(message: str) -> str:
    return f"""
    <!doctype html>
    <html lang="pt-br">
    <head><meta charset="utf-8"><title>Erro no Dashboard</title>{styles()}</head>
    <body>
        <main class="error-box">
            <h1>Não foi possível carregar a base</h1>
            <p>{escape(message)}</p>
            <p>Coloque o arquivo <strong>{DATA_FILE_NAME}</strong> na mesma pasta do <strong>app.py</strong>.</p>
        </main>
    </body>
    </html>
    """


@app.route("/download")
def download() -> Response:
    df = apply_filters(load_dataframe())
    csv_text = df.to_csv(index=False, sep=";", encoding="utf-8-sig")
    return Response(
        "\ufeff" + csv_text,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=jiras_filtrados_dashboard.csv"},
    )


@app.route("/")
def index() -> str:
    try:
        full_df = load_dataframe()
    except Exception as exc:
        return render_error(str(exc))

    df = apply_filters(full_df)
    total_base = len(full_df)
    total = len(df)
    alto = count_contains(df, "Impacto", "Alto")
    finalizados = count_contains(df, "Status executivo", "Finalizado")
    backlog = count_contains(df, "Status executivo", "Backlog")
    andamento = count_contains(df, "Status executivo", "Em andamento")
    plataforma = int(df.apply(is_platform_config, axis=1).sum()) if not df.empty else 0
    resultados = count_contains(df, "Categoria problema", "Resultados") + count_contains(df, "Resumo", "resultado")

    filtros = "".join(select_html(full_df, param, col, label) for param, col, label in FILTERS)
    q = request.args.get("q", "")
    query = current_query_without_empty()
    download_url = f"/download?{query}" if query else "/download"

    leitura = build_executive_reading(df, total_base)

    return f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard Jiras MEC | Análise por Ciclos</title>
{styles()}
</head>
<body>
<header class="hero">
    <div>
        <p class="eyebrow">Análise executiva dos Jiras MEC</p>
        <h1>Dashboard por ciclos, problemas, equipes e responsáveis</h1>
    </div>
    <div class="hero-card">
        <span>Registros na base</span>
        <strong>{fmt_int(total_base)}</strong>
        <small>Antes da aplicação dos filtros</small>
    </div>
</header>

<main class="container">
    <section class="panel filter-panel">
        <div class="section-title">
            <div>
                <h2>Filtros da análise</h2>
                <p>Use os filtros abaixo para recalcular todos os indicadores, rankings, responsáveis e registros.</p>
            </div>
            <a class="ghost" href="/">Limpar filtros</a>
        </div>
        <form method="get" action="/" class="filters">
            {filtros}
            <div class="field field-search">
                <label for="q">Busca livre no texto do Jira</label>
                <input id="q" name="q" value="{escape(q)}" placeholder="Ex.: resultado, upload, permissão, aluno, card...">
            </div>
            <div class="actions">
                <button type="submit">Aplicar filtros</button>
            </div>
        </form>
    </section>

    <section class="metrics">
        {metric_card('Jiras filtrados', fmt_int(total), f'{fmt_pct(total, total_base)} da base total', 'primary')}
        {metric_card('Alto impacto', fmt_int(alto), f'{fmt_pct(alto, total)} dos filtrados', 'danger')}
        {metric_card('Finalizados', fmt_int(finalizados), f'{fmt_pct(finalizados, total)} dos filtrados', 'success')}
        {metric_card('Backlog', fmt_int(backlog), f'{fmt_pct(backlog, total)} dos filtrados', 'warning')}
        {metric_card('Em andamento', fmt_int(andamento), f'{fmt_pct(andamento, total)} dos filtrados', 'info')}
        {metric_card('Configuração / Plataforma', fmt_int(plataforma), f'{fmt_pct(plataforma, total)} dos filtrados', 'purple')}
    </section>

    <section class="panel insight">
        <h2>Leitura executiva dos filtros atuais</h2>
        <p>{leitura}</p>
    </section>

    <section class="grid two">
        <div class="panel">
            <h2>Top naturezas de problema</h2>
            <p class="hint">Ranking calculado exclusivamente sobre os Jiras filtrados.</p>
            <div class="table-wrap"><table><thead><tr><th>Natureza</th><th>Qtd</th><th>%</th><th>Volume</th></tr></thead><tbody>{ranking_table(df, 'Categoria problema', 'Natureza')}</tbody></table></div>
        </div>
        <div class="panel">
            <h2>Equipes indicadas para tratamento</h2>
            <p class="hint">Ajuda a direcionar o fluxo entre Dados, Sistemas Web, Plataforma, Desenvolvimento e outras frentes.</p>
            <div class="table-wrap"><table><thead><tr><th>Equipe</th><th>Qtd</th><th>%</th><th>Volume</th></tr></thead><tbody>{ranking_table(df, 'Equipe sugerida', 'Equipe')}</tbody></table></div>
        </div>
    </section>

    <section class="grid two">
        <div class="panel">
            <h2>Ciclos com maior demanda</h2>
            <p class="hint">Comparativo entre Ciclo I, II e III por ano.</p>
            <div class="table-wrap"><table><thead><tr><th>Ciclo</th><th>Qtd</th><th>%</th><th>Volume</th></tr></thead><tbody>{ranking_table(df, 'Ciclo', 'Ciclo')}</tbody></table></div>
        </div>
        <div class="panel">
            <h2>Situação executiva</h2>
            <p class="hint">Distribuição dos Jiras por status consolidado.</p>
            <div class="table-wrap"><table><thead><tr><th>Situação</th><th>Qtd</th><th>%</th><th>Volume</th></tr></thead><tbody>{ranking_table(df, 'Status executivo', 'Status')}</tbody></table></div>
        </div>
    </section>

    <section class="panel">
        <h2>Matriz especial: configuração e plataforma</h2>
        <p class="hint">Agrupa ocorrências ligadas a permissões, acesso, perfil, upload/download, formulário, grid, select, configuração e comportamento de plataforma.</p>
        <div class="table-wrap"><table><thead><tr><th>Subtipo</th><th>Qtd</th><th>Equipe principal</th><th>Impacto principal</th><th>Solução recomendada</th></tr></thead><tbody>{platform_matrix(df)}</tbody></table></div>
    </section>

    <section class="panel">
        <h2>Análise por responsável</h2>
        <p class="hint">Mostra volume, percentual, resolução, finalização, alto impacto e principal problema por responsável.</p>
        <div class="table-wrap"><table><thead><tr><th>Responsável</th><th>Qtd</th><th>%</th><th>Finalizados</th><th>Taxa finalizada</th><th>Alto impacto</th><th>Principal problema</th><th>Resolução mais comum</th></tr></thead><tbody>{responsible_table(df)}</tbody></table></div>
    </section>

    <section class="panel">
        <div class="section-title">
            <div>
                <h2>Registros filtrados</h2>
                <p>Exibição limitada aos primeiros 250 registros para manter a tela leve. Baixe a base filtrada para ver tudo.</p>
            </div>
            <a class="ghost" href="{escape(download_url)}">Exportar CSV</a>
        </div>
        <div class="table-wrap records"><table><thead><tr><th>Jira</th><th>Ciclo</th><th>Produto</th><th>Resumo</th><th>Natureza</th><th>Equipe</th><th>Responsável</th><th>Status</th><th>Impacto</th></tr></thead><tbody>{records_table(df)}</tbody></table></div>
    </section>
</main>
</body>
</html>"""


def build_executive_reading(df: pd.DataFrame, total_base: int) -> str:
    if df.empty:
        return "Nenhum Jira foi encontrado para os filtros selecionados. Revise ciclo, produto, responsável ou busca livre."

    total = len(df)
    top_problem = df["Categoria problema"].replace("", "Não informado").value_counts().index[0]
    top_team = df["Equipe sugerida"].replace("", "Não informado").value_counts().index[0]
    top_status = df["Status executivo"].replace("", "Não informado").value_counts().index[0]
    high = count_contains(df, "Impacto", "Alto")
    platform = int(df.apply(is_platform_config, axis=1).sum())

    return (
        f"Os filtros atuais retornam {fmt_int(total)} Jiras, equivalentes a {fmt_pct(total, total_base)} da base. "
        f"A principal natureza de problema é '{top_problem}', a equipe mais indicada é '{top_team}' e a situação executiva mais frequente é '{top_status}'. "
        f"Há {fmt_int(high)} caso(s) de alto impacto e {fmt_int(platform)} ocorrência(s) relacionadas a configuração/plataforma."
    )


def styles() -> str:
    return """
<style>
:root{
    --bg:#f4f7fb;
    --panel:#ffffff;
    --ink:#122033;
    --muted:#64748b;
    --line:#e4eaf2;
    --navy:#102a43;
    --blue:#1f6feb;
    --blue-dark:#1f4e78;
    --green:#0f7b55;
    --red:#b42318;
    --orange:#b45309;
    --purple:#6d28d9;
    --shadow:0 18px 45px rgba(15, 23, 42, .09);
    --radius:22px;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);font-family:Inter,Segoe UI,Arial,sans-serif;color:var(--ink)}
a{color:inherit}
.hero{background:linear-gradient(135deg,#071729 0%,#143b5d 56%,#1f6feb 100%);color:#fff;padding:34px 42px;display:grid;grid-template-columns:1fr 260px;gap:28px;align-items:end}
.eyebrow{text-transform:uppercase;letter-spacing:.12em;font-size:12px;font-weight:800;color:#b8d7ff;margin:0 0 12px}
h1{font-size:36px;line-height:1.08;margin:0;max-width:980px}
.subtitle{font-size:15px;color:#d7e9ff;max-width:860px;margin:14px 0 0}
.hero-card{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);border-radius:18px;padding:20px;backdrop-filter:blur(10px)}
.hero-card span,.hero-card small{display:block;color:#d7e9ff;font-size:13px}.hero-card strong{display:block;font-size:34px;margin:6px 0}
.container{padding:28px 42px 52px;max-width:1540px;margin:0 auto}.panel{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);padding:22px;margin-bottom:20px}.filter-panel{margin-top:-12px}.section-title{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;margin-bottom:16px}h2{font-size:20px;margin:0 0 6px}.section-title p,.hint{color:var(--muted);font-size:13px;margin:0 0 14px}.filters{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.field label{display:block;font-size:12px;font-weight:800;color:#334155;margin:0 0 7px}select,input{width:100%;height:43px;border:1px solid #cbd5e1;background:#fff;border-radius:12px;padding:0 12px;color:#172033;outline:none}select:focus,input:focus{border-color:var(--blue);box-shadow:0 0 0 3px rgba(31,111,235,.12)}.field-search{grid-column:span 2}.actions{display:flex;gap:10px;align-items:end}.actions button,.button-secondary,.ghost{border:0;border-radius:12px;height:43px;padding:0 15px;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;font-weight:800;cursor:pointer;white-space:nowrap}.actions button{background:var(--blue-dark);color:white}.button-secondary{background:#eaf2ff;color:#174270}.ghost{background:#f1f5f9;color:#334155}.metrics{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:14px;margin-bottom:20px}.metric{background:var(--panel);border:1px solid var(--line);box-shadow:var(--shadow);border-radius:20px;padding:18px;position:relative;overflow:hidden}.metric:before{content:"";position:absolute;left:0;top:0;bottom:0;width:5px;background:#94a3b8}.metric.primary:before{background:var(--blue)}.metric.danger:before{background:var(--red)}.metric.success:before{background:var(--green)}.metric.warning:before{background:var(--orange)}.metric.info:before{background:var(--blue-dark)}.metric.purple:before{background:var(--purple)}.metric span{display:block;color:var(--muted);font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.04em}.metric strong{display:block;font-size:30px;margin:8px 0 4px}.metric small{color:var(--muted);font-size:12px}.insight{border-left:6px solid var(--blue-dark)}.insight p{font-size:15px;line-height:1.6;margin:0;color:#26374d}.grid.two{display:grid;grid-template-columns:1fr 1fr;gap:20px}.table-wrap{overflow:auto;border-radius:16px;border:1px solid var(--line)}table{width:100%;border-collapse:collapse;background:#fff;min-width:620px}th{background:#102a43;color:white;text-align:left;font-size:12px;letter-spacing:.03em;text-transform:uppercase;padding:12px}td{border-bottom:1px solid #edf2f7;padding:11px 12px;font-size:13px;vertical-align:top}tr:hover td{background:#f8fbff}.num-cell{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.bar{height:9px;background:#e5edf7;border-radius:99px;overflow:hidden;min-width:90px}.bar i{display:block;height:100%;background:linear-gradient(90deg,#1f4e78,#1f6feb);border-radius:99px}.pill{display:inline-flex;align-items:center;border-radius:99px;background:#eef4ff;color:#174270;padding:5px 9px;font-size:12px;font-weight:800;white-space:nowrap}.pill.impact{background:#fff4e6;color:#9a3412}.records table{min-width:1180px}.empty{text-align:center;color:var(--muted);padding:22px}.error-box{max-width:780px;margin:80px auto;background:#fff;border-radius:24px;padding:34px;box-shadow:var(--shadow);border:1px solid var(--line)}.error-box h1{color:var(--red);font-size:28px}@media(max-width:1180px){.hero{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(3,1fr)}.filters{grid-template-columns:repeat(2,1fr)}.grid.two{grid-template-columns:1fr}}@media(max-width:760px){.hero,.container{padding-left:18px;padding-right:18px}h1{font-size:28px}.metrics,.filters{grid-template-columns:1fr}.field-search{grid-column:auto}.actions{flex-direction:column;align-items:stretch}.grid.two{grid-template-columns:1fr}}
</style>
"""


if __name__ == "__main__":
    app.run(debug=True)
