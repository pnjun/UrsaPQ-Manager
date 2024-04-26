import doocspie
from doocspie.abo import TrainAbo
import asyncio
import xarray as xr

from fablive import action
from fablive.gather import _until_timeout, _accumulate

#Context file for URSAPQ measurements, define general data gahtering and measurmement procedures

DOOCS_UNDULATOR = ""
DOOCS_DELAY = ""
DOOCS_ETOF = "FLASH.FEL/ADC.ADQ.FL2EXP1/FL2EXP1.CH00/CH00.DAQ.TD"
SLICER_PARAMS = {'offset': 2246,  'period': 9969.23, 'window': 3000, 'shot_num': 6}

@action
async def retarder(value):
    print("set retarder to %s" % value)
    await asyncio.sleep(3)

@action
async def waveplate(value):
    print("set waveplate to %s" % value)
    await asyncio.sleep(3)

@action
async def coil(value):
    print("set coil to %s" % value)
    await asyncio.sleep(3)

@action
def delay(value):
    print("set delay to %s" % value)

@action
def energy(value):
    print("set energy to %s" % value)


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

def gather_data(integ_time=20, update_time=2):
    yield from _until_timeout(_accumulate(get_eTof_slices(), update_time), integ_time)