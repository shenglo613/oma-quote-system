from src.models import LineItemInput, LineItemResult, QuoteParams, QuoteTotals
from config.defaults import PROC_INVENTORY, PROC_AIR, SHIPPING_INCLUDED, SHIPPING_EXCLUDED


def calculate_line_item(item: LineItemInput, params: QuoteParams) -> LineItemResult:
    # 1. 毛利率（依零件分類）
    margin_rates = {
        "A": params.margin_rate_a,
        "B": params.margin_rate_b,
        "C": params.margin_rate_c,
    }
    if item.part_category not in margin_rates:
        raise ValueError(f"未知零件分類：{item.part_category!r}")
    margin_rate = margin_rates[item.part_category]
    if margin_rate < 0:
        raise ValueError(f"毛利率不可為負數：{margin_rate}")
    if margin_rate >= 1.0:
        raise ValueError(f"毛利率不可 >= 100%：{margin_rate}")

    # 2. 台幣成本
    cost_twd = item.cost_foreign * params.exchange_rate

    # 3. 運費：庫存強制 0，空運依 include_air_freight 決定
    if item.procurement_method == PROC_INVENTORY:
        freight = 0.0
    elif item.procurement_method == PROC_AIR and not params.include_air_freight:
        freight = 0.0
    else:
        freight = item.freight_twd

    # 4. 關稅與到岸成本
    tariff = cost_twd * params.tax_rate
    landed_cost = cost_twd + tariff + freight

    # 5. 零件售價：售價 = 到岸成本 ÷ (1 - 毛利率)，含保底
    raw_price = landed_cost / (1 - margin_rate)
    part_profit = raw_price - landed_cost

    if landed_cost > 0 and part_profit < params.min_profit:
        part_price = landed_cost + params.min_profit
        floor_applied = True
    else:
        part_price = raw_price
        floor_applied = False

    part_profit = part_price - landed_cost

    # 6. 工資與小計
    labor_cost = item.labor_hours * params.labor_rate
    subtotal = part_price + labor_cost

    return LineItemResult(
        cost_twd=round(cost_twd, 2),
        tariff=round(tariff, 2),
        landed_cost=round(landed_cost, 2),
        margin_rate=round(margin_rate, 4),
        part_price=round(part_price, 2),
        labor_cost=round(labor_cost, 2),
        subtotal=round(subtotal, 2),
        part_profit=round(part_profit, 2),
        floor_applied=floor_applied,
    )


def _effective_freight(item: LineItemInput, include_air_freight: bool) -> float:
    """計算單一項目的有效運費（與 calculate_line_item 一致的邏輯）"""
    if item.procurement_method == PROC_INVENTORY:
        return 0.0
    if item.procurement_method == PROC_AIR and not include_air_freight:
        return 0.0
    return item.freight_twd


def calculate_totals(
    results: list[LineItemResult],
    inputs: list[LineItemInput],
    dealer_coefficient: float = 0.0,
    include_air_freight: bool = True,
) -> QuoteTotals:
    if dealer_coefficient < 0:
        raise ValueError(f"經銷商係數不可為負數：{dealer_coefficient}")
    grand_total = round(sum(r.subtotal for r in results), 2)
    return QuoteTotals(
        total_parts=round(sum(r.part_price for r in results), 2),
        total_labor=round(sum(r.labor_cost for r in results), 2),
        total_freight=round(sum(
            _effective_freight(i, include_air_freight) for i in inputs
        ), 2),
        grand_total=grand_total,
        dealer_price=round(grand_total * dealer_coefficient, 2) if dealer_coefficient else 0.0,
    )


def determine_shipping_display(
    inputs: list[LineItemInput],
    include_air_freight: bool,
) -> str:
    """根據明細項目與空運費設定，決定報價單運費顯示文字"""
    has_air = any(i.procurement_method == PROC_AIR for i in inputs)
    if not has_air or include_air_freight:
        return SHIPPING_INCLUDED
    return SHIPPING_EXCLUDED
