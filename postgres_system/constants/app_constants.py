TABLE_NAME = "upi_transactions_2024"
INDEXED_TABLE_NAME = "upi_transactions_indexed"

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 10

ALLOWED_SORT_FIELDS = [
    "timestamp",
    "amount_inr",
    "sender_state",
    "transaction_status",
    "sender_bank",
    "receiver_bank"
]

DEFAULT_SORT_FIELD = "timestamp"
DEFAULT_SORT_ORDER = "desc"
