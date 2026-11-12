"""Tema consistente para figuras Plotly (usa la paleta oficial)."""
import plotly.graph_objects as go

from src.ui.paleta import COLORWAY, NEUTRO_CLARO, TEXTO


def aplicar_tema(fig: go.Figure, titulo: str | None = None) -> go.Figure:
    fig.update_layout(template='plotly_white', colorway=COLORWAY,
                      font=dict(family='Arial', size=13, color=TEXTO),
                      margin=dict(l=15, r=15, t=65, b=25),
                      legend=dict(orientation='h', y=-0.2), hovermode='x unified')
    if titulo:
        fig.update_layout(title=dict(text=titulo, font=dict(size=17)))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor=NEUTRO_CLARO, zeroline=False)
    return fig
