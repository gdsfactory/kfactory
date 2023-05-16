"""Color Utilities."""


def ensure_six_digit_hex_color(color: str | int) -> str:
    """Convert string or int to a full hex color."""
    if isinstance(color, int):
        color = f"#{color:06x}"

    color = color.replace("0x", "#")

    # Convert shortened format to 6-digit (#0fc -> #00ffcc)
    if color[0] == "#" and len(color) == 4:
        color = "#" + "".join([2 * str(c) for c in color[1:]])
    return color
