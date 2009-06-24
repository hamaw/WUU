# -*- coding: utf-8 -*-
# $Id: WUUAbout.py 616 2009-04-20 11:24:22Z jonhogg $

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

import wx
import wx.html
import wx.lib.wxpTag
from WUUHelpers import BrowserHtmlWindow


class WUUAboutBox(wx.Dialog):
    text = '''
<html>
<body>
<center><table width="100%%" cellspacing="0" bgcolor="#336699"
cellpadding="0" border="1">
<tr>
    <td align="center">
    <h3>WoW UI Updater %s</h3>
    <br>
    by The WUU Development Team<br>
    </td>
</tr>
</table>
    
<p><b>WUU</b> is a World of Warcraft UI addon updater</p>
    
<p>More info on <a href="http://wuu.vagabonds.info/" target="_blank">wuu.vagabonds.info</a></p>
    
<p><a href="http://sourceforge.net/projects/wuu" target="_blank">SourceForge project page</a></p>
    
<p><wxp module="wx" class="Button">
    <param name="label" value="Okay">
    <param name="id"    value="ID_OK">
</wxp></p>
</center>
</body>
</html>
'''
    
    def __init__(self, parent, version):
        """"""
        tracer.debug("WUUAboutBox - __init__")
        
        wx.Dialog.__init__(self, parent, -1, 'About WUU',)
        
        html = BrowserHtmlWindow(self, -1, size=(300, -1))
        
        if "gtk2" in wx.PlatformInfo:
            html.SetStandardFonts()
        
        html.SetPage(self.text % (version))
        # btn = html.FindWindowById(wx.ID_OK)
        ir = html.GetInternalRepresentation()
        html.SetSize((ir.GetWidth() +25, ir.GetHeight() +25))
        self.SetClientSize(html.GetSize())
        self.CentreOnParent(wx.BOTH)
    

