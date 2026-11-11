import re


EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}$")


def is_valid_email(email):
    """Validate email syntax before querying the database."""
    return bool(email and EMAIL_PATTERN.fullmatch(email.strip()))
