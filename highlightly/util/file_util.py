import base64
import logging
import shutil

import requests


def save_base64_image(filepath: str, base64_img: str) -> str:
    """Saves the given base64 image to the given filepath."""
    # Find file extension and strip out some of the string.
    base64_img = base64_img.replace("data:image/png;base64,", "")

    # Save the file.
    with open(filepath, "wb+") as f:
        f.write(base64.b64decode(base64_img))


def get_base64(filepath: str) -> str:
    """Return the base64 string representing the image with the given filepath."""
    if filepath:
        with open(filepath, "rb") as icon:
            icon_data = icon.read()
            return base64.b64encode(icon_data).decode()
    else:
        return ""


def download_file_from_url(url: str, filepath: str) -> None:
    """Download the file in the given url to the given filepath."""
    with requests.get(url, stream=True) as response:
        with open(filepath, "wb") as file:
            shutil.copyfileobj(response.raw, file)
            logging.info(f"Downloaded file from {url} to {filepath}.")
