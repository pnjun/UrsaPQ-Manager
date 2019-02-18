import sys
import os
from ursapqUtils import UrsaPQ
from ursapqConsole import Switch

from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QPushButton, QLineEdit
from PySide2.QtCore import QFile, QObject, QTimer, Slot, QEvent

UI_BASEPATH = '/ursapqConsole/'
#style
BG_COLOR_OK = 'background-color: #4CBB17;'
BG_COLOR_WARNING = 'background-color: #F9A602;'
BG_COLOR_ERROR = 'background-color: #DF2800;'
BG_COLOR_OFF = 'background-color: #808080;'

class ConsoleWindow(QObject):
    '''
    Generic consloe window loaded from ui file. Automatically starts a QTimer
    calling self.update() repeatedly. The timer is deleted when the window is
    closed by the user.
    The update and setupcallbacks should be overridden by child classes
    '''

    def __init__(self, uifilename, updateTime = 500):
        super(ConsoleWindow, self).__init__(None)
        self.updateTime = updateTime

        local_dir = os.path.dirname(os.path.abspath(__file__))
        self.window = QUiLoader().load( QFile(local_dir + UI_BASEPATH + uifilename) )

        self.setupCallbacks()

        self.updateTimer = QTimer()
        self.updateTimer.timeout.connect(self.update)
        self.updateTimer.start(self.updateTime)

        self.window.installEventFilter(self)
        self.window.show()

    def eventFilter(self, obj, event):
        if obj is self.window and event.type() == QEvent.Close:
            del self.updateTimer
        return False

    def setupCallbacks(self):
        pass
    def update(self):
        pass

class VacuumWindow(ConsoleWindow):
    def __init__(self, ursapq, *args, **kvargs):
        self.prevacValveLock = Switch(thumb_radius=11, track_radius=8)
        self.pumpsEnable = Switch(thumb_radius=11, track_radius=8)
        super(VacuumWindow, self).__init__('vacuum.ui', *args, **kvargs)
        self.ursapq = ursapq
        self.window.prevacValveLockBox.addWidget(self.prevacValveLock)
        self.window.pumpsEnableBox.addWidget(self.pumpsEnable)

    def setupCallbacks(self):
        self.prevacValveLock.toggled.connect(self.preVacValve_lock)
        self.pumpsEnable.toggled.connect(self.enablePumps)

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
        self.enableSwitch = Switch(thumb_radius=11, track_radius=8)
        super(SampleWindow, self).__init__('sample.ui', *args, **kvargs)
        self.window.ovenEnableBox.addWidget(self.enableSwitch)
        self.ursapq = ursapq

    def setupCallbacks(self):
        self.enableSwitch.toggled.connect(self.oven_enable)
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
        self.mcpEnableSwitch = Switch(thumb_radius=11, track_radius=8)
        self.tofEnableSwitch = Switch(thumb_radius=11, track_radius=8)
        super(SpectrometerWindow, self).__init__('spectrometer.ui', *args, **kvargs)
        self.window.mcpEnableBox.addWidget(self.mcpEnableSwitch)
        self.window.tofEnableBox.addWidget(self.tofEnableSwitch)
        self.ursapq = ursapq

    def setupCallbacks(self):
        self.mcpEnableSwitch.toggled.connect(self.mcpEnable)
        self.tofEnableSwitch.toggled.connect(self.tofEnable)
        self.window.mcpSetButton.clicked.connect(self.mcpSet)
        self.window.tofSetButton.clicked.connect(self.tofSet)

    def update(self):
        self.mcpEnableSwitch.setChecked( self.ursapq.hv_mcpEnable )
        self.tofEnableSwitch.setChecked( self.ursapq.hv_tofEnable )
        self.window.mcpFront_act.setText(  '{:.1f}'.format(self.ursapq.hv_front))
        self.window.mcpBack_act.setText(   '{:.1f}'.format(self.ursapq.hv_back))
        self.window.mcpPhos_act.setText(   '{:.1f}'.format(self.ursapq.hv_phosphor))
        self.window.mcpFront_set.setText(  '{:.1f}'.format(self.ursapq.hv_setFront))
        self.window.mcpBack_set.setText(   '{:.1f}'.format(self.ursapq.hv_setBack))
        self.window.mcpPhos_set.setText(   '{:.1f}'.format(self.ursapq.hv_setPhosphor))

    #Callbacks:
    @Slot()
    def mcpEnable(self):
        self.ursapq.hv_mcpEnable = self.mcpEnableSwitch.isChecked()

    @Slot()
    def tofEnable(self):
        self.ursapq.hv_tofEnable = self.tofEnableSwitch.isChecked()

    @Slot()
    def mcpSet(self):
        try:
            self.ursapq.hv_setFront = float( self.window.mcpFront_in.toPlainText() )
        except Exception:
            pass
        try:
            self.ursapq.hv_setBack = float( self.window.mcpBack_in.toPlainText() )
        except Exception:
            pass
        try:
            self.ursapq.hv_setPhosphor = float( self.window.mcpPhos_in.toPlainText() )
        except Exception:
            pass

    @Slot()
    def tofSet(self):
        pass

class MainWindow(ConsoleWindow):
    def __init__(self, ursapq, *args, **kvargs):
        super(MainWindow, self).__init__('main.ui', *args, **kvargs)
        self.ursapq = ursapq

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
        if self.ursapq.oven_isOn:
            self.window.ovenStatus.setText("ON")
            if self.ursapq.oven_PIDStatus == "OK":
                self.window.sample_SL.setStyleSheet(BG_COLOR_OK)
            else:
                self.window.sample_SL.setStyleSheet(BG_COLOR_WARNING)
        else:
            self.window.ovenStatus.setText("OFF")
            if self.ursapq.oven_enable:
                self.window.sample_SL.setStyleSheet(BG_COLOR_ERROR)
            else:
                self.window.sample_SL.setStyleSheet(BG_COLOR_OFF)

    def updateSpectrometer(self):
        if self.ursapq.HVPS_Status == 'OFF':
            self.window.detector_SL.setStyleSheet(BG_COLOR_OFF)
        elif self.ursapq.HVPS_Status == 'WARNING':
            self.window.detector_SL.setStyleSheet(BG_COLOR_WARNING)
        elif self.ursapq.HVPS_Status == 'OK':
            self.window.detector_SL.setStyleSheet(BG_COLOR_OK)
        else:
            self.window.detector_SL.setStyleSheet(BG_COLOR_ERROR)

    def update(self):
        self.updateVacuum()
        self.updateSample()
        self.updateSpectrometer()

        self.window.statusBar().showMessage( 'Last update: %s' % str( self.ursapq.lastUpdate ) )

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

if __name__ == '__main__':

    ursapq = UrsaPQ( '141.89.116.204' , 2222 , 'ursapqManager_TurboOK'.encode('ascii'))

    app = QApplication(sys.argv)
    ui = MainWindow(ursapq)
    sys.exit(app.exec_())
