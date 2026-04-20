from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import (QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QListWidget, QAbstractItemView,
                             QFileDialog, QLineEdit, QGroupBox, QSizePolicy,
                             QFrame, QGridLayout, QProgressBar, QScrollArea,
                             QWidget, QToolButton)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
import PyQt5.QtCore as QtCore


# ─────────────────────────────────────────────────────────────────────────────
# VRM Group widget — one collapsible card per VRM
# ─────────────────────────────────────────────────────────────────────────────
class VRMGroupWidget(QWidget):
    changed = pyqtSignal()          # emitted when anything changes

    def __init__(self, vrm="", plate_hash="", files=None, parent=None):
        super().__init__(parent)
        self.setObjectName("vrmGroup")

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 4)
        outer.setSpacing(0)

        # ── Header bar ──────────────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet("QFrame { background: #f0f4f8; border: 1px solid #d0d8e0; border-radius: 4px; }")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)

        self.lbl_vrm_display = QLabel("<b>New VRM Group</b>")
        header_layout.addWidget(self.lbl_vrm_display)
        header_layout.addStretch()

        self.btn_remove_group = QToolButton()
        self.btn_remove_group.setText("✕")
        self.btn_remove_group.setToolTip("Remove this VRM group")
        self.btn_remove_group.setStyleSheet("QToolButton { border: none; color: #888; font-weight: bold; }")
        header_layout.addWidget(self.btn_remove_group)
        outer.addWidget(header)

        # ── Body ────────────────────────────────────────────────────────────
        self.body = QFrame()
        self.body.setStyleSheet("QFrame { border: 1px solid #d0d8e0; border-top: none; border-bottom-left-radius: 4px; border-bottom-right-radius: 4px; background: #fff; }")
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(10, 8, 10, 8)
        body_layout.setSpacing(6)

        # VRM / hash row
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("Plate / VRM:"))
        self.line_vrm = QLineEdit(vrm)
        self.line_vrm.setPlaceholderText("e.g. ANZ6427")
        self.line_vrm.setMinimumWidth(100)
        id_layout.addWidget(self.line_vrm)
        id_layout.addWidget(QLabel("Hash (optional):"))
        self.line_hash = QLineEdit(plate_hash)
        self.line_hash.setPlaceholderText("Hash value")
        self.line_hash.setMinimumWidth(100)
        id_layout.addWidget(self.line_hash)
        id_layout.addStretch()
        body_layout.addLayout(id_layout)

        # File list buttons
        file_btn_layout = QHBoxLayout()
        self.btn_add_files = QPushButton("Add GPS File(s)…")
        self.btn_remove_file = QPushButton("Remove Selected")
        file_btn_layout.addWidget(self.btn_add_files)
        file_btn_layout.addWidget(self.btn_remove_file)
        file_btn_layout.addStretch()
        body_layout.addLayout(file_btn_layout)

        # File list
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list.setMinimumHeight(70)
        self.file_list.setMaximumHeight(120)
        body_layout.addWidget(self.file_list)

        outer.addWidget(self.body)
        self.setLayout(outer)

        # Populate files
        for f in (files or []):
            self.file_list.addItem(f)

        # Connections
        self.line_vrm.textChanged.connect(self._update_header)
        self.line_vrm.textChanged.connect(self.changed)
        self.line_hash.textChanged.connect(self.changed)
        self.btn_add_files.clicked.connect(self._add_files)
        self.btn_remove_file.clicked.connect(self._remove_files)
        self._update_header()

    def _update_header(self):
        vrm = self.line_vrm.text().strip()
        self.lbl_vrm_display.setText(f"<b>{vrm}</b>" if vrm else "<b>New VRM Group</b>")

    def _add_files(self):
        files, check = QFileDialog.getOpenFileNames(
            self, "Select GPS File(s)", "",
            "All Files (*.*);;Vbox Files (*.vbo);;OxTS Files (*.csv)"
        )
        if not check:
            return
        existing = self.get_files()
        all_files = existing + files
        if any("vbo" in f.lower() for f in all_files) and any("csv" in f.lower() for f in all_files):
            QtWidgets.QMessageBox.warning(self, "Mixed File Types",
                "Please select only Vbox (.vbo) or only OxTS (.csv) files, not both.")
            return
        for f in files:
            if f not in existing:
                self.file_list.addItem(f)
        self.changed.emit()

    def _remove_files(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))
        self.changed.emit()

    def get_files(self):
        return [self.file_list.item(i).text() for i in range(self.file_list.count())]

    def get_data(self):
        return {
            "plate":      self.line_vrm.text().strip(),
            "plate_hash": self.line_hash.text().strip(),
            "gps_files":  self.get_files(),
        }

    def is_valid(self):
        d = self.get_data()
        return bool(d["plate"] or d["plate_hash"]) and len(d["gps_files"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Page_Intro
# ─────────────────────────────────────────────────────────────────────────────
class Page_Intro(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("GPS / OBO Comparison Wizard")
        self.setSubTitle("This wizard will guide you through comparing GPS data against OBO passage records.")

        layout = QVBoxLayout()
        intro = QLabel(
            "<p>You will need the following files before continuing:</p>"
            "<ul>"
            "<li><b>GPS file(s)</b> — Vbox <tt>.vbo</tt> files <i>or</i> OxTS <tt>.csv</tt> files "
            "(do not mix the two types)</li>"
            "<li><b>OBO data file(s)</b> — tab-delimited <tt>.txt</tt> export or "
            "<tt>.xlsx</tt> file containing a <i>Matched</i> sheet</li>"
            "</ul>"
            "<p>You will assign each GPS file to one or more VRM groups. "
            "The same file can appear in multiple groups.</p>"
            "<p>Click <b>Next</b> to begin.</p>"
        )
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.RichText)
        layout.addWidget(intro)
        layout.addStretch()
        self.setLayout(layout)


# ─────────────────────────────────────────────────────────────────────────────
# Page_VRMGroups  (replaces Page_Plate + Page_GPS)
# ─────────────────────────────────────────────────────────────────────────────
class Page_VRMGroups(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("VRM Groups")
        self.setSubTitle(
            "Create one group per VRM. Add the GPS files that contain passages for that vehicle. "
            "The same file can be added to multiple groups."
        )
        self._groups = []           # list of VRMGroupWidget
        self._previous_state = []   # saved state for Restore Previous

        outer = QVBoxLayout()

        # Top button bar
        btn_bar = QHBoxLayout()
        self.btn_add_group = QPushButton("+ Add VRM Group")
        self.btn_restore   = QPushButton("Restore Previous")
        self.btn_restore.setToolTip("Restore the VRM groups from your last comparison")
        self.btn_restore.setEnabled(False)
        btn_bar.addWidget(self.btn_add_group)
        btn_bar.addWidget(self.btn_restore)
        btn_bar.addStretch()
        outer.addLayout(btn_bar)

        # Scrollable group area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.groups_container = QWidget()
        self.groups_layout = QVBoxLayout(self.groups_container)
        self.groups_layout.setContentsMargins(0, 0, 0, 0)
        self.groups_layout.setSpacing(4)
        self.groups_layout.addStretch()
        self.scroll_area.setWidget(self.groups_container)
        outer.addWidget(self.scroll_area)

        self.lbl_hint = QLabel("Click <b>+ Add VRM Group</b> to get started.")
        self.lbl_hint.setTextFormat(Qt.RichText)
        self.lbl_hint.setAlignment(Qt.AlignCenter)
        self.lbl_hint.setStyleSheet("color: #888;")
        outer.addWidget(self.lbl_hint)

        self.setLayout(outer)

        self.btn_add_group.clicked.connect(lambda: self._add_group())
        self.btn_restore.clicked.connect(self._restore_previous)

    def initializePage(self):
        # Clear existing groups (fresh start)
        for grp in self._groups:
            grp.setParent(None)
        self._groups.clear()
        self._update_hint()
        self.completeChanged.emit()

    def _add_group(self, vrm="", plate_hash="", files=None):
        grp = VRMGroupWidget(vrm, plate_hash, files, self)
        grp.changed.connect(self.completeChanged)
        grp.btn_remove_group.clicked.connect(lambda: self._remove_group(grp))
        # Insert before the stretch
        idx = self.groups_layout.count() - 1
        self.groups_layout.insertWidget(idx, grp)
        self._groups.append(grp)
        self._update_hint()
        self.completeChanged.emit()

    def _remove_group(self, grp):
        self.groups_layout.removeWidget(grp)
        grp.setParent(None)
        self._groups.remove(grp)
        self._update_hint()
        self.completeChanged.emit()

    def _update_hint(self):
        self.lbl_hint.setVisible(len(self._groups) == 0)

    def _restore_previous(self):
        # Clear current
        for grp in self._groups:
            grp.setParent(None)
        self._groups.clear()
        # Repopulate from saved state
        for item in self._previous_state:
            self._add_group(item["plate"], item["plate_hash"], item["gps_files"])
        self.completeChanged.emit()

    def set_previous_state(self, state):
        """Called by main window to inject saved VRM groups from last run."""
        self._previous_state = state
        self.btn_restore.setEnabled(bool(self._previous_state))

    def get_vrm_groups(self):
        """Returns list of {plate, plate_hash, gps_files} dicts."""
        return [g.get_data() for g in self._groups]

    def isComplete(self):
        return any(g.is_valid() for g in self._groups)

    def validatePage(self):
        invalid = [g for g in self._groups if not g.is_valid()]
        if invalid:
            QtWidgets.QMessageBox.warning(
                self, "Incomplete Groups",
                "Each VRM group must have a Plate or Hash, and at least one GPS file.\n"
                "Please complete or remove any incomplete groups."
            )
            return False
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Page_OBO
# ─────────────────────────────────────────────────────────────────────────────
class Page_OBO(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Select OBO Data File(s)")
        self.setSubTitle("Select the OBO passage data files to compare against the GPS recordings.")

        layout = QVBoxLayout()
        info = QLabel(
            "<p>Select one or more OBO data files.</p>"
            "<ul>"
            "<li><b>Tab-delimited export</b> — <tt>.txt</tt> file with a PassageID header row</li>"
            "<li><b>Excel export</b> — <tt>.xlsx</tt> file containing a sheet named <i>Matched</i></li>"
            "</ul>"
            "<p>The file will be searched for passages matching each VRM group you defined.</p>"
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addSpacing(8)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add OBO File(s)…")
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_add.clicked.connect(self.add_files)
        self.btn_remove.clicked.connect(self.remove_selected)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list.setMinimumHeight(120)
        layout.addWidget(self.file_list)
        layout.addStretch()
        self.setLayout(layout)

    def add_files(self):
        files, check = QFileDialog.getOpenFileNames(
            self, "Select OBO Data File(s)", "",
            "OBO Files (*.txt *.xlsx);;Text Files (*.txt);;Excel Files (*.xlsx);;All Files (*.*)"
        )
        if not check:
            return
        existing = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        for f in files:
            if f not in existing:
                self.file_list.addItem(f)
        self.completeChanged.emit()

    def remove_selected(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))
        self.completeChanged.emit()

    def get_files(self):
        return [self.file_list.item(i).text() for i in range(self.file_list.count())]

    def isComplete(self):
        return self.file_list.count() > 0

    def validatePage(self):
        if self.file_list.count() == 0:
            QtWidgets.QMessageBox.warning(self, "No Files", "Please add at least one OBO data file.")
            return False
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Page_PreRun
# ─────────────────────────────────────────────────────────────────────────────
class Page_PreRun(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Ready to Compare")
        self.setSubTitle("Review your selections below then click Next to start the comparison.")

        outer = QVBoxLayout()

        # Scrollable area for everything
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setSpacing(8)
        self.scroll.setWidget(self.content)
        outer.addWidget(self.scroll)
        self.setLayout(outer)

    def initializePage(self):
        # Clear
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        wizard = self.wizard()
        vrm_groups = wizard.page(wizard.VRM_PAGE).get_vrm_groups()

        # VRM Groups section
        vrm_header = QLabel("<b>VRM Groups</b>")
        vrm_header.setTextFormat(Qt.RichText)
        self.content_layout.addWidget(vrm_header)

        for grp in vrm_groups:
            plate  = grp["plate"] or "(no plate)"
            p_hash = grp["plate_hash"]
            files  = grp["gps_files"]

            # Group box per VRM
            box = QGroupBox(f"{plate}" + (f"  |  Hash: {p_hash}" if p_hash else ""))
            box_layout = QVBoxLayout(box)
            box_layout.setSpacing(2)
            box_layout.setContentsMargins(8, 4, 8, 6)

            for f in files:
                import os
                lbl = QLabel(f"• {os.path.basename(f)}")
                lbl.setStyleSheet("color: #444; font-size: 8pt;")
                lbl.setToolTip(f)  # full path on hover
                box_layout.addWidget(lbl)

            self.content_layout.addWidget(box)

        # OBO Files section
        obo_header = QLabel("<b>OBO Files</b>")
        obo_header.setTextFormat(Qt.RichText)
        self.content_layout.addWidget(obo_header)

        obo_box = QGroupBox()
        obo_box_layout = QVBoxLayout(obo_box)
        obo_box_layout.setSpacing(2)
        obo_box_layout.setContentsMargins(8, 4, 8, 6)

        obo_files = wizard.page(wizard.OBO_PAGE).get_files()
        for f in obo_files:
            import os
            lbl = QLabel(f"• {os.path.basename(f)}")
            lbl.setStyleSheet("color: #444; font-size: 8pt;")
            lbl.setToolTip(f)
            obo_box_layout.addWidget(lbl)

        self.content_layout.addWidget(obo_box)
        self.content_layout.addStretch()

    def validatePage(self):
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Page_Progress
# ─────────────────────────────────────────────────────────────────────────────
class Page_Progress(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Running Comparison")
        self.setSubTitle("Please wait while the GPS and OBO data are being compared.")
        self._complete = False

        layout = QVBoxLayout()
        self.lbl_status = QLabel("Starting...")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        layout.addStretch()
        layout.addWidget(self.lbl_status)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress_bar)
        layout.addStretch()
        self.setLayout(layout)
        self.setButtonText(QWizard.NextButton, "Next")

    def initializePage(self):
        self._complete = False
        self.completeChanged.emit()
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Starting...")
        self.wizard().button(QWizard.BackButton).setVisible(False)
        self.wizard().button(QWizard.NextButton).setVisible(False)
        self.wizard().button(QWizard.CancelButton).setVisible(False)
        QtCore.QTimer.singleShot(50, self.wizard().comparisonRequested.emit)

    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.lbl_status.setText(message)

    def mark_complete(self):
        self._complete = True
        self.wizard().button(QWizard.NextButton).setVisible(True)
        self.completeChanged.emit()
        QTimer.singleShot(200, self.wizard().next)

    def mark_failed(self, message):
        self.lbl_status.setText(f"<span style='color:red;'>{message}</span>")
        self.lbl_status.setTextFormat(Qt.RichText)
        self.wizard().button(QWizard.BackButton).setVisible(True)
        self.wizard().button(QWizard.CancelButton).setVisible(True)

    def isComplete(self):
        return self._complete


# ─────────────────────────────────────────────────────────────────────────────
# Page_Results
# ─────────────────────────────────────────────────────────────────────────────
class Page_Results(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Comparison Complete")
        self.setSubTitle("The GPS and OBO data have been compared. Results are shown below.")

        layout = QVBoxLayout()
        self.results_group = QGroupBox("Results")
        self.results_layout = QVBoxLayout()
        self.results_group.setLayout(self.results_layout)
        layout.addWidget(self.results_group)

        self.rules_group = QGroupBox("Validation Rules Applied")
        self.rules_layout = QVBoxLayout()
        self.rules_group.setLayout(self.rules_layout)
        layout.addWidget(self.rules_group)

        self.lbl_note = QLabel("The comparison table in the main window has been updated.")
        self.lbl_note.setAlignment(Qt.AlignCenter)
        self.lbl_note.setStyleSheet("color: #555; margin-top: 8px;")
        layout.addWidget(self.lbl_note)
        layout.addStretch()
        self.setLayout(layout)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def show_results(self, total, passed, failed, config=None, validation_enabled=True):
        self._clear_layout(self.results_layout)
        self._clear_layout(self.rules_layout)

        if not validation_enabled:
            lbl = QLabel("Validation is disabled.\nResults have been loaded into the main table.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #555; font-size: 10pt;")
            passages_lbl = QLabel(f"Total passages found: {total}")
            passages_lbl.setAlignment(Qt.AlignCenter)
            passages_lbl.setStyleSheet("font-size: 10pt;")
            self.results_layout.addWidget(lbl)
            self.results_layout.addWidget(passages_lbl)
            return

        grid = QGridLayout()

        def stat_label(text, colour=None):
            lbl = QLabel(text)
            f = lbl.font()
            f.setPointSize(13)
            f.setBold(True)
            lbl.setFont(f)
            if colour:
                lbl.setStyleSheet(f"color: {colour};")
            lbl.setAlignment(Qt.AlignCenter)
            return lbl

        grid.addWidget(stat_label("Total Passages"),        0, 0)
        grid.addWidget(stat_label("Passed", "#2e7d32"),     0, 1)
        grid.addWidget(stat_label("Failed", "#c62828"),     0, 2)
        grid.addWidget(stat_label(str(total)),              1, 0)
        grid.addWidget(stat_label(str(passed), "#2e7d32"),  1, 1)
        grid.addWidget(stat_label(str(failed), "#c62828"),  1, 2)

        pct = int(passed / total * 100) if total > 0 else 0
        summary = QLabel(f"<b>{pct}%</b> of passages passed validation.")
        summary.setAlignment(Qt.AlignCenter)
        summary.setTextFormat(Qt.RichText)

        self.results_layout.addLayout(grid)
        self.results_layout.addWidget(summary)

        if config:
            cfg = config.get("AverageSpeed", {})
            pct_only      = cfg.get("pct_only", "false").lower() == "true"
            bp            = float(cfg.get("speed_breakpoint", 62))
            low_pos       = float(cfg.get("threshold_low_pos", 3))
            low_neg       = float(cfg.get("threshold_low_neg", 3))
            high_pos      = float(cfg.get("threshold_high_pos", 3))
            high_neg      = float(cfg.get("threshold_high_neg", 3))
            min_sats      = int(float(cfg.get("min_sats", 4)))

            if pct_only:
                rule_text = (
                    f"<b>Percentage Only mode</b> — all speeds judged by % difference:<br>"
                    f"&nbsp;&nbsp;Pass if GPS speed is within <b>+{high_pos}% / \u2212{high_neg}%</b> of OBO speed"
                )
            else:
                rule_text = (
                    f"<b>Speed \u2264 {bp} mph</b> — Pass if GPS speed is within "
                    f"<b>+{low_pos} / \u2212{low_neg} mph</b> of OBO speed<br>"
                    f"<b>Speed &gt; {bp} mph</b> — Pass if GPS speed is within "
                    f"<b>+{high_pos}% / \u2212{high_neg}%</b> of OBO speed"
                )

            rule_lbl = QLabel(rule_text)
            rule_lbl.setTextFormat(Qt.RichText)
            rule_lbl.setWordWrap(True)
            self.rules_layout.addWidget(rule_lbl)
            sats_lbl = QLabel(f"Minimum satellites required per GPS point: <b>{min_sats}</b>")
            sats_lbl.setTextFormat(Qt.RichText)
            self.rules_layout.addWidget(sats_lbl)
        else:
            self.rules_group.setVisible(False)


# ─────────────────────────────────────────────────────────────────────────────
# ValidationWizard
# ─────────────────────────────────────────────────────────────────────────────
class ValidationWizard(QWizard):
    INTRO_PAGE    = 0
    VRM_PAGE      = 1
    OBO_PAGE      = 2
    PRERUN_PAGE   = 3
    PROGRESS_PAGE = 4
    RESULTS_PAGE  = 5

    comparisonRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GPS / OBO Comparison Wizard")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumSize(700, 540)
        self.setOption(QWizard.NoBackButtonOnLastPage, True)
        self.setOption(QWizard.NoCancelButtonOnLastPage, True)

        self.setPage(self.INTRO_PAGE,    Page_Intro(self))
        self.setPage(self.VRM_PAGE,      Page_VRMGroups(self))
        self.setPage(self.OBO_PAGE,      Page_OBO(self))
        self.setPage(self.PRERUN_PAGE,   Page_PreRun(self))
        self.setPage(self.PROGRESS_PAGE, Page_Progress(self))
        self.setPage(self.RESULTS_PAGE,  Page_Results(self))

        self.setStartId(self.INTRO_PAGE)

    def get_vrm_groups(self):
        return self.page(self.VRM_PAGE).get_vrm_groups()

    def get_obo_files(self):
        return self.page(self.OBO_PAGE).get_files()



    def update_progress(self, value, message):
        self.page(self.PROGRESS_PAGE).update_progress(value, message)

    def mark_complete(self):
        self.page(self.PROGRESS_PAGE).mark_complete()

    def mark_failed(self, message):
        self.page(self.PROGRESS_PAGE).mark_failed(message)

    def show_results(self, total, passed, failed, config=None, validation_enabled=True):
        self.page(self.RESULTS_PAGE).show_results(total, passed, failed, config, validation_enabled)