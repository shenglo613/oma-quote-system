from dataclasses import dataclass, field

from config.defaults import (
    TAX_RATE, LABOR_RATE, MIN_PROFIT,
    MARGIN_RATE_A, MARGIN_RATE_B, MARGIN_RATE_C,
)


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
    tax_rate: float = field(default=TAX_RATE)
    labor_rate: float = field(default=LABOR_RATE)
    min_profit: float = field(default=MIN_PROFIT)
    margin_rate_a: float = field(default=MARGIN_RATE_A)
    margin_rate_b: float = field(default=MARGIN_RATE_B)
    margin_rate_c: float = field(default=MARGIN_RATE_C)
    include_air_freight: bool = True


@dataclass
class QuoteTotals:
    """報價單合計"""
    total_parts: float = 0.0
    total_labor: float = 0.0
    total_freight: float = 0.0
    grand_total: float = 0.0
    dealer_price: float = 0.0
