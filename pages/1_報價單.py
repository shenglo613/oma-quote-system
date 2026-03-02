import streamlit as st
import pandas as pd
from datetime import date

from src.ui_helpers import require_login, get_role, build_input_df, parse_input_df, compute_results_df
from src.models import LineItemInput, QuoteParams
from src.calculator import calculate_line_item, calculate_totals
from src.db import load_settings, save_quote, confirm_quote, quote_number_exists, load_quote
from src.export_csv import build_csv_bytes
from src.export_pdf import build_pdf_bytes
from config.defaults import (
    CUSTOMER_TYPES, PART_CATEGORIES, PROCUREMENT_METHODS,
    CURRENCIES, PART_CATEGORY_LABELS,
    TAX_RATE, LABOR_RATE, MIN_PROFIT,
)

st.set_page_config(page_title="報價單 — OMA", layout="wide")
require_login()

# ── 初始化 session state ──
if "line_items" not in st.session_state:
    st.session_state.line_items = [LineItemInput()]
if "quote_id" not in st.session_state:
    st.session_state.quote_id = None

st.title("📋 報價單")

# ══════════════════════════════════════════
# SECTION 1：報價單主資料
# ══════════════════════════════════════════
with st.expander("📌 報價單資訊", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        quote_number = st.text_input("報價單號 *", placeholder="例：Q-20260302-001")
        customer_type = st.selectbox("客戶類型 *", CUSTOMER_TYPES)
        currency = st.selectbox("幣別", CURRENCIES)
    with c2:
        quote_date = st.date_input("報價日期 *", value=date.today())
        customer_name = st.text_input("客戶名稱 *")
        exchange_rate = st.number_input("匯率 *", min_value=0.0001, value=32.0, step=0.01, format="%.4f")
    notes = st.text_area("備註", height=68)

# ══════════════════════════════════════════
# SECTION 2：系統參數
# ══════════════════════════════════════════
with st.expander("⚙️ 系統參數", expanded=False):
    db_settings = load_settings()
    role = get_role()
    disabled = (role != "manager")

    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        tax_rate = st.number_input(
            "關稅率", value=db_settings.get("tax_rate", TAX_RATE),
            min_value=0.0, max_value=1.0, step=0.01, format="%.2f",
            disabled=disabled,
        )
    with pc2:
        labor_rate = st.number_input(
            "工資單價（NT$/hr）", value=db_settings.get("labor_rate", LABOR_RATE),
            min_value=0.0, step=100.0,
            disabled=disabled,
        )
    with pc3:
        min_profit = st.number_input(
            "最低毛利保底（NT$）", value=db_settings.get("min_profit", MIN_PROFIT),
            min_value=0.0, step=500.0,
            disabled=disabled,
        )
    if not disabled and (
        tax_rate != db_settings.get("tax_rate", TAX_RATE)
        or labor_rate != db_settings.get("labor_rate", LABOR_RATE)
        or min_profit != db_settings.get("min_profit", MIN_PROFIT)
    ):
        st.warning("⚠️ 系統參數已修改，將影響此報價單的計算結果。")

params = QuoteParams(
    exchange_rate=exchange_rate,
    tax_rate=tax_rate,
    labor_rate=labor_rate,
    min_profit=min_profit,
    customer_type=customer_type,
)

# ══════════════════════════════════════════
# SECTION 3：明細表
# ══════════════════════════════════════════
st.subheader("明細")

col_add, col_del = st.columns([1, 5])
with col_add:
    if st.button("＋ 新增一筆"):
        st.session_state.line_items.append(LineItemInput())
        st.rerun()

input_df = build_input_df(st.session_state.line_items)

edited_df = st.data_editor(
    input_df,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "分類": st.column_config.SelectboxColumn("分類", options=PART_CATEGORIES, required=True),
        "取得方式": st.column_config.SelectboxColumn("取得方式", options=PROCUREMENT_METHODS, required=True),
        "外幣成本": st.column_config.NumberColumn("外幣成本", min_value=0.0, format="%.4f"),
        "運費(TWD)": st.column_config.NumberColumn("運費(TWD)", min_value=0.0, format="%.0f"),
        "工時(hr)": st.column_config.NumberColumn("工時(hr)", min_value=0.0, format="%.2f"),
    },
    key="line_item_editor",
)

# 更新 session state
st.session_state.line_items = parse_input_df(edited_df)
inputs = st.session_state.line_items

# 計算結果（即時）
results = [calculate_line_item(inp, params) for inp in inputs]
totals = calculate_totals(results, inputs)

# 顯示計算結果
if results:
    result_df = compute_results_df(inputs, params)
    st.dataframe(result_df, use_container_width=True)

# ══════════════════════════════════════════
# SECTION 4：KPI
# ══════════════════════════════════════════
st.divider()
k1, k2, k3, k4 = st.columns(4)
k1.metric("零件合計", f"NT$ {totals.total_parts:,.0f}")
k2.metric("工資合計", f"NT$ {totals.total_labor:,.0f}")
k3.metric("運費合計", f"NT$ {totals.total_freight:,.0f}")
k4.metric("🔖 總報價", f"NT$ {totals.grand_total:,.0f}")

# ══════════════════════════════════════════
# SECTION 5：操作按鈕
# ══════════════════════════════════════════
st.divider()

def _build_quote_data(status: str) -> dict:
    return {
        "id": st.session_state.quote_id,
        "quote_number": quote_number,
        "quote_date": str(quote_date),
        "customer_type": customer_type,
        "customer_name": customer_name,
        "currency": currency,
        "exchange_rate": exchange_rate,
        "notes": notes,
        "status": status,
        "tax_rate": tax_rate,
        "labor_rate": labor_rate,
        "min_profit": min_profit,
    }

def _build_line_items_data() -> list[dict]:
    items = []
    for inp, res in zip(inputs, results):
        items.append({
            "part_name": inp.part_name,
            "part_category": inp.part_category,
            "procurement_method": inp.procurement_method,
            "cost_foreign": inp.cost_foreign,
            "freight_twd": inp.freight_twd if inp.procurement_method != "庫存" else 0,
            "labor_hours": inp.labor_hours,
            "cost_twd": res.cost_twd,
            "tariff": res.tariff,
            "landed_cost": res.landed_cost,
            "margin_rate": res.margin_rate,
            "part_price": res.part_price,
            "labor_cost": res.labor_cost,
            "subtotal": res.subtotal,
            "part_profit": res.part_profit,
            "floor_applied": res.floor_applied,
        })
    return items

btn1, btn2, btn3, btn4 = st.columns(4)

with btn1:
    if st.button("💾 儲存草稿", use_container_width=True):
        if not quote_number:
            st.error("請填寫報價單號")
        elif not customer_name:
            st.error("請填寫客戶名稱")
        else:
            try:
                qid = save_quote(_build_quote_data("草稿"), _build_line_items_data())
                st.session_state.quote_id = qid
                st.success(f"草稿已儲存（{quote_number}）")
            except Exception as e:
                st.error(f"儲存失敗：{e}")

with btn2:
    if st.button("✅ 確認報價", use_container_width=True):
        if not quote_number or not customer_name:
            st.error("請填寫報價單號與客戶名稱")
        else:
            try:
                qid = save_quote(_build_quote_data("已確認"), _build_line_items_data())
                st.session_state.quote_id = qid
                st.success(f"報價已確認（{quote_number}）")
            except Exception as e:
                st.error(f"確認失敗：{e}")

# ── 匯出 ──
quote_meta = {
    "quote_number": quote_number,
    "quote_date": str(quote_date),
    "customer_type": customer_type,
    "customer_name": customer_name,
    "currency": currency,
    "notes": notes,
    "status": "草稿",
}

with btn3:
    csv_bytes = build_csv_bytes(quote_meta, inputs, results, totals, params)
    st.download_button(
        "⬇ 匯出 CSV",
        data=csv_bytes,
        file_name=f"{quote_number or 'quote'}.csv",
        mime="text/csv",
        use_container_width=True,
    )

with btn4:
    pdf_bytes = build_pdf_bytes(quote_meta, inputs, results, totals, params)
    st.download_button(
        "⬇ 下載 PDF",
        data=pdf_bytes,
        file_name=f"{quote_number or 'quote'}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
