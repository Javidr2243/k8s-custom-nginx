"""Check that the intermediate certificates in pipeline/certs/ do not expire soon."""

from __future__ import annotations

import re
import ssl
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from gdmty.paths import CERTS_FILE

_PEM_RE = re.compile(r"-----BEGIN CERTIFICATE-----.+?-----END CERTIFICATE-----", re.S)


def check_expiry(path: Path = CERTS_FILE, *, days: int = 30) -> list[str]:
    """Return one message per certificate that expires within `days` days (or is already expired)."""
    problemas = []
    limite = datetime.now(UTC) + timedelta(days=days)
    for pem in _PEM_RE.findall(path.read_text(encoding="ascii")):
        with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as tmp:
            tmp.write(pem)
        try:
            info = ssl._ssl._test_decode_cert(tmp.name)  # type: ignore[attr-defined]
        finally:
            Path(tmp.name).unlink(missing_ok=True)
        vence = datetime.strptime(info["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)
        sujeto = dict(x[0] for x in info["subject"]).get("commonName", "?")
        if vence < limite:
            problemas.append(f"El certificado '{sujeto}' vence el {vence:%Y-%m-%d}; actualízalo en {path}.")
    return problemas
