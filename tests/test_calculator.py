import pytest
from src.calculator import calculate_line_item, calculate_totals, determine_shipping_display
from src.models import LineItemInput, LineItemResult, QuoteParams, QuoteTotals


def make_params(**kwargs):
    defaults = {
        "exchange_rate": 30.0,
        "tax_rate": 0.15,
        "labor_rate": 1200.0,
        "min_profit": 5000.0,
        "margin_rate_a": 0.30,
        "margin_rate_b": 0.50,
        "margin_rate_c": 0.30,
        "include_air_freight": True,
    }
    defaults.update(kwargs)
    return QuoteParams(**defaults)


# ── 毛利率 ────────────────────────────────────────────────────

class TestMarginRate:
    @pytest.mark.parametrize("category,expected", [
        ("A", 0.30),
        ("B", 0.50),
        ("C", 0.30),
    ])
    def test_margin_rate_by_category(self, category, expected):
        item = LineItemInput(part_category=category, procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params())
        assert result.margin_rate == pytest.approx(expected)

    def test_air_freight_no_bonus(self):
        """空運不再加成毛利率"""
        item = LineItemInput(part_category="A", procurement_method="空運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params())
        assert result.margin_rate == pytest.approx(0.30)

    def test_custom_margin_rates(self):
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params(margin_rate_a=0.40))
        assert result.margin_rate == pytest.approx(0.40)

    def test_margin_rate_zero(self):
        """毛利率為 0：售價 = 到岸成本（無加成）"""
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params(margin_rate_a=0.0, min_profit=0))
        # landed_cost=3450, price = 3450 / (1-0) = 3450
        assert result.part_price == pytest.approx(3450.0)

    def test_margin_rate_very_high(self):
        """毛利率 0.99：售價極大"""
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params(margin_rate_a=0.99, min_profit=0))
        # landed_cost=3450, price = 3450 / 0.01 = 345000
        assert result.part_price == pytest.approx(345000.0)


# ── 輸入驗證 ──────────────────────────────────────────────────

class TestInvalidInput:
    def test_invalid_part_category_raises(self):
        item = LineItemInput(part_category="Z")
        with pytest.raises(ValueError, match="未知零件分類"):
            calculate_line_item(item, make_params())

    def test_margin_rate_too_high_raises(self):
        item = LineItemInput(part_category="A")
        with pytest.raises(ValueError, match="毛利率不可"):
            calculate_line_item(item, make_params(margin_rate_a=1.0))

    def test_margin_rate_above_one_raises(self):
        item = LineItemInput(part_category="B")
        with pytest.raises(ValueError, match="毛利率不可"):
            calculate_line_item(item, make_params(margin_rate_b=1.5))


# ── 售價公式 ──────────────────────────────────────────────────

class TestPriceFormula:
    """新公式：售價 = 到岸成本 ÷ (1 - 毛利率)"""

    def test_price_formula_category_a(self):
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params(min_profit=0))
        assert result.part_price == pytest.approx(3450 / 0.70, rel=1e-2)

    def test_price_formula_category_b(self):
        item = LineItemInput(part_category="B", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params(min_profit=0))
        assert result.part_price == pytest.approx(6900.0, rel=1e-2)

    def test_price_with_freight(self):
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=500, labor_hours=0)
        result = calculate_line_item(item, make_params(min_profit=0))
        assert result.part_price == pytest.approx(3950 / 0.70, rel=1e-2)

    def test_zero_cost_zero_freight(self):
        """成本和運費皆為 0"""
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=0, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params(min_profit=0))
        assert result.cost_twd == 0.0
        assert result.landed_cost == 0.0
        assert result.part_price == 0.0


# ── 成本計算 ──────────────────────────────────────────────────

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
        assert result.tariff == pytest.approx(450.0)

    def test_landed_cost_with_freight(self):
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=500, labor_hours=0)
        result = calculate_line_item(item, make_params(exchange_rate=30.0))
        assert result.landed_cost == pytest.approx(3950.0)

    def test_inventory_freight_forced_to_zero(self):
        item = LineItemInput(part_category="A", procurement_method="庫存",
                             cost_foreign=100, freight_twd=999, labor_hours=0)
        result = calculate_line_item(item, make_params(exchange_rate=30.0))
        assert result.landed_cost == pytest.approx(3450.0)

    def test_labor_cost(self):
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=0, freight_twd=0, labor_hours=2.5)
        result = calculate_line_item(item, make_params(labor_rate=1200.0))
        assert result.labor_cost == pytest.approx(3000.0)


# ── 空運費計入 / 不計入 ───────────────────────────────────────

class TestAirFreightInclude:
    def test_air_freight_included(self):
        """空運費計入 → 運費加入到岸成本"""
        item = LineItemInput(part_category="A", procurement_method="空運",
                             cost_foreign=100, freight_twd=500, labor_hours=0)
        result = calculate_line_item(item, make_params(include_air_freight=True))
        assert result.landed_cost == pytest.approx(3950.0)

    def test_air_freight_excluded(self):
        """空運費不計入 → 運費不加入到岸成本"""
        item = LineItemInput(part_category="A", procurement_method="空運",
                             cost_foreign=100, freight_twd=500, labor_hours=0)
        result = calculate_line_item(item, make_params(include_air_freight=False))
        assert result.landed_cost == pytest.approx(3450.0)

    def test_sea_freight_unaffected_by_flag(self):
        """海運不受 include_air_freight 影響"""
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=500, labor_hours=0)
        result = calculate_line_item(item, make_params(include_air_freight=False))
        assert result.landed_cost == pytest.approx(3950.0)

    def test_inventory_unaffected_by_include_true(self):
        """庫存 + include_air_freight=True → 運費仍為 0"""
        item = LineItemInput(part_category="A", procurement_method="庫存",
                             cost_foreign=100, freight_twd=500, labor_hours=0)
        result = calculate_line_item(item, make_params(include_air_freight=True))
        assert result.landed_cost == pytest.approx(3450.0)

    def test_inventory_unaffected_by_include_false(self):
        """庫存 + include_air_freight=False → 運費仍為 0"""
        item = LineItemInput(part_category="A", procurement_method="庫存",
                             cost_foreign=100, freight_twd=500, labor_hours=0)
        result = calculate_line_item(item, make_params(include_air_freight=False))
        assert result.landed_cost == pytest.approx(3450.0)


# ── 保底機制 ──────────────────────────────────────────────────

class TestFloorMechanism:
    def test_no_floor_when_profit_sufficient(self):
        item = LineItemInput(part_category="B", procurement_method="海運",
                             cost_foreign=1000, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params(exchange_rate=30.0, min_profit=5000.0))
        assert result.floor_applied is False
        assert result.part_price == pytest.approx(69000.0)

    def test_floor_applied_when_profit_too_low(self):
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params(exchange_rate=30.0, min_profit=5000.0))
        assert result.floor_applied is True
        assert result.part_price == pytest.approx(8450.0)
        assert result.part_profit == pytest.approx(5000.0)

    def test_subtotal_includes_labor(self):
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=1.0)
        result = calculate_line_item(item, make_params(exchange_rate=30.0, min_profit=5000.0))
        assert result.subtotal == pytest.approx(8450.0 + 1200.0)

    def test_floor_with_zero_margin(self):
        """毛利率 0 + 保底：利潤為 0 < min_profit → 保底觸發"""
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params(
            margin_rate_a=0.0, min_profit=5000.0))
        assert result.floor_applied is True
        assert result.part_price == pytest.approx(8450.0)

    def test_floor_boundary_exact_min_profit(self):
        """利潤恰好等於 min_profit → 不觸發保底"""
        # 需要 raw_price - landed_cost >= min_profit
        # landed_cost / (1-r) - landed_cost = min_profit
        # landed_cost * (1/(1-r) - 1) = min_profit
        # 設 landed_cost=10000, r=0.50 → profit = 10000/0.5 - 10000 = 10000
        item = LineItemInput(part_category="B", procurement_method="海運",
                             cost_foreign=0, freight_twd=10000, labor_hours=0)
        result = calculate_line_item(item, make_params(
            exchange_rate=30.0, margin_rate_b=0.50, min_profit=10000.0))
        assert result.floor_applied is False

    def test_floor_disabled_when_min_profit_zero(self):
        """min_profit=0 → 保底永不觸發"""
        item = LineItemInput(part_category="A", procurement_method="海運",
                             cost_foreign=100, freight_twd=0, labor_hours=0)
        result = calculate_line_item(item, make_params(min_profit=0))
        assert result.floor_applied is False


# ── 合計 ──────────────────────────────────────────────────────

class TestTotals:
    def test_inventory_freight_excluded_from_total(self):
        results = [LineItemResult()]
        inputs = [LineItemInput(procurement_method="庫存", freight_twd=999)]
        totals = calculate_totals(results, inputs)
        assert totals.total_freight == pytest.approx(0.0)

    def test_totals_calculation(self):
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

    @pytest.mark.parametrize("coeff,expected", [
        (0.0, 0.0),
        (0.5, 5000.0),
        (0.75, 7500.0),
        (1.0, 10000.0),
    ])
    def test_dealer_price_coefficients(self, coeff, expected):
        results = [LineItemResult(part_price=10000, labor_cost=0, subtotal=10000)]
        inputs = [LineItemInput(freight_twd=0)]
        totals = calculate_totals(results, inputs, dealer_coefficient=coeff)
        assert totals.dealer_price == pytest.approx(expected)

    def test_empty_inputs(self):
        """空的明細列表 → 所有合計為 0"""
        totals = calculate_totals([], [])
        assert totals.total_parts == 0.0
        assert totals.total_labor == 0.0
        assert totals.total_freight == 0.0
        assert totals.grand_total == 0.0
        assert totals.dealer_price == 0.0

    def test_all_inventory_freight_zero(self):
        """全部庫存項目 → total_freight = 0"""
        results = [LineItemResult(), LineItemResult(), LineItemResult()]
        inputs = [
            LineItemInput(procurement_method="庫存", freight_twd=500),
            LineItemInput(procurement_method="庫存", freight_twd=300),
            LineItemInput(procurement_method="庫存", freight_twd=200),
        ]
        totals = calculate_totals(results, inputs)
        assert totals.total_freight == pytest.approx(0.0)

    def test_mixed_procurement_freight(self):
        """混合取得方式的運費合計"""
        results = [LineItemResult(), LineItemResult(), LineItemResult()]
        inputs = [
            LineItemInput(procurement_method="庫存", freight_twd=500),
            LineItemInput(procurement_method="海運", freight_twd=300),
            LineItemInput(procurement_method="空運", freight_twd=200),
        ]
        totals = calculate_totals(results, inputs)
        assert totals.total_freight == pytest.approx(500.0)  # 300 + 200

    def test_totals_air_freight_excluded(self):
        """include_air_freight=False → 空運運費不計入合計"""
        results = [LineItemResult(), LineItemResult(), LineItemResult()]
        inputs = [
            LineItemInput(procurement_method="庫存", freight_twd=500),
            LineItemInput(procurement_method="海運", freight_twd=300),
            LineItemInput(procurement_method="空運", freight_twd=200),
        ]
        totals = calculate_totals(results, inputs, include_air_freight=False)
        assert totals.total_freight == pytest.approx(300.0)  # only 海運

    def test_totals_air_freight_included(self):
        """include_air_freight=True → 空運運費計入合計"""
        results = [LineItemResult(), LineItemResult()]
        inputs = [
            LineItemInput(procurement_method="空運", freight_twd=400),
            LineItemInput(procurement_method="海運", freight_twd=300),
        ]
        totals = calculate_totals(results, inputs, include_air_freight=True)
        assert totals.total_freight == pytest.approx(700.0)


# ── 運費顯示判定 ──────────────────────────────────────────────

class TestShippingDisplay:
    def test_no_air_freight_items(self):
        """無空運項目 → 含運費"""
        inputs = [
            LineItemInput(procurement_method="海運"),
            LineItemInput(procurement_method="庫存"),
        ]
        assert determine_shipping_display(inputs, True) == "含運費"
        assert determine_shipping_display(inputs, False) == "含運費"

    def test_air_freight_included(self):
        """有空運 + 計入 → 含運費"""
        inputs = [LineItemInput(procurement_method="空運")]
        assert determine_shipping_display(inputs, True) == "含運費"

    def test_air_freight_excluded(self):
        """有空運 + 不計入 → 不含運費"""
        inputs = [LineItemInput(procurement_method="空運")]
        assert determine_shipping_display(inputs, False) == "不含運費"

    def test_mixed_with_air_excluded(self):
        """混合 + 空運不計入 → 不含運費"""
        inputs = [
            LineItemInput(procurement_method="海運"),
            LineItemInput(procurement_method="空運"),
        ]
        assert determine_shipping_display(inputs, False) == "不含運費"

    def test_empty_inputs(self):
        """空明細 → 含運費"""
        assert determine_shipping_display([], True) == "含運費"
        assert determine_shipping_display([], False) == "含運費"
