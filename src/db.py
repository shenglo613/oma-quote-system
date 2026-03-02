from __future__ import annotations
from typing import Optional
import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_client() -> Client:
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"],
    )


# ── Settings ──────────────────────────────────────────

def load_settings() -> dict[str, float]:
    """從 Supabase 讀取系統參數，回傳 {key: float}"""
    client = get_client()
    rows = client.table("settings").select("key, value").execute().data
    return {row["key"]: float(row["value"]) for row in rows}


def save_settings(tax_rate: float, labor_rate: float, min_profit: float) -> None:
    client = get_client()
    updates = [
        {"key": "tax_rate",   "value": str(tax_rate)},
        {"key": "labor_rate", "value": str(labor_rate)},
        {"key": "min_profit", "value": str(min_profit)},
    ]
    for u in updates:
        client.table("settings").upsert(u).execute()


# ── Quotes ────────────────────────────────────────────

def save_quote(quote_data: dict, line_items: list[dict]) -> str:
    """
    儲存或更新報價單。
    quote_data 包含 id（更新）或不含 id（新增）。
    回傳 quote id。
    """
    client = get_client()

    if "id" in quote_data and quote_data["id"]:
        # 更新：從 payload 排除 id，避免 PostgREST 收到不必要的主鍵欄位
        quote_id = quote_data["id"]
        update_payload = {k: v for k, v in quote_data.items() if k != "id"}
        client.table("quotes").update(update_payload).eq("id", quote_id).execute()
        client.table("line_items").delete().eq("quote_id", quote_id).execute()
    else:
        # 新增
        quote_data.pop("id", None)
        res = client.table("quotes").insert(quote_data).execute()
        quote_id = res.data[0]["id"]

    # 重新插入明細（含 sort_order）；用新 dict 避免 mutate 呼叫方的資料
    items_to_insert = [
        {**item, "quote_id": quote_id, "sort_order": i}
        for i, item in enumerate(line_items)
    ]
    if items_to_insert:
        client.table("line_items").insert(items_to_insert).execute()

    return quote_id


def load_quote(quote_id: str) -> Optional[dict]:
    """讀取報價單主資料 + 明細；找不到時回傳 None"""
    client = get_client()
    try:
        quote = client.table("quotes").select("*").eq("id", quote_id).single().execute().data
    except Exception:
        return None
    if not quote:
        return None
    items = (
        client.table("line_items")
        .select("*")
        .eq("quote_id", quote_id)
        .order("sort_order")
        .execute()
        .data
    )
    quote["line_items"] = items
    return quote


def list_quotes(
    status: Optional[str] = None,
    customer_name: Optional[str] = None,
) -> list[dict]:
    """列出報價單（for 報價記錄頁）"""
    client = get_client()
    q = client.table("quotes").select(
        "id, quote_number, quote_date, customer_type, customer_name, status, created_at"
    ).order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    if customer_name:
        q = q.ilike("customer_name", f"%{customer_name}%")
    return q.execute().data


def confirm_quote(quote_id: str) -> None:
    """將報價單狀態改為已確認"""
    get_client().table("quotes").update({"status": "已確認"}).eq("id", quote_id).execute()


def quote_number_exists(quote_number: str) -> bool:
    """檢查報價單號是否已存在"""
    res = get_client().table("quotes").select("id").eq("quote_number", quote_number).execute()
    return len(res.data) > 0
