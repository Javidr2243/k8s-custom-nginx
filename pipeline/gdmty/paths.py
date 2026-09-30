"""Repository paths used by the pipeline."""

from __future__ import annotations

from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PIPELINE_DIR.parent
SOURCES_FILE = PIPELINE_DIR / "sources.yaml"
CERTS_FILE = PIPELINE_DIR / "certs" / "intermediates.pem"
DATA_RAW = REPO_ROOT / "data" / "raw"
MANIFEST_FILE = DATA_RAW / "manifest.json"
# Masked parser output for originals that are not archived because they contain personal data (see SIN_COPIA).
DATA_INTERMEDIO = REPO_ROOT / "data" / "intermedio"
DATA_PUBLIC = REPO_ROOT / "data" / "public"
PUBLIC_V1 = DATA_PUBLIC / "v1"
CACHE_DIR = REPO_ROOT / ".cache"
