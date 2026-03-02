from src.models import LineItemInput, LineItemResult, QuoteParams, QuoteTotals
from config.defaults import MARGIN_TABLE, AIR_FREIGHT_BONUS


def calculate_line_item(item: LineItemInput, params: QuoteParams) -> LineItemResult:
    # 1. 毛利率
    if params.customer_type not in MARGIN_TABLE:
        raise ValueError(f"未知客戶類型：{params.customer_type!r}")
    if item.part_category not in MARGIN_TABLE[params.customer_type]:
        raise ValueError(f"未知零件分類：{item.part_category!r}")
    margin_rate = MARGIN_TABLE[params.customer_type][item.part_category]
    if item.procurement_method == "空運":
        margin_rate += AIR_FREIGHT_BONUS

    # 2. 台幣成本
    cost_twd = item.cost_foreign * params.exchange_rate

    # 3. 庫存運費強制 0
    freight = 0.0 if item.procurement_method == "庫存" else item.freight_twd

    # 4. 關稅與到岸成本
    tariff = cost_twd * params.tax_rate
    landed_cost = cost_twd + tariff + freight

    # 5. 零件售價（含保底）
    raw_price = landed_cost * (1 + margin_rate)
    part_profit = raw_price - landed_cost

    if part_profit < params.min_profit:
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


def calculate_totals(
    results: list[LineItemResult],
    inputs: list[LineItemInput],
) -> QuoteTotals:
    return QuoteTotals(
        total_parts=round(sum(r.part_price for r in results), 2),
        total_labor=round(sum(r.labor_cost for r in results), 2),
        total_freight=round(sum(0.0 if i.procurement_method == "庫存" else i.freight_twd for i in inputs), 2),
        grand_total=round(sum(r.subtotal for r in results), 2),
    )
