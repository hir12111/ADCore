# Builder definitions for pvCommonCPP
import iocbuilder
from iocbuilder import Device

class pvCommonCPP(Device):
    LibFileList = ['pvMB']
    AutoInstantiate = True

