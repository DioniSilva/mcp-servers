from echo_server.main import server


def test_server_has_tools():
    # server.tools é preenchido pelo FastMCP com tools registradas
    names = {t.name for t in server.tools}
    assert "echo" in names
    assert "time_now" in names

