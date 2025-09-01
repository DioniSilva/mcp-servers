from datetime import datetime, timezone

try:
    from mcp.server.fastmcp import FastMCP
except Exception as e:
    raise SystemExit(
        "Pacote 'mcp' não encontrado. Instale com: pip install mcp\n" f"Detalhes: {e}"
    )


server = FastMCP(name="mcp-example")


@server.tool(
    name="echo",
    description="Retorna exatamente o texto recebido.",
)
async def echo(text: str) -> str:
    return text


@server.tool(
    name="time_now",
    description="Retorna a hora atual em ISO-8601 (UTC).",
)
async def time_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main_cli() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main_cli()

