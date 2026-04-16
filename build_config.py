import os
import sys

bundledExe=False

#Check if bundled exe or development environment
resourcesPath=os.getcwd()

if getattr(sys, 'frozen', False):
    #Bundled exe
    applicationPath = sys._MEIPASS
    bundledExe=True
else:
    #Development environment
    applicationPath = os.path.dirname(os.path.abspath(__file__))
    bundledExe=False
