from pathlib import Path
from datetime import date as _date
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

from src.models import LineItemInput, LineItemResult, QuoteParams, QuoteTotals
from config.defaults import COMPANY_NAME

FONT_PATH = Path(__file__).parent.parent / "assets" / "fonts" / "NotoSansTC-Regular.ttf"
FONT_NAME = "NotoSansTC"


def _draw_footer(canvas, doc):
    """每頁底部印產生日期"""
    _register_font()
    canvas.saveState()
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(colors.grey)
    footer_text = f"產生日期：{_date.today().strftime('%Y-%m-%d')}"
    canvas.drawRightString(
        doc.pagesize[0] - 15 * mm,
        10 * mm,
        footer_text,
    )
    canvas.restoreState()


def _register_font():
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))


def build_pdf_bytes(
    quote_meta: dict,
    inputs: list[LineItemInput],
    results: list[LineItemResult],
    totals: QuoteTotals,
    params: QuoteParams,
) -> bytes:
    _register_font()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    normal = ParagraphStyle("normal_tc", fontName=FONT_NAME, fontSize=9, leading=14)
    title_style = ParagraphStyle("title_tc", fontName=FONT_NAME, fontSize=14,
                                 leading=20, spaceAfter=6)
    h2 = ParagraphStyle("h2_tc", fontName=FONT_NAME, fontSize=11,
                        leading=16, spaceAfter=4)

    story = []

    # ── 抬頭 ──
    story.append(Paragraph(COMPANY_NAME, title_style))
    story.append(Paragraph("零件報價單", h2))
    story.append(Spacer(1, 4 * mm))

    # ── 報價單資訊 ──
    shipping_display = quote_meta.get("shipping_display", "含運費")
    info_data = [
        ["報價單號", quote_meta.get("quote_number", ""),
         "報價日期", str(quote_meta.get("quote_date", ""))],
        ["客戶類型", quote_meta.get("customer_type", ""),
         "客戶名稱", quote_meta.get("customer_name", "")],
        ["幣別", quote_meta.get("currency", ""),
         "匯率", str(params.exchange_rate)],
        ["運費狀態", shipping_display, "", ""],
    ]
    info_table = Table(info_data, colWidths=[30 * mm, 55 * mm, 30 * mm, 55 * mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("BACKGROUND", (2, 0), (2, -1), colors.lightgrey),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 4 * mm))

    # ── 明細表 ──
    headers = ["零件名稱", "分類", "取得", "外幣成本", "到岸成本",
               "毛利率", "零件售價", "保底", "工時", "工資", "小計"]
    # 欄寬合計 = 180mm = A4(210) - 左右邊距(15+15)
    col_widths = [34*mm, 10*mm, 10*mm, 18*mm, 20*mm,
                  12*mm, 20*mm, 10*mm, 10*mm, 16*mm, 20*mm]

    rows = [headers]
    for inp, res in zip(inputs, results):
        rows.append([
            inp.part_name,
            inp.part_category,
            inp.procurement_method,
            f"{inp.cost_foreign:,.2f}",
            f"{res.landed_cost:,.0f}",
            f"{res.margin_rate:.0%}",
            f"{res.part_price:,.0f}",
            "!" if res.floor_applied else "",
            f"{inp.labor_hours}",
            f"{res.labor_cost:,.0f}",
            f"{res.subtotal:,.0f}",
        ])

    detail_table = Table(rows, colWidths=col_widths, repeatRows=1)
    detail_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f6feb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 4 * mm))

    # ── 合計 ──
    total_data = [
        ["零件合計", f"NT$ {totals.total_parts:,.0f}",
         "工資合計", f"NT$ {totals.total_labor:,.0f}"],
        ["運費合計", f"NT$ {totals.total_freight:,.0f}",
         "總報價", f"NT$ {totals.grand_total:,.0f}"],
    ]
    # 經銷商價格
    dealer_price = quote_meta.get("dealer_price", 0)
    if dealer_price:
        total_data.append(
            ["經銷商價格", f"NT$ {dealer_price:,.0f}", "", ""]
        )

    total_table = Table(total_data, colWidths=[30 * mm, 55 * mm, 30 * mm, 55 * mm])
    total_style = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("BACKGROUND", (2, 0), (2, -1), colors.lightgrey),
        ("BACKGROUND", (3, 1), (3, 1), colors.HexColor("#1f6feb")),
        ("TEXTCOLOR", (3, 1), (3, 1), colors.white),
        ("FONTSIZE", (3, 1), (3, 1), 12),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    total_table.setStyle(TableStyle(total_style))
    story.append(total_table)

    # ── 備註 ──
    notes = quote_meta.get("notes", "")
    if notes:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(f"備註：{notes}", normal))

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return buffer.getvalue()
