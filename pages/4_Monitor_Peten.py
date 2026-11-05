"""Monitor de Tikal, AIMM y telefonía; series independientes y meses discontinuos."""
import pandas as pd
import plotly.express as px
import streamlit as st
from src.ui.estilos import aplicar_estilos
from src.ui.componentes import encabezado, aviso_metodologico
from src.ui.graficas import aplicar_tema
from src.ui.analitica import cargar, datos_disponibles


def preparar_comparacion(comp):
    """Completa calendario para dibujar huecos; no inventa observaciones."""
    requeridas = ['fecha', 'indice_boletos_tikal', 'indice_pasajeros_aimm',
                  'indice_movilidad_poligono_aeropuerto']
    if not datos_disponibles(comp, requeridas):
        return pd.DataFrame()
    d = comp.copy()
    d['fecha'] = pd.to_datetime(d['fecha'], errors='coerce').dt.to_period('M').dt.to_timestamp()
    d = d.dropna(subset=['fecha']).sort_values('fecha')
    if d.fecha.duplicated().any():
        raise ValueError('Comparación: meses duplicados')
    if d.empty:
        return d
    calendario = pd.date_range(d.fecha.min(), d.fecha.max(), freq='MS')
    return d.set_index('fecha').reindex(calendario).rename_axis('fecha').reset_index()


def variaciones_consecutivas(comp):
    """Variación porcentual solo cuando hay observaciones en meses adyacentes."""
    d = preparar_comparacion(comp)
    if d.empty:
        return pd.DataFrame(columns=['fecha', 'fuente', 'variacion_pct'])
    cols = ['indice_boletos_tikal', 'indice_pasajeros_aimm',
            'indice_movilidad_poligono_aeropuerto']
    resultado = []
    for col in cols:
        actual = pd.to_numeric(d[col], errors='coerce')
        previo = actual.shift(1)
        cambio = (actual / previo - 1) * 100
        cambio = cambio.where(actual.notna() & previo.gt(0))
        resultado.append(pd.DataFrame({'fecha': d.fecha, 'fuente': col,
                                       'variacion_pct': cambio}))
    return pd.concat(resultado, ignore_index=True)


st.set_page_config(page_title='Monitor | Petén', layout='wide')
aplicar_estilos()
encabezado('Monitor especializado de Petén',
           'Triangulación de boletos de Tikal, pasajeros del AIMM y movilidad telefónica.',
           'Tres fuentes independientes; tendencias comparables, poblaciones no equivalentes')

@st.cache_data(show_spinner=False)
def datos():
    return (cargar('indicadores/comparacion_fuentes_indices.csv'),
            cargar('indicadores/tikal_indicadores.csv'),
            cargar('indicadores/aimm_pasajeros_indicadores.csv'),
            cargar('indicadores/aimm_operaciones_indicadores.csv'))

comp, tik, air, ops = datos()
aviso_metodologico()
cols = {'indice_boletos_tikal': 'Boletos Tikal',
        'indice_pasajeros_aimm': 'Pasajeros AIMM',
        'indice_movilidad_poligono_aeropuerto': 'Telefonía aeropuerto'}

st.subheader('1. Triangulación en meses coincidentes')
st.caption('Índices base 100: muestran cambios relativos, no totales equivalentes. '
           'Enero y febrero de 2026 carecen de observaciones coincidentes.')
if datos_disponibles(comp, ['fecha', *cols, 'boletos_tikal', 'pasajeros_aimm',
                             'movilidad_poligono_aeropuerto']):
    comp = comp.copy()
    comp['fecha'] = pd.to_datetime(comp.fecha, errors='coerce')
    calendario = preparar_comparacion(comp)
    seleccion = st.multiselect('Fuentes en el gráfico', list(cols), default=list(cols),
                               format_func=lambda x: cols[x])
    if seleccion:
        largo = calendario.melt(id_vars='fecha', value_vars=seleccion,
                                var_name='fuente', value_name='indice')
        largo['fuente'] = largo.fuente.map(cols)
        fig = px.line(largo, x='fecha', y='indice', color='fuente', markers=True,
                      labels={'fecha': 'Mes', 'indice': 'Índice base 100', 'fuente': 'Fuente'})
        fig.update_traces(connectgaps=False)
        fig.add_hline(y=100, line_dash='dash', line_color='gray')
        st.plotly_chart(aplicar_tema(fig, 'Evolución relativa de las tres fuentes'), width='stretch')
    meses = sorted(comp.fecha.dropna().unique())
    if meses:
        mes = st.selectbox('Mes coincidente', meses,
                           format_func=lambda x: pd.Timestamp(x).strftime('%Y-%m'))
        fila = comp.loc[comp.fecha.eq(pd.Timestamp(mes))].iloc[0]
        a, b, c = st.columns(3)
        a.metric('Boletos de Tikal', f'{fila.boletos_tikal:,.0f}')
        b.metric('Pasajeros AIMM', f'{fila.pasajeros_aimm:,.0f}')
        c.metric('Movilidad del polígono aeropuerto', f'{fila.movilidad_poligono_aeropuerto:,.0f}')
        st.caption('No sumar estos indicadores: representan universos diferentes.')

    st.subheader('2. Comparación de variaciones mensuales')
    st.caption('Variación únicamente entre meses calendario consecutivos con datos válidos. '
               'Marzo de 2026 no se compara con diciembre de 2025.')
    variaciones = variaciones_consecutivas(comp)
    variaciones = variaciones[variaciones.fuente.isin(seleccion)].copy()
    if not variaciones.empty and variaciones.variacion_pct.notna().any():
        variaciones['fuente'] = variaciones.fuente.map(cols)
        fig = px.line(variaciones, x='fecha', y='variacion_pct', color='fuente',
                      markers=True, labels={'fecha': 'Mes', 'variacion_pct': 'Variación mensual (%)', 'fuente': 'Fuente'})
        fig.update_traces(connectgaps=False)
        fig.add_hline(y=0, line_dash='dash', line_color='gray')
        st.plotly_chart(aplicar_tema(fig, 'Cambios mensuales de las fuentes'), width='stretch')
    else:
        st.info('No hay variaciones mensuales consecutivas para la selección.')
    with st.expander('Ver meses coincidentes e índices'):
        tabla = comp.copy()
        tabla['fecha'] = tabla.fecha.dt.strftime('%Y-%m')
        st.dataframe(tabla, hide_index=True, width='stretch')
else:
    st.info('No hay datos suficientes para triangular las tres fuentes.')

st.divider()
if datos_disponibles(tik, ['fecha', 'total', 'nacionales', 'extranjeros', 'otros']):
    st.subheader('3. Boletos de ingreso a Tikal')
    categoria = st.selectbox('Categoría de boletos', ['total', 'nacionales', 'extranjeros', 'otros'],
                             format_func=lambda x: x.capitalize())
    anios = sorted(tik.fecha.dropna().dt.year.unique().tolist())
    elegidos = st.multiselect('Años de Tikal', anios, default=anios[-4:])
    d = tik.loc[tik.fecha.dt.year.isin(elegidos)].sort_values('fecha').copy()
    if not d.empty:
        fig = px.line(d, x='fecha', y=categoria, markers=True,
                      labels={'fecha': 'Mes', categoria: 'Boletos registrados'})
        st.plotly_chart(aplicar_tema(fig, 'Boletos mensuales de Tikal'), width='stretch')
        if d.total.eq(0).any():
            st.warning('Existen meses con cero: verificar si representan cierre o ausencia de datos.')

if datos_disponibles(air, ['fecha', 'flujo', 'tipo_pasajero', 'pasajeros']):
    st.subheader('4. AIMM · pasajeros')
    flujos = sorted(air.flujo.dropna().unique().tolist())
    tipos = sorted(air.tipo_pasajero.dropna().unique().tolist())
    sel_flujos = st.multiselect('Flujos de pasajeros', flujos, default=flujos)
    sel_tipos = st.multiselect('Tipos de pasajero', tipos, default=tipos)
    d = air.loc[air.flujo.isin(sel_flujos) & air.tipo_pasajero.isin(sel_tipos)]
    d = d.groupby(['fecha', 'flujo'], as_index=False).pasajeros.sum()
    if not d.empty:
        fig = px.line(d, x='fecha', y='pasajeros', color='flujo', markers=True,
                      labels={'fecha': 'Mes', 'pasajeros': 'Movimientos de pasajeros'})
        st.plotly_chart(aplicar_tema(fig, 'Pasajeros AIMM por flujo'), width='stretch')
    st.caption('Los pasajeros no equivalen a turistas únicos; los flujos se mantienen identificados.')

if datos_disponibles(ops, ['fecha', 'tipo_operacion', 'operaciones']):
    st.subheader('5. AIMM · operaciones aeronáuticas')
    d = ops.groupby(['fecha', 'tipo_operacion'], as_index=False).operaciones.sum()
    fig = px.line(d, x='fecha', y='operaciones', color='tipo_operacion', markers=True,
                  labels={'fecha': 'Mes', 'operaciones': 'Operaciones'})
    st.plotly_chart(aplicar_tema(fig, 'Operaciones aeronáuticas (no pasajeros)'), width='stretch')
    st.caption('Operaciones y pasajeros se muestran en gráficas independientes por tener unidades distintas.')

st.divider()
st.subheader('Lectura metodológica de la triangulación')
st.write('**Tikal** registra boletos de acceso; **AIMM** registra movimientos de pasajeros '
         'y operaciones aeronáuticas; **telefonía** estima movilidad en un polígono. '
         'Sus unidades y coberturas son distintas. Los índices base 100 comparan '
         'cambios relativos y no demuestran causalidad ni identidad de personas.')
