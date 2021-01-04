from __future__ import print_function
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

from dls_dependency_tree import dependency_tree

MODULE_TREE = None


def find_dependency(module, dependency):
    global MODULE_TREE
    if MODULE_TREE is None:
        MODULE_TREE = dependency_tree()
        MODULE_TREE.process_module(module)

    for macro, path in MODULE_TREE.macros.items():
        if macro == dependency:
            return path

    raise ValueError("Could not find {} in {}".format(dependency, module))


ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
HDF5_FILTERS_ROOT = find_dependency(ROOT, "HDF5_FILTERS")

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
#        SysLibFileList = ['freetype', 'Xext', 'bz2', 'png12', 'xml2', 'X11', 'gomp', 'z', 'jpeg', 'tiff']
        SysLibFileList = []
    LibFileList += ['ADBase', 'NDPlugin']
    DbdFileList = ['ADSupport', 'NDPluginSupport', 'NDFileHDF5', 'NDFileJPEG', 'NDFileTIFF', 'NDFileNull',
                   'NDPosPlugin']
    AutoInstantiate = True

#############################


def scanRateOverride(cls):
    cls.ArgInfo.descriptions["SCANRATE"] = Choice(
        "Specified scan rate for cpu intensive PVs",
        [".1 second", ".2 second", ".5 second", "1 second", "2 second",
         "5 second", "10 second", "I/O Intr", "Event", "Passive"])
    return cls


@scanRateOverride
class ADBaseTemplate(AutoSubstitution):
    """Template containing the base records of any areaDetector driver"""
    TemplateFile = 'ADBase.template'

#############################

@scanRateOverride
class NDPluginBaseTemplate(AutoSubstitution):
    """Template containing the base records of any areaDetector plugin"""
    TemplateFile = 'NDPluginBase.template'

#############################

@scanRateOverride
class NDFileTemplate(AutoSubstitution):
    """Template containing the records of an areaDetector file writing plugin"""
    TemplateFile = 'NDFile.template'

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
    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, MAX_THREADS = 1, **args):
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
        MAX_THREADS = Simple('Maximum number threads', int))

    ArgInfo.descriptions["FTVL"] = records.waveform.FieldInfo()["FTVL"]

    def Initialise(self):
        print('# NDStdArraysConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory, priority, stackSize, maxThreads)')
        print('NDStdArraysConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, 0, 0, 0, 0, %(MAX_THREADS)d)' % self.__dict__)


#############################

@includesTemplates(NDPluginBaseTemplate, NDFileTemplate)
class NDFileNetCDFTemplate(AutoSubstitution):
    TemplateFile = 'NDFileNetCDF.template'

class NDFileNetCDF(AsynPort):
    """This plugin can compress NDArrays to NetCDF and write them to file"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDFileNetCDFTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, **args):
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
        NDARRAY_ADDR = Simple('Input array port address', int))

    def Initialise(self):
        print('# NDFileNetCDFConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr)' % self.__dict__)
        print('NDFileNetCDFConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s)' % self.__dict__)

#############################

@includesTemplates(NDPluginBaseTemplate, NDFileTemplate)
class NDFileTIFFTemplate(AutoSubstitution):
    TemplateFile = 'NDFileTIFF.template'

class NDFileTIFF(AsynPort):
    """This plugin can compress NDArrays to TIFF and write them to file"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDFileTIFFTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, **args):
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
        NDARRAY_ADDR = Simple('Input array port address', int))

    def Initialise(self):
        print('# NDFileTIFFConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr)' % self.__dict__)
        print('NDFileTIFFConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s)' % self.__dict__)

#############################

@includesTemplates(NDPluginBaseTemplate, NDFileTemplate)
class NDFileJPEGTemplate(AutoSubstitution):
    TemplateFile = 'NDFileJPEG.template'

class NDFileJPEG(AsynPort):
    """This plugin can compress NDArrays to JPEG and write them to file"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDFileJPEGTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, **args):
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
        NDARRAY_ADDR = Simple('Input array port address', int))

    def Initialise(self):
        print('# NDFileJPEGConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr)' % self.__dict__)
        print('NDFileJPEGConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s)' % self.__dict__)

#############################

@includesTemplates(NDPluginBaseTemplate, NDFileTemplate)
class NDFileNexusTemplate(AutoSubstitution):
    TemplateFile = 'NDFileNexus.template'

class NDFileNexus(AsynPort):
    """This plugin can compress NDArrays to Nexus and write them to file"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDFileNexusTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, **args):
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
        NDARRAY_ADDR = Simple('Input array port address', int))

    def Initialise(self):
        print('# NDFileNexusConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr)' % self.__dict__)
        print('NDFileNexusConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s)' % self.__dict__)

#############################

@includesTemplates(NDPluginBaseTemplate, NDFileTemplate)
class NDFileHDF5Template(AutoSubstitution):
    TemplateFile = 'NDFileHDF5.template'

class NDFileHDF5(AsynPort):
    """This plugin can compress NDArrays to HDF5 and write them to file"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDFileHDF5Template

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, **args):
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
        NDARRAY_ADDR = Simple('Input array port address', int))

    def Initialise(self):
        print('# NDFileHDF5Configure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr)' % self.__dict__)
        print('NDFileHDF5Configure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s)' % self.__dict__)

#############################

@includesTemplates(NDPluginBaseTemplate)
class NDCodecTemplate(AutoSubstitution):
    TemplateFile = 'NDCodec.template'

class NDCodec(AsynPort):
    """This plugin can compress or decompress NDArrays"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDCodecTemplate
    EnvironmentVariables = [
        ("HDF5_PLUGIN_PATH", os.path.join(HDF5_FILTERS_ROOT, "prefix/hdf5_1.10/h5plugin"))
    ]

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, MAX_THREADS = 1, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDCodec plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        MAX_THREADS = Simple('Maximum number threads', int))

    def Initialise(self):
        print('# NDCodecConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory, priority, stackSize, maxThreads)' % self.__dict__)
        print('NDCodecConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, 0, 0, 0, 0, %(MAX_THREADS)d)' % self.__dict__)

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

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, **args):
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
        NDARRAY_ADDR = Simple('Input array port address', int))

    def Initialise(self):
        print('# NDFileMagickConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr)' % self.__dict__)
        print('NDFileMagickConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s)' % self.__dict__)

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

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, MAX_THREADS = 1, **args):
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
        MAX_THREADS = Simple('Maximum number threads', int))

    def Initialise(self):
        print('# NDROIConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory, priority, stackSize, maxThreads)' % self.__dict__)
        print('NDROIConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, 0, 0, 0, 0, %(MAX_THREADS)d)' % self.__dict__)

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

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, **args):
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
        NDARRAY_ADDR = Simple('Input array port address', int))

    def Initialise(self):
        print('# NDProcessConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr)' % self.__dict__)
        print('NDProcessConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s)' % self.__dict__)

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
    
    def __init__(self, PORT, NDARRAY_PORT, ENABLED=0, NCHANS = 2048, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, TIMEOUT=1, ADDR=0, MAX_THREADS=1, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Set args for use in Initialise()
        self.args = args
        self.args['NCHANS'] = NCHANS
        self.args['TS_PORT'] = PORT + "_TS"
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

    ArgInfo = makeArgInfo(__init__,
        PORT = Simple('Port name for the NDStats plugin', str),
        P = Simple('Device Prefix', str),
        R = Simple('Device Suffix', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        ENABLED   = Simple('Plugin Enabled at startup?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        MAX_THREADS = Simple('Maximum number threads', int),
        HIST_SIZE = Simple('Maximum size of Pixel binning histogram (e.g. 256 for Int8)', int),
        ADDR = Simple('Asyn Port address', int),
        XSIZE = Simple('XSIZE, Maximum size of X histograms (e.g. 1024)', int),
        YSIZE = Simple('Maximum size of Y histograms (e.g. 768)', int),
        TIMEOUT = Simple('Timeout', int),
        NCHANS = Simple('Maximum length of time series (initialises waveform NELM, fixed on IOC boot)', int))

    def InitialiseOnce(self):
        # Set ADCore path so NDTimeSeries.template can find base plugin template
        print('# ADCore path for manual NDTimeSeries.template to find base plugin template')
        print('epicsEnvSet "EPICS_DB_INCLUDE_PATH", "$(ADCORE)/db"\n')

    def Initialise(self):
        print('# NDStatsConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory, priority, stackSize, maxThreads)' % self.__dict__)
        print('NDStatsConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, 0, 0, 0, 0, %(MAX_THREADS)d)' % self.__dict__)

        print('# NDTimeSeriesConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxSignals)' % self.__dict__)
        print('NDTimeSeriesConfigure("%(PORT)s_TS", %(QUEUE)d, %(BLOCK)d, "%(PORT)s", 1, 23)' % self.__dict__)

        # Manually load the time series template so we do not end up with the embedded EDM tab
        print('# Load time series records')
        print('dbLoadRecords("$(ADCORE)/db/NDTimeSeries.template",  "P={P},R={R}, PORT={PORT} ,ADDR={ADDR},TIMEOUT={TIMEOUT},NDARRAY_PORT={NDARRAY_PORT},NDARRAY_ADDR={NDARRAY_ADDR},NCHANS={NCHANS},ENABLED={ENABLED}")'.format(
            P=self.args['P'], R=self.args['R'] + 'TS:', PORT=self.args['TS_PORT'], ADDR=0, TIMEOUT=1, NDARRAY_PORT=self.PORT, NDARRAY_ADDR=1, NCHANS=self.args['NCHANS'], ENABLED=1)
        )



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

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, MAX_THREADS = 1, **args):
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
        MAX_THREADS = Simple('Maximum number threads', int))

    def Initialise(self):
        print('# NDTransformConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory, priority, stackSize, maxThreads)' % self.__dict__)
        print('NDTransformConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, 0, 0, 0, 0, %(MAX_THREADS)d)' % self.__dict__)

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

    def __init__(self, PORT, NDARRAY_PORT, TIMEOUT=1, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, MAX_THREADS = 1, **args):
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
                YSIZE = "", XWIDTH = "", YWIDTH = "", PORT = PORT, ADDR = i, TIMEOUT = self.TIMEOUT)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDOverlay plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        TIMEOUT = Simple('Timeout', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        MAX_THREADS = Simple('Maximum number threads', int))

    def Initialise(self):
        print('# NDOverlayConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, NOverlays, maxBuffers, maxMemory, priority, stackSize, maxThreads)')
        print('NDOverlayConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(NOverlays)d, 0, 0, 0, 0, %(MAX_THREADS)d)' % self.__dict__)

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

    def __init__(self, PORT, NDARRAY_PORT, TIMEOUT=1, QUEUE=2, BLOCK=0, NDARRAY_ADDR=0,
                 MAX_ROIS=8, NCHANS=4096, MAX_THREADS=1, **args):
        super(NDROIStat, self).__init__(PORT)
        self.__dict__.update(locals())
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
        TIMEOUT = Simple('Timeout', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        MAX_ROIS = Simple('Maximum number of ROIs in this plugin', int),
        NCHANS = Simple('Number of points in the arrays', int),
        MAX_THREADS = Simple('Maximum number threads', int))

    def Initialise(self):
        print('# NDROIStatConfigure(portName, queueSize, blockingCallbacks, '
              'NDArrayPort, NDArrayAddr, maxROIs, maxBuffers, maxMemory,'
              'priority', 'stackSize', 'maxThreads')
        print('NDROIStatConfigure("{PORT}", {QUEUE}, {BLOCK}, '
              '"{NDARRAY_PORT}", {NDARRAY_ADDR}, {MAX_ROIS}, '
              '0, 0, 0, 0, {MAX_THREADS})'.format(**self.__dict__))

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

    def __init__(self, PORT, NDARRAY_PORT, TIMEOUT=1, QUEUE=2, BLOCK=0, NDARRAY_ADDR=0,
                 MAX_ATTRIBUTES=8, NCHANS=4096, **args):
        super(NDAttribute, self).__init__(PORT)
        self.__dict__.update(locals())
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
        TIMEOUT = Simple('Timeout', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        MAX_ATTRIBUTES = Simple('Maximum number of attributes in this plugin', int),
        NCHANS = Simple('Number of points in the arrays', int))

    def InitialiseOnce(self):
        # Set ADCore path so NDTimeSeries.template can find base plugin template
        print('# ADCore path for manual NDTimeSeries.template to find base plugin template')
        print('epicsEnvSet "EPICS_DB_INCLUDE_PATH", "$(ADCORE)/db"\n')

    def Initialise(self):
        print('# NDAttrConfigure(portName, queueSize, blockingCallbacks, '
              'NDArrayPort, NDArrayAddr, maxAttributes)')
        print('NDAttrConfigure("{PORT}", {QUEUE}, {BLOCK}, '
              '"{NDARRAY_PORT}", {NDARRAY_ADDR}, {MAX_ATTRIBUTES})'.format(**self.__dict__))

        # Load timeseries (built-in TS removed in 3.5)
        print('# NDTimeSeriesConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxSignals)')
        print('NDTimeSeriesConfigure("{PORT:s}_TS", {QUEUE:d}, {BLOCK:d}, "{PORT:s}", 1, {MAX_ATTRIBUTES:d})'.format(**self.__dict__))

        # Manually load the time series template so we do not end up with the embedded EDM tab
        print('# Load time series records')
        print('dbLoadRecords("$(ADCORE)/db/NDTimeSeries.template","P={P},R={R_TS},PORT={PORT},ADDR=0,TIMEOUT={TIMEOUT},NDARRAY_PORT={PORT},NDARRAY_ADDR=1,NCHANS={MAX_ATTRIBUTES},ENABLED=1")'.format(
            R_TS=self.args['R']+'TS:', P=self.args['P'], **self.__dict__)
        )

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

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, MAX_THREADS = 1, **args):
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
        MAX_THREADS = Simple('Maximum number threads', int))

    def Initialise(self):
        print('# NDColorConvertConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory, priority, stackSize, maxThreads)' % self.__dict__)
        print('NDColorConvertConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, 0, 0, 0, 0, %(MAX_THREADS)d)' % self.__dict__)

#############################

@scanRateOverride
@includesTemplates(NDPluginBaseTemplate)
class NDPosPluginTemplate(AutoSubstitution):
    TemplateFile = 'NDPosPlugin.template'

class NDPosPlugin(AsynPort):
    """This plugin attaches position information to NDArrays"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDPosPluginTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, PRIORITY = 0, STACKSIZE = 0, **args):
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
        PRIORITY = Simple('Max buffers to allocate', int),
        STACKSIZE = Simple('Max buffers to allocate', int))

    def Initialise(self):
        print('# NDPosPluginConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory, priority, stackSize)' % self.__dict__)
        print('NDPosPluginConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, 0, 0, %(PRIORITY)d, %(STACKSIZE)d)' % self.__dict__)

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

    def __init__(self, PORT, NDARRAY_PORT, PVNAME, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, PRIORITY = 0, STACKSIZE = 0, **args):
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
        PRIORITY = Simple('Max buffers to allocate', int),
        STACKSIZE = Simple('Max buffers to allocate', int))

    DbdFileList = ['NDPluginPva']
    LibFileList = ['ntndArrayConverter']

    def Initialise(self):
        print('# NDPvaConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, pvName, maxBuffers, maxMemory, priority, stackSize)' % self.__dict__)
        print('NDPvaConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(PVNAME)s, 0, 0, %(PRIORITY)d, %(STACKSIZE)d)' % self.__dict__)
        print('startPVAServer')

#############################

@includesTemplates(NDPluginBaseTemplate)
class NDTimeSeriesTemplate(AutoSubstitution):
    """Template containing the records for an NDTimeSeries"""
    TemplateFile = 'NDTimeSeries.template'

class NDTimeSeries(AsynPort):
    """This plugin captures time series data from other asyn ports"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDTimeSeriesTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, MAX_SIGNALS = 1, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDTimeSeries plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        MAX_SIGNALS = Simple('Max number of signals to capture', int))

    def Initialise(self):
        print('# NDTimeSeriesConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxSignals)' % self.__dict__)
        print('NDTimeSeriesConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(MAX_SIGNALS)s)' % self.__dict__)

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
                print("dbpf %s%sNDAttributesFile, %s/%s.xml" % (doc.port.args["P"],
                        doc.port.args["R"], doc.ds.GetDataPath(), doc.port.DeviceName()))
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

##############################


@includesTemplates(NDPluginBaseTemplate)
class _NDCircularBuff(AutoSubstitution):
    TemplateFile = 'NDCircularBuff.template'


class NDCircularBuff(AsynPort):
    """This plugin provides a pre and post external trigger frame capture buffer"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    Dependencies = (ADCore,)
    _SpecificTemplate = _NDCircularBuff

    def __init__(self, PORT, NDARRAY_PORT, QUEUE=50, BLOCK=0, NDARRAY_ADDR=0,
                 ENABLED=1, MAX_BUFFERS=128, **args):
        # args["Enabled"] = Enabled
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    # __init__ arguments
    # NOTE: _NDPluginBase comes 2nd so we overwrite NDARRAY_PORT argInfo
    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT         = Simple('Port name for the FFT_calc plugin', str),
        ENABLED      = Simple('Plugin Enabled at startup?', int),
        QUEUE        = Simple('Input array queue size', int),
        BLOCK        = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        MAX_BUFFERS   = Simple('Max buffer size in number of frames', int))

    def Initialise(self):
        print('# NDCircularBuffConfigure(portName, queueSize, blockingCallbacks, ' \
              'NDArrayPort, NDArrayAddr, maxBuffers, maxMemory, priority, stackSize)')
        print('NDCircularBuffConfigure(' \
              '"%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", ' \
              '%(NDARRAY_ADDR)s, %(MAX_BUFFERS)s, 0, 0, 0)' % self.__dict__)

##############################


@includesTemplates(NDPluginBaseTemplate)
class _NDAttrPlotTemplate(AutoSubstitution):
    TemplateFile = 'NDAttrPlot.template'

class _NDAttrPlotDataTemplate(AutoSubstitution):
    TemplateFile = 'NDAttrPlotData.template'

class _NDAttrPlotAttrTemplate(AutoSubstitution):
    TemplateFile = 'NDAttrPlotAttr.template'

class NDAttrPlot(AsynPort):
    UniqueName = "PORT"
    N_Y_BLOCKS = 4
    N_ATTRS = 198

    Dependencies = (Asyn,)
    _SpecificTemplate = _NDAttrPlotTemplate

    def __init__(self, PORT, NDARRAY_PORT, QUEUE = 10000, N_CACHE = 10000,
            NDARRAY_ADDR = 0, BLOCK = 0, **args):
        self.__super.__init__(PORT)
        self.__dict__.update(locals())
        self.__dict__["N_BLOCKS"] = 1 + 2 * self.N_Y_BLOCKS # X(1) + Y1(4) + Y2(4)
        self.__dict__["N_ATTRS"] = self.N_ATTRS
        makeTemplateInstance(self._SpecificTemplate, locals(), args)
        locals().update(args)

        data_addr = 0
        makeTemplateInstance(_NDAttrPlotDataTemplate, locals(),
                {'DATA_IND' : "", "AXIS" : "X", "DATA_ADDR" : data_addr})
        data_addr += 1;
        for i in range(self.N_Y_BLOCKS):
                makeTemplateInstance(_NDAttrPlotDataTemplate, locals(),
                        {'DATA_IND' : i, "AXIS" : "Y1", "DATA_ADDR" : data_addr})
                data_addr += 1;
        for i in range(self.N_Y_BLOCKS):
                makeTemplateInstance(_NDAttrPlotDataTemplate, locals(),
                        {'DATA_IND' : i, "AXIS" : "Y2", "DATA_ADDR" : data_addr})
                data_addr += 1;

        for i in range(self.N_ATTRS):
            makeTemplateInstance(_NDAttrPlotAttrTemplate, locals(),
                    {'ATTR_IND' : ("%d" % i)})

    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
            PORT = Simple("Asyn port name", str),
            QUEUE = Simple('Input array queue size', int),
            BLOCK = Simple('Blocking callbacks?', int),
            NDARRAY_PORT = Ident("Asyn port of the callback source", AsynPort),
            NDARRAY_ADDR = Simple("Asyn address of the callback source", int),
            N_CACHE  = Simple("Number of NDArrays to store in cache", int))

    def Initialise(self):
        print ('NDAttrPlotConfig("%(PORT)s", %(N_ATTRS)d, %(N_CACHE)d, '
               '%(N_BLOCKS)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)d, '
               '%(QUEUE)d, %(BLOCK)d)' % self.__dict__ )

#############################


@includesTemplates(NDPluginBaseTemplate)
class NDTimeSeriesTemplate(AutoSubstitution):
    """Template containing the records for a NDTimeSeries"""
    TemplateFile = 'NDTimeSeries.template'

class NDTimeSeriesNTemplate(AutoSubstitution):
    """Template containing records for individual signals in NDTimeSeries"""
    TemplateFile = 'NDTimeSeriesN.template'

class NDTimeSeries(AsynPort):
    """This plugin creates time series arrays from callback data"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDTimeSeriesTemplate
    def __init__(self, PORT, NDARRAY_PORT, TIMEOUT=1, NSIGNALS = 1, QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, PRIORITY = 0, STACKSIZE = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the command line args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)
        # Create each time series signal
        self.createNSignalsTimeSeriesNTemplates(P = args["P"], R = args["R"], 
            PORT = PORT, NSIGNALS = NSIGNALS, TIMEOUT = TIMEOUT, 
            NCHANS = args["NCHANS"])

    def createNSignalsTimeSeriesNTemplates(self, P, R, PORT, NSIGNALS, 
            TIMEOUT, NCHANS):
        # Instantiate a template for each signal
        for i in range(NSIGNALS):
            # Append signal number to R suffix
            RSignal = R + str(i) + ":"
            TSName = "TS" + str(i)
            NDTimeSeriesNTemplate(P = P, R = RSignal, PORT = PORT, ADDR = i, 
                TIMEOUT = TIMEOUT, NCHANS = NCHANS, NAME = TSName)

    # __init__ arguments
    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDTimeSeries plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        TIMEOUT = Simple('Timeout', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        NSIGNALS = Simple('Maximum number of time series signals', int),
        PRIORITY = Simple('Thread priority if ASYN_CANBLOCK is set ', int),
        STACKSIZE = Simple('Stack size if ASYN_CANBLOCK is set', int))

    def Initialise(self):
        print('# NDTimeSeriesConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxSignals, maxBuffers, maxMemory, priority, stackSize)')
        print('NDTimeSeriesConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, %(NSIGNALS)d, 0, 0, %(PRIORITY)d, %(STACKSIZE)d)' % self.__dict__)

#############################


@includesTemplates(NDPluginBaseTemplate)
class NDFFTTemplate(AutoSubstitution):
    """Template containing the records for the NDFFT plugin"""
    TemplateFile = 'NDFFT.template'

class NDFFT(AsynPort):
    """This plugin is used to calculate the FFT of a time series"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDFFTTemplate
    def __init__(self, PORT, NDARRAY_PORT, NAME = "", QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, PRIORITY = 0, STACKSIZE = 0, MAX_THREADS = 1, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    # __init__ arguments
    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDTimeSeries plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        NAME = Simple('Label for signal', int),
        PRIORITY = Simple('Thread priority if ASYN_CANBLOCK is set ', int),
        STACKSIZE = Simple('Stack size if ASYN_CANBLOCK is set', int),
        MAX_THREADS = Simple('Maximum number threads', int))

    def Initialise(self):
        print('# NDFFTConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr, maxBuffers, maxMemory, priority, stackSize, maxThreads)')
        print('NDFFTConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s, 0, 0, %(PRIORITY)d, %(STACKSIZE)d, %(MAX_THREADS)d)' % self.__dict__)


#############################


@includesTemplates(NDPluginBaseTemplate)
class NDGatherTemplate(AutoSubstitution):
    """Template containing the records for the NDGather plugin"""
    TemplateFile = 'NDGather.template'


class NDGatherNTemplate(AutoSubstitution):
    """Template containing records for individual signals in NDGather"""
    TemplateFile = 'NDGatherN.template'

class NDGather(AsynPort):
    """This plugin is used to gather NDArrays from multiple upstream plugins and merge them into a single stream"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDGatherTemplate
    def __init__(self, PORT, QUEUE = 2, BLOCK = 0, MAX_PORTS = 5, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    # __init__ arguments
    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDGather plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        MAX_PORTS = Simple('Maximum number of ports that this plugin can connect to for callbacks', int))

    def Initialise(self):
        print('# NDGatherConfigure(portName, queueSize, blockingCallbacks, maxPorts)')
        print('NDGatherConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(MAX_PORTS)d")' % self.__dict__)

class NDGather8(Device):
    """This plugin is used to gather NDArrays from multiple upstream plugins and merge them into a single stream"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    def __init__(self, PORT, QUEUE = 2, BLOCK = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__()
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        numPorts = 8
        self.ndGather = NDGather(PORT, QUEUE, BLOCK, numPorts, **args)
        self.ndNGathers = []
        for n in range(numPorts):
            templateargs = dict(
                P=args["P"],
                R=args["R"],
                N=n+1,
                NDARRAY_PORT=args["NDARRAY_PORT"],
                PORT=PORT,
                ADDR=n)
            self.ndNGathers.append(NDGatherNTemplate(**templateargs))

    # __init__ arguments
    ArgInfo = NDGather.ArgInfo.filtered(without = ['MAX_PORTS'])

#############################


@includesTemplates(NDPluginBaseTemplate)
class NDScatterTemplate(AutoSubstitution):
    """Template containing the records for the NDScatter plugin"""
    TemplateFile = 'NDScatter.template'

class NDScatter(AsynPort):
    """This plugin is used to distribute processing of NDArrays to multiple downstream plugins"""
    # This tells xmlbuilder to use PORT instead of name as the row ID
    UniqueName = "PORT"
    _SpecificTemplate = NDScatterTemplate
    def __init__(self, PORT, NDARRAY_PORT, NAME = "", QUEUE = 2, BLOCK = 0, NDARRAY_ADDR = 0, **args):
        # Init the superclass (AsynPort)
        self.__super.__init__(PORT)
        # Update the attributes of self from the commandline args
        self.__dict__.update(locals())
        # Make an instance of our template
        makeTemplateInstance(self._SpecificTemplate, locals(), args)

    # __init__ arguments
    ArgInfo = _SpecificTemplate.ArgInfo + makeArgInfo(__init__,
        PORT = Simple('Port name for the NDTimeSeries plugin', str),
        QUEUE = Simple('Input array queue size', int),
        BLOCK = Simple('Blocking callbacks?', int),
        NDARRAY_PORT = Ident('Input array port', AsynPort),
        NDARRAY_ADDR = Simple('Input array port address', int),
        NAME = Simple('Label for signal', int))

    def Initialise(self):
        print('# NDScatterConfigure(portName, queueSize, blockingCallbacks, NDArrayPort, NDArrayAddr)')
        print('NDScatterConfigure("%(PORT)s", %(QUEUE)d, %(BLOCK)d, "%(NDARRAY_PORT)s", %(NDARRAY_ADDR)s)' % self.__dict__)


#############################
