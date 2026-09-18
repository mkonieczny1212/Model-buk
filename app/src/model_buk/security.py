"""Public error messages must never contain provider URLs or credentials."""

import ssl
from functools import lru_cache


class ProviderAccessError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        messages = {
            "plan": "Plan API nie obejmuje żądanych danych (ostatnie mecze lub sezon). Sprawdź dostęp do bieżących statystyk.",
            "quota": "Wyczerpano limit zapytań API. Odświeżenie wymaga odnowienia limitu.",
            "parameters": "Dostawca odrzucił parametry zapytania.",
        }
        self.public_message = messages.get(code, "Dostawca odrzucił zapytanie; sprawdź konfigurację dostępu.")
        super().__init__(self.public_message)


@lru_cache(maxsize=1)
def configure_system_tls() -> None:
    """Use OS certificate trust, including enterprise CAs; never disable TLS."""
    try:
        import truststore
    except ImportError:
        return
    truststore.inject_into_ssl()


def safe_error(exc: Exception) -> str:
    """Return a useful status without echoing untrusted upstream exception text.

    HTTP client errors can include complete URLs with query-string API keys.
    Redacting known keys alone misses encoded secrets and proxy error bodies.
    """
    if isinstance(exc, ProviderAccessError):
        return exc.public_message
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if isinstance(status, int):
        return f"Provider request failed (HTTP {status})"
    kind = type(exc).__name__
    if kind in {"SSLError", "Timeout", "ConnectTimeout", "ReadTimeout", "ConnectionError"}:
        return f"Provider connection failed ({kind}); check network and system certificates"
    return "Request failed; check server configuration and provider access"
