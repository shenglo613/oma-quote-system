import streamlit as st
import pandas as pd
from src.ui_helpers import require_login
from src.db import list_quotes, load_quote

st.set_page_config(page_title="報價記錄 — OMA", layout="wide")
require_login()

st.title("📂 報價記錄")

# ── 篩選列 ──────────────────────────────────────────────────
f1, f2 = st.columns(2)
with f1:
    filter_status = st.selectbox("狀態", ["全部", "草稿", "已確認"])
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
info_cols = st.columns(4)
info_cols[0].metric("報價單號", full["quote_number"])
info_cols[1].metric("日期",     str(full["quote_date"]))
info_cols[2].metric("客戶名稱", full["customer_name"])
info_cols[3].metric("狀態",     full["status"])

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
    items_df = items_df[[c for c in display_cols if c in items_df.columns]]
    items_df.columns = [
        "零件名稱", "分類", "取得方式",
        "外幣成本", "運費", "工時",
        "到岸成本", "毛利率", "零件售價",
        "保底", "工資", "小計",
    ]
    st.dataframe(items_df, use_container_width=True, hide_index=True)

# 操作按鈕：草稿可跳轉編輯，已確認只能查看
st.divider()
if full["status"] == "草稿":
    if st.button("✏️ 編輯此草稿", type="primary"):
        st.session_state["load_quote_id"] = full["id"]
        # 清除舊的 quote form session state，讓載入觸發器正常工作
        for key in ["quote_id", "quote_status", "line_items",
                    "qf_quote_number", "qf_customer_type", "qf_customer_name",
                    "qf_currency", "qf_exchange_rate", "qf_notes", "qf_quote_date"]:
            st.session_state.pop(key, None)
        st.switch_page("pages/1_報價單.py")
else:
    st.info("已確認報價單不可再編輯。")
