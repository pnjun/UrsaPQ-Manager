Measurement Utils
===

Some utilities to facilitate the creation of measurement scripts are found in `Measurements` togheter with some already made scripts for basic scanning. The `scan_utils.py` module provides access to DESY hardware through DOOCS, appropriate functions can be used to set and get parameter such as delay state position and undulator gap.

# Usage

## Experimental runs

Each run is given a run ID number and a run type, by setting the appropriate parameters on DOOCS. This is done automatically by the `Run` context manager. For this reason, all scanning should be done using withing the context manager block in order handle the creation / closure of each run. Eg, to start a delay scan run:

```
from scan_utils import *

with Run(RunType.delay):
  #Here goes scanning code
```

## Doocs parameter setting

Some doocs paramters can be set using helper functions in the module. Eg, the `set_delay` function allows to set a delay stage position.

```  
set_delay(2000)                                      # sets the delay stage to 2000
set_delay(4, time_zero = 2000)                       # sets the delay stage to time_zero - delay. In this case 1994
set_delay(4, time_zero = 2000, park_position = 2040) # as above but drives the stage to 2040 before setting it to 1994
```

## Online Plotting

The `DataPreview` class can be used to generate a 2d plot of a numpyarray and update it in real time as the data comes in. Create the plot with:
```
plot = DataPreview(<X Axis>, <Y Axis>, <data array>, sliceX = <slice>)
```
sliceX can be a slice object. If given only that slice of the given X Axis data will be used for plotting.

The function `DataPreview.update_wait(<callable>, <time>)` can be used to update the plot in a loop while waiting for the data to come in.
The function will call the given `<callable>` every second until `<time>` seconds are elapsed, then returns. The `<callable>` should use the `update_data` method to update the data in the plot. Eg:

```
#Set up preview updater 
def updater():
    data = #GET NEW DATA
    plot.update_data(data)
    
DataPreview.update_wait(updater, <TOT INTEGRATION TIME>)
```



# Examples

A time zero scan example is available in the `Measurement` folder.
