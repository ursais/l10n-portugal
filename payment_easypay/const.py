# EasyPay API
API_URL_TEST = "https://api.test.easypay.pt"
API_URL_PROD = "https://api.prod.easypay.pt"

# Payment methods
DEFAULT_PAYMENT_METHOD_CODES = {"card"}
PAYMENT_METHODS_MAPPING = {
    "cc": "Credit/Debit Card",
    "mb": "Multibanco",
    "mbw": "MB WAY",
    "dd": "SEPA Direct Debit",
    "vi": "Virtual IBAN",
    "ap": "Apple Pay",
    "gp": "Google Pay",
    "sw": "Samsung Pay",
}
# Payment types
PAYMENT_TYPE_SALE = "sale"
PAYMENT_TYPE_AUTHORISATION = "authorisation"

# Status mapping
STATUS_MAPPING = {
    "draft": (),
    "pending": ("pending", "waiting", "success"),
    "authorized": ("authorized", "authorised"),
    "done": ("captured", "paid", "tokenized", "complete"),
    "cancel": ("cancelled", "canceled"),
    "error": ("failed", "error"),
}
