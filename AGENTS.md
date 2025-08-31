## 🎯 Objetivo

* Ter um repositório enxuto (`my-mcp/`) com **estrutura organizada**, pronto para escalar.
* Rodar localmente com `uv`.
* Integrar com o **Codex** via STDIO.

---

## ✅ Pré‑requisitos

* **Python** ≥ 3.10
* **uv** instalado (`pipx install uv` ou binário oficial)
* Acesso ao **Codex** (CLI/desktop) e permissão para editar `~/.codex/config.toml`

> Dica: no **WSL**, mantenha o projeto no filesystem Linux (ex.: `~/projects/my-mcp`).

---

## 1) Estrutura de pastas

```
my-mcp/
├─ pyproject.toml
└─ servers/
   └─ websearch/
      ├─ __init__.py
      └─ server.py
```

---

## 2) `pyproject.toml`

Use dependência leve com o SDK MCP.

```toml
[project]
name = "my-mcp-servers"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
  "mcp[cli]>=1.13.0",
  "httpx>=0.27.0",
  "beautifulsoup4>=4.12.3",
  "pydantic>=2.7.0"
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

```

## 2.1) Variáveis de ambiente (necessárias para o Web Search)

```bash
# Obrigatórias
export GOOGLE_API_KEY="seu-api-key"
export GOOGLE_CSE_ID="seu-cse-id"

# Opcionais (padrões no código)
export WEB_RPS=1
export WEB_BURST=5
export WEB_SEARCH_TIMEOUT=10
export WEB_FETCH_TIMEOUT=10
export WEB_FETCH_MAX_CHARS=8000


> Se preferir imobilizar versões para CI, fixe os pins em um `uv.lock` (gerado pelo `uv sync`).

---


## 3) Primeiro server MCP — `servers/websearch/server.py`
Troque a seção inteira do “greeter” pelo teu código (coloque exatamente assim, dentro do arquivo `servers/websearch/server.py`):

```python
import os
import time
import asyncio
from typing import Any, Dict, List

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel

try:
    # Use FastMCP, which provides the @tool decorator API
    from mcp.server.fastmcp import FastMCP
except Exception as e:
    raise SystemExit(
        "Pacote 'mcp' não encontrado. Instale com: pip install mcp\n" f"Detalhes: {e}"
    )


class RateLimiter:
    def __init__(self, rate_per_sec: float, burst: int):
        self.capacity = float(burst)
        self.tokens = float(burst)
        self.rate = float(rate_per_sec)
        self.timestamp = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.timestamp
            self.timestamp = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) / self.rate if self.rate > 0 else 0
                await asyncio.sleep(max(0, wait_time))
                self.tokens = 0.0
            else:
                self.tokens -= 1.0


WEB_RPS = float(os.getenv("WEB_RPS", "1"))
WEB_BURST = int(os.getenv("WEB_BURST", "5"))
_limiter = RateLimiter(WEB_RPS, WEB_BURST)

server = FastMCP(name="mcp-web-search")


class SearchItem(BaseModel):
    title: str | None = None
    link: str
    snippet: str | None = None


class WebSearchResponse(BaseModel):
    results: List[SearchItem]


class FetchUrlResponse(BaseModel):
    url: str
    title: str | None = None
    text: str


async def _google_search(query: str, site: str | None, limit: int) -> List[Dict[str, Any]]:
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        raise RuntimeError("GOOGLE_API_KEY e GOOGLE_CSE_ID são obrigatórios.")

    q = query
    if site:
        q = f"site:{site} {query}"

    params = {
        "key": api_key,
        "cx": cse_id,
        "q": q,
        "num": max(1, min(10, int(limit))),
    }

    timeout = float(os.getenv("WEB_SEARCH_TIMEOUT", "10"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        await _limiter.acquire()
        resp = await client.get("https://www.googleapis.com/customsearch/v1", params=params)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        results = []
        for it in items:
            results.append(
                {
                    "title": it.get("title"),
                    "link": it.get("link"),
                    "snippet": it.get("snippet"),
                }
            )
        return results


async def _fetch_and_clean(url: str, max_chars: int) -> Dict[str, Any]:
    timeout = float(os.getenv("WEB_FETCH_TIMEOUT", "10"))
    headers = {"User-Agent": "mcp-web-search/0.1"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        await _limiter.acquire()
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    # Remove script/style
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())
    if len(text) > max_chars:
        text = text[:max_chars] + "…"
    return {"title": title, "text": text}


@server.tool(
    name="web_search",
    description="Busca na web via Google CSE e retorna resultados.",
)
async def tool_web_search(
    query: str,
    site: str | None = None,
    limit: int | None = None,
) -> WebSearchResponse:
    try:
        default_limit = int(os.getenv("WEB_SEARCH_LIMIT", "5"))
        results = await _google_search(query, site, limit or default_limit)
        items = [
            SearchItem(title=r.get("title"), link=r.get("link", ""), snippet=r.get("snippet"))
            for r in results
            if r.get("link")
        ]
        return WebSearchResponse(results=items)
    except Exception:
        return WebSearchResponse(results=[])


@server.tool(
    name="fetch_url",
    description="Busca conteúdo de uma URL e retorna texto limpo e metadados.",
)
async def tool_fetch_url(url: str, max_chars: int | None = None) -> FetchUrlResponse:
    try:
        maxc = int(os.getenv("WEB_FETCH_MAX_CHARS", "8000")) if max_chars is None else int(max_chars)
        data = await _fetch_and_clean(url, maxc)
        return FetchUrlResponse(url=url, title=data.get("title"), text=data.get("text", ""))
    except Exception as e:
        return FetchUrlResponse(url=url, title=None, text=f"Erro: {e}")


def main_cli() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main_cli()


> Dica: mantenha as ferramentas **puras** (I/O mínimo), e mova integrações externas (FS, HTTP, DB) para módulos de serviço. Facilita testes.

---

## 4) Instalação e execução local

Dentro do diretório do projeto:

```bash
uv sync
uv run python -m servers.websearch.server
```

Você deve ver o processo aguardando comunicação STDIO (normal para MCP). Para encerrar, `Ctrl+C`.

---

## 5) Integração com o **Codex**

O Codex consome MCP servers via **STDIO**. Adicione uma entrada no arquivo `~/.codex/config.toml`.

> Se o arquivo não existir, crie-o. No Windows, se estiver usando WSL, edite o arquivo **dentro do WSL**.

### 5.1) Configuração (um servidor)

```toml
[mcp_servers.websearch]
command = "uv"
args = ["run", "python", "-m", "servers.websearch.server"]
# opcional:
# cwd = "/home/SEU_USUARIO/projects/my-mcp"
```

> **Importante**: se o Codex iniciar em um diretório diferente, defina `cwd` apontando para a raiz do projeto.

### 5.2) Vários servidores (exemplo)

Você pode ter múltiplos blocos no mesmo `config.toml`:

```toml
[mcp_servers.websearch]
command = "uv"
args = ["run", "python", "-m", "servers.websearch.server"]

[mcp_servers.fs]
command = "uv"
args = ["run", "python", "-m", "servers.fs.server"]
```

> Siga o mesmo padrão de módulo `python -m servers.NOME.server` para cada pasta em `servers/`.

---

## 6) Testes de fumaça (opcional mas recomendado)

Antes de plugar no Codex, valide o protocolo localmente com a CLI do SDK MCP:

```bash
# 1) Em um terminal, suba o server
uv run python -m servers.greeter.server

# 2) Em outro terminal (no mesmo repo), rode ferramentas de inspeção do SDK
# (o nome e os comandos podem variar; use o inspector/dev do SDK MCP disponível)
```

Se o inspector listar a ferramenta `hello`, a negociação MCP básica está OK.

---

## 7) Convenções e boas práticas

* **Nomes estáveis**: o nome passado ao `FastMCP("greeter")` será o identificador do provider no cliente. Evite renomear após configurar no Codex.
* **Declaração de tipos**: anote parâmetros e retorne `str`/objetos serializáveis. Evite objetos complexos não JSON‑serializáveis.
* **Logs**: padronize logs em `stderr` (o STDIO do MCP usa `stdin/stdout` para o protocolo).
* **Timeouts/Rate limiting**: se sua ferramenta fizer I/O externo, aplique timeouts e limites para manter o cliente responsivo.
* **Versionamento**: use version bump semântico ao adicionar/alterar ferramentas. Documente no CHANGELOG.

---

## 8) Problemas comuns (troubleshooting)

* **`uv: command not found`**: instale o `uv` (via `pipx`, Homebrew, ou binário oficial). Reinicie o terminal.
* **Caminhos no WSL**: se o Codex estiver no Windows e o server no WSL, configure `cwd` com o **path Linux** e garanta que o Codex consegue iniciar processos no WSL.
* **Permissões**: dê permissões de execução ao Python e acesso ao diretório do projeto.
* **Múltiplas versões de Python**: confira qual Python o `uv` está usando (`uv run python -V`).
* **Conflitos de STDIO**: não faça `print()` no `stdout`; use logging para `stderr`.

---

## 9) Próximos passos (expandindo o template)

* Adicionar um server `fs` com ferramentas de leitura de arquivos (ex.: `list_dir`, `read_text`).
* Criar camada `services/` para integrações HTTP/DB.
* Escrever testes (ex.: `pytest`) para cada ferramenta.
* Publicar como template no GitHub e automatizar `checks` com CI.

---

## 10) TL;DR comandos essenciais

```bash
# criar/entrar no projeto
mkdir -p ~/projects/my-mcp && cd ~/projects/my-mcp

# (adicione os arquivos conforme as seções 1–3 deste guia)

# instalar deps
uv sync

# rodar o server para debug
uv run python -m servers.greeter.server

# configurar o Codex
# edite ~/.codex/config.toml e adicione o bloco [mcp_servers.greeter]

# reinicie o Codex/CLI e use a ferramenta `hello` no cliente
```

## 11) Script de bootstrap do projeto (opcional)
Se quiser criar tudo de uma vez, rode este script no diretório onde o projeto deve existir:

```bash
mkdir -p my-mcp/servers/websearch
cat > my-mcp/pyproject.toml <<'PY'
[project]
name = "my-mcp-servers"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
  "mcp[cli]>=1.13.0",
  "httpx>=0.27.0",
  "beautifulsoup4>=4.12.3",
  "pydantic>=2.7.0"
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
PY

cat > my-mcp/servers/websearch/__init__.py <<'PY'
# empty
PY

cat > my-mcp/servers/websearch/server.py <<'PY'
# (cole aqui o código do server enviado na sua mensagem)
PY

cd my-mcp
uv sync
```