# A/B Testing: Parsing vs Simple Search Approach

## Overview

Two different approaches for LLM interaction with GoaT:

1. **Simple Search (Default)** - LLM chooses simple_search or search_goat tools directly
2. **Parse Query (Experimental)** - LLM extracts structured intent, backend processes

## Switching Between Approaches

### MCP Server

Set the `GOAT_PROMPT_STYLE` environment variable:

```bash
# Use default simple_search approach
export GOAT_PROMPT_STYLE=simple
python -m mcp-server

# Use experimental parse_user_query approach
export GOAT_PROMPT_STYLE=parser
python -m mcp-server
```

### Public API

The public API exposes both approaches. LLMs can use either:

- `goat_parse_user_query` (experimental parsing approach)
- `goat_simple_search` (simple approach)
- `goat_search_goat` (advanced approach)

## Key Differences

### Simple Search Approach (Current Default)

**LLM Responsibilities:**

- Choose between simple_search and search_goat
- Map "families" → what_to_count parameter
- Translate common names to scientific names
- Identify specific_attribute names
- Handle missing vs present logic

**Backend Responsibilities:**

- Construct GoaT API URL
- Execute query
- Format results

**Pros:**

- Clear, straightforward tool interface
- Works well for most queries
- Easy to understand

**Cons:**

- LLMs struggle with edge cases:
  - Missing rank extraction
  - long_list vs sequencing_status confusion
  - Handling "missing" data (exclusions)
  - Direct vs ancestral vs estimated modifiers

### Parse Query Approach (Experimental)

**LLM Responsibilities:**

- Extract intent (count/table/histogram/record)
- Extract taxon (if mentioned)
- Extract rank (if mentioned - backend handles if missed)
- Extract attributes with modifiers

**Backend Responsibilities:**

- Infer search_index from user_query (taxon/assembly/sample)
- Handle missing rank extraction from user_query
- Disambiguate long_list vs sequencing_status
- Convert "missing" modifier to exclusions
- Handle "direct" modifier (exclude ancestral/estimated)
- Process aggregate modifiers (min/max/median)
- Construct GoaT API URL
- Execute query
- Format results

**Pros:**

- Separates understanding from implementation
- Backend handles complex edge cases
- More robust to LLM capability differences
- Extensible to new modifiers

**Cons:**

- More complex backend processing required
- Currently incomplete implementation
- Experimental status

## Modifier System

The parse_user_query approach introduces attribute modifiers:

### Data Availability Modifiers

- `"missing"` - Species WITHOUT this attribute

  - Example: `{"name": "genome_size", "modifier": "missing"}`
  - Backend converts to exclusions: `exclude=["Direct", "Ancestral", "Estimated"]`

- `"direct"` - Only directly measured values

  - Example: `{"name": "genome_size", "modifier": "direct"}`
  - Backend excludes: `exclude=["Ancestral", "Estimated"]`

- `"ancestral"` - Include ancestral values

  - Backend includes both direct and ancestral

- `"estimated"` - Include estimated values

### Aggregate Function Modifiers

- `"min"`, `"max"`, `"median"`, `"length"` - Aggregate functions
  - Example: `{"name": "genome_size", "modifier": "max"}`
  - Backend maps to GoaT API aggregate parameters

## Implementation Status

### ✅ Completed

- parse_user_query tool created
- MCP server prompt switching (GOAT_PROMPT_STYLE env var)
- Public API tool definition (goat_parse_user_query)
- Parser-based system prompt
- Modifier parameter structure
- Automatic search_index inference using choose_search_index

### 🚧 In Progress

- Backend processing of modifiers
- Automatic rank extraction from user_query
- long_list vs sequencing_status disambiguation
- Exclusion handling for "missing" modifier

### 📋 To Do

- Complete backend processing implementation
- Add tests comparing both approaches
- Measure accuracy differences
- Performance comparison
- Documentation of modifier extensions

## Testing

To test both approaches:

```bash
# Terminal 1: Run with simple approach
export GOAT_PROMPT_STYLE=simple
python -m mcp-server

# Terminal 2: Run with parser approach
export GOAT_PROMPT_STYLE=parser
python -m mcp-server

# Compare results for the same queries
```

## Extending Modifiers

The modifier system can be extended to support additional GoaT API features:

- `"summary"` - For GoaT summary parameters
- `"binned"` - For histogram binning
- Custom aggregate functions
- Field-specific modifiers

Add new modifiers to the enum in:

- `tools/query_parser.py` (docstring)
- `public-api/app/services/goat_tools.py` (input_schema)
- Backend processing logic

## Recommendation

Start with the **simple search approach** (default) since it's fully implemented and tested.

Use **parse query approach** for:

- Testing LLMs with varying capabilities
- Queries with complex "missing" semantics
- Queries requiring aggregate functions
- Research into separation of concerns
