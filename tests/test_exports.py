"""
Tests for src/export_csv.py and src/export_pdf.py
"""
import csv
import io

from src.export_csv import build_csv_bytes
from src.export_pdf import build_pdf_bytes
from src.models import LineItemInput, LineItemResult, QuoteParams, QuoteTotals


def _make_fixtures():
    meta = {
        "quote_number": "Q-TEST-001",
        "quote_date": "2026-03-03",
        "customer_type": "終端客戶",
        "customer_name": "測試公司",
        "currency": "USD",
        "notes": "備註",
        "status": "草稿",
        "shipping_display": "含運費",
        "dealer_name": "",
        "dealer_price": 0,
    }
    inputs = [
        LineItemInput(
            part_name="零件A", part_category="A",
            procurement_method="海運", cost_foreign=100.0,
            freight_twd=500.0, labor_hours=2.0,
        )
    ]
    results = [
        LineItemResult(
            cost_twd=3000.0, tariff=450.0, landed_cost=3950.0,
            margin_rate=0.3, part_price=8950.0, labor_cost=2400.0,
            subtotal=11350.0, part_profit=5000.0, floor_applied=True,
        )
    ]
    totals = QuoteTotals(
        total_parts=8950.0, total_labor=2400.0,
        total_freight=500.0, grand_total=11350.0,
        dealer_price=0.0,
    )
    params = QuoteParams(
        exchange_rate=30.0, tax_rate=0.15,
        labor_rate=1200.0, min_profit=5000.0,
        margin_rate_a=0.30, margin_rate_b=0.50, margin_rate_c=0.30,
        include_air_freight=True,
    )
    return meta, inputs, results, totals, params


def _parse_csv(data: bytes) -> list[list[str]]:
    text = data.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


# ── CSV 基本結構 ──────────────────────────────────────────────

class TestCsvStructure:
    def test_starts_with_utf8_bom(self):
        data = build_csv_bytes(*_make_fixtures())
        assert data[:3] == b"\xef\xbb\xbf"

    def test_returns_bytes(self):
        data = build_csv_bytes(*_make_fixtures())
        assert isinstance(data, bytes)

    def test_header_has_28_columns(self):
        rows = _parse_csv(build_csv_bytes(*_make_fixtures()))
        assert len(rows[0]) == 28

    def test_detail_row_column_count_matches_header(self):
        rows = _parse_csv(build_csv_bytes(*_make_fixtures()))
        assert len(rows[1]) == len(rows[0])

    def test_totals_row_column_count_matches_header(self):
        rows = _parse_csv(build_csv_bytes(*_make_fixtures()))
        assert len(rows[3]) == len(rows[0])


# ── CSV 合計行 ────────────────────────────────────────────────

class TestCsvTotals:
    def test_grand_total_at_column_24(self):
        meta, inputs, results, totals, params = _make_fixtures()
        rows = _parse_csv(build_csv_bytes(meta, inputs, results, totals, params))
        assert rows[3][24] == str(totals.grand_total)

    def test_freight_at_column_15(self):
        meta, inputs, results, totals, params = _make_fixtures()
        rows = _parse_csv(build_csv_bytes(meta, inputs, results, totals, params))
        assert rows[3][15] == str(totals.total_freight)

    def test_parts_at_column_21(self):
        meta, inputs, results, totals, params = _make_fixtures()
        rows = _parse_csv(build_csv_bytes(meta, inputs, results, totals, params))
        assert rows[3][21] == str(totals.total_parts)

    def test_labor_at_column_23(self):
        meta, inputs, results, totals, params = _make_fixtures()
        rows = _parse_csv(build_csv_bytes(meta, inputs, results, totals, params))
        assert rows[3][23] == str(totals.total_labor)

    def test_dealer_price_in_totals_when_present(self):
        meta, inputs, results, totals, params = _make_fixtures()
        totals.dealer_price = 8512.5
        rows = _parse_csv(build_csv_bytes(meta, inputs, results, totals, params))
        assert rows[3][27] == str(8512.5)

    def test_dealer_price_empty_when_zero(self):
        meta, inputs, results, totals, params = _make_fixtures()
        totals.dealer_price = 0.0
        rows = _parse_csv(build_csv_bytes(meta, inputs, results, totals, params))
        assert rows[3][27] == ""


# ── CSV 明細行欄位 ────────────────────────────────────────────

class TestCsvDetailRow:
    def test_floor_applied_shows_yes(self):
        rows = _parse_csv(build_csv_bytes(*_make_fixtures()))
        assert rows[1][22] == "是"

    def test_floor_not_applied_shows_no(self):
        meta, inputs, results, totals, params = _make_fixtures()
        results[0] = LineItemResult(
            cost_twd=3000.0, tariff=450.0, landed_cost=3950.0,
            margin_rate=0.3, part_price=5925.0, labor_cost=2400.0,
            subtotal=8325.0, part_profit=1975.0, floor_applied=False,
        )
        rows = _parse_csv(build_csv_bytes(meta, inputs, results, totals, params))
        assert rows[1][22] == "否"

    def test_shipping_display_column(self):
        rows = _parse_csv(build_csv_bytes(*_make_fixtures()))
        assert rows[1][25] == "含運費"

    def test_shipping_display_excluded(self):
        meta, inputs, results, totals, params = _make_fixtures()
        meta["shipping_display"] = "不含運費"
        rows = _parse_csv(build_csv_bytes(meta, inputs, results, totals, params))
        assert rows[1][25] == "不含運費"

    def test_dealer_name_column(self):
        meta, inputs, results, totals, params = _make_fixtures()
        meta["dealer_name"] = "經銷商A"
        rows = _parse_csv(build_csv_bytes(meta, inputs, results, totals, params))
        assert rows[1][26] == "經銷商A"

    def test_dealer_price_column(self):
        meta, inputs, results, totals, params = _make_fixtures()
        meta["dealer_price"] = 8512.5
        rows = _parse_csv(build_csv_bytes(meta, inputs, results, totals, params))
        assert rows[1][27] == "8512.5"

    def test_dealer_price_empty_when_zero(self):
        meta, inputs, results, totals, params = _make_fixtures()
        meta["dealer_price"] = 0
        rows = _parse_csv(build_csv_bytes(meta, inputs, results, totals, params))
        assert rows[1][27] == ""


# ── CSV 多筆明細 ──────────────────────────────────────────────

class TestCsvMultipleItems:
    def test_two_items_produces_correct_rows(self):
        meta, _, _, _, params = _make_fixtures()
        inputs = [
            LineItemInput(part_name="零件A", part_category="A",
                          procurement_method="海運", cost_foreign=100.0,
                          freight_twd=500.0, labor_hours=1.0),
            LineItemInput(part_name="零件B", part_category="B",
                          procurement_method="空運", cost_foreign=200.0,
                          freight_twd=300.0, labor_hours=2.0),
        ]
        results = [
            LineItemResult(cost_twd=3000.0, tariff=450.0, landed_cost=3950.0,
                           margin_rate=0.3, part_price=8950.0, labor_cost=1200.0,
                           subtotal=10150.0, part_profit=5000.0, floor_applied=True),
            LineItemResult(cost_twd=6000.0, tariff=900.0, landed_cost=7200.0,
                           margin_rate=0.5, part_price=14400.0, labor_cost=2400.0,
                           subtotal=16800.0, part_profit=7200.0, floor_applied=False),
        ]
        totals = QuoteTotals(total_parts=23350.0, total_labor=3600.0,
                             total_freight=800.0, grand_total=26950.0)
        rows = _parse_csv(build_csv_bytes(meta, inputs, results, totals, params))
        # header + 2 detail + blank + totals = 5 rows
        assert len(rows) == 5
        assert rows[1][11] == "零件A"
        assert rows[2][11] == "零件B"


# ── PDF 基本 ─────────────────────────────────────────────────

class TestPdfBasic:
    def test_returns_bytes(self):
        data = build_pdf_bytes(*_make_fixtures())
        assert isinstance(data, bytes)

    def test_starts_with_pdf_header(self):
        data = build_pdf_bytes(*_make_fixtures())
        assert data[:5] == b"%PDF-"

    def test_non_empty_output(self):
        data = build_pdf_bytes(*_make_fixtures())
        assert len(data) > 100

    def test_with_dealer_price(self):
        meta, inputs, results, totals, params = _make_fixtures()
        meta["dealer_price"] = 8512.5
        data = build_pdf_bytes(meta, inputs, results, totals, params)
        assert isinstance(data, bytes)
        assert len(data) > 100

    def test_without_notes(self):
        meta, inputs, results, totals, params = _make_fixtures()
        meta["notes"] = ""
        data = build_pdf_bytes(meta, inputs, results, totals, params)
        assert isinstance(data, bytes)

    def test_with_empty_inputs(self):
        meta, _, _, _, params = _make_fixtures()
        totals = QuoteTotals()
        data = build_pdf_bytes(meta, [], [], totals, params)
        assert isinstance(data, bytes)
        assert len(data) > 100
