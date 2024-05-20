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

DOOCS_LAM_SPEED_SET = "FLASH.SYNC/LAM.EXP.ODL/F2.MOD.AMC12/FMC0.MD22.1.SPEED_IN_PERC.WR"
DOOCS_LAM_SET = "FLASH.SYNC/LAM.EXP.ODL/F2.MOD.AMC12/FMC0.MD22.1.POSITION_SET.WR"
DOOCS_LAM_GET = "FLASH.SYNC/LAM.EXP.ODL/F2.MOD.AMC12/FMC0.MD22.1.POSITION.RD"
DOOCS_LAM_FB_EN = "FLASH.LASER/ULGAN1.DYNPROP/TCFIBER.INTS/INTEGER29"
DOOCS_LAM_FB_KP = "FLASH.LASER/ULGAN1.DYNPROP/TCFIBER.DOUBLES/DOUBLE5"
DOOCS_LAM_FB_KI = "FLASH.LASER/ULGAN1.DYNPROP/TCFIBER.DOUBLES/DOUBLE6"


DOOCS_URSA_T0 = "FLASH.EXP/STORE.FL24/URSAPQ/TIMEZERO"

ODL_TOLERANCE = 0.001 # 2fs tolerance
ODL_SPEED = 30
ODL_LAM_DIFF = 3488.757 #hardcoded LAM - DELAY offset, set at start of beamtime based on calibration by laser group

ursa = UrsaPQ()

# DEFINE ACTIONS (what to do when setting parameters)
@action
async def retarder(value):
    ursa.tof_retarderSetHV = value
    while abs(ursa.tof_retarderHV - value) > 0.3:
        await asyncio.sleep(0.1)

@action
async def coil(value):
    if not ursa.coil_enable:
        raise ValueError("Coil is not enabled")
    ursa.coil_setCurrent = value

@action
async def deltest(value):
    await asyncio.sleep(1)

@action
async def waveplate(value):
    await asyncio.sleep(1)

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


async def delay(value):
    t0 = get_t0()
    await lam_dl(value + t0)

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
                if time.time() - start > 90:
                    raise TimeoutError("Timeout while waiting for ODL and LAM to reach target")
            
            await asyncio.sleep(0.01)

@action
def integration_time(value):
    # Used in gather_data
    global _integ_time
    _integ_time = value


def get_t0():
    t0 = doocspie.get(DOOCS_URSA_T0).data
    return t0

def set_t0(t0):
    doocspie.set(DOOCS_URSA_T0, t0)

#**** DATA GATERING FOR PLOTS ****

DOOCS_ETOF = "FLASH.FEL/ADC.ADQ.FL2EXP1/FL2EXP1.CH00/CH00.DAQ.TD"
DOOCS_GMD  = "FLASH.FEL/XGM.INTENSITY/FL2.HALL/INTENSITY.TD"
SLICER_PARAMS = {'offset': 2246,  'period': 9969.23, 'window':  3000, 'shot_num': 6}
ETOF_T0, ETOF_DT =  0.142, 0.0005

class Slicer():
    def __init__(self, offset:int, period:int, window:int, shot_num=None):
        self.offset = offset
        self.period = period
        self.window = window
        assert shot_num % 2 == 0, "shot_num must be even"
        self.max_len = shot_num

    def __getitem__(self, n:int) -> slice:
        if self.max_len:
            if n >= self.max_len: raise IndexError("Slice index out of range")
        start = self.offset + self.period*n
        end   = start + self.window
        return slice(int(round(start)), int(round(end)))

def _tof_to_ev(tof: np.array, retarder: float) -> np.array:
    """ Converts between tof and Ev for main chamber TOF spectrometer """
    l1, l2, l3 = 0.09, 1.690, 0.002  # meters
    m_over_2e = 5.69 / 2
    evOffset = 1.05  # eV

    def ev2tof(e):
        #Parameters for evConversion
        new_e = e - evOffset
        return np.sqrt(m_over_2e) * ( l1 / np.sqrt(new_e) +
                                      l2 / np.sqrt(new_e + retarder) +
                                      l3 / np.sqrt(new_e + 300) )

    def generate_interpolator(ev_min, ev_max):
        evRange = np.arange(ev_min+0.01, ev_max, 0.01)
        tofVals = ev2tof( evRange )
        return interpolate.interp1d(tofVals, evRange, kind='linear')

    return generate_interpolator(evOffset - retarder, 5000)(tof)

def get_eTof_slices():
    slicer = Slicer(**SLICER_PARAMS)
    abo = TrainAbo()
    abo.add(DOOCS_ETOF, label='eTof')
    abo.add(DOOCS_GMD, label='gmd')

    tofs = ETOF_T0 + np.arange(SLICER_PARAMS['window']) * ETOF_DT
    retarder = ursa.tof_retarderHV

    for event in abo:
        eTof_trace = event.get('eTof').data
        gmd = event.get('gmd').data

        gmd_even = gmd[::2].sum()
        gmd_odd = gmd[1::2].sum()

        shots = xr.DataArray([eTof_trace[slice] for slice in slicer], dims=['shots', 'eTof'])

        stacked = xr.Dataset({'even': shots[::2].mean('shots'), 
                              'odd':  shots[1::2].mean('shots'),
                              'gmd_even': gmd_even, 'gmd_odd': gmd_odd}) 

        stacked = stacked.assign_coords(eTof=tofs)
        stacked = stacked.assign_coords(evs=('eTof', _tof_to_ev(tofs, retarder)))
        stacked = stacked.swap_dims(eTof='evs') # make evs the main dimension
        stacked = stacked.transpose(...,'evs') 

        yield stacked.isel(evs=slice(None, None, -1))

_integ_time = 30
@gather
def gather_data():
    yield from _until_timeout(_accumulate(get_eTof_slices(), 2), _integ_time)
