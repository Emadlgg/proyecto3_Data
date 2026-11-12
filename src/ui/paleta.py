"""Paleta oficial del observatorio (documentada en docs/paleta_color.md).

Criterios de teoría del color aplicados:
- Azul profundo como color primario: transmite confianza e institucionalidad.
- Verde azulado y ámbar como secundarios: análogo frío + complementario cálido.
- Terracota reservado EXCLUSIVAMENTE para estimaciones, de modo que lo observado
  y lo estimado nunca compartan color.
- Colores elegidos para distinguirse también con daltonismo (azul / naranja).
- Grises neutros para ejes, cuadrículas y texto secundario.
"""
PRIMARIO = '#1B4F72'      # observado / elemento principal
SECUNDARIO = '#2A9D8F'    # segunda serie
ACENTO = '#E9A23B'        # énfasis / festividades
ESTIMACION = '#D1603D'    # SOLO estimaciones y proyecciones
MORADO = '#8E5A9B'
VERDE = '#7FB069'
NEUTRO = '#6B7280'
NEUTRO_CLARO = '#E5E7EB'
FONDO_TARJETA = '#F3F6F9'
TEXTO = '#1F2933'

# Orden de series categóricas en Plotly (sin ESTIMACION a propósito).
COLORWAY = [PRIMARIO, SECUNDARIO, ACENTO, MORADO, VERDE, NEUTRO]

# Mapa semántico para tipo de dato.
TIPO_DATO = {'Observado': PRIMARIO, 'Estimación': ESTIMACION}
