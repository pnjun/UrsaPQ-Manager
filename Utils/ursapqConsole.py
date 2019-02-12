import sys
from ursapqUtils import UrsaPQ

from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QPushButton, QLineEdit
from PySide2.QtCore import QFile, QObject, QTimer, Slot, QEvent

UI_BASEPATH = 'ursapqConsoleData/'
#style
BG_COLOR_OK = 'background-color: #348035;'
BG_COLOR_WARNING = 'background-color: #efd077;'
BG_COLOR_ERROR = 'background-color: #e76c53;'

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

        self.window = QUiLoader().load( QFile(UI_BASEPATH + uifilename) )

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

    def update(self):
        #Update displayed values
        self.window.prevacPressure.setText(  '{:.2e}'.format(self.ursapq.preVacPressure) )
        self.window.chamberPressure.setText( '{:.2e}'.format(self.ursapq.chamberPressure) )
        self.window.prevacValves.setText( "Open" if self.ursapq.preVacValve_isOpen else "Closed" )
        self.window.pumpStatus.setText(   "Running" if self.ursapq.preVacValve_isOpen else "Stopped" )

        self.window.sampleTemp.setText( '{:.2e}'.format(self.ursapq.ovenVolt) )


        #Update status labels
        if self.ursapq.preVac_OK:
            self.window.vacuum_SL.setStyleSheet(BG_COLOR_WARNING)
        else:
            self.window.vacuum_SL.setStyleSheet(BG_COLOR_ERROR)

        if self.ursapq.preVac_OK and self.ursapq.mainVac_OK:
            self.window.vacuum_SL.setStyleSheet(BG_COLOR_OK)

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
