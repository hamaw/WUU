# -*- coding: utf-8 -*-
# $Id: WurmUtility.py 645 2009-05-04 20:30:53Z jonhogg $

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
import wx

import WurmCommon

# remap dummy translation function to real trans func
_ = WurmCommon.WurmLanguage.s


# The following class was copied from http://wiki.wxpython.org/index.cgi/ListControls
class TypeAheadListCtrlMixin:
    """  A Mixin Class that does type ahead scrolling for list controls.
         Assumes that the wxListCtrl it is mixed into is sorted (it's using
         a binary search to find the correct item).
         
         I wrote this because on Windows there was no type ahead when you
         used a virtual list control, and then couldn't be bothered deciphering
         the default windows typeahead for non-virtual list controls.  So I
         made it work for both virtual and non-virtual controls so that all
         my list controls would have the same functionality.
         
         Things you can change programatically:
         * expand or contract the list of keycodes that stop the type ahead
         * expand or contract the list of keycodes that are allowed to be
           used inside typeahead, but won't start it (e.g. space which normally
           acts as an Activation Key)
         * change the timeout time (init param, defaults to 500 milliseconds)
         * change the sensitivity of the search (init param, defaults to caseinsensitive)
         Things you can change in the class that you mix this into:
         * override the following methods:
           - currentlySelectedItemFoundByTypeAhead
           - currentlySelectedItemNotFoundByTypeAhead
           - newItemFoundByTypeAhead
           - nothingFoundByTypeAhead
           changing these changes the behaviour of the typeahead in various stages.
           See doc comments on methods.
        
        Written by Murray Steele (muz at h-lame dot com)
    """
    
    # These Keycodes are the ones that if we detect them we will cancel the current
    # typeahead state.
    stopTypeAheadKeyCodes = [
     wx.WXK_BACK,
     wx.WXK_TAB,
     wx.WXK_RETURN,
     wx.WXK_ESCAPE,
     wx.WXK_DELETE,
     wx.WXK_START,
     wx.WXK_LBUTTON,
     wx.WXK_RBUTTON,
     wx.WXK_CANCEL,
     wx.WXK_MBUTTON,
     wx.WXK_CLEAR,
     wx.WXK_PAUSE,
     wx.WXK_CAPITAL,
     wx.WXK_PRIOR,
     wx.WXK_NEXT,
     wx.WXK_END,
     wx.WXK_HOME,
     wx.WXK_LEFT,
     wx.WXK_UP,
     wx.WXK_RIGHT,
     wx.WXK_DOWN,
     wx.WXK_PAGEUP,
     wx.WXK_PAGEDOWN,
     wx.WXK_SELECT,
     wx.WXK_PRINT,
     wx.WXK_EXECUTE,
     wx.WXK_SNAPSHOT,
     wx.WXK_INSERT,
     wx.WXK_HELP,
     wx.WXK_F1,
     wx.WXK_F2,
     wx.WXK_F3,
     wx.WXK_F4,
     wx.WXK_F5,
     wx.WXK_F6,
     wx.WXK_F7,
     wx.WXK_F8,
     wx.WXK_F9,
     wx.WXK_F10,
     wx.WXK_F11,
     wx.WXK_F12,
     wx.WXK_F13,
     wx.WXK_F14,
     wx.WXK_F15,
     wx.WXK_F16,
     wx.WXK_F17,
     wx.WXK_F18,
     wx.WXK_F19,
     wx.WXK_F20,
     wx.WXK_F21,
     wx.WXK_F22,
     wx.WXK_F23,
     wx.WXK_F24,
     wx.WXK_NUMLOCK,
     wx.WXK_SCROLL,
    ]
    # These are the keycodes that we have to catch in evt_key_down, not evt_char
    # By the time they get to evt_char then the OS has looked at them and gone,
    # hey, this keypress means do something (like pressing space acts as an ACTIVATE
    # key in a list control.
    catchInKeyDownIfDuringTypeAheadKeyCodes = [
     wx.WXK_SPACE
    ]
    # These are the keycodes that we will allow during typeahead, but won't allow to start
    # the type ahead process.
    dontStartTypeAheadKeyCodes = [
     wx.WXK_SHIFT,
     wx.WXK_CONTROL,
     wx.WXK_MENU, #ALT Key, ALT Gr generates both WXK_CONTROL and WXK_MENU.
    ]
    dontStartTypeAheadKeyCodes.extend(catchInKeyDownIfDuringTypeAheadKeyCodes)
    
    
    def __init__(self, typeAheadTimeout=500, casesensitive=False, columnToSearch=0):
        """"""
        tracer.debug("TypeAheadListCtrlMixin - __init__")
        
        # Do most work in the char handler instead of keydown.
        # This means we get the correct keycode for the key pressed as it should
        # appear on screen, rather than all uppercase or "default" us keyboard
        # punctuation.
        # However there are things that we need to catch in key_down to stop
        # them getting sent to the underlying windows control and generating
        # other events (notably I'm talking about the SPACE key which generates
        # an ACTIVATE event in these list controls).
        
        #  The combined class must have a GetListCtrl method that
        #  returns the wx.ListCtrl to be sorted, and the list control
        #  must exist at the time the wx.TypeAheadListCtrlMixin.__init__
        #  method is called because it uses GetListCtrl.
        
        self.alist = self.GetListCtrl()
        if not self.alist:
            raise ValueError, "TypeAheadListCtrlMixin - No wx.ListCtrl available"
        
        # Bind the events to their handlers
        self.alist.Bind(wx.EVT_KEY_DOWN, self.OnTypeAheadKeyDown)
        self.alist.Bind(wx.EVT_CHAR, self.OnTypeAheadChar)
        
        self.typeAheadTimer = wx.Timer(self, wx.NewId())
        # Bind the Timer event to its handler along with the timer object
        self.Bind(wx.EVT_TIMER, self.OnTypeAheadTimer, self.typeAheadTimer)
        
        self.clearTypeAhead()
        self.typeAheadTimeout = typeAheadTimeout
        self.columnToSearch   = columnToSearch
        
        if not casesensitive:
            self._GetItemText = lambda idx: self.alist.GetItem(idx, self.columnToSearch).GetText().lower()
            self._GetKeyCode = lambda keycode: chr(keycode).lower()
        else:
            self._GetItemText = lambda idx: self.alist.GetItem(idx, self.columnToSearch).GetText()
            self._GetKeyCode = chr
    
    
    def OnTypeAheadKeyDown(self, event):
        """"""
        tracer.debug("TypeAheadListCtrlMixin - OnTypeAheadKeyDown")
        
        keycode = event.GetKeyCode()
        
        if keycode in self.stopTypeAheadKeyCodes:
            self.clearTypeAhead()
        else:
            if self.typeAhead == None:
                if keycode in self.dontStartTypeAheadKeyCodes:
                    self.clearTypeAhead()
            else:
                if keycode in self.catchInKeyDownIfDuringTypeAheadKeyCodes:
                    self.OnTypeAheadChar(event)
                    return
        
        event.Skip()
    
    
    def OnTypeAheadChar(self, event):
        """"""
        tracer.debug("TypeAheadListCtrlMixin - OnTypeAheadChar")
        
        # stop the timer, to make sure that it doesn't fire in the middle of
        # doing this and screw up by None-ifying the typeAhead string.
        # TODO: Yes some kind of lock around a typeAheadState object
        # that contained typeAhead, lastTypeAheadFoundAnything and lastTypeAhead
        # would be better...
        self.typeAheadTimer.Stop()
        
        keycode = event.GetKeyCode()
        
        if keycode in self.stopTypeAheadKeyCodes:
            self.clearTypeAhead()
            skip = True
            # if delete key pressed and function exists then delete the selected item
            if keycode == wx.WXK_DELETE and "OnDeleteSelected" in dir(self):
                self.OnDeleteSelected()
                skip = False
            try:
                # Yield so the display can be seen
                wx.Yield()
            except:
                pass # ignore Yield failure
            # Don't pass on event if it has been handled here
            if skip:
                event.Skip()
            return
        else:
            if self.typeAhead == None:
                if keycode in self.dontStartTypeAheadKeyCodes:
                    self.clearTypeAhead()
                    event.Skip()
                    return
                else:
                    try:
                        self.typeAhead = self._GetKeyCode(keycode)
                    except ValueError:
                        pass # ignore chr() ValueError
            else:
                try:
                    self.typeAhead += self._GetKeyCode(keycode)
                except ValueError:
                    pass # ignore chr() ValueError
            
            self.doTypeAhead()
            
            # This timer is used to nullify the typeahead after a while
            self.typeAheadTimer.Start(self.typeAheadTimeout, wx.TIMER_ONE_SHOT)
    
    
    def inTypeAhead(self):
        """"""
        tracer.debug("TypeAheadListCtrlMixin - inTypeAhead")
        
        return self.typeAhead != None
    
    
    def currentlySelectedItemFoundByTypeAhead(self, idx):
        """This method is called when the typeahead string matches
           the text of the currently selected item.  Put code here if
           you want to have something happen in this case.
           NOTE: Method only called if there was a currently selected item.
           
           idx refers to the index of the currently selected item.
        """
        tracer.debug("TypeAheadListCtrlMixin - currentlySelectedItemFoundByTypeAhead")
        
        pass # we don't do anything as we've already selected the thing we want
    
    
    def currentlySelectedItemNotFoundByTypeAhead(self, idx):
        """This method is called when the typeahead string matches
           an item that isn't the currently selected one.  Put code
           here if you want something to happen to the currently
           selected item.
           NOTE: use newItemFoundByTypeAhead for doing something to
           the newly matched item.
           NOTE: Method only called if there was a currently selected item.
           
           idx refers to the index of the currently selected item.
        """
        tracer.debug("TypeAheadListCtrlMixin - currentlySelectedItemNotFoundByTypeAhead")
        
        # we deselect it.
        self.alist.SetItemState(idx, 0, wx.LIST_STATE_SELECTED)
        self.alist.SetItemState(idx, 0, wx.LIST_STATE_FOCUSED)
        
        try:
            # Yield so the display can be seen
            wx.Yield()
        except:
            pass # ignore Yield failure
    
    
    def newItemFoundByTypeAhead(self, idx):
        """This is called when the typeahead string matches
           an item that isn't the currently selected one.  Put
           code here if you want something to happen to the newly
           found item.
           NOTE: use currentlySelectedItemNotFoundByTypeAhead for
           doing something to the previously selected item.
           
           idx refers to the index of the newly matched item.
        """
        tracer.debug("TypeAheadListCtrlMixin - newItemFoundByTypeAhead")
        
        # we select it and make sure it is focused
        self.alist.SetItemState(idx, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        self.alist.SetItemState(idx, wx.LIST_STATE_FOCUSED, wx.LIST_STATE_FOCUSED)
        self.alist.EnsureVisible(idx)
        
        try:
            # Yield so the display can be seen
            wx.Yield()
        except:
            pass # ignore Yield failure
    
    
    def nothingFoundByTypeAhead(self, idx):
        """This method is called when the typeahead string doesn't
           match any items.  Put code here if you want something to
           happen in this case.
           
           idx refers to the index of the currently selected item
           or -1 if nothing was selected.
        """
        tracer.debug("TypeAheadListCtrlMixin - nothingFoundByTypeAhead")
        
        pass # don't do anything here, what could we do?
    
    
    def doTypeAhead(self):
        """"""
        tracer.debug("TypeAheadListCtrlMixin - doTypeAhead")
        
        curselected = -1
        
        if self.lastTypeAheadFoundSomething:
            curselected = self.lastTypeAhead
        else:
            curselected = self.alist.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        
        minn = 0
        
        try:
            if curselected != -1:
                term_name = self._GetItemText(curselected)
                if term_name.startswith(self.typeAhead):
                    self.currentlySelectedItemFoundByTypeAhead(curselected)
                    self.lastTypeAheadFoundAnything = True
                    self.lastTypeAhead              = curselected
                    return #We don't want this edgecase falling through
            
            new_idx = self.binary_search(self.typeAhead, minn)
            
            if new_idx != -1:
                if new_idx != curselected and curselected != -1:
                    self.currentlySelectedItemNotFoundByTypeAhead(curselected)
                self.newItemFoundByTypeAhead(new_idx)
                self.lastTypeAheadFoundAnything = True
                self.lastTypeAhead              = new_idx
            else:
                self.nothingFoundByTypeAhead(curselected)
                self.lastTypeAheadFoundAnything = False
                self.lastTypeAhead              = -1
        except TypeError:
            # might happen if a None slips by
            self.clearTypeAhead()
    
    
    # NOTE: Originally from ASPN. Augmented.
    def binary_search(self, t, m=0):
        """"""
        tracer.debug("TypeAheadListCtrlMixin - binary_search")
        
        minn = m
        maxx = self.alist.GetItemCount() - 1
        
        while 1:
            if maxx < minn:
                return self.doEdgeCase(m, t)
            m = (minn + maxx) / 2
            cur_term = self._GetItemText(m)
            if cur_term < t:
                minn = m + 1
            elif cur_term > t:
                maxx = m - 1
            else:
                return m
    
    
    def doEdgeCase(self, m, t):
        """ This method makes sure that if we don't find the typeahead
         as an actual string, then we will return the first item
         that starts with the typeahead string (if there is one)
        """
        tracer.debug("TypeAheadListCtrlMixin - doEdgeCase")
        
        before = self._GetItemText(max(0, m - 1))
        this   = self._GetItemText(m)
        after  = self._GetItemText(min((self.alist.GetItemCount() - 1) , m + 1))
        sliced = len(t)
        
        if this[:sliced] == t:
            return m
        elif before[:sliced] == t:
            return max(0, m - 1)
        elif after[:sliced] == t:
            return min((self.alist.GetItemCount() - 1), m + 1)
        else:
            return -1
    
    
    def clearTypeAhead(self):
        """"""
        tracer.debug("TypeAheadListCtrlMixin - clearTypeAhead")
        
        self.typeAhead                   = None
        self.lastTypeAheadFoundSomething = False
        self.lastTypeAheadIdx            = -1
    
    
    def OnTypeAheadTimer(self, event):
        """"""
        tracer.debug("TypeAheadListCtrlMixin - OnTypeAheadTimer")
        
        self.clearTypeAhead()

