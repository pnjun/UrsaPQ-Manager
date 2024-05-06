#Context file for URSAPQ measurements, define general data gahtering and measurmement procedures
import doocspie
from doocspie.abo import TrainAbo
import asyncio
import xarray as xr
from contextlib import contextmanager

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

DOOCS_URSA_T0 = "FLASH.EXP/USER.STORE.FL24/FL24/VAL.01"

ODL_TOLERANCE = 0.002 # 2fs tolerance
ODL_SPEED = 30
ODL_LAM_DIFF = 1181.113037109375 #hardcoded LAM - DELAY offset, set at start of beamtime based on calibration by laser group

DOOCS_ETOF = "FLASH.FEL/ADC.ADQ.FL2EXP1/FL2EXP1.CH00/CH00.DAQ.TD"
SLICER_PARAMS = {'offset': 2246,  'period': 9969.23, 'window': 3000, 'shot_num': 6}

ursa = UrsaPQ()

# DEFINE ACTIONS (what to do when setting parameters)
@action
async def retarder(value):
    await asyncio.sleep(2)

@action
async def waveplate(value):
    await asyncio.sleep(2)

@action
async def deltest(value):
    await asyncio.sleep(2)

@action
async def odl_position(value):
    await asyncio.sleep(2)

@action
def integration_time(value):
    # Used in gather_data
    global _integ_time
    _integ_time = value

@contextmanager
def disable_lam_feedback():
    doocspie.set(DOOCS_LAM_FB_EN, 0)
    try:
        yield
    finally:
        doocspie.set(DOOCS_LAM_FB_EN, 1)

@action
async def delay(target_odl):
    ''' Set ODL and LAM to target values, wait until they reach target '''
    raise NotImplementedError("BEAM IS AT FL23, dont even try")

    with disable_lam_feedback():
        doocspie.set(DOOCS_ODL_SPEED_SET, ODL_SPEED)
        doocspie.set(DOOCS_LAM_SPEED_SET, ODL_SPEED)

        target_lam = target_odl + ODL_LAM_DIFF
        doocspie.set(DOOCS_ODL_SET, target_odl)
        doocspie.set(DOOCS_LAM_SET, target_lam)

        start = time.time()
        while True:
            odl = doocspie.get(DOOCS_ODL_GET).data
            lam = doocspie.get(DOOCS_LAM_GET).data

            if abs(odl - target_odl) < ODL_TOLERANCE and abs(lam - target_lam) < ODL_TOLERANCE:
                break
            else:
                if time.time() - start > 60:
                    raise TimeoutError("Timeout while waiting for ODL and LAM to reach target")
            
            await asyncio.sleep(0.05)

def get_t0():
    t0 = doocspie.get(DOOCS_URSA_T0).data
    return t0

def set_t0(t0):
    doocspie.set(DOOCS_URSA_T0, t0)

#Stuff for plotting
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

def get_eTof_slices():
    slicer = Slicer(**SLICER_PARAMS)
    abo = TrainAbo()
    abo.add(DOOCS_ETOF, label='eTof')

    for event in abo:
        eTof_trace = event.get('eTof').data
        shots = xr.DataArray([eTof_trace[slice] for slice in slicer], dims=['shots', 'eTof'])
        yield xr.Dataset({'even': shots[::2].mean('shots'), 
                          'odd':  shots[1::2].mean('shots')})

_integ_time = 30
@gather
def gather_data():
    yield from _until_timeout(_accumulate(get_eTof_slices(), 2), _integ_time)
