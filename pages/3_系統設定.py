import streamlit as st
from src.ui_helpers import require_login, is_manager
from src.db import load_settings, save_settings, load_dealers, save_dealers
from config.defaults import (
    TAX_RATE, LABOR_RATE, MIN_PROFIT,
    MARGIN_RATE_A, MARGIN_RATE_B, MARGIN_RATE_C,
    DEALER_COEFFICIENT,
)

st.set_page_config(page_title="系統設定 — OMA", layout="wide")
require_login()

if not is_manager():
    st.error("此頁面僅限主管存取")
    st.stop()

st.title("系統設定")
st.caption("修改預設系統參數。此設定影響**所有新建報價單**的預設值。")

try:
    db = load_settings()
except Exception as e:
    st.error(f"讀取系統設定失敗：{e}")
    st.stop()

# ── 系統參數設定 ──────────────────────────────────────────────
with st.form("settings_form"):
    st.subheader("毛利率（依零件分類）")
    st.caption("售價公式：售價 = 到岸成本 ÷ (1 - 毛利率)")
    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        new_margin_a = st.number_input(
            "分類 A 毛利率",
            value=db.get("margin_rate_a", MARGIN_RATE_A),
            min_value=0.0, max_value=0.99, step=0.01, format="%.2f",
        )
    with mc2:
        new_margin_b = st.number_input(
            "分類 B 毛利率",
            value=db.get("margin_rate_b", MARGIN_RATE_B),
            min_value=0.0, max_value=0.99, step=0.01, format="%.2f",
        )
    with mc3:
        new_margin_c = st.number_input(
            "分類 C 毛利率",
            value=db.get("margin_rate_c", MARGIN_RATE_C),
            min_value=0.0, max_value=0.99, step=0.01, format="%.2f",
        )

    st.divider()
    st.subheader("其他參數")
    pc1, pc2 = st.columns(2)
    with pc1:
        new_labor = st.number_input(
            "工資單價（NT$/hr）",
            value=db.get("labor_rate", LABOR_RATE),
            min_value=0.0, step=100.0,
        )
        new_tax = st.number_input(
            "關稅率",
            value=db.get("tax_rate", TAX_RATE),
            min_value=0.0, max_value=1.0, step=0.01, format="%.2f",
        )
    with pc2:
        new_min_profit = st.number_input(
            "最低毛利保底（NT$）",
            value=db.get("min_profit", MIN_PROFIT),
            min_value=0.0, step=500.0,
        )
        new_dealer_coeff = st.number_input(
            "經銷商係數（經銷商價格 = 總報價 × 係數）",
            value=db.get("dealer_coefficient", DEALER_COEFFICIENT),
            min_value=0.0, max_value=1.0, step=0.01, format="%.2f",
        )

    if new_tax != db.get("tax_rate", TAX_RATE):
        st.warning("修改關稅率將影響所有新報價單。歷史已儲存報價不受影響。")

    submitted = st.form_submit_button("儲存設定", type="primary")
    if submitted:
        try:
            save_settings(
                tax_rate=new_tax,
                labor_rate=new_labor,
                min_profit=new_min_profit,
                margin_rate_a=new_margin_a,
                margin_rate_b=new_margin_b,
                margin_rate_c=new_margin_c,
                dealer_coefficient=new_dealer_coeff,
            )
            st.success("設定已儲存")
            st.rerun()
        except Exception as e:
            st.error(f"儲存失敗：{e}")

# ── 經銷商名單維護 ────────────────────────────────────────────
st.divider()
st.subheader("經銷商名單維護")

try:
    dealers = load_dealers()
except Exception as e:
    st.error(f"讀取經銷商名單失敗：{e}")
    dealers = []

st.caption(f"目前共 {len(dealers)} 家經銷商")
for i, d in enumerate(dealers):
    st.text(f"  {i+1}. {d}")

with st.form("dealer_form"):
    st.markdown("**新增經銷商**")
    new_dealer = st.text_input("經銷商名稱")
    add_submitted = st.form_submit_button("新增")
    if add_submitted and new_dealer.strip():
        if new_dealer.strip() in dealers:
            st.error(f"「{new_dealer.strip()}」已存在")
        else:
            dealers.append(new_dealer.strip())
            try:
                save_dealers(dealers)
                st.success(f"已新增「{new_dealer.strip()}」")
                st.rerun()
            except Exception as e:
                st.error(f"新增失敗：{e}")

if dealers:
    with st.form("dealer_delete_form"):
        st.markdown("**刪除經銷商**")
        del_dealer = st.selectbox("選擇要刪除的經銷商", dealers)
        del_submitted = st.form_submit_button("刪除")
        if del_submitted and del_dealer:
            dealers.remove(del_dealer)
            try:
                save_dealers(dealers)
                st.success(f"已刪除「{del_dealer}」")
                st.rerun()
            except Exception as e:
                st.error(f"刪除失敗：{e}")
