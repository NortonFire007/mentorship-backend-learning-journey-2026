import re
from typing import Annotated
from pydantic import AfterValidator


def validate_password_strength(v: str) -> str:
    """
    Validates that a password is at least 8 characters long, contains at least
    one uppercase letter, one digit, and one special character.
    """
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
        raise ValueError("Password must contain at least one special character")
    return v


PasswordStr = Annotated[str, AfterValidator(validate_password_strength)]
