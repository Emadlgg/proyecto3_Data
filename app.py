from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title='Laboratorio 10 | Turismo', layout='wide')
DATA = Path(__file__).parent / 'data'

@st.cache_data
def load():
    total = pd.read_csv(DATA/'serie_mensual_total.csv', parse_dates=['fecha'])
    vias = pd.read_csv(DATA/'serie_mensual_por_via.csv', parse_dates=['fecha'])
    est = pd.read_csv(DATA/'indice_estacional.csv')
    modelos = pd.read_csv(DATA/'final_metricas_modelos.csv')
    pred = pd.read_csv(DATA/'final_pronostico_prueba_intervalo80.csv', parse_dates=['fecha'])
    return total, vias, est, modelos, pred

total, vias, est, modelos, pred = load()
COLS = ['Aérea', 'Terrestre', 'Marítima']
MESES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']

st.title('Observatorio de movilidad turística | Guatemala')
st.caption('Laboratorio 10 · Visualización interactiva · Osman de León · Contexto nacional, no exclusivo de Tikal y Flores')
st.info('Los datos disponibles describen movimientos migratorios nacionales. No deben interpretarse como visitas a Tikal, ocupación hotelera o turistas únicos de Petén.')

st.sidebar.header('Exploración')
years = sorted(total.fecha.dt.year.unique().tolist())
if 'selected_year' not in st.session_state:
    st.session_state.selected_year = 2025
if 'selected_month' not in st.session_state:
    st.session_state.selected_month = 1

year = st.sidebar.selectbox('Año', years, index=years.index(st.session_state.selected_year), key='year_input_'+str(st.session_state.selected_year))
if year != st.session_state.selected_year:
    st.session_state.selected_year = year
    st.session_state.selected_month = 1
month = st.sidebar.selectbox('Mes para detalle', list(range(1,13)), index=st.session_state.selected_month-1,
                             format_func=lambda n: MESES[n-1], key='month_input_'+str(st.session_state.selected_year)+'_'+str(st.session_state.selected_month))
st.session_state.selected_month = month
route = st.sidebar.multiselect('Vías', COLS, default=COLS)
section = st.sidebar.radio('Sección', ['Exploración','Predicciones y modelos'])

# Filtros y selecciones enlazadas: el año seleccionado en gráfica 1 cambia gráficas 2 y 3;
# el mes seleccionado en gráfica 2 cambia gráfica 3.
def selected_point(event):
    try:
        points = event.selection.points
        return points[0] if points else None
    except (AttributeError, KeyError, IndexError, TypeError):
        return None

if section == 'Exploración':
    st.subheader('Evolución y composición de los movimientos')
    st.write('Selecciona una barra anual para actualizar el detalle mensual. Luego selecciona un mes para actualizar la composición por vía.')
    annual = total.assign(anio=total.fecha.dt.year).groupby('anio', as_index=False).viajeros.sum()
    # El año 2026 contiene únicamente enero-junio; evitar comparación anual directa.
    fig1 = px.bar(annual, x='anio', y='viajeros', title='1. Movimientos registrados por año (2026 parcial)', labels={'anio':'Año','viajeros':'Movimientos'})
    fig1.update_xaxes(type='category')
    ev1 = st.plotly_chart(fig1, use_container_width=True, on_select='rerun', selection_mode='points', key='annual_chart')
    p1 = selected_point(ev1)
    if p1:
        try:
            newyear = int(p1.get('x'))
            if newyear in years and newyear != st.session_state.selected_year:
                st.session_state.selected_year = newyear
                st.rerun()
        except (TypeError, ValueError):
            pass
    t_year = total[total.fecha.dt.year == st.session_state.selected_year].copy()
    t_year['mes_num'] = t_year.fecha.dt.month
    fig2 = px.bar(t_year, x='mes_num', y='viajeros', title=f'2. Detalle mensual de {st.session_state.selected_year}', labels={'mes_num':'Mes','viajeros':'Movimientos'})
    fig2.update_xaxes(tickmode='array', tickvals=list(range(1,13)), ticktext=MESES)
    ev2 = st.plotly_chart(fig2, use_container_width=True, on_select='rerun', selection_mode='points', key='month_chart')
    p2 = selected_point(ev2)
    if p2:
        try:
            newmonth = int(p2.get('x'))
            if 1 <= newmonth <= 12 and newmonth != st.session_state.selected_month:
                st.session_state.selected_month = newmonth
                st.rerun()
        except (TypeError, ValueError):
            pass
    detail = vias[(vias.fecha.dt.year == st.session_state.selected_year) & (vias.fecha.dt.month == st.session_state.selected_month)]
    if not detail.empty and route:
        parts = detail[route].iloc[0]
        fig3 = px.pie(names=parts.index, values=parts.values, hole=.45, title=f'3. Composición por vía | {MESES[st.session_state.selected_month-1]} {st.session_state.selected_year}')
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning('Sin datos para el mes o las vías seleccionadas.')
    st.caption('Las gráficas 1, 2 y 3 están vinculadas mediante selección de barras y controles sincronizados.')
    if route:
        df = vias[vias.fecha.dt.year == st.session_state.selected_year].melt(id_vars='fecha', value_vars=route, var_name='Vía', value_name='Movimientos')
        fig4 = px.line(df, x='fecha', y='Movimientos', color='Vía', markers=True, title='4. Tendencia mensual por vía de ingreso')
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.warning('Selecciona al menos una vía para ver la tendencia.')
    est2 = est.copy()
    est2['mes'] = pd.Categorical(est2['mes'], categories=MESES, ordered=True)
    est2 = est2.sort_values('mes')
    fig5 = px.bar(est2, x='mes', y='indice_estacional', title='5. Índice estacional mensual (base 100)', labels={'mes':'Mes','indice_estacional':'Índice'})
    fig5.add_hline(y=100, line_dash='dash', annotation_text='Promedio = 100')
    st.plotly_chart(fig5, use_container_width=True)
    yearly = total.copy()
    yearly['anio'] = yearly.fecha.dt.year
    yearly['mes'] = yearly.fecha.dt.month
    yearly = yearly.sort_values('fecha')
    yearly['variacion'] = yearly.viajeros.pct_change(12, fill_method=None)*100
    yearly = yearly[(yearly.anio == st.session_state.selected_year) & yearly.variacion.notna()]
    if not yearly.empty:
        fig6 = px.line(yearly, x='fecha', y='variacion', markers=True, title='6. Variación interanual por mes (%)', labels={'fecha':'Mes','variacion':'Variación (%)'})
        fig6.add_hline(y=0, line_dash='dash')
        st.plotly_chart(fig6, use_container_width=True)
    else:
        st.info('No hay suficientes observaciones previas para calcular variación interanual.')
    st.caption('Los valores de la serie pueden ser fraccionarios por la metodología de procesamiento de la fuente. 2026 tiene seis meses, no doce.')
else:
    st.subheader('Resultados de modelos ya evaluados')
    st.write('Se reutilizan salidas de laboratorios anteriores; aquí no se entrenan modelos nuevos.')
    metric = st.radio('Métrica de comparación', ['MAE','RMSE'], horizontal=True)
    fig7 = px.bar(modelos.sort_values(metric), x='Modelo', y=metric, title=f'7. Comparación de cuatro modelos: {metric} (menor es mejor)')
    fig7.update_xaxes(tickangle=-20)
    st.plotly_chart(fig7, use_container_width=True)
    st.caption('MAE: error absoluto medio. RMSE: raíz del error cuadrático medio. Comparar solo modelos evaluados sobre la misma partición y serie.')
    p = pred.copy()
    p['inferior_grafico'] = p.limite_inferior_80.clip(lower=0)
    fig8 = go.Figure()
    fig8.add_trace(go.Scatter(x=p.fecha, y=p.limite_superior_80, mode='lines', line=dict(width=0), name='Límite superior 80 %'))
    fig8.add_trace(go.Scatter(x=p.fecha, y=p.inferior_grafico, mode='lines', line=dict(width=0), fill='tonexty', name='Intervalo 80 %'))
    fig8.add_trace(go.Scatter(x=p.fecha, y=p.observado, mode='lines+markers', name='Observado'))
    fig8.add_trace(go.Scatter(x=p.fecha, y=p.estimacion, mode='lines', name='Estimación'))
    fig8.update_layout(title='8. Valores observados, estimados e intervalo del 80 %', xaxis_title='Mes', yaxis_title='Movimientos', hovermode='x unified')
    st.plotly_chart(fig8, use_container_width=True)
    st.caption('El límite inferior original puede ser negativo: para visualizar movimientos no negativos se recorta solo el dibujo a cero; los datos fuente no se alteran. Un intervalo del 80 % no garantiza contener cada observación.')
    with st.expander('Tabla de comparación de modelos (elemento complementario)'):
        st.dataframe(modelos, use_container_width=True, hide_index=True)
    with st.expander('Detalle de pronóstico (elemento complementario)'):
        st.dataframe(pred, use_container_width=True, hide_index=True)

st.divider()
st.caption('Fuente: archivos CSV procesados de laboratorios previos. Repositorio: https://github.com/Emadlgg/proyecto3_Data.git · Uso académico; no publicar datos institucionales sin autorización.')
