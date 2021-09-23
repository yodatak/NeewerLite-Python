#############################################################
## Neewer-PyLite
## by Zach Glenwright
##   > https://github.com/taburineagle/Neewer-PythonLite <
#############################################################
## Based on the NeewerLight project by @keefo (Xu Lian)
##   > https://github.com/keefo/NeewerLite <
#############################################################
## Animation parameters:
#############################################################
## 1 - Emergency Mode A (Police Sirens)
## 2 - Emergency Mode B (One color?)
## 3 - Emergency Mode C (Ambulance)
## 4 - Party Mode A (Alternating colors)
## 5 - Party Mode B (Same as above, but faster)
## 6 - Party Mode C (Candle-light)
## 7 - Lightning Mode A
## 8 - Lightning Mode B
## 9 - Lightning Mode C
#############################################################
## Bytestring layout for Neewer light protocol
#############################################################
##              pfx   mode # of bytes in command
##              ----  ---  -
## (integers) = [120, 134, 4, 0, 0, 0, 0, 0]
##      (hex) = 0x78 0x86 - HSL mode
##                   0x87 - CCT mode
##                   0x88 - ANM mode
##                           ------------ -
##                           data payload checksum
#############################################################

import sys

try:
    from winrt import _winrt
    _winrt.uninit_apartment()
except Exception as e:
    pass # if there is an exception to this module loading, you're not on Windows

import asyncio
from bleak import BleakScanner, BleakClient
from PySide2.QtWidgets import QApplication, QMainWindow
from ui_NeewerLightUI import Ui_MainWindow

sendValue = "" # an array to hold the values to be sent to the light - default to CCT, 5600K, 100%
lastAnimButtonPressed = 1 # which animation button you clicked last - if none, then it defaults to 1 (the police sirens)
availableLights = []

setLightUUID = "69400002-B5A3-F393-E0A9-E50E24DCCA99"

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.connectMe()
        self.computeValueCCT()
        self.show

    def connectMe(self):
        self.sendCommandButton.clicked.connect(lambda: startSend(self.lightSelectorCombo.currentIndex()))
        self.scanCommandButton.clicked.connect(self.startSelfSearch)
        
        self.ColorModeTabWidget.currentChanged.connect(self.autoComputeValue)

        self.Slider_CCT_Hue.valueChanged.connect(self.computeValueCCT)
        self.Slider_CCT_Bright.valueChanged.connect(self.computeValueCCT)

        self.Slider_HSL_1_H.valueChanged.connect(self.computeValueHSL)
        self.Slider_HSL_2_S.valueChanged.connect(self.computeValueHSL)
        self.Slider_HSL_3_L.valueChanged.connect(self.computeValueHSL)

        self.Slider_ANM_Brightness.valueChanged.connect(lambda x: self.computeValueANM(0))
        self.Button_1_police_A.clicked.connect(lambda x: self.computeValueANM(1))
        self.Button_1_police_B.clicked.connect(lambda x: self.computeValueANM(2))
        self.Button_1_police_C.clicked.connect(lambda x: self.computeValueANM(3))
        self.Button_2_party_A.clicked.connect(lambda x: self.computeValueANM(4))
        self.Button_2_party_B.clicked.connect(lambda x: self.computeValueANM(5))
        self.Button_2_party_C.clicked.connect(lambda x: self.computeValueANM(6))
        self.Button_3_lightning_A.clicked.connect(lambda x: self.computeValueANM(7))
        self.Button_3_lightning_B.clicked.connect(lambda x: self.computeValueANM(8))
        self.Button_3_lightning_C.clicked.connect(lambda x: self.computeValueANM(9))

    def autoComputeValue(self, i):
        if i == 0:
        	self.computeValueCCT() # calculate the current CCT value
        elif i == 1:
        	self.computeValueHSL() # calculate the current HSL value
        elif i == 2:
        	self.computeValueANM(lastAnimButtonPressed) # calculate the current ANM value, based on the last button pressed

    def computeValueCCT(self):
        self.TFV_CCT_Hue.setText(str(self.Slider_CCT_Hue.value()) + "00K")
        
        calculateByteString(colorMode="CCT",\
                            temp=str(int(self.Slider_CCT_Hue.value())),\
                            brightness=str(int(self.Slider_CCT_Bright.value())))

        self.statusBar.showMessage("Current value (CCT Mode): " + updateStatus())

    def computeValueHSL(self):
        calculateByteString(colorMode="HSL",\
                            HSL_H=str(int(self.Slider_HSL_1_H.value())),\
                            HSL_S=str(int(self.Slider_HSL_2_S.value())),\
                            HSL_L=str(int(self.Slider_HSL_3_L.value())))

        self.statusBar.showMessage("Current value (HSL Mode): " + updateStatus())

    def computeValueANM(self, buttonPressed):
        global lastAnimButtonPressed

        if buttonPressed == 0:
            buttonPressed = lastAnimButtonPressed
        else:
            # CHANGE THE OLD BUTTON COLOR BACK TO THE DEFAULT COLOR
            if lastAnimButtonPressed == 1:
                self.Button_1_police_A.setStyleSheet("background-color : None")
            elif lastAnimButtonPressed == 2:
                self.Button_1_police_B.setStyleSheet("background-color : None")
            elif lastAnimButtonPressed == 3:
                self.Button_1_police_C.setStyleSheet("background-color : None")
            elif lastAnimButtonPressed == 4:
                self.Button_2_party_A.setStyleSheet("background-color : None")
            elif lastAnimButtonPressed == 5:
                self.Button_2_party_B.setStyleSheet("background-color : None")
            elif lastAnimButtonPressed == 6:    
                self.Button_2_party_C.setStyleSheet("background-color : None")
            elif lastAnimButtonPressed == 7:
                self.Button_3_lightning_A.setStyleSheet("background-color : None")
            elif lastAnimButtonPressed == 8:
                self.Button_3_lightning_B.setStyleSheet("background-color : None")
            elif lastAnimButtonPressed == 9:
                self.Button_3_lightning_C.setStyleSheet("background-color : None")
                
            # CHANGE THE NEW BUTTON COLOR TO GREEN TO SHOW WHICH ANIMATION WE'RE CURRENTLY ON
            if buttonPressed == 1:
                self.Button_1_police_A.setStyleSheet("background-color : aquamarine")
            elif buttonPressed == 2:
                self.Button_1_police_B.setStyleSheet("background-color : aquamarine")
            elif buttonPressed == 3:
                self.Button_1_police_C.setStyleSheet("background-color : aquamarine")
            elif buttonPressed == 4:
                self.Button_2_party_A.setStyleSheet("background-color : aquamarine")
            elif buttonPressed == 5:
                self.Button_2_party_B.setStyleSheet("background-color : aquamarine")
            elif buttonPressed == 6:    
                self.Button_2_party_C.setStyleSheet("background-color : aquamarine")
            elif buttonPressed == 7:
                self.Button_3_lightning_A.setStyleSheet("background-color : aquamarine")
            elif buttonPressed == 8:
                self.Button_3_lightning_B.setStyleSheet("background-color : aquamarine")
            elif buttonPressed == 9:
                self.Button_3_lightning_C.setStyleSheet("background-color : aquamarine")
            
            lastAnimButtonPressed = buttonPressed

        calculateByteString(colorMode="ANM",\
                            brightness=str(int(self.Slider_ANM_Brightness.value())),\
                            animation=str(buttonPressed))

        self.statusBar.showMessage("Current value (ANM Mode): " + updateStatus())

    def startSelfSearch(self):
        startSearch()

        self.lightSelectorCombo.clear()

        if len(availableLights) == 0: # if we return no results, then don't allow sending commands
            self.sendCommandButton.setEnabled(False)
        else:
            self.sendCommandButton.setEnabled(True)

        for a in availableLights:
            self.lightSelectorCombo.addItem(a.address + " (" + a.name + ")")

def updateStatus():
    currentHexString = ""

    for a in range(0, len(sendValue)):
        currentHexString = currentHexString + " " + str(hex(sendValue[a]))

    return currentHexString

def calculateByteString(**modeArgs):
    global sendValue

    if modeArgs["colorMode"] == "CCT":
        # We're in CCT (color balance) mode
        sendValue = [120, 135, 2, 0, 0, 0]

        sendValue[3] = int(modeArgs["brightness"]) # the brightness value
        sendValue[4] = int(modeArgs["temp"]) # the color temp value, ranging from 32(00K) to 56(00)K
        sendValue[5] = calculateChecksum(sendValue) # compute the checksum
    elif modeArgs["colorMode"] == "HSL":
        # We're in HSL (any color of the spectrum) mode
        sendValue = [120, 134, 4, 0, 0, 0, 0, 0]

        sendValue[3] = int(modeArgs["HSL_H"]) & 255 # hue value, up to 255
        sendValue[4] = (int(modeArgs["HSL_H"]) & 65280) >> 8 # offset value, computed from above value
        sendValue[5] = int(modeArgs["HSL_S"]) # saturation value
        sendValue[6] = int(modeArgs["HSL_L"]) # brightness value
        sendValue[7] = calculateChecksum(sendValue) # compute the checksum
    elif modeArgs["colorMode"] == "ANM":
        # We're in ANM (animation) mode
        sendValue = [120, 136, 2, 0, 0, 0]

        sendValue[3] = int(modeArgs["brightness"]) # brightness value
        sendValue[4] = int(modeArgs["animation"]) # the number of animation you're going to run (check comments above)
        sendValue[5] = calculateChecksum(sendValue) # compute the checksum
    else:
        sendValue = [0]

def calculateChecksum(sendValue):
    checkSum = 0

    for a in range(0, len(sendValue) - 1):
        if sendValue[a] < 0:
            checkSum = checkSum + int(sendValue[a] + 256)
        else:
            checkSum = checkSum + int(sendValue[a])

    checkSum = checkSum & 255
    return checkSum

def startSearch():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(findDevices())

def startSend(selectedLight):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(sendCommand(selectedLight))

async def findDevices():
    global availableLights

    availableLights = []
    devices = await BleakScanner.discover()

    for d in devices:
        try:
            d.name.index("NEEWER")
        except ValueError:
            pass
        else:
            availableLights.append(d)

async def sendCommand(selectedLight):
    client = BleakClient(availableLights[selectedLight])

    try:
        if not client.is_connected:
            await client.connect()
        else:
            print("Device is already connected")
    except Exception as e:
        print("There was an error trying to connect")
        print(e)

    try:
        await client.write_gatt_char(setLightUUID, bytearray(sendValue), False)
    except Exception as e:
        print("There was an error communicating with the light.")
        print(e)
    finally:
        await client.disconnect()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    ret = app.exec_()
    sys.exit( ret )
