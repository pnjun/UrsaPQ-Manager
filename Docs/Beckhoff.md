Beckhoff PLC
======

## The system
The beckhoff systems consists of the PLC computer (mounted on the movable arm on the main chamber frame) and of three rails of clamps that provide direct connection to the hardware. Two clamps rails are mounted on the main frame, while a third one is mounted in the UrsaPQ rack.

### Architecture
The following hardware components are managed by the PLC:

* Turbopumps (currently big turbo is still manually operated, but will be connected in the future)
* Prevacuum line valves
* Pressure sensors
* Temperature sensors
* Sample manipulator motors
* Magnet retractor motors
* Frame translation motors
* Safety loop signal for HVPS (located in the rack NIM crate)
* Safety shutoff of oven power supply
* Safety interlock signal to FLASH

### Functions
The system automatically controls the turbopumps start/stop sequence depending on the prevacuum line pressure. There is an additional enable signal that needs to be manually set through the ursapqManager server. 
Note: At the moment the large turbopump is not integraded in the PLC control system due to a non-standard interface. It must be manually started and stopped with the onboard buttons.

It reads out temperature and pressure values and makes them available to users through the ursapqManager server process. Motion controls commands can also be sent to the PLC that will handle the stepper motor controls.

### Safety 
The PLC manages safety interlocks:

* When the pressure in the main chamber is good and pumps are running without error, the PLC sends the enable signal to the FLASH safety interlock, and allows operations of the HVPS. If a pump fault or pressure rise is detected, both the FLASH and HVPS interlocks are tripped.

* The oven power supply is activated only when pressure is good enough for the turbopumps start sequence. An additional oven enable must be set through the ursapqManager server.

* Prevacuum valves are normally open and are atomatically close when a failure in the prevacuum line is detected. They can be manually locked close through ursapqManager.

### Motion
Motors connected to the frame are mananged automatically by the PLC. Limit switches prevent operation outside the normal range. Users can require a motor action through ursapqManager. 

Homing of the motors is achived by driving the motor to its backward limit switch. The motion will be halted and the current position will be automatically reset to 0.


## Usage
The PLC is started by turning on the PC. Just turn the key to the on position and press the power button on the frame. No configuration is required. Safety routines are always active.

Users can interact with the PLC (and with all other experimental systems) through the ursapqUtils python package. The ursapqConsole app provides a GUI for ursapqUtils. It can be run cross platform on any computer that with a network connection to the ursapqManager server.

The ursapqManager process runs on the unix PC located in the rack. The ursapqManager PC must be on for users to be able to control the PLC via ursapqUtils or ursapqConsole. 
