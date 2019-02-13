import sys
import os
from ursapqUtils import UrsaPQ

from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QPushButton, QLineEdit
from PySide2.QtCore import QFile, QObject, QTimer, Slot, QEvent

UI_BASEPATH = '/ursapqConsoleData/'
#style
BG_COLOR_OK = 'background-color: #4CBB17;'
BG_COLOR_WARNING = 'background-color: #efd077;'
BG_COLOR_ERROR = 'background-color: #e76c53;'
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
        super(VacuumWindow, self).__init__('vacuum.ui', *args, **kvargs)
        self.ursapq = ursapq

    def setupCallbacks(self):
        self.window.preVacValve_lock.stateChanged.connect(self.preVacValve_lock)

    def update(self):
        self.window.preVacValve_lock.setChecked( self.ursapq.preVacValve_lock )

    #Callbacks:
    @Slot()
    def preVacValve_lock(self):
        self.ursapq.preVacValve_lock = self.window.preVacValve_lock.isChecked()


class SampleWindow(ConsoleWindow):
    def __init__(self, ursapq, *args, **kvargs):
        super(SampleWindow, self).__init__('sample.ui', *args, **kvargs)
        self.ursapq = ursapq

    def setupCallbacks(self):
        self.window.oven_enable.stateChanged.connect(self.oven_enable)

    def update(self):
        self.window.oven_enable.setChecked( self.ursapq.oven_enable )

    #Callbacks:
    @Slot()
    def oven_enable(self):
        self.ursapq.oven_enable = self.window.oven_enable.isChecked()

class MainWindow(ConsoleWindow):
    def __init__(self, ursapq, *args, **kvargs):
        super(MainWindow, self).__init__('main.ui', *args, **kvargs)
        self.ursapq = ursapq

    def setupCallbacks(self):
        self.window.sample_MB.clicked.connect(self.showSample)
        self.window.vacuum_MB.clicked.connect(self.showVacuum)
        pass

    def updateVacuum(self):
        #VACUUM BOX
        self.window.prevacPressure.setText(  '{:.2e}'.format(self.ursapq.preVacPressure) )
        self.window.chamberPressure.setText( '{:.2e}'.format(self.ursapq.chamberPressure) )
        self.window.prevacValves.setText( '{} ({})'.format(
                                           "Open" if self.ursapq.preVacValve_isOpen else "Closed",
                                           "Locked" if self.ursapq.preVacValve_lock else "Auto" ))
        self.window.pumpStatus.setText(   "Running" if self.ursapq.preVacValve_isOpen else "Stopped" )

        #Update status label
        if self.ursapq.preVac_OK:
            self.window.vacuum_SL.setStyleSheet(BG_COLOR_WARNING)
        else:
            self.window.vacuum_SL.setStyleSheet(BG_COLOR_ERROR)

        if self.ursapq.preVac_OK and self.ursapq.mainVac_OK:
            self.window.vacuum_SL.setStyleSheet(BG_COLOR_OK)

    def updateSample(self):
        self.window.bodyTemp.setText( '{:.1f}'.format(self.ursapq.sample_bodyTemp) )
        self.window.capTemp.setText(  '{:.1f}'.format(self.ursapq.sample_capTemp) )
        self.window.tipTemp.setText(  '{:.1f}'.format(self.ursapq.sample_tipTemp) )

        #Update status label
        if self.ursapq.oven_isOn:
            self.window.ovenStatus.setText("ON")
            if self.ursapq.ovenStatus == "OK":
                self.window.sample_SL.setStyleSheet(BG_COLOR_OK)
            else:
                self.window.sample_SL.setStyleSheet(BG_COLOR_ERROR)
        else:
            self.window.ovenStatus.setText("OFF")
            self.window.sample_SL.setStyleSheet(BG_COLOR_OFF)

    def update(self):
        self.updateVacuum()
        self.updateSample()

        self.window.statusBar().showMessage( 'Last update: %s' % str( self.ursapq.lastUpdate ) )

    #Callbacks:
    @Slot()
    def showSample(self):
        self.sampleWindow = SampleWindow(self.ursapq)
    @Slot()
    def showVacuum(self):
        self.vacuumWindow = VacuumWindow(self.ursapq)


if __name__ == '__main__':

    ursapq = UrsaPQ( '141.89.116.204' , 2222 , 'ursapqManager_TurboOK'.encode('ascii'))

    app = QApplication(sys.argv)
    ui = MainWindow(ursapq)
    sys.exit(app.exec_())
