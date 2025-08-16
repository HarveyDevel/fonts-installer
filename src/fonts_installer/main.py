import sys
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QMessageBox,
)
from .gui import (
    EULADialog,
    MSCoreFontsApp,
)
from .utils import load_eula


def main():
    app = QApplication(sys.argv)

    try:
        eula = load_eula()
    except FileNotFoundError:
        QMessageBox.critical(None, "Error: File not found", "EULA was not found.")
        sys.exit(1)
    except PermissionError:
        QMessageBox.critical(
            None, "Error: Invalid permissions", "Permission denied trying to load EULA."
        )
        sys.exit(1)
    except Exception as e:
        QMessageBox.critical(None, "Unknown error", f"Error loading EULA: {e}")
        sys.exit(1)

    eula_dialog = EULADialog(eula)
    if eula_dialog.exec() != QDialog.Accepted:
        sys.exit(0)

    window = MSCoreFontsApp()
    window.show()
    sys.exit(app.exec())
