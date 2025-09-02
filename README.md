# Ferramentas MCP (Model Context Protocol)

Repositório para servidores MCP escritos em Python. Mantemos apenas um servidor de exemplo genérico para servir de referência de empacotamento e execução.

## Estrutura
- `servers/example`: servidor MCP mínimo com duas tools (`echo`, `time_now`)
- `AGENTS.md`: guia de contribuição
- `Makefile`: `install`, `test`, `lint`, `fmt`, `codex-config`

## Pré‑requisitos
- Python 3.10+
- SDK MCP: `pip install mcp` (instalado via `make install` também)

## Servidor de Exemplo
Instalação e execução:
```bash
cd servers/example
pip install -e .
python -m example_server.main
# ou via entry point
mcp-example
```

Configurar no Codex (~/.codex/config.toml):
```bash
make codex-config NAME=example
```
Isso cria/atualiza `[mcp_servers.example]` com command/args/cwd/env apropriados.

## Inspecionar com MCP Inspector (via uv)
Você pode usar o CLI do SDK MCP para subir o servidor com um inspector interativo e testar as tools.

Pré‑requisito: ter `mcp` instalado (vem como dependência) e o `uv` configurado.

### Exemplo (pacote em `servers/example`)
- Abrir o inspector:
  ```bash
  cd servers/example
  uv run mcp dev src/example_server/main.py:server
  ```

Notas
- O modo `dev` instala dependências temporariamente se necessário e abre o inspector.
- Em ambientes sem STDIN (CI), o processo pode encerrar imediatamente — isso é normal.

## Testes e Qualidade
```bash
make install   # instala todos os servidores em modo editable com deps de dev
make test      # roda pytest em servers/
make lint      # ruff + black --check
make fmt       # ruff format + black
```

## Publicação (PyPI Trusted Publishers)
Configuração via OIDC (recomendado) seguindo PyPI > Account > Publishing. Os workflows vivem dentro de `mcp-servers/.github/workflows` neste monorepo.

Guia completo: veja `PUBLISHING.md`.

1) No PyPI, crie um Trusted Publisher para o projeto do servidor
- Project name: ex.: `mcp-example-server`
- Provider: GitHub
- Repository: `<owner>/<repo>` (este monorepo)
- Workflow filename: `.github/workflows/publish-mcp-example.yml`
- Environment: (opcional)

2) No GitHub, o workflow já possui `permissions: id-token: write`. Este monorepo mantém o workflow em `mcp-servers/.github/workflows/publish-*.yml`. Se preferir rodar automaticamente no repositório, você pode copiar este arquivo para a raiz em `.github/workflows/`.

3) Versão e tag
- Opção A (recomendada): use o helper de release
  ```bash
  # bump patch/minor/major
  make release NAME=example PART=patch
  # ou defina explicitamente a versão
  make release NAME=example VERSION=0.1.4
  # depois envie a tag criada para o remoto
  git push origin example-v0.1.4
  ```
- Opção B (manual):
  - Atualize `servers/example/pyproject.toml` (`project.version`).
  - Crie uma tag seguindo o padrão: `example-v<versão>` (ex.: `example-v0.1.0`).
  - Ao fazer push da tag, o workflow compila e publica o pacote.

4) Múltiplos servidores
- Copie `mcp-servers/.github/workflows/publish-mcp-example.yml` e ajuste o caminho/tag para cada servidor novo.
- Crie também a entrada de Trusted Publisher para cada pacote em PyPI.

5) TestPyPI (opcional)
- Você pode duplicar o workflow e usar `repository-url: https://test.pypi.org/legacy/` no passo de publicação, configurando um Trusted Publisher em `test.pypi.org`.

## Criar novos servidores
- Automático (recomendado):
  ```bash
  make server NAME=meu-servidor DESCRIPTION="desc opcional" AUTHOR="nome opcional"
  ```
  Gera `servers/<NAME>` a partir de `servers/_template`, ajusta pacote/entry point e cria README do servidor.
- Manual: copie `servers/example` para `servers/<NAME>` e ajuste:
  - `pyproject.toml`: `name` e entry point em `[project.scripts]`
  - Pacote em `src/<nome_do_pacote>/`
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
