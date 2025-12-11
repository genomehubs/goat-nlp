# Tools package for GoaT MCP server

def register_all_tools(mcp):
    """Register all tools with the given MCP server instance."""
    from . import (  # search,; simple_search,; record,; report,
        attributes,
        process_attributes,
        process_identifiers,
        query_parser,
        utilities,
    )

    attributes.register_tools(mcp)
    process_attributes.register_tools(mcp)
    process_identifiers.register_tools(mcp)
    query_parser.register_tools(mcp)
    # record.register_tools(mcp)
    # report.register_tools(mcp)
    # search.register_tools(mcp)
    # simple_search.register_tools(mcp)
    utilities.register_tools(mcp)
