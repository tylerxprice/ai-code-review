import re
from typing import List

class Redactor:
    """Detects and redacts secrets and sensitive information from text."""

    SECRET_PATTERNS = [
        r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[\w-]{20,}',
        r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\']?[\w-]{8,}',
        r'(?i)(token|bearer)\s*[=:]\s*["\']?[\w-]{20,}',
        r'-----BEGIN [A-Z]+ PRIVATE KEY-----',
        r'(?i)aws[_-]?(access[_-]?key|secret)',
    ]

    def __init__(self):
        self.patterns = [re.compile(p) for p in self.SECRET_PATTERNS]

    def redact(self, text: str) -> str:
        """Replace detected secrets with redaction labels."""
        redacted_text = text
        for pattern in self.patterns:
            redacted_text = pattern.sub('[REDACTED: potential secret]', redacted_text)
        return redacted_text
