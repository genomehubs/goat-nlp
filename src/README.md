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
- which species with chromosomal or better assemblies have over 10Mb contiguity? - not gemini
  - what about for scaffold n50?
- how many bat families are targeted by the vgp? - not gemini
- which attributes support ordered keyword searches? - not gemini
- how many cat species are missing genome size data?
- which species are on the DTOL target list?
- how many species have a tolid prefix beginning ilLys?
- how many have tolid prefixes ending cori?
- what are the bioprojects for bats?
  - can you get me a list of all the bioprojects?
- what is the lineage for the banded snail?
- how many assemblies are there for species in the cat and dog families?
- show me a table of contig and scaffold n50 for all cat assemblies, sorted by contig n50
- can you give me a table of genome size and chromosome count for the nematode groups shown in [this tree](https://media.springernature.com/lw1200/springer-static/image/art%3A10.1186%2Fs12862-019-1444-x/MediaObjects/12862_2019_1444_Fig4_HTML.png)
- give me a table of current sequencing status for species on both the CANBP and DTOL lists
- what is the protected status of meles meles
- which species of insect have protected status
  - can you give me a table of the conservation statuses

report based queries

- get me a histogram of assembly_span values across all species
  - give me the version with estimated values as well
