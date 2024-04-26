import time
import doocspie as dp
import multiprocessing as mp

#This function runs in forked process and checks DAQ status
def _check_daq_alive_subprocess():
    dp.get("FLASH.DAQ/DQM/SVR.FL2USER2/DQMFSTAT").data

def main():
    dp.get("FLASH.DAQ/DQM/SVR.FL2USER2/DQMFSTAT").data #If you comment this line the error goes away

    # ***  fork process to check DAQ status
    subprocess = mp.Process(target=_check_daq_alive_subprocess)
    subprocess.start()

    # ***  Give time for the error to occur
    time.sleep(20)

    if subprocess is not None:
        subprocess.kill()

if __name__ == "__main__":
    main()