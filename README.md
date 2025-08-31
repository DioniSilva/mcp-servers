# Ferramentas MCP (Model Context Protocol)

Repositório para servidores MCP escritos em Python. Já inclui um servidor de busca na web (Google CSE) e utilitários para criar/registrar novos servidores.

## Estrutura do Projeto
- `servers/`
  - `web-search/`: busca Google CSE e fetch de páginas (principal)
  - `notion/`: cliente genérico Notion (opcional, pode ser desativado)
  - `echo-py/`: exemplo mínimo e base do template
  - `_template/`: template dedicado para `make server`
- `AGENTS.md`: guia de contribuição
- `Makefile`: `install`, `test`, `lint`, `fmt`, `verify-*`, `server`, `codex-config`

## Pré‑requisitos
- Python 3.10+
- SDK MCP: `pip install mcp` (instalado via `make install` também)

## Servidor web-search (Google CSE)
Instalação e execução:
```bash
cd servers/web-search
pip install -e .
python -m web_search.main
```
Variáveis: defina `GOOGLE_API_KEY` e `GOOGLE_CSE_ID` (veja servers/web-search/README.md). Verificação rápida: `make verify-web-search`.

Configurar no Codex (~/.codex/config.toml):
```bash
make codex-config NAME=web-search
```
Isso cria/atualiza `[mcp_servers.web-search]` com command/args/cwd/env apropriados.

## Inspecionar com MCP Inspector (via uv)
Você pode usar o CLI do SDK MCP para subir o servidor com um inspector interativo e testar as tools.

Pré‑requisito: ter `mcp` instalado (vem como dependência) e o `uv` configurado.

### Web Search (pacote em `servers/web-search`)
- Exporte variáveis (necessário para `web_search`):
  ```bash
  export GOOGLE_API_KEY="sua-chave"
  export GOOGLE_CSE_ID="seu-cse-id"
  ```
- Abrir o inspector:
  ```bash
  cd servers/web-search
  uv run mcp dev src/web_search/main.py
  # ou, usando o objeto explicitamente
  uv run mcp dev src/web_search/main.py:server
  ```
- No inspector, chame as tools `web_search` e `fetch_url` e verifique as respostas.

### Projeto mínimo (em `my-mcp`)
Se você estiver usando o esqueleto mínimo descrito em `AGENTS.md`:
```bash
cd my-mcp
uv sync
# opcional: exports como acima para usar web_search
uv run mcp dev servers/websearch/server.py
# ou
uv run mcp dev servers/websearch/server.py:server
```

Notas
- O modo `dev` instala dependências temporariamente se necessário e abre o inspector.
- Para um "smoke test" sem inspector, use `mcp run`:
  ```bash
  uv run mcp run servers/web-search/src/web_search/main.py -t stdio
  ```
- Em ambientes sem STDIN (CI), o processo pode encerrar imediatamente — isso é normal.

## Testes e Qualidade
```bash
make install   # instala todos os servidores em modo editable com deps de dev
make test      # roda pytest em servers/
make lint      # ruff + black --check
make fmt       # ruff format + black
```

## Criar novos servidores
- Automático (recomendado):
  ```bash
  make server NAME=meu-servidor DESCRIPTION="desc opcional" AUTHOR="nome opcional"
  ```
  Gera `servers/<NAME>` a partir de `servers/_template`, ajusta pacote/entry point e cria README do servidor.
- Registrar no Codex:
  ```bash
  make codex-config NAME=<NAME>
  ```

## Boas práticas
- Um pacote por servidor; sem dependências cruzadas
- Ferramentas pequenas com `input_schema`; respostas em texto e JSON
- Segredos fora do git; use `.env` (gitignored) e `~/.codex/config.toml`
- Rate limits e timeouts configuráveis por env

—
Consulte `AGENTS.md` para convenções de estilo, commits e PRs.
