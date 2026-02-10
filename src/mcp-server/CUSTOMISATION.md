# Browser Page Customization Guide

The MCP server includes a user-friendly browser page that can be fully customised for different sites.

## Quick Start

1. **Copy the example configuration:**

   ```bash
   cp config_example.py config.py
   ```

2. **Edit `config.py` to customize your site:**

   ```python
   BROWSER_PAGE_CONFIG = {
       "site_name": "Your Site Name",
       "logo_path": "/site_logo.png",
       "description": "Your site description",
       # ... more options
   }

   LOGO_FILE = "your_logo.png"
   ```

3. **Add your logo file** to the `mcp-server/` directory with the name specified in `LOGO_FILE`

4. **Restart the server** - it will automatically use your custom configuration

## Configuration Options

### `BROWSER_PAGE_CONFIG` Dictionary

- **`site_name`** (str): Display name for your site (appears in title and header)
- **`logo_path`** (str): URL path to serve the logo (keep as `/site_logo.png`)
- **`description`** (str): Main description paragraph
- **`endpoint_description`** (str): Description of the MCP endpoint purpose
- **`tools`** (list): List of tool dictionaries with `name` and `description`
- **`links`** (list): List of link dictionaries with `name` and `url`
- **`mcp_info`** (dict): Protocol and header information for AI agents

### `LOGO_FILE` Variable

The filename of your logo image in the `mcp-server/` directory. Should be a PNG file.

LOGO_FILE = "custom_logo.png"

## Template Variables

The `browser_page.html` template uses Jinja2 syntax. Available variables:

- `{{ site_name }}`
- `{{ logo_path }}`
- `{{ description }}`
- `{{ endpoint_description }}`
- `{% for tool in tools %}` ... `{% endfor %}`
- `{% for link in links %}` ... `{% endfor %}`
- `{{ mcp_info.protocol }}`
- `{{ mcp_info.accept_header }}`

## Customizing Styles

To customize colors, fonts, or layout, edit `browser_page.html` directly. The CSS is embedded in the `<style>` section.

## No Configuration File

If no `config.py` exists, the server uses default GoaT branding and configuration from `goat.py`.

```

```
