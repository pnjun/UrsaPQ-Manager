#!/usr/bin/env python3
import time
import context 
from playsound import playsound

while True:
    if context.ursa.gmd_rate < 300:
        filepath = __file__.replace("alarm.py", "deedle_deedle.mp3") 
        playsound(filepath)
    time.sleep(10)


