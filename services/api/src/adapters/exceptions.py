class AdapterError(Exception):
    """Base exception for all adapter-related errors."""
    pass


class RateLimitError(AdapterError):
    """Raised when the provider rates limits our requests."""
    pass


class TimeoutError(AdapterError):
    """Raised when the request to the provider times out."""
    pass


class AuthError(AdapterError):
    """Raised when authentication with the provider fails."""
    pass


class ParseError(AdapterError):
    """Raised when parsing the provider's response fails."""
    pass
