# -*- coding: utf-8 -*-
# $Id: WUUDialogs.py 658 2009-06-01 15:28:28Z jonhogg $

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

import os
import WurmCommon

# remap dummy translation function to real trans func
translator = WurmCommon.WurmLanguage
_          = translator.s

# shortcuts to code in WurmCommon
origappldir = WurmCommon.origappldir
supportdir  = WurmCommon.supportdir
prefsdir    = WurmCommon.prefsdir

import wx
import wx.lib.mixins.listctrl as listmix
import images
import logging
import Wurm
import WurmUtility

# Addon Site details, URL's are used when chosen from the Help Menu
availablesites = {
    "Auctioneer":("http://www.auctioneeraddon.com/", _("Site ID is directory name"), "%s"),
    "CapnBry":("http://capnbry.net/wow/", _("Site ID is directory name"), "%s"),
    "Cosmos":("http://www.cosmosui.org/addons.php", _("Site ID is the part after f= in the download URL"), "%s"),
    "CTMod":("http://www.ctmod.net/", _("Site ID is directory name"), "%s"),
    "CurseGaming":("http://wow.curse.com/", _("Site ID is the part of the Addon URL after /details/, e.g.: \"2003\" or \"sw-stats\""), "%s"),
    "DBM":("http://www.deadlybossmods.com/", _("Site ID the short name of the addon; 'core', 'old' or 'alpha'"), "%s"),
    "Gatherer":("http://www.gathereraddon.com/", _("Site ID is directory name"), "%s"),
    "GenericGit":("git://", _("SiteID is the Public Clone URL starting git://"), ""),
    "GoogleCode":("http://code.google.com/hosting/search?q=label:worldofwarcraft", _("Site ID is developer name. e.g.:\"tekkub-wow\""), ""),
    "GoogleCodeSVN":("http://code.google.com/hosting/search?q=label:worldofwarcraft", _("Site ID is developer name + | + addon directory,\n e.g.: --> wow-haste|Fane\n Optionally, a branch can be specified --> wow-haste|branches/QuestCopy"), ""),
    "WoWAce":("http://www.wowace.com/projects/", _("Site ID is directory name"), "%s"),
    "WoWAceClone":("http://www.wowace.com/projects/Addon/repositories/", _("Site ID is clone name"), "%s"),
    "WoWI":("http://www.wowinterface.com/", _("Site ID is numeric + Addon name from site. e.g.: \"5001-Minimalist\""), "XXXX-%s"),
    "WoWUI":("http://wowui.incgamers.com/", _("Site ID is the number after m= in the URL"), "%s"),
    "OtherSite":("", _("Please refer to %(wuuki)sOtherSites for Instructions"), ""),
    "Child":("", _("Please refer to %(wuuki)sOtherSites for Instructions"), ""),
    "[Dummy]":(_("Dummy Addon"), "", ""),
    "[Ignore]":(_("Ignore this Addon"), "", ""),
    "[Outdated]":(_("Addon won't be updated anymore"), "", ""),
    "[Related]":(_("Addon is related to/comes with another Addon"), _("Site ID is Addon this one comes with"), ""),
    "[Unknown]":(_("Addon source unknown"), "", ""),
}
# sort the availablesites keys
asKeys = availablesites.keys()
asKeys.sort()

# List of Addons to install
installlist   = []

# Colour tuples used in the Addon List Control
lcColour = {}
lcColour["Installed"] = (0, 238, 0) # addon installed - default Green
lcColour["Missing"]   = (238, 0, 0) # addon missing - default Red
lcColour["Pending"]   = (255, 127, 0) # addon update available - default Amber
lcColour["Unknown"]   = (255, 230, 230) # unknown local version
lcColour["Outdated"]  = (255, 230, 255) # addon outdated
lcColour["New"]       = (230, 230, 255) # new addon

class Label(wx.StaticText):
    """
    Special StaticText control that automatically shows up as bold and right-aligned.
    Used as a label in a grid layout.
    """
    def __init__(self, parent, text):
        """"""
        tracer.debug("Label - __init__")
        
        wx.StaticText.__init__(self, parent, -1, label=text, style=wx.ALIGN_RIGHT )
        
        # Acquire font and make it bold. Reassign to control
        fn = self.GetFont()
        fn.SetWeight(wx.BOLD)
        self.SetFont(fn)
    


class ListCtrlAutoWidth(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, *args, **kwargs):
        """"""
        tracer.debug("ListCtrlAutoWidth - __init__")
        
        wx.ListCtrl.__init__(self, *args, **kwargs)
        listmix.ListCtrlAutoWidthMixin.__init__(self)
    


class WurmAddonEditDlg(wx.Dialog):
    """
    Dialog to edit the settings for an addon
    
    Parameters:
        
        parent          -   The window calling the dialog
        
        addon           -   A unique ID for the addon being edited
        
        settingslist    -   Software preferences for the app - this is no longer needed, but kept "just in case".
        
    """
    
    def __init__(self, parent, addon, settingslist):
        """"""
        tracer.debug("WurmAddonEditDlg - __init__")
        
        wx.Dialog.__init__(self, parent, -1, _('Edit Addon: %(addon)s') % {'addon':addon})
        
        self.addonname    = addon
        self.settingslist = settingslist
        self.specialflags = WurmCommon.addonlist.getAllFlags(addon)
        
        # Canned flags for right (label) and left (control)
        rcflags = wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL | wx.EXPAND
        lcflags = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL
        
        # Top level sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        #
        # Master sizer to hold everything except the buttons.
        # Note that row value == 0 indicates that it should add rows as needed.
        #
        # Essentially, we have here a two-column grid with any number of rows.
        #
        grid = wx.FlexGridSizer(0, 2, 3, 3)
        grid.AddGrowableCol(1)
        
        #
        # Addon path
        # Note this has a size of 250 to establish the minimum width of the sizer.
        # That's the only purpose of the static size. I hate this kind of hack.
        #
        # With one exception, none of the other controls have hard coded size parameters
        #
        apath = wx.TextCtrl(self, -1, size=(250, -1), style=wx.TE_READONLY )
        apath.SetValue(str('%s'%(addon)))
        apath.Enable(False)
        grid.Add(Label(self, _('Addon Directory: ')), 0, lcflags, 3)
        grid.Add(apath, 1, rcflags, 3)
        
        # Friendly name
        self.fname = wx.TextCtrl(self, -1)
        self.fname.SetValue(str(WurmCommon.addonlist.getFname(addon)))
        grid.Add(Label(self, _('Friendly Name: ')), 0, lcflags, 3)
        grid.Add(self.fname, 1, rcflags, 3)
        
        # Source Site
        self.site = wx.ComboBox(self, -1, choices=asKeys, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        startsite = WurmCommon.addonlist.getAtype(addon)
        self.site.SetStringSelection(startsite)
        grid.Add(Label(self, _('Source Site: ')), 0, lcflags, 3)
        grid.Add(self.site, 1, rcflags, 3)
        self.Bind(wx.EVT_COMBOBOX, self.OnSiteChange, self.site)
        
        # Site ID
        self.origsiteid = WurmCommon.addonlist.getSiteid(addon)
        self.siteid = wx.TextCtrl(self, -1)
        self.siteid.SetValue(self.origsiteid)
        grid.Add(Label(self, _('Site ID: ')), 0, lcflags, 3)
        grid.Add(self.siteid, 1, rcflags, 3)
        
        self.originalsite = WurmCommon.addonlist.getAtype(addon)
        
        # Config options, unpopulated
        self.conf = self.confcontrols = self.conflabels = {}
        
        cKeys = []
        # Populate config options
        if addon in WurmCommon.addons:
            self.conf = WurmCommon.addons[addon].configurable
            # sort the configuration parameters
            cKeys = self.conf.keys()
            cKeys.sort()
        
        # Go through the list of custom config settings for this addon
        # and populate them in the dialog.
        for c in cKeys:
            (key, desc, default) = self.conf[c]
            
            # Special instructions
            if key == "Instructions":
                # add a blank line before
                grid.Add(wx.StaticText(self, -1, label=""), 0, rcflags, 3)
                grid.Add(wx.StaticText(self, -1, label=""), 1, rcflags, 3)
                
                grid.Add(Label(self, "Instructions: "), 0, lcflags, 3)
                grid.Add(wx.StaticText(self, -1, label=desc), 1, rcflags, 3)
                
                # add a blank line after
                grid.Add(wx.StaticText(self, -1, label=""), 0, rcflags, 3)
                grid.Add(wx.StaticText(self, -1, label=""), 1, rcflags, 3)
                
            # Everybody Else
            else:
                
                # Label
                self.conflabels[key] = Label(self, "%s:" % (desc))
                grid.Add(self.conflabels[key], 0, rcflags, 3)
                
                #
                # Create the control dependant upon the required data
                #
                # boolean
                if type(default) == bool:
                    self.confcontrols[key] = wx.CheckBox(self, -1)
                
                # text values
                elif type(default) == str:
                    self.confcontrols[key] = wx.TextCtrl(self, -1)
                
                # Add the new control to the dialog - add a blank space if it fails for some reason
                try:
                    grid.Add(self.confcontrols[key], 1, rcflags, 3)
                except KeyError:
                    grid.Add((10,10), 1, rcflags, 3)
                
                # Set the value of the new control - just ignore if this fails for some reason
                try:
                    if key in self.specialflags and self.specialflags[key]:
                        self.confcontrols[key].SetValue(self.specialflags[key])
                    else:
                        self.confcontrols[key].SetValue(default)
                except KeyError:
                    pass
                    
        # Add grid of controls to master sizer
        sizer.Add(grid, 1, wx.ALL | wx.EXPAND, 5)
        
        # setup save and cancel buttons
        saveBtn = wx.Button(self, wx.ID_SAVE, "") #_("Save")
        self.Bind(wx.EVT_BUTTON, self.Save, saveBtn)
        canxBtn = wx.Button(self, wx.ID_CANCEL, "") #_("Cancel")
        self.Bind(wx.EVT_BUTTON, self.Cancel, canxBtn)
        
        # put the buttons into a buttonsizer
        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(saveBtn)
        btnSizer.AddButton(canxBtn)
        btnSizer.SetAffirmativeButton(saveBtn)
        btnSizer.SetCancelButton(canxBtn)
        btnSizer.Realize()
        
        # add button sizer
        sizer.Add(btnSizer, 0, wx.ALL | wx.EXPAND, 5)
        
        # resize the sizer
        self.SetSizer(sizer)
        sizer.Fit(self)
        
        positionDialog(self)
    
    
    def updateFlags(self):
        """ Updates the specialflags with the settings from the controls """
        tracer.debug("WurmAddonEditDlg - updateFlags")
        
        if self.site.GetStringSelection() != self.originalsite:
            self.specialflags = {} # if site has changed, all specialflags are invalidated
            return
        
        for c in self.confcontrols:
            self.specialflags[c] = self.confcontrols[c].GetValue()
    
    
    def Cancel(self, event):
        """
        Return to caller with Cancel status, indicating taht changes should not be committed.
        """
        tracer.debug("WurmAddonEditDlg - Cancel")
        self.EndModal(wx.ID_CANCEL)
    
    
    def OnSiteChange(self, event):
        """"""
        tracer.debug("WurmAddonEditDlg - OnSiteChange")
        
        fitem = self.site.GetStringSelection()
        
        if fitem[0] != "[": # only "real" sites
            # Check if the website has a Site ID for this addon/site
            setting = Wurm.lookupSiteID(self.addonname, fitem)
        else:
            setting = None
        if setting:
            self.siteid.SetValue(setting)
        elif self.siteid.GetValue() == "":
            newsid = availablesites[fitem][2]
            if newsid.count("%s") > 0:
                newsid = newsid % (self.addonname)
            self.siteid.SetValue(newsid)
        
        # TODO: Rebuild the dialog if site changes
        if fitem != self.originalsite:
            for k in self.confcontrols:
                self.confcontrols[k].Disable()
        else:
            for k in self.confcontrols:
                self.confcontrols[k].Enable()
        
        self.siteid.SetToolTip(wx.ToolTip(translator.s(availablesites[fitem][1]))) # translate the text
    
    
    def Save(self, event):
        """
        Return to caller with OK status, indicating that changes should be committed
        """
        tracer.debug("WurmAddonEditDlg - Save")
        self.EndModal(wx.ID_OK)
    


class WurmAddonInstallDlg(wx.Dialog, listmix.ColumnSorterMixin, WurmUtility.TypeAheadListCtrlMixin):
    def __init__(self, parent, addonlist, addontoclist, settingslist, addonsite):
        """"""
        tracer.debug("WurmAddonInstallDlg - __init__")
        
        self.title  = _("Install %(site)s Addons") % {'site': addonsite}
        self.oldfilter = ""
        self.filterok  = True
        # The SearchCtrl only became available in wx version 2.8.0.1
        if wx.VERSION[:2] < (2, 8):
            self.filterok = False
        
        wx.Dialog.__init__(self, parent, title=self.title, size=(660, 400), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        
        # Initialize dictionaries
        self.addonlist    = addonlist
        self.addontoclist = addontoclist
        self.settingslist = settingslist
        self.toInstall    = []
        
        # Counts for displaying in the title line
        self.countt = len(self.addonlist)
        self.counti = 0
        self.countf = len(self.toInstall)
        
        # Resources
        self.il    = wx.ImageList(16, 16)
        self.sm_up = self.il.Add(images.getSmallUpArrowBitmap())
        self.sm_dn = self.il.Add(images.getSmallDnArrowBitmap())
        
        # Controls
        gbsizer = wx.GridBagSizer(2, 2)
        self.lc = ListCtrlAutoWidth(self, wx.ID_ANY, style=wx.LC_REPORT | wx.LC_SORT_ASCENDING)
        self.lc.InsertColumn(0, _("Name"))
        self.lc.InsertColumn(1, _("Ins?"), format=wx.LIST_FORMAT_CENTRE)
        self.lc.InsertColumn(2, _("Version"))
        self.lc.InsertColumn(3, _("Note"))
        
        self.lc.SetColumnWidth(0, 150)
        self.lc.SetColumnWidth(1, 40)
        self.lc.SetColumnWidth(2, 50)
        self.lc.SetColumnWidth(3, 200)
        
        self.lc.SetImageList(self.il, wx.IMAGE_LIST_SMALL)
        
        gbsizer.Add(self.lc, (0, 0), flag=wx.EXPAND)
        gbsizer.AddGrowableRow(0)
        gbsizer.AddGrowableCol(0)
        
        # Add Buttons
        self.btnToggle = wx.Button(self, wx.ID_ANY, _("Toggle Install"))
        self.btnClose  = wx.Button(self, wx.ID_CLOSE, _("Close and Download"))
        self.btnCancel = wx.Button(self, wx.ID_CANCEL, "") #_("Cancel"))
        
        # Put them all in a BoxSizer
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.btnToggle, proportion=1)
        hbox.Add(self.btnClose, proportion=1)
        hbox.Add(self.btnCancel, proportion=1)
        
        if self.filterok:
            self.filter = wx.SearchCtrl(self, style=wx.TE_PROCESS_ENTER)
            self.filter.SetDescriptiveText("Search")
            self.filter.ShowCancelButton(True)
            self.filter.SetToolTip(wx.ToolTip(_("Enter a string to search for in the Name or Note")))
        
        if self.filterok:
            hbox.Add(self.filter, proportion=1)
            
        gbsizer.Add(hbox, (1, 0))
        
        self.SetSizer(gbsizer)
        
        # Bind Events to their handlers
        self.Bind(wx.EVT_BUTTON, self.OnToggle, self.btnToggle)
        self.Bind(wx.EVT_BUTTON, self.OnClickClose, self.btnClose)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, self.btnCancel)
        if self.filterok:
            self.Bind(wx.EVT_TEXT_ENTER, self.OnFilterChanged, self.filter)
            self.Bind(wx.EVT_TEXT, self.OnFilterChanged, self.filter)
            self.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self.OnCancelFilter, self.filter)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        
        # List Sorting
        listmix.ColumnSorterMixin.__init__(self,4)
        self._colSortFlag[1] = -1 # Sort Descending on first click
        
        # Type Ahead mixin
        WurmUtility.TypeAheadListCtrlMixin.__init__(self)
        
        try:
            # Load the List Control
            self.RefreshAddonList()
        except Exception, details:
            logger.exception("Error refreshing the Addon List, %s" % (str(details)))
        
        # Select the first entry
        self.lc.Select(0)
        self.lc.Focus(0)
        
        positionDialog(self)
    
    
    def _showTitle(self):
        """ Display the Addon List Title """
        tracer.debug("WurmAddonInstallDlg - _showTitle")
        
        self.SetTitle(_("%(title)s - [%(cntt)d/%(cnti)d/%(cntf)d] (Total/Installed/Flagged)") % {'title': self.title, 'cntt': self.countt, 'cnti': self.counti, 'cntf': self.countf})
    
    
    def AddAddon(self, addon):
        """ Build the List Control contents from the Addon list """
        tracer.log(WurmCommon.DEBUG5, "WurmAddonInstallDlg - AddAddon")
        
        (fName, lName, siteId, aType) = self.addonlist.getSome(addon)
        ver = ""
        notes = ""
        if lName in self.addontoclist:
            notes = self.addontoclist[lName].getTextField("Notes")
            ver = self.addontoclist[lName].getTextField("WUU-Version")
        
        # filter the addons
        filterstring = ("|".join((lName, notes))).upper() # case insensitive
        if not self.oldfilter.upper() in filterstring: # simple implementation of filter
            return
        
        num_items = self.lc.GetItemCount()
        ix        = self.lc.InsertStringItem(num_items, lName)
        data      = _listid(lName)
        
        self.lc.SetItemData(ix, data)
        
        if lName in self.toInstall:
            instval = 'Y'
            self.lc.SetItemBackgroundColour(ix, lcColour["Pending"])
        elif addon in WurmCommon.addonlist:
            instval = 'I'
            self.lc.SetItemBackgroundColour(ix, lcColour["Installed"])
        else:
            instval = ''
            self.lc.SetItemBackgroundColour(ix, wx.WHITE)
        
        self.lc.SetStringItem(ix, 1, instval)
        self.lc.SetStringItem(ix, 2, ver)
        self.lc.SetStringItem(ix, 3, notes)
        
        self.itemDataMap[data] = (lName.upper(), instval, ver, notes)
    
    
    def GetListCtrl(self):
        """Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
        and by the TypeAheadListCtrlMixin
        """
        tracer.debug("WurmAddonInstallDlg - GetListCtrl")
        
        return self.lc
    
    
    def GetSecondarySortValues(self, col, key1, key2):
        """Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py"""
        tracer.log(WurmCommon.DEBUG5, "WurmAddonInstallDlg - GetSecondarySortValues")
        
        # use the Addon name as the secondary sort value
        return (self.itemDataMap[key1][0], self.itemDataMap[key2][0])
    
    
    def GetSortImages(self):
        """Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py"""
        tracer.debug("WurmAddonInstallDlg - GetSortImages")
        
        return (self.sm_dn, self.sm_up)
    
    
    def OnCancel(self, event):
        """"""
        tracer.debug("WurmAddonInstallDlg - OnCancel")
        
        self.toInstall = []
        WurmCommon.outMessage(_("Install list cleaned"))
        self.Close()
    
    
    def OnCancelFilter(self, event):
        """ Don't filter the addon list """
        tracer.debug("WurmAddonInstallDlg - OnCancelFilter")
        
        self.filter.Clear()
        self.oldfilter = ""
        self.RefreshAddonList()
    
    
    def OnClickClose(self, event):
        """"""
        tracer.debug("WurmAddonInstallDlg - OnClickClose")
        
        self.Close()
    
    
    def OnCloseWindow(self, event):
        """"""
        tracer.debug("WurmAddonInstallDlg - OnCloseWindow")
        
        global installlist
        
        if len(self.toInstall) > 0:
            msg = wx.MessageDialog(self, _("Download and install %(num)d Addons?") % {'num': len(self.toInstall)}, _("Close Install Addon(s)"), style=wx.YES_NO|wx.ICON_QUESTION)
            answer = msg.ShowModal()
            msg.Destroy()
            if answer == wx.ID_YES:
                for a in self.toInstall:
                    (frn, lon, sid, adt, spf) = self.addonlist.getAll(a)
                    spf['install'] = True
                    WurmCommon.addonlist.add(a, fname=frn, lname=lon, siteid=sid, atype=adt, flags=spf)
                WurmCommon.outStatus(_("%(num)d Addons queued for Installation, please wait...") % {'num': len(self.toInstall)})
            else:
                self.toInstall = []
        
        installlist = self.toInstall
        
        # end the dialog
        self.EndModal(wx.ID_OK)
    
    
    def OnFilterChanged(self, event):
        """ Filter the addon list """
        tracer.debug("WurmAddonInstallDlg - OnFilterChanged")
        
        newfilter = self.filter.GetValue()
        
        # TODO: Do some shortcuts here if the filter just has one char added/removed
        
        self.oldfilter = newfilter
        self.RefreshAddonList()
    
    
    def OnToggle(self, event):
        """ Toggle the Install flag for the selected addons """
        tracer.debug("WurmAddonInstallDlg - OnToggle")
        
        if self.lc.GetSelectedItemCount() == 0:
            return
        
        curitem = -1
        while True:
            curitem = self.lc.GetNextItem(curitem, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if not curitem == -1:
                fitem  = self.lc.GetItem(curitem, 0).GetText()
                data   = self.lc.GetItemData(curitem)
                oldmap = self.itemDataMap[data]
                if fitem in WurmCommon.addonlist:
                    continue
                elif fitem not in self.toInstall:
                    self.toInstall.append(fitem)
                    instval = 'Y'
                    self.lc.SetItemBackgroundColour(curitem, lcColour["Pending"])
                else:
                    self.toInstall.remove(fitem)
                    instval = ''
                    self.lc.SetItemBackgroundColour(curitem, wx.WHITE)
                self.lc.SetStringItem(curitem, 1, instval)
                self.itemDataMap[data] = (oldmap[0], instval, oldmap[2], oldmap[3])
            else:
                break
        
        self.countf = len(self.toInstall)
        
        self._showTitle()
    
    
    def RefreshAddonList(self, clear=True):
        """ Refresh the Addon List contents """
        tracer.debug("WurmAddonInstallDlg - RefreshAddonList")
        
        if clear:
            self.itemDataMap = {}
            self.lc.DeleteAllItems()
        
        k = self.addonlist.keys()
        self.counti = 0
        
        for a in k:
            if a in WurmCommon.addonlist: # count addons already installed
                self.counti += 1
            if self.addonlist.getAtype(a)[0] != "[": # only "real" sites
                self.AddAddon(a)
        
        if clear:
            self.SortListItems(col=0, ascending=1) # re-sort after load
        
        self._showTitle()
    


class WurmAdvancedRestoreDlg(wx.Dialog, listmix.ColumnSorterMixin):
    """ A dialog to present the user with a list of previous versions to downgrade to """
    
    def __init__(self, parent, addon):
        """ Creates a new advanced restore dialog and populates it with available downgrades """
        
        wx.Dialog.__init__(self, parent, 10002, _("Advanced Restore: %(name)s") % {'name': addon.localname})
        
        # Resources
        self.il    = wx.ImageList(16, 16)
        self.sm_up = self.il.Add(images.getSmallUpArrowBitmap())
        self.sm_dn = self.il.Add(images.getSmallDnArrowBitmap())
        
        # Controls
        gbsizer = wx.GridBagSizer(2, 2)
        self.lc = ListCtrlAutoWidth(self, wx.ID_ANY, style=wx.LC_REPORT | wx.LC_SORT_ASCENDING | wx.LC_SINGLE_SEL)
        self.lc.InsertColumn(0, _("File"))
        self.lc.InsertColumn(1, _("Version"), format=wx.LIST_FORMAT_CENTRE)
        self.lc.InsertColumn(2, _("Source"))
        self.lc.SetColumnWidth(0, 160)
        self.lc.SetColumnWidth(1, 100)
        self.lc.SetColumnWidth(2, 100)
        
        self.lc.SetImageList(self.il, wx.IMAGE_LIST_SMALL)
        
        gbsizer.Add(self.lc, (0, 0), flag=wx.EXPAND)
        gbsizer.AddGrowableRow(0)
        gbsizer.AddGrowableCol(0)
        
        # Add Buttons
        btnOnlineVersions = wx.Button(self, wx.ID_ADD, _("Add online versions"))
        self.Bind(wx.EVT_BUTTON, self.OnAddOnlineVersions, btnOnlineVersions)
        btnOnlineVersions.Disable()
        btnOk = wx.Button(self, wx.ID_OK, _("Restore"))
        self.Bind(wx.EVT_BUTTON, self.OnRestore, btnOk)
        btnCancel = wx.Button(self, wx.ID_CANCEL, "") #_("Cancel"))
        
        # put the buttons into a buttonsizer
        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(btnOnlineVersions)
        btnSizer.AddButton(btnOk)
        btnSizer.AddButton(btnCancel)
        btnSizer.SetNegativeButton(btnOnlineVersions) # just used to position the button
        btnSizer.SetAffirmativeButton(btnOk)
        btnSizer.SetCancelButton(btnCancel)
        btnSizer.Realize()
        
        # add button sizer
        gbsizer.Add(btnSizer, (1, 0))
        
        self.SetSizer(gbsizer)
        
        # List Sorting
        listmix.ColumnSorterMixin.__init__(self, 4)
        self._colSortFlag[1] = -1 # Sort Descending on first click
        
        self.restoreaddon = addon
        
        self._populateList()
        if self.lc.GetItemCount() > 0:
            # Select the first entry
            self.lc.Select(0)
            self.lc.Focus(0)
        else:
            btnOk.Disable()
            
        positionDialog(self)
        
    
    def _populateList(self, clear = True, online = False):
        """"""
        tracer.debug("WurmAdvancedRestoreDlg - _populateList")
        
        if clear:
            self.itemDataMap = {}
            self.lc.DeleteAllItems()
        
        versions = self.restoreaddon.getAvailableRestores(online)
        
        for v in versions: # v is (file, version, source)
            num_items = self.lc.GetItemCount()
            ix = self.lc.InsertStringItem(num_items, v[0])
            data = _listid("%s|%s" % (v[1], v[2]))
            
            self.lc.SetItemData(ix, data)
            
            self.lc.SetStringItem(ix, 1, v[1])
            self.lc.SetStringItem(ix, 2, v[2])
            
            self.itemDataMap[data] = (v[0], v[1], v[2])
    
    
    def GetListCtrl(self):
        """Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
        and by the TypeAheadListCtrlMixin
        """
        tracer.debug("WurmAdvancedRestoreDlg - GetListCtrl")
        
        return self.lc
    
    
    def GetSortImages(self):
        """Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py"""
        tracer.debug("WurmAdvancedRestoreDlg - GetSortImages")
        
        return (self.sm_dn, self.sm_up)
    
    
    def GetSecondarySortValues(self, col, key1, key2):
        """Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py"""
        tracer.log(WurmCommon.DEBUG5, "WurmAdvancedRestoreDlg - GetSecondarySortValues")
        
        # use the source name as the secondary sort value
        return (self.itemDataMap[key1][2], self.itemDataMap[key2][2])
    
    
    def OnAddOnlineVersions(self, event):
        """ Adds online versions to the list, if possible """
        tracer.debug("WurmAdvancedRestoreDlg - OnAddOnlineVersions")
        
        self._populateList(online = True)
        self.btnOnlineVersions.Disable()
    
    
    def OnRestore(self, event):
        """ Convenience event handler to simplify the work in the main program """
        
        self.toRestore = None
        
        item = self.lc.GetFirstSelected() # only single selection should be possible
        if item != -1:
            data = self.lc.GetItemData(item)
            
            self.toRestore = self.itemDataMap[data]
        
        self.EndModal(wx.ID_OK) # for some reason, this is not called automatically
    


class WUUPreferencesDlg(wx.Dialog):
    SDIR     = 1    # setting is a directory
    SCHECK   = 2    # setting is a boolean (show checkbox)
    STEXT    = 3    # setting is a string
    SCOLOUR  = 4    # setting is a colour select button
    SNUMBER  = 5    # setting is a number or blank
    
    def __init__(self, parent, id, settingslist):
        """"""
        tracer.debug("WUUPreferencesDlg - __init__")
        
        import wx.lib.colourselect as csel
        
        wx.Dialog.__init__(self, parent, id, _('Preferences'), style = wx.DEFAULT_DIALOG_STYLE)
        
        self.settingslist = {}
        
        for s in settingslist:
            self.settingslist[s] = settingslist[s]
        
        self.controls   = {}
        self.buttonRefs = {} # for saving references to colour select buttons
        
        labels = {
            _("10WoW directory"):("WoWDir", _("Directory where WoW.exe resides"), self.SDIR),
            _("11Backup directory"):("BackupDir", _("Directory where previous versions of Addons will be stored"), self.SDIR),
            _("12Download directory"):(":BrowserDownloadDir", _("Directory where your browser downloads to; used as default when selecting files"), self.SDIR),
            _("21Check WUU version"): ("CheckWUUVersion", _("Check the web to see if a new version is available when WUU is started"), self.SCHECK),
            _("23Allow WUU beta version"): ("CheckWUUVersionBeta", _("Check for newer beta versions first"), self.SCHECK),
            _("22Automatically update WUU"): ("AutoUpdate", _("If self-updating doesn't work for you, uncheck this"), self.SCHECK),
            _("15Automatically load settings"): ("Autoload", _("Automatically load Addon settings when WUU starts"), self.SCHECK),
            _("16Delete before extract"): (":CleanExtract", _("Delete the Addon dir before extracting the new version - MIGHT BE DANGEROUS IF NEW VERSION IS CORRUPT"), self.SCHECK),
            _("18Delete after install"): (":CleanDownload", _("Delete the downloaded file after a successful install"), self.SCHECK),
            _("41Use wuu.vagabonds.info data"): (":UseWebsite", _("Use wuu.vagabonds.info for lookups of data"), self.SCHECK),
            _("42Preserve newlines as-is"): (":PreserveNewline", _("Enable this to turn off WUUs handling of newlines when unpacking archives"), self.SCHECK),
            _("43Clean downloaded files on exit"): ("AutoCleanTemp", _("If enabled, the WUU temp directory will be deleted on exit (same effect as running the similar menu option)"), self.SCHECK),
            _("51Language code"): (":LangCode", _("Enter language code for translation to use in WUU (e.g. 'en' for lang-en.xml)"), self.STEXT),
            _("71Check for PTR Client"): ("PTRCheck", _("Check to see if the PTR Client is installed, will allow PTR Addons to be managed if set)"), self.SCHECK),
            _("45Use Coral CDN"): (":UseCoralCDN", _("Uses the Coral Content Distribution Network to save on the sites' bandwidth"), self.SCHECK),
            _("46Use threads"): (":UseThreads", _("Uncheck this if threaded updating is slow"), self.SCHECK),
            _("47Socket timeout"): (":SocketTimeout", _("Set to number of seconds before timeout, or -1 for no timeout"), self.SNUMBER),
            _("81Addon Installed Colour"): ("InstalledRGB", _("Choose the colour to indicate that an Addon is Installed"), self.SCOLOUR),
            _("82Addon Missing Colour"): ("MissingRGB", _("Choose the colour to indicate that an Addon is Missing"), self.SCOLOUR),
            _("83Addon Pending Colour"): ("PendingRGB", _("Choose the colour to indicate an that Addon has an Available Update"), self.SCOLOUR),
            _("99Enable Log Debug Messages"): ("Debug2Log", _("Check to turn on Debug messages in the Log file"), self.SCHECK),
        }
        
        # sort preferences
        keys = labels.keys()
        keys.sort()
        
        # Canned flags for right (label) and left (control)
        rcflags = wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL | wx.EXPAND
        lcflags = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL
        
        # Top level sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        #
        # CONTROLS
        #
        
        # Sizer to hold checkboxes n stuff
        grid = wx.GridBagSizer(3, 3)
        grid.AddGrowableCol(1)
        grid.AddGrowableCol(3)
        
        row=0
        col=0
        
        for l in keys:
            prefs = labels[l][0]
            desc  = translator.s(labels[l][1]) # translate the text
            pref  = labels[l][2]
            
            # Checkboxes first
            
            if pref == self.SCHECK:
                grid.Add(Label(self, l[2:]), (row, col), (1,1) , lcflags, 3)
                
                self.controls[prefs] = wx.CheckBox(self, -1, name = prefs) # no label
                self.controls[prefs].SetToolTip(wx.ToolTip(desc))
                
                if prefs in self.settingslist:
                    if int(self.settingslist[prefs]):
                        self.controls[prefs].SetValue(True)
                self.Bind(wx.EVT_CHECKBOX, self.OnCheck, self.controls[prefs])
                
                grid.Add(self.controls[prefs], (row, col+1), (1,1), rcflags, 3)
                
            else:
                continue
            
            if col == 2:
                col = 0
                row += 1
            else:
                col = 2
        
        for l in keys:
            prefs = labels[l][0]
            desc  = translator.s(labels[l][1]) # translate the text
            pref  = labels[l][2]
            
            if pref == self.STEXT:
                grid.Add(Label(self, l[2:]), (row, col), (1,1) , lcflags, 3)
                
                if "Language" in l:
                    langKeys = WurmCommon.WurmLanguage.languagenames.keys()
                    langKeys.sort()
                    self.controls[prefs] = wx.Choice(self, -1, choices=langKeys, name=prefs)
                    self.Bind(wx.EVT_CHOICE, self.OnLangChange, self.controls[prefs])
                    if prefs in self.settingslist:
                        self.controls[prefs].SetStringSelection(self.settingslist[prefs])
                else:
                    tcSize = (-1, -1)
                    tcFlag = wx.ALL | wx.ALIGN_LEFT
                    
                    self.controls[prefs] = wx.TextCtrl(self, -1, size=tcSize, style=tcFlag, name=prefs)
                    self.Bind(wx.EVT_TEXT, self.OnTextChange, self.controls[prefs])
                    if prefs in self.settingslist:
                        self.controls[prefs].SetValue(self.settingslist[prefs])
                
                self.controls[prefs].SetToolTip(wx.ToolTip(desc))
                
                grid.Add(self.controls[prefs], (row, col+1), (1,1), rcflags, 3)
                
            elif pref == self.SNUMBER:
                grid.Add(Label(self, l[2:]), (row, col), (1,1) , lcflags, 3)
                
                tcSize = (40, -1)
                tcFlag = wx.FIXED_MINSIZE | wx.ALL | wx.ALIGN_LEFT
                
                self.controls[prefs] = wx.TextCtrl(self, -1, size = tcSize, name = prefs)
                self.controls[prefs].SetToolTip(wx.ToolTip(desc))
                
                if prefs in self.settingslist:
                    self.controls[prefs].SetValue(str(self.settingslist[prefs]))
                
                self.Bind(wx.EVT_TEXT, self.OnNumberChange, self.controls[prefs])
                grid.Add(self.controls[prefs], (row, col+1), (1,1), rcflags, 3)
                
            else:
                continue
            
            if col == 2:
                col = 0
                row += 1
            else:
                col = 2
        
        if col == 2:
            col = 0
            row += 1
        
        # Color controls
        for l in keys:
            prefs = labels[l][0]
            desc  = translator.s(labels[l][1]) # translate the text
            pref  = labels[l][2]
            
            if pref == self.SCOLOUR:
                csid = wx.NewId()
                
                grid.Add(Label(self, l[2:]), (row, col), (1,1) , lcflags, 3)
                
                self.controls[prefs] = csel.ColourSelect(self, csid, size=(20,20))
                self.controls[prefs].SetToolTip(wx.ToolTip(desc))
                
                if prefs in self.settingslist:
                    self.controls[prefs].SetValue(lcColour[prefs[:-3]]) # use the lcColour value as the settingslist value is a string and not a Colour value
                
                self.buttonRefs[csid] = prefs # store reference to setting name
                
                grid.Add(self.controls[prefs], (row, col+1), (1,1), wx.FIXED_MINSIZE | wx.ALL | wx.ALIGN_LEFT, 3)
                
            else:
                continue
            
            if col == 2:
                col = 0
                row += 1
            else:
                col = 2
        
        if col == 2:
            row += 1
        
        # Directories
        for l in keys:
            prefs = labels[l][0]
            desc  = translator.s(labels[l][1]) # translate the text
            pref  = labels[l][2]
            
            if pref == self.SDIR:
                grid.Add(Label(self, l[2:]), (row, 0), (1,1) , lcflags, 3)
                
                hbox = wx.BoxSizer(wx.HORIZONTAL)
                self.controls[prefs] = wx.TextCtrl(self, -1, size=(250,-1), name = prefs, style = wx.TE_READONLY)
                self.controls[prefs].SetToolTip(wx.ToolTip(desc))
                
                if prefs in self.settingslist:
                    self.controls[prefs].SetValue(self.settingslist[prefs])
                
                hbox.Add(self.controls[prefs], 1, wx.EXPAND | wx.ALL, 3)
                
                button = wx.Button(self, -1, "...", name = "%s:button" % (prefs), style=wx.BU_EXACTFIT)
                self.Bind(wx.EVT_BUTTON, self.OnSelectDir, button)
                hbox.Add(button, 0, wx.ALL, 3)
                
                grid.Add(hbox, (row, 1), (1,3), rcflags, 3)
            
            else:
                continue
            
            row += 1
        
        if col == 2:
            col = 0
            row += 1
        
        # All of the above gets added to the main sizer
        sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 20)
        
        # setup save and cancel buttons
        saveBtn = wx.Button(self, wx.ID_SAVE, "") #_("Save")
        self.Bind(wx.EVT_BUTTON, self.Save, saveBtn)
        canxBtn = wx.Button(self, wx.ID_CANCEL, "") #_("Cancel")
        self.Bind(wx.EVT_BUTTON, self.Cancel, canxBtn)
        
        # put the buttons into a buttonsizer
        btnSizer = wx.StdDialogButtonSizer()
        btnSizer.AddButton(saveBtn)
        btnSizer.AddButton(canxBtn)
        btnSizer.SetAffirmativeButton(saveBtn)
        btnSizer.SetCancelButton(canxBtn)
        btnSizer.Realize()
        
        # add button sizer
        sizer.Add(btnSizer, 0, wx.ALL | wx.EXPAND, 5)
        
        self.SetSizer(sizer)
        sizer.Fit(self)
        
        positionDialog(self)
    
    
    def Cancel(self, event):
        """
        Return to caller with Cancel status, indicating that changes should not be committed.
        """
        tracer.debug("WUUPreferencesDlg - Cancel")
        self.EndModal(wx.ID_CANCEL)
    
    
    def OnCheck(self, event):
        """"""
        tracer.debug("WUUPreferencesDlg - OnCheck")
        
        name = event.GetEventObject().GetName()
        self.settingslist[name] = int(self.controls[name].GetValue())
        event.Skip()
    
    
    def OnLangChange(self, event):
        """"""
        tracer.debug("WUUPreferencesDlg - OnLangChange")
        
        name = event.GetEventObject().GetName()
        self.settingslist[name] = self.controls[name].GetStringSelection()
        event.Skip()
    
    
    def OnMove(self, event):
        """"""
        tracer.debug("WUUPreferencesDlg - OnMove")
        
        pos = self.GetPosition()
        # update settings with new values
        self.settingslist["PFrameX"] = pos.x
        self.settingslist["PFrameY"] = pos.y
        event.Skip()
    
    
    def OnNumberChange(self, event):
        """"""
        tracer.debug("WUUPreferencesDlg - OnTextChange")
        
        name = event.GetEventObject().GetName()
        value = self.controls[name].GetValue()
        
        if len(value) == 0 or (value[0] == '-' and value[1:].isdigit()) or value.isdigit():
            self.settingslist[name] = value
        else:
            # not a number, reset to previous
            self.controls[name].SetValue(self.settingslist[name])
        
        event.Skip()
    
    
    def OnSelectColour(self, event):
        """"""
        tracer.debug("WUUPreferencesDlg - OnSelectColour")
        
        name = self.buttonRefs[event.GetId()]
        value = event.GetValue()
        
        # MUST return an rgb string so that it can be saved in the settings file correctly
        value = "%s(%d, %d, %d)" % ("rgb", value[0], value[1], value[2])
        self.settingslist[name] = value
        
        event.Skip()
    
    
    def OnSelectDir(self, event):
        """"""
        tracer.debug("WUUPreferencesDlg - OnSelectDir")
        
        name = event.GetEventObject().GetName().rsplit(":",1)[0] # name on format "Setting:button", "Setting" may contain colons
        path = self.settingslist[name]
        
        dlg = wx.DirDialog(self, _("Select your %(name)s") % {'name': name}, defaultPath = path, style = wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.settingslist[name] = dlg.GetPath()
            self.controls[name].SetValue(dlg.GetPath())
        dlg.Destroy()
        
        event.Skip()
    
    
    def OnTextChange(self, event):
        """"""
        tracer.debug("WUUPreferencesDlg - OnTextChange")
        
        name = event.GetEventObject().GetName()
        self.settingslist[name] = self.controls[name].GetValue()
        event.Skip()
    
    
    def Save(self, event):
        """
        Return to caller with OK status, indicating that changes should be committed
        """
        tracer.debug("WUUPreferencesDlg - Save")
        self.EndModal(wx.ID_OK)
    


class WurmProgress(wx.ProgressDialog):
    def __init__(self, title, msg, maximum=100, parent=None, style=wx.PD_AUTO_HIDE | wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME | wx.PD_ESTIMATED_TIME | wx.PD_REMAINING_TIME):
        """"""
        tracer.debug("WurmProgress - __init__")
        
        wx.ProgressDialog.__init__(self, title, msg, maximum=maximum, parent=parent, style=style)
    
    
    def updateProgress(self, task, progress):
        """"""
        tracer.log(WurmCommon.DEBUG5, "WurmProgress - updateProgress")
        
        self.Update(progress, task)
    


# ListControl ID's
listctrlIDs = {}
listctrlnextID = 1

def _listid(objectname):
    """ Returns a guaranteed unique 32bit integer for use as wx ListCtrl ID
    Might fail if you have over 2^32 addons.
    """
    tracer.log(WurmCommon.DEBUG5, "_listid")
    
    global listctrlIDs, listctrlnextID
    
    if not listctrlIDs.has_key(objectname):
        listctrlIDs[objectname] = listctrlnextID
        listctrlnextID += 1
    
    return listctrlIDs[objectname]


def positionDialog(dialog):
    
    #
    # Positioning of dialog. Previously, this was set by a saved parameter.
    # Now, the dialog will open up under the mouse pointer, or close to it.
    # Controls are in place to ensure that the dialog does not open off screen somewhere.
    #
    mpos = wx.GetMousePosition()        # Mouse position
    dbox = dialog.GetRect()             # Dialog's footprint
    sbox = wx.GetClientDisplayRect()    # Actual screen workspace
    
    # Adjust x-position if dialog is off-screen
    if mpos.x < sbox.x:
        mpos.x = sbox.x
    elif mpos.x + dbox.width > sbox.width:
        mpos.x = sbox.width - dbox.width
    
    # Adjust y-position if dialog is off-screen
    if mpos.y < sbox.y:
        mpos.y = sbox.y
    elif mpos.y + dbox.height > sbox.height:
        mpos.y = sbox.height - dbox.height
    
    # All set? OK, let's position it!
    dialog.SetPosition(mpos)


def GetSite():
    """ Prompt the user to choose a Site to change to for the selected Addon(s) """
    tracer.debug("GetSite")
    
    selection = None
    # display dialog and process choice
    try:
        try:
            dlg = wx.SingleChoiceDialog(None, 'Choose a Site to change to', 'Sites', asKeys)
            # The user pressed the "OK" button in the dialog
            if dlg.ShowModal() == wx.ID_OK:
                selection = dlg.GetStringSelection()
                WurmCommon.outDebug('Site selected: %s' % selection)
        except Exception, details:
            logger.exception("Error getting Site: %s" % str(details))
    finally:
        dlg.Destroy()
    
    return selection


def GetTemplate(sitetype):
    """ Prompt the user to choose an OtherSite/Child Template to use for the current Addon """
    tracer.debug("GetTemplate: [%s]" % sitetype)
    
    if sitetype == "OtherSite":
        table = WurmCommon.ostKeys
    else:
        table = WurmCommon.childtKeys
    
    WurmCommon.outDebug("%s keys: %s" % (sitetype, str(table)))
    
    selection = None
    title = '%s Templates' % sitetype
    # display dialog and process choice
    try:
        try:
            dlg = wx.SingleChoiceDialog(None, 'Choose a Template to use or Cancel for the default one', title, table)
            # The user pressed the "OK" button in the dialog
            if dlg.ShowModal() == wx.ID_OK:
                selection = dlg.GetStringSelection()
                WurmCommon.outDebug('Template selected: %s' % selection)
        except Exception, details:
            logger.exception("Error getting %s template: %s" % (sitetype, str(details)))
    finally:
        dlg.Destroy()
    
    return selection


def GetSavedVarsDelete(savedvarslist):
    """ Prompt the user for which (if any) SavedVariables they want to delete """
    tracer.debug("GetSavedVarsDelete")
    
    selection = []
    title = 'Delete SavedVariables'
    
    try:
        try:
            dlg = wx.MultiChoiceDialog(None, 'Select one or more SavedVariables to delete', title, savedvarslist)
            if dlg.ShowModal() == wx.ID_OK:
                sel = dlg.GetSelections()
                selection = [savedvarslist[x] for x in sel]
                WurmCommon.outDebug("Selected %d items: %s" % (len(selection), ", ".join(selection)))
        except Exception, details:
            logger.exception("Error getting SV selection: %s" % (str(details),))
    finally:
        dlg.Destroy()
    
    return selection

