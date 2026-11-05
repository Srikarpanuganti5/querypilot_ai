"""Credential screening at data boundaries; no instruction-keyword blocking."""

import json
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, unquote, urlsplit

if TYPE_CHECKING:
    from querypilot.core.config import Settings

_PATTERNS = (
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*"),
    re.compile(
        r"(?i)\b(?:proxy-)?authorization[\"']?\s*[:=]\s*[\"']?(?:Basic|Bearer)\s+[A-Za-z0-9._~+/-]+=*"
    ),
    re.compile(
        r"(?i)\b(?:postgres(?:ql)?(?:\+psycopg)?|https?)://[^\s\"<>]*:[^\s\"<>]*@[^\s\"<>]+"
    ),
    re.compile(
        r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token)[\"']?\s*[:=]\s*[\"']?[^\s\"',;}]+"
    ),
    re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?"
        r"-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        re.DOTALL,
    ),
)
_SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "password",
        "passwd",
        "api_key",
        "openai_api_key",
        "database_url",
        "reader_database_url",
        "access_token",
    }
)


class SecretGuard:
    def __init__(self, settings: "Settings | None" = None):
        values: set[str] = set()
        if settings is not None:
            for field in (
                settings.openai_api_key,
                settings.database_url,
                settings.reader_database_url,
            ):
                if field is not None and field.get_secret_value():
                    value = field.get_secret_value()
                    values.add(value)
                    try:
                        password = urlsplit(value).password if "://" in value else None
                        if password:
                            values.update(
                                (password, unquote(password), quote(unquote(password), safe=""))
                            )
                    except ValueError:
                        pass  # Invalid configuration still has its full value protected.
        self._values = tuple(sorted(values, key=len, reverse=True))

    def redact(self, text: str) -> str:
        for value in self._values:
            text = text.replace(value, "[REDACTED]")
        for pattern in _PATTERNS:
            text = pattern.sub("[REDACTED]", text)
        return text

    def sanitize(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.redact(value)
        if isinstance(value, dict):
            return {
                key: "[REDACTED]" if str(key).casefold() in _SENSITIVE_KEYS else self.sanitize(item)
                for key, item in value.items()
            }
        if isinstance(value, list | tuple):
            return [self.sanitize(item) for item in value]
        return value

    def contains(self, value: Any) -> bool:
        # Screen values and their JSON representation; function argument JSON is also
        # decoded at the provider boundary. No text is interpreted as instructions.
        encoded = json.dumps(value, ensure_ascii=False)
        return self.sanitize(value) != value or self.redact(encoded) != encoded
