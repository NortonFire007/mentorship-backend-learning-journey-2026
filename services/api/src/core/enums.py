import enum

class CurrencyEnum(str, enum.Enum):
    EUR = "EUR"
    USD = "USD"
    UAH = "UAH"

class TravelType(str, enum.Enum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    PACKAGE = "package"

class AlertStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"

class SearchRunStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
