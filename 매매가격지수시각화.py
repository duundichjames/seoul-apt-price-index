"""
서울 구별 아파트 매매가격지수 — 인터랙티브 시각화
자료: 한국부동산원 R-ONE

실행: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pickle
import io
from pathlib import Path
from collections import defaultdict


# ═══════════════════════════════════════════════════════════
# 페이지 설정
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    layout="wide",
    page_title="서울 아파트 매매가격지수 변동률(%)",
    page_icon="🏠",
)

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

html, body, * {
    font-family: 'Noto Sans KR', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif !important;
}

.main .block-container {
    padding-top: 1.2rem;
    max-width: 1500px;
}

/* 슬라이더 스타일 */
div[data-baseweb="slider"] {
    padding-left: 0.5rem;
    padding-right: 0.5rem;
}

/* 메트릭 카드 */
div[data-testid="stMetric"] {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    border-left: 3px solid #4A90D9;
}

div[data-testid="stMetric"]:has(div[data-testid="stMetricValue"]) {
    transition: all 0.2s;
}

/* 상승 메트릭 */
.metric-up {
    border-left-color: #D32F2F !important;
}

/* 헤더 */
h1 {
    font-weight: 700 !important;
    letter-spacing: -0.02em;
    color: #1a1a2e;
}

/* 범례 바 */
.legend-bar {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 2rem;
    padding: 0.5rem 0;
    margin-bottom: 0.3rem;
    font-size: 0.9rem;
    color: #555;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

.line-blue {
    width: 24px;
    height: 2px;
    background: #4A90D9;
    display: inline-block;
}

.line-red {
    width: 24px;
    height: 3.5px;
    background: #D32F2F;
    display: inline-block;
    border-radius: 1px;
}

.shade-red {
    width: 18px;
    height: 14px;
    background: rgba(211, 47, 47, 0.12);
    border: 1px solid rgba(211, 47, 47, 0.3);
    display: inline-block;
    border-radius: 2px;
}

/* 캡션 */
.source-caption {
    text-align: right;
    color: #999;
    font-size: 0.78rem;
    margin-top: -0.5rem;
    padding-right: 1rem;
}

/* 상세 조회 테이블 */
.detail-table {
    font-size: 0.85rem;
}
</style>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# 상수
# ═══════════════════════════════════════════════════════════

FONT = "'Noto Sans KR', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif"
COLOR_BLUE = '#4A90D9'
COLOR_RED = '#D32F2F'
COLOR_RED_BG = 'rgba(211, 47, 47, 0.12)'
COLOR_GRID = 'rgba(0,0,0,0.06)'
기준일 = pd.Timestamp('2023-01-01')

구순서 = [
    '종로구', '중구', '용산구', '성동구', '광진구',
    '동대문구', '중랑구', '성북구', '강북구', '도봉구',
    '노원구', '은평구', '서대문구', '마포구', '양천구',
    '강서구', '구로구', '금천구', '영등포구', '동작구',
    '관악구', '서초구', '강남구', '송파구', '강동구',
]


# ═══════════════════════════════════════════════════════════
# 데이터 로딩 함수
# ═══════════════════════════════════════════════════════════

def 위계구조생성(파일):
    """한국부동산원 Excel 파일을 위계적 딕셔너리로 변환한다."""
    원본 = pd.read_excel(파일, header=None)
    광역 = 원본.iloc[0, 2:].values
    광역구분 = 원본.iloc[1, 2:].values
    광역상세 = 원본.iloc[2, 2:].values
    시군구 = 원본.iloc[3, 2:].values
    자료형식 = 원본.iloc[5, 2:].values

    자료시점 = pd.to_datetime(
        pd.Series(원본.iloc[6:, 1].values)
        .str.replace('년 ', '-').str.replace('월', ''),
        format='%Y-%m',
    )

    def nd():
        return defaultdict(nd)

    구조 = nd()
    for idx in (i for i, t in enumerate(자료형식) if t == '원자료'):
        node = 구조
        for lv in (광역[idx], 광역구분[idx], 광역상세[idx], 시군구[idx]):
            node = node[lv]
        node['원자료'] = pd.DataFrame({
            '자료시점': 자료시점,
            '값': 원본.iloc[6:, idx + 2].values,
        })

    def to_dict(d):
        return {k: to_dict(v) for k, v in d.items()} if isinstance(d, defaultdict) else d

    return to_dict(구조)


def 서울구추출(위계):
    """위계 구조에서 서울시 자치구 데이터만 추출한다."""
    if '서울' not in 위계:
        return None
    결과 = []

    def scan(node):
        for k, v in node.items():
            if k in ('원자료', '전기대비증감률'):
                continue
            if isinstance(v, dict) and '원자료' in v:
                df = v['원자료'].copy()
                df['시군구'] = k
                결과.append(df)
            elif isinstance(v, dict):
                scan(v)

    scan(위계['서울'])
    if not 결과:
        return None

    dt = pd.concat(결과, ignore_index=True).dropna(subset=['자료시점', '값'])
    dt = dt[dt['시군구'].str.endswith('구')].copy()
    dt['값'] = pd.to_numeric(dt['값'], errors='coerce')
    return dt.dropna(subset=['값']).sort_values(['시군구', '자료시점']).reset_index(drop=True)


@st.cache_data
def load_pkl(path):
    with open(path, 'rb') as f:
        return 서울구추출(pickle.load(f))


@st.cache_data
def load_bytes(data, ftype):
    buf = io.BytesIO(data)
    h = pickle.load(buf) if ftype == 'pkl' else 위계구조생성(buf)
    return 서울구추출(h)


# ═══════════════════════════════════════════════════════════
# 차트 생성 함수
# ═══════════════════════════════════════════════════════════

def 차트생성(서울구만, 구유효, 선택시점, at_max, after_2023):
    """Plotly 서브플롯 차트를 생성한다."""
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

        # 2023년 이전 — 파란선
        if len(pre) > 0:
            fig.add_trace(go.Scatter(
                x=pre['자료시점'], y=pre['값'],
                mode='lines',
                line=dict(color=COLOR_BLUE, width=1.5),
                showlegend=False,
                hovertemplate=ht,
            ), row=r, col=c)

        # 2023년 이후 — 빨간 굵은선
        if len(post) > 0 and after_2023:
            # 이전 구간과의 연결을 위해 마지막 파란 점을 포함한다
            bridge = pd.concat([pre.tail(1), post]) if len(pre) > 0 else post

            fig.add_trace(go.Scatter(
                x=bridge['자료시점'], y=bridge['값'],
                mode='lines',
                line=dict(color=COLOR_RED, width=3),
                showlegend=False,
                hovertemplate=ht,
            ), row=r, col=c)

    # 슬라이더가 맨 우측에 도달하면 2023.01 이후 구간에 음영을 추가한다
    if at_max and after_2023:
        for i in range(len(구유효)):
            fig.add_vrect(
                x0=기준일, x1=선택시점,
                fillcolor=COLOR_RED_BG,
                line_width=0,
                layer='below',
                row=i // ncols + 1,
                col=i % ncols + 1,
            )

    # 레이아웃
    fig.update_layout(
        height=nrows * 215 + 70,
        margin=dict(l=58, r=12, t=48, b=38),
        plot_bgcolor='#FAFBFC',
        paper_bgcolor='white',
        font=dict(family=FONT, size=11, color='#333'),
        hovermode='closest',
        hoverlabel=dict(
            bgcolor='white',
            bordercolor='#ccc',
            font=dict(family=FONT, size=12, color='#222'),
        ),
    )

    fig.update_annotations(font=dict(family=FONT, size=12, color='#333'))
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

    # Y축 라벨
    fig.add_annotation(
        text='매매가격지수',
        xref='paper', yref='paper',
        x=-0.038, y=0.5,
        textangle=-90,
        showarrow=False,
        font=dict(family=FONT, size=13, color='#555'),
    )

    return fig


# ═══════════════════════════════════════════════════════════
# 메인 앱
# ═══════════════════════════════════════════════════════════

# 타이틀
st.markdown(
    '<h1 style="margin-bottom:0.1rem;">서울 구별 아파트 매매가격지수</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="color:#777; margin-top:0; font-size:0.92rem;">'
    '슬라이더를 이동하여 시점별 가격 변동을 확인할 수 있습니다. '
    '각 지점에 마우스를 올리면 해당 시점의 지수가 표시됩니다.'
    '</p>',
    unsafe_allow_html=True,
)

# ── 데이터 로딩 ──

서울구만 = None
for p in ['부동산위계.pkl', 'data/부동산위계.pkl', '../부동산위계.pkl']:
    if Path(p).exists():
        서울구만 = load_pkl(p)
        break

if 서울구만 is None:
    with st.sidebar:
        st.markdown("### 데이터 업로드")
        st.markdown(
            "한국부동산원의 매매가격지수 데이터를 업로드하세요.",
        )
        up = st.file_uploader(
            "파일 선택",
            type=['pkl', 'xlsx'],
            help='부동산위계.pkl 또는 (월) 매매가격지수_아파트.xlsx',
        )
        if up:
            data_bytes = up.read()
            ftype = 'pkl' if up.name.endswith('.pkl') else 'xlsx'
            서울구만 = load_bytes(data_bytes, ftype)

if 서울구만 is None:
    st.markdown("---")
    st.info(
        "📂  사이드바에서 데이터 파일을 업로드하세요.\n\n"
        "부동산위계.pkl 또는 (월) 매매가격지수_아파트.xlsx 파일을 지원합니다."
    )
    st.stop()


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


# ── 요약 메트릭 ──

if after_2023:
    now_dt = 서울구만[서울구만['자료시점'] == 선택시점][['시군구', '값']]
    base_dt = 서울구만[서울구만['자료시점'] == 기준일][['시군구', '값']]

    if len(now_dt) > 0 and len(base_dt) > 0:
        mg = now_dt.merge(base_dt, on='시군구', suffixes=('_현재', '_기준'))
        mg['변동률'] = (mg['값_현재'] / mg['값_기준'] - 1) * 100
        top = mg.nlargest(1, '변동률').iloc[0]
        bot = mg.nsmallest(1, '변동률').iloc[0]
        개월 = (선택시점.year - 2023) * 12 + 선택시점.month - 1

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("선택 시점", 선택시점.strftime('%Y년 %m월'))
        c2.metric("2023.01 이후 경과", f"{개월}개월")
        c3.metric(f"최고 상승  {top['시군구']}", f"+{top['변동률']:.1f}%")
        c4.metric(f"최저 변동  {bot['시군구']}", f"{bot['변동률']:+.1f}%")
    else:
        st.metric("선택 시점", 선택시점.strftime('%Y년 %m월'))
else:
    st.metric("선택 시점", 선택시점.strftime('%Y년 %m월'))


# ── 범례 ──

if after_2023:
    legend_html = (
        '<div class="legend-bar">'
        '<div class="legend-item"><span class="line-blue"></span> 2023년 이전</div>'
        '<div class="legend-item"><span class="line-red"></span> 2023년 이후</div>'
    )
    if at_max:
        legend_html += '<div class="legend-item"><span class="shade-red"></span> 강조 구간</div>'
    legend_html += '</div>'
    st.markdown(legend_html, unsafe_allow_html=True)


# ── 차트 ──

fig = 차트생성(서울구만, 구유효, 선택시점, at_max, after_2023)

st.plotly_chart(
    fig,
    use_container_width=True,
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


# ── 특정 시점 상세 조회 ──

with st.expander("📊  특정 시점 전체 구 지수 조회"):
    조회_str = st.selectbox(
        "조회 시점",
        options=날짜_str[::-1],
        index=0,
        key="detail_date",
    )
    조회시점 = pd.Timestamp(날짜[날짜_str.index(조회_str)])

    조회dt = 서울구만[서울구만['자료시점'] == 조회시점][['시군구', '값']].copy()
    조회dt.columns = ['자치구', '매매가격지수']
    조회dt['매매가격지수'] = 조회dt['매매가격지수'].round(1)
    조회dt = 조회dt.sort_values('매매가격지수', ascending=False).reset_index(drop=True)
    조회dt.index = 조회dt.index + 1

    # 2023.01 대비 변동률도 함께 표시
    if 조회시점 >= 기준일:
        base_vals = 서울구만[서울구만['자료시점'] == 기준일][['시군구', '값']].copy()
        base_vals.columns = ['자치구', '기준값']
        조회dt = 조회dt.merge(base_vals, on='자치구', how='left')
        조회dt['2023.01 대비 변동률(%)'] = ((조회dt['매매가격지수'] / 조회dt['기준값'] - 1) * 100).round(1)
        조회dt = 조회dt.drop(columns=['기준값'])

    st.dataframe(
        조회dt,
        use_container_width=True,
        height=min(len(조회dt) * 36 + 40, 600),
    )
