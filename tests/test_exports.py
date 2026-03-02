"""
Tests for src/export_csv.py — no external dependencies required.
"""
import csv
import io

from src.export_csv import build_csv_bytes
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
            margin_rate=0.5, part_price=8950.0, labor_cost=2400.0,
            subtotal=11350.0, part_profit=5000.0, floor_applied=True,
        )
    ]
    totals = QuoteTotals(
        total_parts=8950.0, total_labor=2400.0,
        total_freight=500.0, grand_total=11350.0,
    )
    params = QuoteParams(
        exchange_rate=30.0, tax_rate=0.15,
        labor_rate=1200.0, min_profit=5000.0,
        customer_type="終端客戶",
    )
    return meta, inputs, results, totals, params


class TestBuildCsvBytes:
    def test_starts_with_utf8_bom(self):
        meta, inputs, results, totals, params = _make_fixtures()
        data = build_csv_bytes(meta, inputs, results, totals, params)
        assert data[:3] == b"\xef\xbb\xbf", "必須以 UTF-8 BOM 開頭"

    def test_returns_bytes(self):
        meta, inputs, results, totals, params = _make_fixtures()
        data = build_csv_bytes(meta, inputs, results, totals, params)
        assert isinstance(data, bytes)

    def test_header_has_25_columns(self):
        meta, inputs, results, totals, params = _make_fixtures()
        data = build_csv_bytes(meta, inputs, results, totals, params)
        text = data.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text)))
        assert len(rows[0]) == 25, f"標題應有 25 欄，實際 {len(rows[0])}"

    def test_detail_row_column_count_matches_header(self):
        meta, inputs, results, totals, params = _make_fixtures()
        data = build_csv_bytes(meta, inputs, results, totals, params)
        text = data.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text)))
        header_cols = len(rows[0])
        detail_cols = len(rows[1])
        assert detail_cols == header_cols, (
            f"明細行欄位數 ({detail_cols}) 應與標題行 ({header_cols}) 相同"
        )

    def test_totals_row_grand_total_in_last_column(self):
        meta, inputs, results, totals, params = _make_fixtures()
        data = build_csv_bytes(meta, inputs, results, totals, params)
        text = data.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text)))
        # rows: [header, detail, blank, totals]
        totals_row = rows[3]
        assert totals_row[-1] == str(totals.grand_total), (
            f"合計行最後欄應為 grand_total={totals.grand_total}"
        )

    def test_totals_row_freight_at_column_15(self):
        meta, inputs, results, totals, params = _make_fixtures()
        data = build_csv_bytes(meta, inputs, results, totals, params)
        text = data.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text)))
        totals_row = rows[3]
        assert totals_row[15] == str(totals.total_freight), (
            f"合計行第 16 欄（index 15）應為 total_freight={totals.total_freight}"
        )

    def test_floor_applied_shows_correct_text(self):
        meta, inputs, results, totals, params = _make_fixtures()
        data = build_csv_bytes(meta, inputs, results, totals, params)
        text = data.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text)))
        detail_row = rows[1]
        assert detail_row[22] == "是", "floor_applied=True 應顯示「是」"

    def test_no_floor_applied_shows_no(self):
        meta, inputs, results, totals, params = _make_fixtures()
        results[0] = LineItemResult(
            cost_twd=3000.0, tariff=450.0, landed_cost=3950.0,
            margin_rate=0.5, part_price=5925.0, labor_cost=2400.0,
            subtotal=8325.0, part_profit=1975.0, floor_applied=False,
        )
        data = build_csv_bytes(meta, inputs, results, totals, params)
        text = data.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text)))
        assert rows[1][22] == "否", "floor_applied=False 應顯示「否」"
