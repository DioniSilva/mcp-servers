# Publicação no PyPI (Trusted Publishers)

Este guia explica como publicar cada servidor (um pacote por pasta em `servers/<nome>`) no PyPI usando Trusted Publishers (OIDC) e, opcionalmente, como publicar manualmente.

## Visão Geral
- Cada servidor é um pacote Python independente com `pyproject.toml` em `servers/<nome>`.
- Usamos GitHub Actions com OIDC (Trusted Publishers) — sem armazenar tokens.
- O workflow de exemplo está em `mcp-servers/.github/workflows/publish-mcp-example.yml` e publica o pacote `servers/example` quando uma tag `example-v<versão>` é enviada.

> Observação (GitHub Actions): o GitHub só executa automaticamente workflows em `.github/workflows` na RAIZ do repositório. Os arquivos dentro de `mcp-servers/.github/workflows` servem como referência. Para automatizar a publicação neste monorepo, crie/copiem workflows equivalentes para a raiz do repositório, ou mantenha um workflow raiz que aponte para cada servidor.

## Passo 1 — Criar o Trusted Publisher no PyPI
1. Acesse sua conta no PyPI: Account → Publishing → Add a Publisher.
2. Configure:
   - Provider: GitHub
   - Repository: `<owner>/<repo>` (este repositório)
   - Workflow filename: `.github/workflows/publish-mcp-example.yml` (ou outro, se duplicar)
   - Project name: nome do pacote (ex.: `mcp-example-server`). Se ainda não existir no PyPI, a primeira publicação cria o projeto.
   - Environment: deixe em branco, a menos que use environments do GitHub.
3. Salve. O PyPI agora aceitará publicações OIDC vindas desse repositório/workflow.

## Passo 2 — Garantir o workflow
- Arquivo de referência: `mcp-servers/.github/workflows/publish-mcp-example.yml`.
- Para publicação automática, copie o arquivo para a RAIZ do repo em `.github/workflows/publish-mcp-example.yml` ou crie um workflow raiz equivalente apontando para o mesmo pacote/tag.

Estrutura do workflow (resumo):
- Checa que a tag = `example-v<versão>` bate com `project.version` do `pyproject.toml`.
- Faz `python -m build` no diretório do servidor.
- Publica com `pypa/gh-action-pypi-publish` usando OIDC (sem secrets).

## Passo 3 — Versionar e taggear
1. Edite `servers/example/pyproject.toml` e atualize `project.version` (ex.: `0.1.1`).
2. Crie uma tag no formato esperado pelo workflow:
   ```bash
   git tag example-v0.1.1
   git push origin example-v0.1.1
   ```
3. O workflow dispara na tag, builda e publica.

## Vários servidores
- Duplique `mcp-servers/.github/workflows/publish-mcp-example.yml` para `publish-<nome>.yml` e ajuste:
  - Padrão da tag (ex.: `web-search-v*`, `notion-v*`).
  - `working-directory` e `packages-dir` para `servers/<nome>`.
  - Validação da tag (o prefixo no script Python).
- Crie um Trusted Publisher correspondente no PyPI para cada pacote.

## TestPyPI (opcional)
- Copie o workflow e adicione no passo de publicação:
  ```yaml
  with:
    repository-url: https://test.pypi.org/legacy/
  ```
- Crie o Trusted Publisher também em `test.pypi.org`.

## Publicação manual (fallback)
Se não quiser/precisar usar OIDC:
1. Crie um token de API no PyPI (Account → API tokens) com escopo para o projeto.
2. No diretório do servidor:
   ```bash
   python -m pip install --upgrade build twine
   python -m build
   twine upload dist/*
   ```
3. Informe o token quando solicitado (`__token__` como usuário, e o valor do token como senha), ou configure `~/.pypirc`.

## Solução de problemas
- Tag não dispara workflow: verifique se o arquivo está na RAIZ (`.github/workflows`) e o padrão da tag confere.
- Erro “Tag não corresponde à versão”: alinhe `project.version` e o sufixo da tag.
- 403 na publicação: confirme o Trusted Publisher no PyPI e `permissions: id-token: write` no workflow.
- Nome de projeto já existe: escolha outro nome em `project.name` no `pyproject.toml`.
