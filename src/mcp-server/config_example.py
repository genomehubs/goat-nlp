# Example configuration for customizing the browser page
# Copy this to config.py and customize for your site

BROWSER_PAGE_CONFIG = {
    # Site branding
    "site_name": "GoaT MCP Server",

    # Main description
    "description": (
        "The GoaT MCP (Model Context Protocol) server is an AI-powered "
        "interface for querying Genomes on a Tree."
    ),

    # Endpoint description
    "endpoint_description": (
        "This URL is configured for machine-to-machine communication "
        "using the Model Context Protocol (MCP)."
    ),

    # List of tools to display
    "tools": [
        {"name": "process_identifiers", "description": "Extract and validate taxa, assemblies, samples"},
        {"name": "process_attributes", "description": "Validate attribute filters and fields"},
        {"name": "goat_query", "description": "Execute searches against GoaT"},
        {"name": "check_taxon_exists", "description": "Validate taxonomic names"},
        {"name": "get_example_queries", "description": "Get curated example queries"},
    ],

    # Developer links
    "links": [
        {"name": "GitHub Repository", "url": "https://github.com/genomehubs/goat-nlp"},
        {"name": "GoaT Database", "url": "https://goat.genomehubs.org"},
        {"name": "View registered tools", "url": "/debug/tools"},
    ],

    # MCP connection info
    "mcp_info": {
        "protocol": "MCP with SSE (Server-Sent Events)",
        "accept_header": "text/event-stream",
    }
}

# Logo file path (on filesystem)
LOGO_FILE = "site_logo.png"
