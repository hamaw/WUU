# -*- coding: utf-8 -*-
# $Id: WurmUnpack.py 645 2009-05-04 20:30:53Z jonhogg $

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

import os, re, shutil
from zipfile import ZipFile
if os.name == 'nt':
    import SevenZip
else:
    import RarFile # RarFile support for non windows machines

import threading

import WurmCommon

# remap dummy translation function to real trans func
_ = WurmCommon.WurmLanguage.s

# local constants
textfiles = ["lua", "toc", "txt", "xml", "wau", "htm", "html", "textile"] # Files to be extracted as text CHANGED: added textile to list
mediafiles = ["tga", "gif", "jpg", "jpeg", "png", "ttf", "blp", "mp3", "wav", "ogg", "m2"] # Whitelist for extensions that will be extracted
allowedfiles = textfiles + mediafiles

interfacere       = "interface(\\\\|/)"
addonsre          = "addons(\\\\|/)"
interfaceaddonsre = "%s%s?" % (interfacere, addonsre)
ignorepaths       = ["^%s$" % (interfaceaddonsre), "^%s?$" % (interfacere)] # Paths that shouldn't be extracted - regular expressions, case insensitive


class Archive(object):
    """This class handles all the required functions for dealing with different Archives used by WUU"""
    
    def __init__(self, filename, addonname):
        """"""
        tracer.debug("Archive - __init__")
        
        self.addonname = addonname
        self.filename  = filename
        self.namelist  = []
        self.addons    = []
        self.filemap   = {}
        self.dirmap    = {}
    
    
    @staticmethod
    def IsFileRequired(filename, filemap):
        """Determines if the file is required"""
        tracer.log(WurmCommon.DEBUG5, "Archive - IsFileRequired")
        
        global ignorepaths, allowedfiles
        
        reignorepaths = [re.compile(x, re.I) for x in ignorepaths]
        
        if not filemap.has_key(filename):
            # File already filtered away in the mapping stage
            return False
        
        ignore = False
        for r in reignorepaths:
                if r.search(filename):
                    WurmCommon.outWarning(_("Ignoring path %(filename)s") % {'filename': filename})
                    ignore = True
        
        if ignore:
            return False
        
        ext = os.path.splitext(filename)[1].replace('.', '') # leaves only the extension, no leading dot
        if not ext.lower() in allowedfiles and not "SkinMe" in filename and not "README" in filename: # don't skip Skinner SkinMe !mkdir or README files
            WurmCommon.outWarning(_("Skipping forbidden file %(filename)s") % {'filename': filename})
            return False
        
        return True
    
    
    @staticmethod
    def _stripDirectoryName(dirname):
        """ Removes leading and trailing slashes from the directory name, and prevents relative paths from posing a security risk outside the WoW dir """
        tracer.log(WurmCommon.DEBUG5, "Archive - _stripDirectoryName")
        
        stripre = '([A-Za-z0-9-_]+)'
        restrip = re.compile(stripre)
        
        simpledir = restrip.findall(dirname)
        if not simpledir or len(simpledir) != 1:
            return None
        else:
            return simpledir[0]
    
    
    @staticmethod
    def _splitPath(path):
        """ Splits a path in to a list of directories - compatible with joinpath below """
        tracer.log(WurmCommon.DEBUG5, "Archive - _splitPath: [%s]" % (path))
        
        try:
            (drive, head) = os.path.splitdrive(path)
            target        = []
            
            while head:
                (head, tail) = os.path.split(head)
                target       = [tail] + target
                
                if tail == '': # happens if path is absolute
                    break
            
            if drive != '':
                target = [drive] + target[1:] # strip off the leading ''
            
            return target
        except Exception, details:
            raise
    
    
    @staticmethod
    def _joinPath(spath):
        """ Joins a path specified as a list of directories """
        tracer.log(WurmCommon.DEBUG5, "Archive - _joinPath")
        
        return os.sep.join(spath)
    
    
    @staticmethod
    def CleanAndBackup(addons):
        """Clean the Addons directories if required and Backup the previous version"""
        tracer.debug("Archive - CleanAndBackup")
        
        if int(WurmCommon.getGlobalSetting(":CleanExtract")):
            # Get all related addons
            toRelate = []
            for a in addons:
                r = WurmCommon.findAllRelated(a)
                if r:
                    toRelate += r
            
            if toRelate:
                total, failed = WurmCommon.DeleteAddons(toRelate, cleansettings=True)
            
            total, failed = WurmCommon.DeleteAddons(addons)
            WurmCommon.outStatus(_("%(stot)d of %(tot)d Addon(s) cleaned successfully") % {'stot': total - failed, 'tot': total})
        else:
            try:
                WurmCommon.BackupAddons(addons) # this won't do anything if no backupdir is set
            except:
                pass # not a critical error
    
    
    @staticmethod
    def updateAddonList(addonname, addons):
        """ Update the AddonList with related Addon info """
        tracer.debug("Archive - updateAddonList")
        
        # Make sure "never before seen addons" have an entry in the list (they'll be set as [Related] to the main addon)
        if WurmCommon.addonlist.has_key(addonname) and len(addons) > 1:
            for a in addons:
                if not WurmCommon.addonlist.has_key(a) or WurmCommon.addonlist.getAtype(a) == '[Unknown]':
                    WurmCommon.addonlist.add(a, siteid=addonname, atype="[Related]")
                    WurmCommon.outDebug("Addon %s set as [Related] to %s" % (a, addonname))
    
    
    # @abstract
    def GetFilelist(self):
        """ Returns the list of files from the archive """
        tracer.log(WurmCommon.DEBUG5, "Archive - GetFilelist")
        
        import inspect
        caller = inspect.getouterframes(inspect.currentframe())[1][3]
        raise NotImplementedError(caller + ' must be implemented in subclass')
    
    
    # @abstract
    def ExtractFiles(self, filelist=None, target=None):
        """
        Extracts the specified files to target dir (if target is None, it uses the unpack dir) without preserving directory structure
        Returns a map 'filename given in filelist' -> 'filename on disk'
        """
        tracer.log(WurmCommon.DEBUG5, "Archive - ExtractFiles")
        
        import inspect
        caller = inspect.getouterframes(inspect.currentframe())[1][3]
        raise NotImplementedError(caller + ' must be implemented in subclass')
    
    
    # @abstract
    def Unpack(self, target=None):
        """Extract the files in the Archive to the path specified in the mapping dictionary"""
        tracer.log(WurmCommon.DEBUG5, "Archive - Unpack")
        
        import inspect
        caller = inspect.getouterframes(inspect.currentframe())[1][3]
        raise NotImplementedError(caller + ' must be implemented in subclass')
    


class ZipArchive(Archive):
    """This class handles Zip Archives"""
    
    def __init__(self, filename, addonname):
        """"""
        tracer.debug("ZipArchive - __init__")
        
        Archive.__init__(self, filename, addonname)
    
    
    def GetFilelist(self):
        """ Returns the list of files from the zip archive """
        tracer.debug("ZipArchive - GetFilelist")
        
        f  = ZipFile(self.filename, "r")
        
        self.namelist = f.namelist()
        
        f.close()
    
    
    def ExtractFiles(self, filelist=None, target=None):
        """
        Extracts the specified files to target dir (if target is None, it uses the unpack dir) without preserving directory structure
        Returns a map 'filename given in filelist' -> 'filename on disk'
        """
        tracer.debug("ZipArchive - ExtractFiles: %s, %s" % (str(filelist), target))
        
        if not filelist:
            filelist = self.namelist
        if not target:
            target = WurmCommon.directories["unpack"]
        
        fmap = {}
        
        f = ZipFile(self.filename, "r")
        
        for fl in filelist:
            if fl: # Ignore missing entries
                (dirname, fname) = os.path.split(fl)
                ext  = os.path.splitext(fl)[1].replace('.', '') # leaves only the extension, no leading dot
                mode = "wb" #default to binary
                if ext.lower() in textfiles and not int(WurmCommon.getGlobalSetting(":PreserveNewline")):
                    mode = "wt"
                
                tfname = os.path.join(target, fname)
                tf     = open(tfname, mode)
                tf.write(f.read(fl))
                tf.close()
                fmap[fl] = tfname
                WurmCommon.outDebug("Extracted %s from %s to %s" % (fname, os.path.split(self.filename)[1], tfname))
        
        f.close()
        
        return fmap
    
    
    def Unpack(self, target=None):
        """Extract the files in the Zip Archive to the path specified in the mapping dictionary"""
        tracer.debug("ZipArchive - Unpack")
        
        global textfiles
        
        totalfiles = float(len(self.namelist)) # float to force non-integer division
        countfiles = 0
        
        zfile = ZipFile(self.filename, "r")
        
        for n in self.namelist:
            # report progress
            countfiles += 1
            if totalfiles > 1:
                WurmCommon.outProgressPercent(_("Unpacking ZIP file"), countfiles/totalfiles)
            
            if not self.IsFileRequired(n, self.filemap):
                continue
            
            filename = self.filemap[n] # this is the filename on disk
            
            if n[-1:] == '/': # is a directory
                continue
            else:
                ext  = os.path.splitext(n)[1].replace('.', '') # leaves only the extension, no leading dot
                mode = "wb" # default to binary
                if ext.lower() in textfiles and not int(WurmCommon.getGlobalSetting(":PreserveNewline")):
                    mode = "wt" # ZipFile needs explicit text mode for text files (unless disabled in WUU)
                
                dirpath = os.path.dirname(filename)
                # Create additional WurmCommon.directories - this is due to ambiguities in the file structure
                if dirpath and not os.path.exists(dirpath):
                    os.makedirs(dirpath)
                
                try:
                    f = open(filename, mode)
                    f.write(zfile.read(n))
                    f.close()
                except Exception, details:
                    WurmCommon.outWarning(_("Could not extract file %(filename)s") % {'filename': n}) # Accept that some files can't be extracted, in case of read-only custom files
                    WurmCommon.outDebug("^^^ - %s" % (str(details)))
                WurmCommon.outDebug("Successfully Extracted %s to %s" % (n, dirpath))
        
        zfile.close()
        WurmCommon.resetProgress()
    


class RaRArchive(Archive):
    """This class handles RaR Archives"""
    
    def __init__(self, filename, addonname):
        """"""
        tracer.debug("RaRArchive - __init__")
        
        Archive.__init__(self, filename, addonname)
        
        try:
            x = RarFile.RarFile # FIXME: Better way of checking for existance of RAR library?
        except NameError:
            raise Exception, "RAR support not available"
    
    
    def GetFilelist(self):
        """ Returns the list of files from the RaR archive """
        tracer.debug("RaRArchive - GetFilelist")
        
        rf = RarFile.RarFile(self.filename)
        
        self.namelist = rf.listfiles()
        
        rf = None
    
    
    def ExtractFiles(self, filelist=None, target=None):
        """
        Extracts the specified files to target dir (if target is None, it uses the unpack dir) without preserving directory structure
        Returns a map 'filename given in filelist' -> 'filename on disk'
        """
        tracer.debug("RaRArchive - ExtractFiles")
        
        if not filelist:
            filelist = self.namelist
        if not target:
            target = WurmCommon.directories["unpack"]
        
        fmap = {}
        
        rf = RarFile.RarFile(self.filename)
        
        for fl in filelist:
            if fl: # Ignore missing entries
               (path, fname) = os.path.split(fl)
               ext = os.path.splitext(fl)[1].replace('.', '') # leaves only the extension, no leading dot
               if len(ext) > 0: # must check size, since directories may appear as files in the RAR
                   rf.extract(fl, target, opts="-ep")
                   fmap[fl] = os.path.join(target, fname)
                   WurmCommon.outDebug("Extracted %s from %s") % (fl, target)
        
        rf = None
        
        return fmap
    
    
    def Unpack(self, target=None):
        """Extract the files in the RaR Archive to the path specified in the mapping dictionary"""
        tracer.debug("RaRArchive - Unpack")
        
        totalfiles = float(len(self.namelist)) # float to force non-integer division
        countfiles = 0
        
        rf = RarFile.RarFile(self.filename)
        
        for n in self.namelist:
            # report progress
            countfiles += 1
            if totalfiles > 1:
                WurmCommon.outProgressPercent(_("Unpacking RAR file"), countfiles/totalfiles)
            
            if not self.IsFileRequired(n, self.filemap):
                continue
            
            ext = os.path.splitext(n)[1].replace('.', '') # leaves only the extension, no leading dot
            if len(ext) == 0: # no extension, probably a directory, so ignore it
                WurmCommon.outWarning(_("Skipping probable directory %(filename)s") % {'filename': n})
                continue
            
            (path, filename) = os.path.split(n)
            if len(filename) > 0: # must check size, since directories may appear as files in the RAR
                rf.extract(n, target)
                WurmCommon.outDebug("Successfully extracted %(file)s to %(dir)s" % {'file': n, 'dir': target})
        
        rf = None
        WurmCommon.resetProgress()
    


class WinRaRArchive(Archive):
    """This class handles Windows RaR Archives"""
    
    def __init__(self, filename, addonname):
        """"""
        tracer.debug("WinRaRArchive - __init__")
        
        Archive.__init__(self, filename, addonname)
    
    
    def GetFilelist(self):
        """ Returns the list of files from the RaR archive """
        tracer.debug("WinRaRArchive - GetFilelist")
        
        f = RarFile(self.filename)
        
        for fi in f.iterfiles():
            self.namelist.append(fi.filename)
        
        del f
    
    
    def ExtractFiles(self, filelist=None, target=None):
        """
        Extracts the specified files to target dir (if target is None, it uses the unpack dir) without preserving directory structure
        Returns a map 'filename given in filelist' -> 'filename on disk'
        """
        tracer.debug("WinRaRArchive - ExtractFiles")
        
        if not filelist:
            filelist = self.namelist
        if not target:
            target = WurmCommon.directories["unpack"]
        
        fmap = {}
        
        f = RarFile(self.filename)
        for fi in f.iterfiles():
            if fl: # Ignore missing entries
                fl = fi.filename
                if fl not in filelist:
                   continue
                
                (dirname, fname) = os.path.split(fl)
                ext   = os.path.splitext(fl)[1].replace('.', '') # leaves only the extension, no leading dot
                mode  = "wb" #default to binary
                rmode = "rb"
                if ext.lower() in textfiles and not int(WurmCommon.getGlobalSetting(":PreserveNewline")):
                   mode  = "wt"
                   rmode = "rt"
                
                tfname = os.path.join(target, fname)
                tf     = open(tfname, mode)
                tf.write(f.open(rmode).read())
                tf.close()
                fmap[fl] = tfname
                WurmCommon.outDebug("Extracted %s from %s" % (fname, os.path.split(self.filename)[1]))
        
        del f
        
        return fmap
    
    
    def Unpack(self, target=None):
        """Extract the files in the RaR Archive to the path specified in the mapping dictionary"""
        tracer.debug("WinRaRArchive - Unpack")
        
        global textfiles
        
        totalfiles = float(len(self.namelist)) # float to force non-integer division
        countfiles = 0
        
        rfile = RarFile(self.filename)
        
        for rf in rfile.iterfiles():
            # report progress
            countfiles += 1
            if totalfiles > 1:
                WurmCommon.outProgressPercent(_("Unpacking RAR file"), countfiles/totalfiles)
            
            n = rf.filename
            
            if not self.IsFileRequired(n, self.filemap):
                continue
            
            if n[-1:] == '/': # is a directory
                try:
                    os.makedirs(os.path.join(target, n))
                except:
                    pass # path already exists
            else:
                ext   = os.path.splitext(n)[1].replace('.', '') # leaves only the extension, no leading dot
                mode  = "wb" # default to binary
                rmode = "rb" # UnRAR needs to have read mode specified, too
                if ext.lower() in textfiles and not int(WurmCommon.getGlobalSetting(":PreserveNewline")):
                    mode  = "wt"
                    rmode = "rt"
                
                filename = os.path.join(target, n)
                dirpath  = os.path.dirname(filename)
                # Create additional directories - this is due to ambiguities in the file structure
                if dirpath and not os.path.exists(dirpath):
                    os.makedirs(dirpath)
                
                if rf.size > 0: # must check size, since directories may appear as files in the RAR
                    try:
                        f = open(os.path.join(target, n), mode)
                        f.write(rf.open(rmode).read())
                        f.close()
                    except Exception, details:
                        WurmCommon.outWarning(_("Could not extract file %(filename)s") % {'filename': n}) # Accept that some files can't be extracted, in case of read-only custom files
                        WurmCommon.outDebug("^^^ - %s %s" % (str(Exception), str(details)))
                    WurmCommon.outDebug("Successfully Extracted %s to %s" % (n, dirpath))
        
        del rfile
        WurmCommon.resetProgress()
    


class SVNArchive(Archive):
    """This class handles SVN Export directories"""
    
    def __init__(self, filename, addonname):
        """"""
        tracer.debug("SVNArchive - __init__")
        
        Archive.__init__(self, filename, addonname)
        
        self.exportdir = self.filename
    
    
    def GetFilelist(self):
        """ Returns the list of directories & files from the SVN Export directory """
        tracer.debug("SVNArchive - GetFilelist")
        
        for root, dirs, files in os.walk(self.exportdir, topdown=True):
            if root == self.exportdir:
                continue
            for name in files:
                # store with subdirectory names
                self.namelist.append(os.path.join(root[len(self.exportdir) + 1:], name))
    
    
    def Unpack(self, target=None):
        """Extract the files from the SVN Export directory to the path specified in the mapping dictionary"""
        tracer.debug("SVNArchive - Unpack")
        
        totalfiles = float(len(self.namelist)) # float to force non-integer division
        countfiles = 0
        
        for n in self.namelist:
            # report progress
            countfiles += 1
            if totalfiles > 1:
                WurmCommon.outProgressPercent(_("Copying from SVN Export dir"), countfiles/totalfiles)
            
            if not self.IsFileRequired(n, self.filemap):
                continue
            
            filename = self.filemap[n] # this is the filename on disk
            
            # create directories if they don't exist
            dirpath = os.path.dirname(filename)
            if dirpath and not os.path.exists(dirpath):
                os.makedirs(dirpath)
            
            # prepend the SVN Export directory to the source filename
            exportdirfile = os.path.join(self.exportdir, n)
            shutil.copy(exportdirfile, filename)
        
        WurmCommon.resetProgress()
    


class SevenZipArchive(Archive):
    """This class handles 7Zip Archives (note that the 7Zip command line version used can unpack ZIP, RAR, 7Z and many more)"""
    
    def __init__(self, filename, addonname):
        """"""
        tracer.debug("7ZipArchive - __init__")
        
        Archive.__init__(self, filename, addonname)
    
    
    def GetFilelist(self):
        """ Returns the list of files from the 7zip archive """
        tracer.debug("7ZipArchive - GetFilelist")
        
        f  = SevenZip.SevenZipFile(self.filename)
        
        self.namelist = f.filelist()
        
        f  = None
    
    
    def ExtractFiles(self, filelist=None, target=None):
        """
        Extracts the specified files to target dir (if target is None, it uses the unpack dir) without preserving directory structure
        Returns a map 'filename given in filelist' -> 'filename on disk'
        """
        tracer.debug("7ZipArchive - ExtractFiles")
        
        if not filelist:
            filelist = self.namelist
        if not target:
            target = WurmCommon.directories["unpack"]
        
        fmap = {}
        
        szf = SevenZip.SevenZipFile(self.filename)
        
        for fl in filelist:
            if fl: # Ignore missing entries
                (dirname, fname) = os.path.split(fl)
                tfname = os.path.join(target, fname)
                szf.extract(fname, tfname)
                fmap[fl] = tfname
                WurmCommon.outDebug("Extracted %s from %s" % (fname, os.path.split(self.filename)[1]))
        
        szf = None
        
        return fmap
    
    
    def Unpack(self, target=None):
        """Extract the files in the archive to the path specified in the mapping dictionary"""
        tracer.debug("7ZipArchive - Unpack")
        
        totalfiles = float(len(self.namelist)) # float to force non-integer division
        countfiles = 0
        
        rf = SevenZip.SevenZipFile(self.filename)
        
        for n in self.namelist:
            # report progress
            countfiles += 1
            if totalfiles > 1:
                WurmCommon.outProgressPercent(_("Unpacking RAR file"), countfiles/totalfiles)
            
            if not self.IsFileRequired(n, self.filemap):
                continue
            
            ext = os.path.splitext(n)[1].replace('.', '') # leaves only the extension, no leading dot
            if len(ext) == 0: # no extension, probably a directory, so ignore it
                WurmCommon.outWarning(_("Skipping probable directory %(filename)s") % {'filename': n})
                continue
            
            (path, filename) = os.path.split(n)
            if len(filename) > 0: # must check size, since directories may appear as files in the RAR
                try:
                    rf.extract(n, os.path.join(target, self.addonname))
                except SevenZip.SevenZipException, details:
                    WurmCommon.outError(_("Could not extract file %(filename)s") % {'filename': filename} + ":" + str(details))
                    continue
                WurmCommon.outMessage(_("Successfully Extracted %(filename)s to %(dirname)s") % {'filename': filename, 'dirname': os.path.join(target, self.addonname)})
        
        rf = None
        WurmCommon.resetProgress()
    


class GitArchive(Archive):
    """This class handles Git Clone directories"""
    
    def __init__(self, filename, addonname):
        """"""
        tracer.debug("GitArchive - __init__")
        
        Archive.__init__(self, filename, addonname)
        
        self.exportdir = self.filename
    
    
    def GetFilelist(self):
        """ Returns the list of directories & files from the Git Clone directory """
        tracer.debug("GitArchive - GetFilelist")
        
        for root, dirs, files in os.walk(self.exportdir, topdown=True):
            # WurmCommon.outDebug("root, dirs, files :[%s, %s, %s]" % (root, dirs, files))
            if root == self.exportdir:
                continue
            # ignore .git directories   
            if '/.git' in root:
                continue
            for name in files:
                # store with subdirectory names
                self.namelist.append(os.path.join(root[len(self.exportdir) + 1:], name))
    
    
    def Unpack(self, target=None):
        """Extract the files from the Git Clone directory to the path specified in the mapping dictionary"""
        tracer.debug("GitArchive - Unpack")
        
        totalfiles = float(len(self.namelist)) # float to force non-integer division
        countfiles = 0
        
        for n in self.namelist:
            # report progress
            countfiles += 1
            if totalfiles > 1:
                WurmCommon.outProgressPercent(_("Copying from Git Clone dir"), countfiles/totalfiles)
            
            if not self.IsFileRequired(n, self.filemap):
                continue
            
            filename = self.filemap[n] # this is the filename on disk
            
            # create directories if they don't exist
            dirpath = os.path.dirname(filename)
            if dirpath and not os.path.exists(dirpath):
                os.makedirs(dirpath)
            
            # prepend the Git Clone directory to the source filename
            exportdirfile = os.path.join(self.exportdir, n)
            shutil.copy(exportdirfile, filename)
        
        WurmCommon.resetProgress()
    


def MapFilenames(addonname, filelist, addonsonly=False, isChild=False):
    """ Makes a mapping filename_in_archive -> filename_on_disk, to place files where they belong.
    Returns a tuple: ({file_archive -> file_disk}, list_of_addons)
    if addonsonly is set, the return value is just list_of_addons.
    Don't assume the return value will stay a 2-tuple - multiple return flags might be added (like telling if an addon has special placements of files)
    """
    tracer.debug("MapFilenames: %s, %s" % (addonname, filelist))
    # WurmCommon.outDebug("MapFilenames: %s, %s" % (addonname, filelist))
    
    wowtoplevelfolders = ["fonts", "interface"] #case insensitve - only allowed folders for addons to put files in
    ignorefolders = ["__MACOSX", "FrameXML", ".svn", ".git"] # folders to ignore
    
    ia_re = "^" + interfaceaddonsre
    reia  = re.compile(ia_re, re.I)
    
    # Some flags we use to avoid double checks
    simple   = False # shortcut for simple addons
    intadd   = False # true if all files are in Interface\AddOns\AddonDir\
    # used to indicate whether we found a version directory
    isverdir = False
    verdir   = ""
    # Internal Lists and dictionaries
    addons   = []
    filemap  = {}
    prepaths = {} # stores the directory containing the addons not intuitively placed
    
    # First, find all the separate addons (every addon will have a .toc file with the same name as its directory)
    # Also, this checks to see if the zip is on the format AddonDir\*.* directly, to skip all the advanced checks
    
    for n in filelist:
        # Skip files with unparseable names
        try:
            n.decode()
        except:
            continue
        
        (path, ext)           = os.path.splitext(n)
        (directory, filename) = os.path.split(path)
        dirlist               = directory.split(os.sep)
        
        # Ignore certain directories
        ignoredir = False
        for dirname in ignorefolders:
            if dirname in directory:
                ignoredir = True
                break
        if ignoredir:
            continue
        
        # Ignore nopatch files and just directory entries
        if filename == "nopatch" or len(filename) == 0:
            continue
        
        # Ignore Library .toc files (prevents them from being installed separately)
        if (filename[:3] == "Lib" or "Library" in filename) and ext == ".toc":
            continue
        
        # Ignore entries that are already set as Ignore/Dummy
        for entry in [ directory, filename, dirlist[0] ]:
            if entry in WurmCommon.addonlist:
                if WurmCommon.addonlist.getAtype(entry) in ("[Ignore]", "[Dummy]"):
                    continue
         
        # no addon directory supplied so use the addonname as the directory name instead
        if directory == "":
            filemapping = os.path.join(WurmCommon.directories["addons"],  addonname, n)
        else:
            # default to assume paths are "good"
            filemapping = os.path.join(WurmCommon.directories["addons"], n)
        
        # Check to see if the filelist contains a version directory entry
        # e.g. "KLHThreatMeter19.17d/"
        path = Archive._splitPath(directory)
        if len(path) > 1:
            # if the sub directory matches the beginning of its parent directory then its
            # parent directory is probably a version directory and should be removed
            if path[1] in path[0][:len(path[1])] and len(path[1]) < len(path[0]):
                # remove the version directory from the front of the namelist entry
                # and store it as the new file mapping
                filemapping = os.path.join(WurmCommon.directories["addons"], n[len(path[0])+1:])
                # remove the version directory from the front of the directory
                directory  = directory[len(path[0])+1:]
                isverdir = True
                verdir = "%s/" % (path[0])
        
        # store the file mapping in the dictionary
        filemap[n] = filemapping
        
        if ext.lower() == ".toc":
            addons.append(filename)
            if directory.lower() == filename.lower(): # if the ENTIRE path containing the file, and the file, are equal, this is a "simple ZIP" - this might not be true 100% of the time
                # If the directory name has a different capitalization to the filename then use the directory name instead, this handles BtmScan/btmScan
                if directory != filename:
                    del addons[-1]
                    addons.append(directory)
                simple = True
            else:
                if reia.search(directory):
                    filemap[n] = os.path.join(WurmCommon.directories["wow"], n) # remap the filename
                    intadd = True # path starts with Interface\AddOns
                elif directory != '':
                    intadd = False # we have to check it more thoroughly if just a single path is missing the Interface\AddOns part, unless it has no path at all
                
                # Store the path removing Interface/Addons from it if present
                if intadd:
                    (prepath, addondir) = os.path.split(directory[17:])
                else:
                    (prepath, addondir) = os.path.split(directory)
                if len(prepath) > 0:
                    prepaths[filename] = prepath
    
    logger.log(WurmCommon.DEBUG5, "prepaths: %s" % str(prepaths))
    
    # Cull the addon list a bit - remove contained addons
    for addon in prepaths:
        if prepaths[addon] in addons or prepaths[addon][:len(addonname)] in addons :
            try:
                del addons[addons.index(addon)] # remove the addon from the list
            except:
                pass # not critical if it isn't removed
    
    # remove the version directory entry from the file mapping dictionary
    if isverdir:
        try:
            del filemap[verdir]
        except:
            WurmCommon.outError("Unable to delete the version directory entry: %s" % verdir)
    
    # Used to simplify finding the addons in a zip
    if addonsonly:
        return addons
    
    if simple: # shortcut it here
        return (filemap, addons)
    
    # Ok, not a simple file, then we check for case 2: Interface\AddOns\AddonDir\*.*
    if intadd:
        # fixing all paths
        for n in filemap:
            if reia.search(n):
                filemap[n] = os.path.join(WurmCommon.directories["wow"], n) # remap the filename, using WoW dir as base instead of AddOns
        
        return (filemap, addons)
    
    # Right, the two simple cases are ruled out :(
    # ClearFont has everything in "[WoW folder]\Fonts" and "[WoW folder]\Interface\AddOns", so next test is to see if any of the "allowed target dirs" for unzip are in the paths (I've added "Fonts" and "Interface" to the list)
    # Tested with a range of addons, but not guaranteed to work with everyone
    
    for n in filelist:
        # Skip files with unparseable names
        try:
            n.decode()
        except:
            continue
        
        (path, filename)    = os.path.split(n)
        (mainpath, lastdir) = os.path.split(path)
        
        if lastdir in addons or (lastdir == addonname and isChild): # this is a plain addon directory
            filemap[n] = os.path.join(WurmCommon.directories["addons"], lastdir, filename)
            continue
        
        # test if this is a subdir of addon dir
        pathfound = False
        for a in addons:
            pathfound = False
            if a in mainpath: # yes, it is
                offset = path.find(a) # need to find how much to strip off the beginning of path
                filemap[n] = os.path.join(WurmCommon.directories["addons"], path[offset:], filename)
                pathfound = True
                break
        if pathfound:
            continue
        
        if lastdir.lower() in wowtoplevelfolders:
            filemap[n] = os.path.join(WurmCommon.directories["wow"], lastdir, filename)
            continue
        
        # no addon directory supplied so use the addonname as the directory name instead
        if lastdir.lower() == "addons" or lastdir == "":
            filemap[n] = os.path.join(WurmCommon.directories["addons"], addonname, filename)
            continue
        elif mainpath == "":
            filemap[n] = os.path.join(WurmCommon.directories["addons"],  addonname, lastdir, filename)
            continue
        
        # If this is a Child Addon then ignore the fact that the file cannot be placed because it hasn't got a TOC file
        if not isChild:
            del filemap[n] # just remove files that can't be placed
            WurmCommon.outWarning(_("Don't know where to place file %(filename)s") % {'filename': n})
    
    return (filemap, addons)


def PlainUnzip(zfilename, target):
    """ Just unzips a zipfile to target - currently only used by the auto-updater """
    tracer.debug("PlainUnzip")
    
    zfile = ZipFile(zfilename, "r")
    
    for n in zfile.namelist():
        if n[-1:] == '/': # is a directory
            try:
                os.makedirs(os.path.join(target, n))
            except:
                pass # path already exists
        else:
            orign = n
            ext   = os.path.splitext(n)[1].replace('.', '') # leaves only the extension, no leading dot
            mode  = "wb" #default to binary
            if ext.lower() in textfiles and not int(WurmCommon.getGlobalSetting(":PreserveNewline")):
                mode = "wt"
            
            filename = os.path.join(target, n)
            dirpath = os.path.dirname(filename)
            # Create additional directories - this is due to ambiguities in the ZIP file structure
            if dirpath and not os.path.exists(dirpath):
                os.makedirs(dirpath)
            
            try:
                f = open(filename, mode)
                f.write(zfile.read(orign))
                f.close()
            except Exception, details:
                WurmCommon.outWarning(_("Could not extract file %(filename)s") % {'filename': n}) # Accept that some files can't be extracted, in case of read-only custom files
                WurmCommon.outDebug("^^^ - %s" % (str(details)))
    
    zfile.close()


def CorrectExtension(filename):
    """since we don't trust the addon sites, we have to check the type of archive and correct the extension if necessary"""
    tracer.debug("CorrectExtension")
    
    newfilename = filename
    extn        = os.path.splitext(filename)[1].replace('.', '') # leaves only the extension, no leading dot
    
    # only test needed, for now, is to see if a zip really is a rar
    if extn.lower() == "zip":
        try:
            header = open(filename, "rb").read(3)
            if header == "Rar":
                WurmCommon.outWarning(_("%(filename)s is really a RAR file - renaming") % {'filename': filename})
                newfilename = filename[:-3] + "rar"
                try:
                    os.remove(newfilename)
                except:
                    pass # don't fail at this point
                try:
                    os.rename(filename, newfilename)
                except Exception, details:
                    raise Exception, "Error renaming %s to %s: %s" % (filename, newfilename, str(details))
                
                extn = "rar"
                WurmCommon.outDebug("^^^^ renamed to %s" % (newfilename))
        except Exception, details:
            raise Exception, "Could not check %s: %s" % (filename, str(details))
    
    return (newfilename, extn)


def WoWInstallAddon(filename, addonname, isChild=False):
    """ Install an Addon. Handles Zip & RaR archives and installation from a Subversion Repository"""
    tracer.debug("WoWInstallAddon: %s, %s, %s" % (filename, addonname, isChild))
    
    if threading.currentThread().getName() != "MainThread":
        WurmCommon.wurmlock["WurmUnpack"].acquire()
    
    (filename, extn) = CorrectExtension(filename)
    
    try:
        try:
            if extn.lower() == "zip":
                addonarchive = ZipArchive(filename, addonname)
            elif extn.lower() == "rar" and os.name == 'nt':
                if SevenZip and SevenZip.isAvailable():
                    addonarchive = SevenZipArchive(filename, addonname)
                else:
                    raise Exception, "Can't extract .rar files; please install 7-Zip (http://www.7-zip.org/) to enable RAR support (specifically, 7z.exe is needed, either in default installation location, on the path, or in the WUU directory)"
            elif extn.lower() == "rar":
                addonarchive = RaRArchive(filename, addonname)
            elif extn.lower() == "svn":
                addonarchive = SVNArchive(filename, addonname)
            elif extn.lower() == "git":
                addonarchive = GitArchive(filename, addonname)
            elif extn.lower() == "7z":
                addonarchive = SevenZipArchive(filename, addonname)
            else:
                raise Exception, "Unknown or unsupported archive type \"%s\"" % (extn)
            
            # Get the Archive file contents
            addonarchive.GetFilelist()
            
            # Map the Archive filenames to the Addon directory structure
            (addonarchive.filemap, addonarchive.addons) = MapFilenames(addonname, addonarchive.namelist, isChild=isChild)
            
            # Clean & Backup Addon directory
            addonarchive.CleanAndBackup(addonarchive.addons)
            
            # Make sure "never before seen addons" have an entry in the list
            addonarchive.updateAddonList(addonname, addonarchive.addons)
            
            # Unpack the archive file
            addonarchive.Unpack(target=WurmCommon.directories["addons"])
        
        except Exception, details:
            WurmCommon.outError("Installation of %s failed: %s" % (addonname, str(details)))
            raise
    finally:
        if threading.currentThread().getName() != "MainThread":
            WurmCommon.wurmlock["WurmUnpack"].release()
    
    return True

