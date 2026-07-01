import os
import gdown
import zipfile
import geopandas as gpd
import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html
from sqlalchemy import create_engine

# --- Conexão PostgreSQL ---
engine = create_engine(os.environ.get("DATABASE_URL"))

# --- Carrega shapefile completo uma vez ---
SHAPEFILE_PATH = "BR_setores_CD2022.shp"
GDRIVE_ID = ""
def carregar_shapefile():
    if not os.path.exists(SHAPEFILE_PATH):
        print("Baixando shapefile do Google Drive...")
        gdown.download(id=GDRIVE_ID, output="shapefile.zip", quiet=False)
        with zipfile.ZipFile("shapefile.zip", "r") as z:
            z.extractall(".")
        os.remove("shapefile.zip")
        print("Pronto!")
    return gpd.read_file(SHAPEFILE_PATH)

gdf = carregar_shapefile()

# --- Busca lista de UFs do banco ---
df_ufs = pd.read_sql(
    'SELECT DISTINCT cd_uf, nm_uf FROM public."IBGE_agregados_por_setores_basico" ORDER BY nm_uf',
    engine,
)
filtro_uf = [
    {"label": row["nm_uf"], "value": row["cd_uf"]} for _, row in df_ufs.iterrows()
]

# Situação fixa (padrão IBGE)
filtro_situacao = [
    {"label": "Urbana", "value": "urbana"},
    {"label": "Rural", "value": "rural"},
]

app = Dash(__name__)

CARD_STYLE = {
    "backgroundColor": "white",
    "borderRadius": "12px",
    "padding": "20px",
    "boxShadow": "0 0 0 2px rgba(13, 43, 85, 0.1)",
    "display": "flex",
    "flexDirection": "column",
    "rowGap": "6px",
    "columnGap": "6px",
    "fontFamily": '"DM Sans", sans-serif',
    "position": "relative",
    "overflow": "hidden",
    "transition": "transform 0.18s ease, box-shadow 0.18s ease",
}

DROPDOWN_STYLE = {"width": "200px", "fontSize": "13px"}


def kpi_card(card_id, titulo, subtitulo, cor_borda="rgb(21, 101, 192)"):
    style = CARD_STYLE.copy()
    style["borderLeft"] = f"5px solid {cor_borda}"
    return html.Div(
        style=style,
        children=[
            html.Span(
                titulo.upper(),
                style={"fontSize": "12px", "color": "#888", "fontWeight": "bold"},
            ),
            html.H2(id=card_id, style={"margin": "0", "color": cor_borda}),
            html.P(
                subtitulo, style={"margin": "0", "fontSize": "13px", "color": "#888"}
            ),
        ],
    )


app.layout = html.Div(
    style={"backgroundColor": "#f4f6f8", "minHeight": "100vh", "fontFamily": "Arial"},
    children=[
        # --- CABEÇALHO ---
        html.Div(
            style={
                "backgroundColor": "white",
                "padding": "15px 30px",
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "boxShadow": "0 1px 3px rgba(0,0,0,0.1)",
            },
            children=[
                html.Div(
                    [
                        html.H2(
                            "Dashboard IBGE — Setores Censitários",
                            style={"margin": "0", "color": "#1a2b4c"},
                        ),
                        html.P(
                            "CENSO 2022 · ANÁLISE GEOESPACIAL",
                            style={"margin": "0", "color": "#888", "fontSize": "12px"},
                        ),
                    ]
                ),
            ],
        ),
        # --- FILTROS ---
        html.Div(
            style={
                "display": "flex",
                "gap": "15px",
                "alignItems": "center",
                "flexWrap": "wrap",
                "padding": "15px 30px",
                "backgroundColor": "white",
                "marginTop": "2px",
                "boxShadow": "0 1px 3px rgba(0,0,0,0.05)",
            },
            children=[
                html.Span(
                    "FILTROS",
                    style={"fontWeight": "bold", "color": "#888", "fontSize": "12px"},
                ),
                dcc.Dropdown(
                    id="dropdown-uf",
                    options=filtro_uf,
                    value=df_ufs["cd_uf"].iloc[0],
                    clearable=False,
                    placeholder="UF",
                    style=DROPDOWN_STYLE,
                ),
                dcc.Dropdown(
                    id="dropdown-mun",
                    options=[],
                    value=None,
                    clearable=True,
                    placeholder="Município",
                    style=DROPDOWN_STYLE,
                ),
                dcc.Dropdown(
                    id="dropdown-dist",
                    options=[],
                    value=None,
                    clearable=True,
                    placeholder="Distrito",
                    style=DROPDOWN_STYLE,
                ),
                dcc.Dropdown(
                    id="dropdown-subdist",
                    options=[],
                    value=None,
                    clearable=True,
                    placeholder="Subdistrito",
                    style=DROPDOWN_STYLE,
                ),
                dcc.Dropdown(
                    id="dropdown-situacao",
                    options=filtro_situacao,
                    value=None,
                    clearable=True,
                    placeholder="Situação",
                    style={"width": "150px", "fontSize": "13px"},
                ),
            ],
        ),
        # --- CONTEÚDO: KPIs + MAPA ---
        html.Div(
            style={
                "display": "flex",
                "gap": "20px",
                "padding": "20px 30px",
                "alignItems": "stretch",
            },
            children=[
                # Coluna de KPIs
                html.Div(
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "gap": "20px",
                        "width": "280px",
                        "flexShrink": "0",
                    },
                    children=[
                        kpi_card(
                            "kpi-uf",
                            "UF Selecionada",
                            "Filtro ativo",
                            "rgb(230, 126, 34)",
                        ),
                        kpi_card(
                            "kpi-setores",
                            "Total de Setores",
                            "Setores censitários ativos",
                            "rgb(21, 101, 192)",
                        ),
                        kpi_card(
                            "kpi-municipios",
                            "Total de Municípios",
                            "Com registros ativos",
                            "rgb(46, 139, 87)",
                        ),
                    ],
                ),
                # Card do mapa
                html.Div(
                    style={**CARD_STYLE, "flex": "1", "padding": "20px"},
                    children=[
                        html.H4(
                            "Mapa de Setores Censitários", style={"margin": "0 0 5px 0"}
                        ),
                        html.P(
                            "Distribuição geográfica conforme filtros selecionados",
                            style={
                                "margin": "0 0 15px 0",
                                "color": "#888",
                                "fontSize": "13px",
                            },
                        ),
                        dcc.Graph(id="mapa", style={"height": "70vh"}),
                    ],
                ),
            ],
        ),
    ],
)


# --- CALLBACK: UF → Município ---
@app.callback(
    Output("dropdown-mun", "options"),
    Output("dropdown-mun", "value"),
    Input("dropdown-uf", "value"),
)
def atualizar_municipios(cd_uf):
    if not cd_uf:
        return [], None
    df = (
        gdf[gdf["CD_UF"] == cd_uf][["CD_MUN", "NM_MUN"]]
        .drop_duplicates()
        .sort_values("NM_MUN")
    )
    opcoes = [{"label": r["NM_MUN"], "value": r["CD_MUN"]} for _, r in df.iterrows()]
    return opcoes, None


# --- CALLBACK: Município → Distrito ---
@app.callback(
    Output("dropdown-dist", "options"),
    Output("dropdown-dist", "value"),
    Input("dropdown-uf", "value"),
    Input("dropdown-mun", "value"),
)
def atualizar_distritos(cd_uf, cd_mun):
    if not cd_uf:
        return [], None
    filtrado = gdf[gdf["CD_UF"] == cd_uf]
    if cd_mun:
        filtrado = filtrado[filtrado["CD_MUN"] == cd_mun]
    df = filtrado[["CD_DIST", "NM_DIST"]].drop_duplicates().sort_values("NM_DIST")
    if df.empty:
        return [], None
    opcoes = [{"label": r["NM_DIST"], "value": r["CD_DIST"]} for _, r in df.iterrows()]
    return opcoes, None


# --- CALLBACK: Distrito → Subdistrito ---
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
    filtrado = gdf[gdf["CD_UF"] == cd_uf]
    if cd_mun:
        filtrado = filtrado[filtrado["CD_MUN"] == cd_mun]
    if cd_dist:
        filtrado = filtrado[filtrado["CD_DIST"] == cd_dist]
    df = (
        filtrado[["CD_SUBDIST", "NM_SUBDIST"]]
        .drop_duplicates()
        .sort_values("NM_SUBDIST")
    )
    if df.empty:
        return [], None
    opcoes = [
        {"label": r["NM_SUBDIST"], "value": r["CD_SUBDIST"]} for _, r in df.iterrows()
    ]
    return opcoes, None


# --- CALLBACK: Mapa + KPIs ---
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

    filtrado = gdf[gdf["CD_UF"] == cd_uf]
    zoom = 6

    if cd_mun:
        filtrado = filtrado[filtrado["CD_MUN"] == cd_mun]
        zoom = 9
    if cd_dist:
        filtrado = filtrado[filtrado["CD_DIST"] == cd_dist]
        zoom = 10
    if cd_subdist:
        filtrado = filtrado[filtrado["CD_SUBDIST"] == cd_subdist]
        zoom = 11
    if cd_sit == "urbana":
        filtrado = filtrado[filtrado["CD_SIT"].isin(["1", "2", "3", "4"])]
    elif cd_sit == "rural":
        filtrado = filtrado[filtrado["CD_SIT"].isin(["5", "6", "7", "8", "9"])]

    # Sem dados para essa combinação de filtros
    if filtrado.empty:
        fig = px.choropleth_map()
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        nome_uf = df_ufs.loc[df_ufs["cd_uf"] == cd_uf, "nm_uf"].values[0]
        return fig, "0", "0", nome_uf

    filtrado = filtrado.copy()

    gdf_proj = filtrado.to_crs(epsg=5880)
    centroide = gdf_proj.geometry.centroid.to_crs(epsg=4326)
    centro = {"lat": centroide.y.mean(), "lon": centroide.x.mean()}

    gdf_plot = filtrado.to_crs(epsg=4326).reset_index(drop=True)
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

    total_setores = f"{len(gdf_plot):,}".replace(",", ".")
    total_municipios = f"{gdf_plot['CD_MUN'].nunique():,}".replace(",", ".")
    nome_uf = df_ufs.loc[df_ufs["cd_uf"] == cd_uf, "nm_uf"].values[0]

    return fig, total_setores, total_municipios, nome_uf


if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)
