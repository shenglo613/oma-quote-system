import streamlit as st
import pandas as pd
from src.models import LineItemInput, LineItemResult, QuoteParams
from config.defaults import PART_CATEGORIES, PROCUREMENT_METHODS, CURRENCIES


def require_login():
    """若未登入，中止頁面執行"""
    if not st.session_state.get("username"):
        st.warning("請先登入")
        st.stop()


def get_role() -> str:
    return st.session_state.get("role", "staff")


def build_input_df(items: list[LineItemInput]) -> pd.DataFrame:
    """將 LineItemInput list 轉成 data_editor 用的 DataFrame"""
    return pd.DataFrame([{
        "零件名稱": i.part_name,
        "分類": i.part_category,
        "取得方式": i.procurement_method,
        "外幣成本": i.cost_foreign,
        "運費(TWD)": i.freight_twd,
        "工時(hr)": i.labor_hours,
    } for i in items])


def parse_input_df(df: pd.DataFrame) -> list[LineItemInput]:
    """DataFrame 轉回 LineItemInput list"""
    items = []
    for _, row in df.iterrows():
        items.append(LineItemInput(
            part_name=str(row.get("零件名稱", "")),
            part_category=str(row.get("分類", "A")),
            procurement_method=str(row.get("取得方式", "海運")),
            cost_foreign=float(row.get("外幣成本", 0) or 0),
            freight_twd=float(row.get("運費(TWD)", 0) or 0),
            labor_hours=float(row.get("工時(hr)", 0) or 0),
        ))
    return items


def compute_results_df(results: list[LineItemResult]) -> pd.DataFrame:
    """將預計算結果轉成顯示用 DataFrame（不重複計算）"""
    rows = []
    for r in results:
        rows.append({
            "台幣成本": f"{r.cost_twd:,.0f}",
            "關稅": f"{r.tariff:,.0f}",
            "到岸成本": f"{r.landed_cost:,.0f}",
            "毛利率": f"{r.margin_rate:.0%}",
            "零件售價": f"{r.part_price:,.0f}",
            "⚠保底": "是" if r.floor_applied else "",
            "工資": f"{r.labor_cost:,.0f}",
            "小計": f"{r.subtotal:,.0f}",
        })
    return pd.DataFrame(rows)
