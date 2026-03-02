import pytest
from src.calculator import calculate_line_item, calculate_totals
from src.models import LineItemInput, QuoteParams, QuoteTotals


def make_params(**kwargs):
    defaults = {
        "exchange_rate": 30.0,
        "tax_rate": 0.15,
        "labor_rate": 1200.0,
        "min_profit": 5000.0,
        "customer_type": "終端客戶",
    }
    defaults.update(kwargs)
    return QuoteParams(**defaults)


class TestMarginRate:
    def test_end_customer_category_a(self):
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params())
        assert result.margin_rate == pytest.approx(0.50)

    def test_end_customer_category_b(self):
        item = LineItemInput(part_category="B", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params())
        assert result.margin_rate == pytest.approx(1.00)

    def test_end_customer_category_c(self):
        item = LineItemInput(part_category="C", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params())
        assert result.margin_rate == pytest.approx(0.50)

    def test_dealer_category_a(self):
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params(customer_type="經銷商"))
        assert result.margin_rate == pytest.approx(0.30)

    def test_dealer_category_b(self):
        item = LineItemInput(part_category="B", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params(customer_type="經銷商"))
        assert result.margin_rate == pytest.approx(0.70)

    def test_air_freight_adds_10_percent(self):
        item = LineItemInput(part_category="A", procurement_method="空運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params())
        assert result.margin_rate == pytest.approx(0.60)  # 50% + 10%

    def test_sea_freight_no_bonus(self):
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params())
        assert result.margin_rate == pytest.approx(0.50)


class TestCostCalculation:
    def test_cost_twd_conversion(self):
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params(exchange_rate=30.0))
        assert result.cost_twd == pytest.approx(3000.0)

    def test_tariff_calculation(self):
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params(exchange_rate=30.0, tax_rate=0.15))
        assert result.tariff == pytest.approx(450.0)  # 3000 * 0.15

    def test_landed_cost_with_freight(self):
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=500, labor_hours=0)
        result = calculate_line_item(item, make_params(exchange_rate=30.0))
        assert result.landed_cost == pytest.approx(3950.0)  # 3000 + 450 + 500

    def test_inventory_freight_forced_to_zero(self):
        item = LineItemInput(part_category="A", procurement_method="庫存",
                             cost_foreign=100, freight_twd=999, labor_hours=0)
        result = calculate_line_item(item, make_params(exchange_rate=30.0))
        assert result.landed_cost == pytest.approx(3450.0)  # freight ignored

    def test_labor_cost(self):
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=0, freight_twd=0, labor_hours=2.5)
        result = calculate_line_item(item, make_params(labor_rate=1200.0))
        assert result.labor_cost == pytest.approx(3000.0)


class TestFloorMechanism:
    def test_no_floor_when_profit_sufficient(self):
        # landed_cost=3450, margin=50% → raw_price=5175, profit=1725 → < 5000 → floor!
        # Use larger amount so floor NOT triggered
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=1000, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params(exchange_rate=30.0, min_profit=5000.0))
        # landed=34500, price=51750, profit=17250 → no floor
        assert result.floor_applied is False
        assert result.part_price == pytest.approx(51750.0)

    def test_floor_applied_when_profit_too_low(self):
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params(exchange_rate=30.0, min_profit=5000.0))
        # landed=3450, raw_price=5175, profit=1725 → < 5000 → floor
        assert result.floor_applied is True
        assert result.part_price == pytest.approx(8450.0)  # 3450 + 5000
        assert result.part_profit == pytest.approx(5000.0)

    def test_subtotal_includes_labor(self):
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=1.0)
        result = calculate_line_item(item, make_params(exchange_rate=30.0, min_profit=5000.0))
        assert result.subtotal == pytest.approx(8450.0 + 1200.0)


class TestTotals:
    def test_totals_calculation(self):
        from src.models import LineItemResult
        results = [
            LineItemResult(part_price=10000, labor_cost=2400, subtotal=12400,
                           part_profit=5000, floor_applied=False,
                           cost_twd=0, tariff=0, landed_cost=5000,
                           margin_rate=0.5),
            LineItemResult(part_price=8000, labor_cost=1200, subtotal=9200,
                           part_profit=5000, floor_applied=True,
                           cost_twd=0, tariff=0, landed_cost=3000,
                           margin_rate=0.5),
        ]
        inputs = [
            LineItemInput(freight_twd=500),
            LineItemInput(freight_twd=300),
        ]
        totals = calculate_totals(results, inputs)
        assert totals.total_parts   == pytest.approx(18000.0)
        assert totals.total_labor   == pytest.approx(3600.0)
        assert totals.total_freight == pytest.approx(800.0)
        assert totals.grand_total   == pytest.approx(21600.0)
