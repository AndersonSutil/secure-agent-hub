#!/usr/bin/env python3
"""Gera overlay/compose.sources.yaml a partir de overlay/sources.toml.

Cada fonte vira uma montagem somente leitura em /sources/<name> no hub-rag.
Uso: scripts/render-sources.py [--overlay DIR]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--overlay", default=str(Path(__file__).resolve().parent.parent / "overlay"))
    overlay = Path(ap.parse_args().overlay)
    src_file = overlay / "sources.toml"
    if not src_file.is_file():
        print(f"sem {src_file}; nada a montar", file=sys.stderr)
        return 0
    data = tomllib.loads(src_file.read_text(encoding="utf-8"))
    lines = ["# GERADO por scripts/render-sources.py a partir de sources.toml. NÃO EDITE.",
             "services:", "  hub-rag:", "    volumes:"]
    count = 0
    for src in data.get("source", []):
        name, host_path = src["name"], Path(src["host_path"]).expanduser()
        if not NAME.match(name):
            raise SystemExit(f"nome de fonte inválido: {name!r}")
        if not host_path.is_absolute():
            raise SystemExit(f"{name}: host_path precisa ser absoluto")
        if not src.get("enabled", True):
            continue
        if not host_path.is_dir():
            print(f"aviso: {name}: {host_path} não existe; montagem ignorada", file=sys.stderr)
            continue
        # Sempre somente leitura. Relabel SELinux (:z) só se a fonte pedir, porque altera
        # o contexto dos seus arquivos no host (necessário em hosts com SELinux enforcing
        # quando a pasta tem rótulo que o container_t não lê).
        opts = "ro,z" if src.get("selinux_relabel", False) else "ro"
        lines.append(f"      - {json.dumps(f'{host_path}:/sources/{name}:{opts}')}")
        count += 1
    if count == 0:
        lines = lines[:1] + ["services: {}"]
    out = overlay / "compose.sources.yaml"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"escrito: {out} ({count} fontes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
