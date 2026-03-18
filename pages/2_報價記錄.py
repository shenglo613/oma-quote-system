import streamlit as st
import pandas as pd
from src.ui_helpers import require_login, clear_quote_form
from src.db import list_quotes, load_quote
from config.defaults import STATUS_DRAFT, STATUS_CONFIRMED, SHIPPING_INCLUDED

st.set_page_config(page_title="報價記錄 — OMA", layout="wide")
require_login()

st.title("報價記錄")

# ── 篩選列 ──────────────────────────────────────────────────
f1, f2 = st.columns(2)
with f1:
    filter_status = st.selectbox("狀態", ["全部", STATUS_DRAFT, STATUS_CONFIRMED])
with f2:
    filter_customer = st.text_input("客戶名稱（模糊搜尋）")

status_param   = None if filter_status == "全部" else filter_status
customer_param = filter_customer if filter_customer else None

try:
    quotes = list_quotes(status=status_param, customer_name=customer_param)
except Exception as e:
    st.error(f"讀取報價記錄失敗：{e}")
    st.stop()

if not quotes:
    st.info("目前沒有符合條件的報價單")
    st.stop()

# ── 報價列表 ─────────────────────────────────────────────────
df = pd.DataFrame(quotes)
df = df[["quote_number", "quote_date", "customer_type", "customer_name", "status", "created_at"]]
df.columns = ["報價單號", "日期", "客戶類型", "客戶名稱", "狀態", "建立時間"]

st.dataframe(df, use_container_width=True, hide_index=True)

# ── 查看 / 編輯明細 ──────────────────────────────────────────
st.divider()
selected_number = st.selectbox(
    "選擇報價單查看明細",
    [""] + [q["quote_number"] for q in quotes],
)

if not selected_number:
    st.stop()

selected = next(q for q in quotes if q["quote_number"] == selected_number)
full = load_quote(selected["id"])

if not full:
    st.error("找不到該報價單，可能已被刪除。")
    st.stop()

# 基本資訊
info_cols = st.columns(5)
info_cols[0].metric("報價單號", full["quote_number"])
info_cols[1].metric("日期",     str(full["quote_date"]))
info_cols[2].metric("客戶名稱", full["customer_name"])
info_cols[3].metric("狀態",     full["status"])
info_cols[4].metric("運費狀態", full.get("shipping_display", SHIPPING_INCLUDED))

if full.get("dealer_name"):
    dc1, dc2 = st.columns(2)
    dc1.metric("經銷商", full["dealer_name"])
    if full.get("dealer_price"):
        dc2.metric("經銷商價格", f"NT$ {full['dealer_price']:,.0f}")

# 明細
if full.get("line_items"):
    st.subheader("明細")
    items_df = pd.DataFrame(full["line_items"])
    display_cols = [
        "part_name", "part_category", "procurement_method",
        "cost_foreign", "freight_twd", "labor_hours",
        "landed_cost", "margin_rate", "part_price",
        "floor_applied", "labor_cost", "subtotal",
    ]
    col_name_map = {
        "part_name": "零件名稱", "part_category": "分類",
        "procurement_method": "取得方式",
        "cost_foreign": "外幣成本", "freight_twd": "運費",
        "labor_hours": "工時", "landed_cost": "到岸成本",
        "margin_rate": "毛利率", "part_price": "零件售價",
        "floor_applied": "保底", "labor_cost": "工資",
        "subtotal": "小計",
    }
    present_cols = [c for c in display_cols if c in items_df.columns]
    items_df = items_df[present_cols].rename(columns=col_name_map)
    st.dataframe(items_df, use_container_width=True, hide_index=True)

# 操作按鈕：草稿可跳轉編輯，已確認只能查看
st.divider()
if full["status"] == STATUS_DRAFT:
    if st.button("編輯此草稿", type="primary"):
        st.session_state["load_quote_id"] = full["id"]
        clear_quote_form()
        st.switch_page("pages/1_報價單.py")
else:
    st.info("已確認報價單不可再編輯。")
