import base64


def get_base64(filename: str) -> str:
    """Return the base64 string representing the image with the given filename."""
    if filename:
        with open(f"media/{filename}", "rb") as icon:
            icon_data = icon.read()
            return base64.b64encode(icon_data).decode()
    else:
        return ""
