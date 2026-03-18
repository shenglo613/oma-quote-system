import json
import streamlit as st
import pandas as pd
from dataclasses import asdict
from datetime import date

from src.ui_helpers import (
    require_login, get_role, is_manager,
    build_input_df, parse_input_df, compute_results_df, clear_quote_form,
)
from src.models import LineItemInput, LineItemResult, QuoteParams, QuoteTotals
from src.calculator import calculate_line_item, calculate_totals, determine_shipping_display
from src.db import load_settings, load_dealers, load_part_categories, save_quote, load_quote, quote_number_exists
from src.export_csv import build_csv_bytes
from src.export_pdf import build_pdf_bytes
from config.defaults import (
    CUSTOMER_TYPES, CUSTOMER_TYPE_DEALER,
    PART_CATEGORIES, PROCUREMENT_METHODS, CURRENCIES,
    PROC_INVENTORY,
    TAX_RATE, LABOR_RATE, MIN_PROFIT,
    MARGIN_RATE_A, MARGIN_RATE_B, MARGIN_RATE_C,
    DEALER_COEFFICIENT, STATUS_DRAFT, STATUS_CONFIRMED,
)


# ── 模組級快取：只在輸入變動時才重新產生 PDF / CSV ──────────────────────
@st.cache_data(show_spinner=False)
def _cached_pdf(meta_json: str, inputs_json: str, results_json: str,
                totals_json: str, params_json: str) -> bytes:
    meta = json.loads(meta_json)
    _inputs  = [LineItemInput(**d)  for d in json.loads(inputs_json)]
    _results = [LineItemResult(**d) for d in json.loads(results_json)]
    _totals  = QuoteTotals(**json.loads(totals_json))
    _params  = QuoteParams(**json.loads(params_json))
    return build_pdf_bytes(meta, _inputs, _results, _totals, _params)


@st.cache_data(show_spinner=False)
def _cached_csv(meta_json: str, inputs_json: str, results_json: str,
                totals_json: str, params_json: str) -> bytes:
    meta = json.loads(meta_json)
    _inputs  = [LineItemInput(**d)  for d in json.loads(inputs_json)]
    _results = [LineItemResult(**d) for d in json.loads(results_json)]
    _totals  = QuoteTotals(**json.loads(totals_json))
    _params  = QuoteParams(**json.loads(params_json))
    return build_csv_bytes(meta, _inputs, _results, _totals, _params)


# ════════════════════════════════════════════════════════════
st.set_page_config(page_title="報價單 — OMA", layout="wide")
require_login()

# ── 從 DB 載入報價（由報價記錄頁設定 load_quote_id 觸發）──────────────────
if "load_quote_id" in st.session_state:
    loaded = load_quote(st.session_state.pop("load_quote_id"))
    if loaded:
        st.session_state["quote_id"]     = loaded["id"]
        st.session_state["quote_status"] = loaded["status"]
        st.session_state["qf_quote_number"]  = loaded["quote_number"]
        st.session_state["qf_customer_type"] = loaded["customer_type"]
        st.session_state["qf_customer_name"] = loaded["customer_name"]
        st.session_state["qf_currency"]      = loaded["currency"]
        st.session_state["qf_exchange_rate"] = float(loaded["exchange_rate"])
        st.session_state["qf_notes"]         = loaded.get("notes", "")
        st.session_state["qf_quote_date"]    = date.fromisoformat(str(loaded["quote_date"]))
        st.session_state["qf_dealer_name"]   = loaded.get("dealer_name", "")
        st.session_state["qf_include_air_freight"] = loaded.get("include_air_freight", True)
        # 還原報價時的毛利率快照
        if loaded.get("margin_rate_a") is not None:
            st.session_state["loaded_margin_a"] = float(loaded["margin_rate_a"])
            st.session_state["loaded_margin_b"] = float(loaded["margin_rate_b"])
            st.session_state["loaded_margin_c"] = float(loaded["margin_rate_c"])
        if loaded.get("line_items"):
            st.session_state["line_items"] = [
                LineItemInput(
                    part_name=item["part_name"],
                    part_category=item["part_category"],
                    procurement_method=item["procurement_method"],
                    cost_foreign=float(item["cost_foreign"]),
                    freight_twd=float(item["freight_twd"]),
                    labor_hours=float(item["labor_hours"]),
                )
                for item in loaded["line_items"]
            ]

# ── 初始化 session state ──────────────────────────────────────────────────
if "line_items" not in st.session_state:
    st.session_state["line_items"] = [LineItemInput()]
if "quote_id" not in st.session_state:
    st.session_state["quote_id"] = None
if "quote_status" not in st.session_state:
    st.session_state["quote_status"] = STATUS_DRAFT
if "qf_include_air_freight" not in st.session_state:
    st.session_state["qf_include_air_freight"] = True

is_confirmed = st.session_state["quote_status"] == STATUS_CONFIRMED

col_title, col_new = st.columns([6, 1])
with col_title:
    st.title("報價單")
with col_new:
    st.write("")
    if st.button("＋ 新增報價", use_container_width=True):
        clear_quote_form()
        st.rerun()

if is_confirmed:
    st.success("此報價單已確認，不可再編輯。")

# ══════════════════════════════════════════
# SECTION 1：報價單主資料
# ══════════════════════════════════════════
with st.expander("報價單資訊", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        quote_number = st.text_input(
            "報價單號 *", placeholder="例：Q-20260302-001",
            key="qf_quote_number", disabled=is_confirmed,
        )
        customer_type = st.selectbox(
            "客戶類型 *", CUSTOMER_TYPES,
            key="qf_customer_type", disabled=is_confirmed,
        )
        currency = st.selectbox(
            "幣別", CURRENCIES,
            key="qf_currency", disabled=is_confirmed,
        )
    with c2:
        quote_date = st.date_input(
            "報價日期 *", value=date.today(),
            key="qf_quote_date", disabled=is_confirmed,
        )
        if customer_type == CUSTOMER_TYPE_DEALER:
            dealers_list = load_dealers()
            if not dealers_list:
                st.warning("尚未設定經銷商名單，請至系統設定頁新增。")
                dealer_name = st.text_input(
                    "經銷商名稱 *",
                    key="qf_dealer_name", disabled=is_confirmed,
                )
            else:
                dealer_name = st.selectbox(
                    "經銷商名稱 *", dealers_list,
                    key="qf_dealer_name", disabled=is_confirmed,
                )
            customer_name = dealer_name
        else:
            customer_name = st.text_input(
                "客戶名稱 *",
                key="qf_customer_name", disabled=is_confirmed,
            )
            dealer_name = ""
        exchange_rate = st.number_input(
            "匯率 *", min_value=0.0001, value=32.0,
            step=0.01, format="%.4f",
            key="qf_exchange_rate", disabled=is_confirmed,
        )

    notes = st.text_area("備註", height=68, key="qf_notes", disabled=is_confirmed)

# ══════════════════════════════════════════
# SECTION 2：系統參數
# ══════════════════════════════════════════
with st.expander("系統參數", expanded=False):
    db_settings = load_settings()
    cat_labels = load_part_categories()
    params_disabled = is_confirmed or not is_manager()

    st.markdown("**毛利率設定**（依零件分類）")
    # 載入舊報價時，優先使用該報價快照的毛利率
    _mr_a = st.session_state.pop("loaded_margin_a", db_settings.get("margin_rate_a", MARGIN_RATE_A))
    _mr_b = st.session_state.pop("loaded_margin_b", db_settings.get("margin_rate_b", MARGIN_RATE_B))
    _mr_c = st.session_state.pop("loaded_margin_c", db_settings.get("margin_rate_c", MARGIN_RATE_C))
    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        st.caption(f"**A** — {cat_labels.get('A', '')}")
        margin_rate_a = st.number_input(
            "分類 A 毛利率", value=_mr_a,
            min_value=0.0, max_value=0.99, step=0.01, format="%.2f",
            disabled=params_disabled,
        )
    with mc2:
        st.caption(f"**B** — {cat_labels.get('B', '')}")
        margin_rate_b = st.number_input(
            "分類 B 毛利率", value=_mr_b,
            min_value=0.0, max_value=0.99, step=0.01, format="%.2f",
            disabled=params_disabled,
        )
    with mc3:
        st.caption(f"**C** — {cat_labels.get('C', '')}")
        margin_rate_c = st.number_input(
            "分類 C 毛利率", value=_mr_c,
            min_value=0.0, max_value=0.99, step=0.01, format="%.2f",
            disabled=params_disabled,
        )

    st.markdown("**其他參數**")
    pc1, pc2, pc3, pc4 = st.columns(4)
    with pc1:
        tax_rate = st.number_input(
            "關稅率", value=db_settings.get("tax_rate", TAX_RATE),
            min_value=0.0, max_value=1.0, step=0.01, format="%.2f",
            disabled=params_disabled,
        )
    with pc2:
        labor_rate = st.number_input(
            "工資單價（NT$/hr）", value=db_settings.get("labor_rate", LABOR_RATE),
            min_value=0.0, step=100.0, disabled=params_disabled,
        )
    with pc3:
        min_profit = st.number_input(
            "最低毛利保底（NT$）", value=db_settings.get("min_profit", MIN_PROFIT),
            min_value=0.0, step=500.0, disabled=params_disabled,
        )
    with pc4:
        dealer_coefficient = st.number_input(
            "經銷商係數", value=db_settings.get("dealer_coefficient", DEALER_COEFFICIENT),
            min_value=0.0, max_value=1.0, step=0.01, format="%.2f",
            disabled=params_disabled,
        )

# ══════════════════════════════════════════
# SECTION 3：空運費選項
# ══════════════════════════════════════════
include_air_freight = st.checkbox(
    "計入空運費（勾選＝含運費，不勾＝不含運費）",
    key="qf_include_air_freight",
    disabled=is_confirmed,
)

params = QuoteParams(
    exchange_rate=exchange_rate,
    tax_rate=tax_rate,
    labor_rate=labor_rate,
    min_profit=min_profit,
    margin_rate_a=margin_rate_a,
    margin_rate_b=margin_rate_b,
    margin_rate_c=margin_rate_c,
    include_air_freight=include_air_freight,
)

# ══════════════════════════════════════════
# SECTION 4：明細表
# ══════════════════════════════════════════
st.subheader("明細")
_cat_help = " ／ ".join(f"**{c}**: {cat_labels.get(c, '')}" for c in PART_CATEGORIES)
st.caption(f"分類說明：{_cat_help}")

input_df = build_input_df(st.session_state["line_items"])

edited_df = st.data_editor(
    input_df,
    use_container_width=True,
    num_rows="dynamic" if not is_confirmed else "fixed",
    column_config={
        "分類": st.column_config.SelectboxColumn("分類", options=PART_CATEGORIES, required=True),
        "取得方式": st.column_config.SelectboxColumn("取得方式", options=PROCUREMENT_METHODS, required=True),
        "外幣成本": st.column_config.NumberColumn("外幣成本", min_value=0.0, format="%.4f"),
        "運費(TWD)": st.column_config.NumberColumn("運費(TWD)", min_value=0.0, format="%.0f"),
        "工時(hr)": st.column_config.NumberColumn("工時(hr)", min_value=0.0, format="%.2f"),
    },
    disabled=is_confirmed,
    key="line_item_editor",
)

# 只在可編輯時才從 editor 更新 session state
if not is_confirmed:
    st.session_state["line_items"] = parse_input_df(edited_df)
inputs = st.session_state["line_items"]

# 計算
results = [calculate_line_item(inp, params) for inp in inputs]
_dealer_coeff = dealer_coefficient if customer_type == CUSTOMER_TYPE_DEALER else 0.0
totals = calculate_totals(results, inputs, dealer_coefficient=_dealer_coeff,
                          include_air_freight=include_air_freight)

if results:
    st.dataframe(compute_results_df(results), use_container_width=True)

# ══════════════════════════════════════════
# SECTION 5：運費註記
# ══════════════════════════════════════════
shipping_display = determine_shipping_display(inputs, include_air_freight)
st.info(f"運費狀態：**{shipping_display}**")

# ══════════════════════════════════════════
# SECTION 6：KPI
# ══════════════════════════════════════════
st.divider()
if customer_type == CUSTOMER_TYPE_DEALER:
    k1, k2, k3, k4, k5 = st.columns(5)
else:
    k1, k2, k3, k4 = st.columns(4)
    k5 = None

k1.metric("零件合計", f"NT$ {totals.total_parts:,.0f}")
k2.metric("工資合計", f"NT$ {totals.total_labor:,.0f}")
k3.metric("運費合計", f"NT$ {totals.total_freight:,.0f}")
k4.metric("總報價",   f"NT$ {totals.grand_total:,.0f}")
if k5 is not None:
    k5.metric("經銷商價格", f"NT$ {totals.dealer_price:,.0f}")

# ══════════════════════════════════════════
# SECTION 7：操作按鈕
# ══════════════════════════════════════════
st.divider()


def _build_quote_data(status: str) -> dict:
    return {
        "id":                  st.session_state["quote_id"],
        "quote_number":        quote_number,
        "quote_date":          str(quote_date),
        "customer_type":       customer_type,
        "customer_name":       customer_name,
        "currency":            currency,
        "exchange_rate":       exchange_rate,
        "notes":               notes,
        "status":              status,
        "tax_rate":            tax_rate,
        "labor_rate":          labor_rate,
        "min_profit":          min_profit,
        "margin_rate_a":       margin_rate_a,
        "margin_rate_b":       margin_rate_b,
        "margin_rate_c":       margin_rate_c,
        "include_air_freight": include_air_freight,
        "dealer_name":         dealer_name,
        "dealer_coefficient":  dealer_coefficient,
        "dealer_price":        totals.dealer_price if customer_type == CUSTOMER_TYPE_DEALER else 0.0,
        "shipping_display":    shipping_display,
    }


def _build_line_items_data() -> list[dict]:
    return [
        {
            "part_name":          inp.part_name,
            "part_category":      inp.part_category,
            "procurement_method": inp.procurement_method,
            "cost_foreign":       inp.cost_foreign,
            "freight_twd":        inp.freight_twd if inp.procurement_method != PROC_INVENTORY else 0,
            "labor_hours":        inp.labor_hours,
            "cost_twd":           res.cost_twd,
            "tariff":             res.tariff,
            "landed_cost":        res.landed_cost,
            "margin_rate":        res.margin_rate,
            "part_price":         res.part_price,
            "labor_cost":         res.labor_cost,
            "subtotal":           res.subtotal,
            "part_profit":        res.part_profit,
            "floor_applied":      res.floor_applied,
        }
        for inp, res in zip(inputs, results)
    ]


def _validate() -> bool:
    if not quote_number:
        st.error("請填寫報價單號")
        return False
    if not customer_name:
        st.error("請填寫客戶名稱")
        return False
    if not any(inp.part_name.strip() for inp in inputs):
        st.error("請至少填寫一筆有名稱的零件明細")
        return False
    if not st.session_state["quote_id"] and quote_number_exists(quote_number):
        st.error(f"報價單號 {quote_number!r} 已存在，請使用不同的編號")
        return False
    return True


if not is_confirmed:
    btn1, btn2 = st.columns(2)
    with btn1:
        if st.button("儲存草稿", use_container_width=True):
            if _validate():
                try:
                    qid = save_quote(_build_quote_data(STATUS_DRAFT), _build_line_items_data())
                    st.session_state["quote_id"] = qid
                    st.session_state["quote_status"] = STATUS_DRAFT
                    st.success(f"草稿已儲存（{quote_number}）")
                except Exception as e:
                    st.error(f"儲存失敗：{e}")
    with btn2:
        if st.button("確認報價", use_container_width=True):
            if _validate():
                try:
                    qid = save_quote(_build_quote_data(STATUS_CONFIRMED), _build_line_items_data())
                    st.session_state["quote_id"] = qid
                    st.session_state["quote_status"] = STATUS_CONFIRMED
                    st.success(f"報價已確認（{quote_number}）")
                    st.rerun()
                except Exception as e:
                    st.error(f"確認失敗：{e}")

# ── 匯出 ──────────────────────────────────────────────────────────────────
quote_meta = {
    "quote_number":     quote_number,
    "quote_date":       str(quote_date),
    "customer_type":    customer_type,
    "customer_name":    customer_name,
    "currency":         currency,
    "notes":            notes,
    "status":           st.session_state["quote_status"],
    "dealer_name":      dealer_name,
    "shipping_display": shipping_display,
    "dealer_price":     totals.dealer_price,
}

_meta_json    = json.dumps(quote_meta)
_inputs_json  = json.dumps([asdict(i) for i in inputs])
_results_json = json.dumps([asdict(r) for r in results])
_totals_json  = json.dumps(asdict(totals))
_params_json  = json.dumps(asdict(params))

exp_c1, exp_c2 = st.columns(2)
with exp_c1:
    st.download_button(
        "匯出 CSV",
        data=_cached_csv(_meta_json, _inputs_json, _results_json, _totals_json, _params_json),
        file_name=f"{quote_number or 'quote'}.csv",
        mime="text/csv",
        use_container_width=True,
    )
with exp_c2:
    st.download_button(
        "下載 PDF",
        data=_cached_pdf(_meta_json, _inputs_json, _results_json, _totals_json, _params_json),
        file_name=f"{quote_number or 'quote'}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
