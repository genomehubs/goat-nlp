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
  - how many bat species have bioprojects beginning prjeb4?
- what is the lineage for the banded snail?
- how many assemblies are there for species in the cat and dog families? - not gpt4.1
- show me a table of contig and scaffold n50 for all cat assemblies, sorted by contig n50
- can you give me a table of genome size and chromosome count for the nematode groups shown in [this tree](link died)
- give me a table of current sequencing status for species on both the CANBP and DTOL lists
- what is the protected status of meles meles - not quite
- which species of insect have protected status - not quite
  - can you give me a table of the conservation statuses

report based queries - not currently available

- get me a histogram of assembly_span values across all species

  - give me the version with estimated values as well

other test queries

- how many ungulates, spiders and lizards have directly measured genome sizes over 1G and less than 2.5G with a chromosome number over 10, excluding snakes

  - can I have a table of the largest 5 genome sizes in that list
  - can you include a list of projects targeting each species in the table
  - can you filter the table to only include rows where bioproject is present
  - I mean apply that filter to the full query

- give me the first 10 rows of a table of crab species targeted by any project. Include common name and family in the table

  - can you sort the table and give me the top 10 by largest genome size
  - can you restrict that to non-ancestral values for genome size
  - can you expand the search to all crustaceans

- what is the sequencing status for bat species found in the UK

- which whale species are on the dtol list

  - are any of these also on the canbp list?
  - which of these have an assembly?
  - are these direct values?
  - can you give me a table sorted by largest to smallest
  - can you include whether the assembly is contig, scaffolf or chromosome in that table
  - can you also add columns for common name family and haploid chromosome number

- are there any crab genomes?

  - which of these are scaffold or worse
  - what is the status for these species in ongoing projects
  - how many projects can you show me the status in?
  - can you check across all these projects and just show me the ones with those crab species listed
    - give me the full status

- can you include a list of projects targeting each species in the table

  - can you use genome_size_kmer field instead of genome_size
  - can you filter out missing values in the projects columns using goat rather than after the table is returned
  - can you reverse the sort order
  - what about sorting by most chromosomes instead
  - what is the status of these species?
  - do any have busco scores

- have any squirrels been sequenced under a bioproject starting prjeb4
