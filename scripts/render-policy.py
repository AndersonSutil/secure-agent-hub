#!/usr/bin/env python3
"""Renderiza policy/*.toml para os arquivos de configuração de cada ferramenta.

Fonte única de regras: policy/. Nunca edite os arquivos gerados à mão.

Uso:
    scripts/render-policy.py           # escreve os arquivos gerados
    scripts/render-policy.py --check   # falha (exit 1) se algum estiver desatualizado

Só usa a biblioteca padrão (Python >= 3.11) para rodar em qualquer máquina e no CI.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / "policy"
OVERLAY = ROOT / "overlay"
HEADER = "GERADO por scripts/render-policy.py a partir de policy/. NÃO EDITE."


def load(name: str) -> dict:
    with open(POLICY / name, "rb") as fh:
        return tomllib.load(fh)


def load_optional(path: Path) -> dict:
    if path.is_file():
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    return {}


# ---------------------------------------------------------------- Claude Code
def claude_path_rule(tool: str, glob: str) -> str:
    # Regras de permissão do Claude Code: caminho absoluto usa prefixo "//".
    if glob.startswith("/"):
        return f"{tool}(/{glob})"
    return f"{tool}({glob})"


def render_claude(cmd: dict) -> dict[str, str]:
    deny: list[str] = []
    for rule in cmd["bash_deny"]:
        for prefix in rule["prefixes"]:
            deny.append(f"Bash({' '.join(prefix)}:*)")
    for glob in cmd["read_deny_globs"]:
        deny.append(claude_path_rule("Read", glob))
    settings = {
        "permissions": {"deny": deny},
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash|Read|Write|Edit|MultiEdit|NotebookEdit|Grep|Glob",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 /opt/hub/harness/claude/hooks/guard.py",
                            "timeout": 10,
                        }
                    ],
                }
            ]
        },
    }
    rules = {
        "_generated": HEADER,
        "bash_deny": [
            {"id": r["id"], "why": r["why"], "regex": r["regex"]} for r in cmd["bash_deny"]
        ],
        "read_deny_globs": cmd["read_deny_globs"],
        "write_allow_roots": cmd["write_allow_roots"],
    }
    return {
        "harness/claude/settings.json": json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        "harness/claude/guard-rules.json": json.dumps(rules, indent=2, ensure_ascii=False) + "\n",
    }


# ---------------------------------------------------------------- Codex
def render_codex(cmd: dict) -> dict[str, str]:
    lines = [f"# {HEADER}", "# execpolicy do Codex: só casa por prefixo de argv.", ""]
    for rule in cmd["bash_deny"]:
        if not rule["prefixes"]:
            lines.append(f"# {rule['id']}: sem equivalente por prefixo (só o hook/proxy cobre).")
            continue
        for prefix in rule["prefixes"]:
            pattern = ", ".join(json.dumps(p) for p in prefix)
            lines.append(
                f"prefix_rule(pattern = [{pattern}], decision = \"forbidden\", "
                f"justification = {json.dumps(rule['why'], ensure_ascii=False)})"
            )
    return {"harness/codex/rules/hub.rules": "\n".join(lines) + "\n"}


# ---------------------------------------------------------------- Gemini CLI
def render_gemini(cmd: dict) -> dict[str, str]:
    exclude = []
    for rule in cmd["bash_deny"]:
        for prefix in rule["prefixes"]:
            exclude.append(f"run_shell_command({shlex.join(prefix)})")
    settings = {"tools": {"exclude": exclude}}
    return {"harness/gemini/settings.json": json.dumps(settings, indent=2) + "\n"}


# ---------------------------------------------------------------- Squid
def check_domains(name: str, domains: list[str]) -> None:
    """Squid recusa ACL com 'x.com' e '.x.com' juntos (o segundo já cobre o primeiro)."""
    for d in domains:
        if d == "*":
            continue
        for other in domains:
            if other != d and other.startswith(".") and (d == other[1:] or d.endswith(other)):
                raise SystemExit(f"egress.toml [{name}]: '{d}' já está coberto por '{other}'; remova um deles")


def render_squid(egress: dict) -> dict[str, str]:
    local = load_optional(OVERLAY / "egress.local.toml")
    deny = egress["deny"]
    out = [
        f"# {HEADER}",
        "# Uma porta por perfil; o perfil é decidido pela porta, não pelo IP de origem.",
        "http_port 3128 name=executor",
        "http_port 3129 name=reader",
        "acl p_executor myportname executor",
        "acl p_reader myportname reader",
        "acl SSL_ports port 443",
        "acl Safe_ports port 80 443",
        "acl CONNECT method CONNECT",
        "acl deny_dst dst " + " ".join(deny["cidrs"]),
        "acl deny_dom dstdomain " + " ".join(deny["domains"]),
    ]
    check_domains("deny", deny["domains"])
    rules = [
        "http_access deny deny_dom",
        # dst resolve o nome: também bloqueia domínios públicos que apontam para IP privado.
        "http_access deny deny_dst",
    ]
    # Exceções de porta por host (antes das regras de porta segura).
    for name, prof in egress["profiles"].items():
        for rule in prof.get("connect", []):
            rid = re.sub(r"[^a-z0-9_]", "_", rule["id"].lower())
            ports = " ".join(str(int(p)) for p in rule["ports"])
            out.append(f"acl cx_{rid}_dom dstdom_regex -i {rule['domain_regex']}")
            out.append(f"acl cx_{rid}_ports port {ports}")
            rules.append(f"http_access allow p_{name} CONNECT cx_{rid}_dom cx_{rid}_ports")
    rules += [
        "http_access deny !Safe_ports",
        "http_access deny CONNECT !SSL_ports",
    ]
    for name, prof in egress["profiles"].items():
        domains = list(prof["domains"]) + list(local.get("extra", {}).get(name, []))
        check_domains(name, domains)
        if domains == ["*"]:
            rules.append(f"http_access allow p_{name}")
        else:
            out.append(f"acl allow_{name} dstdomain " + " ".join(domains))
            rules.append(f"http_access allow p_{name} allow_{name}")
    rules.append("http_access deny all")
    out += rules + [
        "cache deny all",
        "via off",
        "forwarded_for delete",
        "access_log stdio:/dev/stdout",
        "cache_log stdio:/dev/stderr",
        "pid_filename none",
        "",
    ]
    return {"proxy/squid.conf": "\n".join(out)}


# ---------------------------------------------------------------- pull barrier
def render_protected(prot: dict) -> dict[str, str]:
    body = "\n".join([f"# {HEADER}", *prot["globs"]]) + "\n"
    return {"harness/protected-paths.txt": body}


def render_all() -> dict[str, str]:
    cmd = load("commands.toml")
    files: dict[str, str] = {}
    files |= render_claude(cmd)
    files |= render_codex(cmd)
    files |= render_gemini(cmd)
    files |= render_squid(load("egress.toml"))
    files |= render_protected(load("protected-paths.toml"))
    # Valida que ingest/mcp-scopes são TOML válido (consumidos em runtime pelo hub-rag).
    load("ingest.toml")
    scopes = load("mcp-scopes.toml")["scopes"]
    for name, scope in scopes.items():
        for key in ("read", "write", "tools", "rate_per_minute"):
            if key not in scope:
                raise SystemExit(f"mcp-scopes.toml: escopo '{name}' sem '{key}'")
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="só verifica, não escreve")
    args = ap.parse_args()
    stale = []
    for rel, content in render_all().items():
        path = ROOT / rel
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == content:
            continue
        if args.check:
            stale.append(rel)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"escrito: {rel}")
    if stale:
        print("Arquivos gerados desatualizados (rode scripts/render-policy.py):", *stale, sep="\n  ")
        return 1
    if args.check:
        print("policy OK: todos os arquivos gerados estão atualizados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
