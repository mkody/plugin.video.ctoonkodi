# -*- coding: utf-8 -*-
import sys, urllib, urlparse, re, requests, ast
import xbmc,xbmcgui,xbmcplugin

__handle__ = int(sys.argv[1])

ADDON_VERSION = '0.2.0'

BASE_URL = 'https://ctoon.party' # .stream and .network domains redirect to this.

SEASONS_PROPERTY = 'ctoonkodi.seasons_episodes'

#===================================================================================		
    
def view_shows():
    r = open_url(BASE_URL)
    cards = re.findall(r'<div class=.*?pmd-card.*?href="(/.+?)".*?src="(.+?jpg)".*?alt="(.+?)"', r.text, re.DOTALL)
    for show_url, img_url, show_name in cards:
        url_params = {'view': 'seasons', 'url': BASE_URL + show_url, 'thumbnail': BASE_URL + img_url}
        url = build_url(url_params)
        listitem = xbmcgui.ListItem(show_name)
        listitem.setArt({'poster': BASE_URL + img_url, 'fanart': BASE_URL + img_url})
        xbmcplugin.addDirectoryItem(__handle__, url, listitem, isFolder=True)
    xbmcplugin.endOfDirectory(__handle__)
    xbmc.executebuiltin('Container.SetViewMode(500)') # Estuary skin, grid mode.

    
def view_seasons(params):
    r = open_url(params['url'][0])
    html = r.text
    seasons = re.findall(r'false"> (.+?) <i class', html, re.DOTALL)
    seasons_episodes = dict()
    for season_name in seasons:
        ep_list = re.findall(season_name + r'.*?"row">(.*?)</div>\s*?</div>\s*?</div>', html, re.DOTALL)
        episodes = re.findall( r'href="(/.*?)">(.*?)</a>', ep_list[0], re.DOTALL )
        seasons_episodes[season_name] = episodes               
        url_params = {'view': 'episodes', 'season': season_name,
        'url': params['url'][0], 'thumbnail': params['thumbnail'][0]}
        url = build_url(url_params)
        listitem = xbmcgui.ListItem(season_name)
        listitem.setArt({'poster': params['thumbnail'][0]})
        xbmcplugin.addDirectoryItem(__handle__, url, listitem, isFolder=True)
    xbmcplugin.endOfDirectory(__handle__)
    # Store 'seasons_episodes' dict as a Window property (persistent memory data).
    window = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
    window.clearProperty(SEASONS_PROPERTY)
    window.setProperty(SEASONS_PROPERTY, str(seasons_episodes))
    
    
def view_episodes(params):
    current_window = xbmcgui.getCurrentWindowId()
    se_ep_data = xbmcgui.Window(current_window).getProperty(SEASONS_PROPERTY)
    if se_ep_data:
        seasons_episodes = ast.literal_eval( se_ep_data )
        episodes = seasons_episodes[ params['season'][0] ]
    else:
        # In case we're coming in from a favourited season the property won't be set.
        r = open_url(params['url'][0])
        pattern = params['season'][0] + r'.*?"row">(.*?)</div>\s*?</div>\s*?</div>'
        ep_list = re.findall(pattern, r.text, re.DOTALL)
        episodes = re.findall( r'href="(/.*?)">(.*?)</a>', ep_list[0], re.DOTALL )    
    xbmcgui.Window(current_window).clearProperty(SEASONS_PROPERTY)
    
    for episode_url, episode_name in episodes:
        url_params = {'view': 'media', 'url': BASE_URL + episode_url,
                      'thumbnail': params['thumbnail'][0]}
        url = build_url(url_params)
        listitem = xbmcgui.ListItem( episode_name.replace('&amp;', '&') )
        listitem.setArt( {'poster': params['thumbnail'][0]} )
        xbmcplugin.addDirectoryItem(__handle__, url, listitem, isFolder=True)
    xbmcplugin.endOfDirectory(__handle__)
    
    
def view_media(params):
    r = open_url(params['url'][0])
    media_list = re.findall(r'label="(.*?p)".*?src="(.*?webm)"', r.text, re.DOTALL)
    for media_quality, media_url in media_list:
        listitem = xbmcgui.ListItem(media_quality)
        listitem.setArt({'poster': params['thumbnail'][0]})
        listitem.setProperty('IsPlayable', 'true')
        listitem.setPath(media_url)
        xbmcplugin.addDirectoryItem(__handle__, media_url, listitem, isFolder=False) 
    xbmcplugin.endOfDirectory(__handle__)
    
#==================================================================================	=	  

def build_url(query):
    return sys.argv[0] + '?' + urllib.urlencode(query)


def open_url(url):
    r = requests.get(url, headers={'User-Agent' : 'CTOON Kodi/' + ADDON_VERSION})
    if r.status_code != requests.codes.ok:
        raise Exception("Could not connect to CTOON")
    return r
    
#===================================================================================

### Entry point ###

params = urlparse.parse_qs(sys.argv[2][1:])
view = params.get('view', None)

if not view:
    view_shows()
elif view[0] == 'seasons':
    view_seasons(params)
elif view[0] == 'episodes':
    view_episodes(params)
elif view[0] == 'media':
    view_media(params)
else:
    view_shows()