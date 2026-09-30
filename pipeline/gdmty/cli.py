"""Command-line entry point: ``python -m gdmty <command>``."""

from __future__ import annotations

import argparse
import sys

from gdmty import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gdmty", description="Pipeline de datos de ¿A dónde va tu dinero? MTY"
    )
    parser.add_argument("--version", action="version", version=f"gdmty {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch", help="Descarga las fuentes declaradas en sources.yaml")
    sub.add_parser("build", help="Valida los originales y genera data/public/v1")
    args = parser.parse_args(argv)
    print(f"gdmty {args.command}: aún no implementado", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
