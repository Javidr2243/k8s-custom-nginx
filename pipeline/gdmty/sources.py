"""Load and validate pipeline/sources.yaml."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from gdmty.catalogos import MUNICIPIOS
from gdmty.paths import SOURCES_FILE

PERIOD_RE = re.compile(r"^\d{4}T[1-4]$")
Tipo = Literal[
    "mty_egresos_administrativa",
    "mty_egresos_objeto",
    "mty_ingresos",
    "sipot_xxiib",
    "inegi_efipem",
    "inegi_poblacion",
    "shcp_rpu_saldos",
    "shcp_rpu_registro",
    "shcp_alertas",
    "mty_deuda_total",
    "sipot_xxix",
    "sp_contratos",
]
EXTENSION = {"xlsx": "xlsx", "xls": "xls", "zip": "csv", "json": "json", "csv": "csv"}
# Large national originals: only an extract for the three municipalities is kept (plus the original's hash).
EXTRACTOS = {"inegi_efipem", "shcp_rpu_registro"}
# Originals that are not archived in the repo or on the site because they contain personal data (RFC of individuals):
# only their link and SHA-256 are published, and the build uses their masked parser output (data/intermedio/).
SIN_COPIA = {"sipot_xxix", "sp_contratos"}


class Fuente(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    municipio: str | None
    tipo: Tipo
    periodo: str | None
    titulo: str
    emisor: str
    url: str
    pagina: str
    formato: Literal["xlsx", "xls", "zip", "json", "csv"]

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z0-9][A-Za-z0-9-]*[A-Za-z0-9]", v):
            raise ValueError(f"id inválido: {v}")
        return v

    @field_validator("municipio")
    @classmethod
    def _mun(cls, v: str | None) -> str | None:
        if v is not None and v not in MUNICIPIOS:
            raise ValueError(f"municipio desconocido: {v}")
        return v

    @field_validator("periodo")
    @classmethod
    def _periodo(cls, v: str | None) -> str | None:
        if v is not None and not PERIOD_RE.match(v):
            raise ValueError(f"periodo inválido: {v}")
        return v

    @field_validator("url")
    @classmethod
    def _url(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("las fuentes deben usar https")
        return v

    def archivo(self) -> Path:
        """Path of the original, relative to data/raw/ (large national files are stored as a CSV extract)."""
        folder = self.municipio or self.id.split("-")[0]
        ext = "csv" if self.tipo in EXTRACTOS else EXTENSION[self.formato]
        return Path(folder) / f"{self.id}.{ext}"


class Faltante(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    municipio: str
    periodo: str
    motivo: str


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    periodo_inicial: str
    dominios_permitidos: list[str]
    faltantes_conocidos: list[Faltante]
    fuentes: list[Fuente]

    @model_validator(mode="after")
    def _check(self) -> Config:
        ids = [f.id for f in self.fuentes]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            raise ValueError(f"ids duplicados: {sorted(dup)}")
        from urllib.parse import urlsplit

        for f in self.fuentes:
            host = urlsplit(f.url).hostname
            if host not in self.dominios_permitidos:
                raise ValueError(f"{f.id}: el dominio {host} no está en dominios_permitidos")
        return self

    def fuente(self, fid: str) -> Fuente:
        for f in self.fuentes:
            if f.id == fid:
                return f
        raise KeyError(fid)


def load(path: Path = SOURCES_FILE) -> Config:
    with path.open(encoding="utf-8") as fh:
        return Config.model_validate(yaml.safe_load(fh))
