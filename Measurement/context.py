#Context file for URSAPQ measurements, define general data gahtering and measurmement procedures
import doocspie
from doocspie.abo import TrainAbo
import asyncio
import xarray as xr
from contextlib import contextmanager
import numpy as np
from scipy import interpolate

from fablive import action, gather
from fablive.gather import _until_timeout, _accumulate

import time

import sys
sys.path.append("../Utils/")
from ursapq_api import UrsaPQ

# DOOCS ADDRESSES AND PARAMS
DOOCS_ODL_SPEED_SET = "FLASH.SYNC/LASER.LOCK.EXP/F2.PPL.OSC/FMC0.MD22.0.SPEED_IN_PERC.WR"
DOOCS_ODL_SET = "FLASH.SYNC/LASER.LOCK.EXP/F2.PPL.OSC/FMC0.MD22.0.POSITION_SET.WR"
DOOCS_ODL_GET = "FLASH.SYNC/LASER.LOCK.EXP/F2.PPL.OSC/FMC0.MD22.0.POSITION.RD"
DOOCS_WAVEPLATE     = 'FLASH.FEL/FLAPP2BEAMLINES/MOTOR1.FL24/FPOS.SET'
DOOCS_WAVEPLATE_RB  = 'FLASH.FEL/FLAPP2BEAMLINES/MOTOR1.FL24/FPOS'
DOOCS_WAVEPLATE_EN  = 'FLASH.FEL/FLAPP2BEAMLINES/MOTOR1.FL24/CMD'
DOOCS_LASER_SHUTTER = "FLASH.LASER/TIMER/ULGAN2/RTM.TRG3.CONTROL"
DOOCS_UV_STEERING_V = "FLASH.LASER/MOD24.PICOMOTOR/Steering_PMC/MOTOR.2.MOVE.REL" 
DOOCS_UV_STEERING_H = "FLASH.LASER/MOD24.PICOMOTOR/Steering_PMC/MOTOR.1.MOVE.REL" 
DOOCS_UV_GONIOMETER = "FLASH.LASER/MOD24.SMARACT/CH_B/SET_POSITION_FPOS"
DOOCS_UV_GONIOMETER_EN = "FLASH.LASER/MOD24.SMARACT/CH_B/COMMAND"
DOOCS_UV_ROTATION = "FLASH.LASER/MOD24.SMARACT/CH_A/SET_POSITION_FPOS"
DOOCS_UV_ROTATION_EN = "FLASH.LASER/MOD24.SMARACT/CH_A/COMMAND"
DOOCS_SDU_DELAY_SET    = "FLASH.FEL/FL24.SDU_CTRL/SDU_CTRL/OPCUA.MAIN.Delay"
DOOCS_SDU_DELAY_EN     = "FLASH.FEL/FL24.SDU_CTRL/SDU_CTRL/OPCUA.MAIN.NewDelay"
DOOCS_SDU_DELAY_GET    = "FLASH.FEL/FL24.SDU_CTRL/SDU_CTRL/OPCUA.MAIN.DispMeasMotorFemtoDelayEntry"
DOOCS_SDU_DELAY_READY  = "FLASH.FEL/FL24.SDU_CTRL/SDU_CTRL/OPCUA.MAIN.ReadyToMoveSleds"

DOOCS_LAM_SPEED_SET = "FLASH.SYNC/LAM.EXP.ODL/F2.MOD.AMC12/FMC0.MD22.1.SPEED_IN_PERC.WR"
DOOCS_LAM_SET = "FLASH.SYNC/LAM.EXP.ODL/F2.MOD.AMC12/FMC0.MD22.1.POSITION_SET.WR"
DOOCS_LAM_GET = "FLASH.SYNC/LAM.EXP.ODL/F2.MOD.AMC12/FMC0.MD22.1.POSITION.RD"
DOOCS_LAM_FB_EN = "FLASH.LASER/ULGAN1.DYNPROP/TCFIBER.INTS/INTEGER29"
DOOCS_LAM_FB_KP = "FLASH.LASER/ULGAN1.DYNPROP/TCFIBER.DOUBLES/DOUBLE5"
DOOCS_LAM_FB_KI = "FLASH.LASER/ULGAN1.DYNPROP/TCFIBER.DOUBLES/DOUBLE6"

DOOCS_URSA_T0 = "FLASH.EXP/STORE.FL24/URSAPQ/TIMEZERO"
ODL_TOLERANCE = 0.001 # 2fs tolerance
ODL_SPEED = 30
ODL_LAM_DIFF = 3489.914 #hardcoded LAM - DELAY offset, set at start of beamtime based on calibration by laser group

ursa = UrsaPQ()

# DEFINE ACTIONS (what to do when setting parameters)

@action
async def sdu(value):
    doocspie.set(DOOCS_SDU_DELAY_SET, value)
    doocspie.set(DOOCS_SDU_DELAY_EN, 1)
    while doocspie.get(DOOCS_SDU_DELAY_READY).data == 0:
        await asyncio.sleep(0.1)

    #save current delay to timezero
    set_t0(value)

@action
async def retarder(value):
    ursa.tof_retarderSetHV = -abs(value)
    while abs(ursa.tof_retarderHV - value) > 0.3:
        await asyncio.sleep(0.1)

@action
def coil(value):
    if not ursa.coil_enable:
        raise ValueError("Coil is not enabled")
    ursa.coil_current_set = value

@action
def wiggle_freq(value):
    if not ursa.coil_enable:
        raise ValueError("Coil is not enabled")
    ursa.coil_wiggle_freq = value

@action
def wiggle_ampl(value):
    if not ursa.coil_enable:
        raise ValueError("Coil is not enabled")
    ursa.coil_wiggle_ampl = value

@action
def goniometer(value):
    doocspie.set(DOOCS_UV_GONIOMETER, value)
    doocspie.set(DOOCS_UV_GONIOMETER_EN, 3)

@action
def rotation(value):
    doocspie.set(DOOCS_UV_ROTATION, value)
    doocspie.set(DOOCS_UV_ROTATION_EN, 3)

@action
async def waveplate(value):
    shutter = doocspie.get(DOOCS_LASER_SHUTTER).data
    if shutter < 32500:
        raise ValueError("Laser shutter is closed")

    doocspie.set(DOOCS_WAVEPLATE, value)
    doocspie.set(DOOCS_WAVEPLATE_EN, 1)
    await asyncio.sleep(0.4)

@action
def null(value):
    pass

@contextmanager
def disable_lam_feedback():
    #Read current FB values
    kp = doocspie.get(DOOCS_LAM_FB_KP).data
    ki = doocspie.get(DOOCS_LAM_FB_KI).data
    #Set to 0 to stop FB loop while we move the LAM
    doocspie.set(DOOCS_LAM_FB_KP, 0)
    doocspie.set(DOOCS_LAM_FB_KI, 0)
    try:
        yield
    finally:
        #Restore values
        doocspie.set(DOOCS_LAM_FB_KP, kp)
        doocspie.set(DOOCS_LAM_FB_KI, ki)

@action
async def delay(value):
    value /= 1000 # convert to ps
    t0 = get_t0()
    await lam_dl(t0 - value)

@action
async def lam_dl(target_lam):
    ''' Set ODL and LAM to target values, wait until they reach target '''
    #raise NotImplementedError("Dont use")

    with disable_lam_feedback():
        doocspie.set(DOOCS_ODL_SPEED_SET, ODL_SPEED)
        doocspie.set(DOOCS_LAM_SPEED_SET, ODL_SPEED)

        target_odl = target_lam - ODL_LAM_DIFF
        doocspie.set(DOOCS_ODL_SET, target_odl)
        doocspie.set(DOOCS_LAM_SET, target_lam)

        start = time.time()
        while True:
            odl = doocspie.get(DOOCS_ODL_GET).data
            lam = doocspie.get(DOOCS_LAM_GET).data

            if abs(odl - target_odl) < ODL_TOLERANCE and abs(lam - target_lam) < ODL_TOLERANCE:
                break
            else:
                if time.time() - start > 120:
                    raise TimeoutError("Timeout while waiting for ODL and LAM to reach target")
            
            await asyncio.sleep(0.01)

@action
def integ_time(value):
    # Used in gather_data
    global _integ_time
    _integ_time = value

@action
def integ_gmd(value):
    # Used in gather_data
    global _integ_gmd
    _integ_gmd = value

def get_t0():
    t0 = doocspie.get(DOOCS_URSA_T0).data
    return t0

def set_t0(t0):
    doocspie.set(DOOCS_URSA_T0, t0)

def calibrate_evs(data):
    evs_axis = ursa.data_axis[1]
    data = data.rename(eTof='evs').assign_coords(evs=evs_axis)
    data = data.transpose(...,'evs') 
    return data.isel(evs=slice(None, None, -1)) #reverse evs axis

#GMD RATE MONITOR
UPDATE_PERIOD = 2 # seconds
GMD_MIN_RATE = 10 # uJ/train Raise error if GMD rate is below this value
GMD_FILTER = 300 # number of trains over which to filter the GMD rate (exp decay)


_gmd_rate = None
def gmd_rate_monitor(data_in):
    for data in data_in:
        ''' pass through data, but raise error if GMD rate is too low '''
        global _gmd_rate
        gmd = data.gmd_even + data.gmd_odd
        
        if _gmd_rate is None:
            _gmd_rate = gmd * 1.5 # first value, set high to avoid error on first train

        _gmd_rate = _gmd_rate * (1 - 1/GMD_FILTER) + gmd / GMD_FILTER
        if gmd < GMD_MIN_RATE:
            raise ValueError(f"GMD rate is too low: {gmd:.2f} uJ/train")
        yield data


#**** DATA GATERING FOR PLOTS ****
def read_from_ursa():
    data = ursa.data_shots_accumulator

    return xr.Dataset({'even':  xr.DataArray(data[0], dims=['eTof']),
                        'odd':  xr.DataArray(data[1], dims=['eTof']),
                        'gmd':  xr.DataArray(ursa.data_gmd_accumulator)})

_integ_time = None
_integ_gmd = None
@gather
def gather_data():
    if _integ_time is None and _integ_gmd is None:
        raise ValueError("At least one of integ_time or integ_gmd must be set")

    end_time = time.time() + ( _integ_time or 1e3 )
    max_gmd = _integ_gmd or 1e8

    #reset accumulator
    ursa.data_clear_accumulator = True
    time.sleep(1) #wait for data to clear
    
    while True:
        data = read_from_ursa()

        time.sleep(2) #No need to read data too fast
        yield data

        if time.time() > end_time or data.gmd > max_gmd:
            break
