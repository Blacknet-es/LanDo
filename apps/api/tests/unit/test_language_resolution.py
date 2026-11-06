from src.presentation.http.language import _language_from_header


def test_language_resolution_uses_supported_header_and_quality_order() -> None:
    assert _language_from_header("fr-FR, en-GB;q=0.8, es;q=0.9") == "es"
    assert _language_from_header("de, en-US") == "en"


def test_language_resolution_ignores_unsupported_or_zero_quality_values() -> None:
    assert _language_from_header("fr, en;q=0") is None
    assert _language_from_header(None) is None
