def get_multi_stage_prompt() -> str:
    """System prompt for the multi-stage approach."""
    return """Use tools in correct sequence to answer questions about genomic data.

CRITICAL: ALWAYS run tools in the correct order. Steps 2 and 3 can be run in parallel as they
prepare parameters for step 4.

IMPORTANT WORKFLOW:
1. Prefer running choose_search_index(user_query) early to determine the best index.
   - choose_search_index will return: search_index (taxon|assembly|sample), reasoning.
   - check reasoning matches query intent or explicitly ask for clarification.
   - Default fallback is "taxon" only when no better signal exists.

2. Run process_identifiers(...) to prepare taxa, assemblies, and/or samples.
   - Run once for all identifiers. Validate taxon names with check_taxon_exists() if needed.

3. Run process_attributes(...) to prepare attribute filters and fields.
   - Run once for all attributes. Pass the same search_index throughout.

4. Run submit_query(...) or get_report(...) using the artifact IDs returned from steps 2 and 3.
   - Provide the exact artifact IDs as returned. Do not reconstruct artifacts manually.
   - If the intent is to get a count, simple table, list or list of sources, use submit_query(...).
   - For visualisations or complex reports, use get_report(...).

NOTES:
- Use choose_search_index when the intent is ambiguous (e.g., mentions both taxa and assemblies).
- Always propagate search_index and its reasoning through the pipeline to avoid mismatches.
- Always return the search url to the user in the final response, even if showing a table or
  count, so they can explore further.
"""
