"""Monitor de Tikal, AIMM y telefonía; series independientes y meses discontinuos."""
import pandas as pd
import plotly.express as px
import streamlit as st
from src.ui.estilos import aplicar_estilos
from src.ui.componentes import encabezado, aviso_metodologico, tabla_segura
from src.ui.graficas import aplicar_tema
from src.ui.paleta import NEUTRO, ESTIMACION
from src.ui.analitica import cargar, datos_disponibles, completar_calendario
from src.triangulacion import (FUENTES, fuentes_mensuales, cobertura_fuentes, concordancia_pares,
                               indice_base_100)


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
            cargar('indicadores/aimm_operaciones_indicadores.csv'),
            cargar('indicadores/visitantes_subdestino.csv'))

comp, tik, air, ops, mov = datos()
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
        fig.add_hline(y=100, line_dash='dash', line_color=NEUTRO)
        sel_idx = st.plotly_chart(aplicar_tema(fig, 'Evolución relativa de las tres fuentes (selecciona un mes)'),
                                  width='stretch', on_select='rerun', selection_mode='points',
                                  key='mon_indices')
        pts = getattr(getattr(sel_idx, 'selection', None), 'points', []) or []
        if pts:
            try:
                st.session_state['mon_mes_foco'] = pd.Timestamp(pts[0]['x']).to_period('M').to_timestamp()
            except (ValueError, TypeError, KeyError):
                pass
    meses = sorted(comp.fecha.dropna().unique())
    if meses:
        foco = st.session_state.get('mon_mes_foco')
        idx = 0
        if foco is not None:
            hit = [i for i, m_ in enumerate(meses) if pd.Timestamp(m_) == pd.Timestamp(foco)]
            idx = hit[0] if hit else 0
        mes = st.selectbox('Mes coincidente', meses, index=idx,
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
        fig.add_hline(y=0, line_dash='dash', line_color=NEUTRO)
        st.plotly_chart(aplicar_tema(fig, 'Cambios mensuales de las fuentes'), width='stretch')
    else:
        st.info('No hay variaciones mensuales consecutivas para la selección.')
    with st.expander('Ver meses coincidentes e índices'):
        tabla = comp.copy()
        tabla['fecha'] = tabla.fecha.dt.strftime('%Y-%m')
        tabla_segura(tabla, hide_index=True, width='stretch')
else:
    st.info('No hay datos suficientes para triangular las tres fuentes.')

st.divider()
st.subheader('3. Cobertura y concordancia entre fuentes')
if (datos_disponibles(mov, ['fecha', 'subdestino', 'visitantes'])
        and datos_disponibles(tik, ['fecha', 'total']) and datos_disponibles(air, ['fecha', 'pasajeros'])):
    polis = sorted(mov.subdestino.dropna().unique().tolist())
    ini = polis.index('Mundo Maya Aeropuerto') if 'Mundo Maya Aeropuerto' in polis else 0
    poli = st.selectbox('Polígono de telefonía a comparar', polis, index=ini, key='mon_poligono')
    wide = fuentes_mensuales(tik, air, mov, poli)
    st.markdown('**Cobertura temporal de cada fuente**')
    cob = cobertura_fuentes(wide).copy()
    for c in ('primer_mes', 'ultimo_mes'):
        cob[c] = pd.to_datetime(cob[c]).dt.strftime('%Y-%m').fillna('Sin dato')
    tabla_segura(cob.rename(columns={'fuente': 'Fuente', 'primer_mes': 'Primer mes', 'ultimo_mes': 'Último mes',
                                     'meses_con_dato': 'Meses con dato',
                                     'meses_sin_dato_en_rango': 'Meses sin dato dentro del rango'}))
    st.caption('Los meses sin dato (p. ej. ene–feb 2026 en telefonía, ceros de Tikal por confirmar) '
               'no se tratan como cero ni se interpolan.')
    idx, base = indice_base_100(wide)
    if idx is not None:
        largo = idx.melt(id_vars='fecha', var_name='fuente', value_name='indice')
        largo['fuente'] = largo.fuente.map(FUENTES)
        largo = largo.loc[largo.fecha.ge(base)]
        figc = px.line(largo, x='fecha', y='indice', color='fuente', markers=True,
                       labels={'fecha': 'Mes', 'indice': f'Índice (base 100 = {base:%Y-%m})', 'fuente': 'Fuente'})
        figc.update_traces(connectgaps=False)
        figc.add_hline(y=100, line_dash='dash', line_color=NEUTRO)
        st.plotly_chart(aplicar_tema(figc, 'Las tres fuentes desde el primer mes común (cada una termina donde acaba su cobertura)'),
                        width='stretch')
        st.caption('Cada fuente conserva su propia unidad; el índice solo compara variación relativa. '
                   'Tikal y telefonía continúan hasta el último mes disponible, más allá del AIMM.')
    st.markdown('**Concordancia entre pares (solo meses con dato en ambas fuentes)**')
    pares = concordancia_pares(wide).copy()
    pares['Correlación de niveles'] = pares.correlacion_niveles.map(
        lambda v: f'{v:.2f}' if pd.notna(v) else 'n insuficiente')
    pares['Misma dirección'] = pares.misma_direccion_pct.map(lambda v: f'{v:.0f}%' if pd.notna(v) else 'Sin dato')
    pares['Período común'] = [f'{a:%Y-%m} a {b:%Y-%m}' if pd.notna(a) else 'Sin meses comunes'
                              for a, b in zip(pares.primer_mes, pares.ultimo_mes)]
    tabla_segura(pares[['par', 'Período común', 'meses_comunes', 'Correlación de niveles',
                        'variaciones_comparables', 'Misma dirección']].rename(columns={
        'par': 'Par de fuentes', 'meses_comunes': 'Meses comunes',
        'variaciones_comparables': 'Variaciones comparables'}))
    st.caption('«Misma dirección» es el porcentaje de variaciones entre meses consecutivos en que ambas fuentes '
               'suben o bajan juntas. Con pocos meses y estacionalidad compartida, estos valores son indicativos, '
               'no prueban que las fuentes midan lo mismo.')
else:
    st.info('No hay datos suficientes para comparar la cobertura de las fuentes.')

st.divider()
if datos_disponibles(tik, ['fecha', 'total', 'nacionales', 'extranjeros', 'otros']):
    st.subheader('4. Boletos de ingreso a Tikal')
    categoria = st.selectbox('Categoría de boletos', ['total', 'nacionales', 'extranjeros', 'otros'],
                             format_func=lambda x: x.capitalize())
    anios = sorted(tik.fecha.dropna().dt.year.unique().tolist())
    elegidos = st.multiselect('Años de Tikal', anios, default=anios[-4:])
    d = tik.loc[tik.fecha.dt.year.isin(elegidos)].sort_values('fecha').copy()
    if not d.empty:
        ceros = d.total.eq(0)
        # Un mes con total 0 se muestra como hueco ("Sin dato"), nunca como valor cero.
        d.loc[ceros, ['total', 'nacionales', 'extranjeros', 'otros']] = float('nan')
        cierre = d.loc[ceros & d.fecha.between('2020-04-01', '2020-09-30'), 'fecha']
        d = completar_calendario(d)  # años no contiguos: la línea se corta, no se une con una recta
        fig = px.line(d, x='fecha', y=categoria, markers=True,
                      labels={'fecha': 'Mes', categoria: 'Boletos registrados'})
        fig.update_traces(connectgaps=False)
        if not cierre.empty:
            fig.add_vrect(x0=cierre.min() - pd.Timedelta(days=15), x1=cierre.max() + pd.Timedelta(days=15),
                          fillcolor=ESTIMACION, opacity=.10, line_width=0,
                          annotation_text='Sin boletos: cierre del parque por COVID-19',
                          annotation_position='top left')
        st.plotly_chart(aplicar_tema(fig, 'Boletos mensuales de Tikal'), width='stretch')
        if ceros.any():
            st.info('Abr–sep 2020 (cierre del parque por COVID-19) y ene 2017 (inicio de la serie, sin registro) '
                    'aparecen como "Sin dato", no como cero visitas, y se excluyen de variaciones interanuales y cruces. '
                    'Feb 2017 es un registro parcial (~4 % de feb 2018).')

if datos_disponibles(air, ['fecha', 'flujo', 'tipo_pasajero', 'pasajeros']):
    st.subheader('5. AIMM · pasajeros')
    flujos = sorted(air.flujo.dropna().unique().tolist())
    tipos = sorted(air.tipo_pasajero.dropna().unique().tolist())
    sel_flujos = st.multiselect('Flujos de pasajeros', flujos, default=flujos)
    sel_tipos = st.multiselect('Tipos de pasajero', tipos, default=tipos)
    d = air.loc[air.flujo.isin(sel_flujos) & air.tipo_pasajero.isin(sel_tipos)]
    d = d.groupby(['fecha', 'flujo'], as_index=False).pasajeros.sum()
    if not d.empty:
        d = completar_calendario(d, grupos=['flujo'])
        fig = px.line(d, x='fecha', y='pasajeros', color='flujo', markers=True,
                      labels={'fecha': 'Mes', 'pasajeros': 'Movimientos de pasajeros'})
        fig.update_traces(connectgaps=False)
        st.plotly_chart(aplicar_tema(fig, 'Pasajeros AIMM por flujo'), width='stretch')
    st.caption('Los pasajeros no equivalen a turistas únicos; los flujos se mantienen identificados.')

if datos_disponibles(ops, ['fecha', 'tipo_operacion', 'operaciones']):
    st.subheader('6. AIMM · operaciones aeronáuticas')
    d = ops.groupby(['fecha', 'tipo_operacion'], as_index=False).operaciones.sum()
    d = completar_calendario(d, grupos=['tipo_operacion'])
    fig = px.line(d, x='fecha', y='operaciones', color='tipo_operacion', markers=True,
                  labels={'fecha': 'Mes', 'operaciones': 'Operaciones'})
    fig.update_traces(connectgaps=False)
    st.plotly_chart(aplicar_tema(fig, 'Operaciones aeronáuticas (no pasajeros)'), width='stretch')
    st.caption('Operaciones y pasajeros se muestran en gráficas independientes por tener unidades distintas.')

st.divider()
st.subheader('Lectura metodológica de la triangulación')
st.write('**Tikal** registra boletos de acceso; **AIMM** registra movimientos de pasajeros '
         'y operaciones aeronáuticas; **telefonía** estima movilidad en un polígono. '
         'Sus unidades y coberturas son distintas. Los índices base 100 comparan '
         'cambios relativos y no demuestran causalidad ni identidad de personas.')
