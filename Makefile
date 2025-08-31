.PHONY: help install test lint fmt server verify-web-search verify-notion codex-config

help:
	@echo "Targets: install, test, lint, fmt"

install:
	# instala todos os servidores com extras de dev
	@set -e; for d in servers/*; do \
	  if [ -f "$${d}/pyproject.toml" ]; then \
	    pip install -e "$${d}[dev]"; \
	  fi; \
	done

test:
	pytest -q servers

lint:
	ruff check servers
	black --check servers

fmt:
	ruff format servers
	black servers

# Verifica Google CSE usando variáveis do .env do web-search (ou ambiente)
verify-web-search:
	@set -e; \
	if [ -f servers/web-search/.env ]; then set -a; . servers/web-search/.env; set +a; fi; \
	: "$${GOOGLE_API_KEY:?Defina GOOGLE_API_KEY no ambiente ou em servers/web-search/.env}"; \
	: "$${GOOGLE_CSE_ID:?Defina GOOGLE_CSE_ID no ambiente ou em servers/web-search/.env}"; \
	url="https://www.googleapis.com/customsearch/v1?key=$${GOOGLE_API_KEY}&cx=$${GOOGLE_CSE_ID}&q=teste"; \
	echo "Testando Google CSE..."; \
	echo "URL: $$url"; \
	code=0; body=$$(curl -sS -w "\n%{http_code}\n" "$$url" || code=$$?); \
	status=$$(printf "%s" "$$body" | tail -n1); payload=$$(printf "%s" "$$body" | sed '$$d'); \
	if [ "$$code" -ne 0 ]; then echo "Falha ao chamar API (curl exit $$code)"; exit $$code; fi; \
	printf "%s\n" "$$payload" | head -c 1000; echo; \
	if [ "$$status" != "200" ]; then echo "HTTP $$status recebido"; exit 1; fi; \
	echo "OK: resposta 200 recebida."

# Verifica Notion usando variáveis do .env do notion (ou ambiente)
verify-notion:
	@set -e; \
	if [ -f servers/notion/.env ]; then set -a; . servers/notion/.env; set +a; fi; \
	: "$${NOTION_API_KEY:?Defina NOTION_API_KEY no ambiente ou em servers/notion/.env}"; \
	ver="$${NOTION_VERSION:-2022-06-28}"; \
	echo "Testando Notion API..."; \
	code=0; body=$$(curl -sS -w "\n%{http_code}\n" -H "Authorization: Bearer $${NOTION_API_KEY}" -H "Notion-Version: $$ver" "https://api.notion.com/v1/users" || code=$$?); \
	status=$$(printf "%s" "$$body" | tail -n1); payload=$$(printf "%s" "$$body" | sed '$$d'); \
	if [ "$$code" -ne 0 ]; then echo "Falha ao chamar API (curl exit $$code)"; exit $$code; fi; \
	printf "%s\n" "$$payload" | head -c 1000; echo; \
	if [ "$$status" != "200" ]; then echo "HTTP $$status recebido"; exit 1; fi; \
	echo "OK: resposta 200 recebida."

# Configura ~/.codex/config.toml para um servidor arbitrário
# Uso: make codex-config NAME=web-search
# - Lê servers/$(NAME)/.env se existir e injeta as variáveis no bloco env
# - Detecta o pacote Python como o diretório em servers/$(NAME)/src/* contendo main.py
codex-config:
	@set -e; \
	name="$(NAME)"; \
	if [ -z "$$name" ]; then echo "Uso: make codex-config NAME=<server>"; exit 1; fi; \
	dest="servers/$$name"; \
	if [ ! -d "$$dest" ]; then echo "Servidor $$dest não encontrado"; exit 1; fi; \
	# Carrega .env específico do servidor (opcional)
	if [ -f "$$dest/.env" ]; then set -a; . "$$dest/.env"; set +a; fi; \
	# Detecta pacote Python (src/<pkg>/main.py)
	pkg_dir=$$(ls -1d "$$dest/src/"*/ 2>/dev/null | head -n1); \
	if [ -z "$$pkg_dir" ] || [ ! -f "$$pkg_dir/main.py" ]; then \
	  guess_pkg=$$(printf '%s' "$$name" | tr '-' '_'); pkg_dir="$$dest/src/$$guess_pkg"; \
	fi; \
	if [ ! -f "$$pkg_dir/main.py" ]; then echo "Não encontrei $$dest/src/*/main.py"; exit 1; fi; \
	pkg=$$(basename "$$pkg_dir"); \
		cwd="$$(cd "$$dest" && pwd)"; \
		src_path="$$cwd/src"; \
		# Constrói env = { ... }: sempre inclui PYTHONUNBUFFERED e PYTHONPATH absolutos
		env_pairs="\"PYTHONUNBUFFERED\" = \"1\", \"PYTHONPATH\" = \"$$src_path\""; \
		if [ -f "$$dest/.env" ]; then \
		  while IFS= read -r line; do \
		    case "$$line" in \#*|"" ) continue;; esac; \
		    key=$${line%%=*}; val=$${line#*=}; \
		    val_esc=$$(printf '%s' "$$val" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'); \
		    env_pairs="$$env_pairs, \"$$key\" = \"$$val_esc\""; \
		  done < "$$dest/.env"; \
		fi; \
		env_table="{ $$env_pairs }"; \
	confdir="$$HOME/.codex"; conffile="$$confdir/config.toml"; \
	mkdir -p "$$confdir"; touch "$$conffile"; \
	tmpfile=$$(mktemp); \
	sed "/# BEGIN mcp $$name/,/# END mcp $$name/d" "$$conffile" > "$$tmpfile"; \
	pybin=$$(command -v python || command -v python3 || true); \
	if [ -z "$$pybin" ]; then echo "Python não encontrado no PATH"; rm -f "$$tmpfile"; exit 1; fi; \
	# Garante PYTHONUNBUFFERED=1; evita buffering no stdout
	if [ "$$env_table" = "{}" ]; then env_table='{ "PYTHONUNBUFFERED" = "1" }'; \
	else \
	  case "$$env_table" in *'"PYTHONUNBUFFERED"'*) : ;; *) env_table=$$(printf '%s' "$$env_table" | sed 's/}$/, \"PYTHONUNBUFFERED\" = \"1\"}/');; esac; \
	fi; \
	echo "# BEGIN mcp $$name" >> "$$tmpfile"; \
	echo "[mcp_servers.$$name]" >> "$$tmpfile"; \
	echo "command = \"$$pybin\"" >> "$$tmpfile"; \
		echo "args = [\"-m\", \"$$pkg.main\"]" >> "$$tmpfile"; \
	echo "cwd = \"$$cwd\"" >> "$$tmpfile"; \
	echo "env = $$env_table" >> "$$tmpfile"; \
	echo "# END mcp $$name" >> "$$tmpfile"; \
	mv "$$tmpfile" "$$conffile"; \
	echo "Configurado: [mcp_servers.$$name] em $$conffile"; \
	echo "Reinicie o Codex para carregar as mudanças."

# Cria um novo servidor Python a partir do template echo-py
# Uso: make server NAME=meu-servidor
server:
	@test -n "$(NAME)" || (echo "Uso: make server NAME=meu-servidor [DESCRIPTION='desc'] [AUTHOR='Nome']" && exit 1)
	@name="$(NAME)"; pkg=$$(printf '%s' "$$name" | tr '-' '_'); base="servers/_template"; dest="servers/$$name"; \
		desc="$(DESCRIPTION)"; if [ -z "$$desc" ]; then desc="Servidor MCP em Python baseado no template."; fi; \
		author="$(AUTHOR)"; \
		if [ ! -d "$$base" ]; then echo "Template $$base não encontrado"; exit 1; fi; \
		if [ -e "$$dest" ]; then echo "Diretório $$dest já existe"; exit 1; fi; \
		cp -R "$$base" "$$dest"; \
		mv "$$dest/src/echo_server" "$$dest/src/$$pkg"; \
		sed -i "s/name = \"mcp-echo-server\"/name = \"mcp-$$name-server\"/" "$$dest/pyproject.toml"; \
		sed -i "s/mcp-echo-server/mcp-$$name-server/" "$$dest/pyproject.toml"; \
		sed -i "s/echo_server/$$pkg/g" "$$dest/pyproject.toml"; \
		sed -i "s/__DESCRIPTION__/$$desc/" "$$dest/pyproject.toml"; \
		if [ -n "$$author" ]; then \
			sed -i "s/__AUTHOR__/$$author/" "$$dest/pyproject.toml"; \
		else \
			sed -i "/authors = \[\{ name = \"__AUTHOR__\" \}\]/d" "$$dest/pyproject.toml"; \
		fi; \
		sed -i "s/from echo_server.main/from $$pkg.main/" "$$dest/tests/test_tools.py"; \
		sed -i "s/echo_server/$$pkg/g" "$$dest/tests/test_tools.py"; \
		sed -i "s/\"mcp-echo-python\"/\"mcp-$$name\"/" "$$dest/src/$$pkg/main.py"; \
		cat > "$$dest/README.md" << EOF\n# Servidor MCP: $$name\n\n$$desc\n\n## Instalação e execução\n```bash\ncd servers/$$name\npip install -e .\npython -m $$pkg.main\n# ou via entry point\nmcp-$$name-server\n```\n\n## Ferramentas\n- echo: retorna o texto recebido\n- time_now: hora atual ISO-8601 (UTC)\n\n## Configuração (Codex)\nEdite ~/.codex/config.toml ou use:\n```bash\nmake codex-config NAME=$$name\n```\nEOF; \
		echo "Servidor criado em $$dest (pacote: $$pkg)."
