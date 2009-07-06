#!/usr/bin/env python
# -*- coding: utf-8 -*-

# $Id: WUU.py 666 2009-06-30 17:37:45Z lejordet $

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

# Style rules from http://wiki.wxpython.org/index.cgi/wxPython_Style_Guide have been used
# 2008-01-15: Applied patch 1866042 submitted by sourceforge user iroro
# 2008-02-19: Applied patch 1878044 submitted by sourceforge user iroro

# release version bump

import logging, logging.handlers
logger = None
tracer = None

import os, sys
import platform

try:
    import psyco
except ImportError:
    pass

import WurmCommon
# Setup log file names
logfile   = os.path.join(WurmCommon.supportdir, "WUU.log")
tracefile = os.path.join(WurmCommon.supportdir, "WUU.trace")

# Check to see if running Python version 2.4 or later
if map(int, platform.python_version().split(".")[:2]) < [2, 4]:
    message = "\n(FATAL ERROR) You need to install Python (http://www.python.org/) 2.4.4 or higher (2.5 is preferred) to run WUU\n"
    open(logfile, "at").write(message)
    print message
    sys.exit(1)

# Check to see if wxPython is installed and whether it is a suitable version, handles bundles as well
if not hasattr(sys, "frozen"):
    try:
        import wxversion
        wxversion.ensureMinimal('2.6')
    except ImportError:
        # "Friendly" error message
        message = "\n(FATAL ERROR) You need to install wxPython (http://www.wxpython.org/) 2.6.3.3 or higher (2.8 is preferred) to run WUU\n"
        open(logfile, "at").write(message)
        print message
        sys.exit(1)

import wx
import wx.html
import wx.lib.wxpTag
import wx.lib.mixins.listctrl as listmix
import images
import webbrowser
import threading
from datetime import datetime

try: # Import C-based ElementTree module
    from xml.etree.cElementTree import ElementTree, Element, SubElement
except ImportError:
    try:
        # Fallback level 1, try the "native" ElementTree in Python 2.5
        from xml.etree.ElementTree import ElementTree, Element, SubElement
    except ImportError:
        # Fallback level 2, use the provided ElementTree
        from ElementTree import ElementTree, Element, SubElement

# Treat UnicodeWarning's as an error if running Python 2.5 or higher
if map(int, platform.python_version().split(".")[:2]) >= [2, 5]:
    import warnings
    # Warnings Filter
    warnings.simplefilter("error", UnicodeWarning) # turn UnicodeWarning into an error
else:
    UnicodeWarning = UnicodeDecodeError

# Import Application Libraries
import Wurm
import WurmUtility
from WUUHelpers import BrowserHtmlWindow
from WUUAbout import WUUAboutBox
import WUUDialogs

# Remap dummy translation function to real trans func
translator = WurmCommon.WurmLanguage
_          = translator.s

# Revision & Version information
revision    = "$Revision: 666 $"
revision    = revision[revision.find(":") + 1:-1].strip()
wuuversion  = "%s.%s" % (Wurm.wurmversion, revision)
__version__ = wuuversion

# Make WUU look more like a browser
try:
    WurmCommon.setUserAgent(wuuversion)
except:
    pass # We don't care if it's not successfully set

# shortcuts to code in WUUDialogs
lcColour               = WUUDialogs.lcColour
availablesites         = WUUDialogs.availablesites
WurmAddonEditDlg       = WUUDialogs.WurmAddonEditDlg
WUUPreferencesDlg      = WUUDialogs.WUUPreferencesDlg
WurmAddonInstallDlg    = WUUDialogs.WurmAddonInstallDlg
WurmAdvancedRestoreDlg = WUUDialogs.WurmAdvancedRestoreDlg
WurmProgress           = WUUDialogs.WurmProgress

# Files, URLs and paths
masterUrl                  = WurmCommon.wuusite + "master.addons.wurm.xml"
masterFile                 = os.path.join(WurmCommon.supportdir, "master.addons.wurm.xml")
masterVersion              = WurmCommon.wuusite + "version.txt"
masterBetaVersion          = WurmCommon.wuusite + "betaversion.txt"
masterVersionFile          = os.path.join(WurmCommon.supportdir, "latestversion.txt")
masterBetaVersionFile      = os.path.join(WurmCommon.supportdir, "latestbetaversion.txt")
masterListVersion          = WurmCommon.wuusite + "masterlistversion.txt"
masterListVersionFile      = os.path.join(WurmCommon.supportdir, "latestmasterlistversion.txt")
masterListLocalVersionFile = os.path.join(WurmCommon.supportdir, "masterlistversion.txt")
regexpLocalVersionFile     = os.path.join(WurmCommon.supportdir, "reversion.txt")
regexpVersionFile          = os.path.join(WurmCommon.supportdir, "latestreversion.txt")
regexpVersion              = WurmCommon.wuusite + "reversion.txt"
regexpUrl                  = WurmCommon.reurl
regexpFile                 = WurmCommon.refilename
templateLocalVersionFile   = os.path.join(WurmCommon.supportdir, "templateversion.txt")
templateVersionFile        = os.path.join(WurmCommon.supportdir, "latesttemplateversion.txt")
templateVersion            = WurmCommon.wuusite + "templateversion.txt"
templateUrl                = WurmCommon.templateurl
templateFile               = WurmCommon.templatefilename
settingsfile               = os.path.join(WurmCommon.prefsdir, "settings.wurm.xml")
iconfile                   = os.path.join(WurmCommon.origappldir, "WUUmain.ico")
wowTest                    = "WoWTest"

# Used for PTR support
usePTR                     = False
wowDirOrig                 = ""
wowBackupDirOrig           = ""

# Used for local settings (That is, multiple installations of WUU not sharing their settings)
useLocalSettings           = False
if os.path.exists(os.path.join(WurmCommon.origappldir, "overridesettings.wurm.xml")):
    settingsfile           = os.path.join(WurmCommon.origappldir, "overridesettings.wurm.xml")
    useLocalSettings       = True

# other variables
totaltasks = 0 # Count of how many tasks queued
callbackcount = 0 # Count of how many callbacks expected
selectedaddon = None # Addon whose info is being displayed
# used to check Addon type
typeManualDl = ["CurseGaming", "WoWAce", "WoWAceClone", "WoWUI"]

# HTML strings used to display information in the Right Hand Side Panel
rPHTMLTop = """<html><body><center>
<table width="100%%" cellspacing="0" bgcolor="#CCCCFF" cellpadding="3" border="1">
<tr><td align="center">"""

rPHTMLMid = """</td></tr></table>
<table width="100%%" cellspacing="1" cellpadding="2" border="0">"""

rPHTMLBot = """%(additionalHTML)s</table></center></body></html>"""

# Shown when program starts
# rightPanelHTMLDefault fields:
# text
# info
rightPanelHTMLDefault = rPHTMLTop + """%(text)s</td></tr></table></center><p>%(info)s</p></body></html>"""

# rightPanelHTML fields:
# title
# note
# author
# deps
# optdeps
# additionalHTML
# Added patch 1866042
rightPanelHTML = rPHTMLTop + """<h3>%(title)s</h3><br/><i>%(note)s</i>""" + rPHTMLMid + """
<tr><td valign="top">Author:</td><td>%(author)s</td></tr>
<tr><td valign="top">Deps:</td><td>%(deps)s</td></tr>
<tr><td valign="top">OptDeps:</td><td>%(optdeps)s</td></tr>"""  + rPHTMLBot

# rightPanelHTMLNoInfo fields:
# addonname
# text
# additionalHTML
rightPanelHTMLNoInfo = rPHTMLTop + """<h3>%(addonname)s</h3><br/><i>%(text)s</i>""" + rPHTMLMid + rPHTMLBot

# HTML for the Parent/Child & Related Addons, Website & Changelog links & Dependency entries
childHTML     = '<tr><td>Children:</td><td>%s</td></tr>'
parentHTML    = '<tr><td>Parent:</td><td>%s</td></tr>'
relatedHTML   = '<tr><td valign="top">Related:</td><td>%s</td></tr>'
websiteHTML   = '<tr><td>Website:</td><td><a href="%s" target="_blank">link</a></td></tr>\n'
changelogHTML = '<tr><td>Changelog:</td><td><a href="%s" target="_blank">local</a></td></tr>\n'
depHTML       = "<font color=\"red\">%s</font>"


# Define event for thread communication
wxEVT_THREAD_COMMS = wx.NewEventType()

class ThreadCommsEvent(wx.PyEvent):
    """Simple event to carry thread message data."""
    def __init__(self, func, args, kwargs):
        """Init Thread Comms Event."""
        tracer.log(WurmCommon.DEBUG5, "ThreadCommsEvent - __init__")
        
        wx.PyEvent.__init__(self)
        self.SetEventType(wxEVT_THREAD_COMMS)
        self.func   = func
        self.args   = args
        self.kwargs = kwargs
    


STOP = object()

class WurmQUU(object):
    """ Class to represent a queue over non-blocking tasks to do, to stop actions from conflicting """
    
    # Enums used in this class:
    tasktypes = ["local", "remote"] # not used, but in theory local tasks could be performed before all remote tasks
    taskcommands = ["version", "update", "delete", "restore", "load", "install", "smartupdate", "updlocalver"]
    # "version" is version check
    # "update" is a "blind" update (regardless of if it's needed)
    # "smartupdate" updates only if Wurm finds it necessary (missing or older local version)
    # "delete" deletes an addon (local)
    # "load" loads addon settings (local)
    # "restore" restores an addon from backup (local)
    # "install" installs a addon
    # "updlocalver" sets the version of the local addon to whichever is the newest online version (i.e. was updated manually)
    
    def __init__(self):
        """ Sets up queue, locks and thread pool """
        tracer.debug("WurmQUU - __init__")
        
        import Queue
        
        self.queue = Queue.Queue()
        self.pool  = []
        
        for _ in range(10):
            self.pool.append(threading.Thread(target=self.threadloop))
        
        for thread in self.pool:
            thread.start()
        
        # Locks for Addontypes
        for addontype in WurmCommon.addontypes:
            if addontype[0] != "[": # only "real" sites
                WurmCommon.wurmlock[addontype] = threading.Lock()
        
        # Locks for Modules
        WurmCommon.wurmlock["WUU"]         = threading.Lock()
        WurmCommon.wurmlock["Wurm1"]       = threading.Lock()
        WurmCommon.wurmlock["Wurm2"]       = threading.Lock()
        WurmCommon.wurmlock["WurmCommon1"] = threading.Lock()
        WurmCommon.wurmlock["WurmCommon2"] = threading.Lock()
        WurmCommon.wurmlock["WurmUnpack"]  = threading.Lock()
    
    
    def do(self, *args, **kwargs):
        """ Adds a task to the queue """
        tracer.log(WurmCommon.DEBUG5, "WurmQUU - do: %s" % (str(args)))
        
        job = args[0]
        acttype, command, addon, callback = job
        
        if acttype not in self.tasktypes:
            WurmCommon.outError("Unknown task type %s" % (acttype))
        elif command not in self.taskcommands:
            WurmCommon.outError("Unknown command %s" % (command))
        else:
            self.queue.put((args, kwargs))
    
    
    def addMultiTask(self, acttype, command, addons, callback=None):
        """ Adds multiple tasks to the queue
        acttype can be "local" or "remote" (isn't used for anything yet)
        command can be one of ["version", "update" or "delete"]
        addons is a list of addons to perform the action on
        callback is a function to call when the task is done
        """
        tracer.debug("WurmQUU - addMultiTask")
        
        global totaltasks, callbackcount, acedepcheck
        
        callbackcount += len(addons)
        totaltasks += float(callbackcount)
        WurmCommon.outDebug("aMT: %d, %d, %s" % (totaltasks, callbackcount, addons))
        
        for addon in addons:
            job = (acttype, command, addon, callback)
            self.do(job, {})
            # # flag when a WoWAce addon has been changed
            # if not command == "version":
            #     if WurmCommon.addonlist.getAtype(addon) == "WoWAce":
            #         acedepcheck = True
    
    
    def stop(self):
        """ Stops the queue """
        tracer.debug("WurmQUU - stop: %s/%s" % (threading.activeCount(), self.queue.qsize()))
        
        # flush queue
        try:
            while True:
                self.queue.get_nowait()
                # self.queue.get(timeout=1)
        except:
            pass
        
        self.queue.put(STOP)
        for thread in self.pool:
            if thread.isAlive():
                thread.join()
    
    
    def threadloop(self):
        """ Execute the queue """
        tracer.log(WurmCommon.DEBUG5, "WurmQUU - threadloop: [%s]" % (threading.currentThread().getName()))
        
        while True:
            args = self.queue.get()
            tracer.log(WurmCommon.DEBUG7, "threadloop: %s" % (str(args)))
            if args is STOP:
                self.queue.put(STOP)
                break
            self._do(*args[0], **args[1])
    
    
    def _do(self, *args, **kwargs):
        """"""
        tracer.log(WurmCommon.DEBUG7, "WurmQUU - _do: %s" % (str(args)))
        
        success = True
        job = args[0]
        acttype, command, addon, callback = job
        
        # WurmCommon.outDebug("_do :[%s]" % (addon))
        
        try:
            if command == "version":
                if addon in WurmCommon.addons:
                    success = WurmCommon.addons[addon].sync()
                else:
                    WurmCommon.outError("Addon %s is not in the list; could not check version" % (addon))
            
            elif command == "update":
                if addon in WurmCommon.addons:
                    success = WurmCommon.addons[addon].updateMod()
                else:
                    WurmCommon.outError("Addon %s is not in the list; could not update" % (addon))
            
            elif command == "smartupdate":
                if addon in WurmCommon.addons:
                    success = WurmCommon.addons[addon].smartUpdateMod()
                else:
                    pass # just means a [Ignore] or [Related] addon was in the list
                    #WurmCommon.outError("Addon %s is not in the list; could not update" % (addon))
            
            elif command == "updlocalver":
                if addon in WurmCommon.addons:
                    success = WurmCommon.addons[addon].setLocalModVersion(WurmCommon.addons[addon].getOnlineModVersion())
                else:
                    pass # just means a [Ignore] or [Related] addon was in the list
                    #WurmCommon.outError("Addon %s is not in the list; could not update" % (addon))
            
            elif command == "delete":
                WurmCommon.DeleteAddons(addon, cleansettings=True)
            
            elif command == "restore":
                success = WurmCommon.RestoreAddon(addon)
            
            # elif command == "load":
            #     # The addon variable contains the WurmUI instance
            #     wurmUI = addon
            #     wurmUI.OnLoad(None)
            #
            elif command == "install":
                success = WurmCommon.InstallAddon(addon)
        
        except Exception, details:
            logger.exception("Thread Error: %s, %s" % (job, str(details)))
            # raise
            success = False
        
        # if it's set call the callback
        if callback:
            try:
                callback(addon, command, status=success)
            except Exception, details:
                logger.exception("Thread Error, Callback failed: %s, %s, %s" % (addon, command, str(details)))
                raise
    


class CustomStatusBar(wx.StatusBar):
    """Custom Status Bar with a Text String and 2 progress gauges"""
    def __init__(self, parent):
        """Init Status Bar"""
        tracer.log(WurmCommon.DEBUG5, "CustomStatusBar - __init__")
        
        wx.StatusBar.__init__(self, parent, -1)
        
        # This status bar has three fields
        self.SetFieldsCount(3)
        # Sets the three fields to be relative widths to each other.
        self.SetStatusWidths([-4, -1, -1])
        self.sizeChanged = False
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        
        # Field 0 ... just text
        self.SetStatusText("A Custom StatusBar...", 0)
        
        # This will fall into field 1 (the second field)
        self.pg = wx.Gauge(self, -1, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self.pg.SetRange(100)
        
        # This will fall into field 2 (the third field)
        self.pg2 = wx.Gauge(self, -1, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self.pg2.SetRange(100)
        
        # set the initial position of the gauge
        self.Reposition()
    
    
    def OnSize(self, evt):
        self.Reposition()  # for normal size events
        
        # Set a flag so the idle time handler will also do the repositioning.
        # It is done this way to get around a buglet where GetFieldRect is not
        # accurate during the EVT_SIZE resulting from a frame maximize.
        self.sizeChanged = True
    
    
    def OnIdle(self, evt):
        if self.sizeChanged:
            self.Reposition()
    
    
    # reposition the checkbox
    def Reposition(self):
        rect = self.GetFieldRect(1)
        self.pg.SetPosition((rect.x+2, rect.y+2))
        self.pg.SetSize((rect.width-4, rect.height-4))
        rect2 = self.GetFieldRect(2)
        self.pg2.SetPosition((rect2.x+2, rect2.y+2))
        self.pg2.SetSize((rect2.width-4, rect2.height-4))
        self.sizeChanged = False
    


class WurmUI(wx.Frame, listmix.ColumnSorterMixin, WurmUtility.TypeAheadListCtrlMixin):
    def __init__(self, title):
        """ Set up the UI """
        tracer.debug("WurmUI - __init__")
        
        self.title        = title
        self.Visible      = False
        self.settings     = {}
        
        # used to manage positioning in the List Control
        self.topItem      = 1
        self.perPageCount = 0
        
        # We'll use a pool of named IDs for the different UI elements
        # Relevant methods:
        # self._getID("name") will return a new or existing ID
        self.idpool = {}
        self.idpoolindex = 0 # used/incremented for anonymous IDs - will get "wuuctl%d" as name
        
        # Create the Frame
        wx.Frame.__init__(self, None, title=self.title, size=(800, 500))
        
        # Load Language Support
        WurmCommon.loadLanguages()
        
        # Load the saved settings
        self.loadUISettings()
        
        # Bind the Thread Comms event to its handler
        self.Connect(wx.ID_ANY, wx.ID_ANY, wxEVT_THREAD_COMMS, self.OnThreadComms)
       
        # Internal queue for handling addon related tasks
        if int(self._getSetting(":UseThreads", 0)):
            self.quu = WurmQUU()
        
        # Store references for use in other modules
        WurmCommon.Wurm = Wurm
        
        # Create the UI
        self.CreateUI()
        
        # Set the callbacks so that output is displayed in the Event Log panel
        WurmCommon.cbOutError         = self.logError
        WurmCommon.cbOutMessage       = self.logMessage
        WurmCommon.cbOutWarning       = self.logWarning
        WurmCommon.cbOutDebug         = self.logDebug
        WurmCommon.cbOutStatus        = self.showStatus
        WurmCommon.cbProgressPercent  = self.updateProgress
        WurmCommon.cbResetProgress    = self.resetProgress
        WurmCommon.cbProgressPercent2 = self.updateProgress2
        WurmCommon.cbResetProgress2   = self.resetProgress2
        
        # Setup timer to clear Status Messages after 45 seconds
        self.clearStatusTimer   = wx.Timer(self, self._getID("statustimer"))
        self.clearStatusTimeout = 45 * 1000 # milliseconds
        # Bind the Timer event to its handler along with the timer object
        self.Bind(wx.EVT_TIMER, self.OnClearStatusTimer, self.clearStatusTimer)
        
        # Create an instance of the AddonList dictionary
        WurmCommon.addonlist = WurmCommon.AddonList()
        
        # If Autoloading option is true then Autoload the Addons into the list
        if int(self._getSetting("Autoload", 1)):
            WurmCommon.outMessage(_("Autoloading settings"))
            self.OnLoad(None)
        
        # Check to see if the WUU site is available for the version checks
        WurmCommon.checkWebsite(masterVersion) # Using the version file instead of index.php as check, to make the request quick and tiny
        
        # Check for Beta Version if required
        if int(self._getSetting("CheckWUUVersionBeta", 0)):
            self.checkOnlineBetaVersion()
        
        # Check WUU Version
        if int(self._getSetting("CheckWUUVersion", 1)):
            self.checkOnlineVersion()
            # Check for updated regular expressions and templates
            self.checkOnlineRegexps()
            self.checkOnlineTemplates()
        
        # Load the templates
        try:
            WurmCommon.loadTemplates()
        except ExpatError:
            # Local file is corrupted
            try:
                WurmCommon.downloadFile(templateUrl, templateFile)
                WurmCommon.loadTemplates() # try to force a download
            except Exception, details:
                logger.error("Template file is broken, can't download new; giving up [%s]" % (str(details)))
        
        # Logs external libs, etc. - see method for details
        self.logCapabilities()
        
        # All done, so tell the User we're ready to go
        WurmCommon.outStatus(_("--- READY ---"))
        self.log(_("--- READY ---"), wx.GREEN)
        logger.info("All setup done, ready to go")
        
        self.Visible = True
    
    
    def _addonToIndex(self, addon):
        """ Returns the correct index for the addon """
        tracer.log(WurmCommon.DEBUG5, "WurmUI - _addonToIndex")
        
        # find new idx
        newidx = self.lc.FindItem(-1, addon)
        
        if newidx == -1:
            # Scanning thru the list "the slow way" as a last measure (necessary sometimes)
            
            while True:
                newidx = self.lc.GetNextItem(newidx, wx.LIST_NEXT_ALL)
                if not newidx == -1:
                    fitem = self.lc.GetItem(newidx, 0).GetText()
                    if fitem == addon:
                        break
                else:
                    newidx = None
                    break
        
        return newidx
    
    
    def _applyNewSettings(self, settings):
        """ Applies new settings, and handles significant changes, if any """
        tracer.debug("WurmUI - _applyNewSettings")
        
        changed = []
        
        for s in settings:
            if s not in self.settings:
                WurmCommon.outDebug("New setting %s added" % (s))
                self.settings[s] = settings[s]
                changed.append(s)
            elif self.settings[s] != settings[s]:
                WurmCommon.outDebug("Setting %s changed from %s to %s" % (s, self.settings[s], settings[s]))
                self.settings[s] = settings[s]
                changed.append(s)
        
        # Step 1: iterate and check all
        for c in changed:
            if ":" in c: # this is a site specific setting, mirror it in Wurm
                WurmCommon.outDebug("Cascading setting %s to Wurm" % (c))
                WurmCommon.globalsettings[c] = self.settings[c]
            if "RGB" in c: # a colour has been changed
                lcColour[c[:-3]] = self.settings[c]
        
        # Step 2: check specifics
        if "WoWDir" in changed or "BackupDir" in changed:
            WurmCommon.outDebug("WoWDir and/or BackupDir changed - reinitializing Wurm")
            WurmCommon.directories["wow"]    = self.settings["WoWDir"]
            WurmCommon.directories["backup"] = self.settings["BackupDir"]
            Wurm.initialize()
        
        if ":UseThreads" in changed and int(self._getSetting(":UseThreads", 0)):
            # we need to reinitialize WurmQUU
            self.quu = WurmQUU()
        
        if ":SocketTimeout" in changed:
            try:
                WurmCommon.setUserAgent(wuuversion) # setting the user agent also sets the socket timeout
            except:
                pass # We don't care if it's not successfully set
        
        # If Debug is wanted then turn it on, otherwise turn it off
        if "Debug2Log" in changed:
            if self.settings["Debug2Log"]:
                # if a developer is testing
                if os.path.isdir(os.path.join(WurmCommon.appldir, ".svn")) or \
                   os.path.isdir(os.path.join(WurmCommon.appldir, ".git")):
                    logger.setLevel(WurmCommon.DEBUG5)
                    tracer.setLevel(WurmCommon.DEBUG5)
                else:
                    logger.setLevel(logging.DEBUG)
                    tracer.setLevel(logging.DEBUG)
            else:
                logger.setLevel(logging.INFO)
                tracer.setLevel(logging.INFO)
        
        # Step 3. If the WoW directory has changed then clear the Addonslist etc and rescan the 'New' Addons directory
        if "WoWDir" in changed:
            if os.path.exists(Wurm.addondatafile):
                self.OnLoad(None)
            else:
                WurmCommon.addonlist = WurmCommon.AddonList()
                WurmCommon.toclist   = {}
                WurmCommon.addons    = {}
                self.OnScan(None)
        
        self.saveUISettings()
    
    
    def _boolToStr(self, vbool):
        """"""
        tracer.log(WurmCommon.DEBUG5, "WurmUI - _boolToStr")
        
        if vbool:
            return "Y"
        else:
            return "N"
    
    
    def _displayAddonTotal(self):
        """Display the total number of Addons in the RHS panel"""
        tracer.debug("WurmUI - _displayAddonTotal")
        
        global selectedaddon
        
        info = _('%(num)d Addons loaded') % {'num': len(WurmCommon.addonlist)}
        self.p2.SetPage(rightPanelHTMLDefault % {'text': _("Welcome to WUU"), 'info': info})
        
        selectedaddon = None
    
    
    def _getID(self, name=None):
        """ Returns a unique wx ID if the name is new, otherwise returns the ID associated with the name """
        tracer.log(WurmCommon.DEBUG5, "WurmUI - _getID")
        
        if not name: # anonymous controls
            self.idpoolindex += 1
            name = "wuuctl%04d" % (self.idpoolindex)
        
        return self.idpool.setdefault(name, wx.NewId())
    
    
    def _getLcItems(self, state="SELECTED", inAddons=False, hasBackup=False, hasUpdate=False, getRelated=False):
        """ Get the specified entries from the List Control """
        tracer.debug("WurmUI - _getLcItems")
        
        if state == "ALL":
            lcState = wx.LIST_STATE_DONTCARE
        elif state == "SELECTED":
            lcState = wx.LIST_STATE_SELECTED
        
        selList = []
        relList = []
        curitem = -1
        
        while True:
            curitem = self.lc.GetNextItem(curitem, wx.LIST_NEXT_ALL, lcState)
            if not curitem == -1:
                fitem = self.lc.GetItem(curitem, 0).GetText()
                if inAddons:
                    if fitem in WurmCommon.addons:
                        selList.append(fitem)
                elif hasBackup:
                    if fitem in WurmCommon.addons and WurmCommon.addons[fitem].getBackupStatus():
                        selList.append(fitem)
                elif hasUpdate:
                    upd = self.lc.GetItem(curitem, 5).GetText()
                    if "Y" in upd or "E" in upd: # online version is newer, update!
                        selList.append(fitem)
                    elif fitem in WurmCommon.addons:
                        if WurmCommon.addons[fitem].localversion < 0: # unknown local version, update!
                            selList.append(fitem)
                else:
                    selList.append(fitem)
                # check for related Addons if required
                if getRelated:
                    relList = WurmCommon.findAllRelated(fitem)
            else:
                break
        
        if getRelated:
            return selList, relList
        else:
            return selList
    
    
    def _getSetting(self, setting, default=False):
        """"""
        tracer.log(WurmCommon.DEBUG5, "WurmUI - _getSetting")
        
        return self.settings.setdefault(setting, default)
    
    
    def _htmlDepList(self, deplist):
        """"""
        tracer.log(WurmCommon.DEBUG5, "WurmUI - _htmlDepList")
        
        if not deplist:
            return "<i>None</i>"
        
        html = []
        for d in deplist:
            if WurmCommon.checkDeps(d):
                html.append(d)
            else:
                html.append(depHTML % (d))
        
        return ", ".join(html)
    
    
    def _queueCallback(self, addon, command, status=True):
        """ Catch-all callback method for WurmQUU """
        tracer.debug("WurmUI - _queueCallback: %s, %s, %s" % (addon, command, status))
        
        global totaltasks, callbackcount
        
        if threading.currentThread().getName() != "MainThread":
            WurmCommon.wurmlock["WUU"].acquire()
        
        try:
            try:
                # Decrement the callback count
                # WurmCommon.outDebug("_qTT: %d, _qC: %d, _tC: %d" % (totaltasks, callbackcount, threading.activeCount()))
                callbackcount -= 1
                if totaltasks > 1:
                    WurmCommon.outProgressPercent2(callbackcount/totaltasks) # show how we're getting on
                
                # Don't try to update the List Control for a deleted or installed addon
                if not command in ["delete", "install"]:
                    # Update the Addon entry in the List Control
                    wx.PostEvent(self, ThreadCommsEvent(self._quickUpdateAddonList, (addon,), {'updtype': command}))
                
                # Do these actions if not a deletion or version check
                if not command in ["delete", "version"]:
                    # Refresh the Addon entry's TOC information
                    Wurm.refreshSingleAddon(addon, toconly=True)
                    # Check to see if this addon's info is being displayed, if so then refresh it
                    if addon == selectedaddon:
                        wx.PostEvent(self, ThreadCommsEvent(self.RefreshInfoPanel, (addon,), {}))
                
                 # format status message
                if command == "version":
                    cmd = "version check"
                elif command == "updlocalver":
                    cmd = "local version update"
                else:
                    cmd = command
                
                if status == True:
                    if cmd in ["version check", "install"]:
                        cmd = cmd + "e"
                    outcome = "d successfully"
                else:
                    outcome = " was unsuccessful"
                
                WurmCommon.outStatus(_("%(addon)s %(cmd)s%(outcome)s") % {'addon': addon, 'cmd': cmd, 'outcome': outcome})
                
                # Display final Status Message
                if callbackcount == 0:
                    msg = ""
                    if command == "version":
                        msg = _("All Addons version checked")
                    elif command == "install":
                        msg = _("All Addons installed")
                    elif command == "updlocalver" or command == "fileupdate":
                        msg = _("All Addons updated")
                    elif command == "smartupdate":
                        msg = "%s (%s)" % (_("All Addons updated"), _("only if update was needed"))
                    else:
                        msg = _("All Addons %(cmd)sd") % {'cmd': command}
                    if command in ["delete", "install"]:
                        wx.PostEvent(self, ThreadCommsEvent(self.RefreshAddonList, (), {'count': True}))
                    
                    if not command == "version":
                        # redo the dependencies list
                        WurmCommon.depdict = {}
                        WurmCommon.deplist = []
                        wx.PostEvent(self, ThreadCommsEvent(Wurm.scanForDeps, (None,), {}))
                    WurmCommon.outStatus(msg)
                    WurmCommon.resetProgress()
                    WurmCommon.resetProgress2()
                    totaltasks = 0 # reset totaltasks value
            except UnicodeWarning, details:
                logger.exception("UnicodeError: [%s], %s" % (addon, str(details)))
                WurmCommon.outError("_qC - UnicodeError for addon: [%s]" % (addon))
            except Exception, details:
                logger.exception("Error during callback: %s, %s, %s" % (addon, command, str(details)))
                raise
        finally:
            if threading.currentThread().getName() != "MainThread":
                WurmCommon.wurmlock["WUU"].release()
    
    
    def _quickUpdateAddonList(self, addon, idx=0, updtype=None, fname=None, atype=None):
        """ Updates the list with new information without rebuilding the entire list, This is a consolidation of the old _quickChangeAddon, _quickSetNewAddonVersion & AddAddon functions """
        tracer.log(WurmCommon.DEBUG5, "WurmUI - _quickUpdateAddonList: %s, %s, %s, %s, %s" % (addon, idx, updtype, fname, atype))
        
        aType = atype or WurmCommon.addonlist.getAtype(addon)
        fName = fname or WurmCommon.addonlist.getFname(addon)
        
        if updtype != 'add':
            if addon in WurmCommon.addons:
# We used to assume the index delivered was OK, but threading might make the index invalid before this code is called
# The next two lines are "disabled" now.
                # ix = idx
# If the index doesn't match the addon due to a sort, find the new index
#                if self.lc.self.lc.GetItem(ix, 0).GetText() != addon:
                ix = self._addonToIndex(addon)
                if ix is None:
                    WurmCommon.outError("Can't find %s in the Addon list control" % (addon))
                    return False
            else:
                return False
            
            data = self.lc.GetItemData(ix)
        
        if updtype == 'version':
            oldmap = self.itemDataMap[data]
        
        elif updtype in ['restore', 'update', 'smartupdate', 'updlocalver']:
            self.lc.SetStringItem(ix, 1, aType)
            self.lc.SetStringItem(ix, 2, fName)
            
            # If addontype is one that shouldn't be displayed then return False
            # so that it will be removed from the List Control by the calling function
            if aType == "[Dummy]" and int(self._getSetting("HideDummy", 0)) or \
               aType == "[Ignore]" and int(self._getSetting("HideIgnored", 0)) or \
               aType == "[Outdated]" and int(self._getSetting("HideOutdated", 0)) or \
               aType == "[Related]" and int(self._getSetting("HideRelated", 0)):
                return False
        
        elif updtype == 'add':
            (fName, lName, siteId, aType) = WurmCommon.addonlist.getSome(addon)
            num_items                     = self.lc.GetItemCount()
            ix                            = self.lc.InsertStringItem(num_items, lName)
            data                          = WUUDialogs._listid(lName)
            
            self.lc.SetItemData(ix, data)
            self.lc.SetStringItem(ix, 1, aType)
            self.lc.SetStringItem(ix, 2, fName)
        
        if addon in WurmCommon.addons:
            localver        = WurmCommon.addons[addon].localversion
            onlinever       = WurmCommon.addons[addon].onlineversion
            wasembed        = WurmCommon.addons[addon].wasembedonly
            updateava, diff = WurmCommon.addons[addon].updateAvailable()
            restoreava      = WurmCommon.addons[addon].getBackupStatus()
            toc             = WurmCommon.toclist.get(addon)
            tocver          = ""
            if toc != None:
                tocver = str(toc.getInterfaceVersion())
            
            if updtype != 'version':
                updated  = WurmCommon.addons[addon].updated
                wasembed = WurmCommon.addons[addon].wasembedonly
            else:
                updated  = None
                wasembed = None
            
            self.lc.SetStringItem(ix, 3, self._verToStr(localver))
            self.lc.SetStringItem(ix, 4, self._verToStr(onlinever))
            
            if updated and wasembed:
                updval = 'UE'
            elif updated:
                updval = 'U'
            elif updateava and diff != 0 and diff < 1:
                updval = 'E'
            else:
                updval = (self._boolToStr(updateava) == "Y" and "Y" or "-")
            self.lc.SetStringItem(ix, 5, updval)
            
            # New in 1.7: TOC version if available
            self.lc.SetStringItem(ix, 6, tocver)
            
            self.lc.SetStringItem(ix, 7, self._boolToStr(restoreava))
            
            if updateava:
                self.lc.SetItemBackgroundColour(ix, lcColour["Pending"])
            elif localver < 0 and aType != "Child":
                self.lc.SetItemBackgroundColour(ix, lcColour["Unknown"])
            elif updated:
                self.lc.SetItemBackgroundColour(ix, lcColour["Installed"])
            else:
                self.lc.SetItemBackgroundColour(ix, wx.WHITE)
            
            if updtype == 'version':
                self.itemDataMap[data] = (oldmap[0], oldmap[1], oldmap[2], localver, onlinever, updval, tocver, restoreava)
            else:
                self.itemDataMap[data] = (addon.upper(), aType, fName, localver, onlinever, updval, tocver, restoreava)
        
        else:
            if updtype == 'version':
                self.itemDataMap[data] = (oldmap[0], oldmap[1], oldmap[2], "", "", "", "", "")
            else:
                self.itemDataMap[data] = (addon.upper(), aType, fName, "", "", "", "", "")
            
            if addon == WurmCommon.newaddon:
                self.lc.SetItemBackgroundColour(ix, lcColour["New"])
            elif updtype != 'version' and aType == "[Outdated]":
                self.lc.SetItemBackgroundColour(ix, lcColour["Outdated"])
            elif WurmCommon.addonlist.getFlag(addon, "missing"):
                self.lc.SetItemBackgroundColour(ix, lcColour["Missing"])
            else:
                self.lc.SetItemBackgroundColour(ix, wx.WHITE)
        
        return True
    
    
    def _showAddon(self):
        """ Position the specified Addon towards the middle of the List Control"""
        tracer.debug("WurmUI - _showAddon")
        
        # move the top item to the top of the list control
        # the EnsureVisible function puts the entry at the bottom
        # so we add the number of lines in the list control -1 to the index
        idx = 0
        if self.topItem in WurmCommon.addonlist:
            idx = self._addonToIndex(self.topItem)
            if idx:
                idx += self.lc.GetCountPerPage() - 1
            else:
                idx = 0
        
        # if idx is beyond the end of the list, move it to the end - 1
        # otherwise an error occurs
        if idx > len(self.itemDataMap):
            idx = len(self.itemDataMap) - 1
        
        WurmCommon.outDebug("_showAddon, index, total: %s, %s" % (idx, len(self.itemDataMap)))
        self.lc.EnsureVisible(idx)
    
    
    def _verToStr(self, ver):
        """"""
        tracer.log(WurmCommon.DEBUG5, "WurmUI - _verToStr")
        
        if ver < 0:
            return "?"
        else:
            if isinstance(ver, str):
                return ver
            else:
                return "%d" % (ver)
    
    
    def checkOnlineBetaVersion(self):
        """"""
        tracer.debug("WurmUI - checkOnlineBetaVersion")
        
        if not WurmCommon.isAvailable["WUUsite"]:
            WurmCommon.outWarning(_("WUU website marked as not available, skipping beta version check"))
            return False
        
        try:
            ver = WurmCommon.downloadPage(masterBetaVersion, compress=False).strip() # no need to invoke overhead of compression on a 8 byte file
            self.resetProgress()
            WurmCommon.outWarning(_("Online beta version of WUU: %(ver)s") % {'ver': ver})
            (omajor,ominor,orev) = [int(x) for x in ver.split(".")]
            (lmajor,lminor,lrev) = [int(x) for x in wuuversion.split(".")]
            if orev > lrev: # revision is constantly increasing, so it's the only part needed to check
                if int(self._getSetting("AutoUpdate", 1)) and Wurm.canAutoUpdate:
                    msg = wx.MessageDialog(self, _("Beta version %(ver)s of WUU is available from %(site)s\nDownload and install automatically\n(updates are RSA/Blowfish-signed)?") % {'ver': ver, 'site': WurmCommon.wuusite}, _("A new BETA version is available!"), style=wx.YES_NO|wx.ICON_INFORMATION)
                    answer = msg.ShowModal()
                    msg.Destroy()
                    
                    if answer == wx.ID_YES:
                        dlg = WurmProgress("WUU Beta Update", _("Download Progress"))
                        WurmCommon.cbProgressPercent = dlg.updateProgress # To disable progress bar updates
                        if not Wurm.updateWUU(ver, True):
                            WurmCommon.cbProgressPercent = self.updateProgress # reset the progress bar to the internal
                            msg = wx.MessageDialog(self, _("Update failed, check WUU.log for details"), _("WUU Beta Update Unsuccessful"), style=wx.OK|wx.ICON_WARNING)
                            msg.ShowModal()
                            msg.Destroy()
                        else: # Everything's OK :D
                            msg = wx.MessageDialog(self, _("Update successful, please restart WUU now!"), _("WUU Beta Update Successful"), style=wx.OK|wx.ICON_INFORMATION)
                            msg.ShowModal()
                            msg.Destroy()
                            sys.exit(0)
                        dlg.Destroy()
                else:
                    msg = wx.MessageDialog(self, _("Beta version %(ver)s of WUU is available from %(site)s\nDo you want to open the page in a new browser window?") % {'ver': ver, 'site': WurmCommon.wuusite}, _("A new BETA version is available!"), style=wx.YES_NO|wx.ICON_INFORMATION)
                    answer = msg.ShowModal()
                    msg.Destroy()
                    
                    if answer == wx.ID_YES:
                        webbrowser.open(WurmCommon.wuudownload)
        
        except Exception, details:
            logger.exception(_("Error: Could not check online beta version: %(dets)s") % {'dets': str(details)})
    
    
    def checkOnlineRegexps(self, event=None): # event is just there to use this as a menu handler too
        """ Downloads the online regexp list, but only if it's newer (or version check fails) """
        tracer.debug("WurmUI - checkOnlineRegexps")
        
        if not WurmCommon.isAvailable["WUUsite"]:
            WurmCommon.outWarning(_("WUU website marked as not available, skipping regexp check"))
            return False
        
        needsUpdate = False
        msg = (_("Checking for new site regexps"))
        WurmCommon.outMessage(msg)
        WurmCommon.outStatus(msg)
        try:
            try:
                onlineversion = WurmCommon.downloadPage(regexpVersion, compress=False)
            except Exception, details:
                WurmCommon.outWarning(_("Could not download regexp version file - aborting (Reason: %(dets)s)") % {'dets': str(details)})
                return False
        finally:
            self.resetProgress()
        
        try:
            localversion  = WurmCommon.getListVersionFromFile(regexpLocalVersionFile)
            needsUpdate   = onlineversion > localversion
        except Exception, details:
            WurmCommon.outError("Checking of version failed - assuming update needed (Reason: %s)" % (str(details)))
            needsUpdate = True
        
        if needsUpdate:
            try:
                try:
                    WurmCommon.downloadFile(regexpUrl, regexpFile)
                    WurmCommon.downloadFile(regexpVersion, regexpLocalVersionFile) # Cheating again :P
                    msg = (_("Downloaded new site regexps"))
                    WurmCommon.outMessage(msg)
                    WurmCommon.outStatus(msg)
                    WurmCommon.loadRegexps()
                except Exception, details:
                    WurmCommon.outError("Could not download regexp list: %s" % (str(details)))
                    return False
            finally:
                self.resetProgress()
        else:
            WurmCommon.outMessage(_("Already up to date"))
        
        return True
    
    
    def checkOnlineTemplates(self, event=None): # event is just there to use this as a menu handler too
        """ Downloads the online templates list, but only if it's newer (or version check fails) - direct copy of checkOnlineRegexps"""
        tracer.debug("WurmUI - checkOnlineTemplates")
        
        if not WurmCommon.isAvailable["WUUsite"]:
            WurmCommon.outWarning(_("WUU website marked as not available, skipping template check"))
            return False
        
        needsUpdate = False
        msg = (_("Checking for new site templates"))
        WurmCommon.outMessage(msg)
        WurmCommon.outStatus(msg)
        try:
            try:
                onlineversion = WurmCommon.downloadPage(templateVersion, compress=False)
            except Exception, details:
                WurmCommon.outWarning(_("Could not download template version file - aborting (Reason: %(dets)s)") % {'dets': str(details)})
                return False
        finally:
            self.resetProgress()
        
        try:
            localversion  = WurmCommon.getListVersionFromFile(templateLocalVersionFile)
            needsUpdate   = onlineversion > localversion
        except Exception, details:
            WurmCommon.outError("Checking of version failed - assuming update needed (Reason: %s)" % (str(details)))
            needsUpdate = True
        
        if needsUpdate:
            try:
                try:
                    WurmCommon.downloadFile(templateUrl, templateFile)
                    WurmCommon.downloadFile(templateVersion, templateLocalVersionFile) # Cheating again :P
                    msg = (_("Downloaded new site templates"))
                    WurmCommon.outMessage(msg)
                    WurmCommon.outStatus(msg)
                    WurmCommon.loadRegexps()
                except Exception, details:
                    WurmCommon.outError("Could not download template list: %s" % (str(details)))
                    return False
            finally:
                self.resetProgress()
        
        return True
    
    
    def checkOnlineVersion(self):
        """"""
        tracer.debug("WurmUI - checkOnlineVersion")
        
        if not WurmCommon.isAvailable["WUUsite"]:
            WurmCommon.outWarning(_("WUU website marked as not available, skipping version check"))
            return False
        
        try:
            ver = WurmCommon.downloadPage(masterVersion, compress=False).strip() # no need to invoke overhead of compression on a 8 byte file
            self.resetProgress()
            WurmCommon.outWarning(_("Online version of WUU: %(ver)s") % {'ver': ver})
            (omajor,ominor,orev) = [int(x) for x in ver.split(".")]
            try: # handle non numeric version number
                (lmajor,lminor,lrev) = [int(x) for x in wuuversion.split(".")]
            except:
                return False
            if orev > lrev: # revision is constantly increasing, so it's the only part needed to check
                if int(self._getSetting("AutoUpdate", 1)) and Wurm.canAutoUpdate:
                    msg = wx.MessageDialog(self, _("Version %(ver)s of WUU is available from %(site)s\nDownload and install automatically\n(updates are RSA/Blowfish-signed)?") % {'ver': ver, 'site': WurmCommon.wuusite}, _("A new version is available!"), style=wx.YES_NO|wx.ICON_INFORMATION)
                    answer = msg.ShowModal()
                    msg.Destroy()
                    
                    if answer == wx.ID_YES:
                        dlg = WurmProgress("WUU Update", _("Download Progress"))
                        WurmCommon.cbProgressPercent = dlg.updateProgress # To disable progress bar updates
                        if not Wurm.updateWUU(ver):
                            WurmCommon.cbProgressPercent = self.updateProgress # reset the progress bar to the internal
                            msg = wx.MessageDialog(self, _("Update failed, check WUU.log for details"), _("WUU Update Unsuccessful"), style=wx.OK|wx.ICON_WARNING)
                            msg.ShowModal()
                            msg.Destroy()
                        else: # Everything's OK :D
                            msg = wx.MessageDialog(self, _("Update successful, please restart WUU now!"), _("WUU Update Successful"), style=wx.OK|wx.ICON_INFORMATION)
                            msg.ShowModal()
                            msg.Destroy()
                            sys.exit(0)
                        dlg.Destroy()
                else:
                    msg = wx.MessageDialog(self, _("Version %(ver)s of WUU is available from %(site)s\nDo you want to open the page in a new browser window?") % {'ver': ver, 'site': WurmCommon.wuusite}, _("A new version is available!"), style=wx.YES_NO|wx.ICON_INFORMATION)
                    answer = msg.ShowModal()
                    msg.Destroy()
                    
                    if answer == wx.ID_YES:
                        webbrowser.open(WurmCommon.wuudownload)
        
        except Exception, details:
            logger.exception(_("Error: Could not check online version: %(dets)s") % {'dets': str(details)})
    
    
    def loadUISettings(self):
        """ Loads all the Application settings """
        tracer.debug("WurmUI - loadUISettings")
        
        global settingsfile, usePTR, wowDirOrig, wowBackupDirOrig, useLocalSettings
        
        WurmCommon.outMessage(_("Loading UI settings from %(sfile)s") % {'sfile': settingsfile})
        # Load XML file first
        ignoreset = (":ExtractLoD", "FrameWidth", "FrameHeight", ) # settings to skip (deprecated settings)
        
        hasoldsettings = False # keep track of whether this is a 1.0 or 1.5 file
        # (for backup purposes)
        
        # Process the settings file if it exists
        if os.path.exists(settingsfile):
            try:
                tree = ElementTree(file=settingsfile)
                settingslist = tree.find("wurmsettings")
                settings = settingslist.findall("setting")
                
                for se in settings:
                    name  = se.find("name").text.strip()
                    value = se.find("value").text.strip()
                    if len(name) > 0 and name not in ignoreset:
                        hasoldsettings = True # triggers a file backup
                        self.settings[name] = value
                        # WurmCommon.outDebug("Setting '%s' is '%s'" % (name, value))
                
                # Use new, shorter format ("better" XML - at least way shorter)
                options = settingslist.findall("option")
                for opt in options:
                    name = opt.attrib.get("name")
                    value = opt.text.strip()
                    if name and len(name) > 0 and name not in ignoreset:
                        self.settings[name.strip()] = value
                        # WurmCommon.outDebug("Setting '%s' is '%s' [1.5 format]" % (name, value))
            
            except Exception, details:
                logger.exception("settings.wurm.xml failed to load: %s" % (str(details)))
                raise
        
        # XML loaded, check specific settings
        WurmCommon.directories["backup"] = self._getSetting("BackupDir", False) # Force this to False if not set
        if WurmCommon.directories["backup"] != False and not os.path.exists(WurmCommon.directories["backup"]):
            WurmCommon.outWarning(_("Backup directory %(dir)s does not exist!") % {'dir': WurmCommon.directories["backup"]})
        # Prompt for the WoW directory if it isn't set, or doesn't exist
        if not "WoWDir" in self.settings or not os.path.exists(self.settings["WoWDir"]):
            wowdir = self.AskForWoWPath()
            if not wowdir:
                raise Exception, "No WoW directory specified, aborting run"
            else:
                self.settings["WoWDir"] = wowdir
                WurmCommon.directories["wow"] = wowdir
        else:
            WurmCommon.directories["wow"] = self.settings["WoWDir"]
        
        if not ":BrowserDownloadDir" in self.settings or not os.path.exists(self.settings[":BrowserDownloadDir"]):
            dlg = wx.DirDialog(self, _("Please select your default browser download directory (used for Curse updating)"), style=wx.DD_DEFAULT_STYLE)
            answer = dlg.ShowModal()
            dlg.Destroy()
            if answer == wx.ID_OK:
                self.settings[":BrowserDownloadDir"] = dlg.GetPath()
        
        if int(self._getSetting("PTRCheck", 1)): # Check to see if the Test Client is installed
            # If so then ask if the Test Realm Addons should be used
            if os.path.exists(os.path.join(WurmCommon.directories["wow"], wowTest)):
                msg = wx.MessageDialog(self, _("Manage PTR Addons ?"), _("Public Test Realm Addons"), style=wx.YES_NO|wx.NO_DEFAULT|wx.ICON_QUESTION)
                answer = msg.ShowModal()
                msg.Destroy()
                if answer == wx.ID_YES:
                    usePTR = True
        
        # If the Test Realm is chosen then change some directory entries, and change window title
        if usePTR:
            wowDirOrig                       = WurmCommon.directories["wow"]
            wowBackupDirOrig                 = WurmCommon.directories["backup"]
            WurmCommon.directories["wow"]    = os.path.join(WurmCommon.directories["wow"], wowTest)
            self.settings["WoWDir"]          = WurmCommon.directories["wow"]
            WurmCommon.directories["backup"] = False
            self.SetTitle("%(ptr)s  %(title)s  %(ptr)s" % {'ptr': "<<< PTR >>>",  'title': self.title})
        
        # If using local settings (overridesettings.wurm.xml), change window title
        if useLocalSettings:
            self.SetTitle("%(title)s %(locset)s" % {'locset': "[Local Settings]", 'title': self.title})
        
        if hasoldsettings:
            try:
                f_in = open(settingsfile, "rt")
                stext = f_in.read()
                f_in.close()
                WurmCommon.outDebug("Writing backup of old (pre-1.5) config to %s.bak" % (settingsfile))
                
                f_out = open("%s.bak" % (settingsfile), "wt")
                f_out.write(stext)
                f_out.close()
            except Exception, details:
                WurmCommon.outWarning(_("Could not backup settings file to %(sfile)s.bak: %(dets)s") % {'sfile': settingsfile, 'dets': str(details)})
        
        Wurm.initialize() # sets up the parameters related to the WoW dir
        
        # Fix settings after initialization if needed
        self.settings["BackupDir"] = WurmCommon.directories["backup"] # to ensure it's set to an actual directory, and not False
        
        # Set some defaults that aren't guaranteed to be invoked naturally
        self._getSetting(":UseWebsite", 1)
        self._getSetting(":PreserveNewline", 0)
        self._getSetting(":LangCode", "en") # default language to English
        self._getSetting(":UseThreads", 0) # default to 1.2 style threading
        self._getSetting("InstalledRGB", lcColour["Installed"])
        self._getSetting("MissingRGB", lcColour["Missing"])
        self._getSetting("PendingRGB", lcColour["Pending"])
        self._getSetting(":SocketTimeout", 10)
        self.settings["Debug2Log"] = 0 # force Debug mode to off
        
        # Mirror site specific settings in Wurm
        for c in self.settings:
            if ":" in c:
                WurmCommon.globalsettings[c] = self.settings[c]
        
        # Set language to use
        translator.setCurrent(self.settings[":LangCode"])
        
        # Handle the colour strings
        for c in ["InstalledRGB", "MissingRGB", "PendingRGB"]:
            # Convert them if they contain "rgb"
            if self.settings[c][:3] == "rgb":
                self.settings[c] = self.settings[c][3:]
            # Convert them if they are strings
            if type(self.settings[c]) == str:
                # Set the colour to use in the List Control
                lcColour[c[:-3]] = WurmCommon.str2tuple(self.settings[c])
    
    
    def log(self, message, fgcolor=wx.NullColor, bgcolor=wx.NullColor):
        """"""
        tracer.log(WurmCommon.DEBUG7, "WurmUI - log")
        
        self.logwindow.SetDefaultStyle(wx.TextAttr(fgcolor, bgcolor))
        
        output = "%s: %s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message)
        
        self.logwindow.AppendText(output)
        
        # position to the end of the displayed text
        lwGLP = self.logwindow.GetLastPosition()
        # print "lwGLP: [%s]" % (lwGLP)
        self.logwindow.ShowPosition(lwGLP)
        # self.logwindow.ShowPosition(lwGLP is not None and lwGLP or 0)
        
        try:
            # Yield so the display can be seen
            wx.Yield()
        except:
            pass # ignore Yield failure
    
    
    def logCapabilities(self):
        """ Checks what the current installation/environment is capable of (e.g. external programs/libraries),
        and reports to event log. Note that this only checks what the other WUU modules report, it does not
        check if a lib is suddenly available - WUU restart is needed for this to change. """
        
        tracer.debug("WurmUI - logCapabilities")
        
        cap_msg = [] # Features found, list of strings
        cap_opt = [] # Optional features not installed, list of strings
        
        # Load messages from current language
        featureava = _("Feature available")
        optlibmiss = _("Optional library missing")
        extprogava = _("External program available")
        extpromiss = _("Optional external program missing")
        # Self-updating
        if Wurm.canAutoUpdate:
            cap_msg.append("%s: %s %s" % (featureava, _("Automatic self-updating"), "(library: ezPyCrypto)"))
        else:
            cap_opt.append("%s: %s (%s)" % (optlibmiss, "ezPyCrypto", _("needed for automatic self-updating")))
        
        # 7-Zip
        if 'SevenZip' in dir(Wurm.WurmUnpack): # only if it's imported, on Windows platform
            if Wurm.WurmUnpack.SevenZip.isAvailable():
                cap_msg.append("%s: %s (%s: %s)" % (extprogava, "7-ZIP command line client", _("path"), Wurm.WurmUnpack.SevenZip.unpackerpath))
            else:
                cap_opt.append("%s: %s (%s - %s)" % (extpromiss, "7-ZIP command line client", "7z.exe", _("WUU searched path and common locations")))
        
        # SVN
        if Wurm.hasSVN:
            cap_msg.append("%s: %s (%s: %s)" % (extprogava, "SVN command line client", _("path"), Wurm.svn))
        else:
            cap_opt.append("%s: %s (%s - %s)" % (extpromiss, "SVN command line client", "svn(.exe)", _("WUU searched path and common locations")))
        
        # Git
        if Wurm.hasGit:
            cap_msg.append("%s: %s (%s: %s)" % (extprogava, "Git command line client", _("path"), Wurm.git))
        else:
            cap_opt.append("%s: %s (%s - %s)" % (extpromiss, "Git command line client", "git(.exe)", _("WUU searched path and common locations")))
        
        # Output sorted to log
        cap_msg.sort()
        cap_opt.sort()
        
        for msg in cap_msg:
            WurmCommon.outMessage(msg)
        
        for msg in cap_opt:
            WurmCommon.outWarning(msg)
    
    
    def logDebug(self, message):
        """"""
        tracer.log(WurmCommon.DEBUG7, "WurmUI - logDebug")
        
        logger.debug(message)
    
    
    def logError(self, message):
        """"""
        tracer.log(WurmCommon.DEBUG7, "WurmUI - logError")
        
        lw_msg = "(ERROR) %s" % (message)
        
        logger.error(message)
        
        if threading.currentThread().getName() == "MainThread":
            self.log(lw_msg, wx.RED)
        else:
            wx.PostEvent(self, ThreadCommsEvent(self.log, (lw_msg, wx.RED), {}))
    
    
    def logMessage(self, message):
        """"""
        tracer.log(WurmCommon.DEBUG7, "WurmUI - logMessage")
        
        lw_msg = "(INFO) %s" % (message)
        
        logger.info(message)
        
        if threading.currentThread().getName() == "MainThread":
            self.log(lw_msg, wx.BLACK)
        else:
            wx.PostEvent(self, ThreadCommsEvent(self.log, (lw_msg, wx.BLACK), {}))
    
    
    def logWarning(self, message):
        """"""
        tracer.log(WurmCommon.DEBUG7, "WurmUI - logWarning")
        
        lw_msg = "(WARN) %s" % (message)
        
        logger.warning(message)
        
        if threading.currentThread().getName() == "MainThread":
            self.log(lw_msg, wx.BLUE)
        else:
            wx.PostEvent(self, ThreadCommsEvent(self.log, (lw_msg, wx.BLUE), {}))
    
    
    def saveUISettings(self):
        """ Saves all UI settings in an xml file in the directory WUU.py/.exe resides """
        tracer.debug("WurmUI - saveUISettings")
        
        global settingsfile, usePTR, wowDirOrig, wowBackupDirOrig
        
        WurmCommon.outMessage(_("Saving UI settings to %(sfile)s") % {'sfile': settingsfile})
        
        # If the Test Realm is chosen then revert some directory entries
        if usePTR:
            self.settings["WoWDir"]    = wowDirOrig
            self.settings["BackupDir"] = wowBackupDirOrig
        
        root = Element("wurm")
        
        # Settings
        wsettings    = SubElement(root, "wurmsettings")
        version      = SubElement(wsettings, "version")
        version.text = "%s" % (wuuversion)
        
        k = self.settings.keys()
        k.sort()
        
        for a in k:
            # Use new style for 1.5 (WUU will still read old format, and backup original file)
            option                = SubElement(wsettings, "option")
            option.attrib["name"] = a
            option.text           = "%s" % (self.settings[a], )
            
            # WurmCommon.outDebug("Saved UI setting '%s' ('%s')" % (a, self.settings[a]))
        
        tree = ElementTree(root)
        tree.write(settingsfile, "utf-8")
    
    
    def showStatus(self, message):
        """"""
        tracer.log(WurmCommon.DEBUG7, "WurmUI - showStatus")
        
        if threading.currentThread().getName() == "MainThread":
            self.clearStatusTimer.Stop()
            self.SetStatusText(message)
            self.clearStatusTimer.Start(self.clearStatusTimeout, wx.TIMER_ONE_SHOT)
        else:
            wx.PostEvent(self, ThreadCommsEvent(self.showStatus, (message,), {}))
            return
        
        logger.log(WurmCommon.STATUS, message)
        
        try:
            # Yield so the display can be seen
            wx.Yield()
        except:
            pass # ignore Yield failure
    
    
    def resetProgress(self):
        """"""
        tracer.log(WurmCommon.DEBUG5, "WurmUI - resetProgress")
        
        if self.Visible:
            if threading.currentThread().getName() == "MainThread":
                self.sb.pg.SetValue(0)
            else:
                wx.PostEvent(self, ThreadCommsEvent(self.sb.pg.SetValue, (0,), {}))
    
    
    def resetProgress2(self):
        """"""
        tracer.log(WurmCommon.DEBUG5, "WurmUI - resetProgress2")
        
        if self.Visible:
            if threading.currentThread().getName() == "MainThread":
                self.sb.pg2.SetValue(0)
            else:
                wx.PostEvent(self, ThreadCommsEvent(self.sb.pg2.SetValue, (0,), {}))
    
    
    def updateAddonFromFileSelect(self, addon):
        """ Pops up a file selector dialog to ask the user which file is an update for the given addon """
        
        # Try a dirty trick in selecting the most recent file seemingly for this addon, to possibly save time
        quick = WurmCommon.FindRecentDownloads(addon)
        if len(quick) > 0:
            if len(quick) > 1:
                quick.sort()
                quick.reverse() # this probably gives a better result than grabbing the first item
            
            fn = quick[0]
            
            msg = wx.MessageDialog(self, _("Is %(filename)s the correct file for %(addon)s?\nFull path: %(fullpath)s") % {'addon': addon, 'filename': os.path.basename(fn), 'fullpath':fn}, _("Select the downloaded file for %(addon)s")  % {'addon': addon}, style=wx.YES_NO|wx.ICON_WARNING)
            answer = msg.ShowModal()
            msg.Destroy()
            
            if answer == wx.ID_YES: # Shortcut!
                WurmCommon.outMessage(_("Updating %(addon)s from %(filename)s") % {'addon': addon, 'filename':os.path.basename(fn)})
                success = WurmCommon.addons[addon].updateModFromFile(fn)
                self._queueCallback(addon, "fileupdate", status=success)
                return
        
        dlg = wx.FileDialog(self, _("Select the downloaded file for %(addon)s") % {'addon': addon}, defaultDir=self._getSetting(":BrowserDownloadDir", ""), style=wx.FD_OPEN)
        
        if dlg.ShowModal() == wx.ID_OK:
            WurmCommon.outMessage(_("Updating %(addon)s from %(filename)s") % {'addon': addon, 'filename':dlg.GetFilename()})
            success = WurmCommon.addons[addon].updateModFromFile(dlg.GetPath())
        else:
            success = False
        
        dlg.Destroy()
            
        self._queueCallback(addon, "fileupdate", status=success)
    
    
    def updateProgress(self, task, progress):
        """ Show the Progress Gauge moving from left to right.
        If the progress value is -99 a Pulse effect is used instead.
        """
        tracer.log(WurmCommon.DEBUG5, "WurmUI - updateProgress")
        
        # Display progress if window is displayed
        if self.Visible:
            if threading.currentThread().getName() == "MainThread":
                self.showStatus(task)
                if progress == -99:
                    if wx.VERSION[:2] >= (2, 7):
                        self.sb.pg.Pulse()
                else:
                    self.sb.pg.SetValue(progress)
                    self.sb.pg.Refresh()
            else:
                wx.PostEvent(self, ThreadCommsEvent(self.showStatus, (task,), {}))
                if progress == -99:
                    if wx.VERSION[:2] >= (2, 7):
                        wx.PostEvent(self, ThreadCommsEvent(self.sb.pg.Pulse, (), {}))
                else:
                    wx.PostEvent(self, ThreadCommsEvent(self.sb.pg.SetValue, (progress,), {}))
                    wx.PostEvent(self, ThreadCommsEvent(self.sb.pg.Refresh, (), {}))
    
    
    def updateProgress2(self, progress):
        """ Show the Progress Gauge moving from left to right.
        If the progress value is -99 a Pulse effect is used instead.
        """
        tracer.debug("WurmUI - updateProgress2")
        
        # Display progress if window is displayed
        if self.Visible:
            if threading.currentThread().getName() == "MainThread":
                self.sb.pg2.SetValue(progress)
                self.sb.pg2.Refresh()
            else:
                wx.PostEvent(self, ThreadCommsEvent(self.sb.pg2.SetValue, (progress,), {}))
                wx.PostEvent(self, ThreadCommsEvent(self.sb.pg2.Refresh, (), {}))
    
    
    def AskForWoWPath(self): # a hack, for now TODO: Replace this entire deal with a friendly (or evil) wizard
        """"""
        tracer.debug("WurmUI - AskForWoWPath")
        
        wowexename = "WoW.exe"
        wowexedefaultpath = os.path.join(os.environ.get('PROGRAMFILES','C:\\Program Files'), 'World of Warcraft') # must use .get, since environ['PROGRAMFILES'] doesn't exist on OSX/Linux :facepalm:
        if sys.platform == 'darwin':
            wowexename = "World of Warcraft.app"
            wowexedefaultpath = '/Applications/World of Warcraft'
        
        if sys.platform[:5] == 'linux':
            # The next is only the default path if EVERYTHING is kept at their default values in Linux, but worth a try
            wowexedefaultpath = os.path.join(os.environ['HOME'], ".wine", "drive_c", "Program Files", "World of Warcraft")
        
        if os.path.exists(os.path.join(wowexedefaultpath, wowexename)):
            # Ask if we want to use default path
            msg = wx.MessageDialog(self, _("Found a World of Warcraft installation at:\n%(path)s\nDo you want this installation to be managed by WUU?") % {'path':wowexedefaultpath}, _("Found WoW installation!"), style=wx.YES_NO|wx.ICON_INFORMATION)
            answer = msg.ShowModal()
            msg.Destroy()
                    
            if answer == wx.ID_YES:
                return wowexedefaultpath
        
        path = False
        dlg = wx.DirDialog(self, _("Select the directory containing %s") % (wowexename), style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
        dlg.Destroy()
        
        return path
    
    
    def CopyBBCode(self, addDescription=True):
        """ Returns the selected addon(s) in BBCode (web forum) format.
        If addDescription is True, the "Notes" field from the TOC is also added
        """
        tracer.debug("WurmUI - CopyBBCode")
        
        bbwrapper      = "[quote=%s]%s[/quote]" # wraps the result TODO: make this user configurable
        singlemod      = "[url=%(addonurl)s][b]%(localname)s[/b][/url]\n" # Template for listing a single Addon
        singlemodnourl = "[b]%(localname)s[/b]\n" # Template for a single Addon with no available URL
        singlemoddesc  = "\t[i]%(description)s[/i]\n" # Template for adding a description
        author         = "WUU %s" % (wuuversion)
        result         = "" # this string will contain the list
        
        # Addons
        toSet = self._getLcItems()
        
        for a in toSet:
            # Implements "only export selected"
            (frn, lon, sid, adt) = WurmCommon.addonlist.getSome(a)
            description = None
            url = None
            
            if addDescription:
                toc = WurmCommon.toclist.get(a)
                if toc:
                    description = toc.getTextField("Notes")
                    # Shorten the description if it's too long
                    if len(description) > 70:
                        description = description[:65]+"(...)"
            
            addon = WurmCommon.addons.get(a)
            if addon:
                if addon.getAddonURL():
                    url = addon.getAddonURL()
            
            if url:
                result += singlemod % {'localname': lon, 'addonurl': url}
            else:
                result += singlemodnourl % {'localname': lon, 'addonurl': url}
            
            if description:
                result += singlemoddesc % {'description': description}
        
        return bbwrapper % (author, result)
    
    
    def CopyXML(self):
        """ Returns the selected addon(s) on the WUU simple distribution format """
        tracer.debug("WurmUI - CopyXML")
        
        root = Element("wuu")
        waddons = SubElement(root, "wuucopy")
                
        toSet   = self._getLcItems()
        
        for a in toSet:
            # Implements "only export selected"
            (friendlyname, localname, siteid, addontype) = WurmCommon.addonlist.getSome(a)
            
            addon = SubElement(waddons, "add")
            l = SubElement(addon, "l")
            l.text = localname
            
            if addontype != "[Unknown]": # only set addontype if it's changed from unknown
                t = SubElement(addon, "t")
                t.text = addontype
            if friendlyname != localname: # only set friendlyname if it's actually changed
                f = SubElement(addon, "f")
                f.text = friendlyname
            if siteid != localname and siteid != "": # only set siteid if it's actually "not localname and not empty"
                sid = SubElement(addon, "sid")
                sid.text = siteid
        
        tree = ElementTree(root)
        
        s = StringIO()
        tree.write(s, "utf-8")
        
        return s.read()
    
    
    def CreateUI(self):
        """ Create the GUI components """
        tracer.debug("WurmUI - CreateUI")
        
        # shortcut to grab IDs
        _id = lambda x: self._getID(x)
        
        # Window icon
        if os.path.exists(iconfile): # Not really fatal if icon is missing
            _icon = wx.Icon(iconfile, wx.BITMAP_TYPE_ICO)
            self.SetIcon(_icon)
        
        # Create the notebook to hold the other panels
        self.notebook = wx.Notebook(self, _id("notebook"), style=wx.NB_BOTTOM)
        
        # Create the Event Log Notebook page
        self.logwindow = wx.TextCtrl(self.notebook, _id("eventlog"), '', size=(-1, -1), style=wx.TE_MULTILINE | wx.TE_AUTO_SCROLL | wx.TE_AUTO_URL | wx.TE_READONLY | wx.TE_RICH2)
        
        # Bind the Frame Close event to its handler
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        
        # Resources
        self.il    = wx.ImageList(16, 16)
        self.sm_up = self.il.Add(images.getSmallUpArrowBitmap())
        self.sm_dn = self.il.Add(images.getSmallDnArrowBitmap())
        
        # Create a MenuBar
        self.SetMenuBar(self.CreateMenuBar())
        
        # Create a StatusBar with 3 fields, Text & 2 progress gauges
        self.sb = CustomStatusBar(self)
        self.SetStatusBar(self.sb)
        
        # Create the Addon List Notebook page using a Splitter Window
        self.splitter = wx.SplitterWindow(self.notebook, _id("addonlistsplitter"))
        # Setup the Splitter options
        self.splitter.SetMinimumPaneSize(150)
        # Set the Sash Gravity, allows the LHS pane to be resized, RHS stays the same size
        self.splitter.SetSashGravity(1.0)
        
        # Create the Addon Panel as a child of the splitter window
        self.p1 = wx.Panel(self.splitter, _id("addonlistpanel"), size=(600, -1))
        
        # Create a GridBagSizer to position the ListCtrl & Buttons
        self.gbsizer = wx.GridBagSizer(2, 2)
        
        # Create the ListCtrl
        self.lc = wx.ListCtrl(self.p1, _id("addonlistctrl"), style=wx.LC_REPORT | wx.LC_SORT_ASCENDING)
        self.lc.InsertColumn(0, _("Directory"))
        self.lc.InsertColumn(1, _("Site"))
        self.lc.InsertColumn(2, _("Friendly name"))
        self.lc.InsertColumn(3, _("Local ver."))
        self.lc.InsertColumn(4, _("Online ver."))
        self.lc.InsertColumn(5, _("Upd?"), format=wx.LIST_FORMAT_CENTRE)
        self.lc.InsertColumn(6, _("TOC ver."))
        self.lc.InsertColumn(7, _("Res?"), format=wx.LIST_FORMAT_CENTRE)
        self.lc.SetColumnWidth(0, int(self._getSetting("LCcol0", 140)))
        self.lc.SetColumnWidth(1, int(self._getSetting("LCcol1", 80)))
        self.lc.SetColumnWidth(2, int(self._getSetting("LCcol2", 140)))
        self.lc.SetColumnWidth(3, int(self._getSetting("LCcol3", 80)))
        self.lc.SetColumnWidth(4, int(self._getSetting("LCcol4", 80)))
        self.lc.SetColumnWidth(5, int(self._getSetting("LCcol5", 50)))
        self.lc.SetColumnWidth(6, int(self._getSetting("LCcol6", 50)))
        self.lc.SetColumnWidth(7, int(self._getSetting("LCcol7", 50)))
        # Setup the Image List
        self.lc.SetImageList(self.il, wx.IMAGE_LIST_SMALL)
        
        # Fixes bug #1833163: WUU on themed systems sometimes has invisible text:
        self.lc.SetTextColour(wx.BLACK)
        
        # Bind events to their handlers
        self.p1.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnListContextMenu)
        self.p1.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnListItemSelected)
        self.p1.Bind(wx.EVT_LIST_COL_END_DRAG, self.OnColumnResize)
        
        # Add the ListCtrl to the GridBagSizer
        self.gbsizer.Add(self.lc, (0, 0), (1, 1), flag=wx.EXPAND)
        
        # Make sure the sizer can grow
        self.gbsizer.AddGrowableRow(0)
        self.gbsizer.AddGrowableCol(0)
        
        # Size everything in the Addon Panel
        self.p1.SetSizer(self.gbsizer)
        
        # Create the Info panel
        self.p2 = BrowserHtmlWindow(self.splitter, _id("addonhtmlwin"), size=(250, -1))
        self.p2.SetPage(rightPanelHTMLDefault % {'text': _("Welcome to WUU"), 'info': ''})
        
        # Split the notebook page vertically
        self.splitter.SplitVertically(self.p1, self.p2)
         
         # Add the pages to the Notebook
        self.notebook.AddPage(self.splitter, _("Addon List"))
        self.notebook.AddPage(self.logwindow, _("Event Log"))
        
        # Bind the Notebook PageChanged event to its handler
        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnNBPageChanged)
        
        # Initialise the List Sorting
        listmix.ColumnSorterMixin.__init__(self, 8)
        # set the last two columns to sort descending 1st time they are clicked
        self._colSortFlag[5] = -1 # Update
        self._colSortFlag[7] = -1 # Restore
        
        # Initialise the Type Ahead mixin
        WurmUtility.TypeAheadListCtrlMixin.__init__(self)
        
        try:
            # Set the frame position based upon the saved settings
            self.SetPosition((int(self._getSetting("FrameX", 15)), \
                              int(self._getSetting("FrameY", 22))))
            # Set the frame size based upon the saved settings
            self.SetSize((int(self._getSetting("FrameW", 800)), \
                          int(self._getSetting("FrameH", 500))))
            # Reposition the sash
            self.splitter.SetSashPosition(int(self.GetSize()[0] + \
                                          int(self._getSetting("SashOffset", -150))))
        except:
            pass
        
        # Bind the Move event to its handler
        self.Bind(wx.EVT_MOVE, self.OnMove)
        # Bind the Size event to its handler
        self.Bind(wx.EVT_SIZE, self.OnResize)
        # Bind the Sash Position Changed event to its handler
        self.splitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.OnSashPositionChanged)
    
    
    def CreateMenuBar(self):
        """"""
        tracer.debug("WurmUI - CreateMenuBar")
        
        # Create the Menubar and its' menus
        self.menubar = wx.MenuBar() # CHANGED: renamed to self. so menu items can be Enabled/Disabled
        filem        = wx.Menu()
        imposubm     = wx.Menu()
        exposubm     = wx.Menu()
        addonm       = wx.Menu() # CHANGED: editm renamed to addonm
        instsubm     = wx.Menu()
        viewm        = wx.Menu()
        toolm        = wx.Menu()
        # wowacem      = wx.Menu()
        cachem       = wx.Menu()
        helpm        = wx.Menu()
        
        # Syntax used for IDs: "m>X>Y(>Z)" where X>Y>Z are all
        # 1-3 letter variants of their menu paths.
        # Example: "m>f>im>ap" for "File>Import>from addonpack"
        # The lambda "_id(x)" below shortens self._getID("m>a>b")
        # to _id("a>b")
        _id = lambda x: self._getID("m>%s" % (x,))
        
        # File menu
        filem.Append(wx.ID_OPEN, _('&Open\tCtrl+O'), _('Load Addon list'))
        filem.Append(wx.ID_SAVE, _('&Save\tCtrl+S'), _('Save Addon list'))
        filem.AppendSeparator()
        filem.AppendMenu(_id("f>im"), _('Import'), imposubm)
        filem.AppendMenu(_id("f>ex"), _('Export'), exposubm)
        filem.AppendSeparator()
        filem.Append(wx.ID_EXIT, _('&Quit\tCtrl+Q'), _('Quit WUU'))
        # Import submenu of File menu
        imposubm.Append(_id("f>im>a"), _('Addons...'), _('Import Addons from file'))
        imposubm.Append(_id("f>im>s"), _('Sites...'), _('Imports Addon site settings from file, only for addons already on your list'))
        imposubm.Append(_id("f>im>ap"), _('from addonpack'), _('Imports Addons from an addon pack ID'))
        # Export submenu of File menu
        exposubm.Append(_id("f>ex>a"), _('All addons'), _('Export Addons to file'))
        exposubm.Append(_id("f>ex>s"), _('Selected addons'), _('Exports all currently selected Addons to file'))
        
        # Addon menu
        addonm.Append(_id("a>su"), _('One-Button Update\tF10'), _('Version check and, if needed, update all Addons'))
        addonm.Append(_id("a>dl"), _('Open download pages\tF9'), _('Open manual download pages for all addons that need update'))
        addonm.AppendSeparator()
        addonm.Append(wx.ID_NEW, _('&New\tCtrl+N'), _('Insert a New entry into the Addon List'))
        addonm.Append(_id("a>uf"), _('Update from file\tCtrl+F'), _('Update all selected addons from (individual) files'))
        addonm.Append(wx.ID_DELETE, _('&Delete'), _('Delete the selected Addons and all related')) # moved
        addonm.Append(_id("a>r"), _('&Restore from Backup\tCtrl+R'), _('Restore the selected Addons from Backup'))
        addonm.AppendSeparator()
        addonm.Append(_id("a>s"), _('S&can Directory\tCtrl+D'), _('Scan WoW Addon directory')) # moved
        addonm.Append(_id("a>v"), _('Check &online version\tCtrl+V'), _('Checks all the Addon sites for new versions')) # moved
        addonm.Append(_id("a>u"), _('Update to Latest\tCtrl+U'), _('Updates all older Addons - online version must be known for this to work!'))
        #addonm.Append(114, 'Update with &master list\tCtrl+M', 'Gets Addon site settings from the online master list') # moved
        # Make the key Alt + Command + U on a Mac as Command + M is the Minimize Window key binding
        if sys.platform == 'darwin':
            key = 'Alt-Ctrl-U'
        else:
            key = 'Ctrl-M'
        addonm.Append(_id("a>m"), _('Update from Online DB\t%(key)s') % {'key': key}, _('Gets Addon site settings from the online database (user-submitted, only affects [Unknown] Addons)'))
        addonm.AppendSeparator()
        addonm.AppendMenu(_id("a>if"), _('Install from'), instsubm) # moved
        addonm.AppendSeparator()
        addonm.Append(_id("a>bb"), _('&Copy to BBCode'), _('Copy a list of the selected Addons to BBCode for forums')) # CHANGED: removed Ctrl+C as accelerator key as it conflicts with the default Copy function
        # Install submenu of Edit menu
        #instsubm.Append(115, 'the Master List\tCtrl-I', 'Lets you install addons from the master list')
        instsubm.Append(_id("a>if>co"), _('CosmosUI'), _('Lets you install Addons directly from CosmosUI'))
        instsubm.Append(_id("a>if>u"), _('URL...'), _('Installs a single Addon, given the URL to its web page (Experimental, might not work, doesn\'t support all sites yet)'))
        # View menu
        viewm.Append(_id("v>hd"), _('Hide dummy'), _('Hides [Dummy] addons'), wx.ITEM_CHECK)
        viewm.Append(_id("v>hi"), _('Hide ignored'), _('Hides [Ignore]d addons'), wx.ITEM_CHECK)
        viewm.Append(_id("v>ho"), _('Hide outdated'), _('Hides [Outdated] addons'), wx.ITEM_CHECK)
        viewm.Append(_id("v>hr"), _('Hide related'), _('Hides [Related] addons'), wx.ITEM_CHECK)
        
        # set View menu options
        if int(self._getSetting("HideDummy", 0)):
            viewm.Check(_id("v>hd"), True)
        if int(self._getSetting("HideIgnored", 0)):
            viewm.Check(_id("v>hi"), True)
        if int(self._getSetting("HideOutdated", 0)):
            viewm.Check(_id("v>ho"), True)
        if int(self._getSetting("HideRelated", 1)):
            viewm.Check(_id("v>hr"), True)
        
        # Tools menu
        toolm.Append(_id("t>ct"), _('Clean &temp dir\tCtrl-T'), _('Cleans out the temp dir WUU uses to store downloaded addon archives')) # Moved from file menu - keeps ID
        toolm.Append(_id("t>r"), _('Check site regexps'), _('Checks WUU site for updated regular expressions'))
        toolm.Append(_id("t>t"), _('Check templates'), _('Checks WUU site for updated templates'))
        toolm.AppendSeparator()
        toolm.Append(_id("t>sv"), _('Clean Unused SavedVariables'), _('Scans for unused SavedVariables, and allows for selective deletion'))
        toolm.AppendSeparator()
        toolm.Append(_id("t>u"), _('Upload your addon list'), _('Uploads your addon list to the WUU web page, for inclusion in the master list'))
        toolm.Append(_id("t>pm"), _('Purge missing addons'), _('Removes all addons that are deleted outside WUU from the internal addon list'))
        toolm.Append(_id("t>fd"), _('Find duplicate settings'), _('Checks all addons to see if any have the same settings'))
        toolm.AppendSeparator()
        toolm.AppendMenu(_id("t>ca"), _("Web cache"), cachem)
        toolm.Append(wx.ID_PREFERENCES, _('Preferences...'), _('Change WUU preferences'))
        
        # Cache submenu of Tools menu
        cachem.Append(_id("t>ca>e"), _('Enabled'), _('Enables the in-memory cache of web pages'), wx.ITEM_CHECK)
        if int(self._getSetting(":WebCache", 1)):
            cachem.Check(_id("t>ca>e"), True)
        cachem.Append(_id("t>ca>fa"), _('Flush all'), _('Empties the cache completely'))
        cachem.Append(_id("t>ca>fe"), _('Flush expired'), _('Forces a flush of all expired pages'))
        
        # Help menu
        helpm.Append(_id("h>www"), _('WUU Website\tF1'), _('Opens the WUU Website in your browser'))
        helpm.Append(_id("h>wki"), _('WUUki\tCtrl+F1'), _('Opens the WUUki in your browser'))
        helpm.Append(_id("h>wsf"), _('WUU@SourceForge'), _('Opens the WUU SourceForge project in your browser'))
        helpm.AppendSeparator()
        helpm.Append(_id("h>asvn"), _('AceSVN'), _('Opens AceSVN site in your browser'))
        helpm.Append(_id("h>auc"), _('Auctioneer'), _('Opens AuctioneerAddon site in your browser'))
        helpm.Append(_id("h>cb"), _('CapnBry'), _('Opens CapnBry site in your browser'))
        helpm.Append(_id("h>cui"), _('CosmosUI'), _('Opens CosmosUI site in your browser'))
        helpm.Append(_id("h>ct") , _('CTMod'), _('Opens CTMod site in your browser'))
        helpm.Append(_id("h>cg") , _('CurseGaming'), _('Opens CurseGaming site in your browser'))
        helpm.Append(_id("h>g")  , _('Gatherer'), _('Opens GathererAddon site in your browser'))
        helpm.Append(_id("h>gc")  , _('GoogleCode'), _('Opens GoogleCode site in your browser'))
        helpm.Append(_id("h>uiw"), _('WoWUI'), _('Opens WoWUI site in your browser'))
        helpm.Append(_id("h>wa") , _('WoWAce'), _('Opens WoWAce site in your browser'))
        helpm.Append(_id("h>wi") , _('WoWI'), _('Opens WoWInterface site in your browser'))
        helpm.AppendSeparator()
        helpm.Append(_id("h>o")  ,_('Open Addon dir'), _('Opens the WoW Addon dir'))
        helpm.Append(wx.ID_ABOUT, _('&About'), _('About WUU'))
        # Add menus to the Menubar
        self.menubar.Append(filem, _('&File'))
        self.menubar.Append(addonm, _('&Addon')) # renamed
        self.menubar.Append(viewm, _('&View'))
        self.menubar.Append(toolm, _('&Tools'))
        self.menubar.Append(helpm, '&Help') # Don't Translate this string otherwise it won't be put in the right place
        
        # Bind the Menu events to their handlers
        # File menu
        wx.EVT_MENU(self, wx.ID_OPEN, self.OnLoad)
        wx.EVT_MENU(self, wx.ID_SAVE, self.OnSave)
        wx.EVT_MENU(self, _id("f>im>a"), self.OnImport)
        wx.EVT_MENU(self, _id("f>im>ap"), self.OnImportPack)
        wx.EVT_MENU(self, _id("f>im>s"), self.OnMerge)
        wx.EVT_MENU(self, _id("f>ex>a"), self.OnExport)
        wx.EVT_MENU(self, _id("f>ex>s"), self.OnExportSelected)
        wx.EVT_MENU(self, wx.ID_EXIT, self.OnQuit)
        
        # Addon menu
        wx.EVT_MENU(self, _id("a>su"), self.OnUpdateAllSmart)
        wx.EVT_MENU(self, _id("a>dl"), self.OnOpenAddonDlPageSmart)
        wx.EVT_MENU(self, _id("a>uf"), self.OnUpdateFromFile)
        wx.EVT_MENU(self, wx.ID_NEW, self.OnAdd)
        wx.EVT_MENU(self, wx.ID_DELETE, self.OnDeleteSelected)
        # wx.EVT_MENU(self, _id("a>r"), self.OnAdvancedRestore) # for testing only
        wx.EVT_MENU(self, _id("a>r"), self.OnRestoreSelected)
        wx.EVT_MENU(self, _id("a>s"), self.OnScan)
        wx.EVT_MENU(self, _id("a>v"), self.OnSyncAll)
        wx.EVT_MENU(self, _id("a>u"), self.OnUpdateAllNewer)
        wx.EVT_MENU(self, _id("a>m"), self.OnCheckOnlineDB)
        wx.EVT_MENU(self, _id("a>if>co"), self.OnInstallCosmos)
        wx.EVT_MENU(self, _id("a>if>u"), self.OnImportURL)
        wx.EVT_MENU(self, _id("a>bb"), self.OnCopyBB)
        
        # View menu
        wx.EVT_MENU(self, _id("v>hd"), self.OnHideDummy)
        wx.EVT_MENU(self, _id("v>hi"), self.OnHideIgnored)
        wx.EVT_MENU(self, _id("v>ho"), self.OnHideOutdated)
        wx.EVT_MENU(self, _id("v>hr"), self.OnHideRelated)
        
        # Tools menu
        wx.EVT_MENU(self, _id("t>ct"), self.OnCleanTemp)
        wx.EVT_MENU(self, _id("t>r"), self.checkOnlineRegexps)
        wx.EVT_MENU(self, _id("t>t"), self.checkOnlineTemplates)
        wx.EVT_MENU(self, _id("t>sv"), self.OnCheckSavedVariables)
        wx.EVT_MENU(self, _id("t>u"), self.OnUploadAddonlist)
        wx.EVT_MENU(self, _id("t>pm"), self.OnPurgeMissing)
        wx.EVT_MENU(self, _id("t>fd"), self.OnCheckDuplicates)
        wx.EVT_MENU(self, wx.ID_PREFERENCES, self.OnPreferences)
        wx.EVT_MENU(self, _id("t>ca>e"), self.OnCacheToggle)
        wx.EVT_MENU(self, _id("t>ca>fa"), self.OnCacheFlushAll)
        wx.EVT_MENU(self, _id("t>ca>fe"), self.OnCacheFlushExpired)
        # Help menu
        wx.EVT_MENU(self, _id("h>www"), self.OnOpenWUUWeb)
        wx.EVT_MENU(self, _id("h>wki"), self.OnOpenWUUki)
        wx.EVT_MENU(self, _id("h>wsf"), self.OnOpenWUUSFWeb)
        wx.EVT_MENU(self, _id("h>wa"),  self.OnOpenSiteWoWAce)
        wx.EVT_MENU(self, _id("h>wi"),  self.OnOpenSiteWoWI)
        wx.EVT_MENU(self, _id("h>cg"),  self.OnOpenSiteCurseGaming)
        wx.EVT_MENU(self, _id("h>uiw"), self.OnOpenSiteWoWUI)
        wx.EVT_MENU(self, _id("h>auc"), self.OnOpenSiteAuctioneer)
        wx.EVT_MENU(self, _id("h>g"),   self.OnOpenSiteGatherer)
        wx.EVT_MENU(self, _id("h>cui"), self.OnOpenSiteCosmos)
        wx.EVT_MENU(self, _id("h>ct"),  self.OnOpenSiteCTMod)
        wx.EVT_MENU(self, _id("h>cb"),  self.OnOpenSiteCapnBry)
        wx.EVT_MENU(self, _id("h>gc"),  self.OnOpenSiteGoogleCode)
        wx.EVT_MENU(self, _id("h>o"),   self.OnOpenAddonDir)
        wx.EVT_MENU(self, wx.ID_ABOUT, self.OnAbout)
        
        return self.menubar
    
    
    def EditAddon(self, fitem, curitem):
        """ Opens a dialog to edit the given addon """
        try:
            dia = WurmAddonEditDlg(self, fitem, self.settings)
            toDelete = []
            newaddon = False
            
            if dia.ShowModal() == wx.ID_OK:
                dia.updateFlags()
                # Handle the NewAddon entry by changing its name to the friendly one
                if fitem == WurmCommon.newaddon:
                    fitem = dia.fname.GetValue()
                    WurmCommon.addonlist.delete(WurmCommon.newaddon)
                    newaddon = True
                    # Flag as missing to prevent TOC errors
                    dia.specialflags["missing"] = True
                
                # if the Addon type has been changed to either OtherSite or Child
                # prompt the user to select a template to use
                template = None
                curType = WurmCommon.addonlist.getAtype(fitem)
                newType = dia.site.GetStringSelection()
                if not curType == "OtherSite" and newType == "OtherSite":
                    template = WUUDialogs.GetTemplate(newType)
                    templateTable = WurmCommon.ostemplates
                elif not curType == "Child" and newType == "Child":
                    template = WUUDialogs.GetTemplate(newType)
                    templateTable = WurmCommon.childtemplates
                
                if template:
                    # update the dialog attributes
                    dia.siteid.SetValue(templateTable[template]["Siteid"])
                    for key in WurmCommon.templateKeys:
                        dia.specialflags[key] = templateTable[template][key]
                    if newType == "Child":
                        key = "Parent"
                        dia.specialflags[key] = templateTable[template][key]
                 
                # Update the addonlist dictionary
                WurmCommon.addonlist.add(fitem, fname=dia.fname.GetValue(), siteid=dia.siteid.GetValue(), atype=dia.site.GetStringSelection(), flags=dia.specialflags)
                if newaddon:
                    self._quickUpdateAddonList(fitem, updtype='add', fname=dia.fname.GetValue(), atype=dia.site.GetStringSelection())
                
                # Update the addons dictionary, removing entries as necessary
                Wurm.refreshSingleAddon(fitem)
                
                # Update the displayed List Control, any Addon that shouldn't be viewed will return False
                if not self._quickUpdateAddonList(fitem, updtype='update', fname=dia.fname.GetValue(), atype=dia.site.GetStringSelection()):
                    toDelete.append((fitem, curitem))
            
            # Remove any Addons that shouldn't be viewed from the List Control
            for (fitem, curitem) in toDelete:
                self.lc.DeleteItem(curitem)
            
            dia.Destroy()
        
        except Exception, details:
            logger.exception("Error: Editing Addon details: %s" % (str(details)))
        
        if newaddon:
            self.topItem = fitem
        
        # redisplay the ListControl so the updated info is displayed
        self.RefreshAddonList()
        # now position the entry in the List Control
        self._showAddon()
    
    
    def GetListContextMenu(self):
        """ Creates an appropriate context menu for the current selection of addons """
        tracer.log(WurmCommon.DEBUG5, "WurmUI - GetListContextMenu")
        
        if self.lc.GetSelectedItemCount() == 0:
            return None# nothing to do; no behaviour defined for right-click outside the list
        
        toCheck = self._getLcItems(inAddons=False)
        
        # Flags to determine which menu to show; these are True if all selected items...
        allUnknown  = True # ...are [Unknown]
        allMeta     = True # ...are [Unknown]/[Ignore]/[Related]/etc.
        allSite     = True # ...are set to actual sites
        allSameSite = True # ...are set to the SAME site, not meta
        onlyOne     = True # ...are, well, one :P
        allWoWUI    = True # ...are from WoWUI
        allWoWAce   = True # ...are from WoWAce
        allCurse    = True # ...are from Curse (added after the Curse change, April 2009)
        
        # The flags are conflicting right now, but will be set to False as we check the addons one by one
        
        differentsites = []
        
        for ad in toCheck:
            site = WurmCommon.addonlist.getAtype(ad)
            if site != "[Unknown]":
                allUnknown = False
                allMeta = False
            if site[0] != "[":
                allMeta = False
            if site[0] == "[":
                allSite = False
            if site != "WoWUI": # manual downloads required
                allWoWUI = False
            if site != "WoWAce" and site != "WoWAceClone": # manual downloads required
                allWoWAce = False
            if site != "CurseGaming": # manual downloads required
                allCurse = False
            if site not in differentsites:
                differentsites.append(site)
        
        if len(differentsites) > 1:
            allSameSite = False
        
        if len(toCheck) > 1:
            onlyOne = False
        
        # Syntax used for IDs: "p>popup-X" where X is the action
        # The lambda "_id(x)" below shortens self._getID("p>popup-X")
        # to _id("popup-X")
        # _xid returns True if ID is allocated
        _id = lambda x: self._getID("p>%s" % (x,))
        _xid = lambda x: self.idpool.has_key(x)
        
        # Construct menu, based on detected selection
        popupm = wx.Menu()
        popupcnt = 0
        if allSite:
            if not allCurse and not allWoWUI and not allWoWAce:
                popupm.Append(_id("popup-smart"), _("Smartupdate"), _("Checks selected addon(s) for updates, and updates if needed"))
                wx.EVT_MENU(self, _id("popup-smart"), self.OnUpdateSelectedSmart)
                if popupm.GetMenuItemCount() > popupcnt:
                    popupm.AppendSeparator()
                    popupcnt = popupm.GetMenuItemCount()
            popupm.Append(_id("popup-version"), _("Version check"), _("Checks if a newer version is available"))
            wx.EVT_MENU(self, _id("popup-version"), self.OnSyncAddon)
            popupm.Append(_id("popup-localver"), _("Update local version"), _("Updates the selected addon(s) local version"))
            wx.EVT_MENU(self, _id("popup-localver"), self.OnUpdateVersionSelected)
        
        if onlyOne:
            if popupm.GetMenuItemCount() > popupcnt:
                popupm.AppendSeparator()
                popupcnt = popupm.GetMenuItemCount()
            if allUnknown:
                popupm.Append(_id("popup-url"), _("Identify (input URL)"), _("Lets you paste in the URL of the selected addon to identify it"))
                wx.EVT_MENU(self, _id("popup-url"), self.OnIdentifySelectedByURL)
            elif allSite:
                if site != "GenericGit":
                    popupm.Append(_id("popup-visit"), _("Open addon page"), _("Opens this addon's webpage in your default browser"))
                    wx.EVT_MENU(self, _id("popup-visit"), self.OnOpenAddonPage)
                if allCurse or allWoWUI or allWoWAce:
                    popupm.Append(_id("popup-visitdl"), _("Open download page"), _("Opens this addon's download page for the latest version in your browser"))
                    wx.EVT_MENU(self, _id("popup-visitdl"), self.OnOpenAddonDlPage)
                if allWoWAce:
                    popupm.Append(_id("popup-visitfldl"), _("Open files page"), _("Opens this addon's download page for all versions in your browser"))
                    wx.EVT_MENU(self, _id("popup-visitfldl"), self.OnOpenAddonFilesDlPage)
        
        if allUnknown:
            popupm.Append(_id("popup-id"), _("Identify (online DB)"), _("Identifies selected addon(s) using the wuu.vagabonds.info database"))
            wx.EVT_MENU(self, _id("popup-id"), self.OnIdentifySelectedUnknown)
        
        if popupm.GetMenuItemCount() > popupcnt:
            popupm.AppendSeparator()
            popupcnt = popupm.GetMenuItemCount()
        
        if allCurse or allWoWUI or allWoWAce:
            popupm.Append(_id("popup-updfile"), _("Update from file"), _("Updates the selected addon(s) from downloaded file(s)"))
            wx.EVT_MENU(self, _id("popup-updfile"), self.OnUpdateFromFile)
        if not allCurse and not allWoWUI and not allWoWAce:
            popupm.Append(_id("popup-update"), _("Update"), _("Forces an update of the addon(s)"))
            wx.EVT_MENU(self, _id("popup-update"), self.OnUpdateAddon)
        
        if popupm.GetMenuItemCount() > popupcnt:
            popupm.AppendSeparator()
            popupcnt = popupm.GetMenuItemCount()
        
        popupm.Append(_id("popup-delete"), _("Delete"), _("Deletes selected addon(s)"))
        wx.EVT_MENU(self, _id("popup-delete"), self.OnDeleteSelected)
        
        if popupm.GetMenuItemCount() > popupcnt:
            popupm.AppendSeparator()
            popupcnt = popupm.GetMenuItemCount()
            
        if onlyOne:
            popupm.Append(_id("popup-edit"), _("Edit"), _("Edit addon settings"))
            wx.EVT_MENU(self, _id("popup-edit"), self.OnEditAddonSelected)
        else:
            # Allow the Site to be changed for selected addon(s)
            popupm.Append(_id("popup-change"), _("Change Site"), _("Changes selected addon(s) Site"))
            wx.EVT_MENU(self, _id("popup-change"), self.OnChangeSite)
        
        return popupm
    
    
    def GetListCtrl(self):
        """ Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
        and by the TypeAheadListCtrlMixin
        """
        tracer.log(WurmCommon.DEBUG5, "WurmUI - GetListCtrl")
        
        return self.lc
    
    
    def GetSecondarySortValues(self, col, key1, key2):
        """Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py"""
        tracer.log(WurmCommon.DEBUG5, "WurmUI - GetSecondarySortValues")
        # use the Addon name as the secondary sort value
        return (self.itemDataMap[key1][0], self.itemDataMap[key2][0])
    
    
    def GetSortImages(self):
        """Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py"""
        tracer.log(WurmCommon.DEBUG5, "WurmUI - GetSortImages")
        
        return (self.sm_dn, self.sm_up)
    
    
    def RefreshAddonList(self, clear=True, count=False):
        """"""
        tracer.debug("WurmUI - RefreshAddonList: %s, %s" % (clear, count))
        
        if clear:
            self.itemDataMap = {}
            self.lc.DeleteAllItems()
        
        k = WurmCommon.addonlist.keys()
        
        for a in k:
            aType = WurmCommon.addonlist.getAtype(a)
            if aType == "[Dummy]" and int(self._getSetting("HideDummy", 0)): # Hide dummy if set
                continue
            elif aType == "[Ignore]" and int(self._getSetting("HideIgnored", 0)): # Hide ignored if set
                continue
            elif aType == "[Outdated]" and int(self._getSetting("HideOutdated", 0)): # Hide outdated if set
                continue
            elif aType == "[Related]" and int(self._getSetting("HideRelated", 0)): # Hide related if set
                continue
            
            self._quickUpdateAddonList(a, updtype='add', atype=aType)
        
        # bypass if no visible addons
        if clear and len(self.itemDataMap) > 0:
            if threading.currentThread().getName() == "MainThread":
                try:
                    self.SortListItems(col=0, ascending=1) # re-sort after load
                except KeyError, details:
                    WurmCommon.outDebug("KeyError when trying to re-sort addon list")
            else:
                wx.PostEvent(self, ThreadCommsEvent(self.SortListItems, (), {'col':0, 'ascending':1}))
        
        if count:
            if threading.currentThread().getName() == "MainThread":
                self._displayAddonTotal()
            else:
                wx.PostEvent(self, ThreadCommsEvent(self._displayAddonTotal, (), {}))
    
    
    def RefreshInfoPanel(self, addon):
        """Refresh the RHS Info Panel"""
        tracer.log(WurmCommon.DEBUG5, "WurmUI - RefreshInfoPanel")
        
        global selectedaddon
        
        additionalHTML = ""
        
        try:
            if addon in WurmCommon.toclist:
                is_library = False
                
                title   = WurmCommon.toclist[addon].getTextField("Title", True)
                notes   = WurmCommon.toclist[addon].getTextField("Notes", True)
                author  = WurmCommon.toclist[addon].getTextField("Author", True)
                category= WurmCommon.toclist[addon].getTextField("X-Category", True)
                deps    = self._htmlDepList(WurmCommon.toclist[addon].getDependencies())
                optdeps = self._htmlDepList(WurmCommon.toclist[addon].getOptionalDeps())
                # Setup defaults if fields are blank
                if title == "":
                    title = addon
                if author == "":
                    author = "<i>Unknown</i>"
                if deps == "":
                    deps = "<i>None</i>"
                if optdeps == "":
                    optdeps = "<i>None</i>"
                
                if category == "Library":
                    is_library = True
                    additionalHTML += """<tr><td valign="top">Library:</td><td valign="top">Yes</td></tr>"""
                # logger.debug("TOC info: [%s, %s, %s, %s, %s]" % (title, notes, author, deps, optdeps))
                
                if addon in WurmCommon.addons:
                    # check to see if the addon has any related addons
                    related = ", ".join(WurmCommon.findAllRelated(addon))
                    if related:
                        additionalHTML += relatedHTML % (related)
                    # check to see if the Addon has any children
                    children = ", ".join(WurmCommon.findAllChildren(addon))
                    if children:
                        additionalHTML += childHTML % (children)
                    # check if the addon has a URL
                    if WurmCommon.addons[addon].getAddonURL():
                        additionalHTML += websiteHTML % (WurmCommon.addons[addon].getAddonURL())
                    # check if a changelog exists
                    chglog = WurmCommon.addons[addon]._getChangelogFilename()
                    if chglog:
                        additionalHTML += changelogHTML % ('file://' + chglog)
                 
# Begin patch 1866042 (part 2/2)
                usedby = ""
                optionallyusedby = ""
# Begin patch 1878044
                l = WurmCommon.toclist.keys()
                l.sort()
                for a in l:
# End patch 1878044
                    if (addon in WurmCommon.toclist[a].getDependencies()):
                        if len(usedby) == 0:
                            usedby = a
                        else:
                            usedby += ", " + a
                    
                    if (addon in WurmCommon.toclist[a].getOptionalDeps()):
                        if len(optionallyusedby) == 0:
                            optionallyusedby = a
                        else:
                            optionallyusedby += ", " + a
                
                if len(usedby) != 0:
                    additionalHTML += """<tr><td valign="top">Used by:</td><td valign="top">""" + usedby + """</td></tr>"""
                if len(optionallyusedby) != 0:
                    additionalHTML += """<tr><td valign="top">OptUsed by:</td><td valign="top">""" + optionallyusedby + """</td></tr>"""
# End patch 1866042 (part 2/2)
                
# TODO: Re-enable this when we're back in 1.7 beta
#                availrestore = []
#                if addon in WurmCommon.addons:
#                    availrestore = WurmCommon.addons[addon].getAvailableRestores()
#
#                if len(availrestore) != 0:
#                    additionalHTML += """<tr><td valign="top">s:</td><td valign="top">""" + ", ".join(["%s (%s)" % x[1:] for x in availrestore]) + """</td></tr>""" # Shows only version numbers and source
                
                self.p2.SetPage(rightPanelHTML % {'title': title, 'note': notes, 'author': author, 'deps': deps, 'optdeps': optdeps, 'additionalHTML': additionalHTML})
            else:
                # check to see if the Addon has a parent
                if WurmCommon.addonlist.getAtype(addon) == "Child":
                    additionalHTML += parentHTML % (WurmCommon.addonlist.getFlag(addon, "Parent"))
                self.p2.SetPage(rightPanelHTMLNoInfo % {'addonname': addon, 'text': _("No further info available (Addon missing, TOC missing or Child Addon)"), 'additionalHTML': additionalHTML})
        except Exception, details:
            logger.exception("Error getting TOC info: [%s]" % (details))
            raise
        
        selectedaddon = addon
    
    
    # Event Handlers Start Here
    def OnAbout(self, event):
        """"""
        tracer.debug("WurmUI - OnAbout")
        
        dlg = WUUAboutBox(self, wuuversion)
        dlg.ShowModal()
        dlg.Destroy()
    
    
    def OnAdd(self, event):
        """"""
        tracer.debug("WurmUI - OnAdd")
        
        # Flag as missing to prevent TOC errors
        WurmCommon.addonlist.add(WurmCommon.newaddon, flags={"missing": True})
        self.RefreshAddonList()
    
    
    def OnAdvancedRestore(self, event):
        """ Lets the user select any available previous version to revert the selected addon to """
        tracer.debug("WurmUI - OnAdvancedRestore")
        
        global callbackcount
        
        if self.lc.GetSelectedItemCount() != 1:
            WurmCommon.outStatus(_("Exactly one addon must be selected to use advanced restore"))
            return
        
        addon = WurmCommon.addons[self._getLcItems()[0]]
        
        WurmCommon.outStatus(_("Loading list of previous versions for %(aname)s") % {'aname': addon.localname})
        
        try:
            try:
                dlg = WurmAdvancedRestoreDlg(self, addon)
                if dlg.ShowModal() == wx.ID_OK:
                    if dlg.toRestore != None:
                        WurmCommon.outMessage("DEBUG: Would restore version %s from %s" % (dlg.toRestore[0], dlg.toRestore[2]))
                else:
                    WurmCommon.outStatus(_("No previous versions chosen for %(aname)s") % {'aname': addon.localname})
            except Exception, details:
                msg = _("Error on advanced restore: %(dets)s") % {'dets': str(details)}
                WurmCommon.outError(msg)
                # WurmCommon.outStatus(msg)
        finally:
            dlg.Destroy()
    
    
    def OnCacheFlushAll(self, event):
        """"""
        tracer.debug("WurmUI - OnCacheFlushAll")
        WurmCommon.clearCachePages()
    
    
    def OnCacheFlushExpired(self, event):
        """"""
        tracer.debug("WurmUI - OnCacheFlushExpired")
        WurmCommon.clearCachePages(False)
    
    
    def OnCacheToggle(self, event):
        """"""
        tracer.debug("WurmUI - OnCacheToggle")
        if event.Checked():
            setting = {':WebCache': '1'}
            self._applyNewSettings(setting)
        else:
            setting = {':WebCache': '0'}
            self._applyNewSettings(setting)
            WurmCommon.clearCachePages()
    
    
    def OnChangeSite(self, event):
        """ Change the Site for selected addon(s)"""
        tracer.debug("WurmUI - OnChangeSite")
        
        # get the item at the top of the List Control
        # it is used when refreshing the List Control
        self.topItem = self.lc.GetItemText(self.lc.GetTopItem())
        
        if self.lc.GetSelectedItemCount() == 0:
            WurmCommon.outStatus(_("No Addons selected to have their Site changed"))
            return
        
        # prompt for a Site to change to
        site = WUUDialogs.GetSite()
        if not site:
            return
        
        # Prompt for the Related Addon name if required
        if site == "[Related]":
            dlg = wx.TextEntryDialog(self, _('Related Addon'), _("Enter the Related Addon's Name"))
            if dlg.ShowModal() == wx.ID_OK:
                reladdon = dlg.GetValue()
            else:
                reladdon = None
            dlg.Destroy()
        
        toSet = self._getLcItems()
        
        WurmCommon.outStatus(_("Changing all selected Addons to site %(site)s") % {'site': site})
        
        toDelete = []
        for addon in toSet:
            # If the selected site is [Related] then use the entered Addon name
            if site == "[Related]":
                newsid = reladdon
            else:
                # Get the Site string from the dictionary
                newsid = availablesites[site][2]
                # Insert the Addonname into it, if required
                if newsid.count("%s") > 0:
                    newsid = newsid % (addon)
            
            # Update the addonlist dictionary
            WurmCommon.addonlist.add(addon, siteid=newsid, atype=site)
            # Update the addons dictionary, removing entries as necessary
            Wurm.refreshSingleAddon(addon)
            # Update the displayed List Control, any Addon that shouldn't be viewed will return False
            if not self._quickUpdateAddonList(addon, idx=-1, updtype='update', fname=addon, atype=site):
                toDelete.append(addon)
        
        # Remove any Addons that shouldn't be viewed from the List Control
        for addon in toDelete:
            ix = self._addonToIndex(addon)
            if ix:
                self.lc.DeleteItem(ix)
        
        # Refresh the List Control completely
        # fixes the issue with showing normally hidden addons etc
        self.RefreshAddonList()
        
        # now position the entry in the List Control
        self._showAddon()
        
        WurmCommon.outStatus(_("All selected Addons changed to site %(site)s - REMEMBER TO EDIT SITE IDs IF NECESSARY!") % {'site': site})
    
    
    def OnCheckDuplicates(self, event):
        """ Checks for duplicate settings """
        tracer.debug("WurmUI - OnCheckDuplicates")
        
        WurmCommon.outStatus(_("Checking for duplicate addon settings"))
        dupes = WurmCommon.findDuplicateSiteIDs()
        WurmCommon.outStatus(_("Check done, %(count)d duplicates found") % {'count': len(dupes)})
        
        if len(dupes) > 0:
            for ssid in dupes:
                dupetext = _("%(addonnames)s share the site|site id %(sitesid)s") % {'addonnames':", ".join(dupes[ssid]), 'sitesid': ssid}
                WurmCommon.outWarning(_("Duplicate found! %(dupetext)s") % {'dupetext': dupetext})
    
    
    def OnCheckOnlineDB(self, event):
        """ Checks all [Unknown] addons with the database """
        tracer.debug("WurmUI - OnCheckOnlineDB")
        
        msg = _("Checking [Unknown] Addons with the Online DB")
        WurmCommon.outMessage(msg)
        WurmCommon.outStatus(msg)
        
        try:
            changed = Wurm.identifyUnknownAddons()
            if changed > 0:
                msg = _("%(num)d Addon settings updated") % {'num': changed}
                WurmCommon.outMessage(msg)
                WurmCommon.outStatus(msg)
                self.RefreshAddonList()
            else:
                WurmCommon.outStatus(_("No Addons updated"))
        except Exception, details:
            msg = _("Online DB check failed: %(dets)s") % {'dets': str(details)}
            WurmCommon.outWarning(msg)
            WurmCommon.outStatus(msg)
    
    
    def OnCheckSavedVariables(self, event=None):
        """ Checks for unused SavedVariables, and asks user if they want to delete them """
        tracer.debug("WurmUI - OnCheckSavedVariables")
                
        usv = Wurm.identifyUnusedSavedVariables()
        
        if len(usv) > 0:
            sel = WUUDialogs.GetSavedVarsDelete(usv.keys())
            for s in sel:
                WurmCommon.outMessage("Removing %d SavedVariables for addon %s" % (len(usv[s]), s))
                for sv in usv[s]:
                    WurmCommon.outDebug("Deleting '%s'" % (sv,))
                    try:
                        os.remove(sv)
                    except Exception, details:
                        WurmCommon.outError("Could not delete '%s': %s" % (sv, str(details)))
        else:
            msg = _("No unused SavedVariables found")
            WurmCommon.outMessage(msg)
            WurmCommon.outStatus(msg)
    
    
    def OnClearStatusTimer(self, event):
        """Clear the Status Bar Text"""
        tracer.debug("WurmUI - OnClearStatusTimer")
        
        self.SetStatusText("")
    
    
    def OnCleanTemp(self, event=None, noprompt=False):
        """ Removes all files and subdirectories in Wurm's temp dir """
        tracer.debug("WurmUI - OnCleanTemp")
        
        answer = wx.ID_NO
        
        if not noprompt:
            msg = wx.MessageDialog(self, _("This will DELETE all files and folders in %(dir)s") % {'dir': WurmCommon.directories["temp"]}, _("Are you sure?"), style=wx.YES_NO|wx.ICON_WARNING)
            answer = msg.ShowModal()
            msg.Destroy()
        else:
            answer = wx.ID_YES
        
        if answer == wx.ID_YES:
            (cfile, cfolder) = WurmCommon._deletePathRecursive(WurmCommon.directories["temp"], deleteSelf=False)
            Wurm.initialize() # Re-init to recreate deleted folders in the directories["temp"], if any
            WurmCommon.outStatus(_("Temp dir cleaned; %(fnum)d files and %(dnum)d folders removed") % {'fnum': cfile, 'dnum': cfolder})
    
    
    def OnClose(self, event):
        """"""
        tracer.debug("WurmUI - OnClose")
        
        if WurmCommon.listchanged[WurmCommon.addonlist._id]:
            # Unsaved changes
            msg = wx.MessageDialog(self, _("You have some unsaved changes. Save now?"), _("Unsaved changes"), style=wx.YES_NO|wx.CANCEL|wx.ICON_QUESTION)
            answer = msg.ShowModal()
            msg.Destroy()
            if answer == wx.ID_YES:
                Wurm.saveAddonSettings()
            elif answer == wx.ID_CANCEL:
                return
        
        # Save the UI Settings
        self.showStatus(_("Saving UI Settings, please wait..."))
        self.saveUISettings()
        
        # Cleaning temp dir, if requested
        if int(self._getSetting("AutoCleanTemp", 0)):
            self.showStatus(_("Cleaning Temp dir, please wait..."))
            self.OnCleanTemp(noprompt=True)
        
        # Stop the addon handler queue if required
        if int(self._getSetting(":UseThreads", 0)):
            self.showStatus(_("Stopping queue handler, please wait..."))
            self.quu.stop()
        
        # Destroy the window
        self.Destroy()
    
    
    def OnColumnResize(self, event):
        """"""
        tracer.debug("WurmUI - OnColumnResize")
        
        colno   = event.m_col
        colsize = self.lc.GetColumnWidth(colno)
        # update settings with new value
        self.settings["LCcol" + str(colno)] = colsize
        
        event.Skip()
    
    
    def OnCopy(self, event):
        """"""
        tracer.debug("WurmUI - OnCopy")
        
        if wx.TheClipboard.Open():
            wx.TheClipboard.Clear()
            wx.TheClipboard.SetData(wx.TextDataObject(self.CopyXML()))
            wx.TheClipboard.Close()
        else:
            WurmCommon.outError("Could not access clipboard")
    
    
    def OnCopyBB(self, event):
        """"""
        tracer.debug("WurmUI - OnCopyBB")
        
        if wx.TheClipboard.Open():
            wx.TheClipboard.Clear()
            wx.TheClipboard.SetData(wx.TextDataObject(self.CopyBBCode()))
            wx.TheClipboard.Close()
        else:
            WurmCommon.outError("Could not access clipboard")
    
    
    def OnDeleteSelected(self, event=None):
        """ Deletes all selected addons - includes related addons even if not selected """
        tracer.debug("WurmUI - OnDeleteSelected")
        
        global totaltasks, callbackcount
        
        if self.lc.GetSelectedItemCount() == 0:
            WurmCommon.outStatus(_("No Addons selected to Delete"))
            return
        
        # get the item at the top of the List Control
        # it is used when refreshing the List Control
        self.topItem = self.lc.GetItemText(self.lc.GetTopItem())
        
        WurmCommon.outStatus(_("Checking Addons for Deletion"))
        
        toDelete, toRelate = self._getLcItems(getRelated=True)
        
        # Make sure there aren't any duplicates, then include them (this is partly just "fluff" to make the count right and have pretty dialogs)
        toRelate     = WurmCommon.uniq(toRelate)
        before       = len(toDelete)
        toDelete     = WurmCommon.uniq(toDelete + toRelate)
        after        = len(toDelete)
        relatedAdded = after - before
        relatext     = ""
        if relatedAdded > 0:
            relatext = _(" (and %(num)d related addon(s))") % {'num': relatedAdded}
        
        if len(toDelete) > 0:
            msg = wx.MessageDialog(self, _("Delete %(num)d selected Addon(s)%(rtext)s?") % {'num': before, 'rtext': relatext}, _("Are you sure?"), style=wx.YES_NO|wx.ICON_QUESTION)
            answer = msg.ShowModal()
            msg.Destroy()
            
            if answer == wx.ID_YES:
                WurmCommon.outStatus(_("%(num)d Addons queued for deletion, please wait...") % {'num': after})
                if int(self._getSetting(":UseThreads", 0)):
                    self.quu.addMultiTask("remote", "delete", toDelete, self._queueCallback)
                else:
                    callbackcount = len(toDelete)
                    totaltasks = float(callbackcount)
                    for addon in toDelete:
                        WurmCommon.DeleteAddons(addon, cleansettings=True)
                        self._queueCallback(addon, "delete")
                        wx.Yield()
            else:
                WurmCommon.outStatus(_("Removal of %(num)d Addon(s) cancelled") % {'num': after})
    
    
    def OnEditAddon(self, event):
        """"""
        tracer.debug("WurmUI - OnEditAddon")
        
        # get the item at the top of the List Control
        # it is used when refreshing the List Control
        self.topItem = self.lc.GetItemText(self.lc.GetTopItem())
        # WurmCommon.outDebug("OEA - Top Item is: %s" % (self.topItem))
        
        curitem  = event.m_itemIndex
        fitem    = self.lc.GetItem(curitem, 0).GetText()
        self.EditAddon(fitem, curitem)
    
    
    def OnEditAddonSelected(self, event):
        """ Opens an edit dialog on the first selected addon """
        
        # get the item at the top of the List Control
        # it is used when refreshing the List Control
        self.topItem = self.lc.GetItemText(self.lc.GetTopItem())
        # WurmCommon.outDebug("OEAS - Top Item is: %s" % (self.topItem))
        
        curitem = -1
        curitem = self.lc.GetNextItem(curitem, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if not curitem == -1:
            fitem = self.lc.GetItem(curitem, 0).GetText()
            self.EditAddon(fitem, curitem)
    
    
    def OnExport(self, event):
        """"""
        tracer.debug("WurmUI - OnExport")
        
        dlg = wx.FileDialog(self, _("Export to file"), "", datetime.now().strftime("export%Y%m%d.wurm.xml"), "WUU XML Files (*.xml)|*.xml", wx.SAVE|wx.OVERWRITE_PROMPT)
        
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            Wurm.saveAddonSettings(path)
            WurmCommon.outStatus(_("Exported list to %(path)s") % {'path': path})
        else:
            WurmCommon.outStatus(_("Export to file cancelled"))
            
        dlg.Destroy()
    
    
    def OnExportSelected(self, event):
        """"""
        tracer.debug("WurmUI - OnExportSelected")
        
        if self.lc.GetSelectedItemCount() == 0:
            WurmCommon.outStatus(_("No Addons selected to Export"))
            return
        
        WurmCommon.outStatus(_("Checking Addons for Export"))
        
        toExport = self._getLcItems()
        
        if len(toExport) > 0:
            dlg = wx.FileDialog(self, _("Export %(num)d selected Addons to file") % {'num': len(toExport)}, "", datetime.now().strftime("export%Y%m%d.wurm.xml"), "WUU XML Files (*.xml)|*.xml", wx.SAVE|wx.OVERWRITE_PROMPT)
            
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                Wurm.saveAddonSettings(path, toExport)
                WurmCommon.outStatus(_("Exported list of %(num)d selected Addons to %(path)s") % {'num': len(toExport), 'path': path})
            else:
                WurmCommon.outStatus(_("Export of selected Addons to file cancelled"))
            
            dlg.Destroy()
    
    
    def OnHideDummy(self, event):
        """"""
        tracer.debug("WurmUI - OnHideDummy")
        
        if event.Checked():
            self.settings["HideDummy"] = "1"
        else:
            self.settings["HideDummy"] = "0"
        
        self.RefreshAddonList()
    
    
    def OnHideIgnored(self, event):
        """"""
        tracer.debug("WurmUI - OnHideIgnored")
        
        if event.Checked():
            self.settings["HideIgnored"] = "1"
        else:
            self.settings["HideIgnored"] = "0"
        
        self.RefreshAddonList()
    
    
    def OnHideOutdated(self, event):
        """"""
        tracer.debug("WurmUI - OnHideOutdated")
        
        if event.Checked():
            self.settings["HideOutdated"] = "1"
        else:
            self.settings["HideOutdated"] = "0"
        
        self.RefreshAddonList()
    
    
    def OnHideRelated(self, event):
        """"""
        tracer.debug("WurmUI - OnHideOutdated")
        
        if event.Checked():
            self.settings["HideRelated"] = "1"
        else:
            self.settings["HideRelated"] = "0"
        
        self.RefreshAddonList()
    
    
    def OnIdentifySelectedByURL(self, event):
        """ Goes through all selected addons in sequence, and asks for an URL to identify it """
        tracer.debug("WurmUI - OnIdentifyByURL")
        
        msg = _("Trying to identify all selected addons")
        WurmCommon.outStatus(msg)
        WurmCommon.outMessage(msg)
        
        toUpdate = self._getLcItems(state="SELECTED")
        
        if len(toUpdate) > 0:
            #TODO: Add threading possibility here
            for addon in toUpdate:
                if addon not in WurmCommon.addons:
                    dlg = wx.TextEntryDialog(self, _('Enter Addon %(aname)s URL') % {'aname':addon}, _('Identify Addon %(aname)s') % {'aname':addon})
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        addonurl = dlg.GetValue()
                        
                        WurmCommon.outStatus(_("Identifying %(aurl)s, please wait...") % {'aurl': addonurl})
                        try:
                            addetails = Wurm.identifyAddonFromURL(addonurl)
                            msg = _("Addon identified successfully as %(site)s/%(siteid)s!") % {'site':addetails[1], 'siteid':addetails[2]}
                            WurmCommon.outMessage(msg)
                            WurmCommon.addonlist.add(addon, atype=addetails[1], siteid=addetails[2])
                            
                            self._quickUpdateAddonList(addon, updtype='add', fname=addon, atype=addetails[1])
                            
                            # Update the addons dictionary, removing entries as necessary
                            Wurm.refreshSingleAddon(addon)
                        except Wurm.WurmURLParseException, details:
                            WurmCommon.outError("Error identifying %s\n%s" % (addonurl, str(details)))
                            WurmCommon.outStatus(_("Error identifying %(aurl)s") % {'aurl': addonurl})
                    
                    dlg.Destroy()
                    
                    wx.Yield()
            self.RefreshAddonList(count=True)
        else:
            WurmCommon.outStatus(_("No Addons to ID"))
        
        WurmCommon.outStatus(_("Finished identifying all selected addons"))
    
    
    def OnIdentifySelectedUnknown(self, event=None):
        """ Tries to identify the selected [Unknown] addons against the online db """
        tracer.debug("WurmUI - OnIdentifySelectedUnknown")
        
        msg = _("Trying to identify all selected addons")
        WurmCommon.outStatus(msg)
        WurmCommon.outMessage(msg)
        
        toUpdate = self._getLcItems(state="SELECTED")
        
        # WurmCommon.outMessage("DEBUG: LIST OF ITEMS %s" % (str(toUpdate)))
        
        if len(toUpdate) > 0:
            #TODO: Add threading possibility here
            for addon in toUpdate:
                # WurmCommon.outMessage("DEBUG: Checking %s" % (addon))
                if addon not in WurmCommon.addons:
                    # WurmCommon.outMessage("DEBUG: is unknown")
                    addetails = Wurm.lookupSiteID(addon)
                    # addetails is either None, or a (localname, site, siteid) tuple
                    if addetails:
                        WurmCommon.outMessage(_("Addon %(aname)s identified as %(site)s/%(siteid)s") % {'aname':addetails[0], 'site':addetails[1], 'siteid':addetails[2]})
                        WurmCommon.addonlist.add(addon, fname=addon, atype=addetails[1], siteid=addetails[2])
                        
                        self._quickUpdateAddonList(addon, updtype='add', fname=addon, atype=addetails[1])
                        
                        # Update the addons dictionary, removing entries as necessary
                        Wurm.refreshSingleAddon(addon)
                        self.topItem = addon
                    else:
                        WurmCommon.outMessage("Nothing in online db")
                    wx.Yield()
            self.RefreshAddonList(count=True)
            self._showAddon()
        else:
            WurmCommon.outStatus(_("No Addons to ID"))
        
        WurmCommon.outStatus(_("Finished identifying all selected addons"))
    
    
    def OnImport(self, event):
        """ Imports, and optionally downloads and installs addons from an xml file """
        tracer.debug("WurmUI - OnImport")
        
        dlg = wx.FileDialog(self, _("Import from file"), "", "", "Wurm XML Files (*.xml)|*.xml", wx.OPEN)
        
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            WurmCommon.listchanged[WurmCommon.addonlist._id] = False
            (WurmCommon.addonlist, WurmCommon.toclist) = Wurm.getAddonSettings(path)
            
            msg = wx.MessageDialog(self, _("Should WUU download and install all Addons imported automatically? This SHOULD be done on an empty AddOns-directory!"), _("Install imported Addons?"), style=wx.YES_NO|wx.ICON_WARNING)
            answer = msg.ShowModal()
            msg.Destroy()
            
            if answer == wx.ID_YES:
                self.OnScan(True)
                WurmCommon.outStatus(_("File %(path)s imported and installed") % {'path': path})
            elif answer == wx.ID_NO:
                WurmCommon.outStatus(_("File %(path)s imported, no Addons installed") % {'path': path})
            
            WurmCommon.listchanged[WurmCommon.addonlist._id] = True
        
        dlg.Destroy()
    
    
    def OnImportPack(self, event):
        """ Imports, and optionally downloads and installs addons from an addon pack on the web site """
        tracer.debug("WurmUI - OnImportPack")
        
        dlg = wx.TextEntryDialog(self, _('Enter Addon pack ID'), _('Import from Addon pack'))
        
        if dlg.ShowModal() == wx.ID_OK:
            packid = dlg.GetValue()
            if len(packid) != 32: # a MD5 hash is 32 bytes long
                WurmCommon.outError("Invalid addon pack ID - should be 32 characters long")
                return False
            
            WurmCommon.listchanged[WurmCommon.addonlist._id] = False
            (WurmCommon.addonlist, WurmCommon.toclist) = Wurm.getAddonSettingsPack(packid)
            
            msg = wx.MessageDialog(self, _("Should WUU download and install all Addons imported automatically? This SHOULD be done on an empty AddOns-directory!"), _("Install imported Addons?"), style=wx.YES_NO|wx.ICON_WARNING)
            answer = msg.ShowModal()
            msg.Destroy()
            
            if answer == wx.ID_YES:
                self.OnScan(True)
                WurmCommon.outStatus(_("Addon pack %(packid)s imported and installed") % {'packid': packid})
            elif answer == wx.ID_NO:
                WurmCommon.outStatus(_("Addon pack %(packid)s imported, no Addons installed") % {'packid': packid})
            
            WurmCommon.listchanged[WurmCommon.addonlist._id] = True
        
        dlg.Destroy()
    
    
    def OnImportURL(self, event):
        """ Imports and installs an addon, given the addon URL """
        tracer.debug("WurmUI - OnImportURL")
        
        dlg = wx.TextEntryDialog(self, _('Enter Addon URL'), _('Import from Addon URL'))
        
        newaddon = ""
        if dlg.ShowModal() == wx.ID_OK:
            addonurl = dlg.GetValue()
            
            WurmCommon.outStatus(_("Installing %(aurl)s, please wait...") % {'aurl': addonurl})
            try:
                newaddon = Wurm.installAddonFromURL(addonurl)
                if newaddon.addontype in typeManualDl:
                    msg = (_("%s added successfully") % newaddon.localname)
                else:
                    msg = (_("%s installed successfully!") % newaddon.localname)
                WurmCommon.outMessage(msg)
                WurmCommon.outStatus(msg)
                self.RefreshAddonList(count=True)
                self.topItem = newaddon.localname
                # now position the entry in the List Control
                self._showAddon()
            except Exception, details:
                WurmCommon.outError("Error installing %s: %s" % (addonurl, str(details)))
                WurmCommon.outStatus(_("Error installing %(aurl)s") % {'aurl': addonurl})
        
        dlg.Destroy()
        
        # display a dialog to explain how to install an Addon which needs a manual download
        if newaddon.addontype in typeManualDl:
            msg = wx.MessageDialog(self, _("To complete the installation of the addon please follow these steps:\n\n\t1: right-click the Addon and choose Open download page\n\t2: click the download link on the Addon's Web page\n\t3: right-click the Addon and choose Update from File"), _('Installing an addon needing a manual download'), style=wx.OK|wx.ICON_INFORMATION)
            msg.ShowModal()
            msg.Destroy()
    
    
    def OnInstallCosmos(self, event):
        """"""
        tracer.debug("WurmUI - OnInstallCosmos")
        
        global totaltasks, callbackcount
        
        WurmCommon.outStatus(_("Loading Cosmos Addons"))
        
        try:
            try:
                (adlist, adtoclist) = Wurm.getCosmosAddonSettings()
                self.Visible        = False
                dlg                 = WurmAddonInstallDlg(self, adlist, adtoclist, self.settings, "Cosmos")
                dlg.ShowModal()
                dlg.Destroy()
                if len(WUUDialogs.installlist) > 0:
                    if int(self._getSetting(":UseThreads", 0)):
                        self.quu.addMultiTask("remote", "install", WUUDialogs.installlist, self._queueCallback)
                    else:
                        callbackcount = len(WUUDialogs.installlist)
                        totaltasks = float(callbackcount)
                        for addon in WUUDialogs.installlist:
                            WurmCommon.InstallAddon(addon)
                            self._queueCallback(addon, "install")
                            wx.Yield()
                else:
                    WurmCommon.outStatus(_("Nothing to Install"))
            except Exception, details:
                msg = _("Error installing from Cosmos: %(dets)s") % {'dets': str(details)}
                WurmCommon.outError(msg)
                WurmCommon.outStatus(msg)
        finally:
            self.Visible = True
    
    
    def OnListContextMenu(self, event):
        """ Pops up the context menu tailored to the current selection """
        tracer.log(WurmCommon.DEBUG5, "WurmUI - OnListContextMenu")
        
        menu = self.GetListContextMenu()
        if not menu:
            return
        
        self.PopupMenu(menu)
        menu.Destroy()
    
    
    def OnListItemSelected(self, event):
        """"""
        tracer.log(WurmCommon.DEBUG5, "WurmUI - OnListItemSelected")
        
        count = self.lc.GetSelectedItemCount()
        
        if count == 1:
            curitem = event.m_itemIndex
            fitem   = self.lc.GetItem(curitem, 0).GetText()
            self.RefreshInfoPanel(fitem)
        elif count > 1:
            self.p2.SetPage(rightPanelHTMLDefault % {'text': _("%(count)s addons selected") % {'count':count}, 'info': ''})
    
    
    def OnLoad(self, event):
        """"""
        tracer.debug("WurmUI - OnLoad")
        
        if os.path.exists(Wurm.addondatafile):
            (WurmCommon.addonlist, WurmCommon.toclist) = Wurm.getAddonSettings(Wurm.addondatafile)
        
        # # Disable the WoWAce menu
        # self.menubar.Enable(self._getID("m>t>wa"), False)
        # 
        self.OnScan(None)
    
    
    def OnMerge(self, event):
        """"""
        tracer.debug("WurmUI - OnMerge")
        
        dlg = wx.FileDialog(self, _("Import site settings from file"), "", "", "Wurm XML Files (*.xml)|*.xml", wx.OPEN)
        
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            Wurm.mergeSettings(path)
            self.RefreshAddonList(count=True)
        
        dlg.Destroy()
    
    
    def OnMove(self, event):
        """"""
        tracer.debug("WurmUI - OnMove")
        
        pos = self.GetPosition()
        # update settings with new values
        self.settings["FrameX"] = pos.x
        self.settings["FrameY"] = pos.y
        
        event.Skip()
    
    
    def OnNBPageChanged(self, event):
        """ Scrolls the logwindow to the latest event """
        tracer.debug("WurmUI - OnNBPageChanged")
        
        lwGLP = self.logwindow.GetLastPosition()
        # FIXME: Fix this - doesn't work right at the moment
        logger.log(WurmCommon.DEBUG5, "OnNBPageChanged - GLP: %d" % (lwGLP))
        self.logwindow.ShowPosition(lwGLP)
        
        event.Skip()
    
    
    def OnOpenAddonDir(self, event):
        """"""
        tracer.debug("WurmUI - OnOpenAddonDir")
        
        webbrowser.open('file://' + WurmCommon.directories["addons"])
    
    
    def OnOpenAddonPage(self, event):
        """ Opens the first selected addon's webpage in the primary browser """
        
        curitem = -1
        curitem = self.lc.GetNextItem(curitem, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if not curitem == -1:
            fitem = self.lc.GetItem(curitem, 0).GetText()
            
            if fitem in WurmCommon.addons:
                url = WurmCommon.addons[fitem].getAddonURL()
                if url:
                    webbrowser.open(url)
    
    
    def OnOpenAddonDlPage(self, event):
        """ Opens the first selected addon's download page in the primary browser """
        
        curitem = -1
        curitem = self.lc.GetNextItem(curitem, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if not curitem == -1:
            fitem = self.lc.GetItem(curitem, 0).GetText()
            
            if fitem in WurmCommon.addons:
                url = WurmCommon.addons[fitem].getAddonDlURL()
                if url:
                    webbrowser.open(url)
    
    
    def OnOpenAddonDlPageSmart(self, event):
        """ Opens addon page for all addons that need it """
        
        toCheck = self._getLcItems("ALL", hasUpdate=True)
        
        found = []
        
        for a in toCheck:
            if WurmCommon.addonlist.getAtype(a) in typeManualDl:
                url = WurmCommon.addons[a].getAddonDlURL()
                if url:
                    webbrowser.open(url)
                    found.append(a)
                wx.Yield()
        
        if len(found) > 0:
            msg = wx.MessageDialog(self, _("WUU can prompt you to select the file for each addon in sequence now.\nDo you want to use this feature?"), _("Update from files?"), style=wx.YES_NO|wx.ICON_QUESTION)
            answer = msg.ShowModal()
            msg.Destroy()
            
            if answer == wx.ID_YES:
                global totaltasks, callbackcount
                WurmCommon.outStatus(_("%(num)d Addons queued for update, please wait...") % {'num': len(found)})
                callbackcount = len(found)
                totaltasks = float(callbackcount)
                WurmCommon.outProgressPercent2(callbackcount/totaltasks) # show progress bar
                for addon in found:
                    if addon in WurmCommon.addons:
                        self.updateAddonFromFileSelect(addon)
                        wx.Yield()
    
    
    def OnOpenAddonFilesDlPage(self, event):
        """ Opens the first selected addon's all files page in the primary browser """
        
        curitem = -1
        curitem = self.lc.GetNextItem(curitem, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if not curitem == -1:
            fitem = self.lc.GetItem(curitem, 0).GetText()
            
            if fitem in WurmCommon.addons:
                url = WurmCommon.addons[fitem].getAddonFilesDlURL()
                if url:
                    webbrowser.open(url)
    
    
    def OnOpenSiteAuctioneer(self, event):
        """"""
        tracer.debug("WurmUI - OnOpenSiteAuctioneer")
        
        webbrowser.open(availablesites["Auctioneer"][0])
    
    
    def OnOpenSiteCapnBry(self, event):
        """"""
        tracer.debug("WurmUI - OnOpenSiteCapnBry")
        
        webbrowser.open(availablesites["CapnBry"][0])
    
    
    def OnOpenSiteCosmos(self, event):
        """"""
        tracer.debug("WurmUI - OnOpenSiteCosmos")
        
        webbrowser.open(availablesites["Cosmos"][0])
    
    
    def OnOpenSiteCTMod(self, event):
        """"""
        tracer.debug("WurmUI - OnOpenSiteCTMod")
        
        webbrowser.open(availablesites["CTMod"][0])
    
    
    def OnOpenSiteCurseGaming(self, event):
        """"""
        tracer.debug("WurmUI - OnOpenSiteCurseGaming")
        
        webbrowser.open(availablesites["CurseGaming"][0])
    
    
    def OnOpenSiteGatherer(self, event):
        """"""
        tracer.debug("WurmUI - OnOpenSiteGatherer")
        
        webbrowser.open(availablesites["Gatherer"][0])
    
    
    def OnOpenSiteGoogleCode(self, event):
        """"""
        tracer.debug("WurmUI - OnOpenSiteGoogleCode")
        
        webbrowser.open(availablesites["GoogleCode"][0])
    
    
    def OnOpenSiteWoWUI(self, event):
        """"""
        tracer.debug("WurmUI - OnOpenSiteWoWUI")
        
        webbrowser.open(availablesites["WoWUI"][0])
    
    
    def OnOpenSiteWoWAce(self, event):
        """"""
        tracer.debug("WurmUI - OnOpenSiteWoWAce")
        
        webbrowser.open(availablesites["WoWAce"][0])
    
    
    def OnOpenSiteWoWI(self, event):
        """"""
        tracer.debug("WurmUI - OnOpenSiteWoWI")
        
        webbrowser.open(availablesites["WoWI"][0])
    
    
    def OnOpenWUUki(self, event):
        """"""
        tracer.debug("WurmUI - OnOpenWUUki")
        
        webbrowser.open(WurmCommon.wuuki)
    
    
    def OnOpenWUUSFWeb(self, event):
        """"""
        tracer.debug("WurmUI - OnOpenWUUSFWeb")
        
        webbrowser.open(WurmCommon.wuusf)
    
    
    def OnOpenWUUWeb(self, event):
        """"""
        tracer.debug("WurmUI - OnOpenWUUWeb")
        
        webbrowser.open(WurmCommon.wuusite)
    
    
    def OnPreferences(self, event):
        """"""
        tracer.debug("WurmUI - OnPreferences")
        
        dlg = WUUPreferencesDlg(self, self._getID("prefsdlg"), self.settings)
        if dlg.ShowModal() == wx.ID_OK:
            self._applyNewSettings(dlg.settingslist)
        dlg.Destroy()
    
    
    def OnPurgeMissing(self, event):
        """ Remove all addons marked as "missing" """
        tracer.debug("WurmUI - OnPurgeMissing")
        
        count = Wurm.purgeMissing()
        if count > 0:
            self.RefreshAddonList()
    
    
    def OnQuit(self, event):
        """"""
        tracer.debug("WurmUI - OnQuit")
        
        self.Close()
    
    
    def OnResize(self, event):
        """"""
        tracer.debug("WurmUI - OnResize")
        
        size = self.GetSize()
        # update settings with new values
        self.settings["FrameW"] = size.x
        self.settings["FrameH"] = size.y
        
        event.Skip()
    
    
    def OnRestoreSelected(self, event=None):
        """ Restores all selected addons """
        tracer.debug("WurmUI - OnRestoreSelected")
        
        global totaltasks, callbackcount
        
        # get the item at the top of the List Control
        # it is used when refreshing the List Control
        self.topItem = self.lc.GetItemText(self.lc.GetTopItem())
        # WurmCommon.outDebug("ORS - Top Item is: %s" % (self.topItem))
        
        if self.lc.GetSelectedItemCount() == 0:
            WurmCommon.outStatus(_("No Addons selected to Restore"))
            return
        
        WurmCommon.outStatus(_("Checking Addons for Restoration"))
        
        toRestore, toRelate = self._getLcItems(hasBackup=True, getRelated=True)
        
        # Make sure there aren't any duplicates, then include them (this is partly just "fluff" to make the count right and have pretty dialogs)
        toRelate     = WurmCommon.uniq(toRelate)
        before       = len(toRestore)
        toRestore    = WurmCommon.uniq(toRestore + toRelate)
        after        = len(toRestore)
        relatedAdded = after - before
        relatext     = ""
        if relatedAdded > 0:
            relatext = _(" (and %(num)d related addon(s))") % {'num': relatedAdded}
        
        if len(toRestore) > 0:
            msg = wx.MessageDialog(self, _("Restore %(num)d selected Addon(s)%(rtext)s?") % {'num': before, 'rtext': relatext}, _("Are you sure?"), style=wx.YES_NO|wx.ICON_QUESTION)
            answer = msg.ShowModal()
            msg.Destroy()
            
            if answer == wx.ID_YES:
                WurmCommon.outStatus(_("%(num)d Addons queued for restoration, please wait...") % {'num': len(toRestore)})
                if int(self._getSetting(":UseThreads", 0)):
                    self.quu.addMultiTask("remote", "restore", toRestore, self._queueCallback)
                else:
                    callbackcount = len(toRestore)
                    totaltasks = float(callbackcount)
                    for addon in toRestore:
                        WurmCommon.RestoreAddon(addon)
                        self._queueCallback(addon, "restore")
                        wx.Yield()
            else:
                WurmCommon.outStatus(_("Restore of %(num)d Addon(s) cancelled") % {'num': len(toRestore)})
    
    
    def OnSashPositionChanged(self, event):
        """"""
        tracer.debug("WurmUI - OnSashPositionChanged")
        
        size     = self.GetSize()
        sashposn = self.splitter.GetSashPosition()
        # update settings with new value
        self.settings["SashOffset"] = (sashposn - size.x)
        
        event.Skip()
    
    
    def OnSave(self, event):
        """"""
        tracer.debug("WurmUI - OnSave")
        
        Wurm.saveAddonSettings()
    
    
    def OnScan(self, event):
        """"""
        tracer.debug("WurmUI - OnScan")
        
        global totaltasks, callbackcount
        
        if event:
            fim = True
        else:
            fim = False
        
        WurmCommon.outStatus(_("Scanning Addon directory"))
        
        toInstall = Wurm.scanAddons(forceInstallMissing=fim)
        # Check to see if any addons need to be installed
        if len(toInstall) > 0:
            WurmCommon.outStatus(_("%(num)d missing Addons queued for installation, please wait...") % {'num': len(toInstall)})
            if int(self._getSetting(":UseThreads", 0)):
                self.quu.addMultiTask("remote", "install", toInstall, self._queueCallback)
            else:
                callbackcount = len(toInstall)
                totaltasks = float(callbackcount)
                for addon in toInstall:
                    WurmCommon.InstallAddon(addon)
                    self._queueCallback(addon, "install")
                    wx.Yield()
        else:
            Wurm.refreshAddons()
            
        self.RefreshAddonList(count=True)
    
    
    def OnSetAutoload(self, event):
        """"""
        tracer.debug("WurmUI - OnSetAutoload")
        
        if event.Checked():
            self.settings["Autoload"] = "1"
        else:
            self.settings["Autoload"] = "0"
    
    
    def OnSetVersionCheck(self, event):
        """"""
        tracer.debug("WurmUI - OnSetVersionCheck")
        
        if event.Checked():
            self.settings["CheckWUUVersion"] = "1"
            self.checkOnlineVersion()
        else:
            self.settings["CheckWUUVersion"] = "0"
    
    
    def OnSyncAddon(self, event):
        """"""
        tracer.debug("WurmUI - OnSyncAddon")
        
        global totaltasks, callbackcount
        
        # get the item at the top of the List Control
        # it is used when refreshing the List Control
        self.topItem = self.lc.GetItemText(self.lc.GetTopItem())
        # WurmCommon.outDebug("OSA - Top Item is: %s" % (self.topItem))
        
        if self.lc.GetSelectedItemCount() == 0:
            WurmCommon.outStatus(_("No Addons selected to version check"))
            return
        
        WurmCommon.outStatus(_("Checking Online Version"))
        
        toCheck = self._getLcItems(inAddons=True)
        
        WurmCommon.outStatus(_("%(num)d Addons queued for version check, please wait...") % {'num': len(toCheck)})
        if int(self._getSetting(":UseThreads", 0)):
            self.quu.addMultiTask("remote", "version", toCheck, self._queueCallback)
        else:
            callbackcount = len(toCheck)
            totaltasks = float(callbackcount)
            for addon in toCheck:
                if addon in WurmCommon.addons:
                    WurmCommon.addons[addon].sync()
                self._queueCallback(addon, "version")
                wx.Yield()
    
    
    def OnSyncAll(self, event):
        """ Checks the online version of all addons """
        tracer.debug("WurmUI - OnSyncAll")
        
        global totaltasks, callbackcount
        
        WurmCommon.outStatus(_("Checking all Addon versions"))
        # WurmCommon.resetWoWAceCache() # resets the wowace version cache
        
        toCheck = self._getLcItems(state="ALL", inAddons=True)
        
        WurmCommon.outStatus(_("All Addons are queued for version check, please wait..."))
        if int(self._getSetting(":UseThreads", 0)):
            self.quu.addMultiTask("remote", "version", toCheck, self._queueCallback)
        else:
            callbackcount = len(toCheck)
            totaltasks = float(callbackcount)
            for addon in toCheck:
                if addon in WurmCommon.addons:
                    WurmCommon.addons[addon].sync()
                self._queueCallback(addon, "version")
                wx.Yield()
    
    
    def OnThreadComms(self, event):
        """ Handle ThreadComms Events.
        This allows threads to get the Main Thread to perform functions that aren't thread safe.
        """
        tracer.log(WurmCommon.DEBUG5, "WurmUI - OnThreadComms")
        
        try:
            event.func(*event.args, **event.kwargs)
        except Exception, details:
            logger.exception("Error calling: %s: %s, %s\n%s" % (event.func , str(event.args), str(event.kwargs), str(details)))
            raise
    
    
    def OnUpdateAddon(self, event):
        """"""
        tracer.debug("WurmUI - OnUpdateAddon")
        
        global totaltasks, callbackcount
        
        # get the item at the top of the List Control
        # it is used when refreshing the List Control
        self.topItem = self.lc.GetItemText(self.lc.GetTopItem())
        # WurmCommon.outDebug("OUA - Top Item is: %s" % (self.topItem))
        
        if self.lc.GetSelectedItemCount() == 0:
            WurmCommon.outStatus(_("No Addons selected to update"))
            return
        
        WurmCommon.outStatus(_("Updating selected Addons"))
        
        toUpdate = self._getLcItems(inAddons=True)
        
        WurmCommon.outStatus(_("All selected Addons are queued for update, please wait..."))
        if int(self._getSetting(":UseThreads", 0)):
            self.quu.addMultiTask("remote", "update", toUpdate, self._queueCallback)
        else:
            callbackcount = len(toUpdate)
            totaltasks = float(callbackcount)
            for addon in toUpdate:
                if addon in WurmCommon.addons:
                    WurmCommon.addons[addon].updateMod()
                self._queueCallback(addon, "update")
                wx.Yield()
    
    
    def OnUpdateAllNewer(self, event):
        """ Updates all addons that have newer online versions (and tries updating those with unknown local version).
        - Requires addons to be synced with the online version manually first (or Check All Versions)
        """
        tracer.debug("WurmUI - OnUpdateAllNewer")
        
        global totaltasks, callbackcount
        
        WurmCommon.outStatus(_("Updating all Addons with a newer online version"))
        
        toUpdate = self._getLcItems(state="ALL", hasUpdate=True)
        
        if len(toUpdate) > 0:
            WurmCommon.outStatus(_("%(num)d Addons queued for update, please wait...") % {'num': len(toUpdate)})
            if int(self._getSetting(":UseThreads", 0)):
                self.quu.addMultiTask("remote", "update", toUpdate, self._queueCallback)
            else:
                callbackcount = len(toUpdate)
                totaltasks = float(callbackcount)
                for addon in toUpdate:
                    if addon in WurmCommon.addons:
                        WurmCommon.addons[addon].updateMod()
                    self._queueCallback(addon, "update")
                    wx.Yield()
        
        else:
            WurmCommon.outStatus(_("No Addons to Update"))
    
    
    def OnUpdateAllSmart(self, event):
        """ Updates all addons that have newer online versions (and tries updating those with unknown local version)
            - will check the addon version before updating, so no sync is needed before calling
        """
        tracer.debug("WurmUI - OnUpdateAllSmart")
        
        global totaltasks, callbackcount
        
        WurmCommon.outStatus(_("Updating all Addons with a newer online version"))
        
        toUpdate = self._getLcItems(state="ALL")
        
        if len(toUpdate) > 0:
            WurmCommon.outStatus(_("%(num)d Addons queued for update, please wait...") % {'num': len(toUpdate)})
            if int(self._getSetting(":UseThreads", 0)):
                self.quu.addMultiTask("remote", "smartupdate", toUpdate, self._queueCallback)
            else:
                callbackcount = len(toUpdate)
                totaltasks = float(callbackcount)
                for addon in toUpdate:
                    if addon in WurmCommon.addons:
                        success = WurmCommon.addons[addon].smartUpdateMod()
                        self._queueCallback(addon, "smartupdate", status=success)
                        wx.Yield()
        else:
            WurmCommon.outStatus(_("No Addons to Update"))
    
    
    def OnUpdateFromFile(self, event):
        """ Updates all selected addons from their downloaded files (prompting for each one) """
        tracer.debug("WurmUI - OnUpdateFromFile")
        
        global totaltasks, callbackcount
        
        WurmCommon.outStatus(_("Updating all Addons from their downloaded files"))
        
        toUpdate = self._getLcItems(inAddons=True)
        
        if len(toUpdate) > 0:
            WurmCommon.outStatus(_("%(num)d Addons queued for update, please wait...") % {'num': len(toUpdate)})
            callbackcount = len(toUpdate)
            totaltasks = float(callbackcount)
            WurmCommon.outProgressPercent2(callbackcount/totaltasks) # show progress bar
            for addon in toUpdate:
                if addon in WurmCommon.addons:
                    self.updateAddonFromFileSelect(addon)
                    wx.Yield()
        else:
            WurmCommon.outStatus(_("No Addons to Update"))
    
    
    def OnUpdateSelectedSmart(self, event):
        """ Updates all selected addons that have newer online versions (and tries updating those with unknown local version)
            - will check the addon version before updating, so no sync is needed before calling
        """
        tracer.debug("WurmUI - OnUpdateSelectedSmart")
        
        global totaltasks, callbackcount
        
        WurmCommon.outStatus(_("Updating all selected Addons with a newer online version"))
        
        toUpdate = self._getLcItems(state="SELECTED")
        
        if len(toUpdate) > 0:
            WurmCommon.outStatus(_("%(num)d Addons queued for update, please wait...") % {'num': len(toUpdate)})
            if int(self._getSetting(":UseThreads", 0)):
                self.quu.addMultiTask("remote", "smartupdate", toUpdate, self._queueCallback)
            else:
                callbackcount = len(toUpdate)
                totaltasks = float(callbackcount)
                for addon in toUpdate:
                    if addon in WurmCommon.addons:
                        success = WurmCommon.addons[addon].smartUpdateMod()
                        self._queueCallback(addon, "smartupdate", status=success)
                        wx.Yield()
        else:
            WurmCommon.outStatus(_("No Addons to Update"))
    
    
    def OnUpdateVersionSelected(self, event):
        """ Updates the local version to the online version for all selected addons """
        tracer.debug("WurmUI - OnUpdateVersionSelected")
        
        global totaltasks, callbackcount
        
        WurmCommon.outStatus(_("Updating all selected Addons local version"))
        
        toUpdate = self._getLcItems(state="SELECTED")
        
        if len(toUpdate) > 0:
            WurmCommon.outStatus(_("%(num)d Addons queued for update, please wait...") % {'num': len(toUpdate)})
            if int(self._getSetting(":UseThreads", 0)):
                self.quu.addMultiTask("remote", "updlocalver", toUpdate, self._queueCallback)
            else:
                callbackcount = len(toUpdate)
                totaltasks = float(callbackcount)
                for addon in toUpdate:
                    if addon in WurmCommon.addons:
                        success = WurmCommon.addons[addon].smartUpdateMod()
                        self._queueCallback(addon, "updlocalver", status=success)
                        wx.Yield()
        else:
            WurmCommon.outStatus(_("No Addons to Update"))
    
    
    def OnUploadAddonlist(self, event):
        """ Uploads the current addon list to the master database """
        tracer.debug("WurmUI - OnUploadAddonlist")
        
        WurmCommon.outStatus(_("Uploading Addons, please wait..."))
        try:
            Wurm.uploadInfo()
        except:
            msg = _("Upload failed")
            WurmCommon.outWarning(msg)
            WurmCommon.outStatus(msg)
    


class WurmApp(wx.App):
    def OnInit(self):
        """"""
        tracer.debug("WurmApp - OnInit")
        
        # Make WUU look more like a browser
        try:
            WurmCommon.setUserAgent(wuuversion)
        except:
            pass # We don't care if it's not successfully set
        
        # Create the UI
        try:
            ui = WurmUI(_('WoW UI Updater %(ver)s') % {'ver': wuuversion})
        except Exception, details:
            raise
        
        tracer.debug("UI created, displaying it now")
        
        # display the UI
        ui.Show()
        
        return True
    


def runTheApp():
    """ Run the Application """
    
    global logger, tracer
    
    # Setup Loggers
    logger = logging.getLogger(None)
    tracer = logging.getLogger("WUUtrace")
    # define the Handlers
    logrfh  = logging.handlers.RotatingFileHandler(logfile, "a", 1024 * 1024, 5)
    tracefh = logging.FileHandler(tracefile, "w")
    # define the Formatters
    simpleform   = logging.Formatter('%(asctime)s (%(levelname)-7s) %(message)s', '%Y-%m-%d %H:%M:%S')
    detailedform = logging.Formatter('%(asctime)s %(levelname)-7s %(module)-11s:%(lineno)-4d  %(message)s')
    # set the handler to the relevant formatter
    logrfh.setFormatter(simpleform)
    tracefh.setFormatter(detailedform)
    # add the relevant handler to the logger
    logger.addHandler(logrfh)
    tracer.addHandler(tracefh)
    # don't propagate trace records
    tracer.propagate = False
    # set the default logging level
    logger.setLevel(logging.INFO)
    tracer.setLevel(logging.INFO)
    # if a developer is testing
    if os.path.isdir(os.path.join(WurmCommon.appldir, ".svn")) or \
       os.path.isdir(os.path.join(WurmCommon.appldir, ".git")):
        logger.setLevel(logging.DEBUG)
        tracer.setLevel(logging.DEBUG)
    
    # Log initial messages
    tracer.debug("runTheApp")
    logger.info(">>>>>>>> WUU r%s starting <<<<<<<<" % wuuversion)
    logger.info("Python Info: %s - %s - %s\n%s" % (platform.platform(), platform.python_version(), platform.python_build(), str(platform.uname())))
    logger.info("wx Info: [%s, %s]" % (str(wx.VERSION), str(wx.PlatformInfo)))
    # Check to see if we're using a unicode version of wxPython
    if not "unicode" in wx.PlatformInfo:
        logger.warning("You will need to install a unicode version of wxPython (http://www.wxpython.org/) to see the TOC information properly")
    
    if hasattr(open, 'newlines'):
        logger.info('Universal newline support is available')
    
    try:
        # Create the UI
        app = WurmApp(redirect=1, filename=logfile) # will redirect stdout to logfile
        tracer.debug("Running MainLoop now")
        # Process the User's requests
        app.MainLoop()
    except Exception, details:
        raise


def bootWUU():
    try:
        psyco.full()
    except NameError:
        pass
    
    import getopt
    # Process any command line options
    opts = None
    try:
        opts, args = getopt.getopt(sys.argv[1:], "v:u:", ["verifysig= ","unzip= "])
    except:
        pass # no command line options
    
    # If no command line options then start the Application
    if not opts or len(opts) == 0:
        try:
            try:
                runTheApp()
            except Exception, details:
                # Need to handle a SystemExit
                logger.exception("WUU Error: %s" % (str(details)))
                sys.exit(1)
        finally:
            # Shutdown the logging system
            logging.shutdown()
            # Exit here
            os._exit(0)
    
    else: # command line options are used by the updater
        for o, a in opts:
            if o in ("-v", "--verifysig"): # Command line option to quickly verify a file (assumes the file has a matching .sig)
                try:
                    if Wurm.verifySig(a):
                        sys.exit(0)
                except Exception, details:
                    WurmCommon.outError("Error verifying signature: %s, %s" % (a, str(details)))
                sys.exit(1)
            elif o in ("-u", "--unzip"): # Command line option to unzip a file to the temp dir
                try:
                    if Wurm.unzipToTemp(a):
                        sys.exit(0)
                except Exception, details:
                    WurmCommon.outError("Error unzipping file: %s, %s" % (a, str(details)))
                sys.exit(1)


if __name__ == "__main__":
    bootWUU()
