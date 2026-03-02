import streamlit as st
from src.ui_helpers import require_login, get_role
from src.db import load_settings, save_settings
from config.defaults import TAX_RATE, LABOR_RATE, MIN_PROFIT

st.set_page_config(page_title="系統設定 — OMA", layout="wide")
require_login()

if get_role() != "manager":
    st.error("此頁面僅限主管（manager）存取")
    st.stop()

st.title("⚙️ 系統設定")
st.caption("修改預設系統參數。此設定影響**所有新建報價單**的預設值。")

try:
    db = load_settings()
except Exception as e:
    st.error(f"讀取系統設定失敗：{e}")
    st.stop()

with st.form("settings_form"):
    new_labor = st.number_input(
        "工資單價（NT$/hr）",
        value=db.get("labor_rate", LABOR_RATE),
        min_value=0.0, step=100.0,
    )
    new_min_profit = st.number_input(
        "最低毛利保底（NT$）",
        value=db.get("min_profit", MIN_PROFIT),
        min_value=0.0, step=500.0,
    )
    new_tax = st.number_input(
        "關稅率",
        value=db.get("tax_rate", TAX_RATE),
        min_value=0.0, max_value=1.0, step=0.01, format="%.2f",
    )
    if new_tax != db.get("tax_rate", TAX_RATE):
        st.warning("⚠️ 修改關稅率將影響所有新報價單。歷史已儲存報價不受影響。")

    submitted = st.form_submit_button("儲存設定", type="primary")
    if submitted:
        try:
            save_settings(new_tax, new_labor, new_min_profit)
            st.success("設定已儲存")
            st.rerun()
        except Exception as e:
            st.error(f"儲存失敗：{e}")
