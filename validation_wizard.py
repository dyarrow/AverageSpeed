from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import (QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QListWidget, QAbstractItemView,
                             QFileDialog, QLineEdit, QGroupBox, QSizePolicy,
                             QFrame, QGridLayout, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
import PyQt5.QtCore as QtCore
from PyQt5.QtGui import QFont, QColor


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
            "<p>Click <b>Next</b> to begin.</p>"
        )
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.RichText)
        layout.addWidget(intro)
        layout.addStretch()
        self.setLayout(layout)


class Page_Plate(QWizardPage):
    def __init__(self, plate="", plate_hash="", parent=None):
        super().__init__(parent)
        self.setTitle("Vehicle Identification")
        self.setSubTitle("Enter the plate number and/or hash to search for in the OBO data.")

        layout = QVBoxLayout()
        info = QLabel(
            "<p>Enter the <b>Plate Number</b> and/or <b>Plate Hash</b> of the vehicle you want to validate. "
            "At least one must be provided.</p>"
            "<p>The OBO data will be filtered to only include passages matching these values.</p>"
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addSpacing(12)

        form = QGridLayout()
        form.addWidget(QLabel("Plate Number:"), 0, 0)
        self.line_plate = QLineEdit(plate)
        self.line_plate.setPlaceholderText("e.g. ANZ6427")
        form.addWidget(self.line_plate, 0, 1)
        form.addWidget(QLabel("Plate Hash:"), 1, 0)
        self.line_hash = QLineEdit(plate_hash)
        self.line_hash.setPlaceholderText("Hash value (optional if plate entered)")
        form.addWidget(self.line_hash, 1, 1)

        layout.addLayout(form)
        layout.addStretch()
        self.setLayout(layout)

        self.line_plate.textChanged.connect(self.completeChanged)
        self.line_hash.textChanged.connect(self.completeChanged)
        self.registerField("plate", self.line_plate)
        self.registerField("plate_hash", self.line_hash)

    def initializePage(self):
        self.completeChanged.emit()

    def isComplete(self):
        return bool(self.line_plate.text().strip() or self.line_hash.text().strip())

    def validatePage(self):
        if not self.line_plate.text().strip() and not self.line_hash.text().strip():
            QtWidgets.QMessageBox.warning(self, "Missing Details",
                                          "Please enter a plate number or hash before continuing.")
            return False
        return True


class Page_GPS(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Select GPS File(s)")
        self.setSubTitle("Select the Vbox (.vbo) or OxTS (.csv) GPS files recorded during the validation run.")

        layout = QVBoxLayout()
        info = QLabel(
            "<p>Select one or more GPS files. <b>Important:</b> you must select either all Vbox "
            "<tt>.vbo</tt> files <i>or</i> all OxTS <tt>.csv</tt> files — do not mix the two.</p>"
            "<p>Each file represents a GPS recording session. Multiple files can be selected if the "
            "validation run was split across several recordings.</p>"
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addSpacing(8)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add GPS File(s)...")
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

        self.lbl_type = QLabel("")
        self.lbl_type.setStyleSheet("color: #555;")
        layout.addWidget(self.lbl_type)
        layout.addStretch()
        self.setLayout(layout)

    def add_files(self):
        files, check = QFileDialog.getOpenFileNames(
            self, "Select GPS File(s)", "",
            "All Files (*.*);;Vbox Files (*.vbo);;OxTS Files (*.csv)"
        )
        if not check:
            return
        existing = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        all_files = existing + files
        if any("vbo" in f.lower() for f in all_files) and any("csv" in f.lower() for f in all_files):
            QtWidgets.QMessageBox.warning(self, "Mixed File Types",
                "Please select only Vbox (.vbo) or only OxTS (.csv) files, not both.")
            return
        for f in files:
            if f not in existing:
                self.file_list.addItem(f)
        self._update_type_label()
        self.completeChanged.emit()

    def remove_selected(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))
        self._update_type_label()
        self.completeChanged.emit()

    def _update_type_label(self):
        files = self.get_files()
        if not files:
            self.lbl_type.setText("")
        elif any("vbo" in f.lower() for f in files):
            self.lbl_type.setText("✔  Vbox files selected")
        else:
            self.lbl_type.setText("✔  OxTS files selected")

    def get_files(self):
        return [self.file_list.item(i).text() for i in range(self.file_list.count())]

    def isComplete(self):
        return self.file_list.count() > 0

    def validatePage(self):
        if self.file_list.count() == 0:
            QtWidgets.QMessageBox.warning(self, "No Files", "Please add at least one GPS file.")
            return False
        return True


class Page_OBO(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Select OBO Data File(s)")
        self.setSubTitle("Select the OBO passage data files to compare against the GPS recording.")

        layout = QVBoxLayout()
        info = QLabel(
            "<p>Select one or more OBO data files.</p>"
            "<ul>"
            "<li><b>Tab-delimited export</b> — <tt>.txt</tt> file with a PassageID header row</li>"
            "<li><b>Excel export</b> — <tt>.xlsx</tt> file containing a sheet named <i>Matched</i></li>"
            "</ul>"
            "<p>The file must contain passage records for the plate number entered on the previous page.</p>"
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addSpacing(8)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add OBO File(s)...")
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


class Page_PreRun(QWizardPage):
    """Review page shown before the comparison starts. Clicking Next fires the comparison."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Ready to Compare")
        self.setSubTitle("Review your selections below then click Next to start the comparison.")

        layout = QVBoxLayout()

        self.sel_group = QGroupBox("Selected Files")
        self.sel_layout = QGridLayout()
        self.sel_group.setLayout(self.sel_layout)
        layout.addWidget(self.sel_group)
        layout.addStretch()
        self.setLayout(layout)

    def initializePage(self):
        while self.sel_layout.count():
            item = self.sel_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        wizard = self.wizard()
        plate  = wizard.field("plate")
        p_hash = wizard.field("plate_hash")

        row = 0
        self.sel_layout.addWidget(QLabel("<b>Plate:</b>"),  row, 0)
        self.sel_layout.addWidget(QLabel(plate or "—"),     row, 1)
        row += 1
        self.sel_layout.addWidget(QLabel("<b>Hash:</b>"),   row, 0)
        self.sel_layout.addWidget(QLabel(p_hash or "—"),    row, 1)
        row += 1

        gps_files = wizard.page(wizard.GPS_PAGE).get_files()
        obo_files = wizard.page(wizard.OBO_PAGE).get_files()

        self.sel_layout.addWidget(QLabel("<b>GPS Files:</b>"), row, 0, Qt.AlignTop)
        self.sel_layout.addWidget(QLabel("\n".join(gps_files) or "—"), row, 1)
        row += 1
        self.sel_layout.addWidget(QLabel("<b>OBO Files:</b>"), row, 0, Qt.AlignTop)
        self.sel_layout.addWidget(QLabel("\n".join(obo_files) or "—"), row, 1)

    def validatePage(self):
        return True


class Page_Progress(QWizardPage):
    """Shows live progress while the comparison thread runs."""

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

        # Hide Next/Back/Cancel while running
        self.setButtonText(QWizard.NextButton, "Next")

    def initializePage(self):
        self._complete = False
        self.completeChanged.emit()
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Starting...")
        self.wizard().button(QWizard.BackButton).setVisible(False)
        self.wizard().button(QWizard.NextButton).setVisible(False)
        self.wizard().button(QWizard.CancelButton).setVisible(False)
        # Fire comparison now that this page is fully initialised
        QtCore.QTimer.singleShot(50, self.wizard().comparisonRequested.emit)

    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.lbl_status.setText(message)

    def mark_complete(self):
        self._complete = True
        self.wizard().button(QWizard.NextButton).setVisible(True)
        self.completeChanged.emit()
        # Use timer so next() fires after current signal has returned
        QTimer.singleShot(200, self.wizard().next)

    def mark_failed(self, message):
        self.lbl_status.setText(f"<span style='color:red;'>Error: {message}</span>")
        self.lbl_status.setTextFormat(Qt.RichText)
        self.wizard().button(QWizard.BackButton).setVisible(True)
        self.wizard().button(QWizard.CancelButton).setVisible(True)

    def isComplete(self):
        return self._complete


class Page_Results(QWizardPage):
    """Final page showing pass/fail summary."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Comparison Complete")
        self.setSubTitle("The GPS and OBO data have been compared. Results are shown below.")

        layout = QVBoxLayout()

        self.results_group = QGroupBox("Results")
        self.results_layout = QVBoxLayout()
        self.results_group.setLayout(self.results_layout)
        layout.addWidget(self.results_group)

        self.lbl_note = QLabel("The comparison table in the main window has been updated.")
        self.lbl_note.setAlignment(Qt.AlignCenter)
        self.lbl_note.setStyleSheet("color: #555; margin-top: 8px;")
        layout.addWidget(self.lbl_note)

        layout.addStretch()
        self.setLayout(layout)

    def show_results(self, total, passed, failed):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # clear nested layout
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

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

        grid.addWidget(stat_label("Total Passages"),         0, 0)
        grid.addWidget(stat_label("Passed", "#2e7d32"),      0, 1)
        grid.addWidget(stat_label("Failed", "#c62828"),      0, 2)
        grid.addWidget(stat_label(str(total)),               1, 0)
        grid.addWidget(stat_label(str(passed), "#2e7d32"),   1, 1)
        grid.addWidget(stat_label(str(failed), "#c62828"),   1, 2)

        pct = int(passed / total * 100) if total > 0 else 0
        summary = QLabel(f"<b>{pct}%</b> of passages passed validation.")
        summary.setAlignment(Qt.AlignCenter)
        summary.setTextFormat(Qt.RichText)

        self.results_layout.addLayout(grid)
        self.results_layout.addWidget(summary)


class ValidationWizard(QWizard):
    INTRO_PAGE    = 0
    PLATE_PAGE    = 1
    GPS_PAGE      = 2
    OBO_PAGE      = 3
    PRERUN_PAGE   = 4
    PROGRESS_PAGE = 5
    RESULTS_PAGE  = 6

    # Emitted when the user clicks Next on the pre-run page
    comparisonRequested = pyqtSignal()

    def __init__(self, plate="", plate_hash="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("GPS / OBO Comparison Wizard")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumSize(660, 500)
        self.setOption(QWizard.NoBackButtonOnLastPage, True)
        self.setOption(QWizard.NoCancelButtonOnLastPage, True)

        self.setPage(self.INTRO_PAGE,    Page_Intro(self))
        self.setPage(self.PLATE_PAGE,    Page_Plate(plate, plate_hash, self))
        self.setPage(self.GPS_PAGE,      Page_GPS(self))
        self.setPage(self.OBO_PAGE,      Page_OBO(self))
        self.setPage(self.PRERUN_PAGE,   Page_PreRun(self))
        self.setPage(self.PROGRESS_PAGE, Page_Progress(self))
        self.setPage(self.RESULTS_PAGE,  Page_Results(self))

        self.setStartId(self.INTRO_PAGE)

    # --- Accessors ---
    def get_gps_files(self):
        return self.page(self.GPS_PAGE).get_files()

    def get_obo_files(self):
        return self.page(self.OBO_PAGE).get_files()

    def get_plate(self):
        return self.field("plate")

    def get_plate_hash(self):
        return self.field("plate_hash")

    # --- Called by main window to drive progress page ---
    def update_progress(self, value, message):
        self.page(self.PROGRESS_PAGE).update_progress(value, message)

    def mark_complete(self):
        self.page(self.PROGRESS_PAGE).mark_complete()

    def mark_failed(self, message):
        self.page(self.PROGRESS_PAGE).mark_failed(message)

    def show_results(self, total, passed, failed):
        self.page(self.RESULTS_PAGE).show_results(total, passed, failed)