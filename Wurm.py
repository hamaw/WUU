# -*- coding: utf-8 -*-
# $Id: Wurm.py 666 2009-06-30 17:37:45Z lejordet $

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

# 2008-02-19: Applied patch 1878041 by sourceforge user iroro

import logging
logger = logging.getLogger(None)
tracer = logging.getLogger("WUUtrace")

import os, tempfile, re, sys, shutil
from subprocess import *
import xml.dom.minidom
import urllib, urllib2, socket
import urlparse
from datetime import date, timedelta, datetime
from time import sleep, gmtime

# decimal support MUST be included as below, otherwise it doesn't work
from decimal import *
import string
import threading
import codecs

import WurmCommon
import WurmUnpack
import WurmWTF

WurmWTF.WurmCommon = WurmCommon # FIXME: better way to do this?

try:
    from xml.etree.cElementTree import ElementTree, Element, SubElement
except ImportError:
    try:
        # Fallback level 1, try the "native" ElementTree in Python 2.5
        from xml.etree.ElementTree import ElementTree, Element, SubElement
    except ImportError:
        # Fallback level 2, use the provided ElementTree
        from ElementTree import ElementTree, Element, SubElement

# remap dummy translation function to real trans func
_ = WurmCommon.WurmLanguage.s

hasSVN, svn = WurmCommon.check4SCMClient('SVN')
hasGit, git = WurmCommon.check4SCMClient('Git')

try:
    from cStringIO import StringIO
except ImportError:
    import StringIO

# check to see if the ezCrypto package is installed
try:
    import ezPyCrypto
    canAutoUpdate = True
except ImportError:
    canAutoUpdate = False

# Version number is bumped everytime the XML format changes significantly, or other major changes are included
# ...and for major releases, of course
wurmversion = "1.9"

# As made by ezPyCrypto
publickey = '<StartPycryptoKey>\nKEkwMApOVLMCAAAoVQNSU0FxAChjQ3J5cHRvLlB1YmxpY0tleS5SU0EKUlNBb2JqCnEBb3ECfXEE\nKFUBZXEFTDY1NTM3TApVAW5xBkwyODI5Nzc1MjE1Nzc3OTU5OTYyMzQ1MzY5MDI2MDc4MTk2NzA4\nMDU0NTUwNzUwMzYzMDMwODkyMzAxMjQ1MDM2Mzg4MzM2MjI0NTYzNjY2MjMzMDg2OTk2NDI5NzYz\nODY1ODkxODYzMzE1OTMwMjgzNDI3Njk1MTY0NjE1NjQxODU5NTQ1MDg4NTA3Njg5NzQ5NTAyNjc4\nOTc0NzA1MTkyNjMyMDA3NDc1NTAwNTcyMjQ0OTYxMjgyNTE3ODkzMjU5NDU4MzY5NTgzOTA3Nzc5\nMDEyNDc0Mjc5NDExOTU4MzYzNTUxMTMwMDcwNDY3NDg2MTI0MDA1ODA2NDY3NzcxMDU0MTIxODYx\nNzIxMzk1NzU2MDc2MzcxNzY1NDU1NjE1MjU1ODEzMjkxNDkxMTMzNjg4MDk1Mzk4MTAxNDM0NzQ5\nNzgwNTA0ODM2NzY2ODEwODc3MzEyMDUyMzgyNTAwNzQwNTU4NjAzODg0MzI5ODM0MzU5MzcyMjIz\nOTQ2MDEzMTMyMDkwNjA2NjgxNDY2Mzg0ODY1NjgyMDk5ODg2ODYyMjAzNjQ0MTQ1MjAwMjQyODc3\nMjQ0ODc5NTg5MDIwMjUwMDE3NzEzMjMwNTQzMTE5MTgzOTEzODM4NzU3NDY4MTg2MDk4NjY3Mzcy\nNDg3NDQzMTc1NzQzODAzOTcyNDUyNjM0MDA4NjI2MDM0OTQxMzk0MTE2MzEzMjM0NzY2ODY3OTcx\nODc5NjYwOTc4MjcwNzcwOTE5MzI4NjE0NjcyOTc2ODM2MDk5NjY2OTQzMTA0OTEzMDI2MTg1MzMy\nMDgyMzk5MDgxMUwKdWJ0cQcucQB0cQEu\n<EndPycryptoKey>\n'

# constants
origappldir   = WurmCommon.origappldir
appldir       = WurmCommon.appldir
supportdir    = WurmCommon.supportdir
addoninfofile = "addons.wurm.xml"
interfacedir  = "Interface"
addonsdir     = "AddOns"
wuubackupdir  = "WUUBackup"
addondatafile = ""

# common Ace libraries
ace1libs = ['AceAddon', 'AceChatCmd', 'AceCommands', 'AceData', 'AceDB', 'AceEvent', 'AceHook', 'AceLocals', 'AceModule', 'AceState']
ace2libs = ['AceAddon-2.0', 'AceComm-2.0', 'AceConsole-2.0', 'AceDB-2.0', 'AceDebug-2.0', 'AceEvent-2.0', 'AceHook-2.1', 'AceLibrary', 'AceLocale-2.2', 'AceModuleCore-2.0', 'AceOO-2.0', 'AceTab-2.0']
acelibs = ace1libs + ace2libs

# constants for webside link-in
infosubmiturl = WurmCommon.wuusite + "submitaddonpack2.php" # changed to "2" in 1.8.591
addonsidurl   = WurmCommon.wuusite + "addonsettings.php"
addonpackurl  = WurmCommon.wuusite + "addonpack.php"

reportTemplateStart = u"""<html><head><title>WUU Update Report</title><head><body>"""
reportTemplateEnd   = u"""<p align="right"><font size="-3">Generated %s by WUU %s</font></p></body></html>"""

# Dictionary of expected formats for install/identify from URL
installFromURLsupported = {
    # "AceSVN":{
    #     "format": ["http://svn.wowace.com/wowace/[branches|tags|trunk]/<Addon name>/<additional path>",],
    #     "example": "http://svn.wowace.com/wowace/branches/Grid/jerry/Grid/",
    # },
    "GoogleCodeSVN":{
        "format": ["http://<developer>.googlecode.com/svn/[branches|tags|trunk]/<Addon name>",],
        "example": "http://wow-haste.googlecode.com/svn/trunk/Maneki/",
    },
    "WoWAce":{
        "format": ["http://www.wowace.com/projects/<Addon name>",],
        "example": "http://www.wowace.com/projects/ora3/",
    },
    "CurseGaming":{
        "format": ["http://[wow|www].curse.com/downloads/wow-addons/details/<Addon ID>.aspx/",],
        "example": "http://wow.curse.com/downloads/wow-addons/details/ora2.aspx",
    },
    "WoWI":{
        "format": ["http://(www.)wowinterface.com/downloads/[download|info]<Addon ID>-<Addon name>",],
        "example": "http://www.wowinterface.com/downloads/info5244-BigWigs",
    },
    "DBM":{
        "format": ["http://(www.)deadlybossmods.com/download.php?id=<Addon ID>",],
        "example": "http://www.deadlybossmods.com/download.php?id=1",
    },
}

class Addon:
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    websitedowncodes = [60, 500, 501, 502, 504, 505]
    def __init__(self, localname, siteid, baseurl="", flags={}):
        """"""
        tracer.log(WurmCommon.DEBUG5, "Addon - __init__")
        
        self.specialflags = flags # site specific flags are stored here
        self.configurable = {} # a list of which specialflags should be configurable from the UI - format: "Flag short description": ("Flagname", "Flag long description", <default value>), type of default value sets type of input box
        
        self.baseurl       = baseurl
        self.localname     = localname
        if not siteid:
            self.siteid    = self.localname
        else:
            self.siteid    = siteid
        self.versionfile   = '%s.wuuver' % (self.localname)
        self.localversion  = self.getLocalModVersion()
        self.prevversion   = -1 # used to get the version number from pre-update
        self.onlineversion = -1
        self.updated       = False
        self.clreport      = False # whether a changelog report has been shown for the last update
        self.wasembedonly  = False
        self.realDlExt     = "zip"
        self.dlURL         = ""
    
    
    def _expandVer(self, ver):
        """ Tries to expand a version on the form major.minor so it's numerically comparable (i.e. 3.12 > 3.4) - if needed """
        outver = ver
        
        if isinstance(outver, str):
            try:
                if "." in outver:
                    major, minor = outver.split('.')
                    minor        = '%04d' % int(minor)
                    outver       = '%s.%s' % (major, minor)
                    outver       = Decimal(outver)
                else:
                    outver = int(outver)
            except:
                pass
        
        return outver
    
    
    @classmethod
    def _getAvailability(cls):
        """ Returns the URL Availability setting """
        tracer.log(WurmCommon.DEBUG5, "Addon - _getAvailability: %s" % (cls))
        
        # BUGTEST: Have to try and shortcut this a bit, might be leading to errors for some users
        # return True
        
        if not cls in WurmCommon.isAvailable:
            WurmCommon.isAvailable[cls] = True
        
        return WurmCommon.isAvailable[cls]
    
    
    def _getChangelogFilename(self):
        """ Returns the Changelog Filename if there is one """
        tracer.debug("Addon - _getChangelogFilename")
        
        ver = self.localversion
        # ignore the minor part if a decimal value
        v   = ver
        cl3 = cl4 = ""
        if isinstance(ver, str):
            if "." in ver:
                v, minor = ver.split(".")
                # setup changelog filenames with the decimal value
                cl3 = os.path.join(WurmCommon.directories["addons"], self.siteid, "changelog-r%s.txt" % (ver))
                cl4 = os.path.join(WurmCommon.directories["addons"], self.siteid, "changelog-%s-r%s.txt" % (self.siteid, ver))
        
        # setup changelog filenames without the decimal value
        cl1 = os.path.join(WurmCommon.directories["addons"], self.siteid, "changelog-r%s.txt" % (v))
        cl2 = os.path.join(WurmCommon.directories["addons"], self.siteid, "changelog-%s-r%s.txt" %  (self.siteid, v))
        if v > 0:
            if os.path.exists(cl1):
                return cl1
            if os.path.exists(cl2):
                return cl2
            if os.path.exists(cl3):
                return cl3
            if os.path.exists(cl4):
                return cl4
        
        return None
    
    
    def _getFlag(self, flag, default=False):
        """ Returns an Addon's specialflag setting """
        tracer.log(WurmCommon.DEBUG5, "Addon - _getFlag")
        
        return self.specialflags.setdefault(flag, default)
    
    
    def _getRealDlURL(self):
        """ Returns the Real download URL """
        tracer.debug("Addon - _getRealDlURL")
        
        return self.dlURL
    
    
    def _safeURL(self, url):
        """ Converts special chars in URLs to something urllib can use """
        tracer.log(WurmCommon.DEBUG5, "Addon - _safeURL")
        
        # added 2007-07-29: Ogri'Lazy has a ' in the zip name
        result = url.replace("'", "%27").replace("&#039;", "%27")
        
        # added 2007-08-01: Some addons don't work if the site ID contains a ! (bug 1765260)
        result = result.replace("!", "%21")
        
        # generic problem: spaces in the URL
        return result.replace(" ", "%20")
    
    
    @classmethod
    def _setAvailability(cls):
        """ Sets the URL Availability """
        tracer.log(WurmCommon.DEBUG5, "Addon - _setAvailability: %s" % (cls))
        
        WurmCommon.isAvailable[cls] = not WurmCommon.isAvailable.get(cls, False) # have to use .get here, in case it's not seen before
    
    
    def _versionFromText(self, ver):
        """ Converts version numbers on the form X.Y.Z to a single integer """
        tracer.log(WurmCommon.DEBUG5, "Addon - _versionFromText")
        
        # removes unparseable chars first
        res = ""
        for a in ver:
            if a.isdigit():
                res += a
            elif a == ".":
                res += a
            elif a.isalpha():
                # res += ".%d" % (ord(a))
                pass # ignore alphabetic character
            else:
                pass # ignore unparseable character
        ver = res
        version = int("".join(["%03d"%(int(yp)) for yp in ver.split(".")])) # basically expands each of X Y and Z to three digits, then concatenates the strings, and then parses the int
        # end result: 2.9.1 -> 2009001
        return version
    
    
    def downloadMod(self):
        """ Downloads the package, but does not install """
        tracer.debug("Addon - downloadMod: %s" % self.localname)
        
        if self.onlineversion < 0:
            self.onlineversion = self.getOnlineModVersion()
            if self.onlineversion < 0: # Site down?
                raise Exception, "Unable to get Online version: %d" % self.onlineversion
        
        if not self._getRealDlURL():
            msg = _("No download URL found for %(lname)s") % {'lname': self.localname}
            WurmCommon.outWarning(msg)
            raise Exception, msg
        
        if threading.currentThread().getName() != "MainThread":
            WurmCommon.wurmlock[self.addontype].acquire()
        
        modfilename = "%s-r%s.%s" % (self.localname, self.onlineversion, self.realDlExt)
        localfile   = os.path.join(WurmCommon.directories["temp"], modfilename)
        
        try:
            try:
                finalurl = self._safeURL(self._getRealDlURL())
                WurmCommon.downloadFile(finalurl, localfile)
                try:
                    # Quick sleep (default 100ms) to give antivirus time to scan file
                    # Might help with "[Error 32] The process cannot access the file because it is being used by another process"
                    sleep(int(WurmCommon.getGlobalSetting(":AVTimeOut", 100))/1000.0)
                except:
                    pass
                return localfile
            except Exception, details:
                WurmCommon.outWarning(_("Download of %(lname)s failed, URL=%(url)s: %(dets)s") % {'lname': self.localname, 'url': finalurl, 'dets': str(details)})
                raise
        finally:
            if threading.currentThread().getName() != "MainThread":
                WurmCommon.wurmlock[self.addontype].release()
    
    
    def downloadPage(self, pageurl, length=102400):
        """default length = 100Kb """
        tracer.debug("Addon - downloadPage: %s, %d" % (pageurl, length))
        
        if self.siteid == "" or "XXXX" in self.siteid:
            WurmCommon.outError("SiteID for %s not set" % (self.localname))
            return -1
        
        htm = ""
        if self._getAvailability():
            if threading.currentThread().getName() != "MainThread":
                WurmCommon.wurmlock[self.addontype].acquire()
            try:
                try:
                    htm = WurmCommon.downloadPage(self._safeURL(pageurl), length=length)
                except Exception, details:
                    WurmCommon.outWarning(_("Could not open %(addon)s web page: %(purl)s, %(dets)s") % {'addon': self.localname, 'purl':pageurl, 'dets': str(details)})
                    WurmCommon.outDebug("Error: [%(dets)s] [%(vars)s]" % {'dets': repr(details), 'vars': vars(details)})
                    if hasattr(details, "reason"):
                        WurmCommon.outDebug("Error: [%(reason)s] [%(args)s]" % {'reason': details.reason, 'args': details.args})
                    errNo = 0
                    if hasattr(details, 'reason'):
                        WurmCommon.outDebug("...has an reason attr")
                        if isinstance(details.reason, socket.timeout):
                            WurmCommon.outDebug("...is a socket.timeout")
                            errNo = 60
                        elif isinstance(details.reason, socket.error):
                            WurmCommon.outDebug("...is a socket.error")
                            errNo = details.reason[0]
                    else:
                        errNo = details.code
                    WurmCommon.outDebug("Error No: [%s]" % errNo)
                    # check to see if this indicates that the Website is unavailable
                    if errNo in self.websitedowncodes:
                        self._setAvailability()
                        WurmCommon.outWarning(_("%(lname)s's Website Unavailable") % {'lname': self.localname})
                    return -3
            finally:
                if threading.currentThread().getName() != "MainThread":
                    WurmCommon.wurmlock[self.addontype].release()
        else:
            WurmCommon.outWarning(_("%(lname)s's Website Unavailable, please try later") % {'lname': self.localname})
        if htm == "":
            return -4 # no page found, or the version isn't available
        
        return htm
    
    
    def fullChangelogHTML(self):
        """ Returns the full available changelog as HTML """
        tracer.debug("Addon - fullChangelogHTML")
        
        return self.lastChangelogHTML(1)
    
    
    # @abstract
    def getAddonURL(self):
        """ Override to return a webpage for the link in main UI """
        tracer.debug("Addon - getAddonURL")
        
        import inspect
        caller = inspect.getouterframes(inspect.currentframe())[1][3]
        raise NotImplementedError(caller + ' must be implemented in subclass')
    
    
    def getAddonDlURL(self):
        """ Returns a link to the actual download page of the newest version (default same as addon url) """
        tracer.debug("Addon - getAddonDlURL")
        
        return self.getAddonURL() # override where necessary
    
    
    def getAvailableOnlineRestores(self):
        """ Helper function to getAvailableRestores, meant to be overridden by specific site classes """
        return []
    
    
    def getAvailableRestores(self, allowOnline=False):
        """ Returns (filename, version, source) tuples for possible downgrades to the current addon
        source can be either "backup" for the WUUBackup directory, "local" for the temporary directory,
        or "online" for previous versions from the web site.
        If allowOnline is False, only backup and local addons are listed.
        """
        
        result = []
        
        # Test 1: Local backup
        
        backupverfile = os.path.join(WurmCommon.directories["backup"], self.localname, "%s.wuuver" % (self.localname))
        if os.path.exists(backupverfile):
            try:
                version = open(backupverfile, "rt").read()
                result.append(("WUUBackup/%s" % self.localname, version, "backup"))
            except:
                pass
        
        # Test 2: The temp directory
        
        tempfiles = os.listdir(WurmCommon.directories["temp"])
        oldversions = [x for x in tempfiles if "%s-r" % (self.localname) in x] # looks for files on the pattern LocalName-r*.*
        
        for oldfile in oldversions:
            version = oldfile[len("%s-r" % (self.localname)):oldfile.rfind(".")]
            result.append((oldfile, version, "local"))
        
        # Test 3: The specific site, if allowed
        
        if allowOnline:
            result.extend(self.getAvailableOnlineRestores())
        
        return result
    
    
    def getBackupStatus(self):
        """ Returns the Backup Status """
        tracer.log(WurmCommon.DEBUG5, "Addon - getBackupStatus")
        
        if os.path.exists(os.path.join(WurmCommon.directories["backup"], self.localname)):
            return True
        else:
            return False
    
    
    def getLastUpdate(self):
        """ Returns a (previousversion, currentversion) tuple,
        or None if the mod hasn't been updated this session.
        A fresh install of an addon (unknown previous version)
        also counts as "not updated" """
        
        tracer.debug("Addon - getLastUpdate: %s" % self.localname)
        
        if not self.updated or \
               Decimal(self.prevversion) < 0 or \
               Decimal(self.localversion) < 0 or \
               Decimal(self.prevversion) >= Decimal(self.localversion):
            return None
        
        return (Decimal(self.prevversion), Decimal(self.localversion))
    
    
    def getLocalModVersion(self):
        """ Returns the version from the local WUU version file """
        tracer.log(WurmCommon.DEBUG5, "Addon - getLocalModVersion")
        
        versionpath = os.path.join(WurmCommon.directories["addons"], self.localname)
        verfilepath = os.path.join(versionpath, self.versionfile)
        # Check to see if it exists, if not then try the old filename
        oldver = False
        if not os.path.isfile(verfilepath):
            verfilepath = os.path.join(versionpath, 'version.txt')
            oldver = True
        
        try:
            version = open(verfilepath, "rt").read()
        except:
            return -2
        
        # If it was an old version then write the version info to the new file
        # and remove the old file
        if oldver:
            self.setLocalModVersion(version)
            os.remove(verfilepath)
            WurmCommon.outMessage(_("Converted %(addon)s's version.txt to %(verfile)s") % {'addon': self.localname, 'verfile': self.versionfile})
        
        # WurmCommon.outDebug("%s local version: %s" % (self.localname, version))
        
        return version
    
    
    # @abstract
    def getOnlineModVersion(self):
        """ Returns the Online version number """
        tracer.debug("Addon - getOnlineModVersion")
        
        import inspect
        caller = inspect.getouterframes(inspect.currentframe())[1][3]
        raise NotImplementedError(caller + ' must be implemented in subclass')
    
    
    def lastChangelogHTML(self, fromversion=None):
        """ Returns the changelog since the last update (or fromversion,
        if specified), as HTML """
        
        tracer.debug("Addon - lastChangelogHTML")
        
        return ""
    
    
    def setLocalModVersion(self, newVersion):
        """ Updates the local WUU version file to the new version """
        tracer.debug("Addon - setLocalModVersion")
        
        versionpath = os.path.join(WurmCommon.directories["addons"], self.localname)
        verfilepath = os.path.join(versionpath, self.versionfile)
        try:
            open(verfilepath, "wt").write("%s" % (newVersion))
        except:
            return False
        
        self.prevversion = self.localversion
        self.localversion = newVersion
        return True
    
    
    def smartUpdateMod(self):
        """ Updates the local mod if either the online version is newer,
        or the local version is unknown - the online version is updated
        before a decision is made. This differs slightly from the regular
        check in updateAvailable, which will return False if the local
        version is unknown."""
        
        tracer.debug("Addon - smartUpdateMod")
        
        if Decimal(self.onlineversion) < 0:
            self.onlineversion = self.getOnlineModVersion()
            if Decimal(self.onlineversion) < 0: # Site down?
                return False
        
        WurmCommon.outDebug("smartUpdateMod: [%s, %s, %s]" % (self.localname, self.localversion, self.onlineversion))
        
        # using _expandVer, since revision 54032.50 should be considered higher than 54032.6
        if self._expandVer(self.localversion) < self._expandVer(self.onlineversion):
            # since the local version will be < 0 when unknown, this should work perfectly
            WurmCommon.outMessage(_("Update of %(lname)s needed") % {'lname': self.localname})
            return self.updateMod()
        
        return True
    
    
    def sync(self):
        """ Get the Addon version information """
        tracer.debug("Addon - sync: %s" % (self.localname))
        
        self.localversion  = self.getLocalModVersion()
        self.onlineversion = self.getOnlineModVersion()
        
        if Decimal(self.onlineversion) < 0:
            return False
        
        return True
    
    
    def updateAddonFromFileSelect(self, addon):
        """ Pops up a file selector dialog to ask the user which file is an update for the given addon """
        
        # Try a dirty trick in selecting the most recent file seemingly for this addon, to possibly save time
        quick = WurmCommon.FindRecentDownloads(addon)
        if len(quick) > 0:
            if len(quick) > 1:
                quick.sort()
                quick.reverse() # this probably gives a better result than grabbing the first item
            
            fn = quick[0]
            
            msg = wx.MessageDialog(self, _("Is %(filename)s the correct file for %(addon)s?\nFull path: %(fullpath)s") % {'addon': addon, 'filename': os.path.basename(fn), 'fullpath':fn}, _("Select updated package for %(addon)s")  % {'addon': addon}, style=wx.YES_NO|wx.ICON_WARNING)
            answer = msg.ShowModal()
            msg.Destroy()
            
            if answer == wx.ID_YES: # Shortcut!
                WurmCommon.outMessage(_("Updating %(addon)s from %(filename)s") % {'addon': addon, 'filename':os.path.basename(fn)})
                
                WurmCommon.addons[addon].updateModFromFile(fn)
                self._queueCallback(addon, "update")
                return
        
        dlg = wx.FileDialog(self, _("Select an updated package for %(addon)s") % {'addon': addon}, defaultDir=self._getSetting(":BrowserDownloadDir", ""), style=wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            WurmCommon.outMessage(_("Updating %(addon)s from %(filename)s") % {'addon': addon, 'filename':dlg.GetFilename()})
            
            WurmCommon.addons[addon].updateModFromFile(dlg.GetPath())
            self._queueCallback(addon, "update")
        dlg.Destroy()
    
    
    def updateAvailable(self):
        """ Returns the Update Available indicator"""
        tracer.log(WurmCommon.DEBUG5, "Addon - updateAvailable")
        
        localv  = self.localversion
        onlinev = self.onlineversion
        
        # Convert the version numbers if required
        if isinstance(localv, str):
            try:
                if "." in localv:
                    major, minor = localv.split('.')
                    minor        = '%04d' % int(minor)
                    localv       = '%s.%s' % (major, minor)
                    localv       = Decimal(localv)
                else:
                    localv = int(localv)
            except Exception, details:
                logger.exception("Can't parse local version '%s' for addon %s" % (localv, self.localname))
                localv = -4
        
        if isinstance(onlinev, str):
            try:
                if "." in onlinev:
                    major, minor = onlinev.split('.')
                    minor        = '%04d' % int(minor)
                    onlinev      = '%s.%s' % (major, minor)
                    onlinev      = Decimal(onlinev)
                else:
                    onlinev = int(onlinev)
            except Exception, details:
                logger.exception("Can't parse online version '%s' for addon %s" % (onlinev, self.localname))
                onlinev = -4
        
        if localv >= 0 and onlinev >= 0:
            return localv < onlinev, onlinev - localv
        else:
            return False, None
    
    
    def updateMod(self):
        """ Updates the local Addon to the newest online version """
        tracer.debug("Addon - updateMod: %s" % self.localname)
        
        if self.siteid == "":
            msg = "Site ID for %s not set" % self.localname
            WurmCommon.outError(msg)
            raise Exception, msg
        
        if Decimal(self.onlineversion) < 0:
            self.onlineversion = self.getOnlineModVersion()
            if Decimal(self.onlineversion) < 0: # Site down?
                raise Exception, "Unable to get Online version: %d for %s" % (self.onlineversion, self.localname)
        
        # Check to see if only the Embedded Libraries had changed before we update the Addon
        updateava, diff = self.updateAvailable()
        if updateava and diff != 0 and diff < 1:
            self.wasembedonly = True
        else:
            self.wasembedonly = False
        
        WurmCommon.outDebug("Updating %(lname)s from %(lver)s to %(over)s" % {'lname': self.localname, 'lver': self.localversion, 'over': self.onlineversion})
        
        try:
            localfile = self.downloadMod()
            WurmUnpack.WoWInstallAddon(localfile, self.localname)
            self.setLocalModVersion(self.onlineversion)
            self.updated = True
            self.clreport = False
            WurmCommon.outMessage(_("%(lname)s is updated to %(lver)s") % {'lname': self.localname, 'lver': self.localversion})
        except Exception, details:
            logger.exception("Error, Update of %s failed!: %s" % (self.localname, str(details)))
            return False # was "raise", but that made more problems down the line, and strange UI behaviour
            # raise
        
        # If the addon was previously flagged as missing remove the flag
        if WurmCommon.addonlist.getFlag(self.localname, "missing"):
            WurmCommon.outDebug("uM, Removing \"missing\" flag for %s" % (self.localname))
            WurmCommon.addonlist.delFlag(self.localname, "missing")
            if "missing" in self.specialflags:
                del self.specialflags["missing"]
        
        # If the addon was previously flagged for installation remove the flag
        if WurmCommon.addonlist.getFlag(self.localname, 'install'):
            WurmCommon.outDebug("uM, Removing \"install\" flag for %s" % (self.localname))
            WurmCommon.addonlist.delFlag(self.localname, 'install')
            if 'install' in self.specialflags:
                del self.specialflags['install']
        
        # Update the Addon's TOC infomation
        refreshSingleAddon(self.localname, toconly=True)
        
        return True
    
    
    def updateModFromFile(self, filename):
        """ Takes the given archive file name, and installs it as the given version (or latest seen online if version isn't specified) """
        tracer.debug("Addon - updateModFromFile: %s, %s" % (self.localname, filename))
        
        if Decimal(self.onlineversion) < 0:
            self.onlineversion = self.getOnlineModVersion()
            if Decimal(self.onlineversion) < 0: # Site down?
                raise Exception, "Unable to get Online version: %d for %s" % (self.onlineversion, self.localname)
        
        try:
            WurmUnpack.WoWInstallAddon(filename, self.localname)
            self.setLocalModVersion(self.onlineversion)
            self.updated = True
            self.clreport = False
            WurmCommon.outMessage((_("%(lname)s is updated to %(lver)s") % {'lname': self.localname, 'lver': self.localversion}) + (_(" from %(filename)s") % {'filename':filename}))
            # if required remove downloaded file when installed successfully
            if int(WurmCommon.getGlobalSetting(":CleanDownload")):
                os.remove(filename)
        except Exception, details:
            logger.exception("Error, File-based Update of %s failed!: %s" % (self.localname, str(details)))
            return False # was "raise", but that made more problems down the line, and strange UI behaviour
            # raise
        
        # If the addon was previously flagged as missing remove the flag
        if WurmCommon.addonlist.getFlag(self.localname, "missing"):
            WurmCommon.outDebug("uM, Removing \"missing\" flag for %s" % (self.localname))
            WurmCommon.addonlist.delFlag(self.localname, "missing")
            if "missing" in self.specialflags:
                del self.specialflags["missing"]
        
        # If the addon was previously flagged for installation remove the flag
        if WurmCommon.addonlist.getFlag(self.localname, 'install'):
            WurmCommon.outDebug("uM, Removing \"install\" flag for %s" % (self.localname))
            WurmCommon.addonlist.delFlag(self.localname, 'install')
            if 'install' in self.specialflags:
                del self.specialflags['install']
        
        # Update the Addon's TOC infomation
        refreshSingleAddon(self.localname, toconly=True)
        
        return True
    


class AuctioneerAddon(Addon):
    def __init__(self, localname, siteid, baseurl="http://auctioneeraddon.com/dl/", flags={}):
        """"""
        tracer.debug("AuctioneerAddon - __init__: %s" % localname)
        
        Addon.__init__(self, localname, siteid, baseurl=baseurl, flags=flags)
        
        self.addontype = "Auctioneer"
        self.dlURLprefix = "http://mirror.auctioneeraddon.com/dl/"
        self.re = "auct_version2"
    
    
    def _getRealDlURL(self):
        """"""
        tracer.debug("AuctioneerAddon - _getRealDlURL")
        
        return self.dlURLprefix + self.dlURL
    
    
    def getAddonURL(self):
        """"""
        tracer.debug("AuctioneerAddon - getAddonURL")
        
        return self.baseurl
    
    
    def getOnlineModVersion(self):
        """"""
        tracer.debug("AuctioneerAddon - getOnlineModVersion")
        
        # download the addon's webpage
        htm = self.downloadPage(self.getAddonURL())
        if type(htm) is int:
            return htm
        
        version_re = WurmCommon.siteregexps[self.re] % (self.siteid)
        verdata = re.compile(version_re, re.S).findall(htm)
        
        if len(verdata) == 0:
            WurmCommon.outWarning(_("Could not find %(addon)s update date on page - is site ID correct?") % {'addon': self.localname})
            return -1
        
        try: # 'Stubby/stubby-3.8.0.zip', 'stubby-3.8.0.zip', '2006', '09', '02'
            
            (place, url, filename, year, month, day) = verdata[0]
            
            version = int("%s%s%s" % (year, month, day)) # hours/minutes/ampm aren't used, to keep length down
            self.dlURL = ("%s/%s" % (place, url))
        except Exception, details:
            WurmCommon.outWarning(_("Can't get a readable date for %(addon)s out of the page: %(dets)s (%(vdata)s)") % {'addon': self.localname, 'dets': str(details), 'vdata': str(verdata[0])})
        
        WurmCommon.outDebug("%s online version: %d" % (self.localname, version))
        return version
    


class CapnBryAddon(Addon):
    def __init__(self, localname, siteid, baseurl="http://capnbry.net/wow/", flags={}):
        """"""
        tracer.debug("CapnBryAddon - __init__: %s" % localname)
        
        Addon.__init__(self, localname, siteid, baseurl=baseurl, flags=flags)
        
        self.addontype = "CapnBry"
    
    
    def getAddonURL(self):
        """"""
        tracer.debug("CapnBryAddon - getAddonURL")
        
        return self.baseurl
    
    
    def getOnlineModVersion(self):
        """"""
        tracer.debug("CapnBryAddon - getOnlineModVersion")
        
        dlurl = "http://capnbry.net/wow/downloads/"
        # download the addon's webpage
        htm = self.downloadPage(dlurl + "%s.ver" % (self.siteid))
        if type(htm) is int:
            return htm
        
        version = -4
        try: # htm should now contain a number as a string
            verno = htm
            version = int("%s" % verno)
            self.dlURL = dlurl + "%s-%d.zip" % (self.siteid, version)
        except Exception, details:
            WurmCommon.outWarning(_("Can't get a readable date for %(addon)s out of the page: %(dets)s (%(vdata)s)") % {'addon': self.localname, 'dets': str(details), 'vdata': str(verdata[0])})
        
        WurmCommon.outDebug("%s online version: %d" % (self.localname, version))
        return version
    


class CosmosAddon(Addon):
    def __init__(self, localname, siteid, baseurl="http://www.cosmosui.org/addons.php", flags={}):
        """"""
        tracer.debug("CosmosAddon - __init__: %s" % localname)
        
        Addon.__init__(self, localname, siteid, baseurl=baseurl, flags=flags)
        
        self.addontype = "Cosmos"
    
    
    def getAddonURL(self):
        """"""
        tracer.debug("CosmosAddon - getAddonURL")
        
        return "http://www.wowwiki.com/%s" % (self.siteid)
    
    
    def getLocalModVersion(self):
        """ Override standard check to handle change from YYYYMMDD to revision """
        tracer.debug("CosmosAddon - getLocalModVersion")
        
        ver = Addon.getLocalModVersion(self)
        self.localversion = ver
        try:
            ver = int(ver)
            if ver > 20040000: # most likely a date, not a revision
                WurmCommon.outMessage(_("CosmosUI version format changed, setting %(addon)s to version 0 to ensure correct update") % {'addon': self.localname})
                ver = 0
                self.setLocalModVersion(0)
        except ValueError:
            pass
        return ver
    
    
    def getOnlineModVersion(self):
        """"""
        tracer.debug("CosmosAddon - getOnlineModVersion")
        
        # download the addon's webpage
        htm = self.downloadPage(self.baseurl)
        if type(htm) is int:
            return htm
        
        version_re = WurmCommon.siteregexps["cosmos_version2"] % (self.siteid)
        verdata = re.compile(version_re, re.S).findall(htm)
        
        if len(verdata) == 0:
            WurmCommon.outWarning(_("Could not find %(addon)s update date on page - is site ID correct?") % {'addon': self.localname})
            return -1
        
        try: # '<addon>.zip', 'revision', 'MM', 'DD', 'YYYY', 'Yesterday', 'Today' (either MMDDYYYY, "Yesterday" or "Today" is set)
            # WUU < .558 used the YYYYMMDD as version number
            # Got to handle upgrading from YYYYMMDD to revision
            (filename, revision, month, day, year, yesterday, today) = verdata[0]
            version = int(revision)
            
            self.dlURL = "http://www.cosmosui.org/download.php?t=addons&f=%s" % (filename)
        except Exception, details:
            WurmCommon.outWarning(_("Can't get a readable date for %(addon)s out of the page: %(dets)s (%(vdata)s)") % {'addon': self.localname, 'dets': str(details), 'vdata': str(verdata[0])})
        
        WurmCommon.outDebug("%s online version: %d" % (self.localname, version))
        return version
    


class CTModAddon(Addon):
    def __init__(self, localname, siteid, baseurl="http://ctmod.net/downloads/", flags={}):
        """"""
        tracer.debug("CTModAddon - __init__: %s" % localname)
        
        Addon.__init__(self, localname, siteid, baseurl=baseurl, flags=flags)
        
        self.addontype = "CTMod"
    
    
    def getAddonURL(self):
        """"""
        tracer.debug("CTModAddon - getAddonURL")
        
        return self.baseurl
    
    
    def getOnlineModVersion(self):
        """"""
        tracer.debug("CTModAddon - getOnlineModVersion")
        
        # download the addon's webpage
        htm = self.downloadPage(self.getAddonURL())
        if type(htm) is int:
            return htm
        
        version_re = WurmCommon.siteregexps["ctmod_version"] % (self.siteid)
        verdata = re.compile(version_re, re.S).findall(htm)
        
        if len(verdata) == 0:
            WurmCommon.outWarning(_("Could not find %(addon)s update date on page - is site ID correct?") % {'addon': self.localname})
            return -1
        
        try: # '/download/14/', '14', 'CT_UnitFrames', '2', '001'
            
            (path, code, name, majorversion, minorversion) = verdata[0]
            version = int("%d%05d" % (int(majorversion), int(minorversion)))
            self.dlURL = "http://ctmod.net/download/%s/" % (code)
        except Exception, details:
            WurmCommon.outWarning(_("Can't get a readable version for %(addon)s out of the page: %(dets)s (%(vdata)s)") % {'addon': self.localname, 'dets': str(details), 'vdata': str(verdata[0])})
        
        WurmCommon.outDebug("%s online version: %d" % (self.localname, version))
        return version
    


class CurseGamingAddon(Addon):
    def __init__(self, localname, siteid, baseurl="http://wow.curse.com/downloads/wow-addons/details/", flags={}):
        """"""
        tracer.debug("CurseGamingAddon - __init__: %s" % localname)
        
        Addon.__init__(self, localname, siteid, baseurl=baseurl, flags=flags)
        
        self.addontype = "CurseGaming"
    
    
    def _getRealDlURL(self):
        """"""
        tracer.debug("CurseGamingAddon - _getRealDlURL")
        
        if not self.dlURL:
            return None
        
        htm = ""
        if self._getAvailability():
            modurl = self.dlURL
            try:
                htm = WurmCommon.downloadPage(self._safeURL(modurl))
            except:
                self._setAvailability()
                return None
        
        realurl_re = WurmCommon.siteregexps["curse_realdl2"]
        urldata    = re.compile(realurl_re).findall(htm) # no re.S/re.DOTALL in this one
        
        if len(urldata) == 0:
            return None
        else:
            return "http://wow.curse.com/downloads/download.aspx?app=projectFiles&pi=%s&fi=%s" % (urldata[0])
    
    
    def downloadMod(self):
        """do nothing as cannot download from Curse any more - April 2009"""
        tracer.debug("CurseGamingAddon - downloadMod")
        
        raise Exception, "Downloading has been disabled for %s Addon" % self.localname
    
    
    def getAddonURL(self):
        """"""
        tracer.debug("CurseGamingAddon - getAddonURL")
        
        return "%s%s.aspx" % (self.baseurl, self.siteid)
    
    
    def getAddonDlURL(self):
        """ URL of download page for latest version """
        if not self.dlURL:
            if self.getOnlineModVersion() < 0:
                return None
        
        return self.dlURL
    
    
    def getOnlineModVersion(self):
        """"""
        tracer.debug("CurseGamingAddon - getOnlineModVersion")
        
        # download the addon's webpage
        htm = self.downloadPage(self.getAddonURL())
        if type(htm) is int:
            return htm
        
        # find version and download url
        dlversion_re = WurmCommon.siteregexps["curse_dlversion2"]
        verdata = re.compile(dlversion_re, re.S).findall(htm)
        
        if len(verdata) == 0:
            WurmCommon.outWarning(_("Could not find %(addon)s update date on page - is site ID correct?") % {'addon': self.localname})
            return -1
        
        (month, day, year, addonid1, addonid2) = verdata[0]
        if addonid1 == 'baggins' and year == '2008' and month == '9' and day == '29': # fixes "baggins" problem, really specific this time
#            WurmCommon.outWarning(_("Skipping dummy 'baggins' version"))
            (month, day, year, addonid1, addonid2) = verdata[1]
        
        self.dlURL = "%s%s/download/%s.aspx" % (self.baseurl, addonid1, addonid2)
        version = int("%04d%02d%02d" % (int(year), int(month), int(day)))
        
        WurmCommon.outDebug("%s online version: %d" % (self.localname, version))
        
        return version
    


class DBMAddon(Addon):
    """ DeadlyBossMods addon - two different site ids
    'core' are the core/bc mods
    'old' are the old-world mods
    can also use 'alpha' to get development version
    """
    def __init__(self, localname, siteid, baseurl="http://www.deadlybossmods.com/downloads.php", flags={}):
        """"""
        tracer.debug("DBMAddon - __init__: %s" % localname)
        
        Addon.__init__(self, localname, siteid, baseurl=baseurl, flags=flags)
        
        self.addontype = "DBM"
    
    
    def getAddonURL(self):
        """"""
        tracer.debug("DBMAddon - getAddonURL")
        
        return self.baseurl
    
    
    def getOnlineModVersion(self):
        """"""
        tracer.debug("DBMAddon - getOnlineModVersion")
        
        # download the addon's webpage
        htm = self.downloadPage(self.baseurl)
        if type(htm) is int:
            return htm
        
        version_re = WurmCommon.siteregexps["dbm_version2"]
        verdata = re.compile(version_re, re.S).findall(htm)
        
        if len(verdata) == 0:
            WurmCommon.outWarning(_("Could not find %(addon)s update date on page - is site ID correct?") % {'addon': self.localname})
            return -1
        
        vertarget = None
        
        for v in verdata: # verdata[x]=(downloadID(siteID), name, major, minor, revision)
            if self.siteid == v[0]:
                vertarget = v
                break
        
        if vertarget == None:
            WurmCommon.outWarning(_("Can't get a readable version for %(addon)s out of the page: %(siteid)s not found on page") % {'addon': self.localname, 'siteid': self.siteid})
            return -3
        
        version = -4
        try: # vertarget[x]=(downloadID(siteID), name, major, minor, revision)
            
            (downloadID, name, majorversion, minorversion, revision) = vertarget
            version = int("%d" % (int(revision)))
            self.dlURL = "http://www.deadlybossmods.com/download.php?id=%s" % (downloadID)
        except Exception, details:
            WurmCommon.outWarning(_("Can't get a readable version for %(addon)s out of the page: %(dets)s (%(vdata)s)") % {'addon': self.localname, 'dets': str(details), 'vdata': str(verdata[0])})
        
        WurmCommon.outDebug("%s online version: %d" % (self.localname, version))
        return version
    


class GathererAddon(AuctioneerAddon):
    def __init__(self, localname, siteid, baseurl="http://www.gathereraddon.com/dl/", flags={}):
        """"""
        tracer.debug("GathererAddon - __init__: %s" % localname)
        
        AuctioneerAddon.__init__(self, localname, siteid, baseurl=baseurl, flags=flags)
        
        self.addontype = "Gatherer"
        self.dlURLprefix = self.baseurl
        self.re = "gath_version"
    


class GenericGitAddon(Addon):
    """ Addon from any Git repository
    site id is "git-repository-url",(e.g. "git://some.url/rep/osi/Tory")
    """
    
    def __init__(self, localname, siteid, baseurl="git://", flags={}):
        """"""
        tracer.debug("GenericGitAddon - __init__: %s" % localname)
        
        Addon.__init__(self, localname, siteid, baseurl=baseurl, flags=flags)
        
        self.addontype = "GenericGit"
        self.dlURL = self.siteid
    
    
    def downloadMod(self):
        """ Clones the Repository, but does not install """
        tracer.debug("GenericGitAddon - downloadMod")
        
        if self.onlineversion < 0:
            self.onlineversion = self.getOnlineModVersion()
            if self.onlineversion < 0: # Site down?
                raise Exception, "Unable to get Online version: %d" % self.onlineversion
        
        if threading.currentThread().getName() != "MainThread":
            WurmCommon.wurmlock[self.addontype].acquire()
        
        try:
            try:
                WurmCommon.outProgressPercent(_("Cloning %(dlurl)s, please wait...") % {'dlurl': self.dlURL}, -1)
                
                modfilename = "%s-r%s.%s" % (self.localname, self.onlineversion, "git")
                localdir = os.path.join(WurmCommon.directories["temp"], modfilename)
                
                # remove the Git Clone directory if it exists
                if os.path.exists(localdir):
                    WurmCommon._deletePathRecursive(localdir, deleteSelf=True)
                # create the Git Clone directory
                os.makedirs(localdir)
                
                # append the Addon name to the localdir so that the WoWInstallAddon code works properly
                exportdir = os.path.join(localdir, self.localname)
                gitcmd = '%s clone --depth 1 --quiet "%s" "%s"' % (git, self.dlURL, exportdir)
                
                WurmCommon.outDebug("Git download clone command: %s" % (gitcmd))
                
                try:
                    retcode = call(gitcmd, shell=True)
                    if retcode < 0:
                        WurmCommon.outWarning(_("Clone from Git failed"))
                        WurmCommon.resetProgress()
                    else:
                        WurmCommon.outProgressPercent(_("Clone of %(dlurl)s complete!") % {'dlurl': self.dlURL}, 1)
                except OSError, e:
                    raise
                
                return localdir
            except Exception, details:
                logger.exception("Error: Cloning %s: %s" % (self.dlURL, str(details)))
                WurmCommon.resetProgress()
                raise
        finally:
            if threading.currentThread().getName() != "MainThread":
                WurmCommon.wurmlock[self.addontype].release()
    
    
    def getAddonURL(self):
        """ The Addon URL for Git Public Clone URL's cannot be determined (easily)"""
        tracer.debug("GenericGitAddon - getAddonURL")
        
        return ""
    
    
    def getOnlineModVersion(self):
        """ This will git clone the repo using --depth 1 and --mirror to make it as small as possible """
        tracer.debug("GenericGitAddon - getOnlineModVersion")
        
        if self.siteid == "" or self.siteid[:4] == "XXXX": # XXXX is the default set in by WUU
            WurmCommon.outError("SiteID for %s not set" % (self.localname))
            return -1
        
        if  self.siteid[:6] != "git://":
            WurmCommon.outError("SiteID needs to be on the format 'git://some.url/rep/osi/Tory'")
            return -1
        
        if not git:
            WurmCommon.outError("Git client not installed")
            return -1
        
        if threading.currentThread().getName() != "MainThread":
            WurmCommon.wurmlock[self.addontype].acquire()
        
        try:
            try:
                modfilename = "%s-r%s.%s" % (self.localname, 7654321, "git")
                localdir = os.path.join(WurmCommon.directories["temp"], modfilename)
                
                # remove the Git Clone directory if it exists
                if os.path.exists(localdir):
                    WurmCommon._deletePathRecursive(localdir, deleteSelf=True)
                # create the Git Clone directory
                os.makedirs(localdir)
                # get the smallest clone possible
                gitcmd = '%s clone --depth 1 --bare --quiet "%s" "%s"' % (git, self.dlURL, localdir)
                WurmCommon.outDebug("Git version clone command: %s" % (gitcmd))
                retcode = call(gitcmd, shell=True)
                if retcode < 0:
                    WurmCommon.outWarning(_("Unable to get Git version"))
                    return -1
                
                # now get the date
                gitcmd = 'cd %s && %s log -n 1' % (localdir, git)
                gitoutput = Popen(gitcmd, shell=True, stdout=PIPE).stdout.read().strip()
                
                WurmCommon.outDebug("gitoutput :[%s]" % gitoutput)
                
                # Date:   Sun Dec 21 16:04:52 2008 -0700
                date_re = 'Date:\s*.*\s(.*)\s(\d{1,2})\s.*\s(\d{4})\s'
                datedata = re.compile(date_re).findall(gitoutput)
                
                WurmCommon.outDebug("datedata :[%s]" % datedata)
                
                (month, day, year) = datedata[0]
                # convert month string into a number
                try:
                    if isinstance(month, str):
                        for fullmonth in self.months:
                            if month == fullmonth[:len(month)]:
                                month = "%02d" % (self.months.index(fullmonth) + 1)
                                break
                except Exception, details:
                    WurmCommon.outError("GenericGitAddon version - Month Error: %s" % (str(details)))
                    return -1
            
            except Exception, details:
                raise
        finally:
            if threading.currentThread().getName() != "MainThread":
                WurmCommon.wurmlock[self.addontype].release()
                
        version = int("%04d%02d%02d" % (int(year), int(month), int(day)))
        WurmCommon.outDebug("%s online version: %d" % (self.localname, version))
        
        return version
    


class GoogleCodeAddon(Addon):
    def __init__(self, localname, siteid, baseurl="http://code.google.com/p/", flags={}):
        """"""
        tracer.debug("GoogleCodeAddon - __init__: %s" % localname)
        
        Addon.__init__(self, localname, siteid, baseurl=baseurl, flags=flags)
        
        self.addontype = "GoogleCode"
        self.fname     = WurmCommon.addonlist.getFname(localname)
    
    
    def getAddonURL(self):
        """"""
        tracer.debug("GoogleCodeAddon - getAddonURL")
        
        return self.baseurl + self.siteid + "/downloads/list"
    
    
    def getOnlineModVersion(self):
        """"""
        tracer.debug("GoogleCodeAddon - getOnlineModVersion")
        
        # download the addon's webpage
        htm = self.downloadPage(self.getAddonURL())
        if type(htm) is int:
            return htm
        
        version_re = WurmCommon.siteregexps["googlecode_version"] % (self.siteid, self.fname)
        verdata = re.compile(version_re, re.S).findall(htm)
        
        if len(verdata) == 0:
            WurmCommon.outWarning(_("Could not find %(addon)s info on page - is site ID correct?") % {'addon': self.localname})
            return -1
        
        try: # 'tekKompare-2.0.3.294.zip', '2.0.3.294'
            
            (dlfname, verno, self.realDlExt) = verdata[0]
            version = self._versionFromText(verno)
            self.dlURL = "http://" + self.siteid + ".googlecode.com/files/" + dlfname
        except Exception, details:
            WurmCommon.outWarning(_("Can't get a readable date for %(addon)s out of the page: %(dets)s (%(vdata)s)") % {'addon': self.localname, 'dets': str(details), 'vdata': str(verdata[0])})
            return 0
            
        WurmCommon.outDebug("%s online version: %d" % (self.localname, version))
        return version
    


class GoogleCodeSVNAddon(Addon):
    """ Addon from the GoogleCode SVN
    site id is "username|addon", and will be fetched from the trunk unless there's a slash in the name
    (e.g. "username|branches/Test/AnyAddon")
    """
    
    def __init__(self, localname, siteid, baseurl="http://%s.googlecode.com/svn/", flags={}):
        """"""
        tracer.debug("GoogleCodeSVNAddon - __init__: %s" % localname)
        
        Addon.__init__(self, localname, siteid, baseurl=baseurl, flags=flags)
        
        self.addontype = "GoogleCodeSVN"
    
    
    def downloadMod(self):
        """ Exports the Addon from the Repository, but does not install """
        tracer.debug("GoogleCodeSVNAddon - downloadMod")
        
        if self.onlineversion < 0:
            self.onlineversion = self.getOnlineModVersion()
            if self.onlineversion < 0: # Site down?
                raise Exception, "Unable to get Online version: %d" % self.onlineversion
        
        if threading.currentThread().getName() != "MainThread":
            WurmCommon.wurmlock[self.addontype].acquire()
        
        try:
            try:
                modfilename = "%s-r%s.%s" % (self.localname, self.onlineversion, "svn")
                localdir    = os.path.join(WurmCommon.directories["temp"], modfilename)
                
                # remove the SVN Export directory if it exists
                if os.path.exists(localdir):
                    WurmCommon._deletePathRecursive(localdir, deleteSelf=True)
                
                # create the SVN Export directory
                os.makedirs(localdir)
                
                # append the Addon name to the localdir so that the WoWInstallAddon code works properly
                exportdir = os.path.join(localdir, self.localname)
                svncmd    = '%s export -r %d --force "%s" "%s" 2>&1' % (svn, self.onlineversion, self.dlURL, exportdir)
                WurmCommon.outStatus(_("Exporting %(dlurl)s") % {'dlurl': self.dlURL})
                WurmCommon.outDebug("SVN Export command: %s" % (svncmd))
                svnfile = os.popen(svncmd)
                svnoutput = ""
                while 1:
                    line = svnfile.readline()
                    if not line: break
                    WurmCommon.outProgressPercent(_("Exporting %(lname)s, please wait...") % {'lname': self.localname}, -1)
                    svnoutput += line.strip()
                
                export_re = WurmCommon.siteregexps["svn_export"]
                expdata   = re.compile(export_re, re.S).findall(svnoutput)
                
                if expdata and Decimal(expdata[0]) == self.onlineversion:
                    WurmCommon.outDebug("%(dlurl)s downloaded to %(ldir)s" % {'dlurl': self.dlURL, 'ldir': localdir})
                    WurmCommon.outProgressPercent(_("Export of %(lname)s complete!") % {'lname': self.localname}, 1)
                else:
                    WurmCommon.outWarning(_("Export from SVN failed"))
                    WurmCommon.resetProgress()
                    return False
                
                return localdir
            except Exception, details:
                logger.exception("Error: Exporting %s: %s" % (self.dlURL, str(details)))
                raise
        finally:
            if threading.currentThread().getName() != "MainThread":
                WurmCommon.wurmlock[self.addontype].release()
    
    
    def getAddonURL(self):
        """"""
        tracer.debug("GoogleCodeSVNAddon - getAddonURL")
        
        return "" # TODO: Fix this ;)
    
    
    def getOnlineModVersion(self):
        """"""
        tracer.debug("GoogleCodeSVNAddon - getOnlineModVersion")
        
        if self.siteid == "" or self.siteid[:4] == "XXXX": # XXXX is the default set in by WUU
            WurmCommon.outError("SiteID for %s not set" % (self.localname))
            return -1
        
        if  self.siteid.count("|") != 1:
            WurmCommon.outError("SiteID needs to be on the format 'username|path'")
            return -1
        
        if not svn:
            WurmCommon.outError("SVN client not installed")
            return -1
        
        if threading.currentThread().getName() != "MainThread":
            WurmCommon.wurmlock[self.addontype].acquire()
        
        (username, path) = self.siteid.split("|")
        
        if "/" not in path:
            path = "trunk/" + path # shortcut for trunk addons
        
        self.dlURL = self._safeURL((self.baseurl % (username)) + path)
        svncmd     = '%s info "%s" 2>&1' % (svn, self.dlURL)
        svnoutput  = os.popen(svncmd).read().strip()
        
        if threading.currentThread().getName() != "MainThread":
            WurmCommon.wurmlock[self.addontype].release()
        
        version_re = WurmCommon.siteregexps["svn_version"]
        verdata    = re.compile(version_re, re.S).findall(svnoutput)
        
        if len(verdata) == 0:
            WurmCommon.outWarning(_("Could not find %(addon)s info in SVN - is site ID correct?") % {'addon': self.localname})
            return -1
        
        verno   = verdata[0]
        version = int("%s" % verno)
        WurmCommon.outDebug("%s online version: %d" % (self.localname, version))
        
        return version
    


class WoWAceAddon(Addon):
    def __init__(self, localname, siteid, baseurl="http://war.curseforge.com", flags={}):
        """"""
        tracer.debug("WoWAceAddon - __init__: %s" % localname)
        
        Addon.__init__(self, localname, siteid, baseurl=baseurl, flags=flags)
        
        self.addontype = "WoWAce"
    
    
    def _getRealDlURL(self):
        """"""
        tracer.debug("WoWAceAddon - _getRealDlURL")
        
        return realDlURL
    
    
    def getAddonURL(self):
        """"""
        tracer.log(WurmCommon.DEBUG5, "WoWAceAddon - getAddonURL")
        
        return "%s/projects/%s" % (self.baseurl, self.siteid)
    
    
    def getAddonDlURL(self):
        """ URL of download page for latest version """
        tracer.debug("WoWAceAddon - getAddonDlURL")
        
        if not self.dlURL:
            if self.getOnlineModVersion() < 0:
                return None
        
        return self.dlURL
    
    
    def getAddonFilesDlURL(self):
        """ URL of download page for all versions """
        tracer.debug("WoWAceAddon - getAddonFilesDlURL")
        
        return "%s/projects/%s/files" % (self.baseurl, self.siteid)
    
    
    def getOnlineModVersion(self):
        """"""
        tracer.debug("WoWAceAddon - getOnlineModVersion")
        
        # download the addon's webpage
        htm = self.downloadPage(self.getAddonURL())
        if type(htm) is int:
            return htm
        
        # find download info and date
        dlver_re = WurmCommon.siteregexps["wowace_dlversion"] % self.siteid
        dldata = re.compile(dlver_re).findall(htm)
        
        date_re = WurmCommon.siteregexps["wowace_version"]
        datedata = re.compile(date_re).findall(htm)
        
        # WurmCommon.outDebug("download: %s" % dldata)
        # WurmCommon.outDebug("date: %s" % datedata)
        
        if len(dldata) == 0:
            WurmCommon.outWarning(_("Could not find %(addon)s download info on page - is site ID correct?") % {'addon': self.localname})
            return -1
        
        self.dlURL = "%s/projects/%s/files/%s" % (self.baseurl, self.siteid, dldata[0])
        
        if len(datedata) == 0:
            WurmCommon.outWarning(_("Could not find %(addon)s update date on page - is site ID correct?") % {'addon': self.localname})
            return -1
        
        adate = gmtime(float(datedata[0]))
        version = int("%04d%02d%02d" % (adate.tm_year, adate.tm_mon, adate.tm_mday))
        
        WurmCommon.outDebug("%s online version: %s" % (self.localname, version))
        
        return version
    


class WoWAceCloneAddon(Addon):
    def __init__(self, localname, siteid, baseurl="http://www.wowace.com", flags={}):
        """"""
        tracer.debug("WoWAceCloneAddon - __init__: %s" % localname)
        
        Addon.__init__(self, localname, siteid, baseurl=baseurl, flags=flags)
        
        # Define additional configuration parameters
        self.addontype = "WoWAceClone"
    
    
    def getAddonURL(self):
        """"""
        tracer.debug("WoWAceCloneAddon - getAddonURL")
        
        return "%s/projects/%s/repositories/%s" % (self.baseurl, self.localname, self.siteid)
    
    
    def getAddonDlURL(self):
        """ URL of download page for latest version """
        tracer.debug("WoWAceCloneAddon - getAddonDlURL")
        
        return self.getAddonFilesDlURL()
    
    
    def getAddonFilesDlURL(self):
        """ URL of download page for all versions """
        tracer.debug("WoWAceCloneAddon - getAddonFilesDlURL")
        
        return "%s/projects/%s/repositories/%s/files" % (self.baseurl, self.localname, self.siteid)
    
    
    def getOnlineModVersion(self):
        """"""
        tracer.debug("WoWAceCloneAddon - getOnlineModVersion")
        
        # download the clones files webpage
        htm = self.downloadPage(self.getAddonFilesDlURL())
        if type(htm) is int:
            return htm
        
        # find download info and date
        dlver_re = WurmCommon.siteregexps["wowaceclone_dlversion"] % (self.localname, self.siteid)
        dldata = re.compile(dlver_re, re.I).findall(htm) # case insensitive match
        
        date_re = WurmCommon.siteregexps["wowaceclone_version"]
        datedata = re.compile(date_re).findall(htm)
        
        # WurmCommon.outDebug("download: %s" % dldata)
        # WurmCommon.outDebug("date: %s" % datedata)
        
        if len(dldata) == 0:
            WurmCommon.outWarning(_("Could not find %(addon)s download info on page - is site ID correct?") % {'addon': self.localname})
            return -1
        
        self.dlURL = "%s/projects/%s/repositories/%s/files/%s" % (self.baseurl, self.localname, self.siteid, dldata[0])
        
        if len(datedata) == 0:
            WurmCommon.outWarning(_("Could not find %(addon)s update date on page - is site ID correct?") % {'addon': self.localname})
            return -1
        
        adate = gmtime(float(datedata[0]))
        version = int("%04d%02d%02d" % (adate.tm_year, adate.tm_mon, adate.tm_mday))
        
        WurmCommon.outDebug("%s online version: %s" % (self.localname, version))
        
        return version
    


class WoWIAddon(Addon):
    def __init__(self, localname, siteid, baseurl="http://www.wowinterface.com/downloads/", flags={}):
        """"""
        tracer.debug("WoWIAddon - __init__: %s" % localname)
        
        Addon.__init__(self, localname, siteid, baseurl=baseurl, flags=flags)
        
        self.addontype = "WoWI"
    
    
    def _getRealDlURL(self):
        """"""
        tracer.debug("WoWIAddon - _getRealDlURL")
        
        # only use the numeric part of the SiteID
        sitedata = re.compile("(\d+)").findall(self.siteid)
        return "http://fs.wowinterface.com/patcher.php?id=%s" % sitedata[0]
        # return '%sdownload%s' % (self.baseurl, self.siteid)
    
    
    def getAddonURL(self):
        """"""
        tracer.debug("WoWIAddon - getAddonURL")
        
        return self.baseurl + "info" + self.siteid + ".html"
    
    
    def getOnlineModVersion(self):
        """"""
        tracer.debug("WoWIAddon - getOnlineModVersion")
        
        # download the addon's webpage
        htm = self.downloadPage(self.getAddonURL(), length=40960) # only get 1st 40Kb
        if type(htm) is int:
            return htm
        
        version_re = WurmCommon.siteregexps["wowi_version"]
        verdata = re.compile(version_re, re.S).findall(htm)
        
        try:
            if len(verdata) == 0:
                WurmCommon.outWarning(_("Could not find %(addon)s update date on page - is site ID correct?") % {'addon': self.localname})
                return -1
                
            (month, day, year, hour, minute, ampm) = verdata[0]
            version = int("%s%s%s" % (year, month, day)) # hours/minutes/ampm aren't used, to keep length down
        except Exception, details:
            WurmCommon.outWarning(_("Can't get a readable date for %(addon)s out of the page: %(dets)s (%(vdata)s)") % {'addon': self.localname, 'dets': str(details), 'vdata': str(verdata[0])})
        
        WurmCommon.outDebug("%s online version: %d" % (self.localname, version))
        return version
    


class WoWUIAddon(Addon):
    def __init__(self, localname, siteid, baseurl="http://wowui.incgamers.com/", flags={}):
        """"""
        tracer.debug("WoWUIAddon - __init__: %s" % localname)
        
        Addon.__init__(self, localname, siteid, baseurl=baseurl, flags=flags)
        
        self.addontype = "WoWUI"
    
    
    def _getRealDlURL(self):
        """return nothing as unable to access WoWUI website anymore"""
        tracer.debug("WoWUIAddon - _getRealDlURL")
        
        return None
    
    
    def downloadMod(self):
        """do nothing as unable to access WoWUI website anymore"""
        tracer.debug("WoWUIAddon - downloadMod")
        
        raise Exception, "Downloading has been disabled for %s Addon" % self.localname
    
    
    def getAddonURL(self):
        """"""
        tracer.debug("WoWUIAddon - getAddonURL")
        
        return self.baseurl + "?p=mod&m=" + self.siteid
    
    
    def getAddonDlURL(self):
        """ URL of download page for latest version """
    
        return self.getAddonURL()
    
    
    def getOnlineModVersion(self):
        """"""
        tracer.debug("WoWUIAddon - getOnlineModVersion")
        
        # download the addon's webpage
        htm = self.downloadPage(self.getAddonURL(), length=10240) # only get 1st 10Kb
        if type(htm) is int:
            return htm
        
        version_re = WurmCommon.siteregexps["wowui_version"]
        verdata = re.compile(version_re, re.S).findall(htm)
        
        try:
            if len(verdata) == 0:
                WurmCommon.outWarning(_("Could not find %(addon)s update date on page - is site ID correct?") % {'addon': self.localname})
                return -1
                
            (day, month, year) = verdata[0]
            version = int("%s%s%s" % (year, month, day))
        except Exception, details:
            WurmCommon.outWarning(_("Can't get a readable date for %(addon)s out of the page: %(dets)s (%(vdata)s)") % {'addon': self.localname, 'dets': str(details), 'vdata': str(verdata[0])})
                
        WurmCommon.outDebug("%s online version: %d" % (self.localname, version))
        return version
    


class OtherSiteAddon(Addon):
    """ Addon from a specified URL with additional info to help identify version and file extension """
    def __init__(self, localname, siteid, flags={}):
        """"""
        tracer.debug("OtherSiteAddon - __init__: %s" % localname)
        
        Addon.__init__(self, localname, siteid, flags=flags)
        
        # Define additional configuration parameters
        self.configurable = {"00Instructions": ("Instructions", _("Please refer to %(wuuki)sOtherSites") % {'wuuki': WurmCommon.wuuki}, None),
                             "10AddonPage": ("AddonPage", _("Addon Information Page"), ""),
                             "20VerRegExp": ("VerRegExp", _("Addon Version regexp"), ""),
                             "21VerIsDate": ("VerIsDate", _("Version info is a Date"), False),
                             "22DateFormat": ("DateFormat", _("Date Format"), "Month Day Year"),
                             "23VerIsLast": ("VerIsLast", _("Use Last Version string"), False),
                             "30ExtnRegExp": ("ExtnRegExp", _("Addon Extension regexp"), ""),
                             "31ExtnIsName": ("ExtnIsName", _("Use Extension as Name"), False),
                             "32DLNameExp": ("DLNameExp", _("Download Name Expression"), "%(site)s%(name)s.%(ext)s")}
        
        self.addontype = "OtherSite"
        self.verinfo   = 0
        self.fname     = WurmCommon.addonlist.getFname(localname)
    
    
    def _getRealDlURL(self):
        """"""
        tracer.debug("OtherSiteAddon - _getRealDlURL")
        
        return self._getFlag("DLNameExp", "") % ({'site': self.siteid % ({'name': self.localname, 'fname': self.fname}), 'name': self.localname, 'lcname': self.localname.lower(), 'fname': self.fname, 'ver': self.verinfo, 'ext': self.realDlExt, 'dlname': self.realDlName})
    
    
    def getOnlineModVersion(self):
        """"""
        tracer.debug("OtherSiteAddon - getOnlineModVersion")
        
        # download the addon's webpage
        htm = self.downloadPage(self.getAddonURL())
        if type(htm) is int:
            return htm
        
        # Extract the addon extension
        if self._getFlag("ExtnIsName"):
            extnorname = "name"
        else:
            extnorname = "extension"
        extension_re = self._getFlag("ExtnRegExp", "") % ({'name': self.localname, 'fname': self.fname})
        extndata = re.compile(extension_re, re.I).findall(htm)
        if len(extndata) == 0:
            WurmCommon.outWarning(_("Could not find %(addon)s %(eorn)s on page - is the Regular Expression correct?") % {'addon': self.localname, 'eorn': extnorname})
            return -1
        
        self.realDlName = ""
        self.realDlExt = ""
        if self._getFlag("ExtnIsName"):
            self.realDlName = extndata[0]
            WurmCommon.outDebug("%(addon)s Name: %(extn)s" % {'addon': self.localname, 'extn': self.realDlName})
            self.realDlExt = self.realDlName[-3:]
        else:
            self.realDlExt = extndata[0]
            WurmCommon.outDebug("%(addon)s Extension: %(extn)s" % {'addon': self.localname, 'extn': self.realDlExt})
        
#>>>>>>># Start of code ONLY used by the ChildAddon class
        # If the Version RegExp is 'Ignore' then set the value to 20991231 to allow the Addon to be always downloaded
        if self.addontype == "Child" and 'Ignore' in self._getFlag("VerRegExp"):
            WurmCommon.outDebug("Addon Download URL is: %(dlurl)s" % {'dlurl': self._getRealDlURL()})
            return int('20991231')
#>>>>>>># End of code ONLY used by the ChildAddon class
        
        # Extract the addon version
        version_re = self._getFlag("VerRegExp", "") % ({'name': self.localname, 'fname': self.fname, 'ext': self.realDlExt})
        verdata = re.compile(version_re, re.I).findall(htm)
        if len(verdata) == 0:
            WurmCommon.outWarning(_("Could not find %(addon)s version info on page - is the Regular Expression correct?") % {'addon': self.localname})
            return -1
        
        # Save the version info
        self.verinfo = verdata[0]
        
        # If the version info is a date then process it as such
        if self._getFlag("VerIsDate"):
            # Use the User supplied Date Format string
            dateseq = self._getFlag("DateFormat", "Month Day Year").split()
            
            day = month = year = hour = minute = ''
            seq = 0
            
            for d in dateseq:
                try:
                    if d == 'Day':
                        day = "%02d" % (int(self.verinfo[seq]))
                    elif d == 'Month':
                        month = self.verinfo[seq]
                        try:
                            if isinstance(month, str):
                                for fullmonth in self.months:
                                    if month == fullmonth[:len(month)]:
                                        month = "%02d" % (self.months.index(fullmonth) + 1)
                                        break
                        except Exception, details:
                            WurmCommon.outError("Version Date Month Error: %s" % (str(details)))
                            return -1
                    elif d == 'Year':
                        year = self.verinfo[seq]
                        if len(year) <= 2:
                            year = "20%02d" % (int(year))
                        else:
                            year = "%04d" % (int(year))
                    elif d == 'Hour':
                        hour = "%02d" % (int(self.verinfo[seq]))
                    elif d == 'Minute':
                        minute = "%02d" % (int(self.verinfo[seq]))
                except Exception, details:
                    WurmCommon.outError("Version Date Error: %s" % (str(details)))
                    return -1
                # Increment the counter
                seq += 1
            
            version = int('%s%s%s%s%s' % (year, month, day, hour, minute))
            WurmCommon.outDebug("Date Value: %s" % (version))
        else:
            if self._getFlag("VerIsLast"):
                self.verinfo = verdata[-1]
            # Convert into a version number from a string
            version = self._versionFromText(self.verinfo)
        
        WurmCommon.outDebug("%(lname)s Version: %(ver)s" % {'lname': self.localname, 'ver': self.verinfo})
        
        self.dlURL = self._getRealDlURL()
        
        WurmCommon.outDebug("Addon Download URL is: %(dlurl)s" % {'dlurl': self._getRealDlURL()})
        
        return version
    
    
    def getAddonURL(self):
        """"""
        tracer.debug("OtherSiteAddon - getAddonURL")
        
        return self.siteid % ({'name': self.localname, 'fname': self.fname}) + self._getFlag("AddonPage", "")
    


class ChildAddon(OtherSiteAddon):
    """This handles Addons which are 'children' of others i.e. they live in the same directory but are not Addons in their own right"""
    def __init__(self, localname, siteid, flags={}):
        """"""
        tracer.debug("ChildAddon - __init__: %s" % localname)
        
        OtherSiteAddon.__init__(self, localname, siteid, flags=flags)
        
        # Define additional configuration parameters
        self.configurable.update({"05Parent": ("Parent", _("Parent Addon"), "")})
        self.addontype = "Child"
    
    
    def getLocalModVersion(self):
        """ Gets the version from the local WUU version file """
        tracer.log(WurmCommon.DEBUG5, "ChildAddon - getLocalModVersion")
        
        if not self._getFlag("Parent"):
            return -2
        
        versionpath = os.path.join(WurmCommon.directories["addons"], self._getFlag("Parent"))
        verfilepath = os.path.join(versionpath, self.versionfile)
        # Check to see if it exists, if not then try the old filename
        oldver = False
        if not os.path.isfile(verfilepath):
            verfilepath = os.path.join(versionpath, 'version.txt')
            oldver      = True
        
        try:
            version = open(verfilepath, "rt").read()
        except:
            return -2
        
        # If it was an old version then write the version info to the new file
        # and remove the old file
        if oldver:
            self.setLocalModVersion(version)
            os.remove(verfilepath)
            WurmCommon.outMessage(_("Converted %(addon)s's version.txt to %(verfile)s") % {'addon': self.localname, 'verfile': self.versionfile})
        
        # WurmCommon.outDebug("%s local version: %s" % (self.localname, version))
        
        return version
    
    
    def setLocalModVersion(self, newVersion):
        """ Updates the local WUU version file to the new version """
        tracer.debug("ChildAddon - setLocalModVersion")
        
        versionpath = os.path.join(WurmCommon.directories["addons"], self._getFlag("Parent"))
        verfilepath = os.path.join(versionpath, self.versionfile)
        try:
            open(verfilepath, "wt").write("%s" % (newVersion))
        except:
            return False
        
        self.localversion = newVersion
        return True
    
    
    def updateMod(self):
        """ Updates the Child Addon, in its parents' directory, to the newest online version """
        tracer.debug("ChildAddon - updateMod")
        
        if self.siteid == "":
            msg = "Site ID for %s not set" % self.localname
            WurmCommon.outError(msg)
            raise Exception, msg
        
        WurmCommon.outDebug("Updating %(lname)s from %(lver)s to %(over)s" % {'lname': self.localname, 'lver': self.localversion, 'over': self.onlineversion})
        
        try:
            localfile = self.downloadMod()
            # Replace the Addon name with its Parent name
            # This allows it to be installed in its Parent's directory
            WurmUnpack.WoWInstallAddon(localfile, self._getFlag("Parent"), isChild=True)
            self.setLocalModVersion(self.onlineversion)
            self.updated = True
            WurmCommon.outMessage(_("%(lname)s is updated to %(lver)s") % {'lname': self.localname, 'lver': self.localversion})
        except Exception, details:
            logger.exception("Error, Update of %s failed!: %s" % (self.localname, str(details)))
            raise
            # return False # was "raise", but that made more problems down the line, and strange UI behaviour
        
        # If the addon was previously flagged as missing remove the flag
        if WurmCommon.addonlist.getFlag(self.localname, "missing"):
            WurmCommon.outDebug("uM, Removing \"missing\" flag for %s" % (self.localname))
            WurmCommon.addonlist.delFlag(self.localname, "missing")
            if "missing" in self.specialflags:
                del self.specialflags["missing"]
        
        return True
    


class TOCFile:
    def __init__(self, addonname, specialflags):
        """"""
        tracer.log(WurmCommon.DEBUG3, "TOCFile - __init__: %s, %s" % (addonname, str(specialflags)))
        
        self.toc       = {}
        self.addonname = addonname
        self.isValid   = False
        
        # Ignore Blizzard's Addons, Child, Dummy, Ignore & Missing Addons & those about to be installed
        if self.addonname[:9] == "Blizzard_" or WurmCommon.addonlist.getAtype(addonname) in ["Child", "[Dummy]", "[Ignore]"] or (specialflags and ('missing' in specialflags or 'install' in specialflags)):
            return
        
        self.refresh()
    
    
    def _htmlColors(self, text):
        """ Returns the text with "Blizzard-colors" converted to HTML """
        tracer.log(WurmCommon.DEBUG5, "TOCFile - _htmlColors")
        
        btext = text
        while btext.lower().find("|c") != -1:
        # while btext.find("|c") != -1 or btext.find("|C") != -1:
            colourStart = btext.lower().find("|c")
            # colourStart = btext.find("|c")
            # if colourStart == -1:
            #     colourStart = btext.find("|C")
            color = btext[colourStart + 4:colourStart + 10]
            color = "<font color=\"#%s\">" % (color)
            btext = btext[:colourStart] + color + btext[colourStart + 10:] # jumps over the "|c########" part
            colourSep = btext.find("|", colourStart) # find next colour separator
            if colourSep != -1:
                if btext[colourSep + 1] == "r":
                    btext = btext[:colourSep]+"</font>"+btext[colourSep + 2:]
                elif btext[colourSep + 1].lower() == "c": # starts a new color tag directly
                # elif btext[colourSep + 1] == "C" or btext[colourSep + 1] == "c": # starts a new color tag directly
                    btext = btext[:colourSep]+"</font>"+btext[colourSep:] # retain the |C/|c
        
        return btext
    
    
    def _stripColors(self, text):
        """ Returns the text with "Blizzard-colors" removed """
        tracer.log(WurmCommon.DEBUG5, "TOCFile - _stripColors")
        
        # if field is empty return
        if text is None:
            return ""
        
        btext = text
        while btext.find("|c") != -1 or btext.find("|C") != -1:
            c = btext.find("|c")
            if c == -1:
                c = btext.find("|C")
            btext = btext[:c]+btext[c+10:] # jumps over the "|c########" part
            c     = btext.find("|")
            if c != -1:
                if btext[c+1] == "r":
                    btext = btext[:c]+btext[c+2:]
                elif btext[c+1] == "C" or btext[c+1] == "c": # usually this means a transition from one color to another
                    btext = btext[:c]+btext[c:] # retain the |C/|c
        
        return btext
    
    
    def getDependencies(self):
        """"""
        tracer.log(WurmCommon.DEBUG5, "TOCFile - getDependencies")
        
        return self.getListField("Dependencies")
    
    
    def getInterfaceVersion(self):
        """"""
        tracer.log(WurmCommon.DEBUG5, "TOCFile - getInterfaceVersion")
        
        if "Interface" in self.toc:
            try:
                return Decimal(self.toc["Interface"])
            except UnicodeEncodeError:
                return False
            except InvalidOperation:
                return False
        else:
            return False
    
    
    def getListField(self, field):
        """"""
        tracer.log(WurmCommon.DEBUG5, "TOCFile - getListField")
        
        if field not in self.toc:
            return ()
        
        f = self.toc[field].strip()
        return [c.strip() for c in f.split(",")]
    
    
    def getOptionalDeps(self):
        """"""
        tracer.log(WurmCommon.DEBUG5, "TOCFile - getOptionalDeps")
        
# Begin patch 1878041
        optDeps = self.getListField("OptionalDeps")
        xDeps = self.getListField("X-Embeds")
        
        d = {}
        for s in (optDeps , xDeps):
            for x in s:
                d[x] = 1
        
        l = d.keys()
        l.sort()
        d.clear()
        
        return l
        #return self.getListField("OptionalDeps")
# End patch 1878041
    
    
    def getTextField(self, field, html=False):
        """"""
        tracer.log(WurmCommon.DEBUG5, "TOCFile - getTextField")
        
        if field not in self.toc:
            return ""
        
        if html:
            return self._htmlColors(self.toc[field])
        else:
            return self._stripColors(self.toc[field])
    
    
    def refresh(self):
        """ Reloads the TOC file from disk """
        tracer.log(WurmCommon.DEBUG5, "TOCFile - refresh")
        
        filename = os.path.join(WurmCommon.directories["addons"], self.addonname, "%s.toc" % self.addonname)
        # check to see if TOC file exists
        if not os.path.isfile(filename):
            WurmCommon.outWarning("No TOC file for %s" % self.addonname)
            self.isValid = False
        else:
            tocCheck = self.readTOC(filename)
            if not tocCheck:
                WurmCommon.outError("Invalid TOC file for %s" % self.addonname)
                self.isValid = False
            else:
                tracer.log(WurmCommon.DEBUG3, "TOC file contents#1: %s" % str(self.toc))
                self.isValid = True
    
    
    def readTOC(self, tocfile):
        """"""
        tracer.log(WurmCommon.DEBUG5, "TOCFile - readTOC")
        
        try:
            toc = [line.rstrip() for line in open(tocfile, "rt")]
            WurmCommon.removeBOM(toc)
            for line in toc:
                try:
                    newline = unicode(line, 'ascii')
                except:
                    # logger.debug("String not ascii, trying utf-8")
                    try:
                        newline = unicode(line, 'utf-8')
                        # logger.debug("String utf-8: [%s]" % (newline))
                    except:
                        # logger.debug("String not utf-8, trying latin-1")
                        try:
                            newline = unicode(line, 'latin-1')
                            # logger.debug("String latin-1: [%s]" % (newline))
                        except:
                            logger.debug("String encoding unknown: [%s]" % (line))
                            continue
                
                r = newline
                if r[:2] == "##":
                    c = r.find(":")
                    if c != -1:
                        field = r[2:c].strip()
                        value = r[c+1:].strip()
                        if not field in self.toc: # only read first line, if there are multiple
                            self.toc[field] = value
                            # logger.debug("TOC: [%s, %s]" % (field, value))
            
            return True
        except Exception, details:
            logger.exception("Error reading TOC info from %s: %s" % (tocfile, str(details)))
            raise
    


class SimpleTOC(TOCFile):
    """ In-memory version of TOCFile, for dealing with addons that aren't installed yet """
    def __init__(self, addonname):
        """"""
        tracer.debug("SimpleTOC - __init__: %s" % addonname)
        
        self.toc       = {}
        self.addonname = addonname
        self.isValid   = True
    
    
    def refresh(self):
        """ No file on disk, so this is a no-op """
        tracer.log(WurmCommon.DEBUG5, "SimpleTOC - refresh")
        
        pass # do nothing here
    
    
    def setField(self, field, value):
        """ Setting a single field """
        tracer.log(WurmCommon.DEBUG5, "SimpleTOC - setField")
        
        self.toc[field] = value
    


class WurmURLParseException(Exception):
    """ Exception to raise for problems in identifying addon by URL """
    # TODO: Make behave like a real exception (no pydocs available right now :( )
    def __init__(self, site=None, message=None):
        """ Init Exception """
        tracer.debug("WurmURLParseException - __init__: %s, %s" % (site, message))
        
        if message==None and site!=None:
            self.message = "Could not parse %s URL, expected format: %s" % (site, ", ".join(installFromURLsupported[site]["format"]))
        elif message!=None and site==None:
            self.message = message
        else:
            self.message = "[%s] %s" % (site, message)
    


# addon type definitions - defined here after Class definitions
WurmCommon.addontypes = {
    "Auctioneer":       AuctioneerAddon,
    "CapnBry":          CapnBryAddon,
    "Cosmos":           CosmosAddon,
    "CTMod":            CTModAddon,
    "CurseGaming":      CurseGamingAddon,
    "DBM":              DBMAddon,
    "Gatherer":         GathererAddon,
    "GenericGit":       GenericGitAddon,
    "GoogleCode":       GoogleCodeAddon,
    "GoogleCodeSVN":    GoogleCodeSVNAddon,
    "WoWAce":           WoWAceAddon,
    "WoWAceClone":      WoWAceCloneAddon,
    "WoWI":             WoWIAddon,
    "WoWUI":            WoWUIAddon,
    "OtherSite":        OtherSiteAddon,
    "Child":            ChildAddon,
    "[Dummy]":          None,
    "[Ignore]":         None,
    "[Outdated]":       None,
    "[Related]":        None,
    "[Unknown]":        None,
}

def _downloadAndIdentify(addonobj, site, siteid):
    """ Downloads and identifies the addon described by the addon object supplied """
    tracer.debug("_downloadAndIdentify")
    
    downloaded = addonobj.downloadMod()
    
    if not downloaded:
        raise Exception, "Can't download - installation aborted"
    
    addonname = addonobj.localname
    
    # Correct the file extension
    (filename, extn) = WurmUnpack.CorrectExtension(downloaded)
    
    # Create the right type of Archive object
    try:
        if extn.lower() == "zip":
            addonarchive = WurmUnpack.ZipArchive(filename, addonname)
        elif extn.lower() == "rar" and os.name == 'nt':
            if WurmUnpack.SevenZip and WurmUnpack.SevenZip.isAvailable():
                addonarchive = WurmUnpack.SevenZipArchive(filename, addonname)
            else:
                raise Exception, "Can't extract .rar files; please install 7-Zip (http://www.7-zip.org/) to enable RAR support (specifically, 7z.exe is needed, either in default installation location, on the path, or in the WUU directory)"
        elif extn.lower() == "rar":
            addonarchive = WurmUnpack.RaRArchive(filename, addonname)
        elif extn.lower() == "svn":
            addonarchive = WurmUnpack.SVNArchive(filename, addonname)
        elif extn.lower() == "7z":
            addonarchive = WurmUnpack.SevenZipArchive(filename, addonname)
        elif extn.lower() == "git":
            addonarchive = WurmUnpack.GitArchive(filename, addonname)
        else:
            raise Exception, "Unknown or unsupported file type \"%s\"" % (extn)
        
        # Get the Archive file contents
        addonarchive.GetFilelist()
        
        # Return the list of addons in the Archive
        mapfl = WurmUnpack.MapFilenames(addonname, addonarchive.namelist, addonsonly=True)
        WurmCommon.outDebug("Addons in archive: %s" % (str(mapfl)))
    
    except Exception, details:
        logger.exception("Installation of %s failed: %s" % (addonname, str(details)))
        raise
    
    if len(mapfl) < 1:
        raise Exception, "Couldn't find any addons in archive - installation aborted"
    
    mainaddon = mapfl[0] # Assume first found addon is the "main" addon
    
    # make sure the identified addon isn't an Ace Library, if so then find the first entry that isn't
    if mainaddon in acelibs:
        WurmCommon.outDebug("Main Addon is an Ace Library, looking for the real Addon")
        for ad in mapfl:
            if not ad in acelibs:
                mainaddon = ad
                break
    
    for ad in mapfl: # Iterate addons to see if we find a better match
        if ad.upper() in siteid.upper() or siteid.upper() in ad.upper(): # If addon is a partial match to site id, update guess
            mainaddon = ad
        if ad.upper() == siteid.upper(): # On exact match with site ID, we assume it's the correct one and break
            mainaddon = ad
            break
        if len(ad) < len(mainaddon) and mainaddon[:len(ad)].upper() == ad.upper(): # if addon matches the beginnng of the 'main' addon then it's probably the 'parent' of it and should therefore become the 'main' addon
            mainaddon = ad
    
    addonobj.localname   = mainaddon # Use the correct addoname
    addonobj.versionfile = '%s.wuuver' % (addonobj.localname) #  Use the correct addoname
    WurmCommon.addonlist.add(mainaddon, siteid=siteid, atype=site, flags={'install': True})
    WurmCommon.addons[mainaddon] = addonobj
    if not mainaddon in WurmCommon.toclist:
        refreshSingleAddon(mainaddon, toconly=True)
    WurmCommon.outMessage(_("%(maddon)s set as main addon") % {'maddon': mainaddon})
    
    if len(mapfl) > 1: # set remaining addons to "[Related]"
        for rel in mapfl:
            if rel == mainaddon:
                continue
            WurmCommon.addonlist.add(rel, siteid=mainaddon, atype="[Related]", flags={'install': True})
            if not rel in WurmCommon.toclist:
                refreshSingleAddon(rel, toconly=True)
            WurmCommon.outMessage(_("%(rel)s set to [Related]") % {'rel': rel})
    
    addonarchive = None
    
    return WurmCommon.addons[mainaddon]


def createTextNode(doc, tag, data):
    """ Creates a XML text node in the given doc (does not append it to any part of the tree) """
    tracer.log(WurmCommon.DEBUG5, "createTextNode")
    
    elem = doc.createElement(tag)
    val  = doc.createTextNode(unicode(data))
    elem.appendChild(val)
    return elem


def getAddonSettings(filename, loadSpecialFlags=True):
    """ Loads the addon settings from the default file into the default addon storage, unless the parameters are set.
    loadSpecialFlags toggles whether the site specific flags should be loaded or not. """
    
    tracer.debug("getAddonSettings")
    
    newaddonlist = WurmCommon.AddonList()
    newtoclist   = {}
    
    WurmCommon.outMessage(_("Loading settings from %(filename)s") % {'filename': filename})
    dom = xml.dom.minidom.parse(filename)
    
    # Check version
    wsettings = dom.getElementsByTagName("wurmsettings")[0]
    version   = -1
    try:
        version = getXMLText(wsettings.getElementsByTagName("version")[0].childNodes)
    except:
        WurmCommon.outWarning(_("Could not find file version setting"))
    
    if len(version) > 0 and versionNewer(wurmversion, version):
        WurmCommon.outWarning(_("Inputfile is newer: version %(ver)s - please check %(site)s for a newer version of WUU") % {'ver': version, 'site': WurmCommon.wuusite})
    
    # Parse addons
    waddlist    = dom.getElementsByTagName("wurmaddons")[0]
    waddons     = waddlist.getElementsByTagName("addon")
    totaladdons = float(len(waddons))
    countaddons = 0
    
    for wa in waddons:
        countaddons += 1
        if totaladdons > 1:
            WurmCommon.outProgressPercent(_("Loading Addon settings"), countaddons/totaladdons)
        
        lon = getXMLText(wa.getElementsByTagName("localname")[0].childNodes) # Localname is mandatory
        
        if len(wa.getElementsByTagName("addontype")) > 0:
            adt = getXMLText(wa.getElementsByTagName("addontype")[0].childNodes)
        else:
            adt = None
        
        if len(wa.getElementsByTagName("siteid")) > 0:
            sid = getXMLText(wa.getElementsByTagName("siteid")[0].childNodes)
        else:
            sid = None
        
        if len(wa.getElementsByTagName("friendlyname")) > 0:
            frn = getXMLText(wa.getElementsByTagName("friendlyname")[0].childNodes)
        else:
            frn = None
        
        # load site specific flags (new in 1.1)
        flags = wa.getElementsByTagName("flags")
        if loadSpecialFlags and len(flags) > 0:
            specialflags = {}
            for flag in flags:
                if flag.hasAttribute("name"):
                    name = getXMLText(flag.attributes["name"].childNodes)
                    ftype = "str"
                    if flag.hasAttribute("type"):
                        ftype = getXMLText(flag.attributes["type"].childNodes)
                    
                    value = getXMLText(flag.childNodes)
                    if ftype == "bool":
                        if value in ('1', 'True'):
                            value = True
                        else:
                            value = False
                    if ftype == "int":
                        value = int(value)
                    
                    specialflags[name] = value
        else:
            specialflags = None
        
        # Add to the Addon dictionary
        newaddonlist.add(lon, fname=frn, siteid=sid, atype=adt, flags=specialflags)
        
        toc = wa.getElementsByTagName("toc")
        if len(toc) > 0:
            title  = toc[0].getElementsByTagName("title")
            notes  = toc[0].getElementsByTagName("notes")
            ttitle = None
            tnotes = None
            if len(title) > 0:
                ttitle = getXMLText(title[0].childNodes)
            if len(notes) > 0:
                tnotes = getXMLText(notes[0].childNodes)
            
            if ttitle or tnotes:
                newtoclist[lon] = SimpleTOC(lon)
                newtoclist[lon].setField("Title", ttitle)
                newtoclist[lon].setField("Notes", tnotes)
            # TODO: Dependencies
        
        # WurmCommon.outDebug("Loaded %s (%s)" % (lon, adt))
    
    dom.unlink()
    WurmCommon.outMessage(_("Loaded settings, %(num)d Addons found") % {'num': len(newaddonlist)})
    WurmCommon.outStatus(_("Done loading settings"))
    WurmCommon.resetProgress()
    
    return (newaddonlist, newtoclist)


def getAddonSettingsPack(packid):
    """ Loads addon settings from a pack on the web page - basically just constructs the URL and feeds it to getAddonSettings """
    tracer.debug("getAddonSettingsPack")
    
    url       = "%s?id=%s&output=xml" % (addonpackurl, packid)
    localfile = os.path.join(WurmCommon.directories["temp"], "ap_%s.xml" % (packid))
    WurmCommon.downloadFile(url, localfile)
    
    return (getAddonSettings(localfile))


def getCosmosAddonSettings():
    """ Loads the addon list from CosmosUI.org """
    tracer.debug("getCosmosAddonSettings")
    
    newaddonlist = WurmCommon.AddonList()
    newtoclist   = {}
    
    WurmCommon.outMessage(_("Opening %(calist)s") % {'calist': WurmCommon.cosmosaddonslist})
    htm = WurmCommon.downloadPage(WurmCommon.cosmosaddonslist)
    
    version_re = WurmCommon.siteregexps["cosmos_mlist2"]
    waddons    = re.compile(version_re, re.S).findall(htm)
    
    totaladdons = float(len(waddons))
    countaddons = 0
    
    for wa in waddons:
        countaddons += 1
        if totaladdons > 1:
            WurmCommon.outProgressPercent(_("Loading Addon definitions from Cosmos"), countaddons/totaladdons)
        
        addon = wa[0]
        description = wa[1]
        revision = wa[2]
        
        newaddonlist.add(addon, atype="Cosmos")
        
        if len(description) > 0:
            newtoclist[addon] = SimpleTOC(addon)
            newtoclist[addon].setField("Notes", description)
            newtoclist[addon].setField("WUU-Version", revision)
        
        # WurmCommon.outDebug("Loaded %s" % (addon))
    
    WurmCommon.outMessage(_("Loaded Cosmos, %(num)d Addons found") % {'num': len(newaddonlist)})
    WurmCommon.outStatus(_("Done loading Cosmos addon list"))
    WurmCommon.resetProgress()
    
    return (newaddonlist, newtoclist)


def getXMLText(nodelist):
    """"""
    tracer.log(WurmCommon.DEBUG5, "getXMLText")
    
    rc = u""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    
    return rc.strip()


def identifyAddonFromURL(url):
    """ Parses an URL and returns a (addonname, site, siteid) tuple from it, if possible.
    addonname might be None if the URL doesn't give an unambiguous name.
    Throws exceptions, with relatively meaningful error messages on failure
    """
    
    tracer.debug("identifyAddonFromURL")
    
    (scheme, site, page, query, fragment) = urlparse.urlsplit(url)
    
    if scheme != 'http':
        raise WurmURLParseException(message="Can only parse http:// URLs")
    
    siteid = ""
    
    if 'googlecode.com' in site and 'svn' in page: # Google Code SVN
        path = []
        try:
            path = page.split('/')[1:-1] # this should be on the format '/svn/XXXXX(/YYYYYY)/AddonName'
        except:
            raise WurmURLParseException(site="GoogleCodeSVN")
        
        developer = site.split(".")[0] # first subdomain is the developer name
        
        if len(path) < 3:
            raise WurmURLParseException(site="GoogleCodeSVN")
        
        WurmCommon.outMessage(str([developer, path]))
        
        siteid = None
        
        if path[1] == 'trunk': # shortcut the detection
            siteid = "%s|%s" % (developer, path[2])
        else:
            siteid = "%s|%s" % (developer, "/".join(path[1:]))
        addonname = path[-1]
        
        if not siteid:
            raise WurmURLParseException(site="GoogleCodeSVN")
        
        return (addonname, "GoogleCodeSVN", siteid)
    
    elif 'wow.curse.com' in site or 'www.curse.com' in site:
        path = page.split('/') # this should be on the format '/downloads/details/XXXX/', where the 'XXXX' part is the site ID
        
        if len(path) < 4:
            raise Exception, "No sensible site ID in the URL (length)"
        
        if not path[1] == 'downloads' and not path[3] == 'details':
            raise Exception, "No sensible site ID in the URL (name)"
        
        if not path[4][-5:] == ".aspx":
            raise Exception, "No sensible site ID in the URL (should end with .aspx)"
        
        siteid = path[4][:-5]
        
        return (None, "CurseGaming", siteid)
    
    elif 'wowinterface' in site:
        path = page.split('/') # this should be on the format '/downloads/[download|info]XXXXX-addonname', where the 'XXXXX-addonname' part is the site ID
        if len(path) < 3:
            raise WurmURLParseException(site="WoWI")
        
        part = path[2].replace('.html', '')
        if part[0:4] == 'info':
            part = part[4:]
        elif part[0:8] == 'download':
            part = part[8:]
        else:
            raise WurmURLParseException(site="WoWI")
        
        siteid = part
        
        return (None, "WoWI", siteid)
    
    elif 'deadlybossmods.com' in site:
        xid = query[-1] # query should be on format id=X, where X in 1-3
        
        dbm_ids = {'1':'core', '2':'old', '3':'alpha'}
        
        siteid = dbm_ids.get(xid, None)
        
        if siteid == None:
            raise WurmURLParseException(site="DBM")
        
        return (None, "DBM", siteid)
    
    else:
        raise WurmURLParseException(message="Site %s not supported (yet!) - installation aborted" % (site))


def identifyUnknownAddons():
    """ Looks up all addons marked as [Unknown] in the online database - if allowed! """
    tracer.debug("identifyUnknownAddons")
    
    changed = 0
    
    if not int(WurmCommon.getGlobalSetting(":UseWebsite")):
        return changed
    
    if not WurmCommon.isAvailable["WUUsite"]:
        WurmCommon.outWarning(_("WUU website is unavailable at the moment - request aborted"))
        return changed
    
    data = []
    
    for a in WurmCommon.addonlist:
        (frn, lon, sid, adt) = WurmCommon.addonlist.getSome(a)
        if adt == "[Unknown]":
            ql = "%s|*" % (lon)
            WurmCommon.outDebug("Adding %s to list" % (lon))
            data.append("%s=%s" % (urllib.quote_plus("addon[]"), urllib.quote_plus(ql)))
    
    data     = "&".join(data)
    req      = urllib2.Request(addonsidurl, data)
    req.add_header('User-Agent', WurmCommon.useragent)
    the_page = urllib2.urlopen(req).read()
    # A successful page will contain data on the form <localname>|<wuusite>|<siteid>
    lines    = the_page.split()
    # only the first line is interesting right now
    if not len(lines):
        WurmCommon.outDebug("No updates available from the database")
        return changed
    
    for line in lines:
        addon = parseAddonWeb(line)
        
        if addon and len(addon[2]) > 0 and addon[1] != "WoWAce": # since WoWAce is checked explicitly, ignore any (wrong) addons from online db
            localname = addon[0]
            site      = addon[1]
            siteid    = addon[2]
            WurmCommon.outDebug("%s is now set to %s/%s" % (localname, site, siteid))
            WurmCommon.addonlist.add(localname, siteid=siteid, atype=site)
            refreshSingleAddon(localname)
            changed += 1
    
    return changed


def identifyUnusedSavedVariables():
    """ Returns a dict of localname: [savedvarsfile1, savedvarsfile2,...] for savedvariables not used by the current set of addons """
    tracer.debug("identifyUnusedSavedVariables")
    
    WurmWTF.scanWTF()
    
    result = {}
    
    akeys = [a.upper() for a in WurmCommon.addonlist.keys()]
    
    for addon in WurmWTF.savedvariables:
        if addon not in akeys:
            result[addon] = WurmWTF.savedvariables[addon]
    
    return result


def initialize():
    """ Sets up the necessary paths """
    tracer.debug("initialize")
    
    global addondatafile
    
    if (not "wow" in WurmCommon.directories) or WurmCommon.directories["wow"] == "":
        WurmCommon.outError("Panic! WoW directory is not set")
        return
    
    initTempDir()
    
    WurmCommon.directories["interface"] = os.path.join(WurmCommon.directories["wow"], interfacedir)
    WurmCommon.directories["addons"]    = os.path.join(WurmCommon.directories["interface"], addonsdir)
    if not os.path.exists(WurmCommon.directories["addons"]):
        # might be different capitalisation on unix-based OS'es
        WurmCommon.outDebug("Could not find %s/%s in current WoW directory - trying to check other capitalisations" % (interfacedir, addonsdir))
        interface = locateDir(WurmCommon.directories["wow"], interfacedir)
        if not interface:
            WurmCommon.outWarning(_("Can't find directory \"%(idir)s\" in WoW directory, creating it") % {"idir": interfacedir})
            try:
                os.makedirs(WurmCommon.directories["addons"])
            except:
                pass # WurmCommon.directories["addons"] already exists - but...that makes no sense...
        else:
            WurmCommon.directories["interface"] = os.path.join(WurmCommon.directories["wow"], interface)
            addons = locateDir(WurmCommon.directories["interface"], addonsdir)
            if not addons:
                WurmCommon.outWarning(_("Can't find directory \"%(adir)s\" in %(idir)s directory, creating it") % {"adir": addonsdir, "idir": interfacedir})
                WurmCommon.directories["addons"] = os.path.join(WurmCommon.directories["interface"], addonsdir)
                try:
                    os.makedirs(WurmCommon.directories["addons"])
                except:
                    pass # WurmCommon.directories["addons"] already exists - but...that makes no sense...
            else:
                WurmCommon.directories["addons"] = os.path.join(WurmCommon.directories["interface"], addons)
    
    if not WurmCommon.directories["backup"]:
        WurmCommon.directories["backup"] = os.path.join(WurmCommon.directories["interface"], wuubackupdir)
        try:
            os.makedirs(WurmCommon.directories["backup"])
        except:
            pass # WurmCommon.directories["backup"] already exists
    
    addondatafile = os.path.join(WurmCommon.directories["wow"], addoninfofile)
    
    # Load the regular expressions from file (added, so I can update these without making a new version of WUU)
    WurmCommon.loadRegexps()


def initTempDir():
    """ Sets up only the temp dirs - for when Wurm is used as a library """
    tracer.debug("initTempDir")
    
    WurmCommon.directories["temp"] = os.path.join(tempfile.gettempdir(), "Wurm")
    WurmCommon.directories["unpack"] = os.path.join(tempfile.gettempdir(), "Wurm", "Unpack")
    try:
        os.makedirs(WurmCommon.directories["unpack"])
        os.makedirs(WurmCommon.directories["temp"])
    except:
        pass # WurmCommon.directories["temp"] already exists


def installAddonFromURL(url, download=True):
    """ Creates a addon specification from an URL, if possible.
    If download is True, it's also autoinstalled, otherwise it's just added to the lists """
    
    tracer.debug("installAddonFromURL")
    
    (scheme, site, page, query, fragment) = urlparse.urlsplit(url)
    
    WurmCommon.outDebug("split url: [%s, %s, %s, %s, %s]" % (scheme, site, page, query, fragment))
    
    if scheme != 'http' and scheme != "git":
        raise Exception, "Can only handle http:// or git:// URLs"
        
    path = page.split('/')
    
    WurmCommon.outDebug("path: [%s]" % path)
        
    siteid = ""
    
    # Check the different possible sites
    if 'www.wowace.com' in site:
        
        if not path[1] == 'projects':
            raise Exception, "No sensible site ID in the URL"
        
        siteid = path[2]
        
        if not siteid:
            raise Exception, "No sensible site ID in the URL"
        
        newaddon = WoWAceAddon("__temp", siteid)
        
        htm = newaddon.downloadPage(newaddon.getAddonURL())
        if type(htm) is int:
            return htm
        
        try:
            title_re = "WoW\sAddOns\s-\s(.*)\s-\sWowAce.com"
            titledata = re.compile(title_re).findall(htm)
        
            if len(titledata) == 0:
                WurmCommon.outWarning(_("Could not find %(addon)s title on page - is site ID correct?") % {'addon': siteid})
                return -1
                
            addonname = titledata[0]
            newaddon.localname = addonname
            newaddon.versionfile = '%s.wuuver' % (newaddon.localname) #  Use the correct addoname
            WurmCommon.addonlist.add(addonname, siteid=siteid, atype=newaddon.addontype)
            WurmCommon.addons[addonname] = newaddon
            if not addonname in WurmCommon.toclist:
                refreshSingleAddon(addonname, toconly=True)
        
        except:
            raise
                
    
    elif 'googlecode.com' in site and 'svn' in page:
        
        (addon, site, siteid) = identifyAddonFromURL(url)
        
        newaddon = GoogleCodeSVNAddon(addon, siteid)
        
        WurmCommon.addonlist.add(addon, siteid=siteid, atype=site, flags={'install': True})
        WurmCommon.addons[addon] = newaddon
        
        if not addon in WurmCommon.toclist:
            refreshSingleAddon(addon, toconly=True)
    
    elif 'wow.curse.com' in site or 'www.curse.com' in site:
        
        if len(path) < 4:
            raise Exception, "No sensible site ID in the URL (length)"
        
        if not path[1] == 'downloads' and not path[3] == 'details':
            raise Exception, "No sensible site ID in the URL (name)"
        
        if not path[4][-5:] == ".aspx":
            raise Exception, "No sensible site ID in the URL (should end with .aspx)"
        
        siteid = path[4][:-5]
        
        # add an entry for this addon but don't download it
        newaddon = CurseGamingAddon("__temp", siteid)
        
        # get addon name from webpage
        htm = newaddon.downloadPage(newaddon.getAddonURL())
        if type(htm) is int:
            return htm
        
        try:
            title_re = "\t(.*)\s-\sAddons\s-\sCurse"
            titledata = re.compile(title_re).findall(htm)
        
            if len(titledata) == 0:
                WurmCommon.outWarning(_("Could not find %(addon)s title on page - is site ID correct?") % {'addon': siteid})
                return -1
                
            addonname = titledata[0]
            newaddon.localname = addonname
            newaddon.versionfile = '%s.wuuver' % (newaddon.localname) #  Use the correct addoname
            WurmCommon.addonlist.add(addonname, siteid=siteid, atype=newaddon.addontype)
            WurmCommon.addons[addonname] = newaddon
            if not addonname in WurmCommon.toclist:
                refreshSingleAddon(addonname, toconly=True)
        
        except:
            raise
                
    elif 'wowinterface' in site:
        
        if len(path) < 3:
            raise Exception, "No sensible site ID in the URL [1]"
        
        part = path[2].replace('.html', '')
        if part[0:4] == 'info':
            part = part[4:]
        elif part[0:8] == 'download':
            part = part[8:]
        else:
            raise Exception, "No sensible site ID in the URL [3]"
        
        siteid = part
        
        newaddon = WoWIAddon("__temp", siteid)
        
        try:
            newaddon = _downloadAndIdentify(newaddon, "WoWI", siteid)
        except:
            raise
    
    elif 'deadlybossmods' in site:
        
        xid = query[-1] # query should be on format id=X, where X in 1-3
        
        dbm_ids = {'1':'core', '2':'old', '3':'alpha'}
        
        siteid = dbm_ids.get(xid, None)
        
        if siteid == None:
            raise WurmURLParseException(site="DBM")
        
        newaddon = DBMAddon("__temp", siteid)
        
        try:
            newaddon = _downloadAndIdentify(newaddon, "DBM", siteid)
        except:
            raise
    
    elif scheme == 'git':
        
        siteid = url
        
        newaddon = GenericGitAddon("__temp", siteid)
        
        try:
            newaddon = _downloadAndIdentify(newaddon, "GenericGit", siteid)
        except:
            raise
    
    else:
        raise Exception, "Site %s not supported (yet!) - installation aborted" % (site)
    
    if download:
        # Now try and install the Addon
        try:
            newaddon.updateMod()
        except:
            raise
    
    return newaddon


def locateDir(path, dir):
    """ Finds the name of dir in path, if possible, as a case insensitive search """
    tracer.debug("locateDir")
    
    if not os.path.exists(path):
        return None
    
    dir_re = "^%s$" % (dir)
    redir  = re.compile(dir_re, re.I) # case insensitive regexp
    
    listing = os.listdir(path)
    for entry in listing:
        name = os.path.join(path, entry)
        if os.path.isdir(name) and redir.match(entry):
            return entry
    
    return None


def lookupSiteID(localname, site='*'):
    """ Does a quick lookup of the site ID in the online database - if allowed! "*" for site means "any site" """
    tracer.debug("lookupSiteID")
    
    if not int(WurmCommon.getGlobalSetting(":UseWebsite")):
        return None
    
    if not WurmCommon.isAvailable["WUUsite"]:
        WurmCommon.outWarning(_("WUU website is unavailable at the moment - request aborted"))
        return None
    
    try:
        requrl = "%s?addon[]=%s|%s" % (addonsidurl, localname, site) #GET request is OK for single addon query
        req = urllib2.Request(requrl)
        req.add_header('User-Agent', WurmCommon.useragent)
        the_page = urllib2.urlopen(req).read()
        # A successful page will contain data on the form <localname>|<wuusite>|<siteid>
        lines = the_page.split()
        # only the first line is interesting right now
        if not len(lines):
            return None
        
        addon = parseAddonWeb(lines[0])
        
        if addon and len(addon[2]) > 0:
            if site == '*':
                return addon # localname, site, siteid
            else:
                return addon[2] # the site ID
        else:
            return None
    except:
        return None


def mergeSettings(alternateFileName=None):
    """"""
    tracer.debug("mergeSettings")
    
    global addondatafile
    
    WurmCommon.outMessage(_("Merging settings"))
    
    nomerge  = ("[Unknown]", "[Ignore]", "[Dummy]", None) # these types will not be imported INTO running set
    nochange = ("[Ignore]", "[Dummy]", ) # these types will not be changed in running set
    dom      = ""
    
    if alternateFileName:
        dom = xml.dom.minidom.parse(alternateFileName)
    else:
        dom = xml.dom.minidom.parse(addondatafile)
    
    # -- ignore version/settings for now
    
    # Parse addons
    waddlist    = dom.getElementsByTagName("wurmaddons")[0]
    waddons     = waddlist.getElementsByTagName("addon")
    totaladdons = float(len(waddons))
    countaddons = 0
    
    merged = []
    for wa in waddons:
        countaddons += 1
        if totaladdons > 1:
            WurmCommon.outProgressPercent(_("Merging Addons"), countaddons/totaladdons)
        
        lon = getXMLText(wa.getElementsByTagName("localname")[0].childNodes) # Localname is mandatory
        
        if len(wa.getElementsByTagName("addontype")) > 0:
            adt = getXMLText(wa.getElementsByTagName("addontype")[0].childNodes)
        else:
            adt = None
        
        if len(wa.getElementsByTagName("siteid")) > 0:
            sid = getXMLText(wa.getElementsByTagName("siteid")[0].childNodes)
        else:
            sid = None
        
        if len(wa.getElementsByTagName("friendlyname")) > 0:
            frn = getXMLText(wa.getElementsByTagName("friendlyname")[0].childNodes)
        else:
            frn = None
        
        # load site specific flags (new in 1.1)
        flags = wa.getElementsByTagName("flags")
        if len(flags) > 0:
            specialflags = {}
            for flag in flags:
                if flag.hasAttribute("name"):
                    name = getXMLText(flag.attributes["name"].childNodes)
                    ftype = "str"
                    if flag.hasAttribute("type"):
                        ftype = getXMLText(flag.attributes["type"].childNodes)
                    
                    value = getXMLText(flag.childNodes)
                    if ftype == "bool":
                        if value in ('1', 'True'):
                            value = True
                        else:
                            value = False
                    if ftype == "int":
                        value = int(value)
                    
                    specialflags[name] = value
        else:
            specialflags = None
        
        if adt not in nomerge and lon in WurmCommon.addonlist and WurmCommon.addonlist.getAtype(lon) in nomerge and WurmCommon.addonlist.getAtype(lon) not in nochange:
            WurmCommon.addonlist.add(lon, fname=frn, siteid=sid, atype=adt, flags=specialflags)
            if not lon in WurmCommon.toclist:
                refreshSingleAddon(lon)
            WurmCommon.outMessage(_("Merged %(fname)s (%(atype)s)") % {'fname': frn, 'atype': adt})
            merged.append(lon)
        elif adt == "[Ignore]" and lon[:9] == "Blizzard_" and (lon in WurmCommon.addonlist and WurmCommon.addonlist.getAtype(lon) != "[Ignore]"):
            WurmCommon.addonlist.add(lon, fname=frn, siteid=sid, atype=adt, flags=specialflags)
            if not lon in WurmCommon.toclist:
                refreshSingleAddon(lon)
            WurmCommon.outMessage(_("Set %(fname)s to [Ignore]") % {'fname': frn})
            merged.append(lon)
    
    dom.unlink()
    WurmCommon.outMessage(_("Merged settings, %(num)d Addons updated") % {'num': len(merged)})
    WurmCommon.outStatus(_("Done merging settings"))
    WurmCommon.resetProgress()
    
    return merged


def parseAddonWeb(line):
    """ Parses addon settings from a response from the web, on the format <localname>|<wuusite>|<siteid> - returns None if nothing can be gathered from the line """
    tracer.debug("parseAddonWeb")
    
    if not "|" in line:
        return None
    
    fields = line.split("|")
    if fields < 3:
        return None # too few fields
    
    return fields[:3]


def purgeMissing():
    """ Removes all addons flagged as missing from the addon list """
    tracer.debug("purgeMissing")
    
    removedcount = 0
    
    tmpaddonlist = WurmCommon.addonlist.keys() # work on a copy of addonlist
    for addon in tmpaddonlist:
        if WurmCommon.addonlist.getFlag(addon, "missing"):
            WurmCommon.addonlist.delete(addon)
            if WurmCommon.addons.has_key(addon):
                del WurmCommon.addons[addon]
            
            if WurmCommon.toclist.has_key(addon):
                del WurmCommon.toclist[addon]
            
            removedcount += 1
    
    # Save any changes made so they aren't lost :)
    if WurmCommon.listchanged[WurmCommon.addonlist._id]:
        saveAddonSettings()
    
    msg = _("Purged %(num)d missing Addons from the list") % {'num':removedcount}
    WurmCommon.outMessage(msg)
    WurmCommon.outStatus(msg)
    
    return removedcount


def refreshAddons():
    """ Refreshes the Addon List Control information """
    tracer.debug("refreshAddons")
    
    if len(WurmCommon.addonlist) == 0:
        return
    
    totaladdons = float(len(WurmCommon.addonlist))
    countaddons = 0
    
    for a in WurmCommon.addonlist:
        countaddons += 1
        
        # Ignore Blizzard Addons
        if a[:9] == "Blizzard_":
            continue
        
        if totaladdons > 1:
            WurmCommon.outProgressPercent(_("Refreshing Addons"), countaddons/totaladdons)
        
        refreshSingleAddon(a)
    
    WurmCommon.outStatus(_("Addons refreshed"))
    WurmCommon.resetProgress()


def refreshSingleAddon(addonname, toconly=False):
    """ Syncs a single addon from the raw addonlist to the actual list of "live" addon objects """
    tracer.debug("refreshSingleAddon: %s" % (addonname))
    
    if threading.currentThread().getName() != "MainThread":
        WurmCommon.wurmlock["Wurm2"].acquire()
    
    try:
        try:
            (friendlyname, localname, siteid, addontype, specialflags) = WurmCommon.addonlist.getAll(addonname)
            # Get a TOC instance
            toc = TOCFile(addonname, specialflags)
            
            if toc.isValid:
                tracer.log(WurmCommon.DEBUG3, "TOC is Valid: %s" % (addonname))
                WurmCommon.toclist[addonname] = toc
            elif addonname in WurmCommon.toclist and not 'install' in specialflags:
                del WurmCommon.toclist[addonname]
            
            # If only the TOC details are to be updated then leave here
            if toconly:
                return
            
            # If the addon type is one of the following it will not be added to the list
            # it will be removed instead
            # "[Dummy]", "[Ignore]", "[Outdated]", "[Related]", "[Unknown]"
            if WurmCommon.addontypes.get(addontype):
                add = WurmCommon.addontypes[addontype](localname, siteid, flags = specialflags)
                WurmCommon.addons[addonname] = add
            elif addonname in WurmCommon.addons:
                del WurmCommon.addons[addonname]
            elif addontype not in WurmCommon.addontypes:
                WurmCommon.outWarning(_("Unknown Addon site/type: %(atype)s") % {'atype': addontype})
        except Exception, details:
            logger.exception("Error refreshing %s: %s" % (addonname, str(details)))
            raise
    finally:
        if threading.currentThread().getName() != "MainThread":
            WurmCommon.wurmlock["Wurm2"].release()


def saveAddonSettings(alternateFileName=None, selection=None, saveSpecialFlags=True):
    """ Saves the addon list to default XML file unless alternateFileName is specified.
    List can be filtered with the selection parameter, and saveSpecialFlags toggles whether site specific flags should be stored.
    """
    tracer.debug("saveAddonSettings")
    
    global addondatafile, wurmversion
    WurmCommon.outMessage(_("Saving settings"))
    
    impl        = xml.dom.minidom.getDOMImplementation()
    xmldoc      = impl.createDocument(None, "wurm", None)
    top_element = xmldoc.documentElement
    
    # Settings (only version for now)
    wsettings = xmldoc.createElement("wurmsettings")
    wsettings.appendChild(createTextNode(xmldoc, "version", "%s" % (wurmversion)))
    top_element.appendChild(wsettings)
    
    # Addons
    waddons = xmldoc.createElement("wurmaddons")
    
    k = WurmCommon.addonlist.keys()
    k.sort()
    totaladdons = float(len(WurmCommon.addonlist))
    countaddons = 0
    
    for a in k:
        countaddons += 1
        if totaladdons > 1:
            WurmCommon.outProgressPercent(_("Saving Addon settings"), countaddons/totaladdons)
        
        # Implements "only export selected"
        if alternateFileName and selection and (a not in selection):
            continue
        
        (friendlyname, localname, siteid, addontype, flags) = WurmCommon.addonlist.getAll(a)
        
        addon = xmldoc.createElement("addon")
        addon.appendChild(createTextNode(xmldoc, "localname", localname))
        if addontype != "[Unknown]": # only set addontype if it's changed from unknown
            addon.appendChild(createTextNode(xmldoc, "addontype", addontype))
        if friendlyname != localname: # only set friendlyname if it's actually changed
            addon.appendChild(createTextNode(xmldoc, "friendlyname", friendlyname))
        if siteid != localname and siteid != "": # only set siteid if it's actually "not localname and not empty"
            addon.appendChild(createTextNode(xmldoc, "siteid", siteid))
        
        if saveSpecialFlags:
            # Handles the special flags
            # Bugfix: appends the flags from the addon object, if they exist
            if a in WurmCommon.addons:
                flags.update(WurmCommon.addons[a].specialflags)
            
            for flag in flags:
                # Don't write out transient or deprecated flag settings
                if flag in ['missing', 'install', 'no-ext']:
                    continue
                # Don't write out ignore-no-ext or ProcessPackage if setting is false
                if flag in ['ignore-no-ext', 'ProcessPackage'] and not flags[flag]:
                    continue
                xmlflag = createTextNode(xmldoc, "flags", flags[flag])
                xmlflag.attributes["name"] = flag
                if type(flags[flag]) == bool:
                    xmlflag.attributes["type"] = "bool"
                elif type(flags[flag]) == int:
                    xmlflag.attributes["type"] = "int"
                else:
                    xmlflag.attributes["type"] = "str"
                
                addon.appendChild(xmlflag)
        
        try:
            if a in WurmCommon.toclist: # Save some keys from TOC if possible
                toc = xmldoc.createElement("toc")
                toc.appendChild(createTextNode(xmldoc, "title", WurmCommon.toclist[a].getTextField("Title", False)))
                toc.appendChild(createTextNode(xmldoc, "notes", WurmCommon.toclist[a].getTextField("Notes", False)))
                dep = WurmCommon.toclist[a].getDependencies()
                if len(dep) > 0:
                    depend = xmldoc.createElement("dependencies")
                    for de in dep:
                        depend.appendChild(createTextNode(xmldoc, "dep", de))
                    toc.appendChild(depend)
                addon.appendChild(toc)
        except:
            pass # Unicode errors might happen here, but we can safely ignore them for now
        
        waddons.appendChild(addon)
        # WurmCommon.outDebug("Saved %s" % (a))
    
    top_element.appendChild(waddons)
    
    targetFileName = addondatafile
    formatPretty = True #False
    if alternateFileName != None:
        targetFileName = alternateFileName
        formatPretty = True # Using "pretty" XML on exports, plain on internal file
    
    try:
        f = open(targetFileName, "wt")
        xmldata = ""
        if not formatPretty:
            xmldata = xmldoc.toxml(encoding="utf-8")
        else:
            xmldata = xmldoc.toprettyxml(encoding="utf-8")
        f.write(xmldata)
        f.close()
    except IOError, details:
        WurmCommon.outError(_("Unable to write to file %(file)s: %(error)s") % {'file':targetFileName, 'error':str(details)})
    
    WurmCommon.listchanged[WurmCommon.addonlist._id] = False
    
    WurmCommon.outMessage(_("Saved settings"))
    WurmCommon.outStatus(_("Done saving settings"))
    WurmCommon.resetProgress()


def scanAddons(forceInstallMissing=True):
    """"""
    tracer.debug("scanAddons")
    
    # Part 1. Scan the Addon directory, ignore SVN addons and add any new ones found
    seenaddons         = []
    totaladdons        = float(len(WurmCommon.addonlist))
    WurmCommon.depdict = {}
    newadds = missadds = insadds = ignoreadds = dummyadds = countaddons = deladds = childadds = 0
    
    for a in os.listdir(WurmCommon.directories["addons"]):
        # Ignore entries that aren't directories
        if not os.path.isdir(os.path.join(WurmCommon.directories["addons"], a)):
            continue
        
        if a in WurmCommon.addonlist:
            aType = WurmCommon.addonlist.getAtype(a)
        else:
            aType = None
        
        countaddons += 1
        if totaladdons > 1:
            WurmCommon.outProgressPercent(_("Scanning Addons directory"), countaddons/totaladdons)
        
        seenaddons.append(a)
        
        # Flag Blizzard Addons as [Ignore]
        if a[:9] == "Blizzard_":
            if aType != "[Ignore]":
                WurmCommon.addonlist.add(a, atype="[Ignore]")
                ignoreadds += 1
                continue
        else:
            scanForDeps(a)
        
        # Set svn working dirs to "[Ignore]"
        if os.path.isdir(os.path.join(WurmCommon.directories["addons"], a, ".svn")) or \
           os.path.isdir(os.path.join(WurmCommon.directories["addons"], a, ".git")):
            if a in WurmCommon.addonlist:
                if aType != "[Ignore]":
                    WurmCommon.outMessage(_("Changing Addon %(addon)s to [Ignore] due to .svn/.git folder") % {'addon': a})
                    WurmCommon.addonlist.add(a, atype="[Ignore]")
                    if not a in WurmCommon.toclist:
                        refreshSingleAddon(a, toconly=True)
                if a in WurmCommon.addons: # remove it from running addons
                    del WurmCommon.addons[a]
                ignoreadds += 1
            else:
                newadds += 1
                WurmCommon.outMessage(_("New Addon %(addon)s has .svn/.git, and is set to [Ignore]") % {'addon': a})
                WurmCommon.addonlist.add(a, atype="[Ignore]")
                if not a in WurmCommon.toclist:
                    refreshSingleAddon(a)
                ignoreadds += 1
            continue # skip further processing
        
        # Increment Ignore/DummyNew counts as required
        if a in WurmCommon.addonlist:
            if aType == "[Ignore]":
                ignoreadds += 1
            if aType == "[Dummy]":
                dummyadds += 1
        else:
            newadds += 1
            WurmCommon.outMessage(_("New Addon: %(addon)s") % {'addon': a})
            WurmCommon.addonlist.add(a)
            if not a in WurmCommon.toclist:
                refreshSingleAddon(a, toconly=True)
    
    WurmCommon.outStatus(_("Done scanning Addons directory"))
    WurmCommon.resetProgress()
    
    tracer.log(WurmCommon.DEBUG5, "depdict: %d, %s" % (len(WurmCommon.depdict) , str(WurmCommon.depdict)))
    
    # Part 2. Scan the raw addons list, install missing ones if required, tidyup special flag settings as required, flag missing addons
    flaglater    = []
    toInstall    = []
    tmpaddonlist = WurmCommon.addonlist.keys() # work on a copy of addonlist (since .updateMod() might change WurmCommon.addonlist)
    totaladdons  = float(len(tmpaddonlist))
    countaddons  = 0
    
    for a in tmpaddonlist:
        countaddons += 1
        if totaladdons > 1:
            WurmCommon.outProgressPercent(_("Scanning Addons list"), countaddons/totaladdons)
        
        # Ignore Blizzard Addons
        if a[:9] == "Blizzard_":
            continue
        
        aType = WurmCommon.addonlist.getAtype(a)
        if aType == "Child":
            childadds += 1
        
        # Ignore Child, Dummy & Ignore Addons
        if a not in seenaddons and not aType in ["Child", "[Dummy]", "[Ignore]"]:
            # check for lowercase duplicate, if found remove this entry
            if a.lower() in seenaddons:
                WurmCommon.addonlist.delete(a)
                deladds += 1
            # check for Capitalised duplicate, if found remove this entry
            elif a.capitalize() in seenaddons:
                WurmCommon.addonlist.delete(a)
                deladds += 1
            # check for Capitalised duplicate in a hyphenated name, if found remove this entry
            # this code splits the name on a hyphen,
            # capitalises each part and then joins them back together
            elif a.find("-") and string.join(map(string.capitalize, string.split(a, "-")),"-") in seenaddons:
                WurmCommon.addonlist.delete(a)
                deladds += 1
            # addon has been removed, or should be installed
            elif forceInstallMissing and a in WurmCommon.addons:
                insadds += 1
                toInstall.append(a)
            else:
                missadds += 1
                # WurmCommon.outDebug("Addon %(addon)s is missing" % {'addon': a})
                flaglater.append(a)
    
    for a in flaglater:
        if not WurmCommon.addonlist.getFlag(a, "missing"):
            WurmCommon.addonlist.addFlag(a, "missing", True)
            WurmCommon.outWarning(_("Addon %(addon)s has been flagged as missing") % {'addon': a})
        if a in WurmCommon.addons and not "missing" in WurmCommon.addons[a].specialflags:
            WurmCommon.addons[a].specialflags["missing"] = True
    
    # Save any changes made so they aren't lost :)
    if WurmCommon.listchanged[WurmCommon.addonlist._id]:
        saveAddonSettings()
    
    WurmCommon.outMessage(_("Scanned Addon directory, %(snum)d Addons found (%(new)d new, %(ins)d installed fresh, %(miss)d missing, %(ign)d ignored, %(dum)d dummy, %(del)d deleted, %(chld)s children)") % {'snum': len(seenaddons) + childadds, 'new': newadds, 'ins': insadds, 'miss': missadds, 'ign': ignoreadds, 'dum': dummyadds, 'del': deladds, 'chld': childadds})
    WurmCommon.outStatus(_("Done scanning Addons list"))
    WurmCommon.resetProgress()
    
    return toInstall


def scanForDeps(dirname, root=None):
    """"""
    tracer.log(WurmCommon.DEBUG5, "scanForDeps: %s, %s" % (dirname, root))
    
    if not dirname:
        dirname = ""
    
    if not root:
        root = WurmCommon.directories["addons"]
    
    ignoreDirs = [".svn", ".git", "AddonSkins"]
    # Ignore specified directories
    if dirname in ignoreDirs:
        return
    
    # get the last component of the directory name
    (head, tail) = os.path.split(dirname)
    
    try:
        for direntry in os.listdir(os.path.join(root, dirname)):
            if os.path.isdir(os.path.join(root, dirname, direntry)):
                scanForDeps(os.path.join(dirname, direntry), root)
            else:
                (filename, ext) = os.path.splitext(direntry)
                # check to see if we have a dependency
                if (ext.lower() == ".lua" or ext.lower() == ".toc") and filename == tail:
                    WurmCommon.depdict[filename] = dirname
    except Exception, details:
        WurmCommon.outDebug("Error scanning for dependencies: %s" % (str(details)))


def syncAddons():
    """"""
    tracer.debug("syncAddons")
    
    for a in WurmCommon.addons:
        WurmCommon.addons[a].sync()


def unzipToTemp(filename):
    """ Unpacks the given ZIP file to %TEMP%\Wurm """
    tracer.debug("unzipToTemp")
    
    if "temp" not in WurmCommon.directories or len(WurmCommon.directories["temp"]) == 0:
        initTempDir()
    
    try:
        WurmUnpack.PlainUnzip(filename, WurmCommon.directories["temp"])
        WurmCommon.outDebug("Uncompressed %s to %s" % (filename, WurmCommon.directories["temp"]))
        return True
    except Exception, details:
        WurmCommon.outDebug("Could not unzip file, %s" % (str(details)))
        return False


def updateWUU(newversion, beta=False):
    """ Downloads new version + signature, and verifies it """
    """ If verified then install the new version """
    global tracer, logger
    
    tracer.debug("updateWUU")
    
    if os.name != 'nt' and not canAutoUpdate:
        msg = "Autoupdate not implemented for this OS yet"
        WurmCommon.outError(msg)
        raise Exception, msg
    
    if os.name == "nt":
        # It's necessary to drop the loggers, or the signature check will fail
        # 2007-11-14> Testing without dropping the loggers, since faults in this code has been reported
        # TODO: Make a wrapper around the tracer so it can be dropped at any time without being afraid of
        #       "lost objects" (i.e. we should be able to free the file handle without adding a
        #       "if tracer != None" to each function call
        try:
            if not beta:
                os.execv("UpdateWUU.exe", ("UpdateWUU.exe",))
            else:
                os.execv("UpdateWUUbeta.exe", ("UpdateWUUbeta.exe",))
        except OSError:
            upd = "UpdateWUU.exe"
            if beta:
                upd = "UpdateWUUbeta.exe"
                
            WurmCommon.outError(_("Fatal error: Unable to update WUU - please run %(updatewuu)s manually, or download the newest version from the WUU web page.") % (upd))
            raise
    else:
        WurmCommon.outDebug("WUU new version: %s" % (newversion))
        # if the application directory is under SVN/Git control then ignore the update
        if os.path.isdir(os.path.join(appldir, ".svn")) or os.path.isdir(os.path.join(appldir, ".git")):
            msg = _("WUU Application directory is under SVN/Git control, ignoring update")
            WurmCommon.outWarning(msg)
            raise Exception, msg
        
        # setup the filenames
        filename = "WUU-%s-src.zip" % (newversion)
        sigfile = "%s.sig" % (filename)
        
        # download the zip and zip.sig files
        try:
            dlfname  = "%sfiles/%s" % (WurmCommon.wuusite, filename)
            localsrc = os.path.join(WurmCommon.directories["temp"], filename)
            WurmCommon.downloadFile(dlfname, localsrc, shorten=True)
            dlfname  = "%sfiles/%s" % (WurmCommon.wuusite, sigfile)
            localsig = os.path.join(WurmCommon.directories["temp"], sigfile)
            WurmCommon.downloadFile(dlfname, localsig, shorten=True)
        except Exception, details:
            WurmCommon.outWarning(_("WUU Source File(s) download failed: %(dlf)s, %(dets)s") % {'dlf': dlfname, 'dets': str(details)})
            raise
        
        # verify the zip.sig file
        if not verifySig(localsrc, localsig):
            msg = "Signature Verification Failed: %s, %s" % (localsrc, localsig)
            WurmCommon.outError(msg)
            raise Exception, msg
        
        # install the contents of the zip file to the original Application directory
        # ignores the platform it is running on
        try:
            WurmUnpack.PlainUnzip(localsrc, origappldir)
            WurmCommon.outDebug("Installed %s to %s" % (localsrc, origappldir))
            return True
        except Exception, details:
            logger.exception("Error: Couldn't unzip file: %s" % str(details))
            raise


def uploadInfo(): #TODO: Move all website tied code to a new file
    """ Uploads info to WUU website """
    tracer.debug("uploadInfo")
    
    data = []
    
    for a in WurmCommon.addons:
        onlineversion = WurmCommon.addons[a].getOnlineModVersion()
        
        if onlineversion > 0:
            (frn, lon, sid, adt) = WurmCommon.addonlist.getSome(a)
            if adt[0] != "[": # only "real" sites
                ql = "%s|%s|%s" % (lon, adt, sid)
                data.append("%s=%s" % (urllib.quote_plus("addon[]"), urllib.quote_plus(ql)))
    
    data     = "&".join(data)
    req      = urllib2.Request(infosubmiturl, data)
    req.add_header('User-Agent', WurmCommon.useragent)
    the_page = urllib2.urlopen(req).read()
    # on a successful update, the page will return "OK X", where X is the number of addons successfully added/voted for
    if len(the_page) <= 120: # this'll have to do for now - TODO: better check
        fields = the_page.split()
        if fields[0] == "OK":
            packhash  = fields[1]
            packcount = fields[2]
            updated   = fields[3]
            packadded = fields[4]
            WurmCommon.outStatus(_("Thank you! %(upd)s of your Addons were added to the database") % {'upd': updated})
            WurmCommon.outMessage(_("This Addon pack contains %(pcnt)s Addons and has the following code: %(phash)s") % {'pcnt': packcount, 'phash': packhash})
            if packadded == "1":
                WurmCommon.outDebug("The addon pack was added to the database")
        elif fields[0] == "ERROR":
            WurmCommon.outError("ERROR response from web server: %(fields)s" % {'fields': " ".join(fields[1:])})
        else:
            WurmCommon.outWarning(_("Unexpected message from web server: %(page)s") % {'page': the_page})
    else:
        WurmCommon.outWarning(_("Unexpected message from web server: %(page)s") % {'page': the_page})


def verifySig(filename, sigfile=None):
    """ Verifies that a file is correctly signed - if sigfile is None, filename + ".sig" is assumed """
    tracer.debug("verifySig")
    
    if not sigfile:
        sigfile = "%s.sig" % (filename)
    
    verify = False
    try:
        WurmCommon.outDebug("Loading public key")
        key = ezPyCrypto.key(keyobj='')
        key.importKey(publickey)
        f   = open(sigfile, "rt")
        sig = f.read()
        f.close()
        
        WurmCommon.outDebug("Verifying %s" % (filename))
        f      = open(filename, "rb")
        verify = key.verifyString(f.read(), sig)
        f.close()
    except:
        pass # ignore signature verification error
    
    if verify:
        WurmCommon.outDebug("Signature OK!")
    else:
        WurmCommon.outDebug("Signature FAILED!")
    return verify


def versionNewer(oldver, newver):
    """ Returns True if newver is newer than oldver """
    tracer.debug("versionNewer")
    
    oldver = [int(x) for x in oldver.split(".")]
    newver = [int(x) for x in newver.split(".")]
    
    parts = len(oldver)
    if len(oldver) != len(newver):
        if len(newver) < len(oldver):
            parts = len(newver)
    
    for i in range(parts):
        if newver[i] > oldver[i]:
            return True
    
    return False

