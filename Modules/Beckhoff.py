import pyads
from config import config

class BeckhoffSys:
    '''
    This class provides a object oriented interace to the values stored in the PLC running on the
    beckhoff system through the ADS protocol.

    PLC variables are accessible as properties of this class (with either read only or r/w access)
    Note that if a variable name is changed in the PLC, the correspoding property must be adjusted here
    '''

    def start(self):
        self.plc = pyads.Connection(config.Beckhoff_AmsNetID,
                                    config.Beckhoff_AmsPort,
                                    config.Beckhoff_IPAddr)
        self.plc.open()

    def stop(self):
        try:
            self.plc.close()
            del self.plc
        except Exception:
            pass

    def read(self, name, type):
        return self.plc.read_by_name(name, type)

    def write(self, name, val, type):
        return self.plc.write_by_name(name, val, type)


if __name__=='__main__':
    beckhoff = BeckhoffSys()
    print("reading ovenps status")
    print(beckhoff.read('MAIN.OvenPS_Relay', pyads.PLCTYPE_BOOL))
