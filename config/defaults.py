TAX_RATE = 0.15
LABOR_RATE = 1200.0
MIN_PROFIT = 5000.0

CUSTOMER_TYPES = ["經銷商", "終端客戶"]
PART_CATEGORIES = ["A", "B", "C"]
PROCUREMENT_METHODS = ["庫存", "海運", "空運"]
CURRENCIES = ["USD", "EUR", "JPY", "GBP", "CNY", "TWD"]

MARGIN_TABLE = {
    "終端客戶": {"A": 0.50, "B": 1.00, "C": 0.50},
    "經銷商":   {"A": 0.30, "B": 0.70, "C": 0.30},
}
AIR_FREIGHT_BONUS = 0.10

PART_CATEGORY_LABELS = {
    "A": "A — 第一打造廠（外面買得到）",
    "B": "B — 第二打造廠（獨家）",
    "C": "C — 第二打造廠（可替代）",
}
