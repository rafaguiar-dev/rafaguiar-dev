"""Mantém a coluna "Latest" do README do perfil em dia com as releases.

Roda todo dia no GitHub Actions (.github/workflows/update-readme.yml) e só mexe
no que está entre <!-- release:NOME-DO-REPO --> e <!-- /release:NOME-DO-REPO -->:
a última versão publicada e a data. Rascunhos (draft) não contam.
Sem dependências: só a biblioteca padrão.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from pathlib import Path

OWNER = "rafaguiar-dev"
README = Path(__file__).resolve().parent.parent / "README.md"
API = "https://api.github.com"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()  # fixo: não depende do locale


def get(path: str):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": f"{OWNER}-profile-readme",
    })
    if token := os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {token}")
    for attempt in range(3):  # a API às vezes demora a responder; 3 tentativas resolvem
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except (TimeoutError, OSError):
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))


def published_releases(repo: str) -> list[dict]:
    out, page = [], 1
    while True:
        batch = get(f"/repos/{OWNER}/{repo}/releases?per_page=100&page={page}")
        out += [r for r in batch if not r["draft"]]
        if len(batch) < 100:
            return out
        page += 1


def short_date(iso: str) -> str:
    """2026-10-03T21:16:32Z -> Oct&nbsp;3,&nbsp;2026 (não quebra na coluna estreita)."""
    year, month, day = (int(x) for x in iso[:10].split("-"))
    return f"{MONTHS[month - 1]}&nbsp;{day},&nbsp;{year}"


def fill(text: str, marker: str, value: str) -> str:
    pattern = re.compile(rf"(<!-- {re.escape(marker)} -->).*?(<!-- /{re.escape(marker)} -->)", re.S)
    return pattern.sub(lambda m: m.group(1) + value + m.group(2), text)


def main() -> None:
    before = README.read_text(encoding="utf-8")
    text = before
    repos = [r["name"] for r in get(f"/users/{OWNER}/repos?per_page=100&type=owner") if not r["fork"]]
    for repo in repos:
        releases = published_releases(repo)
        if releases:
            last = max(releases, key=lambda r: r["published_at"])
            text = fill(text, f"release:{repo}",
                        f'<a href="{last["html_url"]}"><code>{last["tag_name"]}</code></a><br>'
                        f'<sub>{short_date(last["published_at"])}</sub>')

    if text == before:
        print("nada mudou")
        return
    README.write_text(text, encoding="utf-8")
    print(f"README atualizado ({len(repos)} repositórios conferidos)")


if __name__ == "__main__":
    main()
