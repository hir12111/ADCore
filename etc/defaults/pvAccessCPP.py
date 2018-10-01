# Builder definitions for pvAccessCPP
import iocbuilder
from iocbuilder import Device

class pvAccessCPP(Device):
    LibFileList = ['pvAccess', 'pvAccessIOC', 'pvAccessCA']
    DbdFileList = ['PVAServerRegister']
    AutoInstantiate = True

