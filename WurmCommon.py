# -*- coding: utf-8 -*-
# $Id: WurmCommon.py 663 2009-06-01 18:43:01Z jonhogg $

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

# Purpose of this module:
# - Gather functions used by WUU, Wurm and WurmUnpack, to prevent duplicating/unsyncing of data
# - Gather all global variables used by the Wurm* modules

import logging
STATUS = logging.DEBUG  - 1 # toggle these two lines to see the status messages
# STATUS = logging.INFO  - 1 #
DEBUG3 = logging.DEBUG - 3
DEBUG5 = logging.DEBUG - 5
DEBUG7 = logging.DEBUG - 7
logging.addLevelName(STATUS, "STATUS")
logging.addLevelName(DEBUG3, "DEBUG_3")
logging.addLevelName(DEBUG5, "DEBUG_5")
logging.addLevelName(DEBUG7, "DEBUG_7")
logger = logging.getLogger(None)
tracer = logging.getLogger("WUUtrace")

import os, sys, shutil, re, gzip, platform
import urllib2, urlparse, socket
from datetime import datetime, timedelta
import xml.dom.minidom
import threading
import codecs

try:
    from cStringIO import StringIO
except ImportError:
    import StringIO

import WurmLanguage

# Treat UnicodeWarning's as an error if running Python 2.5 or higher
if map(int, platform.python_version().split(".")[:2]) >= [2, 5]:
    import warnings
    # Warnings Filter
    warnings.simplefilter("error", UnicodeWarning) # turn UnicodeWarning into an error
else:
    UnicodeWarning = UnicodeDecodeError

# remap dummy translation function to real trans func
_ = WurmLanguage.s

# define the Application, Support & Preferences directories
origappldir = appldir = supportdir = prefsdir = os.path.split(os.path.realpath(sys.argv[0]))[0]

# If on Windows then use the preferred directories for Preference files etc
if sys.platform[:3] == "win":
    try:
        userdir    = os.getenv("USERPROFILE")
        supportdir = prefsdir = os.path.join(userdir, "WUU")
        # create these directories if they don't exist
        if not os.path.exists(supportdir):
            os.makedirs(supportdir)
        if not os.path.exists(prefsdir):
            os.makedirs(prefsdir)
    except Exception, details:
        print "Unable to create Windows directories: %s" % str(details)
        raise

# If on a Mac then use the preferred directories for Preference files etc
elif sys.platform == "darwin":
    # if running from an .app then relocate the appldir variable to the directory the .app is in
    if "/WUU.app" in appldir:
        appldir = appldir[:appldir.find("/WUU.app")]
    try:
        userdir    = os.getenv("HOME")
        supportdir = userdir + "/Library/Application Support/WUU"
        prefsdir   = userdir + "/Library/Preferences/WUU"
        # create these directories if they don't exist
        if not os.path.exists(supportdir):
            os.makedirs(supportdir)
        if not os.path.exists(prefsdir):
            os.makedirs(prefsdir)
    except Exception, details:
        print "Unable to create Mac directories: %s" % str(details)
        raise
# print "Application directory: " + appldir
# print "Support directory: " + supportdir
# print "Preferences directory: " + prefsdir

# Locks for Addons sites
wurmlock = {}

# Gather all directory names in a single dictionary instead of separate variables
directories = {"wow":"", "addons":"", "backup":"", "temp":"", "unpack":""}

globalsettings = {} # Global settings for Wurm (so options may be set from the UI)
siteregexps    = {} # Regexps used by the addon site classes

listchanged    = {} # Entries for each list are set to True if the addon list was changed indirectly (that is, when the UI should give a "Do you want to save?"-popup when quitting)

# define working dictionaries
addons          = {}
addonlist       = None
addontypes      = {}
toclist         = {}
depdict         = {}
deplist         = []
needdepslist    = [] # List of missing dependencies; filled by different routines, checked by UI now and then (TODO)
needdepsmap     = {} # Missing dependency -> list of addons using it
unusedliblist   = [] # List of addons marked as libraries that no addon depends on; might not be safe to remove

# Message output and callbacks
cbOutMessage       = None
cbOutDebug         = None
cbOutWarning       = None
cbOutError         = None
cbOutStatus        = None
cbProgressPercent  = None
cbResetProgress    = None
cbProgressPercent2 = None
cbResetProgress2   = None
Wurm               = None

# Filenames etc
langdir          = os.path.join(origappldir, "lang") # where the lang-XX.xml files are stored
refile           = "site_re.txt"
refilename       = os.path.join(supportdir, refile) # regexps for the different sites
clreportfile     = os.path.join(supportdir, "WUU-UpdateReport.html") # Changelog report file
depreportfile    = os.path.join(supportdir, "WUU-DependencyReport.html") # Dependency report file
templatefile     = "templates.xml"
templatefilename = os.path.join(supportdir, templatefile) # Templates

wuusite          = "http://wuu.vagabonds.info/"
wuudownload      = wuusite + "downloads.php"
wuuki            = wuusite + "wuuki/"
wuusf            = "http://sourceforge.net/projects/wuu"
reurl            = wuusite + refile
templateurl      = wuusite + templatefile
cosmosaddonslist = "http://www.cosmosui.org/addons.php"
newaddon         = u">>NewAddon<<"
useragent        = "WUU" # Useragent to use for web requests (set more specifically by WUU)

# Class Specific website availability
isAvailable = {}

# these are the keys used for the Templates
templateKeys = [
    "AddonPage",
    "VerRegExp",
    "VerIsDate",
    "DateFormat",
    "VerIsLast",
    "ExtnRegExp",
    "ExtnIsName",
    "DLNameExp"
]

# OtherSites templates
ostemplates = {}
ostKeys = []
# Child templates
childtemplates = {}
childtKeys = []

pagecache = {}

class AddonList(dict):
    """This is used to manage a list of addons"""
    
    def __init__(self):
        """"""
        tracer.debug("AddonList - __init__")
        
        # store object's id 
        self._id = id(self)
        
        dict.__init__(self)
        self._fname  = 0
        self._lname  = 1
        self._siteid = 2
        self._atype  = 3
        self._flags  = 4
    
    
    def add(self, aname, fname=None, lname=None, siteid=None, atype=None, flags=None):
        """add a new addon entry into the dictionary"""
        tracer.log(DEBUG5, "AddonList - add")
        
        global listchanged
        
        if fname is None:
            fname = aname
        if lname is None:
            lname = aname
        if siteid is None:
            siteid = aname
        if atype is None:
            atype = "[Unknown]"
        if flags is None:
            flags = {}
        self[aname] = (fname, lname, siteid, atype, flags)
        
        # Set list changed indicator
        listchanged[self._id] = True
    
    
    def delete(self, aname):
        """delete an addon entry from the dictionary"""
        tracer.log(DEBUG5, "AddonList - delete")
        
        global listchanged
        
        del self[aname]
         
        # Set list changed indicator
        listchanged[self._id] = True
    
    
    def getSome(self, aname):
        """get some of the addon info from the dictionary"""
        tracer.log(DEBUG5, "AddonList - getSome: %s" % (aname))
        
        return (self.getFname(aname), self.getLname(aname), self.getSiteid(aname), self.getAtype(aname))
    
    
    def getAll(self, aname):
        """get all the addon info from the dictionary"""
        tracer.log(DEBUG5, "AddonList - getAll: %s" % (aname))
        
        return (self.getFname(aname), self.getLname(aname), self.getSiteid(aname), self.getAtype(aname), self.getAllFlags(aname))
    
    
    def getFname(self, aname):
        """get the addon's friendlyname from the dictionary"""
        tracer.log(DEBUG5, "AddonList - getFname")
        
        try:
            return self[aname][self._fname]
        except KeyError:
            return None
    
    
    def getLname(self, aname):
        """get the addon's localname from the dictionary"""
        tracer.log(DEBUG5, "AddonList - getLname")
        
        try:
            return self[aname][self._lname]
        except KeyError:
            return None
    
    
    def getSiteid(self, aname):
        """get the addon's siteid from the dictionary"""
        tracer.log(DEBUG5, "AddonList - getSiteid")
        
        try:
            return self[aname][self._siteid]
        except KeyError:
            return None
    
    
    def getAtype(self, aname):
        """get the addon's addontype from the dictionary"""
        tracer.log(DEBUG5, "AddonList - getAtype")
        
        try:
            return self[aname][self._atype]
        except KeyError:
            return None
    
    
    def getAllFlags(self, aname):
        """get the addon's flags from the dictionary"""
        tracer.log(DEBUG5, "AddonList - getAllFlags: %s" % (aname))
        
        try:
            return self[aname][self._flags]
        except KeyError:
            return None
    
    
    def getFlag(self, aname, flag):
        """get the addon's flags from the dictionary"""
        tracer.log(DEBUG5, "AddonList - getFlag: %s, %s" % (aname, flag))
        
        try:
            return self[aname][self._flags][flag]
        except KeyError:
            return None
    
    
    def addFlag(self, aname, flag, value):
        """add a flag to the addon's flags in the dictionary"""
        tracer.log(DEBUG5, "AddonList - addFlag: %s, %s, %s" % (aname, flag, value))
        
        self[aname][self._flags][flag] = value
    
    
    def delFlag(self, aname, flag):
        """delete a flag from the addon's flags in the dictionary"""
        tracer.log(DEBUG5, "AddonList - delFlag: %s, %s" % (aname, flag))
        
        if flag in self[aname][self._flags]:
            del self[aname][self._flags][flag]
    


class PageCacheEntry:
    """ Simple time-based in-memory caching of web pages """
    def __init__(self, url, content, timeout=600): # default timeout 10 minutes
        self.url = url
        self.content = content
        self.expires = datetime.now() + timedelta(seconds=timeout)
    
    
    def isValid(self):
        return (self.expires >= datetime.now())
    


def _deleteAddon(addon):
    """"""
    tracer.debug("_deleteAddon: %s" % (addon))
    
    if threading.currentThread().getName() != "MainThread":
        wurmlock["WurmCommon1"].acquire()
    
    outDebug("Ok, deleting %s" % (addon))
    # Moving in for the kill
    try:
        try:
            _deletePathRecursive(os.path.join(directories["addons"], addon))
        except Exception, details:
            outDebug("Couldn't remove %s: %s" % (addon, unicode(details)))
            raise
    finally:
        if threading.currentThread().getName() != "MainThread":
            wurmlock["WurmCommon1"].release()
    
    return True


def _deleteBackup(addon):
    """"""
    tracer.debug("_deleteBackup: %s" % (addon))
    
    global directories
    
    if threading.currentThread().getName() != "MainThread":
        wurmlock["WurmCommon1"].acquire()
    
    # Moving in for the kill
    try:
        try:
            if len(directories["backup"]) > 5 and os.path.exists(directories["backup"]): # Minor sanity check
                _deletePathRecursive(os.path.join(directories["backup"], addon))
        except Exception, details:
            msg = "Error removing backup of %s: %s" % (addon, str(details))
            logger.exception(msg)
            outError(msg)
    finally:
        if threading.currentThread().getName() != "MainThread":
            wurmlock["WurmCommon1"].release()


def _deletePathRecursive(path, deleteSelf=True):
    """ Deletes all contained files and subfolders of "path", and, if deleteSelf is set, "path" itself too - returns the count of files and folders deleted, as a tuple """
    tracer.debug("_deletePathRecursive: %s" % (path))
    
    filecount = dircount = 0
    
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
            filecount += 1
        for name in dirs:
            os.rmdir(os.path.join(root, name))
            dircount += 1
    if deleteSelf:
        os.rmdir(path)
        dircount += 1
    
    return (filecount, dircount)


def addCachedPage(url, content, timeout=600):
    """ Adds a page to the cache """
    global pagecache
    
    pagecache[url] = PageCacheEntry(url, content, timeout)


def cacheSize():
    """ Returns a tuple of (count, total size) of the pages currently in the cache, in bytes """
    total = 0
    
    for url in pagecache:
        total += len(pagecache[url].content)
    
    return (len(pagecache), total)

    
def checkDeps(depReqd):
    """ check to see if the specified dependecy exists """
    tracer.debug("checkDeps: %s" % (depReqd))
    
    global addonlist, deplist
    
    if deplist == []:
        deplist = depdict.keys()
    
    # already in the addonlist
    if depReqd in addonlist:
        # not flagged as Unknown
        if not addonlist.getAtype(depReqd) == "[Unknown]":
            return True
    
    # already in the dependency list
    elif depReqd in deplist or depReqd.lower() in deplist:
        return True
    
    # As most dependencies don't match actual Addon lua filenames
    # try to map them to actual Addons that we know about
    # Ace2
    elif depReqd == "Ace2":
        for libReqd in ("AceLibrary", "AceAddon", "AceEvent", "AceDB", "AceConsole", "AceHook"):
            depFound = False
            for depname in deplist:
                if libReqd == depname[:len(libReqd)]:
                    depFound = True
                    continue
            if not depFound:
                return False
        return True
    
    # Ace3 Libraries
    elif (depReqd.startswith("Ace") and depReqd.endswith("-3.0")) or depReqd == "CallbackHandler-1.0":
        if "Ace3" in deplist:
            return True
        return False
    
    # handle mis-spelt Fubar
    elif depReqd == "Fubar":
        if "FuBar" in deplist:
                return True
        return False
    
    # DewdropLib
    elif depReqd == "Dewdrop-2.0":
        if "DewdropLib" in deplist:
            return True
        return False
    
    # TabletLib
    elif depReqd == "Tablet-2.0":
        if "TabletLib" in deplist:
            return True
        return False
    
    # Does it start with SpecialEvents?
    elif depReqd.startswith("SpecialEvents"):
        libReqd = depReqd[:13]
        for depname in deplist:
            if libReqd == depname[:len(libReqd)]:
                return True
        return False
    
    # Does it end in Lib?
    elif depReqd.lower().endswith("lib"):
        libReqd = depReqd[:-3]
        for depname in deplist:
            if libReqd == depname[:len(libReqd)]:
                return True
        return False
    
    # Does it exist without a version number?
    elif not checkDeps.verno_re.search(depReqd):
        for depname in deplist:
            if depReqd in addonlist or depReqd == depname[:len(depReqd)]:
                return True
        return False


# dependency check regular expression
checkDeps.verno_re = re.compile("-\d\.\d")

def checkWebsite(url):
    """ check to see if the specified website site is available """
    tracer.debug("checkWebsite: %s" % (url))
    
    req      = urllib2.Request(url)
    response = None
    
    try:
        try:
            req.add_header('User-Agent', useragent)
            response = urllib2.urlopen(req)
        except urllib2.URLError, details:
            if hasattr(details, "reason"):
                outWarning(_("We failed to reach %(url)s, Reason: %(dets)s") % {'url': url, 'dets': details.reason})
            elif hasattr(details, "code"):
                outWarning(_("%(url)s couldn\'t fulfill the request, Error code: %(dets)s") % {'url': url, 'dets': details.code})
            isAvailable["WUUsite"] = False
        else:
            isAvailable["WUUsite"] = True
    finally:
        if response:
            response.close()
            del response


def check4SCMClient(scmType):
    
    # Check to see if the SCM client exists somewhere
    
    scmClient = None
    hasClient = False
    
    if scmType == 'SVN':
        scmClient = 'svn'
    elif scmType == 'Git':
        scmClient = 'git'
    
    if not scmClient:
        return False, None
        
    # Define the SCM executable name
    if os.name == 'nt':
        scmClient = scmClient + '.exe'
    
    for path in os.getenv('PATH').split(os.pathsep) + ['./']: # have to use pathsep, since Windows uses ';', not ':'
        if os.path.isfile(os.path.join(path, scmClient)):
            hasClient = True
            break
    del path
    
    # Handle scmClient not on the Path on a Mac
    # try the default directory
    if not hasClient and sys.platform == 'darwin':
        if os.path.isfile(os.path.join('/usr/local/bin', scmClient)):
            scmClient = os.path.join('/usr/local/bin', scmClient)
            hasClient = True
        elif os.path.isfile(os.path.join('/opt/local/bin', scmClient)):
            scmClient = os.path.join('/opt/local/bin', scmClient)
            hasClient = True
    
    # Test default installation directory on Windows
    if not hasClient and os.name == 'nt':
        if scmType == 'SVN':
            windir = 'Subversion'
        elif scmType == 'Git':
            windir = 'Git'
        defscmpath = os.path.join(os.getenv('PROGRAMFILES'), windir, 'bin', scmClient)
        if os.path.isfile(defscmpath):
            scmClient = defscmpath
            hasClient = True
        del windir, defscmpath
    
    if not hasClient:
        scmClient = None
    
    return hasClient, scmClient


def clearCachePages(expiredonly = False):
    """ Clears either only the expired, or all pages from the cache """
    global pagecache
    
    size = cacheSize()
    outMessage(_("Cache size before flush: %(size)dKb in %(count)d pages") % {'count': size[0], 'size':size[1]/1024} )
    
    if not expiredonly:
        pagecache = {}
    else:
        todelete = []
        for url in pagecache:
            if not pagecache[url].isValid():
                todelete.append(url)
        
        for url in todelete:
            del pagecache[url]
    
    size = cacheSize()
    outMessage(_("Cache size after flush: %(size)dKb in %(count)d pages") % {'count': size[0], 'size':size[1]/1024} )


def downloadFile(url, localfile, shorten=False, allowcoral=True):
    """ File download that reports its progress """
    tracer.debug("downloadFile: %s, %s" % (url, localfile))
    
    global useragent
    
    if threading.currentThread().getName() != "MainThread":
        wurmlock["WurmCommon2"].acquire()
    
    if int(getGlobalSetting(":UseCoralCDN")) == 1 and allowcoral: # allowcoral is added so we can force certain urls to direct download
        # Rewrite the URL to use the Coral Content Distribution Network
        o = urlparse.urlparse(url)
        newurl = [x for x in o]
        newhost = newurl[1]
        if ':' in newhost:
            newhost = newhost.replace(':', '.')
        newurl[1] = "%s.nyud.net:8080" % (newhost)
        
        url = urlparse.urlunparse(newurl)
        logger.log(DEBUG5, "Changed URL to %s" % (url))
    
    showname = url
    # shorten the url so that it displays in the progress dialog, if required
    if shorten:
        showname = "..." + url[len(url) - 20:]
    
    try:
        try:
            blocksize = 2048 # 2kb blocks
            target = open(localfile, "wb")
            request = urllib2.Request(url)
            request.add_header('User-Agent', useragent)
            source = urllib2.urlopen(request)
            size = 0.0
            
            try:
                size = float(source.info()['Content-Length'])
            except:
                pass # ignore size error
            
            data = "dummy"
            progress = 0
            while len(data) > 0:
                data = source.read(blocksize)
                target.write(data)
                progress += len(data)
                
                if size > 0:
                    outProgressPercent(_("Downloading %(sname)s") % {'sname': showname}, progress / size)
                else:
                    # Default when size is not known is to just let the progressbar run backwards
                    outProgressPercent(_("Downloading %(sname)s") % {'sname': showname}, (10 - (int(progress / blocksize) % 10)) / 10)
            
            outProgressPercent(_("Download of %(sname)s complete!") % {'sname': showname}, 1)
            target.close()
            source.close()
        except Exception, details:
            logger.exception("Error downloading %s: %s" % (url, str(details)))
            if os.path.exists(localfile):
                os.remove(localfile) # remove file if it exists
            raise
    finally:
        if threading.currentThread().getName() != "MainThread":
            wurmlock["WurmCommon2"].release()
        resetProgress()
    
    outDebug("%(url)s downloaded to %(lfile)s" % {'url': url, 'lfile': localfile})


def downloadPage(url, opener=urllib2.build_opener(urllib2.HTTPHandler), compress=True, forcereload=False, length=307200):
    """ Returns the content from a webpage, but tries to use gzip encoding if the server supports it (unless explicitly told otherwise)
    compress = False would disable gzip encoding
    forcereload = True bypasses the cache
    length = 300 Kb
    """
    tracer.debug("downloadPage: %s, %d" % (url, length))
    
    global useragent
    
    allowcache = (int(getGlobalSetting(":WebCache", 1)) == 1) and not forcereload # Follow both global setting and parameter
    
    if allowcache: # Try the cache first
        content = getCachedPage(url)
        if content:
            return content
    
    if threading.currentThread().getName() != "MainThread":
        wurmlock["WurmCommon2"].acquire()
    
    try:
        try:
            request = urllib2.Request(url)
            request.add_header('User-Agent', useragent)
            if compress:
                request.add_header('Accept-Encoding', 'gzip')
            f = opener.open(request)
            data = None
            # Handle potentially gzipped result
            if f.headers.get('Content-Encoding', '') == 'gzip':
                gzdata = f.read()
                
                # Extract gzipped data
                gzstream = StringIO(gzdata)
                gzf = gzip.GzipFile(fileobj=gzstream)
                data = gzf.read()
                gzf.close()
                del gzdata
                del gzstream
            else:
                data = f.read(length)
            
            f.close()
        except Exception, details:
            logger.exception("Error downloading %s: %s" % (url, str(details)))
            raise
    finally:
        if threading.currentThread().getName() != "MainThread":
            wurmlock["WurmCommon2"].release()
    
    if allowcache:
        addCachedPage(url, data)
    
    logger.log(DEBUG5, "Addon webpage: %s, %d" % (url, len(data)))
    
    return data


def findAllChildren(addonname):
    """ Returns a list of all addons who are the child of this Addon """
    tracer.debug("findAllChildren")
    
    children = []
    for a in addonlist:
        if addonlist.getAtype(a) == "Child" and addonlist.getFlag(a, "Parent") == addonname:
            children.append(a)
    
    return children


def findAllRelated(addonname, stopiteration=3):
    """ Returns a list of all addons marked [Related] with "addonname" as siteid.
    It calls itself for each related Addon in case they have relations
    (e.g. Babble, PeriodicTable & SpecialEvents), unless stopiteration is 0.
    Default is to iterate 3 times.
    """
    tracer.log(DEBUG5, "findAllRelated")
    
    related = []
    try:
        for a in addonlist:
            if addonlist.getAtype(a) == "[Related]" and addonlist.getSiteid(a) == addonname:
                related.append(a)
                if stopiteration > 0:
                    related += findAllRelated(a, stopiteration - 1)
    except UnicodeWarning, details:
        msg = "UnicodeError: [%s], %s" % (addonname, str(details))
        logger.exception(msg)
        outError(msg)
    
    return related


def findDuplicateSiteIDs():
    """ Scans all addons, and returns addons with the same site/siteID combination -
    any such duplicates will result in multiple downloads of the same .zip, which is wrong
    (usually the result of errors in the online database) """
    
    tracer.log(DEBUG5, "findDuplicateSiteIDs")
    
    duplicates = {}
    seensiteids = {} # storing site|siteid: addon here, to quickly check if it's seen before
    try:
        for a in addonlist:
            if addonlist.getAtype(a)[0] != "[":
                sitesid = "%s|%s" % (addonlist.getAtype(a), addonlist.getSiteid(a))
                if sitesid in duplicates:
                    duplicates[sitesid].append(a)
                elif sitesid in seensiteids:
                    duplicates[sitesid] = [a, seensiteids[sitesid],]
                else:
                    seensiteids[sitesid] = a
    except UnicodeWarning, details:
        msg = "UnicodeError: [%s], %s" % (addonname, str(details))
        logger.exception(msg)
        outError(msg)
    
    if len(duplicates) > 0:
        outMessage(_("%(duplicatecount)d site IDs are duplicated") % {'duplicatecount': len(duplicates)})
    
    return duplicates


def getCachedPage(url):
    """ Returns a cached page if available/still valid, otherwise None """
    global pagecache
    
    if url in pagecache:
        if pagecache[url].isValid():
            return pagecache[url].content
        else:
            del pagecache[url]
    
    return None


def getDirectory(dirname, default=False):
    """ Fetches a directory from the dictionary, if it is set, otherwise returns the default """
    tracer.debug("getDirectory: %s" % (dirname))
    
    global directories
    
    if directories.has_key(dirname):
        return directories["dirname"]
    else:
        return default


def getGlobalSetting(setting, default=False):
    """ Gets a global setting, or sets it to the specified default if it doesn't exist """
    tracer.log(DEBUG5, "getGlobalSetting: %s" % (setting))
    
    global globalsettings
    
    if globalsettings.has_key(setting):
        return globalsettings[setting]
    else:
        globalsettings[setting] = default
        return default


def getListVersionFromFile(filename):
    """ Gets the version from the file - it's kinda "cheating", since the strings are directly comparable to check if a version is newer - no conversion necessary. """
    tracer.debug("getListVersionFromFile")
    
    return open(filename, "rt").read()


def loadLanguages():
    """ Loads all languages in the <WUU dir>/lang folder """
    tracer.debug("loadLanguages")
    
    global langdir
    
    if os.path.exists(langdir):
        outMessage("Loading languages from %s" % (langdir))
        for f in os.listdir(langdir):
            if "lang" in f and ".xml" in f: # TODO: Better check
                # outDebug("Loading language file %s" % (f))
                try:
                    WurmLanguage.loadLanguageFile(os.path.join(langdir, f))
                except Exception, details:
                    outWarning("Could not load entire language from %s (Reason: %s)" % (f, str(details)))
        outMessage("Available languages: %s" % (", ".join(WurmLanguage.getLanguages().keys())))


def loadRegexps():
    """ Loads the site regexps from file """
    tracer.debug("loadRegexps")
    
    global refilename, reurl, siteregexps
    
    if not os.path.exists(refilename): # grab it from the web server if it's not present
        downloadFile(reurl, refilename)
    
    relines = open(refilename, "rt").readlines()
    for line in relines:
        re = line.strip().split("\t")
        if len(re) >= 2:
            siteregexps[re[0]] = re[1]
            tracer.debug("Loaded regexp %s" % (re[0]))


def loadTemplates():
    """Process the templates file"""
    tracer.debug("WurmCommon - loadTemplates")
    
    global ostemplates, childtemplates, ostKeys, childtKeys
    
    if not os.path.exists(templatefilename): # grab it from the web server if it's not present
        try:
            downloadFile(templateurl, templatefilename)
        except:
            pass # ignore download error
    
    if not os.path.exists(templatefilename): # if it's still not there display warning and leave
        outWarning(_("Templates file, %s, is unavailable") % templatefilename)
        return
    
    try:
        dom = xml.dom.minidom.parse(templatefilename)
        modelslist = dom.getElementsByTagName("templates")[0]
        osmodels = modelslist.getElementsByTagName("othersites")
        childmodels = modelslist.getElementsByTagName("child")
        
        for ost in osmodels:
            templatename = Wurm.getXMLText(ost.getElementsByTagName("templatename")[0].childNodes)     
            
            ostemplates[templatename] = {}
            
            parameters = ost.getElementsByTagName("parm")
            
            for parm in parameters:
                if parm.hasAttribute("name"):
                    name = Wurm.getXMLText(parm.attributes["name"].childNodes)
                    ftype = "str"
                    if parm.hasAttribute("type"):
                        ftype = Wurm.getXMLText(parm.attributes["type"].childNodes)
                    
                    value = Wurm.getXMLText(parm.childNodes)
                    if ftype == "bool":
                        if value in ('1', 'True'):
                            value = True
                        else:
                            value = False
                    
                    ostemplates[templatename][name] = value
        
        for child in childmodels:
            templatename = Wurm.getXMLText(child.getElementsByTagName("templatename")[0].childNodes)     
            
            childtemplates[templatename] = {}
            
            parameters = child.getElementsByTagName("parm")
            
            for parm in parameters:
                if parm.hasAttribute("name"):
                    name = Wurm.getXMLText(parm.attributes["name"].childNodes)
                    ftype = "str"
                    if parm.hasAttribute("type"):
                        ftype = Wurm.getXMLText(parm.attributes["type"].childNodes)
                    
                    value = Wurm.getXMLText(parm.childNodes)
                    if ftype == "bool":
                        if value in ('1', 'True'):
                            value = True
                        else:
                            value = False
                    
                    childtemplates[templatename][name] = value
    
    except Exception, details:
        logger.exception("Error processing %s: %s" % (templatefilename, str(details)))
        raise
    
    tracer.debug("Template tables: %s\n%s" % (str(ostemplates), str(childtemplates)))
    
    # now sort the keys ready for the dialogs
    ostKeys = ostemplates.keys()
    ostKeys.sort()
    childtKeys = childtemplates.keys()
    childtKeys.sort()
    
    tracer.debug("Template keys: %s\n%s" % (str(ostKeys), str(childtKeys)))


def nullOutput():
    """ Resets the message callbacks to default """
    tracer.debug("nullOutput")
    
    global cbOutMessage, cbOutDebug, cbOutWarning, cbOutError, cbOutStatus, cbProgressPercent, cbResetProgress, cbProgressPercent2, cbResetProgress2
    
    cbOutMessage       = None
    cbOutDebug         = None
    cbOutWarning       = None
    cbOutError         = None
    cbOutStatus        = None
    cbProgressPercent  = None
    cbResetProgress    = None
    cbProgressPercent2 = None
    cbResetProgress2   = None


def outDebug(msg):
    """"""
    tracer.log(DEBUG7, "outDebug")
    
    if cbOutDebug is None:
        logger.debug(msg)
    else:
        cbOutDebug(msg)


def outMessage(msg):
    """"""
    tracer.log(DEBUG7, "outMessage")
    
    if cbOutMessage is None:
        logger.info(msg)
    else:
        cbOutMessage(msg)


def outWarning(msg):
    """"""
    tracer.log(DEBUG7, "outWarning")
    
    if cbOutWarning is None:
        logger.warn(msg)
    else:
        cbOutWarning(msg)


def outError(msg):
    """"""
    tracer.log(DEBUG7, "outError")
    
    if cbOutError is None:
        logger.error(msg)
    else:
        cbOutError(msg)


def outStatus(msg):
    """"""
    tracer.log(DEBUG7, "outStatus")
    
    if cbOutStatus is None:
        logger.log(STATUS, msg)
    else:
        cbOutStatus(msg)


def outProgressPercent(task, fraction):
    """"""
    tracer.log(DEBUG7, "outProgressPercent")
    
    percent = int((fraction * 100) + 0.5) # 0.5 to force it to round up
    if cbProgressPercent:
        cbProgressPercent(task, percent)


def outProgressPercent2(fraction):
    """"""
    tracer.log(DEBUG7, "outProgressPercent2")
    
    percent = int((fraction * 100) + 0.5) # 0.5 to force it to round up
    if cbProgressPercent2:
        cbProgressPercent2(percent)


def removeBOM(data):
    """"""
    tracer.log(DEBUG5, "removeBOM")
    
    # determine if a codec has been used when the file was written
    try:
        if data[0][:2] == codecs.BOM:
            foundBOM = "BOM"
            data[0] = data[0][2:]
        elif data[0][:3] == codecs.BOM_UTF8:
            foundBOM = "BOM_UTF8"
            data[0] = data[0][3:]
        elif data[0][:4] == codecs.BOM_UTF32:
            foundBOM = "BOM_UTF32"
            data[0] = data[0][4:]
        else:
            foundBOM = None
        
        if foundBOM is not None:
            tracer.log(DEBUG3, "Removed BOM: [%s]" % (foundBOM))
    except IndexError:
        pass # Could not read BOM; not fatal, might be empty TOC
    return data


def resetProgress():
    """"""
    tracer.log(DEBUG7, "resetProgress")
    
    if cbResetProgress:
        cbResetProgress()


def resetProgress2():
    """"""
    tracer.log(DEBUG7, "resetProgress2")
    
    if cbResetProgress2:
        cbResetProgress2()


def setUserAgent(wuuversion):
    """ Sets the user agent to use for web requests.
    Also sets the socket timeout, in lieu of a better place. """
    tracer.debug("setUserAgent")
    
    global useragent
    
    wuuplatform = "Unknown"
    if sys.platform[:5] == 'linux':
        wuuplatform = 'X11; U; Linux %s; Python %s' % (platform.machine(), platform.python_version())
    elif sys.platform == 'darwin':
        maccpu = 'PPC'
        if platform.machine() == 'i386':
            maccpu = 'Intel'
        wuuplatform = 'Macintosh; U; %s Mac OS X' % (maccpu)
    elif sys.platform == 'win32':
        winver = platform.version()[:3] # should grab only the major.minor of the OS version
        wuuplatform = 'Windows; U; Windows NT %s; Python %s' % (winver, platform.python_version())
    
    useragent = "WUU/%s (%s)" % (wuuversion, wuuplatform) # sets the user agent used for web requests
    logger.log(DEBUG5, 'User agent set to %s' % (useragent))
    
    # Try to set global socket timeout - if unparseable as an integer, use blocking mode
    try:
        timeout = int(getGlobalSetting(":SocketTimeout"))
        if timeout > 0:
            socket.setdefaulttimeout(timeout)
            outDebug("Socket timeout set to %d seconds" % (timeout))
    except:
        pass # blocking mode (the all-round default)


def str2tuple(s):
    """Convert tuple-like strings to real tuples.
    eg '(1,2,3,4)' -> (1, 2, 3, 4)
    """
    tracer.log(DEBUG5, "str2tuple")
    
    if s[0] + s[-1] != "()":
        raise ValueError("Badly formatted string (missing brackets).")
    
    items = s[1:-1] # removes the leading and trailing brackets
    items = items.split(',')
    L = [int(x.strip()) for x in items] # clean up spaces, convert to ints
    
    return tuple(L)


def uniq(alist): # Fastest order preserving
    """ Returns alist, but with duplicates removed (order is preserved) """
    tracer.log(DEBUG5, "uniq: %s" % str(alist))
    
    newset = {}
    return [newset.setdefault(e,e) for e in alist if e not in newset]


def BackupAddons(listedaddons):
    """ Copies the listed addons to the backup directory """
    tracer.debug("BackupAddons: %s" % str(listedaddons))
    
    global directories
    
    if isinstance(listedaddons, str): # single addon
        listedaddons = [listedaddons] # convert to list
    
    if len(directories["backup"]) > 0 and os.path.exists(directories["backup"]):
        for addon in listedaddons:
            if addon in addonlist and addonlist.getAtype(addon) not in ("[Ignore]", "[Dummy]"):
                addondir  = os.path.join(directories["addons"], addon)
                backupdir = os.path.join(directories["backup"], addon)
                if os.path.exists(addondir):
                    # check to see if the only file in the addon directory is placeholder.txt
                    # if so then ignore the backup
                    dirlist = os.listdir(addondir)
                    if len(dirlist) == 1 and "placeholder.txt" in dirlist:
                        continue
                    if os.path.exists(backupdir): # old backup exists, have to delete
                        try:
                            _deleteBackup(addon)
                        except:
                            raise
                    
                    try:
                        shutil.copytree(addondir, backupdir)
                        outDebug("Backup of %(addon)s done" % {'addon': addon})
                    except Exception, details:
                        outWarning(_("Backup of %(addon)s failed") % {'addon': addon})
                        outDebug("^^^^ %s" % (str(details)))


def DeleteAddons(listedaddons, cleansettings=False):
    """ Deletes the listed addons from the WoW interface dir.
    If cleansettings is True, all traces of the addons are removed from the lists
    """
    tracer.debug("DeleteAddons: %s, %s" % (str(listedaddons), cleansettings))
    
    global addonlist, addons, toclist, listchanged
    
    if not isinstance(listedaddons, list): # single addon
        listedaddons = list((listedaddons, )) # convert to a list
    
    total = failed = 0
    
    for addon in listedaddons:
        total += 1
        
        # If the addon isn't new then back it up and delete it
        if addon in addonlist and not addonlist.getFlag(addon, 'install'):
            # Backup the addon
            BackupAddons(addon)
            
            try:
                # Delete the addon
                _deleteAddon(addon)
                outDebug("%(addon)s removed successfully" % {'addon': addon})
            except Exception, details:
                if details.errno == 2: #ignore file/directory missing errors
                    pass
                else:
                    outError(_("Failed to remove %(addon)s: %(details)s") % {'addon': addon, 'details': str(details)})
                    failed += 1
        
        # Then do some cleanup if required
        if cleansettings:
            
            if addonlist.has_key(addon):
                addonlist.delete(addon)
            
            if addons.has_key(addon):
                del addons[addon]
            
            if toclist.has_key(addon):
                del toclist[addon]
            
    return total, failed


def InstallAddon(addon):
    """ Install an Addon using it's Update Method '"""
    tracer.debug("InstallAddon: %s" % (addon))
    
    try:
        Wurm.refreshSingleAddon(addon)
        if addon in addons:
            return addons[addon].updateMod()
        else:
            outWarning(_("Unable to Install %(name)s, Invalid Source Site") % {'name': addon})
            raise Exception, "Invalid Source Site"
    except Exception, details:
        logger.exception("Error, install of %s failed: %s" % (addon, str(details)))
        raise


def RestoreAddon(addon):
    """ Copies the addon back from the backup directory """
    tracer.debug("RestoreAddon: %s" % (addon))
    
    global directories
    
    if len(directories["backup"]) > 0 and os.path.exists(directories["backup"]):
        addondir  = os.path.join(directories["addons"], addon)
        backupdir = os.path.join(directories["backup"], addon)
        if os.path.exists(backupdir):
            # clean out dir if it already exists
            if os.path.exists(addondir):
                try:
                    _deleteAddon(addon)
                except:
                    raise
            
            try:
                # Copy the Backup to the Addon directory
                shutil.copytree(backupdir, addondir)
                # Refresh the Addon details
                Wurm.refreshSingleAddon(addon)
                # Remove the Backup
                _deleteBackup(addon)
                outDebug("%(addon)s restored successfully" % {'addon': addon})
                return True
            except Exception, details:
                logger.exception("Error, restore of %s failed: %s" % (addon, str(details)))
                raise
        else:
            outWarning(_("No backup of %(addon)s exists") % {'addon': addon})
            return False


acronym = lambda xstr: "".join([x for x in xstr if x.isupper()]) # to quickly get the acronym for an addon

def FindRecentDownloads(addon, ageminutes=180):
    """ Looks in the default download folder to find potential matches for the given addon,
    downloaded recently (as specified by ageminutes) """
    
    tracer.debug("FindRecentDownloads: %s" % (addon))
    
    bdd = getGlobalSetting(":BrowserDownloadDir", None)
    if not bdd or not os.path.exists(bdd):
        outError("Can't check download directory '%s', setting not set or directory does not exist" % (bdd,))
        return []
    
    # use friendly name to help with acronym checks
    if addon in addonlist:
        addon = addonlist.getFname(addon)
    
    base_re = "[-_]?[vr]?.*\d*.*\.zip|rar"
    filename_re =  addon + base_re # typically, most will match this regexp
    
    # add "^" to ensure correct file is chosen
    fre = re.compile("^" + filename_re)

    filelist = os.listdir(bdd)
    tmpresult = []
    
    # Find all matching files
    for fn in filelist:
        if len(fre.findall(fn)) > 0:
            if fn[-3:] == "zip" or fn[-3:] == "rar":
                tmpresult.append(fn)
    
    # use this if the first one doesn't return ANYTHING
    if len(tmpresult) == 0:
        acronym_re = acronym(addon) + base_re # some will only match this (DeadlyBossMods -> DBM)
        if len(acronym_re) > 1: # if we made an acronym larger than 1 character
            fre = re.compile("^" + acronym_re)
            # Find all matching files
            for fn in filelist:
                if len(fre.findall(fn)) > 0:
                    if fn[-3:] == "zip" or fn[-3:] == "rar":
                        tmpresult.append(fn)
    
    # Then filter out older files (and add full path to the name)
    cutoff = datetime.now() - timedelta(minutes=ageminutes)
    
    result = []
    
    try:
        for fn in tmpresult:
            fullpath = os.path.join(bdd, fn)
            fstat = os.stat(fullpath)
            # outDebug("stat info: [%s], atime:%s, mtime:%s, ctime:%s]" % (str(fstat), datetime.fromtimestamp(fstat.st_atime), datetime.fromtimestamp(fstat.st_mtime), datetime.fromtimestamp(fstat.st_ctime)))
            ftime = datetime.fromtimestamp(fstat.st_ctime) # use creation timestamp [works on Mac OS ;-)]
            # ftime = datetime.fromtimestamp(os.stat(fullpath).st_mtime)
            if ftime >= cutoff:
                result.append(fullpath)
    except Exception, details:
        outError(_("Error retrieving file stat info: [%s]" % str(details)))
        
    return result

