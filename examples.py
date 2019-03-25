from Utils.ursapqUtils import UrsaPQ
import numpy as np


exp = UrsaPQ()

# DATA ANALYIS PARAMTERS THAT CAN BE SET 
print(exp.data_filterLvl)      # Float, between 0 and 1. 0 = no filter, 1 = full filter
print(exp.data_slicePeriod)    # Float. Number of samples between each FEL shot. It's float since ADC clock runs out of sync with the FEL
print(exp.data_sliceSize)      # Integer. Size of TOF slice in samples. MUST BE LESS than slicePeriod
print(exp.data_sliceOffset)    # Integer. How many samples to skip at the begninnig of trace before slicing starts -> Use for time zero setting
print(exp.data_skipSlices)    # Integer. How many slices to skip for singleShot average

# OUTPUT VARIABLES
# Laser and ADC traces. First row is times, second row is data
print(exp.data_tofTrace)          

# Average of even and odd slices. First row is times, second row are eV, third row is data
print(exp.data_evenShots)     
print(exp.data_oddShots)       

# Time of arrival of first laser shot. None when no rising edge is found
print(exp.data_laserTime)
