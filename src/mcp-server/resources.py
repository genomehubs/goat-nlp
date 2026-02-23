from .config import DATASTORE_FULL_DESCRIPTION, SITE_NAME


async def get_datastore_description() -> str:
    """Get a description of the datastore."""
    return DATASTORE_FULL_DESCRIPTION


def register_resources(mcp) -> None:
    """Register resources with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register resources with
    """

    mcp.resource(f"resource://{SITE_NAME}/description")(get_datastore_description)
