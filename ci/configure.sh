#!/bin/bash
# Configure ADCore in preparation for build
# Make sure we exit on any error
set -e

# Remove the RELEASE.linux-x86_64.Common file
rm configure/RELEASE.local
rm configure/RELEASE.linux-x86_64.Common
rm configure/CONFIG_SITE.linux-x86_64.Common

# Generate the configure/RELEASE.local and configure/CONFIG_SITE.linux-x86_64.Common
# with the details of where to find various external libraries.
echo "EPICS_BASE=/usr/lib/epics"             >> configure/RELEASE.local
echo "HDF5=/usr"                             >> configure/CONFIG_SITE.linux-x86_64.Common
echo "HDF5_LIB=/usr/lib/x86_64-linux-gnu"    >> configure/CONFIG_SITE.linux-x86_64.Common
echo "HDF5_INCLUDE=-I/usr/include"           >> configure/CONFIG_SITE.linux-x86_64.Common
#echo "SZIP=/usr"                             >> configure/CONFIG_SITE.linux-x86_64.Common
#echo "SZIP_LIB=/usr/lib/x86_64-linux-gnu"    >> configure/CONFIG_SITE.linux-x86_64.Common
#echo "SZIP_INCLUDE=-I/usr/include"           >> configure/CONFIG_SITE.linux-x86_64.Common
echo "XML2_INCLUDE=-I/usr/include/libxml2"   >> configure/CONFIG_SITE.linux-x86_64.Common
echo "BOOST=/usr"                            >> configure/CONFIG_SITE.linux-x86_64.Common
echo "BOOST_LIB=/usr/lib/x86_64-linux-gnu"   >> configure/CONFIG_SITE.linux-x86_64.Common
echo "BOOST_INCLUDE=-I/usr/include"          >> configure/CONFIG_SITE.linux-x86_64.Common
echo "HOST_OPT=NO"                           >> configure/CONFIG_SITE.linux-x86_64.Common 
echo "USR_CXXFLAGS_Linux=--coverage"         >> configure/CONFIG_SITE.linux-x86_64.Common 
echo "USR_LDFLAGS_Linux=--coverage"          >> configure/CONFIG_SITE.linux-x86_64.Common 

echo "ASYN=`pwd`/external/asyn-R4-26"        >> configure/RELEASE.local

echo "======= configure/RELEASE.local ========================================="
cat configure/RELEASE.local

echo "======= configure/CONFIG_SITE.linux-x86_64.Common ======================="
cat configure/CONFIG_SITE.linux-x86_64.Common

