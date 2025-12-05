# Record Intent Handling

## Overview

The `record` intent is used to fetch detailed information about a single record from any of the three GoaT indices.

## Intent Patterns

### Taxon Records

Fetch detailed information about a specific taxonomic unit.

**Query:** "Tell me about Canis familiaris (domestic dog)"

**parse_user_query call:**

```python
parse_user_query(
    user_query="Tell me about Canis familiaris (domestic dog)",
    record_id="Canis familiaris",  # Scientific name
    # OR
    record_id="9615",  # NCBI taxon ID if known
    intent="record"
)
```

**Backend Processing:**

- If `record_id` is a scientific name → look up taxon ID in GoaT
- If `record_id` is already a taxon ID (e.g., "9615" - NCBI ID) → use directly
- Call `get_record` with `search_index="taxon"` and `record_id=<taxon_id>`

### Assembly Records

Fetch details about a specific genome assembly.

**Query:** "Get details on the Canis familiaris reference assembly GCF_000002305.6"

**parse_user_query call:**

```python
parse_user_query(
    user_query="Get details on the Canis familiaris reference assembly GCF_000002305.6",
    record_id="GCF_000002305.6",  # Assembly accession
    intent="record"
)
```

**Backend Processing:**

- `search_index` is inferred as "assembly" (from pattern in user_query or assembly ID format)
- Call `get_record` with `search_index="assembly"` and `record_id="GCF_000002305.6"`

### Sample Records

Fetch details about a specific sequencing sample.

**Query:** "Tell me about sample SRR1234567"

**parse_user_query call:**

```python
parse_user_query(
    user_query="Tell me about sample SRR1234567",
    record_id="SRR1234567",  # Sample accession
    intent="record"
)
```

**Backend Processing:**

- `search_index` is inferred as "sample"
- Call `get_record` with `search_index="sample"` and `record_id="SRR1234567"`

## Key Differences from Table Intent

| Aspect              | Record                       | Table                              |
| ------------------- | ---------------------------- | ---------------------------------- |
| **IDs**             | Single ID                    | Multiple IDs or filtered set       |
| **Result**          | All details for ONE record   | Multiple rows with selected fields |
| **Use Case**        | "Tell me everything about X" | "Show me which species have Y"     |
| **Taxon Parameter** | Specific ID or name          | Optional scope (can be None)       |
| **Attributes**      | Usually empty                | May contain filters                |

## ID Format Recognition

The backend should infer ID type from format:

- **Taxon ID:** Numeric NCBI ID (e.g., "9615") or scientific name
- **Assembly ID:** Starts with "GCF*", "GCA*", "ASM", etc.
- **Sample ID:** Starts with "SRR", "ERR", "DRR", etc. (SRA patterns)

If unsure, `choose_search_index` on the full query string helps determine the type.

## Backend Implementation Notes

1. **Taxon ID Resolution**

   - If user provides scientific name → use `check_taxon_exists` to resolve to taxon ID
   - If user provides taxon ID → use directly

2. **Record Retrieval**

   - Call `get_record(record_id=taxon, search_index=search_index, attributes=...)`
   - `attributes` parameter for selecting specific fields to include

3. **Single Record Validation**
   - Ensure exactly one record matches the query
   - If intent is "record" but attributes would match multiple records → convert to table intent
   - Return error if no records found

## Examples from GoaT

### Taxon Record

```
GET /api/v2/record?result=taxon&recordId=9615&taxonomy=ncbi
```

### Assembly Record

```
GET /api/v2/record?result=assembly&recordId=GCF_000002305.6&taxonomy=ncbi
```

### Sample Record

```
GET /api/v2/record?result=sample&recordId=SRR1234567&taxonomy=ncbi
```
