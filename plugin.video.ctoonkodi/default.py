# -*- coding: utf-8 -*-
import sys, urllib, urlparse, re, requests
import xbmc,xbmcaddon,xbmcgui,xbmcplugin,xbmcvfs


__handle__ = int(sys.argv[1])

BASE_URL    = 'https://ctoon.party' # .stream and .network domains redirect to this.


def view_shows(params):
    r = open_url(BASE_URL)
    
    html = r.text
    cards = re.findall(r'<div class=.*?pmd-card.*?href="(/.+?)".*?src="(.+?jpg)".*?alt="(.+?)"', html, re.DOTALL)
    listing = []
    for show_url, img_url, show_name in cards:
        listing.append( make_list_item('SEASONS', BASE_URL + show_url, show_name, BASE_URL + img_url) )
        
    xbmcplugin.addDirectoryItems(__handle__, listing, len(listing))
    xbmcplugin.endOfDirectory(__handle__)
    xbmc.executebuiltin('Container.SetViewMode(500)') # Estuary skin, grid mode.

    
def view_seasons(params):
    r = open_url(params['URL'])
    
    html = r.text
    seasons = re.findall(r'false"> (.+?) <i class', html, re.DOTALL)
    listing = []
    for season_name in seasons:
        listing.append( make_list_item('EPISODES', params['URL'], season_name, params['THUMB']) )
        
    xbmcplugin.addDirectoryItems(__handle__, listing, len(listing))
    xbmcplugin.endOfDirectory(__handle__)
        
    
def view_episodes(params):
    # Silly XBMC API that doesn't allow persistent data, now we have to waste
    # another GET request for the same page to get data for a different screen.
    r = open_url(params['URL'])
    
    html = r.text
    ep_list = re.findall(params['NAME'] + r'.*?"row">(.*?)</div>\s*?</div>\s*?</div>', html, re.DOTALL)
    episodes = re.findall( r'href="(/.*?)">(.*?)</a>', ep_list[0], re.DOTALL )
    
    listing = []
    for episode_url, episode_name in episodes:
        listing.append( make_list_item('MEDIA', BASE_URL + episode_url, \
        	                               episode_name.replace('&amp;', '&'), params['THUMB']) )
        
    xbmcplugin.addDirectoryItems(__handle__, listing, len(listing))
    xbmcplugin.endOfDirectory(__handle__)
    
    
def view_media(params):
    r = open_url(params['URL'])
    
    html = r.text
    media_list = re.findall(r'label="(.*?p)".*?src="(.*?webm)"', html, re.DOTALL)
    
    listing = []
    for media_quality, media_url in media_list:        
        listing.append( make_list_item('PLAY', media_url, media_quality, params['THUMB']) )
        
    xbmcplugin.addDirectoryItems(__handle__, listing, len(listing))
    xbmcplugin.endOfDirectory(__handle__)
    

#===================================================================================


def open_url(url):
    r = requests.get(url, headers={'User-Agent' : 'CTOON Kodi/0.1.0'})
    if r.status_code != requests.codes.ok:
        raise Exception("Could not connect to CTOON")
        #xbmcplugin.endOfDirectory(__handle__) # Is this really needed?
    return r

    
def make_list_item(mode, url, name, thumbnail):
    item_url=sys.argv[0]+"?mode="+mode+"&url="+urllib.quote_plus(url)+"&name="+urllib.quote_plus(name)+"&thumb="+urllib.quote_plus(thumbnail)
    is_folder = False
    if mode=='SEASONS' or mode=='EPISODES':
        li=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=thumbnail)
        is_folder = True
        if mode=='SEASONS':
            li.setArt({'thumb' : thumbnail, 'posterbanner' : thumbnail, 'fanart' : thumbnail})
    elif mode=='MEDIA' or mode=='PLAY':
        li=xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=thumbnail)
        li.setInfo(type="Video", infoLabels={"Title": name})
        if mode=='PLAY':
            li.setProperty('IsPlayable', 'true')
            li.setPath(url)
        else:
            is_folder=True
    return (item_url, li, is_folder)
    

def play_url(params):
    li = xbmcgui.ListItem(path=params['URL'])
    li.setProperty('IsPlayable', 'true')
    li.setPath(params['URL'])
    xbmcplugin.setResolvedUrl(__handle__, True, listitem=li) # Play the thing.

    
def get_params():
    temp = urlparse.parse_qs(sys.argv[2][1:])
    if len(temp)>1:
        params = {
            'MODE' : temp['mode'][0],
            'URL'  : urllib.unquote_plus(temp['url'][0]),
            'NAME' : urllib.unquote_plus(temp['name'][0]),
            'THUMB': urllib.unquote_plus(temp['thumb'][0])
        }
        return params
    else:
        return { 'MODE' : 'SHOWS' }
    
    
#===================================================================================


params = get_params()

actions = {
    'SHOWS' : view_shows,
    'SEASONS' : view_seasons,
    'EPISODES' : view_episodes,
    'MEDIA' : view_media,
    'PLAY' : play_url
}
actions[ params['MODE'] ]( params )