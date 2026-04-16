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

        #Average Speed Tab
        self.btn_file_check = self.findChild(QtWidgets.QPushButton,'btn_file_check')
        self.btn_file_check.clicked.connect(self.btn_file_checkPressed)

        self.btn_save_kml = self.findChild(QtWidgets.QPushButton,'btn_save_kml')
        self.btn_save_kml.clicked.connect(self.btn_save_kmlPressed)

        self.btn_export_validation_data = self.findChild(QtWidgets.QPushButton,'btn_export_validation_data')
        self.btn_export_validation_data.clicked.connect(self.export_validation_data)
        self.tableValidation=self.findChild(QtWidgets.QTableView,'tbl_validation')

        
        self.line_plate = self.findChild(QtWidgets.QLineEdit,'line_plate')
        self.line_hash = self.findChild(QtWidgets.QLineEdit,'line_hash')

        #self.dateValidation.setDateTime(QtCore.QDateTime.currentDateTime())

        self.pbAverageSpeedValidation = self.findChild(QtWidgets.QProgressBar,'pb_link_validation')
    
        self.btn_import_config_file = self.findChild(QtWidgets.QPushButton,'btn_import_config_file')
        self.btn_import_config_file.clicked.connect(self.btnImportConfigFilePressed)
        self.btn_import_config_file.setVisible(False)

        self.btn_save_kml.setEnabled(False)
        self.btn_export_validation_data.setEnabled(False)

        #self.validation_headers=['Passage','Date','VRM','Time','From','To','GPS','ERCU','% Diff','Points','Errors','Validity']
        #self.validation_headers=['Passage','Date','VRM','Time','From','To','GPS','ERCU','% Diff', "FromVbox","ToVbox",'Points','Errors']
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
            
            for x in range(0,len(headers)-1):
                self.tbl_view_section_data_proxy_header.setSectionResizeMode(x, QtWidgets.QHeaderView.ResizeToContents)
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
        
        for x in range(0,len(self.gps_data_headers)-1):
            self.tbl_view_gps_data_proxy_header.setSectionResizeMode(x, QtWidgets.QHeaderView.ResizeToContents)

    def export_multiple(self):
        saveFolder = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if not saveFolder: return

        if self.section_data_objects != None:
            for section in self.section_data_objects:
                self.section_data_objects[section].export_filtered_vbo(f"{saveFolder}/{self.section_data_objects[section].uid}.vbo")

#endregion

#region Link Validation
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
            ERCUDataFilenames , check = QFileDialog.getOpenFileNames(None,"Select ERCU Data File","","All Files (*.*);;Text Files (*.txt);;CSV Files (*.csv)",)
            if not check: return

            self.btn_save_kml.setEnabled(False)
            self.btn_export_validation_data.setEnabled(False)
            self.btn_file_check.setEnabled(False)
            self.tableValidation.setModel(None)
            self.AverageSpeedValidationManualCheckCompare=AverageSpeedLinkValidationManualComparison(GPSFilenames,ERCUDataFilenames,self.commissioningConfig, self.line_plate.text(), self.line_hash.text())
            self.AverageSpeedValidationManualCheckCompare.updateAverageSpeedValidationPB.connect(self.updateAverageSpeedValidationPB)
            self.AverageSpeedValidationManualCheckCompare.updateValidationTable.connect(self.updateValidationTable)
            self.AverageSpeedValidationManualCheckCompare.validationThreadFinished.connect(self.validationThreadFinished)
            self.AverageSpeedValidationManualCheckCompare.start()
        else:
            self.showErrorMessagebox("Invalid plate","Please enter a plate")




    def btn_save_kmlPressed(self):
        saveFilename, check = QFileDialog.getSaveFileName(None,"Save Google Earth KML File:","","Google Earth (*.kml);;All Files (*.*)",)
        if not check: return

        self.AverageSpeedLinkValidationSaveKML=AverageSpeedLinkValidationSaveKML(saveFilename,self.linkValidationData,self.commissioningConfig)
        self.AverageSpeedLinkValidationSaveKML.updateAverageSpeedValidationPB.connect(self.updateAverageSpeedValidationPB)
        self.AverageSpeedLinkValidationSaveKML.validationThreadFinished.connect(self.validationThreadFinished)
        self.AverageSpeedLinkValidationSaveKML.start()

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
            for x in range(0,len(self.validation_headers)-1):
                tableValidationHeader.setSectionResizeMode(x, QtWidgets.QHeaderView.ResizeToContents)

    def updateAverageSpeedValidationPB(self, str_val):
        if "progress" in str_val:
            self.pbAverageSpeedValidation.setValue(str_val["progress"])
        self.pbAverageSpeedValidation.setFormat(str_val['message'])
        self.pbAverageSpeedValidation.setAlignment(QtCore.Qt.AlignCenter)
 
    def validationThreadFinished(self, result):
        self.btn_file_check.setEnabled(True)
        if result['Result']:
            if len(self.linkValidationData.validationResultData):
                self.btn_save_kml.setEnabled(True)
                self.btn_export_validation_data.setEnabled(True)
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
