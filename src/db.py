from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
import json
import streamlit as st
from supabase import create_client, Client

from config.defaults import STATUS_CONFIRMED


@st.cache_resource
def get_client() -> Client:
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"],
    )


# ── Settings ──────────────────────────────────────────

@st.cache_data(ttl=300)
def load_settings() -> dict[str, float]:
    """從 Supabase 讀取系統參數，回傳 {key: float}；快取 5 分鐘"""
    client = get_client()
    rows = client.table("settings").select("key, value").execute().data
    result = {}
    for row in rows:
        key = row["key"]
        val = row["value"]
        if key == "dealers":
            continue  # dealers 由 load_dealers 處理
        try:
            result[key] = float(val)
        except (ValueError, TypeError):
            pass
    return result


def save_settings(
    tax_rate: float,
    labor_rate: float,
    min_profit: float,
    margin_rate_a: float,
    margin_rate_b: float,
    margin_rate_c: float,
    dealer_coefficient: float,
) -> None:
    client = get_client()
    updates = [
        {"key": "tax_rate",           "value": str(tax_rate)},
        {"key": "labor_rate",         "value": str(labor_rate)},
        {"key": "min_profit",         "value": str(min_profit)},
        {"key": "margin_rate_a",      "value": str(margin_rate_a)},
        {"key": "margin_rate_b",      "value": str(margin_rate_b)},
        {"key": "margin_rate_c",      "value": str(margin_rate_c)},
        {"key": "dealer_coefficient", "value": str(dealer_coefficient)},
    ]
    for u in updates:
        client.table("settings").upsert(u, on_conflict="key").execute()
    load_settings.clear()


# ── Dealers ───────────────────────────────────────────

@st.cache_data(ttl=300)
def load_dealers() -> list[str]:
    """從 settings 表讀取經銷商名單"""
    client = get_client()
    rows = client.table("settings").select("value").eq("key", "dealers").execute().data
    if rows:
        try:
            return json.loads(rows[0]["value"])
        except (json.JSONDecodeError, TypeError):
            pass
    from config.defaults import DEALERS
    return DEALERS


def save_dealers(dealers: list[str]) -> None:
    client = get_client()
    client.table("settings").upsert(
        {"key": "dealers", "value": json.dumps(dealers, ensure_ascii=False)},
        on_conflict="key",
    ).execute()
    load_dealers.clear()


# ── Part Categories ───────────────────────────────────

@st.cache_data(ttl=300)
def load_part_categories() -> dict[str, str]:
    """從 settings 表讀取零件分類標籤，回傳 {code: label}"""
    client = get_client()
    rows = client.table("settings").select("value").eq("key", "part_categories").execute().data
    if rows:
        try:
            return json.loads(rows[0]["value"])
        except (json.JSONDecodeError, TypeError):
            pass
    from config.defaults import PART_CATEGORY_LABELS
    return PART_CATEGORY_LABELS


def save_part_categories(categories: dict[str, str]) -> None:
    client = get_client()
    client.table("settings").upsert(
        {"key": "part_categories", "value": json.dumps(categories, ensure_ascii=False)},
        on_conflict="key",
    ).execute()
    load_part_categories.clear()


# ── Quotes ────────────────────────────────────────────

def save_quote(quote_data: dict, line_items: list[dict]) -> str:
    """
    儲存或更新報價單。
    quote_data 包含 id（更新）或不含 id（新增）。
    回傳 quote id。已確認的報價單不可修改，否則拋 ValueError。
    """
    client = get_client()

    if "id" in quote_data and quote_data["id"]:
        # 更新：先確認現有狀態，禁止覆寫已確認單
        quote_id = quote_data["id"]
        existing = client.table("quotes").select("status").eq("id", quote_id).execute()
        if existing.data and existing.data[0].get("status") == STATUS_CONFIRMED:
            raise ValueError("已確認的報價單不可修改")
        update_payload = {k: v for k, v in quote_data.items() if k != "id"}
        update_payload["updated_at"] = datetime.now(timezone.utc).isoformat()
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
    result = client.table("quotes").select("*").eq("id", quote_id).execute()
    if not result.data:
        return None
    quote = result.data[0]
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


def quote_number_exists(quote_number: str, exclude_id: str | None = None) -> bool:
    """檢查報價單號是否已存在（可排除指定 ID）"""
    q = get_client().table("quotes").select("id").eq("quote_number", quote_number)
    if exclude_id:
        q = q.neq("id", exclude_id)
    return len(q.execute().data) > 0
