import os
import zipfile
import requests
import geopandas as gpd
import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html
from sqlalchemy import create_engine

# --- Conexão PostgreSQL ---
engine = create_engine(os.environ.get("DATABASE_URL"))

# --- Caminhos do shapefile ---
LOCAL_PATH  = r"D:\VSCode\FUNASA\BR_setores\BR_setores_CD2022.shp"
SERVER_PATH = "BR_setores_CD2022.shp"
IBGE_URL    = "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais/2022/Malha_de_setores_(shp)_Brasil/BR/BR_Setores_2022.zip"

def garantir_shapefile():
    """Baixa o shapefile se não existir — não carrega nada na memória."""
    if os.path.exists(LOCAL_PATH) or os.path.exists(SERVER_PATH):
        return
    print("Baixando shapefile do IBGE...")
    with requests.get(IBGE_URL, stream=True) as r:
        r.raise_for_status()
        with open("BR_setores_CD2022.zip", "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    with zipfile.ZipFile("BR_setores_CD2022.zip", "r") as z:
        z.extractall(".")
    os.remove("BR_setores_CD2022.zip")
    print("Shapefile pronto!")

def ler_uf(cd_uf, cd_mun=None, cd_dist=None, cd_subdist=None):
    """Lê do disco apenas os setores da UF/filtro selecionado."""
    path = LOCAL_PATH if os.path.exists(LOCAL_PATH) else SERVER_PATH

    # Monta filtro SQL progressivo
    where = f"CD_UF = '{cd_uf}'"
    if cd_mun:
        where += f" AND CD_MUN = '{cd_mun}'"
    if cd_dist:
        where += f" AND CD_DIST = '{cd_dist}'"
    if cd_subdist:
        where += f" AND CD_SUBDIST = '{cd_subdist}'"

    return gpd.read_file(path, where=where)

# Garante que o shapefile existe (baixa se necessário)
garantir_shapefile()

# --- Busca lista de UFs do banco (leve, sem shapefile) ---
df_ufs = pd.read_sql(
    'SELECT DISTINCT cd_uf, nm_uf FROM public."IBGE_agregados_por_setores_basico" ORDER BY nm_uf',
    engine,
)
filtro_uf = [{"label": r["nm_uf"], "value": r["cd_uf"]} for _, r in df_ufs.iterrows()]

filtro_situacao = [
    {"label": "Urbana", "value": "urbana"},
    {"label": "Rural",  "value": "rural"},
]

# --- App ---
app = Dash(__name__)
server = app.server

CARD_STYLE = {
    "backgroundColor": "white",
    "borderRadius": "12px",
    "padding": "20px",
    "boxShadow": "0 0 0 2px rgba(13, 43, 85, 0.1)",
    "display": "flex",
    "flexDirection": "column",
    "rowGap": "6px",
    "fontFamily": '"DM Sans", sans-serif',
    "position": "relative",
    "overflow": "hidden",
    "transition": "transform 0.18s ease, box-shadow 0.18s ease",
}

DROPDOWN_STYLE = {"width": "180px", "fontSize": "13px"}


def kpi_card(card_id, titulo, subtitulo, cor_borda="rgb(21, 101, 192)"):
    style = {**CARD_STYLE, "borderLeft": f"5px solid {cor_borda}"}
    return html.Div(style=style, children=[
        html.Span(titulo.upper(), style={"fontSize": "12px", "color": "#888", "fontWeight": "bold"}),
        html.H2(id=card_id, style={"margin": "0", "color": cor_borda}),
        html.P(subtitulo, style={"margin": "0", "fontSize": "13px", "color": "#888"}),
    ])


app.layout = html.Div(style={"backgroundColor": "#f4f6f8", "minHeight": "100vh", "fontFamily": "Arial"}, children=[

    # CABEÇALHO
    html.Div(style={
        "backgroundColor": "white", "padding": "15px 30px",
        "display": "flex", "justifyContent": "space-between", "alignItems": "center",
        "boxShadow": "0 1px 3px rgba(0,0,0,0.1)",
    }, children=[
        html.Div([
            html.H2("Dashboard IBGE — Setores Censitários", style={"margin": "0", "color": "#1a2b4c"}),
            html.P("CENSO 2022 · ANÁLISE GEOESPACIAL", style={"margin": "0", "color": "#888", "fontSize": "12px"}),
        ]),
    ]),

    # FILTROS
    html.Div(style={
        "display": "flex", "gap": "15px", "alignItems": "center", "flexWrap": "wrap",
        "padding": "15px 30px", "backgroundColor": "white", "marginTop": "2px",
        "boxShadow": "0 1px 3px rgba(0,0,0,0.05)",
    }, children=[
        html.Span("FILTROS", style={"fontWeight": "bold", "color": "#888", "fontSize": "12px"}),
        dcc.Dropdown(id="dropdown-uf",       options=filtro_uf,       value=df_ufs["cd_uf"].iloc[0], clearable=False,  placeholder="UF",           style=DROPDOWN_STYLE),
        dcc.Dropdown(id="dropdown-mun",      options=[],              value=None,                    clearable=True,   placeholder="Município",     style=DROPDOWN_STYLE),
        dcc.Dropdown(id="dropdown-dist",     options=[],              value=None,                    clearable=True,   placeholder="Distrito",      style=DROPDOWN_STYLE),
        dcc.Dropdown(id="dropdown-subdist",  options=[],              value=None,                    clearable=True,   placeholder="Subdistrito",   style=DROPDOWN_STYLE),
        dcc.Dropdown(id="dropdown-situacao", options=filtro_situacao, value=None,                    clearable=True,   placeholder="Situação",      style={"width": "140px", "fontSize": "13px"}),
    ]),

    # CONTEÚDO
    html.Div(style={"display": "flex", "gap": "20px", "padding": "20px 30px", "alignItems": "stretch"}, children=[

        # KPIs
        html.Div(style={"display": "flex", "flexDirection": "column", "gap": "20px", "width": "280px", "flexShrink": "0"}, children=[
            kpi_card("kpi-uf",         "UF Selecionada",     "Filtro ativo",               "rgb(230, 126, 34)"),
            kpi_card("kpi-setores",    "Total de Setores",   "Setores censitários ativos",  "rgb(21, 101, 192)"),
            kpi_card("kpi-municipios", "Total de Municípios","Com registros ativos",         "rgb(46, 139, 87)"),
        ]),

        # Mapa
        html.Div(style={**CARD_STYLE, "flex": "1", "padding": "20px"}, children=[
            html.H4("Mapa de Setores Censitários", style={"margin": "0 0 5px 0"}),
            html.P("Distribuição geográfica conforme filtros selecionados",
                   style={"margin": "0 0 15px 0", "color": "#888", "fontSize": "13px"}),
            dcc.Graph(id="mapa", style={"height": "70vh"}),
        ]),
    ]),
])


# UF → Município (lê só colunas necessárias)
@app.callback(
    Output("dropdown-mun", "options"),
    Output("dropdown-mun", "value"),
    Input("dropdown-uf", "value"),
)
def atualizar_municipios(cd_uf):
    if not cd_uf:
        return [], None
    gdf_uf = gpd.read_file(
        LOCAL_PATH if os.path.exists(LOCAL_PATH) else SERVER_PATH,
        where=f"CD_UF = '{cd_uf}'",
        columns=["CD_MUN", "NM_MUN"],
    )
    df = gdf_uf[["CD_MUN", "NM_MUN"]].drop_duplicates().sort_values("NM_MUN")
    return [{"label": r["NM_MUN"], "value": r["CD_MUN"]} for _, r in df.iterrows()], None


# Município → Distrito
@app.callback(
    Output("dropdown-dist", "options"),
    Output("dropdown-dist", "value"),
    Input("dropdown-uf", "value"),
    Input("dropdown-mun", "value"),
)
def atualizar_distritos(cd_uf, cd_mun):
    if not cd_uf:
        return [], None
    where = f"CD_UF = '{cd_uf}'"
    if cd_mun:
        where += f" AND CD_MUN = '{cd_mun}'"
    gdf_f = gpd.read_file(
        LOCAL_PATH if os.path.exists(LOCAL_PATH) else SERVER_PATH,
        where=where, columns=["CD_DIST", "NM_DIST"],
    )
    df = gdf_f[["CD_DIST", "NM_DIST"]].drop_duplicates().sort_values("NM_DIST")
    if df.empty:
        return [], None
    return [{"label": r["NM_DIST"], "value": r["CD_DIST"]} for _, r in df.iterrows()], None


# Distrito → Subdistrito
@app.callback(
    Output("dropdown-subdist", "options"),
    Output("dropdown-subdist", "value"),
    Input("dropdown-uf", "value"),
    Input("dropdown-mun", "value"),
    Input("dropdown-dist", "value"),
)
def atualizar_subdistritos(cd_uf, cd_mun, cd_dist):
    if not cd_uf:
        return [], None
    where = f"CD_UF = '{cd_uf}'"
    if cd_mun:
        where += f" AND CD_MUN = '{cd_mun}'"
    if cd_dist:
        where += f" AND CD_DIST = '{cd_dist}'"
    gdf_f = gpd.read_file(
        LOCAL_PATH if os.path.exists(LOCAL_PATH) else SERVER_PATH,
        where=where, columns=["CD_SUBDIST", "NM_SUBDIST"],
    )
    df = gdf_f[["CD_SUBDIST", "NM_SUBDIST"]].drop_duplicates().sort_values("NM_SUBDIST")
    if df.empty:
        return [], None
    return [{"label": r["NM_SUBDIST"], "value": r["CD_SUBDIST"]} for _, r in df.iterrows()], None


# Mapa + KPIs
@app.callback(
    Output("mapa", "figure"),
    Output("kpi-setores", "children"),
    Output("kpi-municipios", "children"),
    Output("kpi-uf", "children"),
    Input("dropdown-uf", "value"),
    Input("dropdown-mun", "value"),
    Input("dropdown-dist", "value"),
    Input("dropdown-subdist", "value"),
    Input("dropdown-situacao", "value"),
)
def atualizar_mapa(cd_uf, cd_mun, cd_dist, cd_subdist, cd_sit):
    if not cd_uf:
        return px.choropleth_map(), "—", "—", "—"

    # Lê só o necessário do disco
    zoom = 6
    if cd_mun:    zoom = 9
    if cd_dist:   zoom = 10
    if cd_subdist: zoom = 11

    gdf_filtrado = ler_uf(cd_uf, cd_mun, cd_dist, cd_subdist)

    if gdf_filtrado.empty:
        nome_uf = df_ufs.loc[df_ufs["cd_uf"] == cd_uf, "nm_uf"].values[0]
        return px.choropleth_map(), "0", "0", nome_uf

    # Filtro de situação
    if cd_sit == "urbana":
        gdf_filtrado = gdf_filtrado[gdf_filtrado["CD_SIT"].isin(["1", "2", "3", "4"])]
    elif cd_sit == "rural":
        gdf_filtrado = gdf_filtrado[gdf_filtrado["CD_SIT"].isin(["5", "6", "7", "8", "9"])]

    if gdf_filtrado.empty:
        nome_uf = df_ufs.loc[df_ufs["cd_uf"] == cd_uf, "nm_uf"].values[0]
        return px.choropleth_map(), "0", "0", nome_uf

    # Centroide e reprojeção
    gdf_proj = gdf_filtrado.to_crs(epsg=5880)
    centroide = gdf_proj.geometry.centroid.to_crs(epsg=4326)
    centro = {"lat": centroide.y.mean(), "lon": centroide.x.mean()}

    gdf_plot = gdf_filtrado.to_crs(epsg=4326).reset_index(drop=True)
    gdf_plot["geometry"] = gdf_plot.geometry.simplify(0.001)

    fig = px.choropleth_map(
        gdf_plot,
        geojson=gdf_plot.__geo_interface__,
        locations=gdf_plot.index,
        color_discrete_sequence=["steelblue"],
        map_style="carto-positron",
        zoom=zoom,
        center=centro,
        opacity=0.4,
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    total_setores    = f"{len(gdf_plot):,}".replace(",", ".")
    total_municipios = f"{gdf_plot['CD_MUN'].nunique():,}".replace(",", ".")
    nome_uf          = df_ufs.loc[df_ufs["cd_uf"] == cd_uf, "nm_uf"].values[0]

    return fig, total_setores, total_municipios, nome_uf


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)