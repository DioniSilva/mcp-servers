## 🎯 Objetivo

- Manter um projeto enxuto com um pacote por servidor MCP.
- Fornecer um template para criar novos servidores rapidamente.
- Integrar com o Codex via STDIO e facilitar testes locais.

---

## ✅ Pré‑requisitos

- Python ≥ 3.10
- uv instalado (opcional, para usar `mcp dev`): `pipx install uv`
- Acesso ao Codex (CLI/desktop) e permissão para editar `~/.codex/config.toml`

> Dica: em WSL, mantenha o projeto no filesystem Linux (ex.: `~/projects/mcp-servers`).

---

## Estrutura do Projeto

```
mcp-servers/
├─ Makefile
├─ README.md
├─ AGENTS.md
└─ servers/
   ├─ example/
   │  ├─ pyproject.toml
   │  └─ src/example_server/main.py
   └─ _template/
      ├─ pyproject.toml
      ├─ src/echo_server/main.py
      └─ tests/test_tools.py
```

---

## Criar um novo servidor (scaffold)

Use o template oficial para gerar um novo servidor MCP:

```bash
cd mcp-servers
make server NAME=meu-servidor DESCRIPTION="desc opcional" AUTHOR="nome opcional"
```

Isso cria `servers/meu-servidor` com:
- `pyproject.toml` ajustado (nome do pacote e entry point)
- pacote Python em `src/<nome_do_pacote>/`
- README com instruções básicas

Edite `src/<nome_do_pacote>/main.py` e adicione suas `@server.tool(...)` conforme necessário.

---

## Rodar localmente

Instalação em modo desenvolvimento:

```bash
cd mcp-servers/servers/<nome>
pip install -e .
```

Executar via entry point (STDIO):

```bash
mcp-<nome>-server
```

Ou via módulo Python (útil para `mcp dev`):

```bash
python -m <nome_do_pacote>.main
```

Inspecionar com MCP Inspector (uv):

```bash
cd mcp-servers/servers/<nome>
uv run mcp dev src/<nome_do_pacote>/main.py:server
```

---

## Configurar no Codex

Use o alvo do Makefile para escrever a entrada em `~/.codex/config.toml`:

```bash
cd mcp-servers
make codex-config NAME=<nome>
```

Isso detecta o pacote em `servers/<nome>/src/*/main.py` e configura `command`, `args`, `cwd` e variáveis de ambiente (carregadas de `servers/<nome>/.env`, se existir).

> Recomenda-se manter segredos fora do git e usar `.env` por servidor (gitignored).

---

## Testes, Lint e Formatação

Executar em todos os servidores (o template é ignorado nos testes):

```bash
cd mcp-servers
make install   # instala todos os servidores em -e com [dev]
make test      # pytest servers (ignora servers/_template)
make lint      # ruff + black --check
make fmt       # ruff format + black
```

---

## Boas práticas

- Um pacote por servidor; evite dependências cruzadas.
- Mantenha as tools pequenas e puras; mova I/O para módulos de serviço.
- Defina configurações por ambiente via `.env` no diretório do servidor.
- Use timeouts e rate limits configuráveis por env quando fizer I/O externo.
- Tipos com `pydantic`/`dataclasses` para entradas/saídas previsíveis.


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
