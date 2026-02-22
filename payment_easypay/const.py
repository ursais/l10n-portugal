# EasyPay API
API_URL_TEST = "https://api.test.easypay.pt"
API_URL_PROD = "https://api.prod.easypay.pt"

# Payment methods
DEFAULT_PAYMENT_METHOD_CODES = {"card", "visa", "mastercard"}
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
DEFAULT_PAYMENT_METHODS = ["cc"]

# Payment types
PAYMENT_TYPE_SALE = "sale"
PAYMENT_TYPE_AUTHORISATION = "authorisation"

# Status mapping
STATUS_MAPPING = {
    "draft": (),
    "pending": ("pending",),
    "authorized": ("authorized", "authorised"),
    "done": ("success", "captured", "paid"),
    "cancel": ("cancelled",),
    "error": ("failed",),
}

# Webhook events
HANDLED_WEBHOOK_EVENTS = ["generic", "authorisation", "transaction"]

# Supported countries
SUPPORTED_COUNTRIES = {"PT"}
