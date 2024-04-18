#!/usr/bin/python
import sys
import os
import time
from ursapq_api import UrsaPQ
from ursapqConsoleResources.switch import Switch


from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QPushButton, QLineEdit
from PySide2.QtCore import QFile, QObject, QTimer, Slot, QEvent
from PySide2.QtGui import QPixmap

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

class ManipulatorWindow(ConsoleWindow):
    def __init__(self, ursapq, *args, **kvargs):
        super(ManipulatorWindow, self).__init__('manipulator.ui', *args, **kvargs)
        self.ursapq = ursapq
        self.setupCallbacks()
        
        local_dir = os.path.dirname(os.path.abspath(__file__))
        bgPixmap = QPixmap(local_dir + UI_BASEPATH + "manipulators.png")
        self.window.background.setPixmap(bgPixmap)
        
    def setupCallbacks(self):
        self.window.magnetButton.clicked.connect(self.move_magnet_y)
        self.window.moveButtonY.clicked.connect(self.move_sample_y)
        self.window.moveButtonX.clicked.connect(self.move_sample_x)
        self.window.moveButtonZ.clicked.connect(self.move_sample_z)
        self.window.stopButton.clicked.connect(self.stop_motion)

    def update(self):
        self.window.mag_y.setText( 'Y = {:.1f}'.format(self.ursapq.magnet_pos_y))
        self.window.pos_x.setText( 'X = {:.1f}'.format(self.ursapq.sample_pos_x))
        self.window.pos_y.setText( 'Y = {:.1f}'.format(self.ursapq.sample_pos_y))
        self.window.pos_z.setText( 'Z = {:.1f}'.format(self.ursapq.sample_pos_z))
        
        motionlocked = self.ursapq.sample_pos_x_stop or \
                       self.ursapq.sample_pos_y_stop or \
                       self.ursapq.sample_pos_z_stop or \
                       self.ursapq.magnet_pos_y_stop
            
        self.window.stopButton.setChecked(motionlocked)
        self.window.stopButton.setText("Unlock" if motionlocked else "Stop")

    @Slot()
    def move_sample_x(self):
        try:
            self.ursapq.sample_pos_x_setPoint = float( self.window.pos_x_set.toPlainText() )
        except Exception:
            pass
        else:
            self.ursapq.sample_pos_x_enable = True

    @Slot()
    def move_sample_y(self):
        try:
            self.ursapq.sample_pos_y_setPoint = float( self.window.pos_y_set.toPlainText() )
        except Exception:
            pass
        else:
            self.ursapq.sample_pos_y_enable = True

    @Slot()
    def move_sample_z(self):
        try:
            self.ursapq.sample_pos_z_setPoint = float( self.window.pos_z_set.toPlainText() )
        except Exception:
            pass
        else:
            self.ursapq.sample_pos_z_enable = True

    @Slot()
    def move_magnet_y(self):
        try:
            self.ursapq.magnet_pos_y_setPoint = float( self.window.mag_y_set.toPlainText() )
        except Exception:
            pass
        else:
            self.ursapq.magnet_pos_y_enable = True

    @Slot()
    def stop_motion(self):
        self.ursapq.sample_pos_x_stop = self.window.stopButton.isChecked()
        self.ursapq.sample_pos_y_stop = self.window.stopButton.isChecked()
        self.ursapq.sample_pos_z_stop = self.window.stopButton.isChecked()
        self.ursapq.magnet_pos_y_stop = self.window.stopButton.isChecked()
        
class SampleWindow(ConsoleWindow):
    def __init__(self, ursapq, *args, **kvargs):
        super(SampleWindow, self).__init__('sample.ui', *args, **kvargs)
        self.ovenSwitch = Switch(thumb_radius=11, track_radius=8)
        self.window.ovenEnableBox.addWidget(self.ovenSwitch)
        self.gasLine_switch = Switch(thumb_radius=11, track_radius=8)
        self.window.flowEnableBox.addWidget(self.gasLine_switch)

        self.resetTimer = False
        
        self.ursapq = ursapq
        self.setupCallbacks()

    def setupCallbacks(self):
        self.window.ovenSetButton.clicked.connect(self.newSetPoints)
        self.window.flow_setButton.clicked.connect(self.newFlow)
        self.ovenSwitch.clicked.connect(self.oven_enable)
        self.gasLine_switch.clicked.connect(self.gasLine_enable)

    def update(self):
        self.ovenSwitch.setChecked( self.ursapq.oven_enable )
        self.gasLine_switch.setChecked( self.ursapq.gasLine_enable )
        self.window.oven_temp.setText(  '{:.2f}'.format(self.ursapq.sample_bodyTemp))
        self.window.ovenPow.setText(  '{:.2f}'.format(self.ursapq.oven_output_pow))
        self.window.ovenSetPoint.setText('{:.1f}'.format(self.ursapq.oven_setPoint))
        self.window.flow_act.setText('{:.3f}'.format(self.ursapq.gasLine_flow))
        self.window.flow_set.setText('{:.3f}'.format(self.ursapq.gasLine_flow_set))

        if self.resetTimer:
            self.updateTimer.setInterval( self.updateTime )
            self.resetTimer = False

    #Callbacks:
    @Slot()
    def oven_enable(self):
        self.ursapq.oven_enable = self.ovenSwitch.isChecked()
        #Prolong next update cycle so that server has time to process the enable request
        #Update func will set update interval back to normal
        self.updateTimer.setInterval(self.updateTime*3)
        self.resetTimer = True

    #Callbacks:
    @Slot()
    def gasLine_enable(self):
        self.ursapq.gasLine_enable = self.gasLine_switch.isChecked()
        #Prolong next update cycle so that server has time to process the enable request
        #Update func will set update interval back to normal
        self.updateTimer.setInterval(self.updateTime*3)
        self.resetTimer = True

    @Slot()
    def newFlow(self):
        try:
            self.ursapq.gasLine_flow_set = float( self.window.flow_in.toPlainText() )
        except Exception:
            pass

    @Slot()
    def newSetPoints(self):
        try:
            self.ursapq.oven_setPoint = float( self.window.ovenSetPoint_in.toPlainText() )
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

        self.window.tofRetarder_act.setText( '{:.1f}'.format(self.ursapq.tof_retarderHV))
        self.window.tofRetarder_set.setText( '{:.1f}'.format(self.ursapq.tof_retarderSetHV))
        self.window.coilCurr_act.setText( '{:.1f}'.format(self.ursapq.coil_current))
        self.window.coilCurr_set.setText( '{:.1f}'.format(self.ursapq.coil_setCurrent))        

        if self.resetTimer:
            self.updateTimer.setInterval( self.updateTime )
            self.resetTimer = False

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
        self.ursapq.coil_enable = self.coilEnableSwitch.isChecked()
        #Prolong next update cycle so that server has time to process the enable request
        #Update func will set update interval back to normal
        self.updateTimer.setInterval(self.updateTime*3)
        self.resetTimer = True

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
            self.ursapq.tof_retarderSetHV = float( self.window.tofRetarder_in.toPlainText() )
        except Exception:
            pass
        try:
            self.ursapq.coil_setCurrent = float( self.window.coilCurr_in.toPlainText() )
        except Exception:
            pass

class DataDisplayWindow(ConsoleWindow):
    def __init__(self, ursapq, title, varname, *args, **kvargs):
        super(DataDisplayWindow, self).__init__('dataDisplay.ui', *args, **kvargs)
        self.ursapq = ursapq
        self.window.dataBox.setTitle(title)
        self.varname = varname

    def update(self):
        self.window.dataView.setText( '{:.2e}'.format(self.ursapq.__getattr__(self.varname)))


class MainWindow(ConsoleWindow):
    def __init__(self, *args, **kvargs):
        super(MainWindow, self).__init__('main.ui', *args, **kvargs)
        self.lightSwitch = Switch(thumb_radius=11, track_radius=8)
        self.window.lightOnBox.addWidget(self.lightSwitch)
        self.ursapq = None
        self.childWindows = [] # lists of all children windows

        self.setupCallbacks()
        self.window.installEventFilter(self)

    def eventFilter(self, obj, event):
        #Close child windows event
        if obj is self.window and event.type() == QEvent.Close:
            self.closeChildWindows()

        if obj is self.window.chamberPressure and event.type() == QEvent.MouseButtonPress:
            self.childWindows.append(DataDisplayWindow(self.ursapq, "Main Chamber Pressure", "chamberPressure"))
        if obj is self.window.prevacPressure and event.type() == QEvent.MouseButtonPress:
            self.childWindows.append(DataDisplayWindow(self.ursapq, "Pre Vacuum Pressure", "preVacPressure"))
        if obj is self.window.gasLine_pressure and event.type() == QEvent.MouseButtonPress:
            self.childWindows.append(DataDisplayWindow(self.ursapq, "Gas Line Pressure", "gasLine_pressure"))


        return super(MainWindow, self).eventFilter(obj, event)


    def setupCallbacks(self):
        self.window.sample_MB.clicked.connect(self.showSample)
        self.window.vacuum_MB.clicked.connect(self.showVacuum)
        self.window.spectr_MB.clicked.connect(self.showSpectrometer)
        self.window.manipulator_MB.clicked.connect(self.showManipulator)
        self.lightSwitch.clicked.connect(self.lightClick)

        self.window.chamberPressure.installEventFilter(self)
        self.window.prevacPressure.installEventFilter(self)
        self.window.gasLine_pressure.installEventFilter(self)
        pass

    def updateManipulator(self):
        self.lightSwitch.setChecked( self.ursapq.light_enable )

    def updateVacuum(self):
        #VACUUM BOX
        self.window.prevacPressure.setText(  f'{self.ursapq.preVacPressure:.2e}')
        self.window.chamberPressure.setText( f'{self.ursapq.chamberPressure:.2e}') 
        self.window.pump_speed.setText( f'{self.ursapq.pump_speed}' )

        self.window.prevacValves.setText( '{} ({})'.format(
                                           "Open" if self.ursapq.preVacValve_isOpen else "Closed",
                                           "Locked" if self.ursapq.preVacValve_lock else "Auto" ))
        if not self.ursapq.pumps_areON:
            pump_status = "Stop"
        elif self.ursapq.pumps_normalOp:
            pump_status = "Running"
        else:
            pump_status = "Starting"

        self.window.pumpStatus.setText(  '{} ({})'.format( 
                                          pump_status,
                                          "Auto" if self.ursapq.pumps_enable else "Locked" ))
        #Update status label
        if self.ursapq.preVac_OK:
            self.window.vacuum_SL.setStyleSheet(BG_COLOR_WARNING)
        else:
            if self.ursapq.pumps_enable:
                self.window.vacuum_SL.setStyleSheet(BG_COLOR_ERROR)
            else:
                self.window.vacuum_SL.setStyleSheet(BG_COLOR_OFF)

        if self.ursapq.preVac_OK and self.ursapq.mainVac_OK:
            self.window.vacuum_SL.setStyleSheet(BG_COLOR_OK)

    def updateSample(self):
        self.window.bodyTemp.setText( '{:.1f}'.format(self.ursapq.sample_bodyTemp) )
        self.window.capTemp.setText(  '{:.1f}'.format(self.ursapq.sample_capTemp) )
        self.window.tipTemp.setText(  '{:.1f}'.format(self.ursapq.sample_tipTemp) )
        self.window.gasLine_flow.setText('{:.3f}'.format(self.ursapq.gasLine_flow))
        self.window.gasLine_pressure.setText('{:.2e}'.format(self.ursapq.gasLine_pressure))

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
        self.window.retarder.setText(  '{:.1f}'.format(self.ursapq.tof_retarderHV))
        self.window.coil_curr.setText(  '{:.1f}'.format(self.ursapq.coil_current))

        if self.ursapq.HV_Status == 'OFF':
            self.window.detector_SL.setStyleSheet(BG_COLOR_OFF)
        elif self.ursapq.HV_Status == 'WARNING':
            self.window.detector_SL.setStyleSheet(BG_COLOR_WARNING)
        elif self.ursapq.HV_Status == 'OK':
            self.window.detector_SL.setStyleSheet(BG_COLOR_OK)
        else:
            self.window.detector_SL.setStyleSheet(BG_COLOR_ERROR)

    def connect(self):
        self.ursapq = UrsaPQ()

    def update(self):
        try:
            self.updateVacuum()
            self.updateSample()
            self.updateSpectrometer()
            self.updateManipulator()
        except Exception as e:
            try:
                self.connect()
            except Exception as e:
                print(str(e))
                self.closeChildWindows()
            self.window.statusBar().setStyleSheet(BG_COLOR_ERROR)
            statusbar = "NOT CONNECTED - Attempting connection (check config file)"

        else:
            lastStatusMessage = self.ursapq.lastStatusMessage.strftime("%H:%M:%S")
            message = lastStatusMessage + " - " + self.ursapq.statusMessage
            update =  'Last update: %s' % self.ursapq.lastUpdate.strftime("%d-%m-%y %H:%M:%S")
            statusbar = update + " | " + message
            self.window.statusBar().setStyleSheet(BG_COLOR_WHITE)

        self.window.statusBar().showMessage(statusbar)

    def closeChildWindows(self):
        for win in self.childWindows:
            win.close()
            del win

    #Callbacks:
    @Slot()
    def lightClick(self):
        self.ursapq.light_enable = self.lightSwitch.isChecked()
        
    @Slot()
    def showManipulator(self):
        self.childWindows.append(ManipulatorWindow(self.ursapq))
    @Slot()
    def showSample(self):
        self.childWindows.append(SampleWindow(self.ursapq))
    @Slot()
    def showVacuum(self):
        self.childWindows.append(VacuumWindow(self.ursapq))
    @Slot()
    def showSpectrometer(self):
        self.childWindows.append(SpectrometerWindow(self.ursapq))

def main():
    app = QApplication(sys.argv)
    ui = MainWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
