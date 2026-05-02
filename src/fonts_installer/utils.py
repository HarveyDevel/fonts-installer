import hashlib
from importlib.resources import files


def load_eula():
    with (
        files("fonts_installer")
        .joinpath("Corefonts_EULA")
        .open("r", encoding="utf-8") as f
    ):
        corefonts_eula = f.read()
    with (
        files("fonts_installer").joinpath("Aptos_EULA").open("r", encoding="utf-8") as f
    ):
        aptos_eula = f.read()
    return (
        "All licenses must be accepted to continue using this application and use the fonts\n\n"
        "License 1 of 2 for Microsoft Core Fonts:\n\n"
        + corefonts_eula
        + "\n\nLicense 2 of 2 for Microsoft Aptos Fonts:\n\n"
        + aptos_eula
    )


def sha256sum(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
