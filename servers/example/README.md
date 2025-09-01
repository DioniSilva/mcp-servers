# mcp-example-server

Servidor MCP (Model Context Protocol) de exemplo, com duas tools básicas:
- `echo`: retorna o texto recebido
- `time_now`: devolve a hora atual (UTC) em ISO-8601

## Instalação
```bash
cd mcp-servers/servers/example
pip install -e .
```

## Execução
- Via entry point (STDIO):
```bash
mcp-example
```
- Via módulo Python:
```bash
python -m example_server.main
```

## Inspecionar com MCP Inspector
```bash
uv run mcp dev src/example_server/main.py:server
```

> Use este pacote como base mínima para criar novos servidores MCP.
