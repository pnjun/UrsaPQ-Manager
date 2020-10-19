import pydoocs

DOOCS_RUNID   = 'FLASH.UTIL/STORE/URSAPQ/RUN.ID'
DOOCS_RUNTYPE = 'FLASH.UTIL/STORE/URSAPQ/RUN.TYPE'

runtypes = { 'time_zero'    : 0,
             'delay'        : 1,
             'energy'       : 2,
             'uvPower'      : 3,
             'delay_energy' : 4,
             'other'        : 5 
            }

class Run:
    def __init__(self, runtype):
        try:
            self.id = runtypes[runtype]
        except KeyError as exc:
            raise ValueError("Invalid run type") from exc
            
    def __enter__(self):
        lastId = pydoocs.read(DOOCS_RUNID)['data']
        pydoocs.write(DOOCS_RUNID, lastId + 1)
        pydoocs.write(DOOCS_RUNTYPE, self.id)
        
    def __exit__(self, type, value, traceback):
        pydoocs.write(DOOCS_RUNTYPE, -1)

print(pydoocs.read(DOOCS_RUNID))
