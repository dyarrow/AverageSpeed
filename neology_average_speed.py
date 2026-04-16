from PyQt5.QtWidgets import QWidget,QMessageBox
from PyQt5 import uic
import os
import sys
from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import QMessageBox,QSizePolicy
from PyQt5.QtCore import *
from PyQt5.QtGui import * 
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
from datetime import datetime
import time
from PyQt5.QtCore import Qt, QSortFilterProxyModel
from PyQt5.QtWidgets import QFileDialog,QLineEdit, QPushButton, QApplication,QVBoxLayout, QDialog,QAction,QLabel,QTableWidgetItem
from openpyxl import Workbook

import openpyxl
from tablemodel import CustomTableModel,CustomProxyModel
from queue import Queue

import json
import sys

from build_config import resourcesPath
from build_config import applicationPath

from baseline_measurement import SectionData,ProcessSectionData

from averagespeed_config import AverageSpeedConfig
from link_validation import AverageSpeedLinkValidationManualComparison,AverageSpeedLinkValidationSaveKML
from validation_wizard import ValidationWizard



class ExcelSectionData:
    ID="ID"
    ROADID="RoadID"
    MEASUREMENT_NUMBER="MeasurementNumber"
    SECTION_NUMBER="SectionNumber"
    GPS_FILENAME="GPSFileName"
    TIME_STARTED="TimeStarted"
    TIME_ENDED="TimeEnded"

class ProgressDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        progress = index.data(QtCore.Qt.UserRole+1000)
        opt = QtWidgets.QStyleOptionProgressBar()
        opt.rect = option.rect
        opt.minimum = 0
        opt.maximum = 100
        opt.progress = progress
        opt.text = "{}%".format(progress)
        opt.textVisible = True
        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_ProgressBar, opt, painter)



class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, config, config_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(350)
        self.config = config
        self.config_path = config_path

        layout = QtWidgets.QVBoxLayout()

        form = QtWidgets.QFormLayout()

        self.spin_min_sats = QtWidgets.QSpinBox()
        self.spin_min_sats.setRange(0, 20)
        self.spin_min_sats.setValue(int(config["AverageSpeed"]["min_sats"]))
        self.spin_min_sats.setToolTip("Minimum number of GPS satellites required for a point to be included in speed calculations")
        form.addRow("Min Satellites:", self.spin_min_sats)

        self.spin_time_offset = QtWidgets.QDoubleSpinBox()
        self.spin_time_offset.setRange(-24, 24)
        self.spin_time_offset.setDecimals(1)
        self.spin_time_offset.setSingleStep(0.5)
        self.spin_time_offset.setValue(float(config["AverageSpeed"]["time_offset"]))
        self.spin_time_offset.setToolTip("Time offset in hours to apply to GPS timestamps")
        form.addRow("Time Offset (hours):", self.spin_time_offset)

        self.spin_leap_seconds = QtWidgets.QSpinBox()
        self.spin_leap_seconds.setRange(0, 60)
        self.spin_leap_seconds.setValue(int(config["AverageSpeed"]["leap_seconds"]))
        self.spin_leap_seconds.setToolTip("GPS leap seconds to subtract from epoch time (currently 18)")
        form.addRow("Leap Seconds:", self.spin_leap_seconds)

        layout.addLayout(form)
        layout.addSpacing(8)

        # Buttons
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self.save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.setLayout(layout)

    def save(self):
        self.config["AverageSpeed"]["min_sats"]    = str(self.spin_min_sats.value())
        self.config["AverageSpeed"]["time_offset"]  = str(self.spin_time_offset.value())
        self.config["AverageSpeed"]["leap_seconds"] = str(self.spin_leap_seconds.value())
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)
            self.accept()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Save Failed",
                f"Could not save settings:\n{str(e)}")


#Plugin UI Class
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui=uic.loadUi(f"{applicationPath}/ui/neology_average_speed.ui", self)

        try:
            with open(f"{resourcesPath}/neology_average_speed.json") as c:
                self.commissioningConfig = json.load(c)
        except Exception as e:
            print(str(e))
            exit()

        self.tbl_view_section_data=self.findChild(QtWidgets.QTableView,'tbl_view_section_data')
        self.tbl_view_gps_data=self.findChild(QtWidgets.QTableView,'tbl_view_gps_data')
        self.btn_import_section_data=self.findChild(QtWidgets.QPushButton,'btn_import_section_data')
        self.btn_process_vbox_data=self.findChild(QtWidgets.QPushButton,'btn_process_vbox_data')
        self.btn_export_multiple=self.findChild(QtWidgets.QPushButton,'btn_export_multiple')
        self.combo_section_selection=self.findChild(QtWidgets.QComboBox,'combo_section_selection')
        self.combo_section_selection.activated.connect(self.combo_section_selection_changed)
        self.pb_progress=self.findChild(QtWidgets.QProgressBar,'pb_progress')
        self.btn_import_section_data.clicked.connect(self.import_section_data)
        self.btn_export_multiple.clicked.connect(self.export_multiple)
        self.btn_process_vbox_data.clicked.connect(self.import_vbox_data)


        self.tbl_view_section_data_proxy=CustomProxyModel()
        self.tbl_view_section_data_proxy_header = self.tbl_view_section_data.horizontalHeader()

        
        self.tbl_view_gps_data_proxy=CustomProxyModel()
        self.tbl_view_gps_data_proxy_header = self.tbl_view_gps_data.horizontalHeader()

        self.section_data=[]

        self.progress_bar_value = 0
        self.no_threads=30
        self.vbox_processing_threads = {}
        self.vbox_processing_objects = {}
        self.thread_progress = {}
        self.vbox={}
        self.mutex = QMutex()

        self.data=[]

        # Hide Baseline Measurement tab - uncomment to re-enable
        self.tabWidget = self.findChild(QtWidgets.QTabWidget, 'tabWidget')
        self.tabWidget.setTabVisible(0, False)

        #Average Speed Tab
        self.btn_file_check = self.findChild(QtWidgets.QPushButton,'btn_file_check')
        self.btn_file_check.clicked.connect(self.btn_file_checkPressed)
        self.btn_wizard = self.findChild(QtWidgets.QPushButton,'btn_wizard')
        self.btn_wizard.clicked.connect(self.btn_wizardPressed)

        self.btn_save_kml = self.findChild(QtWidgets.QPushButton,'btn_save_kml')
        self.btn_save_kml.clicked.connect(self.btn_save_kmlPressed)

        self.btn_export_validation_data = self.findChild(QtWidgets.QPushButton,'btn_export_validation_data')
        self.btn_export_validation_data.clicked.connect(self.export_validation_data)
        self.btn_export_vbox_cut = self.findChild(QtWidgets.QPushButton,'btn_export_vbox_cut')
        self.btn_export_vbox_cut.clicked.connect(self.export_vbox_cut_data)
        self.tableValidation=self.findChild(QtWidgets.QTableView,'tbl_validation')

        
        self.line_plate = self.findChild(QtWidgets.QLineEdit,'line_plate')
        self.line_hash = self.findChild(QtWidgets.QLineEdit,'line_hash')

        #self.dateValidation.setDateTime(QtCore.QDateTime.currentDateTime())

        self.pbAverageSpeedValidation = self.findChild(QtWidgets.QProgressBar,'pb_link_validation')
    
        self.btn_import_config_file = self.findChild(QtWidgets.QPushButton,'btn_import_config_file')
        self.btn_import_config_file.clicked.connect(self.btnImportConfigFilePressed)
        self.btn_import_config_file.setVisible(False)
        self.btn_settings = self.findChild(QtWidgets.QPushButton, 'btn_settings')
        self.btn_settings.clicked.connect(self.btnSettingsPressed)

        self.chk_validation_enabled  = self.findChild(QtWidgets.QCheckBox, 'chk_validation_enabled')
        self.chk_pct_only            = self.findChild(QtWidgets.QCheckBox, 'chk_pct_only')
        self.spin_speed_breakpoint   = self.findChild(QtWidgets.QDoubleSpinBox, 'spin_speed_breakpoint')
        self.spin_threshold_low_pos  = self.findChild(QtWidgets.QDoubleSpinBox, 'spin_threshold_low_pos')
        self.spin_threshold_low_neg  = self.findChild(QtWidgets.QDoubleSpinBox, 'spin_threshold_low_neg')
        self.spin_threshold_high_pos = self.findChild(QtWidgets.QDoubleSpinBox, 'spin_threshold_high_pos')
        self.spin_threshold_high_neg = self.findChild(QtWidgets.QDoubleSpinBox, 'spin_threshold_high_neg')
        self.chk_validation_enabled.stateChanged.connect(self.onValidationEnabledChanged)
        self.chk_pct_only.stateChanged.connect(self.onPctOnlyChanged)
        self.spin_speed_breakpoint.valueChanged.connect(self.recolourValidationTable)
        self.spin_threshold_low_pos.valueChanged.connect(self.recolourValidationTable)
        self.spin_threshold_low_neg.valueChanged.connect(self.recolourValidationTable)
        self.spin_threshold_high_pos.valueChanged.connect(self.recolourValidationTable)
        self.spin_threshold_high_neg.valueChanged.connect(self.recolourValidationTable)

        self.btn_save_kml.setEnabled(False)
        self.btn_export_validation_data.setEnabled(False)
        self.btn_export_vbox_cut.setEnabled(False)

        #self.validation_headers=['Passage','Date','VRM','Time','From','To','GPS','OBO','% Diff','Points','Errors','Validity']
        #self.validation_headers=['Passage','Date','VRM','Time','From','To','GPS','OBO','% Diff', "FromVbox","ToVbox",'Points','Errors']
        self.validation_headers=['Passage','Pri Entry Time','Sec Entry Time','Entry Time Diff','Pri Exit Time','Sec Exit Time','Exit Time Diff','VRM','From','To','Vbox Average Spd','Pri OBO Spd','Vbox/Pri Speed % Diff',"Vbox / Pri Speed MPH Diff","Sec OBO Speed","% Pri/Sec Spd Diff","FromVboxCutTime","ToVboxCutTime",'GPS Points','# Errors (low satellite)']
        self.gps_data_headers=['Sat #','Epoch','Time','Lat','Long','Speed','Northing','Easting','Altitude']


        #End Average Speed Tab


#region Baseline Measurement 
    def import_section_data(self):
        section_data_filename, check = QFileDialog.getOpenFileName(None,"Select Section Data Spreadsheet File:","","Excel File (*.xlsx);;All Files (*.*)",)
        if not check: return


        try:
            self.section_data=[]

            workbook=openpyxl.load_workbook(section_data_filename)
            sheet = workbook['BaselineVboxTimings']

            list_values = list(sheet.values)
            headers=list(list_values[0])

            #Dynamically get excel column numbers (in case someone changes the format of excel file)
            self.id_col=headers.index(ExcelSectionData.ID)
            self.road_id_col=headers.index(ExcelSectionData.ROADID)
            self.measurement_number_col=headers.index(ExcelSectionData.MEASUREMENT_NUMBER)
            self.section_number_col=headers.index(ExcelSectionData.SECTION_NUMBER)
            self.gps_filename_col=headers.index(ExcelSectionData.GPS_FILENAME)
            self.start_time_col=headers.index(ExcelSectionData.TIME_STARTED)
            self.end_time_col=headers.index(ExcelSectionData.TIME_ENDED)

            self.section_data=[list(elem) for elem in list_values[1:]]

            for row in self.section_data:
                if row is not None:
                    row[self.start_time_col]=row[self.start_time_col].strftime("%d/%m/%Y %H:%M:%S.%f").strip()[:-3]
                    row[self.end_time_col]=row[self.end_time_col].strftime("%d/%m/%Y %H:%M:%S.%f").strip()[:-3]
                    
            self.tbl_view_section_data_model = CustomTableModel(self.section_data,headers)      
            
            self.tbl_view_section_data_proxy.setFilterKeyColumn(-1)
            self.tbl_view_section_data_proxy.setSourceModel(self.tbl_view_section_data_model)
            self.tbl_view_section_data.setModel(self.tbl_view_section_data_proxy)
            self.tbl_view_section_data.setSortingEnabled(True)
            
            self.tbl_view_section_data_proxy_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
            self.tbl_view_section_data_proxy_header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        except Exception as e:
            print(e)
            self.showErrorMessagebox("Section Import Error","Failed to import section data, please check format of excel spreadsheet")

    def import_vbox_data(self):

        self.section_processing_thread=ProcessSectionData(self.section_data,self.id_col,self.gps_filename_col, self.start_time_col, self.end_time_col)
        self.section_processing_thread.section_data_processing_finished.connect(self.on_section_data_processing_finished, QtCore.Qt.QueuedConnection)
        self.section_processing_thread.section_processing_error_occurred.connect(self.on_section_processing_error_occurred, QtCore.Qt.QueuedConnection)
        self.section_processing_thread.update_section_processing_progress.connect(self.update_section_processing_progress, QtCore.Qt.QueuedConnection)
        self.section_processing_thread.start()

        #self.vbox.import_vbox_file("C:\\Users\\dyarrow\\OneDrive - Neology\\Desktop\\WSDOT\\Baseline Measurement\\Trailer speed\\Trailer speed\\SB I-5 all passes.vbo", start_time, end_time)
        #self.vbox.export_to_csv("baseline_tool.csv")

    def update_section_processing_progress(self, progress_dict):
        if "progress" in progress_dict:
            self.pb_progress.setValue(progress_dict["progress"])
            self.pb_progress.setFormat(progress_dict['message'])
            self.pb_progress.setAlignment(QtCore.Qt.AlignCenter)
    
    def combo_section_selection_changed(self):
        self.update_gps_table(self.combo_section_selection.currentText())

    def on_section_data_processing_finished(self, section_data_objects):
        self.section_processing_thread.quit()
        self.section_processing_thread.wait()
        self.update_section_processing_progress({"progress":100,"message":"Finished Processing Section Data"})

        for row in self.section_data:
            #section_data_objects[row[self.id_col]].display_points()
            self.combo_section_selection.addItem(str(row[self.id_col]))

        self.section_data_objects=section_data_objects
        self.update_gps_table()

    def on_section_processing_error_occurred(self, error_message):
        QMessageBox.warning(self, 'Vbox Processing Error', f'Vbox Processing failed with error: {error_message}')

        self.refresh_progress_output()
        
        self.section_processing_thread.quit()
        self.section_processing_thread.wait()

    def update_gps_table(self,section_number=1):
        gps_data_list=self.section_data_objects[int(section_number)].get_gps_point_list()
        
        self.tbl_view_gps_data_model = CustomTableModel(gps_data_list,self.gps_data_headers)      
        
        self.tbl_view_gps_data_proxy.setFilterKeyColumn(-1)
        self.tbl_view_gps_data_proxy.setSourceModel(self.tbl_view_gps_data_model)
        self.tbl_view_gps_data.setModel(self.tbl_view_gps_data_proxy)
        self.tbl_view_gps_data.setSortingEnabled(True)
        
        self.tbl_view_gps_data_proxy_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.tbl_view_gps_data_proxy_header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)

    def export_multiple(self):
        saveFolder = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if not saveFolder: return

        if self.section_data_objects != None:
            for section in self.section_data_objects:
                self.section_data_objects[section].export_filtered_vbo(f"{saveFolder}/{self.section_data_objects[section].uid}.vbo")
            self._offer_open(saveFolder)

#endregion

#region Link Validation
    def btnSettingsPressed(self):
        dlg = SettingsDialog(self.commissioningConfig, f"{resourcesPath}/neology_average_speed.json", self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            # Reload config so any running comparison picks up new values
            try:
                with open(f"{resourcesPath}/neology_average_speed.json") as c:
                    self.commissioningConfig = json.load(c)
            except Exception as e:
                self.showErrorMessagebox("Settings Error", f"Could not reload settings: {str(e)}")

    def btnImportConfigFilePressed(self):
        xmlFilename, check = QFileDialog.getOpenFileName(None,"Select AverageSpeed EWA Config File:","","XML File (*.xml);;All Files (*.*)",)
        if not check: return
        self.safeZoneConfig=AverageSpeedConfig()
        self.safeZoneConfig.importConfig(xmlFilename)

    def btn_file_checkPressed(self):
        if str(self.line_plate.text()) != "" or str(self.line_hash.text()) != "":
            GPSFilenames, check = QFileDialog.getOpenFileNames(None,"Select Vbox/OxTS GPS File(s):","","All Files (*.*);;Vbox Files (*.vbo);;OxTS Files (*.csv)",)
            if not check: return
            if any("vbo" in s.lower() for s in GPSFilenames) and any("csv" in s.lower() for s in GPSFilenames):
                self.showErrorMessagebox("Incorrect selection","Please select only Vbox or only OxTS csv files.")
                return
            OBODataFilenames, check = QFileDialog.getOpenFileNames(None,"Select OBO Data File","","OBO Files (*.txt *.xlsx);;Text Files (*.txt);;Excel Files (*.xlsx);;All Files (*.*)",)
            if not check: return
            self._wizard = None
            self._startComparison(GPSFilenames, OBODataFilenames, self.line_plate.text(), self.line_hash.text())
        else:
            self.showErrorMessagebox("Invalid plate","Please enter a plate")

    def btn_wizardPressed(self):
        self._wizard = ValidationWizard(self.line_plate.text(), self.line_hash.text(), self)
        self._wizard.comparisonRequested.connect(self._onWizardComparisonRequested)
        self._wizard.show()

    def _onWizardComparisonRequested(self):
        self.line_plate.setText(self._wizard.get_plate())
        self.line_hash.setText(self._wizard.get_plate_hash())
        self._startComparison(self._wizard.get_gps_files(), self._wizard.get_obo_files(), self._wizard.get_plate(), self._wizard.get_plate_hash())

    def _onWizardProgress(self, str_val):
        if self._wizard is None:
            return
        progress = str_val.get("progress", 0)
        message  = str_val.get("message", "")
        page = self._wizard.page(self._wizard.PROGRESS_PAGE)
        page.progress_bar.setValue(progress)
        page.lbl_status.setText(message)

    def _startComparison(self, GPSFilenames, OBODataFilenames, plate, plate_hash):
        self.btn_save_kml.setEnabled(False)
        self.btn_export_validation_data.setEnabled(False)
        self.btn_export_vbox_cut.setEnabled(False)
        self.btn_file_check.setEnabled(False)
        self.btn_wizard.setEnabled(False)
        self.tableValidation.setModel(None)
        self.AverageSpeedValidationManualCheckCompare=AverageSpeedLinkValidationManualComparison(GPSFilenames,OBODataFilenames,self.commissioningConfig, plate, plate_hash)
        self.AverageSpeedValidationManualCheckCompare.updateAverageSpeedValidationPB.connect(self.updateAverageSpeedValidationPB)
        self.AverageSpeedValidationManualCheckCompare.updateValidationTable.connect(self.updateValidationTable)
        self.AverageSpeedValidationManualCheckCompare.validationThreadFinished.connect(self.validationThreadFinished)
        if hasattr(self, '_wizard') and self._wizard is not None:
            self.AverageSpeedValidationManualCheckCompare.updateAverageSpeedValidationPB.connect(self._onWizardProgress)
        self.AverageSpeedValidationManualCheckCompare.start()




    def _offer_open(self, filepath):
        reply = QtWidgets.QMessageBox.question(
            self, "Open File",
            f"File saved successfully.\nWould you like to open it?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes
        )
        if reply == QtWidgets.QMessageBox.Yes:
            import subprocess, sys
            if sys.platform == "win32":
                os.startfile(filepath)
            elif sys.platform == "darwin":
                subprocess.call(["open", filepath])
            else:
                subprocess.call(["xdg-open", filepath])

    def btn_save_kmlPressed(self):
        saveFilename, check = QFileDialog.getSaveFileName(None,"Export Google Earth KML File:","","Google Earth (*.kml);;All Files (*.*)",)
        if not check: return

        self._kml_save_filename = saveFilename
        self.AverageSpeedLinkValidationSaveKML=AverageSpeedLinkValidationSaveKML(saveFilename,self.linkValidationData,self.commissioningConfig)
        self.AverageSpeedLinkValidationSaveKML.updateAverageSpeedValidationPB.connect(self.updateAverageSpeedValidationPB)
        self.AverageSpeedLinkValidationSaveKML.validationThreadFinished.connect(self.kmlThreadFinished)
        self.AverageSpeedLinkValidationSaveKML.start()

    def kmlThreadFinished(self, result):
        if result['Result']:
            self._offer_open(self._kml_save_filename)
        else:
            self.showErrorMessagebox(result['Title'], result['Text'])

    def export_validation_data(self):
        saveFilename, check = QFileDialog.getSaveFileName(None,"Save Comparison Data:","","CSV (*.csv);;All Files (*.*)",)
        if not check: return

        with open(saveFilename,"w") as outfile:
            outfile.write(','.join(map(str, self.validation_headers)) + "\n")

            for row in self.linkValidationData.validationResultData:
                outfile.write(','.join(map(str, row)) + "\n")
            
        wb = Workbook()
        ws = wb.active
        ws.append(self.validation_headers)
        for row in self.linkValidationData.validationResultData:
            ws.append(row)
        wb.save(f"{saveFilename}.xlsx")
        self._offer_open(saveFilename)


    def export_vbox_cut_data(self):
        saveFilename, check = QFileDialog.getSaveFileName(None, "Save Vbox Cut Data:", f"{self.line_plate.text()}_vbox_cut_data.csv", "CSV Files (*.csv);;All Files (*.*)")
        if not check: return

        with open(saveFilename, "w") as f:
            f.write("PassageID,Sats,Time,Speed,Lat,Long\n")
            for row in self.linkValidationData.vboxCutData:
                f.write(",".join(str(v) for v in row) + "\n")
        self._offer_open(saveFilename)

    def updateValidationTable(self, linkValidationData):
        self.linkValidationData=linkValidationData

        if len(self.linkValidationData.validationResultData):

            self.model = CustomTableModel(self.linkValidationData.validationResultData,self.validation_headers)
            self.proxy_model = QSortFilterProxyModel()
            self.proxy_model.setFilterKeyColumn(-1) # Search all columns.
            self.proxy_model.setSourceModel(self.model)
            self.proxy_model.sort(0, Qt.AscendingOrder)
            self.tableValidation.setModel(self.proxy_model)
            tableValidationHeader=self.tableValidation.horizontalHeader()
            tableValidationHeader.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
            tableValidationHeader.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
            self.recolourValidationTable()

    def setValidationControlsEnabled(self, enabled):
        pct_only = self.chk_pct_only.isChecked()
        self.chk_pct_only.setEnabled(enabled)
        self.spin_threshold_high_pos.setEnabled(enabled)
        self.spin_threshold_high_neg.setEnabled(enabled)
        self.spin_speed_breakpoint.setEnabled(enabled and not pct_only)
        self.spin_threshold_low_pos.setEnabled(enabled and not pct_only)
        self.spin_threshold_low_neg.setEnabled(enabled and not pct_only)

    def onValidationEnabledChanged(self):
        self.setValidationControlsEnabled(self.chk_validation_enabled.isChecked())
        self.recolourValidationTable()

    def onPctOnlyChanged(self):
        # Grey out the speed breakpoint and low speed controls when pct-only is active
        self.setValidationControlsEnabled(self.chk_validation_enabled.isChecked())
        self.recolourValidationTable()

    def recolourValidationTable(self):
        # Vbox/Pri Speed % Diff is col 12, Vbox/Pri Speed MPH Diff is col 13
        # Vbox Average Spd is col 10, Pri OBO Spd is col 11
        if not hasattr(self, 'model') or self.model is None:
            return

        if not self.chk_validation_enabled.isChecked():
            for row in range(self.model.rowCount(None)):
                for col in range(len(self.validation_headers)):
                    self.model.change_color(row, col, None)
            return

        low_pos_mph        = self.spin_threshold_low_pos.value()
        low_neg_mph        = self.spin_threshold_low_neg.value()
        high_pos_pct       = self.spin_threshold_high_pos.value()
        high_neg_pct       = self.spin_threshold_high_neg.value()
        speed_breakpoint   = self.spin_speed_breakpoint.value()

        GREEN = QColor(144, 238, 144)
        RED   = QColor(255, 102, 102)

        for row in range(self.model.rowCount(None)):
            try:
                pri_speed  = float(self.model._data[row][11])   # Pri OBO Speed
                mph_diff   = float(self.model._data[row][13])   # Vbox/Pri Speed MPH Diff
                pct_diff   = float(self.model._data[row][12])   # Vbox/Pri Speed % Diff

                if self.chk_pct_only.isChecked():
                    passed = (-high_neg_pct <= pct_diff <= high_pos_pct)
                elif pri_speed <= speed_breakpoint:
                    # mph_diff = vbox - obo, so positive means vbox is faster
                    passed = (-low_neg_mph <= mph_diff <= low_pos_mph)
                else:
                    passed = (-high_neg_pct <= pct_diff <= high_pos_pct)

                colour = GREEN if passed else RED
                for col in range(len(self.validation_headers)):
                    self.model.change_color(row, col, colour)
            except (ValueError, TypeError, IndexError):
                pass

    def updateAverageSpeedValidationPB(self, str_val):
        if "progress" in str_val:
            self.pbAverageSpeedValidation.setValue(str_val["progress"])
        self.pbAverageSpeedValidation.setFormat(str_val['message'])
        self.pbAverageSpeedValidation.setAlignment(QtCore.Qt.AlignCenter)

 
    def validationThreadFinished(self, result):
        self.btn_file_check.setEnabled(True)
        self.btn_wizard.setEnabled(True)
        if result['Result']:
            if len(self.linkValidationData.validationResultData):
                self.btn_save_kml.setEnabled(True)
                self.btn_export_validation_data.setEnabled(True)
                self.btn_export_vbox_cut.setEnabled(True)

                # Build pass/fail counts using current threshold settings and show in wizard
                if hasattr(self, '_wizard') and self._wizard is not None:
                    total  = len(self.linkValidationData.validationResultData)
                    passed = 0
                    failed = 0
                    bp     = self.spin_speed_breakpoint.value()
                    lp     = self.spin_threshold_low_pos.value()
                    ln     = self.spin_threshold_low_neg.value()
                    hp     = self.spin_threshold_high_pos.value()
                    hn     = self.spin_threshold_high_neg.value()
                    pct_only = self.chk_pct_only.isChecked()
                    val_on   = self.chk_validation_enabled.isChecked()
                    for row in self.linkValidationData.validationResultData:
                        try:
                            pri_speed = float(row[11])
                            mph_diff  = float(row[13])
                            pct_diff  = float(row[12])
                            if not val_on:
                                passed += 1
                            elif pct_only:
                                passed += 1 if (-hn <= pct_diff <= hp) else 0
                            elif pri_speed <= bp:
                                passed += 1 if (-ln <= mph_diff <= lp) else 0
                            else:
                                passed += 1 if (-hn <= pct_diff <= hp) else 0
                        except (ValueError, TypeError, IndexError):
                            passed += 1
                    failed = total - passed
                    self._wizard.show_results(total, passed, failed)
                    self._wizard.mark_complete()
                    self._wizard.show()

            if "DisplayMessage" in result:
                self.showInfoMessagebox(result['Title'], result['Text'])
        else:
            self.btn_save_kml.setEnabled(False)
            self.btn_export_validation_data.setEnabled(False)
            self.showErrorMessagebox(result['Title'], result['Text'])


    def showInfoMessagebox(self,title, maintext):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(maintext)
        msg.setWindowTitle(title)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    
    def showErrorMessagebox(self,title, maintext):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(maintext)
        msg.setWindowTitle(title)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
#endregion


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())