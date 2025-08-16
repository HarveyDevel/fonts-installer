import hashlib
from importlib.resources import files


def load_eula():
    with files("fonts_installer").joinpath("EULA").open("r", encoding="utf-8") as f:
        return f.read()


def sha256sum(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
