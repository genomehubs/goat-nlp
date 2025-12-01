# Source code directory

Install uv to `$HOME/.local/bin`

```
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

Setup directory for querying GoaT MCP server

```
cd src

# Create virtual environment and activate it
uv venv
source .venv/bin/activate

# Install dependencies
uv add fastmcp httpx
```

Run GoaT MCP server

```
uv run python goat.py
```

connect with copilot (uses repository `mcp.json` file)

Try a query:

- how many species are in goat?
- which species are on both the DToL and CANBP long lists?
- which species with chromosomal or better assemblies have over 10Mb contiguity?
- what about for scaffold n50?
- how many bat families are targeted by the vgp?
- which attributes support ordered keyword searches?
- how many cat species are missing genome size data?
- which species are on the DTOL target list?
- how many species have a tolid prefix beginning ilLys?
- how many have tolid prefixes ending cori?
