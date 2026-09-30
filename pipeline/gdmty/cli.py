"""Command-line entry point: ``python -m gdmty <command>``."""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from gdmty import __version__


def _cmd_fetch(args: argparse.Namespace) -> int:
    from gdmty.fetch import fetch

    resultados = fetch(only=args.only)
    counts = Counter(r.estado for r in resultados)
    for r in resultados:
        if r.estado != "sin_cambios":
            print(f"{r.estado:12} {r.id} {r.detalle}")
    print("Resumen: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    # Failures don't stop the build (a site may be down); they are reported in the PR.
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    from gdmty.build import build

    report = build()
    for w in report.advertencias:
        print(f"ADVERTENCIA {w}")
    for e in report.errores:
        print(f"ERROR {e}", file=sys.stderr)
    print(
        f"Archivos generados: {len(report.archivos)}; advertencias: {len(report.advertencias)}; "
        f"errores: {len(report.errores)}"
    )
    return 1 if report.errores else 0


def _cmd_certs(args: argparse.Namespace) -> int:
    from gdmty.certs import check_expiry

    problemas = check_expiry(days=args.days)
    for p in problemas:
        print(p)
    return 1 if problemas else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gdmty", description="Pipeline de datos de ¿A dónde va tu dinero? MTY"
    )
    parser.add_argument("--version", action="version", version=f"gdmty {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    p_fetch = sub.add_parser("fetch", help="Descarga las fuentes declaradas en sources.yaml")
    p_fetch.add_argument("--only", help="Solo fuentes cuyo id empiece con este prefijo")
    p_fetch.set_defaults(func=_cmd_fetch)
    p_build = sub.add_parser("build", help="Valida los originales y genera data/public/v1")
    p_build.set_defaults(func=_cmd_build)
    p_certs = sub.add_parser("certs", help="Revisa la vigencia de los certificados intermedios")
    p_certs.add_argument("--days", type=int, default=30)
    p_certs.set_defaults(func=_cmd_certs)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
