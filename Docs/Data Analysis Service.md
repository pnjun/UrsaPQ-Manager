Data Analysis Service
=======

This serivce is run by systemd on the Unix server mounted in the experimental rack. It pulls data from doocs and performs some basic online analysis for online data display. The data is made available through the API and can be displayed with ursapqOnlineView (See "Online Utilities and Control" page)

It runs automatically at startup and is automatically restarted in case if fails.

# Functions
The service reads the MCP TOF traces from the ADC in a loop as fast as possible, as well as the optical laser diode and (optionally) the hall GMD monitor. The output data that is available (through the API) is as follows:

``` 
data_tofTrace           Full ADC trace for whole macrobunch, low passed according to data_filterTau 
data_laserTrace         Full diode for whole macrobunch
data_evenShots          Single shot pumped data, low passed and averaged over a macrobunch
data_oddShots           Single shot unpumped data, low passed and averaged over a macrobunch
data_evenAccumulator    Single shot pumped data, averaged since last accumulator clear instruction
data_oddAccumulator     Single shot unpumped data, averaged since last accumulator clear instruction
data_AccumulatorCount   Number of macrobunches averaged to create even and odd accumulators
data_axis               TOF and EKIN axis labels for data_evenShots, data_oddShots, data_evenAccumulator 
                        and data_oddAccumulator
data_updateFreq         The frequency in Hz at which the server is able to pull data from doocs. 
                        10Hz means every macrobunch is processed.
```

GMD normalization can be activated for the accumulated traces by setting the corresponding flag in the configuration file (see below). The low passed traces are not normalized.

Online control is done by setting these parameters:
``` 
data_filterTau          Time constant of lorenzian low pass filter for filtered data
data_clearAccumulator   Set this to true to clear the accumulator
``` 

# Start / Stop / Restart

The service can be started stopped and restarted with:
* `sudo systemctl start ursapqData.service`
* `sudo systemctl stop ursapqData.service`
* `sudo systemctl restart ursapqData.service`

## Logging
Logs can be seen using:
* `journalctl -n 30 -u ursapqData.service`
* `sudo systemctl status ursapqData.service`

## Source location
The soruce code for the server process is located in ~/ExpManager/Modules/. The server script is ursapqManager.py

# Configuration

Configuration of the analysis parameters can be done by editing `Modules/config.json`. The service must be restarted for the changes to take effect. Data analysis parameters are prefixed with "Data_". All other parameters are used by the Manager service and should not be modified.

```
"Data_DOOCS_TOF"   : DOOCS address of tof trace
"Data_DOOCS_Trig"  : DOOCSaddress of trigger trace (not used)
"Data_DOOCS_GMD"   : DOOCS addres of GMD
"Data_DOOCS_LASER" : DOOCS address of laser trace
"Data_FilterTau"   : default value for low pass tau,
"Data_SlicePeriod" : rep rate of FEL in samples (float beacuse FLASH and ADC are not in sync),
"Data_SliceSize"   : lenght of a single shot in samples (longer values give more low ekin data)
"Data_SliceOffset" : samples to skip before starting slicing (use for time zero on single shot traces),
"Data_SkipSlices"    : slices to skip at the beginning of each bunch train: must be even,
"Data_SkipSlicesEnd" : slices to skip at the end of each bunch train: must be even  
"Data_GmdNorm"       : set to 1 to use gmd normalization (long time trends only, not shot to shot) 
"Data_Invert"        : set to 1 to invert y axis of data
"Data_Jacobian"      : set to 1 to use jacobian normalization                                       ** NOT WORKING **
```

