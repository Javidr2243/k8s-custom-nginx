"""Data checks.

Two levels:
- ERROR: points to a problem in *our* processing (a sum that does not match its own document's total, an
  undeclared period, a broken structure). Blocks the build and the PR.
- ADVERTENCIA: an inconsistency *in the official document* (e.g. Modificado ≠ Aprobado + Ampliaciones)
  or a difference between sources. The data is published as it appears in the document, the problem
  is recorded in the report and in the period's `notas`, and the PR reviewer checks it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

TOLERANCIA = 1.0  # pesos
UMBRAL_ANOMALIA = 0.30


@dataclass
class Reporte:
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)
    anomalias: list[str] = field(default_factory=list)
    archivos: list[str] = field(default_factory=list)

    def error(self, msg: str) -> None:
        self.errores.append(msg)

    def advertencia(self, msg: str) -> None:
        self.advertencias.append(msg)


def identidades_egresos(montos: dict[str, float | None], donde: str) -> list[str]:
    """Accounting identities of a spending line. Returns a description of each one that fails."""
    out = []
    apr, amp, mod = montos.get("aprobado"), montos.get("ampliaciones"), montos.get("modificado")
    dev, sub = montos.get("devengado"), montos.get("subejercicio")
    if None not in (apr, amp, mod) and abs(apr + amp - mod) > TOLERANCIA:  # type: ignore[operator]
        out.append(f"{donde}: Modificado ({mod:,.2f}) ≠ Aprobado + Ampliaciones ({apr + amp:,.2f})")  # type: ignore[operator]
    if None not in (mod, dev, sub) and abs(mod - dev - sub) > TOLERANCIA:  # type: ignore[operator]
        out.append(f"{donde}: Subejercicio ({sub:,.2f}) ≠ Modificado − Devengado ({mod - dev:,.2f})")  # type: ignore[operator]
    return out


def suma_cuadra(
    partes: list[dict[str, float]], total: dict[str, float], medidas: tuple[str, ...]
) -> list[str]:
    """Components add up to the document's total (± TOLERANCIA)."""
    out = []
    for m in medidas:
        s = sum(p[m] for p in partes if p.get(m) is not None)
        if abs(s - total[m]) > TOLERANCIA:
            out.append(f"{m}: suma {s:,.2f} vs total {total[m]:,.2f}")
    return out


def cambio_relativo(nuevo: float, anterior: float) -> float | None:
    if abs(anterior) < 1:
        return None
    return (nuevo - anterior) / abs(anterior)
