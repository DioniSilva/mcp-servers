#!/usr/bin/env python3

"""
Release helper: bump a server version and create a git tag.

Usage examples:
  - Bump patch:   python scripts/release.py --server example --bump patch
  - Bump minor:   python scripts/release.py --server example --bump minor
  - Bump major:   python scripts/release.py --server example --bump major
  - Set version:  python scripts/release.py --server example --new-version 0.2.0

By default, the script will:
  1) Update servers/<name>/pyproject.toml [project].version
  2) git add the file and commit
  3) Create an annotated git tag using the distribution name, e.g.: mcp-example-server@v0.2.0

Flags:
  --dry-run     Show actions without changing files or running git
  --no-git      Do not run git commit/tag (only update the file)
  --message     Custom commit message (optional)
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


@dataclass
class ProjectInfo:
    name: str
    version: str


def repo_root() -> Path:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
        return Path(out.strip())
    except Exception:
        return Path.cwd()


def load_project_info(pyproject_path: Path) -> ProjectInfo:
    name = None
    version = None
    in_project = False
    for raw in pyproject_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            in_project = line == "[project]"
            continue
        if not in_project:
            continue
        if line.startswith("name"):
            m = re.match(r'name\s*=\s*"([^"]+)"', line)
            if m:
                name = m.group(1)
        elif line.startswith("version"):
            m = re.match(r'version\s*=\s*"([^"]+)"', line)
            if m:
                version = m.group(1)
        if name and version:
            break
    if not name or not version:
        raise RuntimeError(f"Não foi possível ler [project].name/version em {pyproject_path}")
    return ProjectInfo(name=name, version=version)


def compute_bumped_version(current: string, bump: str | None, new_version: str | None) -> str:
    if (bump is None) == (new_version is None):
        raise ValueError("Informe exatamente um: --bump {patch,minor,major} OU --new-version X.Y.Z")
    if new_version is not None:
        if not SEMVER_RE.match(new_version):
            raise ValueError(f"Versão inválida: {new_version}. Use X.Y.Z")
        return new_version
    m = SEMVER_RE.match(current)
    if not m:
        raise ValueError(f"Versão atual não segue semver X.Y.Z: {current}")
    major, minor, patch = map(int, m.groups())
    if bump == "patch":
        patch += 1
    elif bump == "minor":
        minor += 1
        patch = 0
    elif bump == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError("--bump deve ser patch|minor|major")
    return f"{major}.{minor}.{patch}"


def update_pyproject_version(pyproject_path: Path, new_version: str, dry_run: bool) -> None:
    text = pyproject_path.read_text(encoding="utf-8").splitlines()
    in_project = False
    replaced = False
    for i, raw in enumerate(text):
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            in_project = line == "[project]"
            continue
        if in_project and line.startswith("version"):
            m = re.match(r'(\s*)version\s*=\s*"([^"]+)"', raw)
            if m:
                indent = m.group(1)
                text[i] = f'{indent}version = "{new_version}"'
                replaced = True
                break
    if not replaced:
        raise RuntimeError("Não encontrei a linha version = \"...\" em [project]")
    if dry_run:
        print(f"[dry-run] Atualizaria {pyproject_path} para versão {new_version}")
        return
    pyproject_path.write_text("\n".join(text) + "\n", encoding="utf-8")


def run_git(args: list[str], cwd: Path, dry_run: bool) -> None:
    if dry_run:
        print("[dry-run] git", " ".join(args))
        return
    subprocess.check_call(["git", *args], cwd=str(cwd))


def ensure_git_repo(cwd: Path) -> None:
    try:
        subprocess.check_call(["git", "rev-parse", "--is-inside-work-tree"], cwd=str(cwd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        raise SystemExit("Este diretório não parece ser um repositório Git.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bump de versão e criação de tag para um servidor MCP")
    p.add_argument("--server", required=True, help="nome do servidor (diretório em servers/<name>)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--bump", choices=["patch", "minor", "major"], help="tipo de incremento semântico")
    g.add_argument("--new-version", help="define versão explicitamente no formato X.Y.Z")
    p.add_argument("--message", help="mensagem de commit personalizada")
    p.add_argument("--no-git", action="store_true", help="não executar git commit/tag")
    p.add_argument("--dry-run", action="store_true", help="não altera arquivos nem executa git")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    root = repo_root()
    ensure_git_repo(root)

    server = args.server
    server_dir = root / "servers" / server
    pyproject = server_dir / "pyproject.toml"
    if not pyproject.exists():
        raise SystemExit(f"pyproject.toml não encontrado em {pyproject}")

    info = load_project_info(pyproject)
    new_version = compute_bumped_version(info.version, args.bump, args.new_version)

    print(f"Servidor: {server} | pacote: {info.name}")
    print(f"Versão atual: {info.version} -> nova: {new_version}")

    update_pyproject_version(pyproject, new_version, dry_run=args.dry_run)

    if args.no_git:
        print("--no-git: pulando commit e tag")
        return

    rel_path = os.path.relpath(str(pyproject), str(root))
    commit_msg = args.message or f"chore({server}): release v{new_version}"
    # Tag padrão para compatibilidade com workflows: <server>-vX.Y.Z
    tag_name = f"{server}-v{new_version}"
    tag_msg = f"Release {server} v{new_version}"

    # Stage, commit and tag
    run_git(["add", rel_path], cwd=root, dry_run=args.dry_run)
    run_git(["commit", "-m", commit_msg], cwd=root, dry_run=args.dry_run)
    run_git(["tag", "-a", tag_name, "-m", tag_msg], cwd=root, dry_run=args.dry_run)

    print(f"OK: commit criado e tag {tag_name} gerada.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)
