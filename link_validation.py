import os
import re
from datetime import *
from datetime import datetime, timedelta
from dateutil.relativedelta import *
from PyQt5 import QtCore
#import mysql.connector
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch,cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import openpyxl

from build_config import resourcesPath
from build_config import applicationPath


class WSDOTInputData:
    ENTRY_PRI_TIME="Entry Primary Time"
    ENTRY_SEC_TIME="Entry Secondary Time"
    EXIT_PRI_TIME="Exit Primary Time"
    EXIT_SEC_TIME="Exit Secondary Time"
    PRI_SPEED="Primary Speed"
    SEC_SPEED="Secondary Speed"
    PRI_CAM_ID="Primary Camera ID"
    LP_NUMBER="LP Number"
    LP_HASH="LP Hash"


class linkValidationData:
    def __init__(self):
        super().__init__()
        self.gpsFilenames = ""
        self.ercuFilenames = ""
        self.gpsData = []
        self.ercuData=[]
        self.ercuRawDataFile=[]
        self.validationResultData=[]
        self.instationIP=""
        self.username=""
        self.password=""
        self.VRM=""
        self.searchDateTime=""
        self.saveFilename=""
        self.vboxSerials=[]
        self.calibrationEquipmentType=""
        self.commissioningConfig=""

class AverageSpeedLinkValidationManualComparison(QtCore.QThread):
    updateValidationTable = QtCore.pyqtSignal(linkValidationData)
    validationThreadFinished = QtCore.pyqtSignal(dict)
    updateAverageSpeedValidationPB = QtCore.pyqtSignal(dict)
        
    def __init__(self,GPSFilenames,ERCUDataFilenames,commissioningConfig, plate, plate_hash):
        super(QtCore.QThread,self).__init__()
        self.linkValData = linkValidationData()
        self.linkValData.gpsFilenames=GPSFilenames
        self.linkValData.ercuFilenames=ERCUDataFilenames
        self.pbTotal=len(GPSFilenames)+len(ERCUDataFilenames)+1
        self.linkValData.commissioningConfig=commissioningConfig
        self.plate=str(plate)
        self.plate_hash=str(plate_hash)

    def run(self):
        try:
            linkVal = linkValidation(self)
            self.linkValData=linkVal.manualComparison(self.linkValData,self.plate, self.plate_hash)
            self.updateValidationTable.emit(self.linkValData)
            self.validationThreadFinished.emit({"Result":True, "Title":"Validation Complete", "Text":"Manual validation comparison is complete."})
            self.updateAverageSpeedValidationPB.emit({"progress":100,"message":"Completed Successfully"})
        except Exception as e:
            self.validationThreadFinished.emit({"Result":False, "Title":"Validation Failed", "Text":str(e), "DisplayMessage":True})
            self.updateAverageSpeedValidationPB.emit({"progress":0,"message":""})

class AverageSpeedLinkValidationSaveKML(QtCore.QThread):
    validationThreadFinished = QtCore.pyqtSignal(dict)
    updateAverageSpeedValidationPB = QtCore.pyqtSignal(dict)
        
    def __init__(self,saveFilename, validationData,commissioningConfig):
        super(QtCore.QThread,self).__init__()
        self.linkValData = validationData
        self.linkValData.saveFilename=saveFilename
        self.linkValData.commissioningConfig=commissioningConfig
        self.pbTotal=2

    def run(self):
        try:
            linkVal = linkValidation(self)
            linkVal.saveKML(self.linkValData)
            self.validationThreadFinished.emit({"Result":True, "Title":"Google Earth File Saved", "Text":"Google Earth file saved in " + self.linkValData.saveFilename, "DisplayMessage":True}) 
            self.updateAverageSpeedValidationPB.emit({"progress":100,"message":"Completed Successfully"})
        except Exception as e:
            self.validationThreadFinished.emit({"Result":False, "Title":"Save KML Failed", "Text":str(e), "DisplayMessage":True})
            self.updateAverageSpeedValidationPB.emit({"progress":0,"message":""})

class linkValidation:
    def __init__(self,UI):
        super().__init__()
        self.validationData=linkValidationData()
        self.UI=UI
        self.pbProgress=0

    def manualComparison(self,linkValData,plate, plate_hash):
        #Do link validation comparison between GPS and ERCU files
        self.validationData = linkValData
        self.plate=str(plate)
        self.plate_hash=str(plate_hash)

        if self.validationData.gpsFilenames and self.validationData.ercuFilenames:
            self.importGPSFiles()
            self.importERCUFiles()
            self.doComparison()
            return self.validationData

    def ercuComparison(self,linkValData):
        #Do link validation comparison between GPS and ERCU database
        self.validationData = linkValData

        if self.validationData.gpsFilenames:
            self.importGPSFiles()
            self.getPassagesFromERCU()
            self.doComparison()
            return self.validationData
        

    def importGPSFiles(self):
        #Determine if GPS file is OxTS or Vbox then call appropriate function
        self.UI.updateAverageSpeedValidationPB.emit({"progress":0,"message":"Importing GPS File(s)"})

        for file in self.validationData.gpsFilenames:
            if os.path.splitext(file)[-1].lower() == ".vbo":
                self.validationData.calibrationEquipmentType="Vbox"
                self.importVboxFile(file)
            elif os.path.splitext(file)[-1].lower() == ".csv":
                self.validationData.calibrationEquipmentType="OxTS"
                self.importOxTSFile(file)
            self.pbProgress+=1
            currentProgress=int((self.pbProgress/self.UI.pbTotal)*100)
            self.UI.updateAverageSpeedValidationPB.emit({"progress":currentProgress,"message":"Importing GPS File(s)"})
        
        
    def importVboxFile(self, file):
        #Import Vbox data to a list of dict
        dataReached=False
        firstDataLine=True
        vboxFile = open(file)
        fileType = "sx10"
        speedUnits="mph"

        for line in vboxFile:
            if line.startswith("File"):     #First line, grab start date
                vboxStartDate=line.split()[3]
            
            #Check if SX10 file or touch file
            if line.startswith("Type"):
                fileType="touch"

            
            if line.startswith("Serial") and fileType == "sx10":     #Serials line, add to serial list
                serial=line.split()[3].lstrip('0')
                if serial not in self.validationData.vboxSerials:
                    self.validationData.vboxSerials.append(serial)
            elif line.startswith("Serial") and fileType == "touch":
                serial=line.split()[2].lstrip('0')
                if serial not in self.validationData.vboxSerials:
                    self.validationData.vboxSerials.append(serial)
            
            #Determine if mph or kph
            if line.startswith("velocity mph"):
                speedUnits="mph"
            elif line.startswith("velocity kmh"):                
                speedUnits="kmh"
            

            if dataReached and fileType == "sx10":
                gpsDataLine = line.split()


                #Ignore midnight
                if not "240000" in line[1]:
                    #Combine Vbox Date and gps point time
                    gpsDateTimeString = vboxStartDate + " " + gpsDataLine[1] + "0"

                    #Convert DateTime to a datetime
                    utc_time = datetime.strptime(gpsDateTimeString, "%d/%m/%Y %H%M%S.%f")

                    #If its not the first data line (i.e Vbox didnt start at midnight) and data crosses midnight then add a day
                    if not firstDataLine and line[1].startswith("000000.10"):
                        #Add day
                        utc_time = utc_time + timedelta(days=1)

                    #Add configured time offset (in hours)
                    #utc_time = utc_time + timedelta(hours=TimeOffset)
                    utc_time = utc_time + timedelta(hours=int(float(self.validationData.commissioningConfig['AverageSpeed']['time_offset'])))
                    
                    #Convert to epoch in ms
                    #epochTime = (utc_time - datetime(1970, 1, 1)).total_seconds()*1000
                    #Subtract the GPS leap seconds  
                    #epochTime = int(epochTime) - (int(self.validationData.commissioningConfig['AverageSpeed']['leap_seconds'])*1000)

                    self.validationData.gpsData.append({"SatNumber":gpsDataLine[0],"Time":utc_time,"Speed":gpsDataLine[4],"Lat":gpsDataLine[2],"Long":gpsDataLine[3]})

                    firstDataLine=False
            elif dataReached and fileType == "touch":
                gpsDataLine = line.split()

                #Ignore midnight
                if not "240000" in line[1]:
                    #Combine Vbox Date and gps point time
                    gpsDateTimeString = vboxStartDate + " " + gpsDataLine[1] + "0"

                    #Convert DateTime to a datetime
                    utc_time = datetime.strptime(gpsDateTimeString, "%d/%m/%Y %H%M%S.%f")

                    #If its not the first data line (i.e Vbox didnt start at midnight) and data crosses midnight then add a day
                    if not firstDataLine and line[1].startswith("000000.10"):
                        #Add day
                        utc_time = utc_time + timedelta(days=1)

                    #Add configured time offset (in hours)
                    #utc_time = utc_time + timedelta(hours=TimeOffset)
                    utc_time = utc_time + timedelta(hours=int(float(self.validationData.commissioningConfig['AverageSpeed']['time_offset'])))
                    
                    #Convert to epoch in ms
                    #epochTime = (utc_time - datetime(1970, 1, 1)).total_seconds()*1000
                    #Subtract the GPS leap seconds  
                    #epochTime = int(epochTime) - (int(self.validationData.commissioningConfig['AverageSpeed']['leap_seconds'])*1000)

                    #Convert speed units to mph
                    if speedUnits=="kmh":
                        speed=float(gpsDataLine[4])/1.609344
                        gpsDataLine[4]=str(speed)

                    self.validationData.gpsData.append({"SatNumber":gpsDataLine[0],"Time":utc_time,"Speed":gpsDataLine[4],"Lat":gpsDataLine[2],"Long":gpsDataLine[3]})

                    firstDataLine=False

            if line.startswith("[data]"):   #Vbox Data reached
                dataReached=True

        vboxFile.close()
        

    """ def importOxTSFile(self, file):
        #Import OxTS File to a list of dict
        lineNumber=0
        columnNumber=0

        OxTSFile = open(file)
        for gpsDataLine in OxTSFile:
            #Configure columns he
            if lineNumber == 0:
                for column in gpsDataLine.split(","):
                    if column == "Date (UTC)":
                        dateColumn=columnNumber
                    elif column ==  "Time (UTC)":
                        timeColumn=columnNumber
                    elif column ==  "Speed2D (mph)":
                        speedColumn=columnNumber
                    elif column ==  "PosLat (deg)":
                        latColumn=columnNumber
                    elif column ==  "PosLon (deg)":
                        longColumn=columnNumber
                    elif column ==  "GpsNumSats":
                        satColumn=columnNumber
                    columnNumber=columnNumber+1
            else:
                gpsDataList=gpsDataLine.split(',')
                #Combine date and time
                gpsDateTimeString = gpsDataList[dateColumn] + " " + gpsDataList[timeColumn]
                #Convert DateTime to a datetime
                utc_time = datetime.strptime(gpsDateTimeString, "%d/%m/%Y %H:%M:%S.%f")
                #Convert to epoch in ms
                epochTime = int((utc_time - datetime(1970, 1, 1)).total_seconds()*1000)
                
                #Check for null values in data, set to 0 if found
                if gpsDataList[satColumn].strip() == "" or gpsDataList[speedColumn].strip() == "" or gpsDataList[latColumn].strip() == "" or gpsDataList[longColumn].strip() == "":
                    self.validationData.gpsData.append({"SatNumber":0,"EpochTime":epochTime,"Speed":0,"Lat":0,"Long":0})
                else:
                    self.validationData.gpsData.append({"SatNumber":gpsDataList[satColumn],"EpochTime":epochTime,"Speed":gpsDataList[speedColumn],"Lat":gpsDataList[latColumn],"Long":gpsDataList[longColumn]})
            lineNumber=lineNumber+1 """
        

    def importERCUFiles(self):
        #Import ERCU datafiles to a dict
        self.UI.updateAverageSpeedValidationPB.emit({"message":"Importing ERCU File(s)"})

        for file in self.validationData.ercuFilenames:
            self.importERCUFile(file)
            self.pbProgress+=1
            currentProgress=int((self.pbProgress/self.UI.pbTotal)*100)
            self.UI.updateAverageSpeedValidationPB.emit({"progress":currentProgress,"message":"Importing ERCU File(s)"})
        

    def importERCUFile(self, file):
        #Check if input file is WSDOT or SpeedSpike
        if file.endswith(".xls") == True or file.endswith(".xlsx") == True:
            #Process WSDOT excel file
            workbook=openpyxl.load_workbook(file)
            sheets = workbook.sheetnames
            #sheet = workbook[sheets[0]]
            sheet = workbook['Matched']

            list_values = list(sheet.values)
            headers=list(list_values[0])
            
            #self.plate_col=headers.index(WSDOTInputData.PLATE)


            self.entry_pri_time_col=headers.index(WSDOTInputData.ENTRY_PRI_TIME)
            self.entry_sec_time_col=headers.index(WSDOTInputData.ENTRY_SEC_TIME)
            self.exit_pri_time_col=headers.index(WSDOTInputData.EXIT_PRI_TIME)
            self.exit_sec_time_col=headers.index(WSDOTInputData.EXIT_SEC_TIME)
            self.pri_speed_col=headers.index(WSDOTInputData.PRI_SPEED)
            self.sec_speed_col=headers.index(WSDOTInputData.SEC_SPEED)
            self.pri_camera_id_col=headers.index(WSDOTInputData.PRI_CAM_ID)
            self.lp_number_col=headers.index(WSDOTInputData.LP_NUMBER)
            self.lp_hash_col=headers.index(WSDOTInputData.LP_HASH)

            ercu_data=[list(elem) for elem in list_values[1:]]
            
            passage_id=1
            for row in ercu_data:
                if row[0] != None:
                    #Check if passage is a VRM we are interested in
                    if str(row[self.lp_number_col]) == str(self.plate) or str(row[self.lp_hash_col]) == str(self.plate_hash):
                        #Convert datetime strings to datetime types

                        if isinstance(row[self.entry_pri_time_col],str) == True:
                            entry_pri_utc_time = datetime.strptime(row[self.entry_pri_time_col], "%Y-%m-%d %H:%M:%S.%f")
                            exit_pri_utc_time = datetime.strptime(row[self.exit_pri_time_col], "%Y-%m-%d %H:%M:%S.%f")
                        else:
                            entry_pri_utc_time = row[self.entry_pri_time_col]
                            exit_pri_utc_time = row[self.exit_pri_time_col]

                        if isinstance(row[self.entry_sec_time_col],str) == True:
                            entry_sec_utc_time = datetime.strptime(row[self.entry_sec_time_col], "%Y-%m-%d %H:%M:%S.%f")
                            exit_sec_utc_time = datetime.strptime(row[self.exit_sec_time_col], "%Y-%m-%d %H:%M:%S.%f")
                        else:
                            entry_sec_utc_time = row[self.entry_sec_time_col]
                            exit_sec_utc_time = row[self.exit_sec_time_col]

                        #entry_pri_utc_time = entry_pri_utc_time + timedelta(seconds=18)
                        #exit_pri_utc_time = exit_pri_utc_time + timedelta(seconds=18)
                        #entry_sec_utc_time = entry_sec_utc_time + timedelta(seconds=18)
                        #exit_sec_utc_time = exit_sec_utc_time + timedelta(seconds=18)
                        

                        entry_time_diff=entry_pri_utc_time-entry_sec_utc_time
                        exit_time_diff=exit_pri_utc_time-exit_sec_utc_time

                        vrm=str(row[self.lp_number_col])

                        pri_speed=float(row[self.pri_speed_col])
                        sec_speed=float(row[self.sec_speed_col])
                        diff=(sec_speed-pri_speed)*100/pri_speed


                        self.validationData.ercuData.append({"PassageID":vrm + "_" + str(passage_id), "DateTime":row[self.entry_pri_time_col],"VRM":vrm,"Speed":row[self.pri_speed_col],"SecSpeed":sec_speed,"PriSecSpeedDiff":diff,"FromRSE":row[self.pri_camera_id_col],"FromTime":entry_pri_utc_time,"ToRSE":"NA","ToTime":exit_pri_utc_time,"EntrySecTime":entry_sec_utc_time,"ExitSecTime":exit_sec_utc_time,"EntryTimeDiff":entry_time_diff.total_seconds(),"ExitTimeDiff":exit_time_diff.total_seconds()})                        
                        passage_id+=1
        else:
            ERCUFile = open(file)
            #Process Speed Spike
            for ERCUDataLine in ERCUFile:
                ERCUDataList=re.split(r'\t+', ERCUDataLine.rstrip('\t'))

                #Ignore header line:
                if ERCUDataList[0] != "PassageID":
                    passageID=ERCUDataList[0]
                    dateTime=ERCUDataList[1]
                    fromRSE=ERCUDataList[2]
                    toRSE=ERCUDataList[3]
                    fromEpochTime=ERCUDataList[4]
                    toEpochTime=ERCUDataList[5]
                    speed=ERCUDataList[6].rstrip()
                    self.validationData.ercuData.append({"PassageID":passageID, "DateTime":dateTime,"Speed":speed,"FromRSE":fromRSE,"FromEpochTime":fromEpochTime,"ToRSE":toRSE,"ToEpochTime":toEpochTime})
                    passageID=None
                    dateTime=None
                    speed=None
                    fromRSE=None
                    fromEpochTime=None
                    toRSE=None

    def getPassagesFromERCU(self):
        #Connect to ERCU and get passage information
        mydb = mysql.connector.connect( host=self.validationData.instationIP, user=self.validationData.username, password=self.validationData.password, database="liftdb", ssl_disabled=True)
        cur = mydb.cursor()
        sql="SELECT a.PASSAGE_ID,a.TIMEDATE,a.VRM,a.PRIMARY_SPEED,a.ENTRY_RSE_ID, a.EXIT_RSE_ID, b.CAPTUREDATE_MS, c.CAPTUREDATE_MS from violationcreation.speedviolations_" + self.validationData.searchDateTime + " a join liftdb.ernoncompliantlog_" + self.validationData.searchDateTime + " b on a.ENTRY_ERID = b.ER_ID join liftdb.ernoncompliantlog_" + self.validationData.searchDateTime + " c on a.EXIT_ERID = c.ER_ID where a.VRM='" + self.validationData.VRM + "' and b.RSE_ID IS NOT null and c.RSE_ID IS NOT null"

        cur.execute(sql)
        ercuData=cur.fetchall()
        cur.close()
        mydb.close()

        for passage in ercuData:
            self.validationData.ercuData.append({"PassageID":passage[0], "DateTime":passage[1].strftime("%d/%m/%Y %H:%M:%S"),"Speed":str(passage[3]),"FromRSE":str(passage[4]),"FromTime":str(passage[6]),"ToRSE":str(passage[5]),"ToTime":str(passage[7])})

        
    def doComparison(self):
        currentProgress=int((self.UI.pbTotal-1/self.UI.pbTotal)*100)
        self.UI.updateAverageSpeedValidationPB.emit({"progress":currentProgress,"message":"Calculating Passages"})
        f = open(f"{self.plate}_vbox_cut_data.csv","w")
        f.write("PassageID,Sats,Time,Speed,Lat,Long\n")


        for passage in self.validationData.ercuData:   #For each ERCU passage do a calculation from GPS data
            vbox_cut_data=[]
            validity=""
            totalSpeed=0
            totalGPSPoints=0
            percentDiff=0
            avSpeed=0
            gpsErrorPoints=0
            MinSats=int(self.validationData.commissioningConfig['AverageSpeed']['min_sats'])

            for gpsPoint in self.validationData.gpsData:
                if gpsPoint['Time'] >= passage['FromTime'] and gpsPoint['Time'] <= passage['ToTime'] and int(float(gpsPoint['SatNumber'])) >= MinSats:
                    totalSpeed = totalSpeed+ float(gpsPoint['Speed'])
                    totalGPSPoints+=1


                    #TEMPORARY
                    f.write(f"{passage['PassageID']},{gpsPoint['SatNumber']},{gpsPoint['Time']},{gpsPoint['Speed']},{gpsPoint['Lat']},{gpsPoint['Long']}\n")

                    vbox_cut_data.append(gpsPoint)

                elif gpsPoint['Time'] >= passage['FromTime'] and gpsPoint['Time'] <= passage['ToTime'] and int(float(gpsPoint['SatNumber'])) < MinSats:
                    gpsErrorPoints+=1
        

            if totalGPSPoints > 0:
                avSpeed=totalSpeed / totalGPSPoints
                #print(f"{totalSpeed} : {totalGPSPoints} : {avSpeed}")
                percentDiff=((float(passage['Speed']) - avSpeed) / avSpeed * 100)
                ercuSpeed=passage['Speed']

                #Check validity of run against Home Office requirements
                if (float(ercuSpeed) < 66 and (float(avSpeed) - float(ercuSpeed)) > 2) or \
                        (float(ercuSpeed) < 50 and (float(avSpeed) - float(ercuSpeed)) < -5) or \
                        (float(ercuSpeed) > 66 and percentDiff > 3) or \
                        (float(ercuSpeed) > 50 and percentDiff < -10):
                    validity="Invalid"
                else:
                    validity="Valid"

                vbox_start=vbox_cut_data[0]['Time'].strftime("%Y/%m/%d %H:%M:%S.%f")
                vbox_end=vbox_cut_data[-1]['Time'].strftime("%Y/%m/%d %H:%M:%S.%f")

                speed_diff=round(avSpeed,3) - float(passage['Speed'])

                #self.validationData.validationResultData.append([passage['PassageID'],str(passage['DateTime']).split(' ')[0],passage['VRM'],str(passage['DateTime']).split(' ')[1],passage['FromRSE'],passage['ToRSE'],round(avSpeed,3),passage['Speed'],str(round(percentDiff,3)),vbox_start,vbox_end,totalGPSPoints,gpsErrorPoints,validity])
                #self.validationData.validationResultData.append([passage['PassageID'],str(passage['DateTime']).split(' ')[0],passage['VRM'],str(passage['DateTime']).split(' ')[1],passage['FromRSE'],passage['ToRSE'],round(avSpeed,3),passage['Speed'],str(round(percentDiff,3)),vbox_start,vbox_end,totalGPSPoints,gpsErrorPoints])
                self.validationData.validationResultData.append([passage['PassageID'],str(passage['DateTime']),str(passage['EntrySecTime'])[:-3],passage['EntryTimeDiff'], str(passage['ToTime'])[:-3],str(passage['ExitSecTime'])[:-3],passage['ExitTimeDiff'],str(passage['VRM']),passage['FromRSE'],passage['ToRSE'],round(avSpeed,3),passage['Speed'],str(round(percentDiff,3)),speed_diff,passage['SecSpeed'],passage['PriSecSpeedDiff'],vbox_start[:-3],vbox_end[:-3],totalGPSPoints,gpsErrorPoints])
        
                self.validation_headers=['Passage','Pri Entry Time','Sec Entry Time','Entry Time Diff','Pri Exit Time','Sec Exit Time','Exit Time Diff','VRM','From','To','GPS Spd','Pri ERCU Spd','% Diff',"Spd Diff","Sec Spd","% Pri/Sec Spd Diff","FromVbox","ToVbox",'Points','Errors']
        
        f.close()

    #Save validation runs in Google Earth KML format
    def saveKML(self,linkValData):
        self.validationData = linkValData
        self.UI.updateAverageSpeedValidationPB.emit({"progress":0,"message":"Importing GPS File(s)"})
        self.UI.pbTotal=len(self.validationData.ercuData*2)
        MinSats=int(self.validationData.commissioningConfig['AverageSpeed']['min_sats'])

        if self.validationData.saveFilename != "":
            f = open(self.validationData.saveFilename, "w")
            f.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?><kml xmlns=\"http://earth.google.com/kml/2.1\"><Document><Folder><name>Filtered Passage Data</name><description>GPS data for each passage filtered by minimum number of satellites (" + str(MinSats) + ")</description>\n")

            for passage in self.validationData.ercuData:   #Step through passages one by one
                #KML PATH START
                f.write("<Placemark><name>" + passage['FromRSE'] + "_" + passage['PassageID'] + "</name><LineString><tessellate>1</tessellate><coordinates>\n")
                for gpsPoint in self.validationData.gpsData:
                    if gpsPoint['Time'] >= passage['FromTime'] and gpsPoint['Time'] <= passage['ToTime'] and int(float(gpsPoint['SatNumber'])) >= MinSats:

                        if gpsPoint['Lat'][2] == ".":   #Process OxTS
                            Lat=gpsPoint['Lat']
                            Long=gpsPoint['Long']
                        else:   #Process Vbox
                            Long = 0;
                            Lat = 0;

                            #Convert Latitude co-ordinate
                            if ('+' in gpsPoint['Lat']):  #Lat co-ordinates are North
                                latSplit = gpsPoint['Lat'].split('+')
                                Lat = float(latSplit[1])
                                Lat = Lat / 60;
                            
                            else:  #Lat co-ordinates are South
                                latSplit = gpsPoint['Lat'].split('-')
                                Lat = float(latSplit[1]);
                                Lat = Lat / 60;
                                Lat = Lat * -1;
                            

                            #Convert Longitude co-ordinate
                            if ('+' in gpsPoint['Long']):  #Long co-ordinates are West
                                longSplit = gpsPoint['Long'].split('+');
                                Long = float(longSplit[1]);
                                Long = Long / 60;
                                Long = Long * -1;
                            
                            else:  #Long co-ordinates are East
                                longSplit = gpsPoint['Long'].split('-');
                                Long = float(longSplit[1]);
                                Long = Long / 60;
                            

                        f.write(str(Long) + "," + str(Lat) + ",0\n")
                f.write("</coordinates></LineString></Placemark>\n")
                
                self.pbProgress+=1
                currentProgress=int((self.pbProgress/self.UI.pbTotal)*100)
                self.UI.updateAverageSpeedValidationPB.emit({"progress":currentProgress,"message":"Saving Filtered GPS Points"})

            f.write("</Folder><Folder><name>Raw Unfiltered GPS Data</name><description>Raw GPS data for each passage with no satellite filtering applied.</description>")

            for passage in self.validationData.ercuData:   #Step through passages one by one
                #KML PATH START
                f.write("<Placemark><name>" + passage['PassageID'] + "</name><LineString><tessellate>1</tessellate><coordinates>\n")
                for gpsPoint in self.validationData.gpsData:
                    if gpsPoint['Time'] >= passage['FromTime'] and gpsPoint['Time'] <= passage['ToTime']:

                        if gpsPoint['Lat'][2] == ".":   #Process OxTS
                            Lat=gpsPoint['Lat']
                            Long=gpsPoint['Long']
                        else:   #Process Vbox
                            Long = 0;
                            Lat = 0;

                            #Convert Latitude co-ordinate
                            if ('+' in gpsPoint['Lat']):  #Lat co-ordinates are North
                                latSplit = gpsPoint['Lat'].split('+')
                                Lat = float(latSplit[1])
                                Lat = Lat / 60;
                            
                            else:  #Lat co-ordinates are South
                                latSplit = gpsPoint['Lat'].split('-')
                                Lat = float(latSplit[1]);
                                Lat = Lat / 60;
                                Lat = Lat * -1;
                            

                            #Convert Longitude co-ordinate
                            if ('+' in gpsPoint['Long']):  #Long co-ordinates are West
                                longSplit = gpsPoint['Long'].split('+');
                                Long = float(longSplit[1]);
                                Long = Long / 60;
                                Long = Long * -1;
                            
                            else:  #Long co-ordinates are East
                                longSplit = gpsPoint['Long'].split('-');
                                Long = float(longSplit[1]);
                                Long = Long / 60;
                            
                        f.write(str(Long) + "," + str(Lat) + ",0\n")

                
                self.pbProgress+=1
                currentProgress=int((self.pbProgress/self.UI.pbTotal)*100)
                self.UI.updateAverageSpeedValidationPB.emit({"progress":currentProgress,"message":"Saving Raw GPS Points"})

                f.write("</coordinates></LineString></Placemark>\n")
            f.write("</Folder></Document></kml>\n")
            f.close()
               

    def saveERCUData(self, linkValData):
        self.validationData = linkValData

        #Export ERCU datafile to file
        f = open(self.validationData.saveFilename, "w")
        f.write("PASSAGE_ID\tTIMEDATE\tPRIMARY_SPEED\tFROM_RSE\tFROM_TIMEDATE_MS\tTO_RSE\tTO_RSE_MS\n")
        for line in self.validationData.ercuData:
            f.write(line["PassageID"] + "\t" + line["DateTime"] + "\t" + line["Speed"] + "\t" + line["FromRSE"] + "\t" + line["FromTime"] + "\t" + line["ToRSE"] + "\t" + line["ToEpochTime"] + "\n")
        f.close()