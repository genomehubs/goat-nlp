"""URL utilities for GoaT MCP server."""


def update_query_string(search_url: str, parameter: str, value: str) -> str:
    """Update the search URL to include the desired report type."""
    if f"{parameter}=" in search_url:
        base_url, query_params = search_url.split("?", 1)
        params = query_params.split("&")
        updated_params = []
        for param in params:
            if param.startswith(f"{parameter}="):
                updated_params.append(f"{parameter}={value}")
            else:
                updated_params.append(param)
        updated_query = "&".join(updated_params)
        return f"{base_url}?{updated_query}"
    else:
        separator = "&" if "?" in search_url else "?"
        return f"{search_url}{separator}{parameter}={value}"
