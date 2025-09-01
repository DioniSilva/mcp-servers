# Template de Servidor MCP

Use esta pasta como base para criar um novo servidor MCP.

## Estrutura
- `pyproject.toml`: metadados e entry point (será ajustado pelo Makefile)
- `src/echo_server/`: pacote Python com `main.py` expondo `server` e `main_cli`
- `tests/`: teste básico de verificação de tools

## Geração automática
```bash
make server NAME=meu-servidor DESCRIPTION="desc opcional" AUTHOR="nome opcional"
```
Isso cria `servers/meu-servidor` com o pacote renomeado e entry point adequado.
