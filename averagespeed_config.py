import xml.etree.ElementTree as ET

class AverageSpeedConfig:
    def __init__(self):
        super().__init__()
        self.configFile=""
        self.siteData=[]
        self.linkData=[]
        self.baselineData=[]

    def importConfig(self,xmlFile):
        self.configFile=xmlFile
        try:
            tree = ET.parse(self.configFile)
            self.root = tree.getroot()
            self.parseSiteData()
            self.parseLinkData()
            self.parseBaselineData()
        except Exception as e:
            print("An error occurred processing config data - " + str(e))
            return False

    def parseSiteData(self):
        #List format & usage example
        #sites =[{"siteName":"1","location":"location","cameras":[{"cameraId":"1","serial":"2"},{"cameraId":"2","serial":"3"}]}, \
        #        {"siteName":"2","location":"location","cameras":[{"cameraId":"1","serial":"2"},{"cameraId":"2","serial":"3"}]}]
        #for site in sites:
        #    print(site['siteName'])
        #    for camera in site['cameras']:
        #        print(camera)
        self.siteData=[]
        for tag in self.root.findall('Site'):
            site={}
            site["siteName"]=(tag.get('Name'))
            site["siteLocation"]=(tag.get('Camera_Location'))
            cameras=[]
            for element in tag:
                if element.tag == "Camera":
                    camera={}
                    camera["cameraId"]=(element.get('Id'))
                    camera["serial"]=(element.get('Serial'))
                    for item in element:
                        if item.tag == "IP_Address":
                            camera["ipAddress"]=item.text
                        elif item.tag == "Netmask":
                            camera["netmask"]=item.text
                        elif item.tag == "Gateway":
                            camera["gateway"]=item.text
                        elif item.tag == "Instation_IP":
                            camera["instationIP"]=item.text
                        elif item.tag == "Short_Name":
                            camera["shortName"]=item.text
                        elif item.tag == "Height":
                            camera["height"]=item.text
                        elif item.tag == "Skew":
                            camera["skew"]=item.text
                        elif item.tag == "DistanceD":
                            camera["distanceD"]=item.text
                    cameras.append(camera)
                if element.tag == "Instation":
                    instation={}
                    instation["serial"]=(element.get('Serial'))
                    for item in element:
                        if item.tag == "IP_Address":
                            instation["ipAddress"]=item.text


            site["cameras"]=cameras
            site["instation"]=instation
            self.siteData.append(site)

    def parseLinkData(self):
        #List format & usage example
        #links =[{"linkId":"1","From_Site":"2","To_Site":"3","Certificate_Part_Number":"2","Certificate_Issue":"2"}, \
        #        {"linkId":"2","From_Site":"2","To_Site":"3","Certificate_Part_Number":"2","Certificate_Issue":"2"}]
        #for link in links:
        #    print(link['linkId'])
        self.linkData=[]
        for tag in self.root.findall('Links'):
            for element in tag:
                link={}
                link["linkId"]=(element.get('Id'))
                for item in element:
                    if item.tag == "From_Site":
                        link["fromSite"]=item.text
                    elif item.tag == "To_Site":
                        link["toSite"]=item.text
                    elif item.tag == "Certificate_Part_Number":
                        link["certificatePartNumber"]=item.text
                    elif item.tag == "Certificate_Issue":
                        link["certificateIssue"]=item.text
                self.linkData.append(link)
    
    def parseBaselineData(self):
        #List format & usage example
        #baselines =[{"baselineId":"1","fromCamera":"2","toCamera":"3","fromSite":"2","toSite":"2","minDistance":"2","calibrationEquipmentType":"2","calibrationEquipmentSerial":"2","certificatePartNumber":"2","certificateIssue":"2"}, \
        #            {"baselineId":"2","fromCamera":"2","toCamera":"3","fromSite":"2","toSite":"2","minDistance":"2","calibrationEquipmentType":"2","calibrationEquipmentSerial":"2","certificatePartNumber":"2","certificateIssue":"2"}]
        #for baseline in baselines:
        #    print(baseline['baselineId'])
        self.baselineData=[]
        for tag in self.root.findall('Baselines'):
            for element in tag:
                baseline={}
                baseline["baselineId"]=(element.get('Id'))
                for item in element:
                    if item.tag == "From_Camera":
                        baseline["fromCamera"]=item.text
                    elif item.tag == "To_Camera":
                        baseline["toCamera"]=item.text
                    elif item.tag == "From_Site":
                        baseline["fromSite"]=item.text
                    elif item.tag == "To_Site":
                        baseline["toSite"]=item.text
                    elif item.tag == "Min_Distance":
                        baseline["minDistance"]=item.text
                    elif item.tag == "Calibration_Equipment_Type":
                        baseline["calibrationEquipmentType"]=item.text
                    elif item.tag == "Calibration_Equipment_Serial":
                        baseline["calibrationEquipmentSerial"]=item.text
                    elif item.tag == "Calibration_Equipment_Antenna_Serial":
                        baseline["calibrationEquipmentAntennaSerial"]=item.text
                    elif item.tag == "Certificate_Part_Number":
                        baseline["certificatePartNumber"]=item.text
                    elif item.tag == "Certificate_Issue":
                        baseline["certificateIssue"]=item.text
                self.baselineData.append(baseline)

    def getLinkDetailsFromConfig(self,fromSite,toSite):
        linkId=""
        certPartNumber=""
        certIssue=""
        for link in self.linkData:
            if link['fromSite'] == fromSite and link['toSite'] == toSite:
                linkId=link['linkId']
                certPartNumber=link['certificatePartNumber']
                certIssue=link['certificateIssue']
        return linkId,certPartNumber,certIssue

    def isCameraInConfig(self,cameraId):
        isCameraInConfig=False
        for site in self.siteData:
            for camera in site['cameras']:
                if cameraId == camera['cameraId']:
                    isCameraInConfig=True
        return isCameraInConfig
    
    def getCameraDetailsFromConfig(self,siteName):
        cameraIds=""
        serialNumbers=""
        location=""
        for site in self.siteData:
            if site['siteName'] == siteName:
                location=site['siteLocation']
                for camera in site['cameras']:
                    if not len(cameraIds):
                        cameraIds=camera['cameraId']
                    else:
                        cameraIds=cameraIds+", " + camera['cameraId']
                    if not len(serialNumbers):
                        serialNumbers=camera['serial']
                    else:
                        serialNumbers=serialNumbers+", " + camera['serial']

        return location,cameraIds, serialNumbers

    def getInstationDetails(self,siteName):
        serial=""
        ipAddress=""
        for site in self.siteData:
            if site['siteName'] == siteName:
                serial=site['instation']['serial']
                ipAddress=site['instation']['ipAddress']
        return serial,ipAddress
