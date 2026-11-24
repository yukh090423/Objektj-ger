import plotly.graph_objects as go
from plotly.subplots import make_subplots


COMPONENT_COLORS = {"x": "#2563eb", "y": "#b45309"}


def plot_motion(results, length_unit, *, filtered_results=None):
    """운동 분석 결과를 위치·속도·가속도 패널의 Plotly Figure로 반환한다.

    비교하려면 results에 필터를 끈 결과를, filtered_results에 같은
    영상에서 필터를 켠 결과를 전달한다. 측정 위치는 한 번만 표시한다.
    """
    results = list(results)
    if not results:
        raise ValueError("표시할 분석 결과가 없습니다. 먼저 영상을 분석하세요.")

    comparing = filtered_results is not None
    if comparing:
        filtered_results = list(filtered_results)
        if not filtered_results:
            raise ValueError("필터를 적용한 비교 결과가 비어 있습니다.")

    figure = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        subplot_titles=("위치", "속도", "가속도"),
    )
    for row, unit in enumerate((length_unit, f"{length_unit}/s", f"{length_unit}/s²"), 1):
        figure.update_yaxes(title_text=unit, row=row, col=1)

    raw_label = "필터 끔" if comparing else ""
    for row in range(1, 4):
        label = "측정 위치" if comparing and row == 1 else raw_label
        show_legend = row == 1 or (comparing and row == 2)
        _add_components(figure, results, row, label, "solid", show_legend)
        if comparing and row > 1:
            _add_components(figure, filtered_results, row, "필터 켬", "dot", row == 2)

    figure.update_xaxes(title_text="시간 (초)", row=3, col=1)
    figure.update_layout(height=760, hovermode="x", legend={"orientation": "h", "y": -0.1})
    return figure


def _add_components(figure, results, row, label, dash, showlegend):
    field = row + 1  # 위치, 속도, 가속도의 튜플 인덱스는 각각 2, 3, 4다.
    times = [record[1] for record in results]
    for axis, (component, color) in enumerate(COMPONENT_COLORS.items()):
        values = [
            None if record[field] is None else record[field][axis]
            for record in results
        ]
        name = f"{component} · {label}" if label else component
        figure.add_trace(
            go.Scatter(
                x=times,
                y=values,
                name=name,
                legendgroup=name,
                showlegend=showlegend,
                mode="lines+markers",
                marker={"size": 4},
                line={"color": color, "dash": dash},
                connectgaps=False,
            ),
            row=row,
            col=1,
        )
