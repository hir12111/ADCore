# Builder definitions for pvDatabaseCPP
import iocbuilder
from iocbuilder import Device

class pvDatabaseCPP(Device):
    LibFileList = ['pvDatabase']
    AutoInstantiate = True

