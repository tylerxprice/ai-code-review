from ai_review.security.redact import Redactor


def test_redact_counts_and_labels():
    redactor = Redactor()
    text = "api_key=abcdefghijklmnopqrstuvwxyz123456 token=abcd1234abcd1234abcd1234"
    redacted, count = redactor.redact(text)

    assert count >= 2
    assert "[REDACTED: potential secret]" in redacted


def test_redact_no_false_positive_on_plain_text():
    redactor = Redactor()
    text = "hello world"
    redacted, count = redactor.redact(text)

    assert redacted == text
    assert count == 0
