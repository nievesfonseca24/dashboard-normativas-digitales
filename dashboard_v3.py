import streamlit as st
import pandas as pd
import plotly.express as px
import networkx as nx
import plotly.graph_objects as go
from pathlib import Path
import numpy as np
import os
from datetime import datetime

# Set page config once at the beginning
st.set_page_config(
    page_title="Dashboard de Normativas Digitales", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS for better styling
st.markdown("""
<style>
    .main .block-container {padding-top: 2rem;}
    .stTabs [data-baseweb="tab-panel"] {padding-top: 1rem;}
    div[data-testid="stSidebarNav"] {background-color: #f8f9fa;}
    div[data-testid="stSidebar"] {background-color: #f8f9fa;}
    .st-emotion-cache-16idsys p {margin-bottom: 0.5rem;}
    .normativa-card {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 1rem;
        margin-bottom: 1rem;
        border-left: 4px solid #3498DB;
    }
    .metric-card {
        background-color: #f1f3f9;
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# Configuración de la página principal
st.title("📜 Dashboard de Normativas Digitales en la UE")

# Path configuration with file uploader option
def get_data_path():
    # Opción para cargar archivo propio
    uploaded_file = st.sidebar.file_uploader("Cargar archivo Excel", type=['xlsx'])
    if uploaded_file is not None:
        return uploaded_file
    
    # Path por defecto (intentar usar una ruta relativa)
    default_path = Path("data/modulo3.xlsx")
    if default_path.exists():
        return default_path
    
    # Fallback a la ruta absoluta original
    return Path(r"C:\Users\lujan\Desktop\PYTHON\normativa\Nueva carpeta\modulo3.xlsx")

# Mensaje de última actualización de datos
def show_last_updated(data):
    if "Fecha Actualización" in data["Normativa"].columns:
        last_update = data["Normativa"]["Fecha Actualización"].max()
        st.sidebar.caption(f"Última actualización: {last_update}")
    else:
        st.sidebar.caption(f"Última actualización: {datetime.now().strftime('%d/%m/%Y')}")

# Load Excel file with better caching and error handling
@st.cache_data(ttl=3600)
def load_excel_data(file_path):
    try:
        if isinstance(file_path, Path):
            if not file_path.exists():
                st.error(f"El archivo no existe en la ruta: {file_path}")
                return None
            xls = pd.ExcelFile(file_path)
        else:
            # Si es un archivo subido por el usuario
            xls = pd.ExcelFile(file_path)
            
        # Verificar que las hojas necesarias existen
        required_sheets = ["Normativa", "Relaciones"]
        missing_sheets = [sheet for sheet in required_sheets if sheet not in xls.sheet_names]
        
        if missing_sheets:
            st.error(f"El archivo no contiene las siguientes hojas necesarias: {', '.join(missing_sheets)}")
            return None
            
        data = {
            "Normativa": xls.parse("Normativa"),
            "Relaciones": xls.parse("Relaciones")
        }
        
        # Data preprocessing
        data["Normativa"]["Fecha Entrada en Vigor"] = pd.to_datetime(
            data["Normativa"].get("Fecha Entrada en Vigor"), errors='coerce'
        )
        data["Normativa"].dropna(subset=["Fecha Entrada en Vigor"], inplace=True)
        data["Normativa"]["Año"] = data["Normativa"]["Fecha Entrada en Vigor"].dt.year
        
        # Asegurar que tenemos ID como string para evitar problemas al mapear
        data["Normativa"]["ID"] = data["Normativa"]["ID"].astype(str)
        if not data["Relaciones"].empty:
            data["Relaciones"]["ID_Normativa_1"] = data["Relaciones"]["ID_Normativa_1"].astype(str)
            data["Relaciones"]["ID_Normativa_2"] = data["Relaciones"]["ID_Normativa_2"].astype(str)
            
        return data
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return None

# Load data with better error handling
try:
    file_path = get_data_path()
    datos = load_excel_data(file_path)
    
    if datos is None:
        st.error("No se pudieron cargar los datos. Por favor, revisa el archivo Excel.")
        st.stop()
        
    df_normativas = datos["Normativa"]
    df_relaciones = datos["Relaciones"]
    
    # Verificar datos críticos
    if df_normativas.empty:
        st.error("No hay datos de normativas en el archivo.")
        st.stop()
        
    # Crear mapeo de IDs a nombres
    id_to_nombre = dict(zip(df_normativas["ID"], df_normativas["Nombre"]))
    
    # Procesar relaciones
    if not df_relaciones.empty:
        df_relaciones["Normativa_1_Nombre"] = df_relaciones["ID_Normativa_1"].map(id_to_nombre)
        df_relaciones["Normativa_2_Nombre"] = df_relaciones["ID_Normativa_2"].map(id_to_nombre)
    
    # Mostrar info de actualización
    show_last_updated(datos)
    
except Exception as e:
    st.error(f"Error inesperado: {e}")
    st.stop()

# Sidebar filters with better organization
with st.sidebar:
    st.header("🔎 Filtros")
    
    # Creamos un contenedor para los filtros
    filter_container = st.container()
    
    with filter_container:
        # Filtro de años con mejor manejo de valores extremos
        min_year, max_year = int(df_normativas["Año"].min()), int(df_normativas["Año"].max())
        years_selected = st.slider("Rango de Años", min_year, max_year, (min_year, max_year))
        
        # Filtro de bloque temático con opción "Todos"
        all_bloques = sorted(df_normativas["Bloque Temático"].unique())
        bloque_seleccionado = st.multiselect(
            "Bloque Temático", 
            all_bloques,
            default=all_bloques
        )
        
        # Filtro de estado
        if "Estado" in df_normativas.columns:
            estados = sorted(df_normativas["Estado"].unique())
            estado_seleccionado = st.multiselect(
                "Estado", 
                estados,
                default=estados
            )
        else:
            estado_seleccionado = None
            
        # Búsqueda mejorada
        search_term = st.text_input("Buscar por nombre o descripción:")
        
        # Botón para resetear filtros
        if st.button("Resetear Filtros"):
            st.rerun()

    # Añadir información o ayuda
    with st.expander("ℹ️ Ayuda"):
        st.markdown("""
        **Cómo usar este dashboard:**
        - Usa los filtros para encontrar normativas específicas
        - Explora las relaciones entre normativas en el gráfico de red
        - Consulta la evolución temporal de las normativas
        """)

# Apply all filters with improved logic
filter_conditions = [
    (df_normativas["Bloque Temático"].isin(bloque_seleccionado)),
    (df_normativas["Año"] >= years_selected[0]),
    (df_normativas["Año"] <= years_selected[1])
]

# Añadir filtro de estado si existe
if estado_seleccionado is not None and "Estado" in df_normativas.columns:
    filter_conditions.append(df_normativas["Estado"].isin(estado_seleccionado))

# Combinar condiciones de filtro
df_filtrado = df_normativas.copy()
for condition in filter_conditions:
    df_filtrado = df_filtrado[condition]

# Aplicar búsqueda de texto mejorada
if search_term:
    search_columns = ["Nombre", "Descripción"] if "Descripción" in df_filtrado.columns else ["Nombre"]
    search_mask = pd.DataFrame(False, index=df_filtrado.index, columns=['match'])
    
    for col in search_columns:
        if col in df_filtrado.columns:
            col_match = df_filtrado[col].astype(str).str.contains(search_term, case=False, na=False)
            search_mask['match'] = search_mask['match'] | col_match
    
    df_filtrado = df_filtrado[search_mask['match']]

# Crear tabs para mejor organización
tab1, tab2, tab3 = st.tabs(["📊 Resumen", "📈 Evolución Temporal", "🔗 Relaciones"])

# Tab 1: Panel de resumen
with tab1:
    # ---------- MÉTRICAS PRINCIPALES ----------
    st.subheader("Resumen de Normativas")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h1>{len(df_filtrado)}</h1>
            <p>Normativas</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        years_range = max_year - min_year + 1
        avg_per_year = round(len(df_filtrado) / years_range, 1) if years_range > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <h1>{avg_per_year}</h1>
            <p>Promedio por año</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        if "Estado" in df_filtrado.columns and "Vigente" in df_filtrado["Estado"].unique():
            vigentes = df_filtrado[df_filtrado["Estado"] == "Vigente"].shape[0]
            porcentaje = round((vigentes / len(df_filtrado)) * 100) if len(df_filtrado) > 0 else 0
            st.markdown(f"""
            <div class="metric-card">
                <h1>{vigentes} ({porcentaje}%)</h1>
                <p>Normativas vigentes</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="metric-card">
                <h1>{len(df_filtrado.get("Bloque Temático", pd.Series()).unique())}</h1>
                <p>Bloques temáticos</p>
            </div>
            """, unsafe_allow_html=True)
    
    # ---------- DISTRIBUCIÓN POR BLOQUE TEMÁTICO ----------
    st.subheader("Distribución por Bloque Temático")
    bloque_counts = df_filtrado["Bloque Temático"].value_counts().reset_index()
    bloque_counts.columns = ["Bloque Temático", "Cantidad"]
    
    if not bloque_counts.empty:
        fig_bloque = px.bar(
            bloque_counts, 
            x="Bloque Temático", 
            y="Cantidad",
            color="Bloque Temático",
            labels={"Bloque Temático": "Bloque", "Cantidad": "Número de normativas"},
            title="Distribución de Normativas por Bloque Temático"
        )
        fig_bloque.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_bloque, use_container_width=True)
        
    # ---------- VISUALIZACIÓN JERÁRQUICA (SUNBURST) ----------
    if not df_filtrado.empty:
        st.subheader("Visualización Jerárquica de Normativas (Sunburst)")
        
        # Preparar datos para el gráfico sunburst
        # Usaremos jerarquía: Bloque Temático -> Nivel Regulador -> Nombre
        
        # Crear una copia del DataFrame para trabajar
        if all(col in df_filtrado.columns for col in ['Bloque Temático', 'Nivel Regulador', 'Nombre']):
            sunburst_df = df_filtrado[['Bloque Temático', 'Nivel Regulador', 'Nombre']].copy()
            
            # Asegurarse de que cada normativa tenga un valor para cada nivel
            sunburst_df['Bloque Temático'] = sunburst_df['Bloque Temático'].fillna('No especificado')
            sunburst_df['Nivel Regulador'] = sunburst_df['Nivel Regulador'].fillna('No especificado')
            
            # Añadir columna de valor (1 para cada normativa)
            sunburst_df['value'] = 1
            
            # Crear figura sunburst
            fig_sunburst = px.sunburst(
                sunburst_df,
                path=['Bloque Temático', 'Nivel Regulador', 'Nombre'],
                values='value',
                title="Visualización Jerárquica de Normativas",
                color_discrete_sequence=px.colors.qualitative.Bold,
                maxdepth=3  # Limitar la profundidad visible por defecto
            )
            
            # Configurar diseño
            fig_sunburst.update_layout(
                margin=dict(t=30, l=0, r=0, b=0),
                height=700,
                uniformtext=dict(minsize=10, mode='hide')  # Gestionar textos
            )
            
            # Mostrar gráfico
            st.plotly_chart(fig_sunburst, use_container_width=True)
            
            # Añadir explicación
            st.caption("""
            **Cómo interpretar este gráfico:**
            - El círculo interior representa los Bloques Temáticos
            - El anillo intermedio muestra los Niveles Reguladores dentro de cada bloque
            - El anillo exterior muestra los nombres de cada normativa individual
            - Haz clic en cualquier sección para ampliarla
            - Haz clic en el centro para volver al nivel anterior
            """)
            
            # Opción para mostrar datos alternativos
            alt_view = st.checkbox("Mostrar vista alternativa (Nivel Regulador → Bloque Temático → Nombre)")
            
            if alt_view:
                # Vista alternativa invirtiendo primeros niveles de jerarquía
                fig_sunburst_alt = px.sunburst(
                    sunburst_df,
                    path=['Nivel Regulador', 'Bloque Temático', 'Nombre'],
                    values='value',
                    title="Distribución por Nivel Regulador y Bloque Temático",
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                    maxdepth=3
                )
                
                fig_sunburst_alt.update_layout(
                    margin=dict(t=30, l=0, r=0, b=0),
                    height=700,
                    uniformtext=dict(minsize=10, mode='hide')
                )
                
                st.plotly_chart(fig_sunburst_alt, use_container_width=True)
            
        else:
            st.info("Faltan columnas necesarias para el gráfico Sunburst (Bloque Temático, Nivel Regulador, Nombre)")
    else:
        st.info("No hay datos suficientes para generar el gráfico Sunburst.")
    
    # ---------- DIAGRAMA DE SANKEY ----------
    st.subheader("Flujo entre Bloques Temáticos y Niveles Reguladores")
    
    if not df_filtrado.empty and all(col in df_filtrado.columns for col in ['Bloque Temático', 'Nivel Regulador']):
        # Preparar datos para el diagrama Sankey
        # Contar flujos entre Bloque Temático -> Nivel Regulador
        flujo_df = df_filtrado.groupby(['Bloque Temático', 'Nivel Regulador']).size().reset_index(name='Cantidad')
        
        # Reemplazar NaN con "No especificado"
        flujo_df['Bloque Temático'] = flujo_df['Bloque Temático'].fillna('No especificado')
        flujo_df['Nivel Regulador'] = flujo_df['Nivel Regulador'].fillna('No especificado')
        
        # Para Sankey, necesitamos listas de nodos fuente, destino y valores
        # Primero, crear índices para bloques y niveles
        bloques_unicos = flujo_df['Bloque Temático'].unique().tolist()
        niveles_unicos = flujo_df['Nivel Regulador'].unique().tolist()
        
        # Crear mapeo de nombres a índices
        bloque_to_idx = {bloque: idx for idx, bloque in enumerate(bloques_unicos)}
        nivel_to_idx = {nivel: idx + len(bloques_unicos) for idx, nivel in enumerate(niveles_unicos)}
        
        # Crear listas para el diagrama Sankey
        fuentes = []
        destinos = []
        valores = []
        
        # Llenar las listas
        for _, fila in flujo_df.iterrows():
            bloque = fila['Bloque Temático']
            nivel = fila['Nivel Regulador']
            cantidad = fila['Cantidad']
            
            fuentes.append(bloque_to_idx[bloque])
            destinos.append(nivel_to_idx[nivel])
            valores.append(cantidad)
        
        # Crear lista de nodos (bloques + niveles)
        nodos = [{'name': bloque} for bloque in bloques_unicos] + [{'name': nivel} for nivel in niveles_unicos]
        
        # Crear figura Sankey
        fig_sankey = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=[nodo['name'] for nodo in nodos],
                color="blue"
            ),
            link=dict(
                source=fuentes,
                target=destinos,
                value=valores
            )
        )])
        
        fig_sankey.update_layout(
            title_text="Flujo de Normativas: Bloques Temáticos → Niveles Reguladores",
            font_size=10,
            height=600
        )
        
        st.plotly_chart(fig_sankey, use_container_width=True)
        
        st.caption("""
        **Cómo interpretar este diagrama:**
        - El flujo muestra la distribución de normativas desde los bloques temáticos (izquierda) hacia los niveles reguladores (derecha)
        - El grosor de cada flujo representa la cantidad de normativas que comparten esa relación
        - Este diagrama permite identificar qué bloques temáticos tienen mayor presencia en cada nivel regulador
        """)
    else:
        st.info("No hay datos suficientes para generar el diagrama de Sankey. Se requieren las columnas 'Bloque Temático' y 'Nivel Regulador'.")
        
    # ---------- LISTA DE NORMATIVAS FILTRADAS ----------
    st.subheader("Normativas Filtradas")

    if df_filtrado.empty:
        st.info("No hay normativas que coincidan con los filtros seleccionados.")
    else:
        # Ordenar por fecha más reciente primero
        df_mostrar = df_filtrado.sort_values("Fecha Entrada en Vigor", ascending=False)
        
        # Paginación
        items_per_page = 10
        total_pages = (len(df_mostrar) + items_per_page - 1) // items_per_page
        
        if total_pages > 1:
            page = st.select_slider("Página", options=range(1, total_pages + 1), value=1)
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(df_mostrar))
            df_pagina = df_mostrar.iloc[start_idx:end_idx]
        else:
            df_pagina = df_mostrar
        
        # Mostrar cada normativa como una tarjeta
        for _, row in df_pagina.iterrows():
            fecha = row["Fecha Entrada en Vigor"].strftime("%d/%m/%Y") if pd.notnull(row["Fecha Entrada en Vigor"]) else "N/A"
            estado_tag = f'<span style="background-color: #28a745; color: white; padding: 2px 6px; border-radius: 3px;">{row["Estado"]}</span>' if "Estado" in row and row["Estado"] == "Vigente" else ""
            
            # Incluir la variable Detalles
            detalles = row.get("Detalles", "")
            
            st.markdown(f"""
            <div class="normativa-card">
                <h3>{row["Nombre"]} {estado_tag}</h3>
                <p><strong>Bloque:</strong> {row["Bloque Temático"]} | <strong>Fecha:</strong> {fecha}</p>
                <p>{row.get("Descripción", "")}</p>
                <p><strong>Detalles:</strong> {detalles}</p>
            </div>
            """, unsafe_allow_html=True)

# Tab 2: Análisis temporal
with tab2:
    st.subheader("📈 Evolución de Normativas en el Tiempo")
    
    # Análisis por año mejorado
    año_counts = df_filtrado.groupby("Año").size().reset_index(name="Cantidad")
    
    if not año_counts.empty:
        # Asegurar que todos los años en el rango estén representados
        all_years = pd.DataFrame({"Año": range(int(años_seleccionados[0]) if 'años_seleccionados' in locals() else min_year, 
                                            int(años_seleccionados[1]) if 'años_seleccionados' in locals() else max_year + 1)})
        año_counts = pd.merge(all_years, año_counts, on="Año", how="left").fillna(0)
        
        # Crear gráfico mejorado
        fig_año = px.line(
            año_counts, 
            x="Año", 
            y="Cantidad", 
            markers=True, 
            title="Evolución de Normativas Digitales por Año",
            labels={"Año": "Año", "Cantidad": "Número de normativas"}
        )
        fig_año.update_layout(
            xaxis=dict(tickmode='linear'),
            yaxis=dict(tickmode='linear', dtick=1),
            hovermode="x unified"
        )
        st.plotly_chart(fig_año, use_container_width=True)
        
        # Añadir vista acumulativa
        show_cumulative = st.checkbox("Mostrar vista acumulativa")
        if show_cumulative:
            año_counts["Acumulado"] = año_counts["Cantidad"].cumsum()
            fig_acumulado = px.line(
                año_counts, 
                x="Año", 
                y="Acumulado", 
                markers=True, 
                title="Normativas Digitales Acumuladas",
                labels={"Año": "Año", "Acumulado": "Número acumulado de normativas"}
            )
            fig_acumulado.update_layout(
                xaxis=dict(tickmode='linear'),
                hovermode="x unified"
            )
            st.plotly_chart(fig_acumulado, use_container_width=True)
    else:
        st.info("No hay datos para mostrar en el rango seleccionado.")
        
    # Análisis por tipo de norma a lo largo del tiempo
    st.subheader("Evolución por Nivel Regulador")

    if not df_filtrado.empty:
        nivel_año = df_filtrado.groupby(["Año", "Nivel Regulador"]).size().reset_index(name="Cantidad")
        
        if not nivel_año.empty:
            fig_nivel_tiempo = px.line(
                nivel_año, 
                x="Año", 
                y="Cantidad",
                color="Nivel Regulador",
                markers=True,
                title="Evolución de Normativas por Nivel Regulador",
                labels={"Año": "Año", "Cantidad": "Número de normativas", "Nivel Regulador": "Nivel"}
            )
            fig_nivel_tiempo.update_layout(
                xaxis=dict(tickmode='linear'),
                yaxis=dict(tickmode='linear', dtick=1),
                hovermode="x unified"
            )
            st.plotly_chart(fig_nivel_tiempo, use_container_width=True)
        
# Tab 3: Análisis de relaciones
with tab3:
    st.subheader("🔗 Análisis de Relaciones entre Normativas")
    
    # Verificar si hay relaciones para analizar
    if df_relaciones.empty:
        st.info("No hay datos de relaciones para mostrar.")
    else:
        # Filtrar relaciones basadas en las normativas filtradas
        normativas_ids = df_filtrado['ID'].astype(str).tolist()
        df_relaciones_filtradas = df_relaciones[
            (df_relaciones['ID_Normativa_1'].isin(normativas_ids)) | 
            (df_relaciones['ID_Normativa_2'].isin(normativas_ids))
        ]
        
        if df_relaciones_filtradas.empty:
            st.info("No hay relaciones entre las normativas filtradas.")
        else:
            # ---------- CREACIÓN DEL GRAFO ----------
            G = nx.Graph()
            
            # Obtener todos los nodos únicos de las relaciones
            all_nodes = set(df_relaciones_filtradas['ID_Normativa_1'].tolist() + 
                           df_relaciones_filtradas['ID_Normativa_2'].tolist())
            
            # Añadir nodos con atributos
            for node_id in all_nodes:
                # Buscar información de la normativa
                normativa_info = df_normativas[df_normativas['ID'].astype(str) == node_id]
                if not normativa_info.empty:
                    row = normativa_info.iloc[0]
                    G.add_node(
                        node_id,
                        name=row.get('Nombre', f'ID: {node_id}'),
                        bloque=row.get('Bloque Temático', 'No especificado'),
                        año=int(row.get('Año', 0)) if pd.notnull(row.get('Año', 0)) else 0
                    )
                else:
                    # Si no se encuentra información, añadir con valores por defecto
                    G.add_node(
                        node_id,
                        name=f'ID: {node_id}',
                        bloque='No especificado',
                        año=0
                    )
            
            # Diccionario para almacenar atributos de relaciones
            edge_attributes = {}
            
            # Añadir relaciones con atributos
            for _, row in df_relaciones_filtradas.iterrows():
                id1 = row["ID_Normativa_1"]
                id2 = row["ID_Normativa_2"]
                
                # Añadir la arista al grafo
                G.add_edge(id1, id2)
                
                # Guardar atributos de la relación
                tipo = row.get("Tipo_Relacion", "No especificado")
                comentario = row.get("Comentario", "")
                
                # Guardar en diccionario de atributos
                edge_attributes[(id1, id2)] = {
                    "tipo": tipo,
                    "comentario": comentario
                }
            
            # Verificar si hay nodos en el grafo
            if not G.nodes():
                st.info("No se pudo crear un grafo de relaciones con los datos filtrados.")
            else:
                # ---------- VISUALIZACIÓN DEL GRAFO DE RED ----------
                # Aplicar layout spring
                pos = nx.spring_layout(G, seed=42)
                
                # Preparar trazos de edges con información de tipo de relación
                edge_trace = go.Scatter(
                    x=[], y=[], 
                    line=dict(width=0.8, color='#888'), 
                    hoverinfo='text', 
                    mode='lines',
                    text=[]
                )
                
                for edge in G.edges():
                    x0, y0 = pos[edge[0]]
                    x1, y1 = pos[edge[1]]
                    edge_trace.x += (x0, x1, None)
                    edge_trace.y += (y0, y1, None)
                    
                    # Obtener atributos de la relación
                    attrs = edge_attributes.get(edge, edge_attributes.get((edge[1], edge[0]), {"tipo": "No especificado", "comentario": ""}))
                    
                    # Texto para hover
                    hover_text = f"Tipo: {attrs['tipo']}"
                    if attrs['comentario']:
                        hover_text += f"<br>Comentario: {attrs['comentario']}"
                        
                    # Añadir None para mantener alineación con las coordenadas
                    edge_trace.text += (hover_text, hover_text, None)
                
                # Preparar colores de nodos por Bloque Temático
                bloques = [G.nodes[n]["bloque"] for n in G.nodes()]
                unique_bloques = list(set(bloques))
                color_map = {bloque: i for i, bloque in enumerate(unique_bloques)}
                node_colors = [color_map[G.nodes[n]["bloque"]] for n in G.nodes()]
                colorbar_title = "Bloque Temático"
                colorscale = px.colors.qualitative.Set1
                
                # Preparar hover text
                hover_texts = []
                for n in G.nodes():
                    node_info = G.nodes[n]
                    connections = len(list(G.neighbors(n)))
                    hover_text = f"{node_info['name']}<br>Bloque: {node_info['bloque']}<br>Año: {node_info['año']}<br>Conexiones: {connections}"
                    hover_texts.append(hover_text)
                
                # Crear trazo de nodos
                node_trace = go.Scatter(
                    x=[pos[n][0] for n in G.nodes()], 
                    y=[pos[n][1] for n in G.nodes()],
                    mode='markers',
                    hoverinfo='text',
                    text=hover_texts,
                    marker=dict(
                        size=[10 + len(list(G.neighbors(n))) * 2 for n in G.nodes()],
                        color=node_colors,
                        colorscale=colorscale,
                        showscale=True,
                        colorbar=dict(title=colorbar_title)
                    )
                )
                
                # Crear figura final
                fig_network = go.Figure(data=[edge_trace, node_trace])
                fig_network.update_layout(
                    title="Red de Relaciones entre Normativas",
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20, l=5, r=5, t=40),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                
                # Mostrar gráfico de red
                st.plotly_chart(fig_network, use_container_width=True)
                
                # ---------- ESTADÍSTICAS DE LA RED ----------
                st.subheader("Estadísticas de la Red")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Normativas Conectadas", len(G.nodes()))
                    
                with col2:
                    st.metric("Relaciones", len(G.edges()))
                    
                with col3:
                    if len(G.nodes()) > 0:
                        density = nx.density(G)
                        st.metric("Densidad de Conexión", f"{density:.3f}")
                    else:
                        st.metric("Densidad de Conexión", "N/A")
                
                # ---------- TABLA DE RELACIONES ----------
                st.subheader("Detalle de Relaciones")
                
                # Crear dataframe con detalles de relaciones
                relations_data = []
                for edge in G.edges():
                    id1, id2 = edge
                    name1 = G.nodes[id1]['name']
                    name2 = G.nodes[id2]['name']
                    
                    # Obtener atributos de la relación
                    attrs = edge_attributes.get(edge, edge_attributes.get((id2, id1), {"tipo": "No especificado", "comentario": ""}))
                    
                    relations_data.append({
                        "Normativa 1": name1,
                        "Normativa 2": name2,
                        "Tipo de Relación": attrs['tipo'],
                        "Comentario": attrs['comentario']
                    })
                
                # Crear dataframe y mostrar tabla
                if relations_data:
                    df_relaciones_detalle = pd.DataFrame(relations_data)
                    st.dataframe(df_relaciones_detalle, use_container_width=True)
                
                # ---------- ANÁLISIS POR TIPO DE RELACIÓN ----------
                if relations_data:
                    st.subheader("Análisis por Tipo de Relación")
                    
                    # Contar tipos de relación
                    tipos_relacion = [r["Tipo de Relación"] for r in relations_data]
                    conteo_tipos = pd.Series(tipos_relacion).value_counts().reset_index()
                    conteo_tipos.columns = ["Tipo de Relación", "Cantidad"]
                    
                    # Crear gráfico de barras
                    fig_tipos = px.bar(
                        conteo_tipos,
                        x="Tipo de Relación",
                        y="Cantidad",
                        title="Distribución de Tipos de Relación",
                        color="Tipo de Relación"
                    )
                    st.plotly_chart(fig_tipos, use_container_width=True)
                
                # ---------- MATRIZ DE ADYACENCIA ----------
                st.subheader("Matriz de Adyacencia")
                
                # Obtener nombres de todas las normativas
                nombres_normativas = {}
                for n in G.nodes():
                    nombres_normativas[n] = G.nodes[n]['name']
                
                # Crear matriz de adyacencia usando networkx
                adj_matrix = nx.to_numpy_array(G)
                
                # Crear dataframe con nombres de normativas
                node_ids = list(G.nodes())
                nombres_lista = [nombres_normativas[nid] for nid in node_ids]
                
                # Crear dataframe con matriz de adyacencia
                df_matriz = pd.DataFrame(adj_matrix, index=nombres_lista, columns=nombres_lista)
                
                # Mostrar matriz como tabla interactiva
                st.dataframe(df_matriz, use_container_width=True)
                
                # ---------- NORMATIVAS MÁS CONECTADAS ----------
                if len(G.nodes()) > 0:
                    st.subheader("Normativas más Conectadas")
                    
                    # Calcular centralidad
                    degree_dict = dict(G.degree())
                    sorted_degrees = sorted(degree_dict.items(), key=lambda x: x[1], reverse=True)
                    
                    # Mostrar top 5 o todas si hay menos
                    top_n = min(5, len(sorted_degrees))
                    top_connected = []
                    
                    for i in range(top_n):
                        if i < len(sorted_degrees):
                            node_id, degree = sorted_degrees[i]
                            node_name = nombres_normativas.get(node_id, f"ID: {node_id}")
                            top_connected.append((node_name, degree))
                    
                    # Crear dataframe para visualización
                    top_df = pd.DataFrame(top_connected, columns=["Normativa", "Conexiones"])
                    
                    # Crear gráfico de barras horizontal
                    if not top_df.empty:
                        fig_top = px.bar(
                            top_df, 
                            y="Normativa", 
                            x="Conexiones", 
                            orientation='h',
                            title="Normativas con más Conexiones",
                            labels={"Normativa": "", "Conexiones": "Número de conexiones"}
                        )
                        st.plotly_chart(fig_top, use_container_width=True)
                
                # ---------- MAPA DE CALOR TEMPORAL ----------
                st.subheader("Mapa de Calor Temporal de Relaciones")
                
                # Obtener años de las normativas relacionadas
                normativas_en_relaciones = set(df_relaciones_filtradas['ID_Normativa_1'].tolist() + 
                                             df_relaciones_filtradas['ID_Normativa_2'].tolist())
                
                # Crear un diccionario para mapear IDs a años
                id_to_year = dict(zip(df_normativas['ID'].astype(str), df_normativas['Año']))
                
                # Inicializar una matriz para el mapa de calor
                años_unicos = sorted(df_normativas['Año'].unique())
                n_años = len(años_unicos)
                
                # Crear un diccionario para mapear año a índice
                año_to_idx = {año: idx for idx, año in enumerate(años_unicos)}
                
                # Inicializar matriz de conexiones
                matriz_conexiones = np.zeros((n_años, n_años))
                
                # Llenar la matriz con las conexiones entre años
                for _, relacion in df_relaciones_filtradas.iterrows():
                    id1 = relacion['ID_Normativa_1']
                    id2 = relacion['ID_Normativa_2']
                    
                    if id1 in id_to_year and id2 in id_to_year:
                        año1 = id_to_year[id1]
                        año2 = id_to_year[id2]
                        
                        if año1 in año_to_idx and año2 in año_to_idx:
                            idx1 = año_to_idx[año1]
                            idx2 = año_to_idx[año2]
                            
                            # Incrementar el conteo en ambas direcciones para una matriz simétrica
                            matriz_conexiones[idx1, idx2] += 1
                            matriz_conexiones[idx2, idx1] += 1
                
                # Crear un DataFrame para el mapa de calor
                df_heatmap = pd.DataFrame(
                    matriz_conexiones,
                    index=años_unicos,
                    columns=años_unicos
                )
                
                # Crear el mapa de calor con Plotly
                fig_heatmap = px.imshow(
                    df_heatmap,
                    labels=dict(x="Año", y="Año", color="N° de Relaciones"),
                    x=años_unicos,
                    y=años_unicos,
                    color_continuous_scale="Blues",
                    title="Mapa de Calor de Relaciones entre Normativas por Año"
                )
                
                fig_heatmap.update_layout(
                    height=600,
                    xaxis=dict(tickangle=-45),
                    coloraxis_colorbar=dict(
                        title="N° de Relaciones",
                        tickmode="array"
                    )
                )
                
                st.plotly_chart(fig_heatmap, use_container_width=True)      
# Agregar footer con información
st.markdown("---")
st.caption("Dashboard de Normativas Digitales en la UE. Nieves Fonseca. © 2025")
