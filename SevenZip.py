# -*- coding: utf-8 -*-
# $Id: SevenZip.py 623 2009-04-21 18:54:22Z jonhogg $
# Unpacker that uses 7-zip to extract the contents of the archive

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
import tempfile
import datetime

# This module repeats some of the work WurmCommon does - it should stay as standalone as possible
if os.name == 'nt':
    # TODO: Make this less of an "if-else tree"
    unpackerpath = os.path.join(os.environ["PROGRAMFILES"], "7-zip", "7z.exe") # default installation directory
    if not os.path.exists(unpackerpath):
        # Check if there is a 64 bit Program Files
        if os.environ.has_key("PROGRAMW6432"):
            #unpackerpath = os.path.join(os.environ["PROGRAMW6432"], "7-zip", "7z.exe") # default installation directory for 64bit version
            # 64-bit 7-zip won't work on 32-bit python; you don't get the stdout from it at all
            # TODO: Fix this in the future
            pass
        if not os.path.exists(unpackerpath):
            # Check WUU directory
            if os.path.exists(os.path.join(os.path.dirname(sys.argv[0]), "7z.exe")):
                unpackerpath = os.path.join(os.path.dirname(sys.argv[0]), "7z.exe")
            else: # Last try before hardcoded: Search in %PATH%
                for ospath in os.getenv('PATH').split(':') + ['./']:
                    if os.path.isfile(os.path.join(ospath, '7z.exe')):
                        unpackerpath = os.path.join(ospath, '7z.exe')
                        break
else:
    unpackerpath = False

tempdir = tempfile.gettempdir()


def isAvailable():
    """ Returns True if 7-zip command line client is available """
    tracer.debug("7z-isAvailable")
    global unpackerpath
    
    if not unpackerpath:
        return False
    
    return os.path.exists(unpackerpath)


class SevenZipException(Exception):
    def __init__(self, error):
        """"""
        tracer.debug("SevenZipException - __init__")
        
        self.error = error
    
    
    def __str__(self):
        """"""
        tracer.debug("SevenZipException - __str__")
        
        return self.error
    


def _quote(path): # adds quotes to the path, if necessary
    """"""
    if ' ' in path:
        return '"%s"' % (path)
    else:
        return path


class SevenZipFile:
    def __init__(self, filename):
        """"""
        tracer.debug("SevenZipFile - __init__")
        
        if not unpackerpath:
            raise SevenZipException, "Couldn't find 7z.exe"
        if not unpackerpath:
            raise SevenZipException, "Couldn't find 7z.exe"
        if not os.path.exists(unpackerpath):
            raise SevenZipException, "Can't find 7z.exe at %s" % (unpackerpath)
        if not tempdir or not os.path.exists(tempdir):
            raise SevenZipException, "No temporary directory defined or directory does not exist"
        if not os.path.exists(filename):
            raise SevenZipException, "%s does not exist" % (filename)
        
        self.fn = filename
        
        # Index the file
        commandline = '%s l %s' % (_quote(unpackerpath), _quote(filename))
        (fin, fout) = os.popen4(commandline)
        index = fout.readlines()
        fout.close()
        fin.close()
        
        if len(index) < 9:
            print index
            raise SevenZipException, "Could not execute %s or file empty" % (commandline)
        
        self.fileindex = {}
        
        for zf in index[7:-2]:
            try:
                datetime.datetime.strptime(zf[:10], "%Y-%m-%d") # verification that this is a correct line
            except ValueError:
                continue
            
            (fdate, ftime, fattr, fsize, fcomp, fname) = zf.split()
            self.fileindex[fname] = (fdate, ftime, fattr, fsize, fcomp)
    
    
    def filelist(self):
        """ Returns a list of files in the archive """
        tracer.debug("SevenZipFile - filelist")
        
        return self.fileindex.keys()
    
    
    def extract(self, archivefn, targetdir):
        """ Extracts a single file "archivefn" from the archive to "targetdir" """
        tracer.debug("SevenZipFile - extract")
        
        if archivefn not in self.fileindex:
            raise SevenZipException, "Trying to extract nonexistant file %s" % (archivefn)
        
        if self.fileindex[archivefn][3][0] == 'D': # Checking the attributes; the first attribute is 'D' if this is a directory
            return True # directories are silently ignored, since we decide explicitly where we want the files
        
        commandline = '%s e -y -o%s %s %s' % (_quote(unpackerpath), _quote(targetdir), _quote(self.fn), _quote(archivefn))
        f = os.popen(commandline)
        status = f.readlines()
        f.close()
        if 'Everything is Ok\n' in status:
            return True
        else:
            raise SevenZipException, "NO OUTPUT? "+"|".join([s.strip() for s in status]) #("|".join([s.strip() for s in status[3:] if s not in ('\n', '\r')])) # tries to format the output from 7z.exe in a relatively OK way ;)
    

