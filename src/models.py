from dataclasses import dataclass


@dataclass
class LineItemInput:
    """使用者輸入的原始資料（可編輯）"""
    part_name: str = ""
    part_category: str = "A"           # 'A' | 'B' | 'C'
    procurement_method: str = "海運"   # '庫存' | '海運' | '空運'
    cost_foreign: float = 0.0
    freight_twd: float = 0.0
    labor_hours: float = 0.0


@dataclass
class LineItemResult:
    """計算後的結果（唯讀）"""
    cost_twd: float = 0.0
    tariff: float = 0.0
    landed_cost: float = 0.0
    margin_rate: float = 0.0
    part_price: float = 0.0
    labor_cost: float = 0.0
    subtotal: float = 0.0
    part_profit: float = 0.0
    floor_applied: bool = False


@dataclass
class QuoteParams:
    """報價單計算參數（快照用）"""
    exchange_rate: float = 1.0
    tax_rate: float = 0.15
    labor_rate: float = 1200.0
    min_profit: float = 5000.0
    customer_type: str = "終端客戶"


@dataclass
class QuoteTotals:
    """報價單合計"""
    total_parts: float = 0.0
    total_labor: float = 0.0
    total_freight: float = 0.0
    grand_total: float = 0.0
