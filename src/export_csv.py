import csv
import io
from src.models import LineItemInput, LineItemResult, QuoteParams, QuoteTotals


def build_csv_bytes(
    quote_meta: dict,
    inputs: list[LineItemInput],
    results: list[LineItemResult],
    totals: QuoteTotals,
    params: QuoteParams,
) -> bytes:
    """
    產生 UTF-8 BOM CSV bytes，可直接傳給 st.download_button。
    Windows Excel 開啟不會亂碼。
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # 標題行
    writer.writerow([
        "報價單號", "日期", "客戶類型", "客戶名稱",
        "幣別", "匯率", "關稅率", "工資單價", "最低保底",
        "狀態", "備註",
        "零件名稱", "分類", "取得方式",
        "外幣成本", "運費(TWD)", "工時",
        "台幣成本", "關稅", "到岸成本",
        "毛利率", "零件售價", "保底觸發",
        "工資", "小計",
    ])

    # 明細行
    for inp, res in zip(inputs, results):
        writer.writerow([
            quote_meta.get("quote_number", ""),
            quote_meta.get("quote_date", ""),
            quote_meta.get("customer_type", ""),
            quote_meta.get("customer_name", ""),
            quote_meta.get("currency", ""),
            params.exchange_rate,
            params.tax_rate,
            params.labor_rate,
            params.min_profit,
            quote_meta.get("status", ""),
            quote_meta.get("notes", ""),
            inp.part_name,
            inp.part_category,
            inp.procurement_method,
            inp.cost_foreign,
            inp.freight_twd,
            inp.labor_hours,
            res.cost_twd,
            res.tariff,
            res.landed_cost,
            f"{res.margin_rate:.0%}",
            res.part_price,
            "是" if res.floor_applied else "否",
            res.labor_cost,
            res.subtotal,
        ])

    # 合計行
    writer.writerow([])
    writer.writerow([
        "", "", "", "", "", "", "", "", "", "", "",   # 0-10
        "【合計】", "", "", "",                       # 11-14
        totals.total_freight,                         # 15: 運費(TWD)
        "",                                           # 16: 工時
        "", "", "",                                   # 17-19: 台幣成本/關稅/到岸成本
        "",                                           # 20: 毛利率
        totals.total_parts,                           # 21: 零件售價
        "",                                           # 22: 保底觸發
        totals.total_labor,                           # 23: 工資
        totals.grand_total,                           # 24: 小計
    ])

    # UTF-8 BOM
    return ("\ufeff" + output.getvalue()).encode("utf-8")
