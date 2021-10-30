# -*- coding: utf-8 -*-
"""
Created on Sat Oct 30 09:31:13 2021

@author: Barun
"""
from WeatherSensor import UMBError, WS_UMB

from PyQt5.uic import loadUi
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QDialog, QApplication, QWidget

import time, struct, sys
import serial.tools.list_ports

#temp[degC], rel. humidity[%], rel. air pressure[hpa], wind speed[m/s], wind direction[deg]
#MinMax = ['120', '140', '220', '240', '325', '345', '420', '440', '520', '540']
Channels = ['100', '200', '305', '400', '500']


class WelcomeScreen(QDialog):
    def __init__(self):
        super(WelcomeScreen, self).__init__()
        loadUi("main.ui", self)
        self.pushButton.clicked.connect(self.port_select)
        
        self.pushButton_2.clicked.connect(self.savedata)
        self.pushButton_3.clicked.connect(self.exit_program)    
        
    
    def exit_program(self):
        sys.exit(0)
        
    def port_select(self):
        for i in serial.tools.list_ports.comports():
            self.comboBox.addItems(i)
            self.COM_Port = str(self.comboBox.currentText())
            return self.COM_Port
            
    def savedata(self):
        self.worker = WorkerThread()
        self.worker.start()
        #self.worker.finished.connect(self.evt_worker_finished)
    
    def evt_worker_finished(self):
        QtWidgets.QMessageBox.information(self, "Done", "Worker Thread complete")

import csv

def getdata():
    weatherData = []
    with WS_UMB() as umb:
        for channel in Channels:
            if 100 <= int(channel) <= 29999:
                value, status = umb.onlineDataQuery(channel)
                if status == 0:
                    weatherData.append(value)
    return weatherData 

def file_save():
    file = 'DataOutput.csv' ## Windows Python3   
    with open(file, 'a', newline='') as f:
        writer = csv.writer(f)
        try:
            writer.writerow(getdata())
            #print(getdata())
        except KeyboardInterrupt:
            print("Keyboard Interrupt")
        except:
            print("Other exception")
    

class WorkerThread(QtCore.QThread):
    def run(self):
        while True:
            file_save()
            time.sleep(5)
            
       
if __name__ == "__main__":
    app = QApplication(sys.argv)   
    welcome = WelcomeScreen()
    widget = QtWidgets.QStackedWidget()
    widget.setWindowTitle("UMB")
    widget.addWidget(welcome)
    widget.show()
    sys.exit(app.exec_())