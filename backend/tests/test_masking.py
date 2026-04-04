"""
Unit tests for PII masking functions.

All functions are pure (no DB, no HTTP), so no fixtures are needed.
Google testing convention: test_<condition>_<expected_result>.
"""

import pytest

from app.utils.masking import mask_account_number, mask_email, mask_ip_address, mask_phone


# ─── mask_account_number ──────────────────────────────────────────────────────


def test_mask_account_number_none_returns_placeholder() -> None:
    assert mask_account_number(None) == "****"


def test_mask_account_number_empty_string_returns_placeholder() -> None:
    assert mask_account_number("") == "****"


def test_mask_account_number_short_under_four_digits_returns_placeholder() -> None:
    assert mask_account_number("123") == "****"


def test_mask_account_number_exactly_four_digits_returns_masked() -> None:
    assert mask_account_number("1234") == "****1234"


def test_mask_account_number_long_number_keeps_last_four() -> None:
    assert mask_account_number("12345678") == "****5678"


def test_mask_account_number_with_dashes_strips_separators() -> None:
    assert mask_account_number("ACC-12345678") == "****5678"


def test_mask_account_number_with_spaces_strips_separators() -> None:
    assert mask_account_number("1234 5678") == "****5678"


# ─── mask_email ───────────────────────────────────────────────────────────────


def test_mask_email_none_returns_placeholder() -> None:
    assert mask_email(None) == "***@***"


def test_mask_email_empty_string_returns_placeholder() -> None:
    assert mask_email("") == "***@***"


def test_mask_email_no_at_sign_returns_placeholder() -> None:
    assert mask_email("notanemail") == "***@***"


def test_mask_email_single_char_local_masks_entirely() -> None:
    assert mask_email("a@example.com") == "*@example.com"


def test_mask_email_two_char_local_masks_second_char() -> None:
    assert mask_email("ab@example.com") == "a*@example.com"


def test_mask_email_normal_address_keeps_first_last_and_domain() -> None:
    result = mask_email("john.doe@gmail.com")
    assert result.endswith("@gmail.com")
    assert result.startswith("j")
    assert result[1:-len("@gmail.com") - 1].replace("*", "") == "e"
    assert "****" in result or "******" in result


def test_mask_email_preserves_domain_unchanged() -> None:
    result = mask_email("alice@company.io")
    assert result.endswith("@company.io")


# ─── mask_ip_address ──────────────────────────────────────────────────────────


def test_mask_ip_address_none_returns_placeholder() -> None:
    assert mask_ip_address(None) == "***"


def test_mask_ip_address_empty_string_returns_placeholder() -> None:
    assert mask_ip_address("") == "***"


def test_mask_ip_address_invalid_format_returns_placeholder() -> None:
    assert mask_ip_address("not.an.ip") == "***"


def test_mask_ip_address_normal_ipv4_keeps_first_two_octets() -> None:
    assert mask_ip_address("192.168.1.100") == "192.168.*.*"


def test_mask_ip_address_private_range_correct_mask() -> None:
    assert mask_ip_address("10.0.0.1") == "10.0.*.*"


def test_mask_ip_address_loopback_correct_mask() -> None:
    assert mask_ip_address("127.0.0.1") == "127.0.*.*"


# ─── mask_phone ───────────────────────────────────────────────────────────────


def test_mask_phone_none_returns_placeholder() -> None:
    assert mask_phone(None) == "****"


def test_mask_phone_empty_string_returns_placeholder() -> None:
    assert mask_phone("") == "****"


def test_mask_phone_short_under_four_digits_returns_placeholder() -> None:
    assert mask_phone("123") == "****"


def test_mask_phone_exactly_four_digits_returns_masked() -> None:
    assert mask_phone("1234") == "****1234"


def test_mask_phone_with_dashes_and_plus_keeps_last_four() -> None:
    assert mask_phone("+1-800-555-1234") == "****1234"


def test_mask_phone_international_format_keeps_last_four() -> None:
    assert mask_phone("+44 20 7946 0958") == "****0958"
