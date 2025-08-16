import shutil
import subprocess
import tempfile
from pathlib import Path

import requests
from PySide6.QtCore import (
    QThread,
    Signal,
)

from .fonts import (
    FONT_DOWNLOADS,
    FONT_INSTALL_DIR,
    FONT_PKGS,
)
from .utils import sha256sum


class FontInstallerThread(QThread):
    log_signal = Signal(str)
    finished_signal = Signal(bool)

    def __init__(self, selected_packages):
        super().__init__()
        self.selected_packages = selected_packages

    def run(self):
        try:
            if not shutil.which("7z"):
                self.log_signal.emit(
                    "<span style='color:#c47474;'>Error:</span> '7z' command not found. Please install p7zip."
                )
                self.finished_signal.emit(False)
                return

            if not FONT_INSTALL_DIR.exists():
                self.log_signal.emit(
                    f"Creating install directory:\n {FONT_INSTALL_DIR}"
                )
                FONT_INSTALL_DIR.mkdir(parents=True)

            with tempfile.TemporaryDirectory() as tmpdir:
                self.log_signal.emit(f"Using temporary directory {tmpdir}")
                failed_hash_checks = []
                for pkg in self.selected_packages:
                    url = FONT_DOWNLOADS[pkg]
                    pkg_path = Path(tmpdir) / pkg
                    pkg_extract_dir = Path(tmpdir) / f"extract_{pkg}"
                    pkg_extract_dir.mkdir()

                    self.log_signal.emit(f"Downloading {pkg}...")
                    if not self.download_file(url, pkg_path):
                        self.log_signal.emit(
                            f"<span style='color:#c47474;'>Error:</span> Failed to download {pkg}, skipping."
                        )
                        continue

                    expected_hash = FONT_PKGS[pkg]["hash"]
                    if expected_hash:
                        actual_hash = sha256sum(pkg_path)
                        if actual_hash != expected_hash:
                            self.log_signal.emit(
                                f"<span style='color:#c47474;'>Error:</span> Checksum verification failed for {pkg}"
                            )
                            failed_hash_checks.append(FONT_PKGS[pkg]["name"])
                            continue

                    self.log_signal.emit(f"Extracting fonts from {pkg}...")
                    if not self.extract_fonts(pkg_path, pkg_extract_dir):
                        self.log_signal.emit(
                            f"<span style='color:#c47474;'>Error:</span> Extraction failed for {pkg}, skipping."
                        )
                        continue

                    for ttf_file in pkg_extract_dir.rglob(
                        "*.ttf", case_sensitive=False
                    ):
                        shutil.copy(ttf_file, FONT_INSTALL_DIR / ttf_file.name.lower())
                        self.log_signal.emit(f"Installed font: {ttf_file.name}")

            self.log_signal.emit("Updating font cache...")
            fonts_cached = subprocess.run(
                ["fc-cache", "-fv", str(FONT_INSTALL_DIR)],
                capture_output=True,
                text=True,
                check=True,
            )
            try:
                line = next(
                    line
                    for line in fonts_cached.stdout.splitlines()
                    if str(FONT_INSTALL_DIR) in line and ":" in line
                )
                installdir, cached = line.split(":", 1)
                self.log_signal.emit(
                    "<span style='color:#aac474;'>Success:</span> mscorefonts cached:"
                )
                self.log_signal.emit(installdir.strip())
                self.log_signal.emit(cached.strip())
            except StopIteration:
                self.log_signal.emit(
                    "<span style='color:#c47474;'>Error:</span> fc-cache was unable to find mscorefonts."
                )

            if failed_hash_checks:
                self.log_signal.emit(
                    "<span style='color:#c47474;'>Error:</span> These fonts failed checksum verification and were not installed:"
                )
                for pkg in failed_hash_checks:
                    self.log_signal.emit(f" - {pkg}")

            self.finished_signal.emit(len(failed_hash_checks) == 0)

        except Exception as e:
            self.log_signal.emit(f"Error: {e}")
            self.finished_signal.emit(False)

    def download_file(self, url, dest_path):
        try:
            with requests.get(url, stream=True, timeout=10) as r:
                r.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            return True
        except requests.exceptions.HTTPError as e:
            self.log_signal.emit(f"<span style='color:#c47474;'>HTTP Error:</span> {e}")
        except requests.exceptions.ConnectionError as e:
            self.log_signal.emit(
                f"<span style='color:#c47474;'>Error Connecting:</span> {e}"
            )
        except requests.exceptions.Timeout as e:
            self.log_signal.emit(
                f"<span style='color:#c47474;'>Timeout Error:</span> {e}"
            )
        except requests.exceptions.RequestException as e:
            self.log_signal.emit(
                f"<span style='color:#c47474;'>Download error:</span> {e}"
            )
        return False

    def extract_fonts(self, pkg_path, tmpdir):
        try:
            subprocess.run(
                ["7z", "x", str(pkg_path), f"-o{tmpdir}", "-y"],
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            self.log_signal.emit(
                f"<span style='color:#c47474;'>Error:</span> Extraction failed for {pkg_path.name}. 7z returned an error: {e.stderr}"
            )
            return False
        except Exception as e:
            self.log_signal.emit(
                f"<span style='color:#c47474;'>Error:</span> Something went wrong... {e}"
            )
            return False
