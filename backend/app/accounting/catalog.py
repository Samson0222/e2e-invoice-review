"""Hypothetical fixed chart of accounts for this case study."""

from typing import Literal

NORTHSTAR_GL_CATALOG: tuple[tuple[str, str], ...] = (
    ("5000", "Cost of Goods Sold"),
    ("5100", "Office Supplies Expense"),
    ("5200", "Travel & Entertainment Expense"),
    ("5300", "Professional Services Expense"),
    ("5400", "IT & Software Expense"),
    ("5500", "Utilities Expense"),
    ("5600", "Marketing & Advertising Expense"),
    ("5700", "Repairs & Maintenance Expense"),
    ("5800", "Freight & Shipping Expense"),
    ("5900", "Miscellaneous Expense"),
)
GL_ACCOUNT_NAMES: dict[str, str] = dict(NORTHSTAR_GL_CATALOG)

GLAccountCode = Literal[
    "5000", "5100", "5200", "5300", "5400", "5500", "5600", "5700", "5800", "5900"
]
