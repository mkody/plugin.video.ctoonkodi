# -*- coding: utf-8 -*-
import sys
import json
import requests
from urllib import urlencode
from urlparse import parse_qs
from ast import literal_eval

import xbmc
import xbmcgui
import xbmcplugin


ADDON_VERSION = '0.3.0'


# Changelog:
#   0.3.0
#       - Added support for the ctoon web API.
#       - Code cleanup and improvement.
#
#   0.2.0
#       - Initial release.
#
#   TODO: 
#       - Allow VTT subtitle loading, and convert to SRT:
#         # VTT to SRT conversion code from Jansen A. Simanullang:
#         # https://github.com/jansenicus/vtt-to-srt.py/blob/master/vtt-to-srt.py#L29-L32
#         import re
#         tempSRT = re.sub( r'([\d]+)\.([\d]+)', r'\1,\2', vttData )
#         tempSRT = re.sub( r'WEBVTT[\s]*', '', tempSRT )
#         tempSRT = re.sub( r'^\d+\n', '', tempSRT )
#         srtData = re.sub( r'\n\d+\n', '\n', tempSRT )
#  
#         # etc. etc., load subtitle into the Player like this:
#         https://github.com/covenantkodi/script.module.covenant/blob/master/lib/resources/lib/modules/player.py#L339-L355
#
#       - Add some simple 'unwatched \ watched' marking so users can tell what episodes they've watched.
#         (That is, so you don't get the error message when you cancel the 'Select Quality' dialog.)


__handle__ = int( sys.argv[1] )

BASE_URL = 'https://ctoon.party'

PROPERTY = 'ctoonkodi.property'

#===================================================================================

def viewShows():
    global __handle__
    xbmcplugin.setContent( __handle__, 'episodes' ) # Estuary skin has better layout for this than for 'tvshows' content.

    r = ctoonGET()
    if r:
        data = json.loads( r.text )
        itemList = [ ]

        for showData in data:
            coverUrl = BASE_URL + showData['cover']
            showName = showData['name']

            item = xbmcgui.ListItem( showName )
            item.setArt( { 'icon': coverUrl, 'poster': coverUrl, 'fanart': coverUrl } )
            item.setInfo( 'video', infoLabels = {
                                       'tvshowtitle': showName,
                                       'plot': showData['description'],
                                       'description': showName,
                                       'mediatype': 'episode'                                       
                                   }
                        )

            urlParams = {
                'view': 'SEASONS',
                'name': showName,
                'short_name': showData['short_name'],
                'thumbnail': coverUrl
            }
            url = buildUrl( urlParams )

            itemList.append( ( url, item, True ) )

        xbmcplugin.addDirectoryItems( __handle__, itemList )
    xbmcplugin.endOfDirectory( __handle__ )


def viewSeasons( params ):
    global __handle__
    xbmcplugin.setContent( __handle__, 'episodes' )

    r = ctoonGET( params['short_name'][0] )
    if r:
        data = json.loads( r.text )
        itemList = [ ]

        coverUrl = params['thumbnail'][0]

        # Sort seasons and put the 'Extra' and 'Movie' seasons at the end of the list.
        orderedKeys = sorted( data['seasons'].keys(), key = lambda k: k if k.lower().startswith( 'season' ) else 'z' )
        
        for seasonKey in orderedKeys:
            item = xbmcgui.ListItem( seasonKey )
            item.setArt( { 'icon': coverUrl, 'poster': coverUrl } )
            seasonNumber = data['seasons'][seasonKey][0]['season']
            seasonNumber = int( seasonNumber ) if seasonNumber.isdigit() else 0
            item.setInfo( 'video', infoLabels = {
                                       'originaltitle': params['name'],
                                       'tvshowtitle': params['name'],
                                       'season': seasonNumber,
                                       'mediatype': 'season'
                                   }
                        )

            urlParams = {
                'view': 'EPISODES',
                'name': params['name'][0],
                'short_name': params['short_name'][0],
                'seasonKey': seasonKey,
                'seasonNumber': seasonNumber,
                'thumbnail': coverUrl
            }
            url = buildUrl( urlParams )

            itemList.append( ( url, item, True ) )

        clearWindowProperty( PROPERTY )
        setWindowProperty( PROPERTY, data['seasons'] ) # Pass on to the 'viewEpisodes' function, to save off a GET request.
        xbmcplugin.addDirectoryItems( __handle__, itemList )
    xbmcplugin.endOfDirectory( __handle__ )


def viewEpisodes( params ):
    global __handle__
    xbmcplugin.setContent( __handle__, 'episodes' )

    episodes = None

    allSeasons = getWindowProperty( PROPERTY )
    if allSeasons:
        episodes = allSeasons[ params['seasonKey'][0] ]
    else:
        # In case we're coming in from a favourited season the property won't be set.
        r = ctoonGET( params['short_name'][0] )
        if r:
            data = json.loads( r.text )
            episodes = data['seasons'][ params['seasonKey'][0] ]
    clearWindowProperty( PROPERTY )

    itemList = [ ]
    dateLength = len( 'yyyy-mm-dd' )
    coverUrl = params['thumbnail'][0]
    seasonNumber = params['seasonNumber'][0]
    seasonLabel = ( seasonNumber + 'x' ) if seasonNumber != '0' else ''
    showName = params['name'][0]
    
    genericInfo = {
        'originaltitle': showName,
        'tvshowtitle': showName,
        'season': int( seasonNumber ),
        'episode': -1,
        'mediatype': 'episode'
    }

    for episodeData in episodes:
        episodeNumbers = episodeData['episode'].split('_') # Handles single episodes e.g. '8' and double episodes e.g. '20_21'.
        if len( episodeNumbers ) > 1:
            label = '-'.join( episodeNumbers )
            # These are multiple episodes in one.
            # Maybe get the metadata for only the first one?
        else:
            label = episodeNumbers[0]
            # Since it's a single episode, at this point it's easy
            # to get the episode description, thumbnail, subtitle etc.
            # from a metadata service.
        
        label = seasonLabel + label + ' ' + episodeData['title']
        airdate = episodeData['published_date'][:dateLength]
        
        episodeInfo = genericInfo.copy()
        episodeInfo.update(
            {
                'title': label,
                'episode': int( episodeNumbers[0] ),
                'aired': airdate,
                'premiered': airdate,
                'year': airdate.split('-')[0]
            }
        )
        item = xbmcgui.ListItem( label )
        item.setArt( { 'icon': coverUrl, 'poster': coverUrl } )
        item.setInfo( 'video', episodeInfo )
        item.setProperty( 'IsPlayable', 'true' ) # Allows the checkmark to be placed on watched episodes.
                
        urlParams = {
           'view': 'MEDIA',
           'apiEpisode': params['short_name'][0] + '/' + str( episodeData['id'] ),
           'itemLabel': label,
           'infoLabels': str( episodeInfo ),
           'thumbnail': coverUrl
        }
        url = buildUrl( urlParams )

        itemList.append( ( url, item, False ) )

    xbmcplugin.addDirectoryItems( __handle__, itemList )
    xbmcplugin.endOfDirectory( __handle__ )


def viewMedia( params ):
    global __handle__

    r = ctoonGET( params['apiEpisode'][0] )
    if r:
        episodeData = json.loads( r.text )['episode']
        
        itemLabel = params['itemLabel'][0]
        episodeInfo = literal_eval( params['infoLabels'][0] )
        coverUrl = params['thumbnail'][0]
        
        itemList = [ ]
        listOrder = { '720p': 0, '1080p': 1, '480p': 2, '240p': 3 } # Use the same media order as the HTML source.
        
        for quality in episodeData['files']['webm']:
            mediaUrl = BASE_URL + episodeData['files']['webm'][quality]
            
            item = xbmcgui.ListItem( quality )
            item.setArt( { 'icon': coverUrl, 'poster': coverUrl } )
            item.setInfo( 'video', episodeInfo )
            item.setPath( mediaUrl )
            item.setMimeType( 'video/webm' )
            item.setProperty( 'IsPlayable', 'true' )
            item.setProperty( '_tempKey', quality if quality.endswith( 'p' ) else quality + 'p' )

            itemList.append( item )

        itemList = sorted( itemList, key = lambda item: listOrder.get( item.getProperty( '_tempKey' ), 4 ) )
        index = xbmcgui.Dialog().select(
            'Select Quality',
            [ item.getProperty( '_tempKey' ) for item in itemList ],
            useDetails = True
        )
        if index >= 0:
            xbmcplugin.setResolvedUrl( __handle__, True, listitem = itemList[index] )
            #xbmc.Player().play( item = mediaUrl, listitem = itemList[index] ) # Alternative play method.
        else:
            pass

#==================================================================================	=

def buildUrl( query ):
    return sys.argv[0] + '?' + urlencode( { k: unicode( v ).encode( 'utf-8' ) for k, v in query.iteritems() } )


def ctoonGET( apiLocation = '' ):
    userAgent = 'CTOONKodi/' + ADDON_VERSION + ' (JSON API; +https://github.com/dokoab/ctoonkodi)'
    try:
        r = requests.get(
            BASE_URL + '/api/' + apiLocation,
            headers = { 'User-Agent': userAgent },
            timeout = 15 # Seconds.
        )
        if r.status_code != requests.codes.ok:
            raise Exception( 'Could not connect to CTOON' )
        else:
            return r
    except requests.exceptions.Timeout:
        raise Exception( 'Request to CTOON timed out' )
    return None


def getWindowProperty( prop ):
    window = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
    data = window.getProperty( prop )
    return json.loads( data ) if data else None


def setWindowProperty( prop, data ):
    window = xbmcgui.Window( xbmcgui.getCurrentWindowId())
    temp = json.dumps( data )
    window.setProperty( prop, temp )
    return temp


def clearWindowProperty( prop ):
    window = xbmcgui.Window( xbmcgui.getCurrentWindowId())
    window.clearProperty( prop )

#===================================================================================

params = parse_qs( sys.argv[2][1:] )
view = params.get( 'view', None )

if not view:
    viewShows()             # View all shows.
elif view[0] == 'SEASONS':
    viewSeasons( params )   # View all seasons of a show.
elif view[0] == 'EPISODES':
    viewEpisodes( params )  # View all episodes of a season.
elif view[0] == 'MEDIA':
    viewMedia( params )     # View all media URLs of an episode.
else:
    viewShows()