import xml.dom.minidom
import os
import iocbuilder
from iocbuilder import Substitution, AutoSubstitution, SetSimulation, Device, records, Architecture, IocDataStream
from iocbuilder.arginfo import *
from iocbuilder.modules.asyn import Asyn, AsynPort, AsynIP
from iocbuilder.modules.busy import Busy
from iocbuilder.modules.calc import Calc
from iocbuilder.modules.ADSupport import ADSupport

__all__ = ['ADCore']

# Record local default builder definition path
defaults = os.path.join(os.path.dirname(__file__), 'defaults')

# Import non-builder module pvAccessCPP
from iocbuilder.modules import pvAccessCPP
pvAccessCPP.LoadDefinitions(defaults)
from iocbuilder.modules.pvAccessCPP import pvAccessCPP

# Import non-builder module pvDatabaseCPP
from iocbuilder.modules import pvDatabaseCPP
pvDatabaseCPP.LoadDefinitions(defaults)
from iocbuilder.modules.pvDatabaseCPP import pvDatabaseCPP

# Import non-builder module pvDataCPP
from iocbuilder.modules import pvDataCPP
pvDataCPP.LoadDefinitions(defaults)
from iocbuilder.modules.pvDataCPP import pvDataCPP

# Import non-builder module normativeTypesCPP
from iocbuilder.modules import normativeTypesCPP
normativeTypesCPP.LoadDefinitions(defaults)
from iocbuilder.modules.normativeTypesCPP import normativeTypesCPP


#############################
#    ADCore base classes    #
#############################

# This function is used to create a template instance using
# the provided locals and arguments.  It also checks if there
# are any unused arguments and if any are found the assert fails
def makeTemplateInstance(template, _locals, args):
    # Create an empty dictionary used to hold the template args
    template_args = {}
    # Make a copy of the supplied arguments
    args_copy = args.copy()
    # Loop over each template argument name
    for arg in template.ArgInfo.Names():
        # Check if the argument is found in args
        if arg in args_copy:
            template_args[arg] = args_copy.pop(arg)
        # Check if the argument is found in the locals
        elif arg in _locals:
            template_args[arg] = _locals[arg]
    # Check there are no unused args left
    assert not args_copy, "Unused arguments %s" % args_copy            
    # Return the template class
    return template(**template_args)  


# This decorator provides the ability to create a template class
# that overrides another template.  Use this when a *.template file
# has an include statement.  This functionality will be moved into
# iocbuilder in the future
def includesTemplates(*templates):
    def decorator(cls):
        arginfo = templates[0].ArgInfo
        arguments = list(templates[0].Arguments)
        defaults = templates[0].Defaults.copy()
        for template in templates[1:]:
            arginfo += template.ArgInfo
            arguments += [x for x in template.Arguments if x not in arguments]
            defaults.update(template.Defaults)
        cls.ArgInfo = arginfo + cls.ArgInfo
        cls.Arguments = list(cls.Arguments) + [x for x in arguments if x not in cls.Arguments]
        defaults.update(cls.Defaults)
        cls.Defaults = defaults
        return cls
    return decorator    


NDDataTypes=["NDInt8", "NDUInt8", "NDInt16", "NDUInt16", "NDInt32",
                 "NDUInt32", "NDFloat32", "NDFloat64"]

class ADCore(Device):
    """Library dependencies for ADCore"""
    Dependencies = (Asyn, Busy, ADSupport)
    if Architecture() == "win32-x86" or Architecture() == "windows-x64":
        LibFileList = []
    else:
#        LibFileList = ['GraphicsMagick', 'GraphicsMagickWand', 'GraphicsMagick++', 'PvAPI', 'sz', 'hdf5', 'NeXus', 'cbfad']
        LibFileList = []
        SysLibFileList = ['freetype', 'Xext', 'bz2', 'png12', 'xml2', 'X11', 'gomp', 'z', 'jpeg', 'tiff']
    LibFileList += ['ADBase', 'NDPlugin']
    DbdFileList = ['ADSupport', 'NDPluginSupport', 'NDFileHDF5', 'NDFileJPEG', 'NDFileTIFF', 'NDFileNull']
    AutoInstantiate = True

#############################

class ADBaseTemplate(AutoSubstitution):
    """Template containing the base records of any areaDetector driver"""
    TemplateFile = 'ADBase.template'

#############################

class NDPluginBaseTemplate(AutoSubstitution):
    """Template containing the base records of any areaDetector plugin"""
    TemplateFile = 'NDPluginBase.template'

#############################

class NDFileTemplate(AutoSubstitution):
    """Template containing the records of an areaDetector file writing plugin"""
    TemplateFile = 'NDFile.template'

#############################

########################
# Areadetector plugins #
########################

@includesTemplates(NDPluginBaseTemplate)
class NDStdArraysTemplate(AutoSubstitution):
    """Template containing the records for an NDStdArray"""
    TemplateFile = 'NDStdArrays.template'

class NDStdArrays(AsynPort):
    """This plugin provides a waveform record that can display the NDArrays
    produced by its NDARRAY_PORT"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDStdArraysTemplate
    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    # __init__ arguments
    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDStdArrays plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all attached plugins', int))

    ArgInfo.descriptions["FTVL"] = records.waveform.FieldInfo()["FTVL"]

    def Initialise(self):
        print '# NDStdArraysConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxMemory)'
        print 'NDStdArraysConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(MEMORY)d)' % self.__dict__


#############################

@includesTemplates(NDPluginBaseTemplate, NDFileTemplate)
class NDFileNetCDFTemplate(AutoSubstitution):
    TemplateFile = 'NDFileNetCDF.template'

class NDFileNetCDF(AsynPort):
    """This plugin can compress NDArrays to NetCDF and write them to file"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDFileNetCDFTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, BUFFERS = 50, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDFileNetCDF plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        BUFFERS = Simple('Max buffers to allocate', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all attached plugins', int))

    def Initialise(self):
        print '# NDFileNetCDFConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory)' % self.__dict__
        print 'NDFileNetCDFConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(BUFFERS)d, %(MEMORY)d)' % self.__dict__

#############################

@includesTemplates(NDPluginBaseTemplate, NDFileTemplate)
class NDFileTIFFTemplate(AutoSubstitution):
    TemplateFile = 'NDFileTIFF.template'

class NDFileTIFF(AsynPort):
    """This plugin can compress NDArrays to TIFF and write them to file"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDFileTIFFTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, BUFFERS = 50, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDFileTIFF plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        BUFFERS = Simple('Max buffers to allocate', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all attached plugins', int))

    def Initialise(self):
        print '# NDFileTIFFConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory)' % self.__dict__
        print 'NDFileTIFFConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(BUFFERS)d, %(MEMORY)d)' % self.__dict__

#############################

@includesTemplates(NDPluginBaseTemplate, NDFileTemplate)
class NDFileJPEGTemplate(AutoSubstitution):
    TemplateFile = 'NDFileJPEG.template'

class NDFileJPEG(AsynPort):
    """This plugin can compress NDArrays to JPEG and write them to file"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDFileJPEGTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, BUFFERS = 50, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDFileJPEG plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        BUFFERS = Simple('Max buffers to allocate', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all attached plugins', int))

    def Initialise(self):
        print '# NDFileJPEGConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory)' % self.__dict__
        print 'NDFileJPEGConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(BUFFERS)d, %(MEMORY)d)' % self.__dict__

#############################

@includesTemplates(NDPluginBaseTemplate, NDFileTemplate)
class NDFileNexusTemplate(AutoSubstitution):
    TemplateFile = 'NDFileNexus.template'

class NDFileNexus(AsynPort):
    """This plugin can compress NDArrays to Nexus and write them to file"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDFileNexusTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, BUFFERS = 50, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDFileNexus plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        BUFFERS = Simple('Max buffers to allocate', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all attached plugins', int))

    def Initialise(self):
        print '# NDFileNexusConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory)' % self.__dict__
        print 'NDFileNexusConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(BUFFERS)d, %(MEMORY)d)' % self.__dict__

#############################

@includesTemplates(NDPluginBaseTemplate, NDFileTemplate)
class NDFileHDF5Template(AutoSubstitution):
    TemplateFile = 'NDFileHDF5.template'

class NDFileHDF5(AsynPort):
    """This plugin can compress NDArrays to HDF5 and write them to file"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDFileHDF5Template

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, BUFFERS = 50, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDFileHDF5 plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        BUFFERS = Simple('Max buffers to allocate', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all attached plugins', int))

    def Initialise(self):
        print '# NDFileHDF5Configure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory)' % self.__dict__
        print 'NDFileHDF5Configure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(BUFFERS)d, %(MEMORY)d)' % self.__dict__

#############################

@includesTemplates(NDPluginBaseTemplate, NDFileTemplate)
class NDFileMagickTemplate(AutoSubstitution):
    TemplateFile = 'NDFileMagick.template'

class NDFileMagick(AsynPort):
    """This plugin can compress NDArrays to a range of formats supported by
    graphics magick and write them to file"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDFileMagickTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, BUFFERS = 50, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDFileMagick plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        BUFFERS = Simple('Max buffers to allocate', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all attached plugins', int))

    def Initialise(self):
        print '# NDFileMagickConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory)' % self.__dict__
        print 'NDFileMagickConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(BUFFERS)d, %(MEMORY)d)' % self.__dict__

#############################

@includesTemplates(NDPluginBaseTemplate)
class NDROITemplate(AutoSubstitution):
    """Template containing the records for an NDROI"""
    TemplateFile = 'NDROI.template'

class NDROI(AsynPort):
    """This plugin selects a region of interest and optionally scales it to
    fit in a particular data type"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDROITemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, BUFFERS = 50, MEMORY = 0, **args):
        # Init the superclass (_NDPluginBase)
        self.__super.__init__(PORT)
        # Store the args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDROI plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        BUFFERS = Simple('Max buffers to allocate', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all attached plugins', int))

    def Initialise(self):
        print '# NDROIConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory)' % self.__dict__
        print 'NDROIConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(BUFFERS)d, %(MEMORY)d)' % self.__dict__

#############################

@includesTemplates(NDPluginBaseTemplate)
class NDProcessTemplate(AutoSubstitution):
    """Template containing the records for an NDProcess"""
    TemplateFile = 'NDProcess.template'

class NDProcess(AsynPort):
    """This plugin does image processing like flat field correction, background
    subtraction, and recursive filtering"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDProcessTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, BUFFERS = 50, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDProcess plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        BUFFERS = Simple('Max buffers to allocate', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all attached plugins', int))

    def Initialise(self):
        print '# NDProcessConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory)' % self.__dict__
        print 'NDProcessConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(BUFFERS)d, %(MEMORY)d)' % self.__dict__

#############################

@includesTemplates(NDPluginBaseTemplate)
class NDStatsTemplate(AutoSubstitution):
    """Template containing the records for an NDStats"""
    TemplateFile = 'NDStats.template'

class NDStats(AsynPort):
    """This plugin calculates statistics like X and Y profile, centroid, and plots a histogram of binned pixels"""
    Dependencies = (Calc, )
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDStatsTemplate
    
    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, BUFFERS = 50, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)
        # Table of statistics parameters, tuple of:
        # (database name, attribute name, datatype, description)
        statsparams = [("COMPUTE_STATISTICS", "StatsComputeStats", "INT",    "Statistics: enable statistics computation"),
                       ("MIN_VALUE",          "StatsMin",          "DOUBLE", "Statistics: minimum value"),
                       ("MIN_X",              "StatsMinX",         "DOUBLE", "Statistics: minimum value X position"),
                       ("MIN_Y",              "StatsMinY",         "DOUBLE", "Statistics: minimum value Y position"),
                       ("MAX_VALUE",          "StatsMax",          "DOUBLE", "Statistics: maximum value"),
                       ("MAX_X",              "StatsMaxX",         "DOUBLE", "Statistics: maximum value X position"),
                       ("MAX_Y",              "StatsMaxY",         "DOUBLE", "Statistics: maximum value Y position"),
                       ("MEAN_VALUE",         "StatsMean",         "DOUBLE", "Statistics: mean value"),
                       ("SIGMA_VALUE",        "StatsSigma",        "DOUBLE", "Statistics: sigma value"),
                       ("TOTAL",              "StatsTotal",        "DOUBLE", "Statistics: total sum of all elements"),
                       ("NET",                "StatsNet",          "DOUBLE", "Statistics: sum of all elements minus background"),
                       ("BGD_WIDTH",          "StatsNetBgd",       "INT",    "Statistics: net background subtraction value"),
                       
                       ("COMPUTE_CENTROID",   "StatsComputeCentroid",   "INT",    "Statistics: enable centroid computation"),
                       ("CENTROID_THRESHOLD", "StatsCentroidThreshold", "DOUBLE", "Statistics: centroid threshold"),
                       ("CENTROIDX_VALUE",    "StatsCentroidX",         "DOUBLE", "Statistics: centroid X position"),
                       ("CENTROIDY_VALUE",    "StatsCentroidY",         "DOUBLE", "Statistics: centroid Y position"),
                       ("SIGMAX_VALUE",       "StatsCentroidSigmaX",    "DOUBLE", "Statistics: centroid sigma X"),
                       ("SIGMAY_VALUE",       "StatsCentroidSigmaY",    "DOUBLE", "Statistics: centroid sigma Y"),
                       ("SIGMAXY_VALUE",      "StatsCentroidSigmaXY",   "DOUBLE", "Statistics: centroid sigma XY") ]
        for (dbname, attrname, dtype, desc) in statsparams:
            NDAttributes(port=self, 
                         source=dbname, attrname=attrname, 
                         type="PARAM", datatype=dtype, 
                         description=desc)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDStats plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        BUFFERS = Simple('Max buffers to allocate', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all attached plugins', int))

    def Initialise(self):
        print '# NDStatsConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory)' % self.__dict__
        print 'NDStatsConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(BUFFERS)d, %(MEMORY)d)' % self.__dict__

#############################

@includesTemplates(NDPluginBaseTemplate)
class NDTransformTemplate(AutoSubstitution):
    """Template containing the records for an NDTransform"""
    TemplateFile = 'NDTransform.template'

class NDTransform(AsynPort):
    """This plugin selects a region of interest and optionally scales it to fit in a particular data type"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDTransformTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, BUFFERS = 50, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDTransform plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        BUFFERS = Simple('Max buffers to allocate', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all attached plugins', int))

    def Initialise(self):
        print '# NDTransformConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory)' % self.__dict__
        print 'NDTransformConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(BUFFERS)d, %(MEMORY)d)' % self.__dict__

#############################

@includesTemplates(NDPluginBaseTemplate)
class NDOverlayTemplate(AutoSubstitution):
    """Template containing the records for an NDOverlay"""
    TemplateFile = 'NDOverlay.template'

class NDOverlayNTemplate(AutoSubstitution):
    """Template containing the records for an NDOverlay"""
    TemplateFile = 'NDOverlayN.template'

class NDOverlay(AsynPort):
    """This plugin writes overlays on the array, like cursors and boxes"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDOverlayTemplate
    NOverlays = 8

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, BUFFERS = 50, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__["NOverlays"] = self.NOverlays
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)
        # Create some overlays
        for i in range(self.NOverlays):
            NDOverlayNTemplate(P = args["P"], O = args["R"], R = "%s%d:" % (args["R"], i + 1),
                NAME = "Overlay %d" % (i + 1), SHAPE = 1, XPOS = "", YPOS = "", XSIZE = "",
                YSIZE = "", XWIDTH = "", YWIDTH = "", PORT = PORT, ADDR = i, TIMEOUT = args["TIMEOUT"])

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDOverlay plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        BUFFERS = Simple('Max buffers to allocate', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all attached plugins', int))

    def Initialise(self):
        print '# NDOverlayConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, NOverlays, maxBuffers, maxMemory)'
        print 'NDOverlayConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(NOverlays)d, %(BUFFERS)d, %(MEMORY)d)' % self.__dict__

#############################

@includesTemplates(NDPluginBaseTemplate)
class NDROIStatTemplate(AutoSubstitution):
    """Template containing the records for an NDROIStat"""
    TemplateFile = 'NDROIStat.template'

class NDROIStatNTemplate(AutoSubstitution):
    """Template containing the records for an NDROIStat"""
    TemplateFile = 'NDROIStatN.template'

class NDROIStat(AsynPort):
    """This plugin calculates statistics of ROIs"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = 'PORT'
    _SpecificTemplate = NDROIStatTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE=2, BLOCK=0, NDARRAY_ADDR=0,
                 MAX_ROIS=8, BUFFERS=50, MEMORY=0, NCHANS=4096, **args):
        super(NDROIStat, self).__init__(PORT)
        self.__dict__.update(locals())
        self.TIMEOUT = args['TIMEOUT']
        makeTemplateInstance(self._SpecificTemplate, locals(), args)
        self._create_roi_stat_n_templates()

    def _create_roi_stat_n_templates(self):
        for i in range(self.MAX_ROIS):
            NDROIStatNTemplate(P=self.args['P'],
                               R='{}{}:'.format(self.args['R'], i + 1),
                               NCHANS=self.NCHANS, PORT=self.PORT,
                               ADDR=i, TIMEOUT=self.TIMEOUT)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(
        __init__,
        PORT = Simple('Port name for the NDPluginROIStat plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        MAX_ROIS = Simple('Maximum number of ROIs in this plugin', int),
        BUFFERS = Simple('Max buffers to allocate', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer '
                        'for driver and all attached plugins', int),
        NCHANS = Simple('Number of points in the arrays', int))

    def Initialise(self):
        print('# NDROIStatConfigure(portName, queueSize, blockingCallbacks, '
              'NDArrayPort, NDArrayAddr, maxROIs, maxBuffers, maxMemory)')
        print('NDROIStatConfigure("{PORT}", {QUEUE}, {BLOCK}, '
              '"{NDARRAY_PORT}", {NDARRAY_ADDR}, {MAX_ROIS}, '
              '{BUFFERS}, {MEMORY})'.format(**self.__dict__))

#############################

@includesTemplates(NDPluginBaseTemplate)
class NDAttributeTemplate(AutoSubstitution):
    """Template containing the records for an NDAttribute"""
    TemplateFile = 'NDAttribute.template'

class NDAttributeNTemplate(AutoSubstitution):
    """Template containing the records for an NDAttribute"""
    TemplateFile = 'NDAttributeN.template'

class NDAttribute(AsynPort):
    """This plugin displays NDArray attributes"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = 'PORT'
    _SpecificTemplate = NDAttributeTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE=2, BLOCK=0, NDARRAY_ADDR=0,
                 MAX_ATTRIBUTES=8, BUFFERS=50, MEMORY=0, NCHANS=4096, **args):
        super(NDAttribute, self).__init__(PORT)
        self.__dict__.update(locals())
        self.TIMEOUT = args['TIMEOUT']
        makeTemplateInstance(self._SpecificTemplate, locals(), args)
        self._create_attribute_n_templates()

    def _create_attribute_n_templates(self):
        """Instanciate self.MAX_ATTRIBUTES number of NDattributeN templates

        Override this method when extending the NDAttributeN template
        """
        for i in range(self.MAX_ATTRIBUTES):
            NDAttributeNTemplate(P=self.args['P'],
                                 R='{}{}:'.format(self.args['R'], i + 1),
                                 NCHANS=self.NCHANS, PORT=self.PORT,
                                 ADDR=i, TIMEOUT=self.TIMEOUT)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(
        __init__,
        PORT = Simple('Port name for the NDAttribute plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        MAX_ATTRIBUTES = Simple('Maximum number of attributes in this plugin',
                                int),
        BUFFERS = Simple('Max buffers to allocate', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer '
                        'for driver and all attached plugins', int),
        NCHANS = Simple('Number of points in the arrays', int))

    def Initialise(self):
        print('# NDAttrConfigure(portName, queueSize, blockingCallbacks, '
              'NDArrayPort, NDArrayAddr, maxAttributes, maxBuffers, maxMemory)')
        print('NDAttrConfigure("{PORT}", {QUEUE}, {BLOCK}, '
              '"{NDARRAY_PORT}", {NDARRAY_ADDR}, {MAX_ATTRIBUTES}, '
              '{BUFFERS}, {MEMORY})'.format(**self.__dict__))

#############################

@includesTemplates(NDPluginBaseTemplate)
class NDColorConvertTemplate(AutoSubstitution):
    """Template containing the records for an NDColorConvert"""
    TemplateFile = 'NDColorConvert.template'

class NDColorConvert(AsynPort):
    """This plugin converts arrays from one colour type to another, e.g. Bayer -> RGB1"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDColorConvertTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, BUFFERS = 50, MEMORY = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDColorConvert plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        BUFFERS = Simple('Max buffers to allocate', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all attached plugins', int))

    def Initialise(self):
        print '# NDColorConvertConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory)' % self.__dict__
        print 'NDColorConvertConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(BUFFERS)d, %(MEMORY)d)' % self.__dict__

#############################

@includesTemplates(NDPluginBaseTemplate)
class NDPosPluginTemplate(AutoSubstitution):
    TemplateFile = 'NDPosPlugin.template'

class NDPosPlugin(AsynPort):
    """This plugin attaches position information to NDArrays"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDPosPluginTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, BUFFERS = 50, MEMORY = 0, PRIORITY = 0, STACKSIZE = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDPosPlugin plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        BUFFERS = Simple('Max buffers to allocate', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all attached plugins', int),
        PRIORITY = Simple('Max buffers to allocate', int),
        STACKSIZE = Simple('Max buffers to allocate', int))

    def Initialise(self):
        print '# NDPosPluginConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory, priority, stackSize)' % self.__dict__
        print 'NDPosPluginConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(BUFFERS)d, %(MEMORY)d, %(PRIORITY)d, %(STACKSIZE)d)' % self.__dict__

#############################

@includesTemplates(NDPluginBaseTemplate)
class NDPvaTemplate(AutoSubstitution):
    TemplateFile = 'NDPva.template'

class NDPvaPlugin(AsynPort):
    """This plugin makes NDArrays available through PVAccess"""
    Dependencies = (pvAccessCPP, pvDatabaseCPP, pvDataCPP, normativeTypesCPP)
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDPvaTemplate

    def __init__(self, PORT, NDARRAY_PORT, PVNAME, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, MEMORY = 0, PRIORITY = 0, STACKSIZE = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDPosPlugin plugin', str),
        PVNAME = Simple('Name of the PV to post NDArray out on', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        MEMORY = Simple('Max memory to allocate, should be maxw*maxh*nbuffer for driver and all attached plugins', int),
        PRIORITY = Simple('Max buffers to allocate', int),
        STACKSIZE = Simple('Max buffers to allocate', int))

    DbdFileList = ['NDPluginPva']
    LibFileList = ['ntndArrayConverter']

    def Initialise(self):
        print '# NDPvaConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, pvName, maxMemory, priority, stackSize)' % self.__dict__
        print 'NDPvaConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(PVNAME)s, %(MEMORY)d, %(PRIORITY)d, %(STACKSIZE)d)' % self.__dict__

##############################

class NDAttributes(Device):
    """Add an attribute to the NDAttributes file for a particular ADDriver or
    NDPlugin, and associate it with the NDAttributes file"""

    _xmlfiles = {}
    done = False

    def __init__(self, port, source, name = None, attrname = None, type = "EPICS_PV", dbrtype = "DBR_NATIVE", datatype = "INT", description = "", addr = 0):
        self.__super.__init__()
        if port.DeviceName() not in self._xmlfiles:
            # write the tables to disk
            impl = xml.dom.minidom.getDOMImplementation()
            doc = impl.createDocument(None, 'Attributes', None)            
            doc.port = port
            doc.ds = IocDataStream(port.DeviceName() + ".xml")
            self._xmlfiles[port.DeviceName()] = doc            
        else:
            doc = self._xmlfiles[port.DeviceName()]
        if attrname is None:
            attrname = "%s.%s" % (port.DeviceName(), source)
        el = doc.createElement("Attribute")
        doc.documentElement.appendChild(el)
        d = dict(name=attrname, type=type, source=source, description=description)
        if type == "EPICS_PV":
            d["dbrtype"] = dbrtype
        else:
            d["datatype"] = datatype
            d["addr"] = addr
        for k,v in d.items():
            el.setAttribute(k, str(v))            

    def PostIocInitialise(self):
        if not NDAttributes.done:
            for doc in self._xmlfiles.values():                
                doc.ds.write(doc.toprettyxml())
                print "dbpf %s%sNDAttributesFile, %s/%s.xml" % (doc.port.args["P"],
                        doc.port.args["R"], doc.ds.GetDataPath(), doc.port.DeviceName())
            NDAttributes.done = True

    ArgInfo = makeArgInfo(__init__,
        name = Simple("Object name. You do not need to specify this"),
        attrname = Simple("Name of the attribute. If you leave this blank it defaults to <source>"),
        port = Ident("ADDriver or NDPlugin to attach xml file to", AsynPort),
        source = Simple("The EPICS PV (if type=EPICS_PV) or attribute name (if type=PARAM)"),
        type = Choice("Where the data should be picked up from", ["EPICS_PV", "PARAM"]),
        dbrtype = Choice("DBR type (only used if type=EPICS_PV)", ["DBR_CHAR", "DBR_SHORT", "DBR_ENUM", "DBR_INT", "DBR_LONG", "DBR_FLOAT", "DBR_STRING", "DBR_NATIVE"]),
        datatype = Choice("Data type (only used if type=PARAM)", ["INT", "DOUBLE", "STRING"]),
        description = Simple("Description of the attribute"),
        addr = Simple("Asyn address of the parameter (only used if type=PARAM)", int))
        
