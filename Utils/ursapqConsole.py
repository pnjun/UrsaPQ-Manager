import sys
import os
import time
from ursapqUtils import UrsaPQ
from ursapqConsoleResources.switch import Switch
from ursapqConsoleResources.config import config

from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QPushButton, QLineEdit
from PySide2.QtCore import QFile, QObject, QTimer, Slot, QEvent

UI_BASEPATH = '/ursapqConsoleResources/'
#style
BG_COLOR_OK = 'background-color: #4CBB17;'
BG_COLOR_WARNING = 'background-color: #F9A602;'
BG_COLOR_ERROR = 'background-color: #DF2800;'
BG_COLOR_OFF = 'background-color: #808080;'
BG_COLOR_WHITE = 'background-color: #FFFFFF;'

class ConsoleWindow(QObject):
    '''
    Generic consloe window loaded from ui file. Automatically starts a QTimer
    calling self.update() repeatedly. The timer is deleted when the window is
    closed.
    The update and setupcallbacks should be overridden by child classes
    '''

    def __init__(self, uifilename, updateTime = 500):
        super(ConsoleWindow, self).__init__(None)
        self.updateTime = updateTime
        self.uifilename = uifilename

        self.loadUi()

        self.updateTimer = QTimer()
        self.updateTimer.timeout.connect(self.update)
        self.updateTimer.start(self.updateTime)

    def loadUi(self):
        local_dir = os.path.dirname(os.path.abspath(__file__))
        self.window = QUiLoader().load( QFile(local_dir + UI_BASEPATH + self.uifilename) )
        self.window.installEventFilter(self)
        self.window.show()

    def eventFilter(self, obj, event):
        if obj is self.window and event.type() == QEvent.Close:
            try:
                del self.updateTimer
            except AttributeError:
                pass
        return False

    def update(self):
        pass

    def close(self):
        self.window.close()

class VacuumWindow(ConsoleWindow):
    def __init__(self, ursapq, *args, **kvargs):
        super(VacuumWindow, self).__init__('vacuum.ui', *args, **kvargs)
        self.ursapq = ursapq
        self.prevacValveLock = Switch(thumb_radius=11, track_radius=8)
        self.pumpsEnable = Switch(thumb_radius=11, track_radius=8)
        self.window.prevacValveLockBox.addWidget(self.prevacValveLock)
        self.window.pumpsEnableBox.addWidget(self.pumpsEnable)
        self.setupCallbacks()

    def setupCallbacks(self):
        self.prevacValveLock.clicked.connect(self.preVacValve_lock)
        self.pumpsEnable.clicked.connect(self.enablePumps)

    def update(self):
        self.prevacValveLock.setChecked( self.ursapq.preVacValve_lock )
        self.pumpsEnable.setChecked( self.ursapq.pumps_enable )

    #Callbacks:
    @Slot()
    def preVacValve_lock(self):
        self.ursapq.preVacValve_lock = self.prevacValveLock.isChecked()

    @Slot()
    def enablePumps(self):
        self.ursapq.pumps_enable = self.pumpsEnable.isChecked()

class SampleWindow(ConsoleWindow):
    def __init__(self, ursapq, *args, **kvargs):
        super(SampleWindow, self).__init__('sample.ui', *args, **kvargs)
        self.enableSwitch = Switch(thumb_radius=11, track_radius=8)
        self.window.ovenEnableBox.addWidget(self.enableSwitch)
        self.ursapq = ursapq
        self.setupCallbacks()

    def setupCallbacks(self):
        self.enableSwitch.clicked.connect(self.oven_enable)
        self.window.setPointsButton.clicked.connect(self.newSetPoints)

    def update(self):
        self.enableSwitch.setChecked( self.ursapq.oven_enable )
        self.window.capPow.setText(  '{:.2f}'.format(self.ursapq.oven_capPow))
        self.window.tipPow.setText(  '{:.2f}'.format(self.ursapq.oven_tipPow))
        self.window.bodyPow.setText( '{:.2f}'.format(self.ursapq.oven_bodyPow))
        self.window.bodySetPoint.setText('{:.1f}'.format(self.ursapq.oven_bodySetPoint))
        self.window.tipSetPoint.setText('{:.1f}'.format(self.ursapq.oven_tipSetPoint))
        self.window.capSetPoint.setText('{:.1f}'.format(self.ursapq.oven_capSetPoint))

    #Callbacks:
    @Slot()
    def oven_enable(self):
        self.ursapq.oven_enable = self.enableSwitch.isChecked()

    @Slot()
    def newSetPoints(self):
        try:
            self.ursapq.oven_bodySetPoint = float( self.window.bodySetPoint_in.toPlainText() )
        except Exception:
            pass
        try:
            self.ursapq.oven_tipSetPoint = float( self.window.tipSetPoint_in.toPlainText() )
        except Exception:
            pass
        try:
            self.ursapq.oven_capSetPoint = float( self.window.capSetPoint_in.toPlainText() )
        except Exception:
            pass

class SpectrometerWindow(ConsoleWindow):
    def __init__(self, ursapq, *args, **kvargs):
        super(SpectrometerWindow, self).__init__('spectrometer.ui', *args, **kvargs)
        self.mcpEnableSwitch = Switch(thumb_radius=11, track_radius=8)
        self.tofEnableSwitch = Switch(thumb_radius=11, track_radius=8)
        self.coilEnableSwitch = Switch(thumb_radius=11, track_radius=8)
        self.window.mcpEnableBox.addWidget(self.mcpEnableSwitch)
        self.window.tofEnableBox.addWidget(self.tofEnableSwitch)
        self.window.coilEnableBox.addWidget(self.coilEnableSwitch)
        self.ursapq = ursapq
        self.setupCallbacks()

        self.resetTimer = False

    def setupCallbacks(self):
        self.mcpEnableSwitch.clicked.connect(self.mcpEnable)
        self.tofEnableSwitch.clicked.connect(self.tofEnable)
        self.coilEnableSwitch.clicked.connect(self.coilEnable)
        self.window.mcpSetButton.clicked.connect(self.mcpSet)
        self.window.tofSetButton.clicked.connect(self.tofSet)

    def update(self):
        self.mcpEnableSwitch.setChecked( self.ursapq.mcp_hvEnable )
        self.tofEnableSwitch.setChecked( self.ursapq.tof_hvEnable )
        self.window.mcpFront_act.setText(  '{:.1f}'.format(self.ursapq.mcp_frontHV))
        self.window.mcpBack_act.setText(   '{:.1f}'.format(self.ursapq.mcp_backHV))
        self.window.mcpPhos_act.setText(   '{:.1f}'.format(self.ursapq.mcp_phosphorHV))
        self.window.mcpFront_set.setText(  '{:.1f}'.format(self.ursapq.mcp_frontSetHV))
        self.window.mcpBack_set.setText(   '{:.1f}'.format(self.ursapq.mcp_backSetHV))
        self.window.mcpPhos_set.setText(   '{:.1f}'.format(self.ursapq.mcp_phosphorSetHV))

        self.window.tofMesh_act.setText(     '{:.1f}'.format(self.ursapq.tof_meshHV))
        self.window.tofRetarder_act.setText( '{:.1f}'.format(self.ursapq.tof_retarderHV))
        self.window.tofLens_act.setText(     '{:.1f}'.format(self.ursapq.tof_lensHV))
        self.window.tofMagnet_act.setText(   '{:.1f}'.format(self.ursapq.tof_magnetHV))
        self.window.tofMesh_set.setText(     '{:.1f}'.format(self.ursapq.tof_meshSetHV))
        self.window.tofRetarder_set.setText( '{:.1f}'.format(self.ursapq.tof_retarderSetHV))
        self.window.tofLens_set.setText(     '{:.1f}'.format(self.ursapq.tof_lensSetHV))
        self.window.tofMagnet_set.setText(   '{:.1f}'.format(self.ursapq.tof_magnetSetHV))

        if self.resetTimer:
            self.updateTimer.setInterval( self.updateTime )

    #Callbacks:
    @Slot()
    def mcpEnable(self):
        self.ursapq.mcp_hvEnable = self.mcpEnableSwitch.isChecked()
        #Prolong next update cycle so that server has time to process the enable request
        #Update func will set update interval back to normal
        self.updateTimer.setInterval(self.updateTime*3)
        self.resetTimer = True

    @Slot()
    def tofEnable(self):
        self.ursapq.tof_hvEnable = self.tofEnableSwitch.isChecked()
        #Prolong next update cycle so that server has time to process the enable request
        #Update func will set update interval back to normal
        self.updateTimer.setInterval(self.updateTime*3)
        self.resetTimer = True

    @Slot()
    def coilEnable(self):
        pass

    @Slot()
    def mcpSet(self):
        try:
            self.ursapq.mcp_frontSetHV = float( self.window.mcpFront_in.toPlainText() )
        except Exception:
            pass
        try:
            self.ursapq.mcp_backSetHV = float( self.window.mcpBack_in.toPlainText() )
        except Exception:
            pass
        try:
            self.ursapq.mcp_phosphorSetHV = float( self.window.mcpPhos_in.toPlainText() )
        except Exception:
            pass

    @Slot()
    def tofSet(self):
        try:
            self.ursapq.tof_meshSetHV = float( self.window.tofMesh_in.toPlainText() )
        except Exception:
            pass
        try:
            self.ursapq.tof_retarderSetHV = float( self.window.tofRetarder_in.toPlainText() )
        except Exception:
            pass
        try:
            self.ursapq.tof_lensSetHV = float( self.window.tofLens_in.toPlainText() )
        except Exception:
            pass
        try:
            self.ursapq.tof_magnetSetHV = float( self.window.tofMagnet_in.toPlainText() )
        except Exception:
            pass

class MainWindow(ConsoleWindow):
    def __init__(self, *args, **kvargs):
        super(MainWindow, self).__init__('main.ui', *args, **kvargs)
        self.ursapq = None
        self.sampleWindow = None
        self.spectrWindow = None
        self.vacuumWindow = None

        self.setupCallbacks()

        self.window.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.window and event.type() == QEvent.Close:
            self.closeChildWindows()
        return super(MainWindow, self).eventFilter(obj, event)

    def setupCallbacks(self):
        self.window.sample_MB.clicked.connect(self.showSample)
        self.window.vacuum_MB.clicked.connect(self.showVacuum)
        self.window.spectr_MB.clicked.connect(self.showSpectrometer)
        pass

    def updateVacuum(self):
        #VACUUM BOX
        self.window.prevacPressure.setText(  '{:.2e}'.format(self.ursapq.preVacPressure) )
        self.window.chamberPressure.setText( '{:.2e}'.format(self.ursapq.chamberPressure) )
        self.window.prevacValves.setText( '{} ({})'.format(
                                           "Open" if self.ursapq.preVacValve_isOpen else "Closed",
                                           "Locked" if self.ursapq.preVacValve_lock else "Auto" ))
        self.window.pumpStatus.setText(  '{} ({})'.format(
                                           "Running" if self.ursapq.pumps_areON else "Stopped",
                                           "Auto" if self.ursapq.pumps_enable else "Locked" ))
        #Update status label
        if self.ursapq.preVac_OK:
            self.window.vacuum_SL.setStyleSheet(BG_COLOR_WARNING)
        else:
            if self.ursapq.pumps_enable:
                self.window.vacuum_SL.setStyleSheet(BG_COLOR_ERROR)
            else:
                self.window.vacuum_SL.setStyleSheet(BG_COLOR_OK)

        if self.ursapq.preVac_OK and self.ursapq.mainVac_OK:
            self.window.vacuum_SL.setStyleSheet(BG_COLOR_OK)

    def updateSample(self):
        self.window.bodyTemp.setText( '{:.1f}'.format(self.ursapq.sample_bodyTemp) )
        self.window.capTemp.setText(  '{:.1f}'.format(self.ursapq.sample_capTemp) )
        self.window.tipTemp.setText(  '{:.1f}'.format(self.ursapq.sample_tipTemp) )

        #Update status label
        self.window.ovenStatus.setText(self.ursapq.oven_PIDStatus)

        if self.ursapq.oven_PIDStatus == "OK":
            self.window.sample_SL.setStyleSheet(BG_COLOR_OK)
        elif self.ursapq.oven_PIDStatus == "TRACKING":
            self.window.sample_SL.setStyleSheet(BG_COLOR_WARNING)
        elif self.ursapq.oven_PIDStatus == "OFF":
            self.window.sample_SL.setStyleSheet(BG_COLOR_OFF)
        else:
            self.window.sample_SL.setStyleSheet(BG_COLOR_ERROR)

    def updateSpectrometer(self):
        self.window.mcpFront_act.setText( '{:.1f}'.format(self.ursapq.mcp_frontHV))
        self.window.mcpBack_act.setText(  '{:.1f}'.format(self.ursapq.mcp_backHV))
        self.window.mcpPhos_act.setText(  '{:.1f}'.format(self.ursapq.mcp_phosphorHV))
        self.window.magnet_temp.setText(  '{:.1f}'.format(self.ursapq.magnet_temp))

        if self.ursapq.HV_Status == 'OFF':
            self.window.detector_SL.setStyleSheet(BG_COLOR_OFF)
        elif self.ursapq.HV_Status == 'WARNING':
            self.window.detector_SL.setStyleSheet(BG_COLOR_WARNING)
        elif self.ursapq.HV_Status == 'OK':
            self.window.detector_SL.setStyleSheet(BG_COLOR_OK)
        else:
            self.window.detector_SL.setStyleSheet(BG_COLOR_ERROR)

    def connect(self):
        self.ursapq = UrsaPQ(  config.UrsapqServer_IP ,
                               config.UrsapqServer_Port ,
                               config.UrsapqServer_AuthKey.encode('ascii'))

    def update(self):
        try:
            self.updateVacuum()
            self.updateSample()
            self.updateSpectrometer()
        except Exception as e:
            try:
                self.connect()
            except Exception:
                self.closeChildWindows()

            self.window.statusBar().setStyleSheet(BG_COLOR_ERROR)
            statusbar = "NOT CONNECTED - Attempting connection to: %s:%d" % (config.UrsapqServer_IP, config.UrsapqServer_Port)
        else:
            lastStatusMessage = self.ursapq.lastStatusMessage.strftime("%H:%M:%S")
            message = lastStatusMessage + " - " + self.ursapq.statusMessage
            update =  'Last update: %s' % self.ursapq.lastUpdate.strftime("%d-%m-%y %H:%M:%S")
            statusbar = update + " | " + message
            self.window.statusBar().setStyleSheet(BG_COLOR_WHITE)

        self.window.statusBar().showMessage(statusbar)

    def closeChildWindows(self):
        if self.sampleWindow:
            self.sampleWindow.close()
            self.sampleWindow = None
        if self.spectrWindow:
            self.spectrWindow.close()
            self.spectrWindow = None
        if self.vacuumWindow:
            self.vacuumWindow.close()
            self.vacuumWindow = None

    #Callbacks:
    @Slot()
    def showSample(self):
        self.sampleWindow = SampleWindow(self.ursapq)
    @Slot()
    def showVacuum(self):
        self.vacuumWindow = VacuumWindow(self.ursapq)
    @Slot()
    def showSpectrometer(self):
        self.spectrWindow = SpectrometerWindow(self.ursapq)

def main():
    app = QApplication(sys.argv)
    ui = MainWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
