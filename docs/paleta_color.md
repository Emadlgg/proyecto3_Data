# Paleta de color del observatorio

Definida en `src/ui/paleta.py` y aplicada a Plotly (`src/ui/graficas.py`), CSS (`src/ui/estilos.py`) y
tema de Streamlit (`.streamlit/config.toml`).

| Rol | Hex | Uso | Justificación |
|---|---|---|---|
| Primario | `#1B4F72` | Datos observados, títulos, KPIs | Azul profundo: confianza e institucionalidad |
| Secundario | `#2A9D8F` | Segunda serie | Verde azulado, análogo frío del primario |
| Acento | `#E9A23B` | Festividades, selección activa | Ámbar, contraste cálido (complementario) |
| Estimación | `#D1603D` | **Solo** estimaciones/proyecciones | Terracota: lo estimado nunca comparte color con lo observado |
| Neutros | `#6B7280`, `#E5E7EB`, `#F3F6F9` | Ejes, cuadrículas, tarjetas | Jerarquía visual sin competir con los datos |

Criterios: pares azul/naranja distinguibles con daltonismo; máximo 6 colores categóricos por gráfica;
color semántico consistente en todas las páginas (observado = azul sólido, estimación = terracota punteada).
