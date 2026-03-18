TAX_RATE = 0.15
LABOR_RATE = 1200.0
MIN_PROFIT = 5000.0

# 毛利率（依零件分類）
MARGIN_RATE_A = 0.30
MARGIN_RATE_B = 0.50
MARGIN_RATE_C = 0.30

# 經銷商
DEALER_COEFFICIENT = 0.75
DEALERS = ["經銷商A", "經銷商B", "經銷商C", "經銷商D", "經銷商E"]

# 公司名稱
COMPANY_NAME = "歐馬企業股份有限公司"

# 報價單狀態
STATUS_DRAFT = "草稿"
STATUS_CONFIRMED = "已確認"

# 運費顯示
SHIPPING_INCLUDED = "含運費"
SHIPPING_EXCLUDED = "不含運費"

# 取得方式
PROC_INVENTORY = "庫存"
PROC_SEA = "海運"
PROC_AIR = "空運"

# 角色
ROLE_MANAGER = "manager"

CUSTOMER_TYPES = ["經銷商", "終端客戶"]
CUSTOMER_TYPE_DEALER = "經銷商"
CUSTOMER_TYPE_END = "終端客戶"
PART_CATEGORIES = ["A", "B", "C"]
PROCUREMENT_METHODS = [PROC_INVENTORY, PROC_SEA, PROC_AIR]
CURRENCIES = ["USD", "EUR", "JPY", "GBP", "CNY", "TWD"]

PART_CATEGORY_LABELS = {
    "A": "A — 第一打造廠（外面買得到）",
    "B": "B — 第二打造廠（獨家）",
    "C": "C — 第二打造廠（可替代）",
}
