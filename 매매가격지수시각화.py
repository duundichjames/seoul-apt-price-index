"""
서울 구별 아파트 매매가격지수 — 인터랙티브 시각화
자료: 한국부동산원 R-ONE

실행: streamlit run 매매가격지수시각화.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ═══════════════════════════════════════════════════════════
# 페이지 설정
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    layout="wide",
    page_title="서울 아파트 매매가격지수",
    page_icon="🏠",
)

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@300;400;500;700&display=swap');

html, body, * {
    font-family: 'Noto Serif KR', 'Batang', serif !important;
}

.main .block-container {
    padding-top: 1.2rem;
    max-width: 1500px;
}

div[data-baseweb="slider"] {
    padding-left: 0.5rem;
    padding-right: 0.5rem;
}

h1 {
    font-weight: 700 !important;
    letter-spacing: -0.02em;
}

.source-caption {
    text-align: right;
    opacity: 0.5;
    font-size: 0.78rem;
    margin-top: -0.5rem;
    padding-right: 1rem;
}
</style>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# 상수
# ═══════════════════════════════════════════════════════════

FONT = "'Noto Serif KR', 'Batang', serif"

# 2023년 이전 — 배경에 녹아드는 은회색
COLOR_PRE = 'rgba(155, 165, 180, 0.4)'
# 2023년 이후 — 시선을 끄는 따뜻한 앰버
COLOR_POST = '#FFB347'
# 하이라이트 음영 — 앰버 계열 반투명
COLOR_HIGHLIGHT = 'rgba(255, 179, 71, 0.18)'

COLOR_GRID = 'rgba(128, 128, 128, 0.12)'
기준일 = pd.Timestamp('2023-01-01')

구순서 = [
    '종로구', '중구', '용산구', '성동구', '광진구',
    '동대문구', '중랑구', '성북구', '강북구', '도봉구',
    '노원구', '은평구', '서대문구', '마포구', '양천구',
    '강서구', '구로구', '금천구', '영등포구', '동작구',
    '관악구', '서초구', '강남구', '송파구', '강동구',
]


# ═══════════════════════════════════════════════════════════
# 데이터 로딩
# ═══════════════════════════════════════════════════════════

DATA_PATH = 'data/서울구만.parquet'

@st.cache_data
def load_data():
    df = pd.read_parquet(DATA_PATH)
    df['자료시점'] = pd.to_datetime(df['자료시점'])
    df['값'] = pd.to_numeric(df['값'], errors='coerce')
    return df.dropna(subset=['값']).sort_values(['시군구', '자료시점']).reset_index(drop=True)


# ═══════════════════════════════════════════════════════════
# 차트 생성 함수
# ═══════════════════════════════════════════════════════════

def 차트생성(서울구만, 구유효, 선택시점, at_max, after_2023):
    ncols = 5
    nrows = (len(구유효) + ncols - 1) // ncols

    fig = make_subplots(
        rows=nrows, cols=ncols,
        subplot_titles=구유효,
        shared_xaxes=True,
        shared_yaxes=True,
        vertical_spacing=0.065,
        horizontal_spacing=0.032,
    )

    for i, 구 in enumerate(구유효):
        r, c = i // ncols + 1, i % ncols + 1
        gd = 서울구만[(서울구만['시군구'] == 구) & (서울구만['자료시점'] <= 선택시점)]
        pre = gd[gd['자료시점'] < 기준일]
        post = gd[gd['자료시점'] >= 기준일]

        ht = (
            f'<b>{구}</b><br>'
            '%{x|%Y년 %m월}<br>'
            '매매가격지수  %{y:.1f}'
            '<extra></extra>'
        )

        # 2023년 이전 — 은회색 가는 선
        if len(pre) > 0:
            fig.add_trace(go.Scatter(
                x=pre['자료시점'], y=pre['값'],
                mode='lines',
                line=dict(color=COLOR_PRE, width=1.2),
                showlegend=False,
                hovertemplate=ht,
            ), row=r, col=c)

        # 2023년 이후 — 앰버 굵은 선
        if len(post) > 0 and after_2023:
            bridge = pd.concat([pre.tail(1), post]) if len(pre) > 0 else post
            fig.add_trace(go.Scatter(
                x=bridge['자료시점'], y=bridge['값'],
                mode='lines',
                line=dict(color=COLOR_POST, width=2.8),
                showlegend=False,
                hovertemplate=ht,
            ), row=r, col=c)

    # 슬라이더 맨 우측 → 하이라이트 음영
    if at_max and after_2023:
        for i in range(len(구유효)):
            fig.add_vrect(
                x0=기준일, x1=선택시점,
                fillcolor=COLOR_HIGHLIGHT,
                line_width=0,
                layer='below',
                row=i // ncols + 1,
                col=i % ncols + 1,
            )

    fig.update_layout(
        height=nrows * 215 + 70,
        margin=dict(l=40, r=12, t=48, b=38),
        font=dict(family=FONT, size=11),
        hovermode='closest',
        hoverlabel=dict(
            font=dict(family=FONT, size=12),
        ),
    )

    fig.update_annotations(font=dict(family=FONT, size=12))
    fig.update_yaxes(
        range=[35, 125],
        gridcolor=COLOR_GRID,
        zeroline=False,
        tickfont=dict(size=10),
    )
    fig.update_xaxes(
        gridcolor=COLOR_GRID,
        zeroline=False,
        nticks=6,
        tickfont=dict(size=10),
    )

    return fig


# ═══════════════════════════════════════════════════════════
# 메인 앱
# ═══════════════════════════════════════════════════════════

st.markdown(
    '<h1 style="margin-bottom:0.1rem;">서울 구별 아파트 매매가격지수: 2023년 이후 무슨 일??</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="opacity:0.6; margin-top:0; font-size:0.92rem;">'
    '슬라이더를 이동하여 시점별 가격 변동을 확인할 수 있습니다. '
    '각 지점에 마우스를 올리면 해당 시점의 지수가 표시됩니다.'
    '</p>',
    unsafe_allow_html=True,
)

# ── 데이터 로딩 ──

서울구만 = load_data()

# ── 데이터 준비 ──

구유효 = [g for g in 구순서 if g in 서울구만['시군구'].unique()]
날짜 = sorted(서울구만['자료시점'].unique())
날짜_str = [pd.Timestamp(d).strftime('%Y.%m') for d in 날짜]

# ── 슬라이더 ──

st.markdown("")
선택_str = st.select_slider(
    "시점 선택",
    options=날짜_str,
    value=날짜_str[-1],
)
선택i = 날짜_str.index(선택_str)
선택시점 = pd.Timestamp(날짜[선택i])
at_max = (선택i == len(날짜) - 1)
after_2023 = (선택시점 >= 기준일)

# ── 차트 ──

fig = 차트생성(서울구만, 구유효, 선택시점, at_max, after_2023)

st.plotly_chart(
    fig,
    use_container_width=True,
    theme="streamlit",
    config={
        'displayModeBar': True,
        'modeBarButtonsToRemove': ['lasso2d', 'select2d', 'autoScale2d'],
        'displaylogo': False,
    },
)

st.markdown(
    '<p class="source-caption">자료, 한국부동산원 (2025.03 = 100)</p>',
    unsafe_allow_html=True,
)