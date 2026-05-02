import shutil
import subprocess
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .fonts import (
    FONT_PKGS,
    FONT_INSTALL_DIR,
)
from .installer import FontInstallerThread


class EULADialog(QDialog):
    def __init__(self, eula_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Microsoft Core Fonts and Aptos EULA")
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(eula_text)
        layout.addWidget(text_edit)

        row1_btns = QHBoxLayout()
        accept_btn = QPushButton("Accept")
        decline_btn = QPushButton("Decline")
        row1_btns.addWidget(accept_btn)
        row1_btns.addWidget(decline_btn)
        layout.addLayout(row1_btns)

        accept_btn.clicked.connect(self.accept)
        decline_btn.clicked.connect(self.reject)


class MSCoreFontsApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("fonts-installer")
        self.resize(500, 680)

        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)

        menu_bar = self.menuBar()

        help_menu = menu_bar.addMenu("Help")
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about_dialog)

        label = QLabel("Select fonts to download and install:")
        self.main_layout.addWidget(label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        cb_container = QWidget()
        self.cb_layout = QVBoxLayout(cb_container)
        self.checkboxes = {}

        current_group = None
        for filename, info in FONT_PKGS.items():
            group = info.get("group")
            if group != current_group:
                current_group = group
                if group == "corefonts":
                    self._add_section_header("Microsoft Core Fonts")
                elif group == "aptos":
                    self.cb_layout.addSpacing(8)
                    self._add_section_header("Microsoft Aptos Fonts")

            cb = QCheckBox(info["name"])
            cb.setChecked(False)
            self.cb_layout.addWidget(cb)
            self.checkboxes[filename] = cb

        scroll_area.setWidget(cb_container)
        self.main_layout.addWidget(scroll_area)

        row1_btns = QHBoxLayout()

        select_toggle_btn = QPushButton("Select/Deselect all")
        select_toggle_btn.clicked.connect(self.toggle_all_checkboxes)
        row1_btns.addWidget(select_toggle_btn)

        self.download_btn = QPushButton("Install")
        self.download_btn.clicked.connect(self.start_install)
        row1_btns.addWidget(self.download_btn)

        row2_btns = QHBoxLayout()

        remove_all_btn = QPushButton("Remove all fonts")
        remove_all_btn.clicked.connect(self.remove_all_fonts)
        row2_btns.addWidget(remove_all_btn)

        self.main_layout.addLayout(row1_btns)
        self.main_layout.addLayout(row2_btns)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.main_layout.addWidget(self.log)

        self.installer_thread = None

    def _add_section_header(self, text):
        label = QLabel(text)
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        self.cb_layout.addWidget(label)

    def show_about_dialog(self):
        QMessageBox.information(
            self,
            "About",
            (
                f"""
                <b>fonts-installer</b><br />
                Version: {__version__}<br />
                Author: Troy Harvey<br />
                License: Apache-2.0<br />
                Source code available on <a href="https://github.com/HarveyDevel/fonts-installer">GitHub</a><br /><br />
                The icon for fonts-installer is taken from <a href="https://develop.kde.org/frameworks/breeze-icons/">breeze-icons.</a><br />
                <a href="https://api.kde.org/frameworks/breeze-icons/html/index.html">Breeze icons</a> copyright KDE and licenced under the GNU LGPL version 3 or later.<br /><br />
                Microsoft Core Fonts:<br />
                Fonts are subject to <a href="https://corefonts.sourceforge.net/eula.htm">Microsoft's Core Fonts EULA</a><br />
                and are downloaded from <a href="https://corefonts.sourceforge.net/">corefonts SourceForge</a><br /><br />
                Microsoft Aptos Fonts:<br />
                Fonts are downloaded directly from Microsoft and are subject to
                <a href="https://download.microsoft.com/download/8/6/0/860a94fa-7feb-44ef-ac79-c072d9113d69/Microsoft%20Aptos%20Fonts.zip">Microsoft's Aptos EULA</a>
                (Links to zip file)
                """
            ),
        )

    def remove_all_fonts(self):
        if not FONT_INSTALL_DIR.exists():
            QMessageBox.information(
                self,
                f"Alert",
                f"{FONT_INSTALL_DIR} does not exist. No changes were made.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Please confirm:",
            f"{FONT_INSTALL_DIR} will be deleted.\nAre you sure you wish to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.log_message("Deleting...")
                shutil.rmtree(FONT_INSTALL_DIR)
                subprocess.run(
                    ["fc-cache", "-fv", str(FONT_INSTALL_DIR.parent)],
                    check=True,
                )
                self.log_message(
                    "<span style='color:#aac474;'>Success:</span> Folder deleted and font cache updated."
                )
            except Exception as e:
                self.log_message(f"<span style='color:#c47474;'>Error:</span> {e}")

    def toggle_all_checkboxes(self):
        all_checked = all(cb.isChecked() for cb in self.checkboxes.values())
        state = not all_checked
        for cb in self.checkboxes.values():
            cb.setChecked(state)

    def log_message(self, msg):
        self.log.append(msg)

    def start_install(self):
        selected = [name for name, cb in self.checkboxes.items() if cb.isChecked()]
        if not selected:
            QMessageBox.warning(
                self, "No fonts selected", "Please select at least one font to install."
            )
            return

        self.download_btn.setEnabled(False)
        self.log.clear()
        self.log_message(f"Starting installation of {len(selected)} fonts...")

        self.installer_thread = FontInstallerThread(selected)
        self.installer_thread.log_signal.connect(self.log_message)
        self.installer_thread.finished_signal.connect(self.finished)
        self.installer_thread.start()

    def finished(self, success):
        if success:
            self.log_message(
                "<span style='color:#aac474;'>Success:</span> Install complete."
            )
        else:
            self.log_message(
                "<span style='color:#c47474;'>Error:</span> Installation failed."
            )
        self.download_btn.setEnabled(True)
