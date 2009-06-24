# -*- coding: utf-8 -*-

# Parse variables from LUA files (as used by the WoW SavedVariables)
# Based on the simple JSON parser by Paul McGuire: http://pyparsing.wikispaces.com/space/showimage/jsonParser.py

from pyparsing import *

TRUE = Keyword("true").setParseAction( replaceWith(True) )
FALSE = Keyword("false").setParseAction( replaceWith(False) )
NULL = Keyword("nil").setParseAction( replaceWith(None) )

luaIdentifier = Word(alphas, alphanums + "_")
luaString = dblQuotedString.setParseAction( removeQuotes )
luaInteger = Word(nums)
luaNumber = Combine( Optional('-') + ( '0' | Word('123456789',nums) ) +
                    Optional( '.' + Word(nums) ) +
                    Optional( Word('eE',exact=1) + Word(nums+'+-',nums) ) )

luaDictIndex = ( luaString | luaInteger )

luaValue = Forward()
luaMembers = Forward()
luaArray = Suppress('{') + Optional(delimitedList( luaValue ), None) + Optional(Suppress(",")) + Suppress('}')
luaKey = Suppress('[') + luaDictIndex + Suppress(']')
luaMembers << Group(luaKey + Suppress('=') + luaValue)
luaValue << ( luaMembers | luaString | luaNumber | luaArray | TRUE | FALSE | NULL )

luaObject = dictOf(luaIdentifier + Suppress("="),  luaValue)

luaComment = "--" + restOfLine

settingsFile = ZeroOrMore(luaObject)
settingsFile.ignore(luaComment)

def convertNumbers(s,l,toks):
    n = toks[0]
    try:
        return int(n)
    except ValueError, ve:
        return float(n)


luaNumber.setParseAction( convertNumbers )
luaInteger.setParseAction( convertNumbers )

def parseLua(filename):
    """ Parses a lua file using the pyparsing library """
    return settingsFile.parseFile(filename)


def unparseLua(pr):
    """ Outputs lua from the given parseresult """
    
    prl = pr.asList()
    
    result = "%s = "

