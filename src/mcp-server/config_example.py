# Constants
DATASTORE_NAME = "GoaT"  # Full name of the database (for prompts)
SITE_NAME = f"{DATASTORE_NAME} MCP Server"  # Used in browser page and prompts
DATASTORE_FULL_NAME = "Genomes on a Tree"  # Full name of the database (for prompts)
DATASTORE_DESCRIPTION = "a searchable datastore of genomic and sequencing project metadata"
DATASTORE_FULL_DESCRIPTION = (
    f"{DATASTORE_NAME} ({DATASTORE_FULL_NAME}): {DATASTORE_DESCRIPTION}"
)
WEB_URL = f"https://{DATASTORE_NAME.lower()}.genomehubs.org"  # Base URL for the web interface
API_BASE = f"https://{DATASTORE_NAME.lower()}.genomehubs.org/api/v2"  # Base URL for API
USER_AGENT = f"{DATASTORE_NAME.lower()}-app/1.0"  # User agent string for API requests
LOGO_FILE = "site_logo.png"  # Logo file path (on filesystem)
MCP_DESCRIPTION = (
    f"The {SITE_NAME} (Model Context Protocol) server is an AI-powered "
    f"interface for querying {DATASTORE_FULL_NAME}."
)
ISSUE_URL = "https://github.com/genomehubs/goat-nlp/issues"  # URL for users to report issues
ISSUE_TEMPLATE_UNHANDLED_ERROR = (
    "Unhandled error in tool '{tool_name}': {error_message}\n\n"
    "Please investigate the error and consider adding handling for this case in the tool implementation."
)

BROWSER_PAGE_CONFIG = {
    # Site branding
    "datastore_name": DATASTORE_NAME,
    "datastore_full_name": DATASTORE_FULL_NAME,
    "datastore_description": DATASTORE_DESCRIPTION,
    "site_name": SITE_NAME,

    # Main description
    "description": MCP_DESCRIPTION,

    # Endpoint description
    "endpoint_description": (
        "This URL is configured for machine-to-machine communication "
        "using the Model Context Protocol (MCP)."
    ),

    # List of tools to display
    "tools": [
        {"name": "process_identifiers", "description": "Extract and validate taxa, assemblies, samples"},
        {"name": "process_attributes", "description": "Validate attribute filters and fields"},
        {"name": "submit_query", "description": f"Execute searches against {DATASTORE_FULL_NAME}"},
        {"name": "check_taxon_exists", "description": "Validate taxonomic names"},
    ],

    # Developer links
    "links": [
        {"name": "GitHub Repository", "url": "https://github.com/genomehubs/goat-nlp"},
        {"name": f"{DATASTORE_NAME} Database", "url": WEB_URL},
        {"name": f"{DATASTORE_NAME} API Documentation", "url": f"{WEB_URL}/api-docs"},
        {"name": "View registered tools", "url": "/debug/tools"},
        {"name": "Report an Issue", "url": ISSUE_URL},
    ],

    # MCP connection info
    "mcp_info": {
        "protocol": "MCP with SSE (Server-Sent Events)",
        "accept_header": "text/event-stream",
    }
}
