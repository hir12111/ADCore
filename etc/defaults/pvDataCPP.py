# Builder definitions for pvDataCPP
import iocbuilder
from iocbuilder import Device

class pvDataCPP(Device):
    LibFileList = ['pvData']
    AutoInstantiate = True

