# -*- coding: utf-8 -*-
# $Id: RarFile.py 638 2009-04-28 11:58:39Z lejordet $
# Unpacker that uses UnRaR/RaR to extract the contents of the archive

# Copyright (c) 2006-2009 The WUU Development Team
#
# This software is provided 'as-is', without any express or implied warranty. In no event will the
# authors be held liable for any damages arising from the use of this software.
#
# Permission is granted to anyone to use this software for any purpose, including commercial applications,
# and to alter it and redistribute it freely, subject to the following restrictions:
#
#    1. The origin of this software must not be misrepresented; you must not claim that you
#    wrote the original software. If you use this software in a product, an acknowledgment
#    in the product documentation would be appreciated but is not required.
#
#    2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
#
#    3. This notice may not be removed or altered from any source distribution.

import logging
logger = logging.getLogger(None)
tracer = logging.getLogger("WUUtrace")

import os, sys

import WurmCommon

# check to see if unrar/rar exists
rar = None # must be defined regardless of OS
if os.name != 'nt':
    for ospath in os.getenv('PATH').split(':') + ['./']:
        if os.path.isfile(os.path.join(ospath, 'unrar')):
            rar = 'unrar'
            break
        elif os.path.isfile(os.path.join(ospath, 'rar')):
            rar = 'rar'
            break

# Handle unrar/rar not on the Path on a Mac
# try the default directory
if not rar and sys.platform == 'darwin':
    ulb = '/usr/local/bin'
    olb = '/opt/local/bin'

    if os.path.isfile(os.path.join(ulb, 'unrar')):
        rar = os.path.join(ulb, 'unrar')
    elif os.path.isfile(os.path.join(ulb, 'rar')):
        rar = os.path.join(ulb, 'rar')
    elif os.path.isfile(os.path.join(olb, 'unrar')):
        rar = os.path.join(olb, 'unrar')
    elif os.path.isfile(os.path.join(olb, 'rar')):
        rar = os.path.join(olb, 'rar')



class RarFileException(Exception):
    def __init__(self, error):
        """Initial Setup"""
        tracer.debug("RarFileException - __init__")
        
        self.error = error
    
    
    def __str__(self):
        """Return the Error string"""
        tracer.debug("RarFileException - __str__")
        
        return self.error
    


class RarFile:
    def __init__(self, filename):
        """Initial Setup"""
        tracer.debug("RarFile - __init__")
        
        if not rar:
            raise RarFileException, "No rar/unrar binaries found - RAR support disabled"
        if not os.path.exists(filename):
            raise RarFileException, "%s does not exist" % (filename)
        
        self.fn = filename
        
        # command line options (v -> verbose, b -> bare)
        raropts = "vb"
        rarcmd  = "%s %s \"%s\"" % (rar, raropts, self.fn)
        logger.log(WurmCommon.DEBUG5, "rarcmd: %s" % (rarcmd))
        self.filelist = []
        for line in os.popen(rarcmd).readlines():
            # remove trailing whitespace and newline
            line = line.rstrip()
            logger.log(WurmCommon.DEBUG5, "rar line: %s" % (line))
            self.filelist.append(line)
    
    
    def listfiles(self):
        """ Returns a list of files in the archive """
        tracer.log(WurmCommon.DEBUG5, "RarFile - filelist")
        
        return self.filelist
    
    
    def extract(self, archivefn, targetdir, opts=""):
        """ Extracts a single file "archivefn" from the archive to "targetdir" """
        tracer.debug("RarFile - extract")
        
        if archivefn not in self.filelist:
            raise RarFileException, "Trying to extract nonexistant file %s" % (archivefn)
        
        # command line options (x -> extract, -o+ -> overwrite existing files)
        raropts = "%s %s" % ("x -o+", opts)
        rarcmd  = "%s %s \"%s\" \"%s\" \"%s\"" % (rar, raropts, self.fn, archivefn, targetdir)
        logger.log(WurmCommon.DEBUG5, "rarcmd: %s" % (rarcmd))
        cmdoutput = []
        for line in os.popen(rarcmd).readlines():
            # remove trailing whitespace and newline
            line = line.rstrip()
            logger.log(WurmCommon.DEBUG5, "RarFile - extract: %s" % (line))
            cmdoutput.append(line)
        
        if "All OK" in cmdoutput:
            return True
        else:
            raise RarFileException, "Error extracting %s from %s:\n%s" % (archivefn, self.fn, cmdoutput)
    

