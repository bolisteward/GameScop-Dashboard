import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Reporte Trimestral | GameScope",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================
# 2. EXTRACCIÓN DE DATOS Y CACHÉ
# ==========================================
@st.cache_data(ttl=86400, show_spinner="Conectando con Google Sheets...")
def load_live_data():
    sheet_id = "17JCJHTfxHZIvUbNPSh3HfissUnFYulFHgAp9tI9J2qQ"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

    df = pd.read_csv(csv_url)

    df["metacritic"] = pd.to_numeric(df["metacritic"], errors="coerce")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(
        "Int64"
    )  # Int64 evita decimales (2017.0 -> 2017)
    df["ratings_count"] = pd.to_numeric(df["ratings_count"], errors="coerce")

    df["rating_scaled"] = df["rating"] * 20
    df["discrepancy"] = abs(df["metacritic"] - df["rating_scaled"])

    df = df.dropna(subset=["metacritic", "rating", "year"])
    return df


try:
    df_raw = load_live_data()
except Exception as e:
    st.error(f"Error al conectar con la base de datos de RAWG: {e}")
    st.stop()

# ==========================================
# 3. CONTEXTO Y NARRATIVA
# ==========================================
st.title("🎮 Informe Ejecutivo: Estado de la Industria de Videojuegos")
st.markdown("""
Bienvenido al panel analítico interactivo. Este reporte evalúa el estado del arte de la industria 
de los videojuegos mediante la correlación de puntuaciones de la crítica, recepción de los usuarios 
y datos históricos. **Utilice la barra lateral para ajustar el alcance del análisis.**
""")
st.markdown("---")

# ==========================================
# 4. BARRA LATERAL (FILTROS AVANZADOS)
# ==========================================
st.sidebar.header("⚙️ Parámetros del Reporte")

# Mínimo de Votos
min_votes = st.sidebar.slider("Mínimo de votos de usuarios:", 0, 5000, 200, 50)

# Filtro: Años (Dropdown con Seleccionar Todo)
all_years = sorted(df_raw["year"].unique())
select_all_years = st.sidebar.checkbox("Seleccionar todos los años", value=True)

if select_all_years:
    selected_years = all_years
else:
    selected_years = st.sidebar.multiselect(
        "Seleccione Años:", options=all_years, default=all_years[-5:]
    )

# Extraer listas únicas de plataformas y géneros para los filtros
all_platforms = sorted(list(set(", ".join(df_raw["platforms"].dropna()).split(", "))))
all_genres = sorted(list(set(", ".join(df_raw["genres"].dropna()).split(", "))))

# Filtros Categóricos
selected_platforms = st.sidebar.multiselect(
    "🎮 Filtro Plataforma (Afecta Gráficas 1, 2, 3):", options=all_platforms
)
selected_genres = st.sidebar.multiselect(
    "🎭 Filtro Género (Afecta Gráficas 2, 3, 4):", options=all_genres
)

# -- LÓGICA DE FILTRADO CRUZADO --
df_base = df_raw[
    (df_raw["ratings_count"] >= min_votes) & (df_raw["year"].isin(selected_years))
]

def filter_by_list(df, column, selected_items):
    if not selected_items:
        return df
    pattern = "|".join([f"(?i){item}" for item in selected_items])
    return df[df[column].fillna("").str.contains(pattern)]

df_plat = filter_by_list(df_base, "platforms", selected_platforms)  # Afecta 1
df_gen = filter_by_list(df_base, "genres", selected_genres)  # Afecta 4
df_both = filter_by_list(df_plat, "genres", selected_genres)  # Afecta 2 y 3

# ==========================================
# 5. BUSCADOR DE JUEGO ESPECÍFICO
# ==========================================
with st.expander(
    "🔍 Buscador de Juego Específico (Haz clic para expandir)", expanded=False
):
    game_list = ["-- Escriba o seleccione un juego --"] + sorted(
        df_raw["name"].unique()
    )
    selected_game = st.selectbox(
        "Seleccione un juego del catálogo global:", options=game_list
    )

    if selected_game != "-- Escriba o seleccione un juego --":
        game_data = df_raw[df_raw["name"] == selected_game].iloc[0]

        col_img, col_metrics1, col_metrics2 = st.columns([1, 1.5, 1.5])

        with col_img:
            if pd.notna(game_data["background_image"]):
                st.image(game_data["background_image"], width=True)
            else:
                st.info("Imagen no disponible")

        with col_metrics1:
            st.subheader(game_data["name"])
            st.write(f"**Año:** {game_data['year']}")
            st.write(f"**Desarrollador:** {game_data['developers']}")
            st.write(f"**Géneros:** {game_data['genres']}")
            st.write(f"**Plataformas:** {game_data['platforms']}")

        with col_metrics2:
            st.metric("Metacritic Score", f"{game_data['metacritic']} / 100")
            st.metric("Rating Comunidad", f"{game_data['rating']} / 5.0")
            st.metric("Total Ratings", f"{game_data['ratings_count']:,}")
            st.metric("Tiempo de Juego (Media)", f"{game_data['playtime']} hrs")

st.markdown("---")

# ==========================================
# 6. RANKING GLOBAL Y KPIs
# ==========================================
col1, col2, col3, col4 = st.columns(4)
col1.metric("Juegos Analizados (Filtro Actual)", f"{len(df_both):,}")
col2.metric("Promedio Crítica", f"{df_both['metacritic'].mean():.1f}")
col3.metric("Promedio Comunidad", f"{df_both['rating_scaled'].mean():.1f}")
if not df_both.empty:
    col4.metric(
        "Juego #1 (Actual)", df_both.loc[df_both["metacritic"].idxmax()]["name"]
    )

st.header("🏆 Top 10: Ranking de Juegos")
if not df_both.empty:
    top_10 = df_both.sort_values(
        by=["metacritic", "rating_scaled"], ascending=[False, False]
    ).head(10)
    
    st.dataframe(
        top_10[["name", "year", "metacritic", "rating", "genres", "platforms"]],
        column_config={
            "name": "Título del Juego",
            "year": "Año",
            "metacritic": st.column_config.ProgressColumn(
                "Metacritic", format="%f", min_value=0, max_value=100
            ),
            "rating": st.column_config.NumberColumn(
                "Rating Usuarios", format="%.2f ⭐"
            ),
            "genres": "Géneros",
            "platforms": "Plataformas",
        },
        hide_index=True,
        use_container_width=True,
    )
else:
    st.warning("No hay juegos que coincidan con los filtros seleccionados.")

st.markdown("---")

# ==========================================
# 7. GRÁFICA 1: CALIDAD POR GÉNERO (Usa df_plat)
# ==========================================
st.header("1. Calidad por Género")
st.markdown("**Objetivo:** Identificar qué categorías de videojuegos mantienen consistentemente los estándares de calidad más altos según la crítica (Metacritic). Esto nos permite entender qué nichos de desarrollo son los más premiados de la industria.")

genre_avg = df_plat.groupby("genres")["metacritic"].agg(["mean", "count"]).reset_index()
genre_avg = (
    genre_avg[genre_avg["count"] > 2].sort_values(by="mean", ascending=True).tail(12)
)

if not genre_avg.empty:
    fig_genres = px.bar(
        genre_avg, x='mean', y='genres', orientation='h', 
        color='mean', color_continuous_scale='Viridis',
        labels={'mean': 'Score Promedio (Metacritic)', 'genres': 'Género'},
        text='mean' 
    )
    fig_genres.update_traces(texttemplate='%{text:.1f}', textposition='outside')
    fig_genres.update_layout(uniformtext_minsize=8, uniformtext_mode='hide', margin=dict(r=50))
    st.plotly_chart(fig_genres, use_container_width=True)
    
    # Análisis dinámico
    best_genre = genre_avg.iloc[-1]['genres']
    best_genre_score = genre_avg.iloc[-1]['mean']
    st.info(f"💡 **Insight:** Bajo los filtros actuales, los juegos etiquetados como **'{best_genre}'** dominan la crítica con un puntaje promedio de **{best_genre_score:.1f}**. Este género representa el estándar de oro actual en cuanto a recepción especializada.")
else:
    st.warning("Datos insuficientes para la gráfica 1.")

# ==========================================
# 8. GRÁFICA 2: TENDENCIAS TEMPORALES (Usa df_both)
# ==========================================
st.header("2. Evolución Histórica de la Calidad")
st.markdown("**Objetivo:** Contrastar cómo ha evolucionado el score promedio a lo largo de los años en relación con el volumen de juegos producidos. Ayuda a verificar si la 'época dorada' de los videojuegos es un mito o una realidad estadística.")

yearly_stats = (
    df_both.groupby("year")
    .agg(avg_metacritic=("metacritic", "mean"), games_count=("id", "count"))
    .reset_index()
)

if not yearly_stats.empty:
    fig_trends = make_subplots(specs=[[{"secondary_y": True}]])
    fig_trends.add_trace(
        go.Scatter(
            x=yearly_stats["year"], y=yearly_stats["avg_metacritic"],
            name="Score Promedio", line=dict(color="orange", width=3),
        ), secondary_y=False,
    )
    fig_trends.add_trace(
        go.Bar(
            x=yearly_stats["year"], y=yearly_stats["games_count"],
            name="Volumen de Lanzamientos", opacity=0.3, marker_color="blue",
        ), secondary_y=True,
    )
    fig_trends.update_layout(hovermode="x unified")
    st.plotly_chart(fig_trends, use_container_width=True)
    
    # Análisis dinámico
    best_year_row = yearly_stats.loc[yearly_stats["avg_metacritic"].idxmax()]
    st.success(f"📈 **Conclusión:** El año **{int(best_year_row['year'])}** representa un pico histórico en calidad, con un score promedio de **{best_year_row['avg_metacritic']:.1f}** basado en **{int(best_year_row['games_count'])}** títulos registrados bajo este filtro.")
else:
    st.warning("Datos insuficientes para la gráfica 2.")

# ==========================================
# 9. GRÁFICA 3: CRÍTICA VS COMUNIDAD (Usa df_both)
# ==========================================
st.header("3. Matriz de Consenso: Crítica vs Comunidad")
st.markdown("**Objetivo:** Explorar la polarización de la industria. La línea punteada representa el 'consenso absoluto'. Los puntos alejados de esta línea revelan la desconexión entre la prensa especializada y los jugadores. El tamaño del círculo representa la cantidad de votos.")

if not df_both.empty:
    fig_scatter = px.scatter(
        df_both, x="metacritic", y="rating_scaled",
        size="ratings_count", hover_name="name",
        color="discrepancy", color_continuous_scale="Reds",
        labels={
            "rating_scaled": "Rating Comunidad (Escalado 0-100)",
            "metacritic": "Score Crítica (Metacritic)",
            "discrepancy": "Grado de Discrepancia",
        },
    )
    fig_scatter.add_shape(
        type="line", x0=20, y0=20, x1=100, y1=100, line=dict(color="gray", dash="dash")
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    # Análisis dinámico y Outliers
    overrated = df_both[(df_both["metacritic"] > 80) & (df_both["rating_scaled"] < 65)].head(1)
    cult_classic = df_both[(df_both["metacritic"] < 75) & (df_both["rating_scaled"] > 80)].head(1)
    
    col_out1, col_out2 = st.columns(2)
    with col_out1:
        st.error("📉 **Desconexión (Aclamados por crítica, baja recepción de usuarios)**")
        if not overrated.empty:
            game = overrated.iloc[0]
            st.write(f"Ejemplo: **{game['name']}** (Crítica: {game['metacritic']} vs Usuarios: {game['rating_scaled']:.1f})")
        else:
            st.write("No hay valores atípicos notables en este cuadrante.")
            
    with col_out2:
        st.warning("💎 **Títulos de Culto (Ignorados por crítica, amados por usuarios)**")
        if not cult_classic.empty:
            game = cult_classic.iloc[0]
            st.write(f"Ejemplo: **{game['name']}** (Crítica: {game['metacritic']} vs Usuarios: {game['rating_scaled']:.1f})")
        else:
             st.write("No hay valores atípicos notables en este cuadrante.")
else:
    st.warning("Datos insuficientes para la gráfica 3.")

# ==========================================
# 10. GRÁFICA 4: ECOSISTEMA DE PLATAFORMAS (Usa df_gen)
# ==========================================
st.header("4. Plataformas Dominantes")
st.markdown("**Objetivo:** Cuantificar qué plataformas de hardware o tiendas concentran el mayor volumen de títulos de excelencia. Use el umbral a continuación para definir qué considera un juego 'Bien Valorado'.")

umbral_excelencia = st.slider(
    "Definir Umbral de Excelencia (Metacritic):", 70, 95, 80, 5
)

df_excelentes = df_gen[df_gen["metacritic"] >= umbral_excelencia].copy()
if not df_excelentes.empty:
    df_excelentes["platforms"] = df_excelentes["platforms"].astype(str)
    plataformas_expandidas = df_excelentes["platforms"].str.split(", ").explode()
    platform_counts = plataformas_expandidas.value_counts().reset_index()
    platform_counts.columns = ["Plataforma", "Cantidad_Juegos"]
    platform_counts = platform_counts.head(15).sort_values(
        by="Cantidad_Juegos", ascending=True
    )

    fig_plataformas = px.bar(
        platform_counts, x='Cantidad_Juegos', y='Plataforma', orientation='h',
        color='Cantidad_Juegos', color_continuous_scale='Purples',
        labels={'Cantidad_Juegos': 'Títulos Excelentes'},
        text='Cantidad_Juegos'
    )
    
    fig_plataformas.update_traces(texttemplate='%{text}', textposition='outside')
    fig_plataformas.update_layout(margin=dict(r=50))
    st.plotly_chart(fig_plataformas, use_container_width=True)
    
    # Análisis dinámico
    top_plat = platform_counts.iloc[-1]['Plataforma']
    top_plat_count = platform_counts.iloc[-1]['Cantidad_Juegos']
    st.info(f"🏆 **Recomendación de Hardware:** El ecosistema de **{top_plat}** lidera actualmente con **{top_plat_count}** juegos superando el umbral de {umbral_excelencia} puntos, convirtiéndola en la plataforma con el catálogo más robusto según estos parámetros.")
else:
    st.warning(
        "No se encontraron juegos que superen el umbral con los filtros actuales."
    )

st.markdown("---")
st.caption("GameScope Pipeline Automático | Datos provistos por RAWG API")