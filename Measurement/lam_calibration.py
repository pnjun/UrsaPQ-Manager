import doocspie
import time

DOOCS_ODL_SPEED_SET = "FLASH.SYNC/LASER.LOCK.EXP/F2.PPL.OSC/FMC0.MD22.0.SPEED_IN_PERC.WR"
DOOCS_ODL_SET = "FLASH.SYNC/LASER.LOCK.EXP/F2.PPL.OSC/FMC0.MD22.0.POSITION_SET.WR"
DOOCS_ODL_GET = "FLASH.SYNC/LASER.LOCK.EXP/F2.PPL.OSC/FMC0.MD22.0.POSITION.RD"

DOOCS_LAM_SPEED_SET = "FLASH.SYNC/LAM.EXP.ODL/F2.MOD.AMC12/FMC0.MD22.1.SPEED_IN_PERC.WR"
DOOCS_LAM_SET = "FLASH.SYNC/LAM.EXP.ODL/F2.MOD.AMC12/FMC0.MD22.1.POSITION_SET.WR"
DOOCS_LAM_GET = "FLASH.SYNC/LAM.EXP.ODL/F2.MOD.AMC12/FMC0.MD22.1.POSITION.RD"

DOOCS_LAM_FB_TYPE = "FLASH.LASER/ULGAN1.DYNPROP/TCFIBER.INTS/INTEGER30"
DOOCS_LAM_FB_EN = "FLASH.LASER/ULGAN1.DYNPROP/TCFIBER.INTS/INTEGER29"

DOOCS_LAM_FB_DEL =  "FLASH.LASER/ULGAN1.DYNPROP/TCFIBER.DOUBLES/DOUBLE26"

DOOCS_LAM_PID_P = "FLASH.LASER/ULGAN1.DYNPROP/TCFIBER.DOUBLES/DOUBLE5"
DOOCS_LAM_PID_I = "FLASH.LASER/ULGAN1.DYNPROP/TCFIBER.DOUBLES/DOUBLE6"
DOOCS_LAM_PID_D = "FLASH.LASER/ULGAN1.DYNPROP/TCFIBER.DOUBLES/DOUBLE7"

ODL_TOLERANCE = 0.002 # 2fs tolerance
ODL_SPEED = 30
ODL_LAM_DIFF = 1181.113037109375 #hardcoded LAM - DELAY offset, set at start of beamtime based on calibration by laser group


#Set speed
doocspie.set(DOOCS_ODL_SPEED_SET, ODL_SPEED)
doocspie.set(DOOCS_LAM_SPEED_SET, ODL_SPEED)

def abs_move(val):
    doocspie.set(DOOCS_ODL_SET, val)
    doocspie.set(DOOCS_LAM_SET, val + ODL_LAM_DIFF)

    #wait until they reach target
    while True: # 10 ties, 3s in total
        odl = doocspie.get(DOOCS_ODL_GET).data
        lam = doocspie.get(DOOCS_LAM_GET).data

        if abs(odl - val) < ODL_TOLERANCE and abs(lam - (val + ODL_LAM_DIFF)) < ODL_TOLERANCE:
            break

def rel_move(val):
    odl = doocspie.get(DOOCS_ODL_GET).data
    abs_move(odl + val)

def feedback_en(enable):
    if enable:
        doocspie.set(DOOCS_LAM_FB_EN, 1)
    else:
        doocspie.set(DOOCS_LAM_FB_EN, 0)

def get_fb_delay():
    #average 10 s
    delay = 0
    for i in range(10):
        delay += doocspie.get(DOOCS_LAM_FB_DEL).data
        time.sleep(0.1)
    return delay/10


feedback_en(False)
time.sleep(.5)
rel_move(200)
time.sleep(.5)
feedback_en(True)



