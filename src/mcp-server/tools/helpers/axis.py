def axis_opts_to_string(axis_opts: dict, is_cat: bool) -> str:
    """
    Convert axis options dict to string for query parameters.

    Args:
        axis_opts: Dict containing axis options like min_value, max_value, bin_count, scale.
        is_cat: Boolean indicating if the axis is categorical.
    Returns:
        String representation of axis options for query parameters.
    """
    if is_cat and axis_opts.get("bin_count") is not None:
        return (
            f"[{axis_opts['bin_count']}]"
        )
    # Include all values in order: min, max, bin_count, scale (empty string for None)
    return ";".join(
        str(axis_opts.get(key)) if axis_opts.get(key) is not None else ""
        for key in ["min_value", "max_value", "bin_count", "scale"]
    )
