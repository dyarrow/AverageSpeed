from pyproj import Transformer
from pyproj import Proj, transform
from datetime import datetime
from datetime import timedelta
import queue
import math
import utm
import geopy.distance
from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
from PyQt5.QtWidgets import QFileDialog,QMainWindow,QApplication
import time

leap_seconds=18
time_offset=0


def toDMS(val):
    negative=False
    if val < 0:
        negative=True
        val = -val
    
    degrees = math.floor(val)
    min =  math.floor(val*60) - degrees*60
    sec =  val*3600 - degrees*3600 - min*60

    if negative==True:
        return str(-degrees)+ "°" + str(min) + "\'" + str(round(sec,5)) + "\""
    else:
        return str(degrees)+ "°" + str(min) + "\'" + str(round(sec,5)) + "\""
 
class gpsPoint:
    def __init__(self,sat_number, epochtime, intime, lat, long, speed):
        super().__init__()
        self.sat_number=sat_number
        self.epochtime=epochtime
        self.time=intime #datetime.strptime(intime,"%Y-%m-%d %H:%M:%S.%f")
        self.speed=speed
        self.altitude=1
        
        self.lat=float(lat)/(60*1)
        self.long=-float(long)/(60*1)
        self.lat_dms=toDMS(self.lat)
        self.long_dms=toDMS(self.long)

        utm_zone = utm.from_latlon(self.lat, self.long)
        self.utm_zone=utm_zone[2]

        self.northing,self.easting=self.lat_long_northing_easting(self.lat, self.long)


    
    def print_point(self):
        print (f"{self.sat_number},{self.epochtime},{self.time},{self.lat},{self.long},{self.speed},{self.northing},{self.easting},{self.altitude}")

    def get_list(self):
        gps_list=[self.sat_number,self.epochtime,self.time.strftime('%Y/%m/%d %H:%M:%S.%f').strip()[:-3],self.lat,self.long,self.speed,str(self.northing),str(self.easting),self.altitude]
        return gps_list
        #print (f"{self.sat_number},{self.epochtime},{self.time},{self.lat},{self.long},{self.speed},{self.northing},{self.easting},{self.altitude}")

    def to_str(self):        
        return f"{self.time.strftime('%Y/%m/%d %H:%M:%S.%f').strip()[:-3]},{self.lat},{self.long},1,{self.sat_number},1,1,1,1,{self.easting},{self.northing},{self.altitude}"

    def lat_long_northing_easting(self,lat,long):
        # Define the UTM projection (WGS84 datum)
        proj_utm = Proj(proj="utm", zone=self.utm_zone, ellps="WGS84", south=False)

        # Convert to UTM
        easting, northing = proj_utm(long, lat)

        return northing, easting

class SectionData:
    def __init__(self, UI, uid, file,start_time,end_time):
        super().__init__()
        self.UI=UI
        self.uid=uid
        self.model=""
        self.serials=[]
        self.gps_data=[]
        self.vbox_start_date=""
        self.speed_units="mph"
        self.progress=0
        self.vbo_filtered_data=""

        self.section_file=file
        self.start_time=start_time
        self.end_time=end_time

    def add_gps_point(self,sat_number, epochtime, time, lat, long, speed):
        try:
            self.gps_data.append(gpsPoint(sat_number, epochtime, time, lat, long, speed))
        except Exception as e:
            print(e)
    
    def display_points(self):
        print("Satellites,Epoch,Time,Latitude(),Longitude(),Speed,Northing,Easting,Altitude")
        for gps_point in self.gps_data:
            gps_point.print_point()
    
    def get_gps_point_list(self):
        gps_point_list=[]
        for gps_point in self.gps_data:
            
            #gps_point_list.append((gps_point.long,gps_point.lat))
            gps_point_list.append(gps_point.get_list())
        return gps_point_list

    def export_to_csv(self,filename):
        with open(filename,"w") as csv_file:
            csv_file.write("Time, Latitude(), Longitude(),Height, Number of GPS satellites used(), GPS position mode(), Position accuracy north, Position accuracy east, Position accuracy down,Easting,Northing,Altitude\n")
            for gps_point in self.gps_data:                
                csv_file.write(gps_point.to_str() + "\n")

    def export_filtered_vbo(self,filename):
        with open(filename,"w") as vbo_file:
            for line in self.vbo_filtered_data:                
                vbo_file.write(line)

    def display_distances(self):
        ctr=0
        for gps_point in self.gps_data:
            if ctr>0:
                coords_1 = (gps_point.lat, gps_point.long)
                coords_2 = (self.gps_data[ctr-1].lat,self.gps_data[ctr-1].long)
                distance=geopy.distance.geodesic(coords_1,coords_2).m
                print(distance)
            ctr+=1

    def process_gps_data(self):
        try:
            start_time=datetime.strptime(self.start_time,"%d/%m/%Y %H:%M:%S.%f")
            end_time=datetime.strptime(self.end_time,"%d/%m/%Y %H:%M:%S.%f")
            self.filtered_num_lines=0
            dataReached=False
            fileType = "sx10"

            gps_data_file=open(self.section_file)

            for line in gps_data_file:
                if line.startswith("File"):     #First line, grab start date
                    self.vbox_start_date=line.split()[3]
                
                #Check if SX10 file or touch file
                if line.startswith("Type"):
                    fileType="touch"

                self.model=fileType
                
                if line.startswith("Serial") and fileType == "sx10":     #Serials line, add to serial list
                    serial=line.split()[3].lstrip('0')
                    if serial not in self.serials:
                        self.serials.append(serial)

                elif line.startswith("Serial") and fileType == "touch":
                    serial=line.split()[2].lstrip('0')
                    if serial not in self.serials:
                        self.serials.append(serial)

                #Determine if mph or kph
                if line.startswith("velocity mph"):
                    self.speed_units="mph"
                elif line.startswith("velocity kmh"):                
                    self.speed_units="kmh"

                if dataReached and fileType == "touch":
                    if self.start_time != None and self.end_time != None:
                        vbox_datetime=datetime.strptime(self.vbox_start_date + " " + line.split()[1],"%d/%m/%Y %H%M%S.%f")
                        if vbox_datetime >= start_time and vbox_datetime <= end_time:
                            self.process_vbox_line(line)
                            self.vbo_filtered_data+=line

                    else:
                        self.process_vbox_line(line)
                        self.vbo_filtered_data+=line
                else:
                    self.vbo_filtered_data+=line

                if line.startswith("[data]"):   #Vbox Data reached
                    dataReached=True

            gps_data_file.close()


        except Exception as e:
            print(e)

    def process_vbox_line(self,line):
        firstDataLine=True

        gpsDataLine = line.split()

        #Filter out satellite 0
        if int(gpsDataLine[0]) > 0:

            #Ignore midnight
            if not "240000" in line[1]:
                #Combine Vbox Date and gps point time
                if len(gpsDataLine[1]) == 9:
                    gpsDataLine[1] = gpsDataLine[1] + "0"

                gpsDateTimeString = self.vbox_start_date + " " + gpsDataLine[1]

                #Convert DateTime to a datetime
                utc_time = datetime.strptime(gpsDateTimeString, "%d/%m/%Y %H%M%S.%f")

                #If its not the first data line (i.e Vbox didnt start at midnight) and data crosses midnight then add a day
                if not firstDataLine and line[1].startswith("000000.10"):
                    #Add day
                    utc_time = utc_time + timedelta(days=1)

                #Add configured time offset (in hours)
                #utc_time = utc_time + timedelta(hours=TimeOffset)
                utc_time = utc_time + timedelta(hours=int(time_offset))
                
                #Convert to epoch in ms
                epochTime = (utc_time - datetime(1970, 1, 1)).total_seconds()*1000
                #Subtract the GPS leap seconds  
                epochTime = int(epochTime) - (int(leap_seconds)*1000)

                #Convert speed units to mph
                if self.speed_units=="kmh":
                    speed=float(gpsDataLine[4])/1.609344
                    gpsDataLine[4]=str(speed)

                self.add_gps_point(gpsDataLine[0],epochTime, utc_time, gpsDataLine[2], gpsDataLine[3], gpsDataLine[4])

                firstDataLine=False


class ProcessSectionData(QtCore.QThread):
    section_data_processing_finished = pyqtSignal(dict)
    section_processing_error_occurred = pyqtSignal(str)
    update_section_processing_progress = pyqtSignal(dict)
        
    def __init__(self,section_data:list,id_col,gps_filename_col,start_time_col,end_time_col):
        super().__init__()
        self.section_data=section_data
        self.id_col=id_col
        self.gps_filename_col=gps_filename_col
        self.start_time_col=start_time_col
        self.end_time_col=end_time_col
        self.section_data_objects={}

    def run(self):
        try:
            self.section_count=len(self.section_data)
            self.current_progress=0

            for section in self.section_data:
                self.uid=section[self.id_col]

                current_progress_percentage=int((self.current_progress/self.section_count)*100)
                self.update_section_processing_progress.emit({"progress":current_progress_percentage, "message":f"Processing Section {self.uid}"})

                self.file=section[self.gps_filename_col]
                self.start_time=section[self.start_time_col]
                self.end_time=section[self.end_time_col]

                self.section_data_objects[self.uid]=SectionData(self, self.uid, self.file,self.start_time,self.end_time)
                self.section_data_objects[self.uid].process_gps_data()

                self.current_progress+=1

            self.section_data_processing_finished.emit(self.section_data_objects)


        except Exception as e:
            print(e)
            self.section_processing_error_occurred.emit(str(e))

