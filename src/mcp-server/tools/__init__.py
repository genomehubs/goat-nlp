# Tools package for GoaT MCP server

def register_all_tools(mcp):
    """Register all tools with the given MCP server instance."""
    from . import (
        attributes,
        query_parser,
        record,
        report,
        search,
        simple_search,
        utilities,
    )

    attributes.register_tools(mcp)
    query_parser.register_tools(mcp)
    record.register_tools(mcp)
    report.register_tools(mcp)
    search.register_tools(mcp)
    simple_search.register_tools(mcp)
    utilities.register_tools(mcp)
