"""
PII Masking — GDPR + Enterprise RBAC Standard.

All functions are pure (no DB, no HTTP, no side effects) so they are
trivially testable and safe to call at any layer.

Google privacy principle: mask as close to the data as possible, as late
as possible — at the serialization boundary, not in business logic.
This ensures masked data never leaks into internal processing pipelines.

RBAC application:
  - admin / analyst roles  → TransactionResponseFull (raw values)
  - viewer role            → TransactionResponseViewer (masked values)
"""


def mask_account_number(account_number: str | None) -> str:
    """
    Mask an account number, keeping only the last 4 digits.

    'ACC-12345678' → '****5678'
    '1234'         → '****1234'
    None / ''      → '****'
    """
    if not account_number:
        return "****"
    clean = account_number.replace("-", "").replace(" ", "")
    return "****" + clean[-4:] if len(clean) >= 4 else "****"


def mask_email(email: str | None) -> str:
    """
    Mask an email address, preserving domain and first/last chars of local part.

    'john.doe@gmail.com'  → 'j******e@gmail.com'
    'ab@example.com'      → 'a*@example.com'
    'a@example.com'       → '*@example.com'
    None / no '@'         → '***@***'
    """
    if not email or "@" not in email:
        return "***@***"
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"{'*' * len(local)}@{domain}"
    if len(local) == 2:
        return f"{local[0]}*@{domain}"
    return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{domain}"


def mask_ip_address(ip: str | None) -> str:
    """
    Mask an IPv4 address, keeping only the first two octets.

    '192.168.1.100' → '192.168.*.*'
    '10.0.0.1'      → '10.0.*.*'
    None / invalid  → '***'
    """
    if not ip:
        return "***"
    parts = ip.split(".")
    if len(parts) != 4:
        return "***"
    return f"{parts[0]}.{parts[1]}.*.*"


def mask_phone(phone: str | None) -> str:
    """
    Mask a phone number, keeping only the last 4 digits.

    '+1-800-555-1234' → '****1234'
    '5551234'         → '****1234'
    None / short      → '****'
    """
    if not phone:
        return "****"
    digits = "".join(ch for ch in phone if ch.isdigit())
    return "****" + digits[-4:] if len(digits) >= 4 else "****"
