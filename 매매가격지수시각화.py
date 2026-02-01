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
import json
import matplotlib.colors as mcolors


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

h2 {
    font-weight: 600 !important;
    letter-spacing: -0.01em;
    margin-top: 3rem !important;
}

.source-caption {
    text-align: right;
    opacity: 0.5;
    font-size: 0.78rem;
    margin-top: -0.5rem;
    padding-right: 1rem;
}

.section-divider {
    border: none;
    border-top: 1px solid rgba(128, 128, 128, 0.2);
    margin: 3rem 0 1rem 0;
}
</style>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# 상수
# ═══════════════════════════════════════════════════════════

FONT = "'Noto Serif KR', 'Batang', serif"

COLOR_PRE = 'rgba(155, 165, 180, 0.4)'
COLOR_POST = '#FFB347'
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
GEOJSON_PATH = 'data/서울구경계.geojson'

@st.cache_data
def load_data():
    df = pd.read_parquet(DATA_PATH)
    df['자료시점'] = pd.to_datetime(df['자료시점'])
    df['값'] = pd.to_numeric(df['값'], errors='coerce')
    return df.dropna(subset=['값']).sort_values(['시군구', '자료시점']).reset_index(drop=True)

@st.cache_data
def load_geojson():
    with open(GEOJSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════
# 시계열 차트
# ═══════════════════════════════════════════════════════════

def 시계열차트생성(서울구만, 구유효, 선택시점, at_max, after_2023):
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

        if len(pre) > 0:
            fig.add_trace(go.Scatter(
                x=pre['자료시점'], y=pre['값'],
                mode='lines',
                line=dict(color=COLOR_PRE, width=1.2),
                showlegend=False,
                hovertemplate=ht,
            ), row=r, col=c)

        if len(post) > 0 and after_2023:
            bridge = pd.concat([pre.tail(1), post]) if len(pre) > 0 else post
            fig.add_trace(go.Scatter(
                x=bridge['자료시점'], y=bridge['값'],
                mode='lines',
                line=dict(color=COLOR_POST, width=2.8),
                showlegend=False,
                hovertemplate=ht,
            ), row=r, col=c)

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
        hoverlabel=dict(font=dict(family=FONT, size=12)),
    )

    fig.update_annotations(font=dict(family=FONT, size=12))
    fig.update_yaxes(range=[35, 125], gridcolor=COLOR_GRID, zeroline=False, tickfont=dict(size=10))
    fig.update_xaxes(gridcolor=COLOR_GRID, zeroline=False, nticks=6, tickfont=dict(size=10))

    return fig


# ═══════════════════════════════════════════════════════════
# 지도 차트 (버블맵)
# ═══════════════════════════════════════════════════════════

def 경계선좌표추출(geojson):
    all_lons, all_lats = [], []
    for feature in geojson['features']:
        geom = feature['geometry']
        rings = []
        if geom['type'] == 'Polygon':
            rings = [geom['coordinates'][0]]
        elif geom['type'] == 'MultiPolygon':
            rings = [poly[0] for poly in geom['coordinates']]
        for ring in rings:
            all_lons.extend([c[0] for c in ring] + [None])
            all_lats.extend([c[1] for c in ring] + [None])
    return all_lons, all_lats


def 중심점사전생성(geojson):
    return {
        f['properties']['SGG_NM']: (f['properties']['lat'], f['properties']['lon'])
        for f in geojson['features']
    }


def 글자색결정(변동률값, vmin, vmax):
    """변동률 값에 따른 버블 배경색의 휘도를 계산하여 글자색을 결정한다."""
    # RdYlBu_r 컬러맵 기준 (reversescale=True이므로 RdYlBu 원본 사용)
    cmap = mcolors.LinearSegmentedColormap.from_list(
        'rdylbu_r', ['#313695', '#4575b4', '#74add1', '#abd9e9',
                      '#e0f3f8', '#ffffbf', '#fee090', '#fdae61',
                      '#f46d43', '#d73027', '#a50026']
    )
    if vmax == vmin:
        norm_val = 0.5
    else:
        norm_val = (변동률값 - vmin) / (vmax - vmin)
    norm_val = max(0, min(1, norm_val))
    rgba = cmap(norm_val)
    휘도 = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
    return 'rgba(30, 30, 30, 0.9)' if 휘도 > 0.55 else 'rgba(255, 255, 255, 0.95)'


def 지도차트생성(서울구만, 서울geojson, 선택시점):
    기준dt = 서울구만[서울구만['자료시점'] == 기준일][['시군구', '값']].copy()
    현재dt = 서울구만[서울구만['자료시점'] == 선택시점][['시군구', '값']].copy()

    if len(기준dt) == 0 or len(현재dt) == 0:
        return None

    변동률dt = 현재dt.merge(기준dt, on='시군구', suffixes=('_현재', '_기준'))
    변동률dt['변동률'] = (변동률dt['값_현재'] / 변동률dt['값_기준'] - 1) * 100

    중심점 = 중심점사전생성(서울geojson)
    변동률dt['lat'] = 변동률dt['시군구'].map(lambda x: 중심점.get(x, (None, None))[0])
    변동률dt['lon'] = 변동률dt['시군구'].map(lambda x: 중심점.get(x, (None, None))[1])
    변동률dt = 변동률dt.dropna(subset=['lat', 'lon'])

    변동률_shifted = 변동률dt['변동률'] - 변동률dt['변동률'].min() + 3
    변동률dt['버블크기'] = np.sqrt(변동률_shifted) * 9

    vmin = 변동률dt['변동률'].min()
    vmax = 변동률dt['변동률'].max()

    # 구별 글자색 결정
    변동률dt['글자색'] = 변동률dt['변동률'].apply(lambda v: 글자색결정(v, vmin, vmax))

    fig = go.Figure()

    # 1) 구 경계선
    경계_lon, 경계_lat = 경계선좌표추출(서울geojson)
    fig.add_trace(go.Scatter(
        x=경계_lon, y=경계_lat,
        mode='lines',
        line=dict(color='rgba(180, 180, 180, 0.5)', width=1.2),
        showlegend=False,
        hoverinfo='skip',
    ))

    # 2) 버블
    fig.add_trace(go.Scatter(
        x=변동률dt['lon'],
        y=변동률dt['lat'],
        mode='markers',
        marker=dict(
            size=변동률dt['버블크기'],
            color=변동률dt['변동률'],
            colorscale='RdYlBu',
            reversescale=True,
            cmid=0,
            colorbar=dict(
                title=dict(text='변동률 (%)', font=dict(family=FONT, size=11)),
                tickfont=dict(family=FONT, size=10),
                thickness=15,
                len=0.6,
            ),
            line=dict(width=1, color='rgba(255, 255, 255, 0.5)'),
            opacity=0.88,
        ),
        customdata=np.stack([
            변동률dt['시군구'],
            변동률dt['변동률'].round(1),
            변동률dt['값_현재'].round(1),
            변동률dt['값_기준'].round(1),
        ], axis=-1),
        hovertemplate=(
            '<b>%{customdata[0]}</b><br>'
            '변동률  %{customdata[1]}%<br>'
            '현재 지수  %{customdata[2]}<br>'
            '2023.01 지수  %{customdata[3]}'
            '<extra></extra>'
        ),
        showlegend=False,
    ))

    # 3) 구 이름 — 글자색을 버블 배경에 맞춰 동적 지정
    for _, row in 변동률dt.iterrows():
        fig.add_annotation(
            x=row['lon'],
            y=row['lat'],
            text=row['시군구'],
            showarrow=False,
            font=dict(family=FONT, size=10, color=row['글자색']),
            xanchor='center',
            yanchor='middle',
        )

    fig.update_layout(
        height=700,
        margin=dict(l=10, r=60, t=10, b=10),
        font=dict(family=FONT),
        xaxis=dict(visible=False),
        yaxis=dict(
            visible=False,
            scaleanchor='x',
            scaleratio=1 / np.cos(np.radians(37.55)),
        ),
        hovermode='closest',
        hoverlabel=dict(font=dict(family=FONT, size=12)),
        dragmode='pan',
    )

    return fig


# ═══════════════════════════════════════════════════════════
# 메인 앱
# ═══════════════════════════════════════════════════════════

# ── 데이터 로딩 ──

서울구만 = load_data()

서울geojson = None
try:
    서울geojson = load_geojson()
except FileNotFoundError:
    pass

구유효 = [g for g in 구순서 if g in 서울구만['시군구'].unique()]
날짜 = sorted(서울구만['자료시점'].unique())
날짜_str = [pd.Timestamp(d).strftime('%Y.%m') for d in 날짜]


# ═══════════════════════════════════════════════════════════
# 1장. 시계열
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

fig_ts = 시계열차트생성(서울구만, 구유효, 선택시점, at_max, after_2023)

st.plotly_chart(
    fig_ts,
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


# ═══════════════════════════════════════════════════════════
# 2장. 지도
# ═══════════════════════════════════════════════════════════

if 서울geojson and after_2023:
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    시점문자열 = 선택시점.strftime('%Y년 %m월')
    st.markdown(
        f'<h2 style="margin-bottom:0.2rem;">2023년 1월 기준 구별 상승률: 뛰는 곳과 기는 곳</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="opacity:0.6; margin-top:0; font-size:0.92rem;">'
        f'2023년 1월 대비 {시점문자열} 기준. '
        f'원의 크기와 색상이 변동률을 나타냅니다.'
        f'</p>',
        unsafe_allow_html=True,
    )

    fig_map = 지도차트생성(서울구만, 서울geojson, 선택시점)
    if fig_map:
        st.plotly_chart(
            fig_map,
            use_container_width=True,
            theme="streamlit",
            config={
                'displayModeBar': True,
                'modeBarButtonsToRemove': ['lasso2d', 'select2d', 'autoScale2d'],
                'displaylogo': False,
                'scrollZoom': True,
            },
        )

    st.markdown(
        '<p class="source-caption">자료, 한국부동산원 (2025.03 = 100)</p>',
        unsafe_allow_html=True,
    )