import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Reporte Trimestral | GameScope",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. EXTRACCIÓN DE DATOS Y CACHÉ
# ==========================================
# Usamos cache_data con un Time To Live (ttl) de 1 día (86400 segundos).
# Esto asegura rendimiento, pero mantiene el reporte fresco.
@st.cache_data(ttl=86400, show_spinner="Conectando con Google Sheets y descargando matriz de datos...")
def load_live_data():
    # URL pública del Google Sheet convertida a formato CSV exportable
    sheet_id = "17JCJHTfxHZIvUbNPSh3HfissUnFYulFHgAp9tI9J2qQ"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    df = pd.read_csv(csv_url)
    
    # Limpieza y conversión de tipos
    df['metacritic'] = pd.to_numeric(df['metacritic'], errors='coerce')
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    df['ratings_count'] = pd.to_numeric(df['ratings_count'], errors='coerce')
    
    # Atributos derivados para el análisis
    df['rating_scaled'] = df['rating'] * 20 # Escalar de 0-5 a 0-100 para comparar con Metacritic
    df['discrepancy'] = abs(df['metacritic'] - df['rating_scaled']) # Medir diferencia crítica vs usuarios
    
    # Filtrar datos inválidos críticos
    df = df.dropna(subset=['metacritic', 'rating'])
    
    return df

try:
    df_raw = load_live_data()
except Exception as e:
    st.error(f"Error al conectar con la base de datos de RAWG: {e}")
    st.stop()

# ==========================================
# 3. CONTEXTO Y NARRATIVA (HEADER)
# ==========================================
st.title("🎮 Informe Ejecutivo: Estado de la Industria de Videojuegos")
st.markdown("---")

st.markdown("""
### 📖 Contexto del Reporte
**Analista:** María (Equipo de Contenido y Cultura Gamer)  
**Objetivo:** Este informe trimestral interactivo identifica las tendencias de calidad por género, la evolución histórica de la industria y la polarización de opiniones entre la crítica especializada (Metacritic) y la comunidad de jugadores. Los insights aquí generados dictarán la línea editorial de las próximas publicaciones.
""")

# ==========================================
# 4. BARRA LATERAL (PARÁMETROS DEL REPORTE)
# ==========================================
st.sidebar.header("⚙️ Parámetros del Reporte")
st.sidebar.markdown("Ajuste los filtros para recalcular las narrativas y gráficas en tiempo real.")

min_votes = st.sidebar.slider(
    "Filtrar por relevancia (Mínimo de votos):", 
    min_value=0, max_value=5000, value=200, step=50,
    help="Excluye juegos de nicho o con muy pocas valoraciones para evitar sesgos estadísticos."
)

decades_available = sorted(df_raw['decade'].dropna().unique())
selected_decades = st.sidebar.multiselect(
    "Décadas en análisis:", 
    options=decades_available, 
    default=decades_available
)

# Aplicar filtros
df = df_raw[(df_raw['ratings_count'] >= min_votes) & (df_raw['decade'].isin(selected_decades))]

# ==========================================
# 5. KPIs DE ALTO NIVEL
# ==========================================
st.markdown("### 📊 Visión General del Catálogo")
col1, col2, col3, col4 = st.columns(4)

col1.metric("Juegos Analizados", f"{len(df):,}")
col2.metric("Promedio Crítica (Metacritic)", f"{df['metacritic'].mean():.1f} / 100")
col3.metric("Promedio Comunidad (Escalado)", f"{df['rating_scaled'].mean():.1f} / 100")
top_game = df.loc[df['metacritic'].idxmax()]['name']
col4.metric("Juego Mejor Calificado (Crítica)", top_game)

st.markdown("---")

# ==========================================
# 6. TAREA 1: CALIDAD POR GÉNERO
# ==========================================
st.header("1. ¿Dónde reside la calidad consistente? (Análisis por Género)")
st.markdown("Para guiar los próximos artículos de recomendaciones, evaluamos qué géneros garantizan una mayor satisfacción crítica.")

# Lógica de datos
genre_avg = df.groupby('genres')['metacritic'].agg(['mean', 'count']).reset_index()
genre_avg = genre_avg[genre_avg['count'] > 5] # Excluir géneros con muy pocos juegos
genre_avg = genre_avg.sort_values(by='mean', ascending=True).tail(12)

# Gráfico
fig_genres = px.bar(
    genre_avg, x='mean', y='genres', orientation='h', 
    color='mean', color_continuous_scale='Viridis',
    labels={'mean': 'Score Promedio (Metacritic)', 'genres': 'Género'},
    title="Top Géneros por Score de Metacritic"
)
st.plotly_chart(fig_genres, use_container_width=True)

# Resultados dinámicos (Insight narrativo)
best_genre = genre_avg.iloc[-1]['genres']
best_genre_score = genre_avg.iloc[-1]['mean']
st.info(f"💡 **Insight Editorial:** Actualmente, los títulos catalogados como **'{best_genre}'** dominan la crítica con un promedio de **{best_genre_score:.1f}** puntos. El equipo editorial debería considerar reportajes centrados en este género para atraer a la audiencia más exigente.")

st.markdown("---")

# ==========================================
# 7. TAREA 2: TENDENCIAS TEMPORALES
# ==========================================
st.header("2. La 'Época Dorada': Evolución de la Calidad Histórica")
st.markdown("La nostalgia es un fuerte motivador de clics. ¿Pero los juegos antiguos eran realmente mejores, o la industria moderna ha superado sus propios estándares?")

# Lógica de datos
yearly_stats = df.groupby('year').agg(
    avg_metacritic=('metacritic', 'mean'),
    games_count=('id', 'count')
).reset_index()
yearly_stats = yearly_stats[yearly_stats['games_count'] > 3] # Limpiar años anómalos

# Gráfico con doble eje Y (Plotly Express base, ajustado con Graph Objects para más profesionalismo)
import plotly.graph_objects as go
from plotly.subplots import make_subplots

fig_trends = make_subplots(specs=[[{"secondary_y": True}]])
fig_trends.add_trace(
    go.Scatter(x=yearly_stats['year'], y=yearly_stats['avg_metacritic'], name="Promedio Metacritic", mode='lines+markers', line=dict(color='orange', width=3)),
    secondary_y=False,
)
fig_trends.add_trace(
    go.Bar(x=yearly_stats['year'], y=yearly_stats['games_count'], name="Volumen de Lanzamientos", opacity=0.3, marker_color='blue'),
    secondary_y=True,
)
fig_trends.update_layout(title="Evolución Histórica: Calidad Crítica vs Volumen de Producción", hovermode="x unified")
fig_trends.update_yaxes(title_text="Score Metacritic", secondary_y=False)
fig_trends.update_yaxes(title_text="Cantidad de Juegos", secondary_y=True)

st.plotly_chart(fig_trends, use_container_width=True)

# Resultados dinámicos (Insight narrativo)
best_year_row = yearly_stats.loc[yearly_stats['avg_metacritic'].idxmax()]
st.success(f"📈 **Conclusión Histórica:** Los datos muestran que el año **{int(best_year_row['year'])}** representa un pico histórico en calidad, con un score promedio de **{best_year_row['avg_metacritic']:.1f}** basado en **{int(best_year_row['games_count'])}** títulos analizados. Proponemos un artículo especial titulado: *'Retrospectiva: Por qué {int(best_year_row['year'])} cambió la industria'*.")

st.markdown("---")

# ==========================================
# 8. TAREA 3: DIVISIÓN COMUNIDAD VS CRÍTICA
# ==========================================
st.header("3. Obras Maestras Incomprendidas y Placeres Culpables")
st.markdown("Comparando Metacritic con las votaciones de la comunidad, descubrimos la polarización. Aquellos títulos alejados de la línea diagonal representan discrepancias que siempre generan debate orgánico en redes sociales.")

# Gráfico
fig_scatter = px.scatter(
    df, x='metacritic', y='rating_scaled', 
    size='ratings_count', hover_name='name', color='discrepancy',
    color_continuous_scale='Reds',
    labels={'rating_scaled': 'Rating Comunidad (Escalado 0-100)', 'metacritic': 'Score Crítica (Metacritic)', 'discrepancy': 'Grado de Discrepancia'},
    title="Matriz de Consenso: Crítica vs Comunidad"
)
fig_scatter.add_shape(type='line', x0=20, y0=20, x1=100, y1=100, line=dict(color='gray', dash='dash'), name="Línea de Consenso")
st.plotly_chart(fig_scatter, use_container_width=True)

# Lógica de Outliers (Dinámicos)
most_divisive = df.loc[df['discrepancy'].idxmax()]
overrated_by_critics = df[(df['metacritic'] > 85) & (df['rating_scaled'] < 70)].head(1)
loved_by_fans = df[(df['metacritic'] < 75) & (df['rating_scaled'] > 85)].head(1)

col_out1, col_out2 = st.columns(2)
with col_out1:
    st.error("🔥 **Favoritos de la Crítica (Rechazados por usuarios)**")
    if not overrated_by_critics.empty:
        game = overrated_by_critics.iloc[0]
        st.write(f"**{game['name']}** (Crítica: {game['metacritic']} | Usuarios: {game['rating_scaled']:.1f})")
    else:
        st.write("Con los filtros actuales, no hay un consenso dividido en este cuadrante.")

with col_out2:
    st.warning("💎 **Títulos de Culto (Amados por usuarios, ignorados por la crítica)**")
    if not loved_by_fans.empty:
        game = loved_by_fans.iloc[0]
        st.write(f"**{game['name']}** (Crítica: {game['metacritic']} | Usuarios: {game['rating_scaled']:.1f})")
    else:
         st.write("Con los filtros actuales, no hay un consenso dividido en este cuadrante.")

st.markdown("---")
st.caption("GameScope Pipeline Automático | Datos provistos por RAWG API | Analítica Trimestral Interna")



# ==========================================
# 9. TAREA 4: ECOSISTEMA DE PLATAFORMAS
# ==========================================
st.header("4. El Ecosistema de la Calidad: Plataformas Dominantes")
st.markdown("¿Qué consola o entorno garantiza un catálogo de excelencia? Analizamos el volumen de juegos 'bien valorados' disponibles en cada plataforma.")

# Filtro interactivo específico para esta sección
umbral_excelencia = st.slider(
    "Definir 'Título Bien Valorado' (Umbral Metacritic):", 
    min_value=70, max_value=95, value=80, step=5,
    help="Define a partir de qué puntaje un juego es considerado 'bien valorado' o de excelencia."
)

# Lógica de datos: Filtrar, separar listas separadas por coma y contar (Explode)
# 1. Filtrar los que superan el umbral
df_excelentes = df[df['metacritic'] >= umbral_excelencia].copy()

# 2. Manejar nulos y separar la cadena de texto de las plataformas
df_excelentes = df_excelentes.dropna(subset=['platforms'])
df_excelentes['platforms'] = df_excelentes['platforms'].astype(str)

# 3. Separar por coma y expandir las filas (explode)
# Ej: Fila 1 ["PC, PS5"] se convierte en Fila 1 ["PC"], Fila 2 ["PS5"]
plataformas_expandidas = df_excelentes['platforms'].str.split(', ').explode()

# 4. Contar la frecuencia de cada plataforma y tomar el Top 15
platform_counts = plataformas_expandidas.value_counts().reset_index()
platform_counts.columns = ['Plataforma', 'Cantidad_Juegos']
platform_counts = platform_counts.head(15).sort_values(by='Cantidad_Juegos', ascending=True)

# Gráfico
fig_plataformas = px.bar(
    platform_counts, 
    x='Cantidad_Juegos', 
    y='Plataforma', 
    orientation='h',
    color='Cantidad_Juegos', 
    color_continuous_scale='Purples', # Un color distinto para separar temáticamente
    labels={'Cantidad_Juegos': 'Cantidad de Títulos', 'Plataforma': 'Plataforma'},
    title=f"Top Plataformas con más juegos 'Bien Valorados' (Metacritic >= {umbral_excelencia})"
)
st.plotly_chart(fig_plataformas, use_container_width=True)

# Resultados dinámicos (Insight narrativo)
if not platform_counts.empty:
    top_plat = platform_counts.iloc[-1]['Plataforma'] # El último porque lo ordenamos ascendente para el gráfico
    top_plat_count = platform_counts.iloc[-1]['Cantidad_Juegos']
    
    st.info(f"🏆 **Recomendación de Hardware:** Para los títulos con un score mayor a **{umbral_excelencia}**, la plataforma dominante es **{top_plat}**, la cual concentra un total de **{top_plat_count}** juegos excepcionales. Esto confirma que el ecosistema de {top_plat} es el más robusto para jugadores exigentes en las décadas seleccionadas.")
else:
    st.warning("No se encontraron juegos que cumplan con los filtros actuales en ninguna plataforma.")