# -*- coding: utf-8 -*-
# $Id: WurmLanguage.py 623 2009-04-21 18:54:22Z jonhogg $

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

# This file has no connections back to the rest of WUU (and should stay as standalone as possible)

import os, sys

try: # Import C-based ElementTree module
    from xml.etree.cElementTree import ElementTree, Element, SubElement
except ImportError:
    try:
        # Fallback level 1, try the "native" ElementTree in Python 2.5
        from xml.etree.ElementTree import ElementTree, Element, SubElement
    except ImportError:
        # Fallback level 2, use the provided ElementTree
        from ElementTree import ElementTree, Element, SubElement

languagenames = {'en': 'English'}
languages = {'en': {}}
current = None


def _parse(lstr):
    """ Parses and expands the escaped characters in the given string"""
    # TODO: Make this handle more than \n & \t (if necessary)
    
    if "\\t" in lstr:
        return lstr.replace("\\t", "\t")
    else:
        return lstr.replace("\\n", "\n")


def loadLanguageFile(langfile):
    """ Loads one or more languages from disk
    Returns list of language codes found."""
    
    global languagenames, languages
    
    tree = ElementTree(file=langfile)
    
    foundlangs = []
    
    langslist = tree.find("wurmlanguages")
    langs     = langslist.findall("languagedef")
    
    for language in langs:
        code = language.attrib["code"]
        name = language.attrib.get("name", code)
        
        languagenames[code] = name
        languages.setdefault(code, {}) # make sure the base map is ready
        
        if code not in foundlangs:
            foundlangs.append(code)
        
        lstrings = language.findall("string")
        for lstr in lstrings:
            orig = _parse(lstr.find("original").text.strip())
            tran = _parse(lstr.find("translation").text.strip())
            languages[code][orig] = tran
    
    return foundlangs


def s(strcode):
    """ Retrieves a string code from the current language, falling back to English if necessary
    Typically s() will be aliased to _() in the modules that use WurmLanguage.py.
    """
    
    global languages, current
    
    if not current:
        setCurrent('en') # sets the default language if none are specified
    
    langstr = sl(strcode, current)
    
    return langstr


def sl(strcode, lang):
    """ Retrieves a string code from the specific language, falling back to English if necessary """
    global languages
    
    language = languages.get(lang, languages['en'])
    langstr = language.get(strcode, strcode)
    
    return langstr


def getLanguages():
    """ Returns the inverse of languagenames """
    global languagenames
    
    # TODO: Rewrite this with map()/zip() and stuff
    languageset = {}
    
    for l in languagenames:
        languageset[languagenames[l]] = l
    
    return languageset


def setCurrent(langcode):
    """ Sets current language """
    global languagenames, current
    
    oldlang = current
    
    current = langcode
    
    return oldlang # returns previous language, if for some insane reason we want a temporary switch

