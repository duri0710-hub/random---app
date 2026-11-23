import streamlit as st
import random
import pandas as pd

st.set_page_config(page_title="블랙아웃 서바이벌", page_icon="⚡", layout="wide")

# --- 1. 상태 초기화 ---
def init_game():
    st.session_state.hour = 0
    st.session_state.freq = 60.0
    st.session_state.budget = 100
    st.session_state.ess_soc = 50.0  # ESS 잔량 (%)
    st.session_state.superconductor = False  # 초전도 송전망 여부
    st.session_state.graphene_cap = False    # 그래핀 슈퍼커패시터 여부
    st.session_state.game_over = False
    st.session_state.win = False
    st.session_state.msg = "전력망 관제실에 오신 것을 환영합니다. 24시간 동안 블랙아웃을 막으세요!"
    st.session_state.history = []

if "hour" not in st.session_state:
    init_game()

# 시간대별 기본 수요 & 태양광 패턴
def get_environment(hour):
    # 기본 수요 (MW): 출근(8~10시), 오후 피크(14~16시), 저녁(19~21시) 상승
    base_demand = 400 + 150 * (
        (1 if 8 <= hour <= 10 else 0)
        + (1.3 if 14 <= hour <= 16 else 0)
        + (1.2 if 19 <= hour <= 21 else 0)
    )
    demand = int(base_demand + random.randint(-30, 40))

    # 태양광 발전 (MW): 낮 시간대 발전 + 구름 변수
    if 7 <= hour <= 17:
        cloud = random.choice([1.0, 1.0, 0.7, 0.4])
        solar = int(220 * (1 - abs(hour - 12) / 6) * cloud)
    else:
        solar = 0
    return demand, solar

if "current_env" not in st.session_state:
    st.session_state.current_env = get_environment(0)

# --- 2. 상단 타이틀 & 상태 표시 ---
st.title("⚡ 블랙아웃 서바이벌: 스마트 그리드 & 신소재 관제")
st.caption("수요와 공급을 맞춰 계통 주파수 60.0Hz를 사수하세요! (허용 범위: 59.0 ~ 61.0 Hz)")

demand, solar = st.session_state.current_env
loss_rate = 0.0 if st.session_state.superconductor else 0.08  # 일반 구리선 8% 손실 vs 초전도체 0%

col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
col_m1.metric("현재 시각", f"{st.session_state.hour:02d}:00 / 24:00")
col_m2.metric("계통 주파수", f"{st.session_state.freq:.2f} Hz", delta=f"{st.session_state.freq - 60.0:+.2f} Hz")
col_m3.metric("도시 전력 수요", f"{demand} MW")
col_m4.metric("전고체 ESS 잔량", f"{st.session_state.ess_soc:.0f} %")
col_m5.metric("운영 예산", f"{st.session_state.budget} 억")

st.info(st.session_state.msg)

# --- 3. 메인 컨트롤 & 그래프 ---
left, right = st.columns([1, 1.3])

with left:
    st.subheader("🎛️ 발전 및 신소재 제어")
    if not st.session_state.game_over and not st.session_state.win:
        st.write(f"☀️ **현재 태양광 발전량:** `{solar} MW` (기상 변동 반영)")
        st.write(f"🔌 **송전 손실률:** `{loss_rate * 100:.0f}%` ({'초전도 케이블 가동 중' if st.session_state.superconductor else '기존 구리선'})")

        gas_power = st.slider("🔥 LNG 가스터빈 출력 (MW)", 0, 600, 300, step=20)
        ess_action = st.slider("🔋 전고체 ESS 충·방전 (MW) [음수: 충전 / 양수: 방전]", -150, 150, 0, step=10)

        # 예상 수급 계산 미리보기
        gross_supply = solar + gas_power + ess_action
        net_supply = gross_supply * (1 - loss_rate)
        diff = net_supply - demand
        st.markdown(f"**예상 순공급:** `{net_supply:.0f} MW` (수요 대비 `{diff:+.0f} MW`)")

        if st.button("⏭️ 1시간 진행 (턴 종료)", type="primary", use_container_width=True):
            # ESS 잔량 체크
            actual_ess = ess_action
            if ess_action > 0 and st.session_state.ess_soc <= 0:
                actual_ess = 0
            elif ess_action < 0 and st.session_state.ess_soc >= 100:
                actual_ess = 0

            # 실제 순공급 및 주파수 변화 계산
            net_supply = (solar + gas_power + actual_ess) * (1 - loss_rate)
            imbalance = net_supply - demand

            # 그래핀 슈퍼커패시터가 있으면 주파수 급변 50% 완화
            damping = 0.5 if st.session_state.graphene_cap else 1.0
            freq_delta = (imbalance / 250.0) * damping
            st.session_state.freq = round(st.session_state.freq + freq_delta, 2)

            # ESS SOC 및 예산 업데이트
            st.session_state.ess_soc = max(0.0, min(100.0, st.session_state.ess_soc - actual_ess * 0.2))
            fuel_cost = int(gas_power * 0.03)
            revenue = 18 if abs(st.session_state.freq - 60.0) <= 0.4 else 8
            st.session_state.budget += (revenue - fuel_cost)

            # 기록 저장
            st.session_state.history.append({
                "시간": f"{st.session_state.hour}시",
                "수요(MW)": demand,
                "순공급(MW)": round(net_supply),
                "주파수(Hz)": st.session_state.freq
            })

            # 승패 판정
            st.session_state.hour += 1
            if st.session_state.freq < 59.0:
                st.session_state.game_over = True
                st.session_state.msg = "💥 [블랙아웃 발생] 공급 부족으로 주파수가 59.0Hz 아래로 붕괴했습니다!"
            elif st.session_state.freq > 61.0:
                st.session_state.game_over = True
                st.session_state.msg = "⚡ [과전압 트립] 과잉 공급으로 발전기가 긴급 정지되었습니다!"
            elif st.session_state.hour >= 24:
                st.session_state.win = True
                st.session_state.msg = f"🎉 24시간 전력망 방어 성공! 최종 예산: {st.session_state.budget}억"
            else:
                st.session_state.current_env = get_environment(st.session_state.hour)
                st.session_state.msg = f"⏱️ {st.session_state.hour}시 관제 돌입! 수급 오차 {imbalance:+.0f}MW → 주파수 {freq_delta:+.2f}Hz 변동"
            st.rerun()

        st.divider()
        st.subheader("🧬 신소재 R&D 업그레이드")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("❄️ 초전도 송전망 (70억)", disabled=st.session_state.superconductor or st.session_state.budget < 70, use_container_width=True):
                st.session_state.budget -= 70
                st.session_state.superconductor = True
                st.session_state.msg = "❄️ 고온 초전도 케이블 도입 완료! 송전 손실이 8% → 0%가 되었습니다."
                st.rerun()
        with c2:
            if st.button("🛡️ 그래핀 커패시터 (60억)", disabled=st.session_state.graphene_cap or st.session_state.budget < 60, use_container_width=True):
                st.session_state.budget -= 60
                st.session_state.graphene_cap = True
                st.session_state.msg = "🛡️ 그래핀 슈퍼커패시터 설치 완료! 주파수 급변 충격이 50% 완화됩니다."
                st.rerun()
    else:
        if st.button("🔄 새 게임 시작", type="primary", use_container_width=True):
            init_game()
            st.session_state.current_env = get_environment(0)
            st.rerun()

with right:
    st.subheader("📊 실시간 전력 수급 & 주파수 추이")
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history).set_index("시간")
        st.line_chart(df[["수요(MW)", "순공급(MW)"]])
        st.line_chart(df[["주파수(Hz)"]])
    else:
        st.write("첫 번째 턴을 진행하면 실시간 전력 수급 그래프와 주파수 차트가 표시됩니다.")
