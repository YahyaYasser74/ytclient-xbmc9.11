# -*- coding: ascii -*-
# default.py  -  XBMC 9.11 YouTube client  (Python 2.4)

import xbmc
import xbmcgui
import urllib
import os
import time
import random

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        # Neither json nor simplejson available -- provide a minimal stub
        # so the rest of the script can still run (API features will not work).
        class json:
            @staticmethod
            def loads(s):
                return {}
            @staticmethod
            def dumps(o):
                return '{}'

# =============================================================================
# Configuration
# =============================================================================
PROXY = "http://127.0.0.1:8080"

# VOD Playback Method: "direct", "conversion", or "pipe"
# "direct" = stream directly from CDN (current method)
# "conversion" = download/convert first, then play (fallback method)
# "pipe" = stream video data directly through proxy without CDN resolution
VOD_PLAYBACK_METHOD = "pipe"

# YouTube Data API v3 key.  Leave empty to use proxy only. (item 12)
# Get a key at: https://console.cloud.google.com/
YT_API_KEY = ""   # e.g. "AIzaSy..."

# YouTube API Account Key for OAuth-based operations (notifications, comments, etc.)
# This is used for tasks requiring authentication
YT_API_ACCOUNT_KEY = ""

# Custom proxy settings (e.g., yt2009, Invidious, etc.)
CUSTOM_PROXY_URL = ""  # e.g., "https://yt.lemnoslife.com"

# Cookies file path for authentication
COOKIES_FILE = xbmc.translatePath("special://profile/yt_cookies.txt")

# JSON config file path
JSON_CONFIG_FILE = xbmc.translatePath("special://profile/yt_config.json")

# Playback timeout settings (in seconds)
PLAYBACK_START_TIMEOUT = 10
LIVE_STREAM_START_TIMEOUT = 30
CONVERSION_DOWNLOAD_TIMEOUT = 60

# Cache settings (in seconds)
CONFIG_CACHE_TIMEOUT = 5
LIST_CACHE_TIMEOUT = 10

# Result limits
SEARCH_RESULT_LIMIT = 10
TRENDING_RESULT_LIMIT = 10
RECOMMENDATION_RESULT_LIMIT = 12
COMMENT_LIMIT = 20

# Notification duration (in milliseconds)
NOTIFICATION_DURATION = 4000

# File paths
PROF_DIR  = xbmc.translatePath("special://profile/")
HIST_FILE = xbmc.translatePath("special://profile/yt_history.txt")
WL_FILE   = xbmc.translatePath("special://profile/yt_watchlater.txt")
SH_FILE   = xbmc.translatePath("special://profile/yt_searchhist.txt")
CH_FILE   = xbmc.translatePath("special://profile/yt_channels.txt")
CFG_FILE  = xbmc.translatePath("special://profile/yt_config.txt")
MUSIC_FILE = xbmc.translatePath("special://profile/yt_music.txt")

# Script directory for downloaded audio
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADED_AUDIOS_DIR = os.path.join(SCRIPT_DIR, "downloaded_audios")

# Auto-create directories
for path in [PROF_DIR, DOWNLOADED_AUDIOS_DIR]:
    if path and not os.path.exists(path):
        try:
            os.makedirs(path)
        except Exception:
            pass

# Auto-create config files if they don't exist
for path in [COOKIES_FILE, JSON_CONFIG_FILE, HIST_FILE, WL_FILE, SH_FILE, CH_FILE, CFG_FILE, MUSIC_FILE]:
    if path and not os.path.exists(path):
        try:
            # Create parent directory if needed
            parent = os.path.dirname(path)
            if parent and not os.path.exists(parent):
                os.makedirs(parent)
            # Create empty file (Python 2.4 compatible - no with statement)
            f = open(path, 'w')
            f.close()
        except Exception:
            pass

SH_MAX = 20

# Quality options shown in the play/download picker
QUALITY_OPTS = [
    ("[144p]  144p",      "144p"),
    ("[240p]  240p",      "240p"),
    ("[360p]  360p",      "360p"),
    ("[480p]  480p",      "480p"),
    ("[720p]  720p",      "720p"),
    ("[MP4]   Best Quality",  "best_mp4"),
    ("[MAX]   Max Quality",      "best"),
]

# Subtitle options for download
SUB_OPTS = [
    ("[OFF]  No subtitles",         "none"),
    ("[EN]   English subtitles",    "en"),
    ("[AUTO] Auto-generated (EN)",  "auto"),
]

# =============================================================================
# Seed video pool -- fallback for recommendations
# =============================================================================
SEED_VIDEOS = [
    ("Michael Jackson - Billie Jean",           "Zi_XLOBDo_Y"),
    ("Michael Jackson - Thriller",              "sOnqjkJTMaA"),
    ("Queen - Bohemian Rhapsody",               "tgbNymZ7vqY"),
    ("Queen - We Will Rock You",                "gP5GamevRJg"),
    ("Eminem - Lose Yourself",                  "iik25wqIuFo"),
    ("Eminem - Without Me",                     "YVkUvmDQ3HY"),
    ("Rick Astley - Never Gonna Give You Up",   "dQw4w9WgXcQ"),
    ("Nirvana - Smells Like Teen Spirit",       "hTWKbfoikeg"),
    ("The Beatles - Let It Be",                 "QDYfEBY9NM4"),
    ("The Beatles - Hey Jude",                  "A_MjCqQoLLA"),
    ("ABBA - Dancing Queen",                    "xFrGuyw1V8s"),
    ("ABBA - Waterloo",                         "Sj_9CiNkkn4"),
    ("Guns N Roses - Sweet Child O Mine",       "1w7OgIMMRc4"),
    ("David Bowie - Heroes",                    "6F5gBBNMXfU"),
    ("Led Zeppelin - Stairway To Heaven",       "QkF3oxziUI4"),
    ("AC DC - Back In Black",                   "pAgnJDJN4VA"),
    ("Metallica - Enter Sandman",               "CD-E4UxokGs"),
    ("Daft Punk - Get Lucky",                   "5NV6Rdv1h3I"),
    ("Daft Punk - Around The World",            "K0HSD71XJSQ"),
    ("Adele - Rolling in the Deep",             "rYEDA3JcQqw"),
    ("Adele - Hello",                           "YQHsXMglC9A"),
    ("Drake - God's Plan",                      "xpVfcZ0ZcFM"),
    ("Taylor Swift - Shake It Off",             "nfWlot6h_JM"),
    ("Taylor Swift - Blank Space",              "e-ORhEE9VVg"),
    ("Ed Sheeran - Shape of You",               "JGwWNGJdvx8"),
    ("Kendrick Lamar - HUMBLE.",                "tvtjLV5bbSU"),
    ("Bruno Mars - Uptown Funk",                "OPf0YbXqDm0"),
    ("Bruno Mars - 24K Magic",                  "UqyT8IEBqlY"),
    ("Billie Eilish - bad guy",                 "DyDfgMOUjCI"),
    ("The Weeknd - Blinding Lights",            "4NRXx6U8ABQ"),
    ("Post Malone - Rockstar",                  "UceaB4D0jpo"),
    ("Coldplay - Yellow",                       "yKNxeF4KMsY"),
    ("Coldplay - The Scientist",                "RB-RcX5DS5A"),
    ("Amy Winehouse - Rehab",                   "KUmZp8pR1uc"),
    ("Red Hot Chili Peppers - Californication", "YlUKcNNmywk"),
    ("Pink Floyd - Comfortably Numb",           "x-xTttimcNk"),
    ("Johnny Cash - Hurt",                      "8AHCfZTRGiI"),
    ("Bob Marley - No Woman No Cry",            "IT8XvzIfiOc"),
    ("Whitney Houston - I Will Always Love You","3JWTaaS7LdU"),
    ("Prince - Purple Rain",                    "TvnYmWpD_T8"),
]

# =============================================================================
# Config helpers (simple key=value file)
# =============================================================================
def read_config():
    """Read config dict from CFG_FILE (simple key=value format)."""
    cfg = {}
    try:
        if os.path.exists(CFG_FILE):
            for line in open(CFG_FILE):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    cfg[k.strip()] = v.strip()
    except Exception:
        pass
    return cfg

def read_json_config():
    """Read JSON config from JSON_CONFIG_FILE for advanced settings."""
    cfg = {}
    try:
        if JSON_CONFIG_FILE and os.path.exists(JSON_CONFIG_FILE):
            f = open(JSON_CONFIG_FILE, 'r')
            try:
                content = f.read()
                if content.strip():
                    cfg = json.loads(content)
            finally:
                f.close()
    except Exception:
        # If file doesn't exist or can't be read, return empty config
        pass
    return cfg

def write_json_config(cfg):
    """Write config dict to JSON_CONFIG_FILE."""
    try:
        if JSON_CONFIG_FILE:
            # Ensure directory exists
            json_dir = os.path.dirname(JSON_CONFIG_FILE)
            if json_dir and not os.path.exists(json_dir):
                os.makedirs(json_dir)
            f = open(JSON_CONFIG_FILE, 'w')
            try:
                json.dump(cfg, f, indent=2)
            finally:
                f.close()
            return True
    except Exception:
        pass
    return False

def write_config(cfg):
    try:
        f = open(CFG_FILE, "w")
        for k, v in cfg.items():
            f.write(k + '=' + v + '\n')
        f.close()
    except Exception:
        pass

def get_api_key():
    if YT_API_KEY:
        return YT_API_KEY
    cfg = read_config()
    return cfg.get('api_key', '')

def set_api_key(key):
    cfg = read_config()
    cfg['api_key'] = key
    write_config(cfg)

# Config cache for optimization
_config_cache = {}
_config_cache_time = 0

def get_cached_config():
    """Get config with caching to reduce file I/O."""
    global _config_cache, _config_cache_time
    import time
    current_time = time.time()
    if current_time - _config_cache_time > CONFIG_CACHE_TIMEOUT:
        _config_cache = read_config()
        _config_cache_time = current_time
    return _config_cache

def get_api_key_optional():
    """Get API key if available, return None if not set (for optional API usage)."""
    cfg = get_cached_config()
    key = cfg.get('api_key', YT_API_KEY)
    if key:
        return key
    return None

def get_vod_playback_method():
    cfg = get_cached_config()
    return cfg.get('vod_playback_method', VOD_PLAYBACK_METHOD)

def set_vod_playback_method(method):
    cfg = read_config()
    cfg['vod_playback_method'] = method
    write_config(cfg)
    # Invalidate cache
    global _config_cache_time
    _config_cache_time = 0

# =============================================================================
# File list helpers  (title on line N, id on line N+1)
# =============================================================================
# File list cache for optimization
_list_cache = {}
_list_cache_time = {}

def read_list(filepath):
    """Read list with caching to reduce file I/O."""
    import time
    current_time = time.time()
    cache_time = _list_cache_time.get(filepath, 0)
    
    # Cache for LIST_CACHE_TIMEOUT seconds
    if filepath in _list_cache and current_time - cache_time < LIST_CACHE_TIMEOUT:
        return _list_cache[filepath]
    
    titles, ids = [], []
    if not os.path.exists(filepath):
        _list_cache[filepath] = (titles, ids)
        _list_cache_time[filepath] = current_time
        return titles, ids
    f = open(filepath, "r")
    raw = f.readlines()
    f.close()
    for i in range(0, len(raw), 2):
        if i + 1 < len(raw):
            titles.append(raw[i].strip())
            ids.append(raw[i + 1].strip())
    
    _list_cache[filepath] = (titles, ids)
    _list_cache_time[filepath] = current_time
    return titles, ids

def write_list(filepath, titles, ids):
    f = open(filepath, "w")
    for k in range(len(titles)):
        f.write(titles[k] + "\n" + ids[k] + "\n")
    f.close()
    # Invalidate cache
    global _list_cache_time
    _list_cache_time[filepath] = 0

def file_append(filepath, title, vid, check_dupe=0):
    titles, ids = read_list(filepath)
    if check_dupe and vid in ids:
        return 0
    titles.append(title)
    ids.append(vid)
    write_list(filepath, titles, ids)
    return 1

def count_list(filepath):
    return len(read_list(filepath)[0])

def dedup_list(filepath):
    titles, ids = read_list(filepath)
    if not ids:
        return 0
    seen, new_t, new_i, removed = [], [], [], 0
    idx = len(ids) - 1
    while idx >= 0:
        if ids[idx] not in seen:
            seen.append(ids[idx])
            new_t.insert(0, titles[idx])
            new_i.insert(0, ids[idx])
        else:
            removed += 1
        idx -= 1
    if removed:
        write_list(filepath, new_t, new_i)
    return removed

# =============================================================================
# Search history
# =============================================================================
def read_search_hist():
    if not os.path.exists(SH_FILE):
        return []
    f = open(SH_FILE, "r")
    raw = f.readlines()
    f.close()
    return [l.strip() for l in raw if l.strip()]

def write_search_hist(queries):
    f = open(SH_FILE, "w")
    for q in queries:
        f.write(q + "\n")
    f.close()

def push_search_hist(query):
    queries = read_search_hist()
    queries = [q for q in queries if q != query]
    queries.insert(0, query)
    write_search_hist(queries[:SH_MAX])

def clear_search_hist():
    if os.path.exists(SH_FILE):
        os.remove(SH_FILE)

# =============================================================================
# Notification helper  (item 9, 10, etc.)
# Commas and parens break executebuiltin -- sanitise before passing.
# =============================================================================
def notify(header, message, ms=None):
    if ms is None:
        ms = NOTIFICATION_DURATION
    def _s(t, n):
        return t.replace(',', '-').replace('(', '').replace(')', '')[:n]
    try:
        xbmc.executebuiltin(
            'Notification(' + _s(header, 30) + ',' + _s(message, 80)
            + ',' + str(ms) + ')')
    except Exception:
        pass

# =============================================================================
# Progress dialog helper  (item 10)
#
# Usage:
#   pd = progress_open("YouTube", "Fetching results...")
#   ... fetch ...
#   progress_close(pd)
#
# Falls back to busydialog silently if DialogProgress is unavailable.
# =============================================================================
def progress_open(title, msg):
    try:
        dp = xbmcgui.DialogProgress()
        dp.create(title, msg)
        dp.update(0, msg)
        return dp
    except Exception:
        try:
            xbmc.executebuiltin("ActivateWindow(busydialog)")
        except Exception:
            pass
        return None

def progress_update(dp, pct, msg):
    if dp is None:
        return
    try:
        dp.update(pct, msg)
    except Exception:
        pass

def progress_close(dp):
    if dp is None:
        try:
            xbmc.executebuiltin("Dialog.Close(busydialog)")
        except Exception:
            pass
        return
    try:
        dp.close()
    except Exception:
        pass

# =============================================================================
# YouTube Data API v3 helpers  (item 12)
# =============================================================================
YT_API_BASE = "https://www.googleapis.com/youtube/v3/"

def _api_get(endpoint, params):
    key = get_api_key()
    if not key:
        return None
    params['key'] = key
    # Python 2.4 compatible - use list comprehension instead of generator
    param_list = [k + '=' + urllib.quote_plus(str(v)) for k, v in params.items()]
    qs = '&'.join(param_list)
    url = YT_API_BASE + endpoint + '?' + qs
    try:
        f    = urllib.urlopen(url)
        data = f.read()
        f.close()
        if not isinstance(data, str):
            data = data.decode('utf-8', 'ignore')
        return json.loads(data)
    except Exception:
        return None

def api_search(query, limit=None):
    """Returns (titles, ids) or (None, None) if API unavailable."""
    if limit is None:
        limit = SEARCH_RESULT_LIMIT
    data = _api_get('search', {
        'part': 'snippet', 'q': query,
        'type': 'video', 'maxResults': str(limit)
    })
    if not data:
        return None, None
    titles, ids = [], []
    for item in data.get('items', []):
        t = item.get('snippet', {}).get('title', '')
        i = item.get('id', {}).get('videoId', '')
        if t and i:
            titles.append(t)
            ids.append(i)
    if titles:
        return titles, ids
    return None, None

def api_trending(limit=None):
    if limit is None:
        limit = TRENDING_RESULT_LIMIT
    data = _api_get('videos', {
        'part': 'snippet', 'chart': 'mostPopular',
        'maxResults': str(limit), 'regionCode': 'US'
    })
    if not data:
        return None, None
    titles, ids = [], []
    for item in data.get('items', []):
        t = item.get('snippet', {}).get('title', '')
        i = item.get('id', '')
        if t and i:
            titles.append(t)
            ids.append(i)
    if titles:
        return titles, ids
    return None, None

# =============================================================================
# Proxy fetch helpers
# =============================================================================
def proxy_fetch(path):
    """
    Fetch from proxy with a notification popup instead of progress dialog.
    Returns list of decoded lines, or None on error.
    """
    notify("YouTube", "Fetching...", 4000)
    xbmc.sleep(4000)  # Wait for notification to appear
    try:
        f     = urllib.urlopen(PROXY + path)
        lines = f.readlines()
        f.close()
        result = []
        for l in lines:
            if hasattr(l, 'decode'):
                result.append(l.decode('utf-8', 'ignore'))
            else:
                result.append(l)
        return result
    except IOError:
        xbmcgui.Dialog().ok("Connection Error", "Could not reach proxy.", PROXY)
        return None
    except Exception:
        return None

def proxy_fetch_str(path):
    """Return body as stripped string, or None."""
    lines = proxy_fetch(path)
    if lines is None:
        return None
    return ''.join(lines).strip()

def parse_lines(lines):
    clean = [l.strip() for l in lines if l.strip()]
    if clean and clean[0].startswith("Failed"):
        return [], clean[0]
    titles, ids = [], []
    i = 0
    while i + 1 < len(clean):
        titles.append(clean[i])
        ids.append(clean[i + 1])
        i += 2
    return titles, ids

# =============================================================================
# Normalize video id
# =============================================================================
def normalize_vid(vid):
    if not vid:
        return vid
    v = vid.strip()
    if "v=" in v:
        v = v.split("v=")[-1]
        if "&" in v:
            v = v.split("&")[0]
    if "/" in v and not v.startswith("UC") and not v.startswith("@"):
        v = v.rstrip("/").split("/")[-1]
    # Remove any remaining query parameters or fragments
    if "?" in v:
        v = v.split("?")[0]
    if "#" in v:
        v = v.split("#")[0]
    # Ensure video ID is not empty after normalization
    if not v:
        return vid
    return v

# =============================================================================
# Quality picker  (item 3)
# Shows a dialog letting the user choose resolution before playback/download.
# Returns the fmt_key string or None if cancelled.
# =============================================================================
def pick_quality(title="Select Quality"):
    labels = [o[0] for o in QUALITY_OPTS]
    sel    = xbmcgui.Dialog().select(title, labels)
    if sel == -1:
        return None
    return QUALITY_OPTS[sel][1]

def pick_sub(title="Select Subtitles"):
    labels = [o[0] for o in SUB_OPTS]
    sel    = xbmcgui.Dialog().select(title, labels)
    if sel == -1:
        return 'none'
    return SUB_OPTS[sel][1]

def pick_format(title="Select Format", is_audio=0):
    """Pick video or audio format extension for download."""
    if is_audio:
        formats = [
            ("[MP3]  MP3 (Default)", "mp3"),
            ("[M4A]  M4A", "m4a"),
            ("[WAV]  WAV", "wav"),
            ("[FLAC]  FLAC", "flac"),
        ]
    else:
        formats = [
            ("[MP4]  MP4 (Default)", "mp4"),
            ("[MKV]  MKV", "mkv"),
            ("[AVI]  AVI", "avi"),
            ("[WEBM]  WebM", "webm"),
        ]
    labels = [o[0] for o in formats]
    sel = xbmcgui.Dialog().select(title, labels)
    if sel == -1:
        return formats[0][1]
    return formats[sel][1]

def pick_audio_quality(title="Select Audio Quality"):
    """Pick audio quality for download."""
    qualities = [
        ("[Low]  Low Quality", "low"),
        ("[Medium]  Medium Quality", "medium"),
        ("[Best]  Best Quality", "best"),
    ]
    labels = [o[0] for o in qualities]
    sel = xbmcgui.Dialog().select(title, labels)
    if sel == -1:
        return 'best'
    return qualities[sel][1]

# =============================================================================
# VOD Playback  (item 3: quality picker added)
#
# proxy /play/<vid>/<fmt> returns direct CDN URL as plain text.
# player.play(bare_url) -- no ListItem -- avoids plugin re-invocation in XBMC 9.11.
# =============================================================================
def play_v(vid, title, fmt_key=None):
    vid = normalize_vid(vid)
    if not vid:
        xbmcgui.Dialog().ok("Playback Error", "Invalid video ID.")
        return

    # Quality picker
    if fmt_key is None:
        fmt_key = pick_quality("Quality for: " + title[:40])
        if fmt_key is None:
            return   # user cancelled

    playback_method = get_vod_playback_method()

    if playback_method == "pipe":
        # Pipe streaming: stream video data directly through proxy
        notify("YouTube", "Starting pipe stream...", 4000)

        pipe_url = PROXY + "/pipe/" + urllib.quote_plus(vid) + "/" + urllib.quote_plus(fmt_key)

        try:
            player = xbmc.Player()
            player.play(pipe_url)
        except Exception:
            xbmcgui.Dialog().ok("Playback Error", "player.play() failed.")
            return

        waited = 0
        while waited < PLAYBACK_START_TIMEOUT:
            if player.isPlaying():
                break
            xbmc.sleep(1000)
            waited += 1

        if not player.isPlaying():
            xbmcgui.Dialog().ok(
                "Playback Error", "Pipe stream did not start.", "Check proxy.log.")
            return

        notify("Now Playing", title, 4000)
        while player.isPlaying():
            xbmc.sleep(1000)

    elif playback_method == "conversion":
        # Conversion-based playback: download first, then play local file
        notify("YouTube", "Downloading video for playback...", 4000)
        
        # Request download to temp location
        temp_dir = xbmc.translatePath("special://temp/")
        if not os.path.exists(temp_dir):
            try:
                os.makedirs(temp_dir)
            except Exception:
                temp_dir = PROF_DIR
        
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        temp_file = os.path.join(temp_dir, safe_title + ".mp4")
        
        # Remove existing temp file if present
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception:
            pass
        
        try:
            # Use query parameters for temp path to avoid URL parsing issues with backslashes
            url = (PROXY + "/download_to_temp/"
                   + urllib.quote_plus(vid) + "/"
                   + urllib.quote_plus(fmt_key) + "/"
                   + urllib.quote_plus("none")
                   + "?path=" + urllib.quote_plus(temp_file))
            urllib.urlopen(url).read()
            
            # Wait for download to complete (simple polling with size check)
            waited = 0
            last_size = 0
            stable_count = 0
            while waited < CONVERSION_DOWNLOAD_TIMEOUT:  # Wait up to configured timeout
                if os.path.exists(temp_file):
                    current_size = os.path.getsize(temp_file)
                    # Check if file size is stable (download complete)
                    if current_size > 100000 and current_size == last_size:
                        stable_count += 1
                        if stable_count >= 3:  # Size stable for 3 checks
                            break
                    else:
                        stable_count = 0
                    last_size = current_size
                xbmc.sleep(1000)
                waited += 1
            
            if not os.path.exists(temp_file) or os.path.getsize(temp_file) < 100000:
                xbmcgui.Dialog().ok("Playback Error", "Download failed or incomplete.")
                return
            
            notify("YouTube", "Playing downloaded video...")
            player = xbmc.Player()
            player.play(temp_file)
            
            waited = 0
            while waited < PLAYBACK_START_TIMEOUT:
                if player.isPlaying():
                    break
                xbmc.sleep(1000)
                waited += 1
            
            if not player.isPlaying():
                xbmcgui.Dialog().ok("Playback Error", "Could not play downloaded file.")
                return
            
            notify("Now Playing", title)
            while player.isPlaying():
                xbmc.sleep(1000)
            
            # Clean up temp file
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
                
        except IOError:
            xbmcgui.Dialog().ok("Connection Error", "Could not reach proxy.", PROXY)
            return
    else:
        # Direct streaming (current method)
        notify("YouTube", "Resolving stream...")

        direct_url = proxy_fetch_str(
            "/play/" + urllib.quote_plus(vid) + "/" + urllib.quote_plus(fmt_key))

        if direct_url is None:
            return
        if not direct_url or direct_url.startswith("Failed"):
            xbmcgui.Dialog().ok(
                "Playback Error", "Could not resolve stream.", "Check proxy.log.")
            return

        try:
            player = xbmc.Player()
            player.play(direct_url)
        except Exception:
            xbmcgui.Dialog().ok("Playback Error", "player.play() failed.")
            return

        waited = 0
        while waited < PLAYBACK_START_TIMEOUT:
            if player.isPlaying():
                break
            xbmc.sleep(1000)
            waited += 1

        if not player.isPlaying():
            xbmcgui.Dialog().ok(
                "Playback Error", "Stream did not start.", "Try again or check proxy.log.")
            return

        notify("Now Playing", title)
        while player.isPlaying():
            xbmc.sleep(1000)

# =============================================================================
# Live Stream Playback
#
# proxy /live_stream/<vid> streams MPEG-TS bytes.
# XBMC 9.11 / FFmpeg 0.5 plays MPEG-TS natively by 0x47 sync detection.
# =============================================================================
def play_live(vid, title):
    vid = normalize_vid(vid)
    if not vid:
        xbmcgui.Dialog().ok("Playback Error", "Invalid video ID.")
        return

    file_append(HIST_FILE, title, vid, check_dupe=0)

    stream_url = PROXY + "/live_stream/" + urllib.quote_plus(vid)

    try:
        player = xbmc.Player()
        player.play(stream_url)
    except Exception:
        xbmcgui.Dialog().ok("Playback Error", "player.play() failed.")
        return

    # Wait longer for live stream to start (up to configured timeout)
    waited = 0
    while waited < LIVE_STREAM_START_TIMEOUT:
        if player.isPlaying():
            break
        xbmc.sleep(1000)
        waited += 1

    if not player.isPlaying():
        xbmcgui.Dialog().ok(
            "Live Stream Error", "Stream did not start.",
            "Stream may have ended or be unavailable.")
        return

    notify("YouTube Live", "Connecting: " + title)
    notify("Now Live", title)
    while player.isPlaying():
        xbmc.sleep(1000)

# =============================================================================
# Download with quality + subtitle + format + audio quality picker  (item 4, 9)
# =============================================================================
def download_video(v_id, v_t, is_audio_only=0):
    if is_audio_only:
        # Audio-only download
        audio_fmt = pick_format("Audio Format", is_audio=1)
        audio_quality = pick_audio_quality("Audio Quality")
    else:
        # Video download with format selection
        fmt_key = pick_quality("Download Quality: " + v_t[:40])
        if fmt_key is None:
            return
        sub_key = pick_sub("Subtitles for download?")
        video_fmt = pick_format("Video Format", is_audio=0)
        audio_quality = pick_audio_quality("Audio Quality")
    
    try:
        if is_audio_only:
            url = (PROXY + "/download_audio/"
                   + urllib.quote_plus(v_id) + "/"
                   + audio_fmt + "/"
                   + urllib.quote_plus(audio_quality))
        else:
            url = (PROXY + "/download/"
                   + urllib.quote_plus(v_id) + "/"
                   + urllib.quote_plus(fmt_key) + "/"
                   + urllib.quote_plus(sub_key) + "/"
                   + urllib.quote_plus(video_fmt) + "/"
                   + urllib.quote_plus(audio_quality))
        urllib.urlopen(url).read()
        notify("YouTube", "Download started: " + v_t)
        xbmcgui.Dialog().ok("Download", "Download started.", "Check downloaded_videos folder.")
    except IOError:
        xbmcgui.Dialog().ok("Connection Error", "Could not reach proxy.", PROXY)

# =============================================================================
# Comments viewer  (item 8)
# =============================================================================
def view_comments(vid, title):
    notify("YouTube", "Loading comments...", 4000)
    xbmc.sleep(4000)  # Wait for notification to appear
    raw = proxy_fetch_str("/comments/" + urllib.quote_plus(vid))

    if raw is None or not raw.strip() or raw.startswith("Failed"):
        xbmcgui.Dialog().ok("Comments", "Could not load comments.")
        return

    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if not lines:
        xbmcgui.Dialog().ok("Comments", "No comments found.")
        return

    while 1:
        display = []
        for line in lines:
            if '|' in line:
                author, text = line.split('|', 1)
                display.append(author.strip() + ": " + text.strip()[:60])
            else:
                display.append(line[:80])

        sel = xbmcgui.Dialog().select(
            "Comments: " + title[:30], display + ["[Back]"])
        if sel == -1 or sel == len(display):
            return

        # Show full comment text
        if '|' in lines[sel]:
            author, text = lines[sel].split('|', 1)
            xbmcgui.Dialog().ok(author.strip(), text.strip())

# =============================================================================
# Video action menu  (item 13: pseudo-icon prefixes, item 14: loops back)
# =============================================================================
def video_action(v_id, v_t):
    while 1:
        opt = [
            "[>]  Play",
            "[+]  Add to Watch Later",
            "[m]  Add to Music Playlist",
            "[v]  Download to PC",
            "[a]  Download as Audio",
            "[~]  Recommended",
            "[#]  View Comments",
            "[!]  Post Comment",
            "[<]  Back",
        ]
        c = xbmcgui.Dialog().select(v_t, opt)

        if c == 0:
            play_v(v_id, v_t)
            # After playback ends loop back to this action menu

        elif c == 1:
            saved = file_append(WL_FILE, v_t, v_id, check_dupe=1)
            if saved:
                notify("Watch Later", "Saved: " + v_t)
                xbmcgui.Dialog().ok("Watch Later", "Saved.")
            else:
                xbmcgui.Dialog().ok("Watch Later", "Already in Watch Later.")

        elif c == 2:
            saved = file_append(MUSIC_FILE, v_t, v_id, check_dupe=1)
            if saved:
                notify("Music Playlist", "Added: " + v_t)
                xbmcgui.Dialog().ok("Music Playlist", "Added to playlist.")
            else:
                xbmcgui.Dialog().ok("Music Playlist", "Already in playlist.")

        elif c == 3:
            download_video(v_id, v_t, is_audio_only=0)

        elif c == 4:
            download_video(v_id, v_t, is_audio_only=1)

        elif c == 5:
            return 1   # caller opens recommendations

        elif c == 6:
            view_comments(v_id, v_t)

        elif c == 7:
            do_post_comment(v_id, v_t)

        else:   # Back or -1
            return 0

# =============================================================================
# Live action menu  (item 14: loops)
# =============================================================================
def live_action(v_id, v_t):
    while 1:
        opt = [
            "[>]  Watch Live",
            "[+]  Add to Watch Later",
            "[<]  Back",
        ]
        c = xbmcgui.Dialog().select(v_t + " [LIVE]", opt)

        if c == 0:
            play_live(v_id, v_t)

        elif c == 1:
            saved = file_append(WL_FILE, v_t, v_id, check_dupe=1)
            if saved:
                notify("Watch Later", "Saved: " + v_t)
                xbmcgui.Dialog().ok("Watch Later", "Saved.")
            else:
                xbmcgui.Dialog().ok("Watch Later", "Already in Watch Later.")

        else:
            return

# =============================================================================
# Recommended browser  (item 14: already loops)
# =============================================================================
def browse_recommended(v_id, v_t):
    cur_id, cur_t = v_id, v_t
    while 1:
        enc_id = urllib.quote_plus(cur_id)
        enc_t  = urllib.quote_plus(cur_t)
        rec_lines = proxy_fetch("/recommended/" + enc_id + "/" + enc_t)

        if rec_lines is None:
            return

        titles, ids = parse_lines(rec_lines)
        if not titles:
            pool = [(t, i) for t, i in SEED_VIDEOS if i != cur_id]
            random.shuffle(pool)
            titles = [t for t, _ in pool[:10]]
            ids    = [i for _, i in pool[:10]]

        if not titles:
            xbmcgui.Dialog().ok("Recommended", "No recommendations found.")
            return

        sel = xbmcgui.Dialog().select("Recommended: " + cur_t, titles + ["[<] Back"])
        if sel == -1 or sel == len(titles):
            return

        r_id = normalize_vid(ids[sel])
        r_t  = titles[sel]
        if not r_id:
            continue

        opt = ["[>]  Play", "[+]  Watch Later", "[>>] Browse Recommended", "[<]  Back"]
        r_c = xbmcgui.Dialog().select(r_t, opt)

        if r_c == 0:
            play_v(r_id, r_t)
        elif r_c == 1:
            saved = file_append(WL_FILE, r_t, r_id, check_dupe=1)
            if saved:
                notify("Watch Later", "Saved: " + r_t)
                xbmcgui.Dialog().ok("Watch Later", "Saved.")
            else:
                xbmcgui.Dialog().ok("Watch Later", "Already in Watch Later.")
        elif r_c == 2:
            cur_id, cur_t = r_id, r_t
        else:
            return

# =============================================================================
# Generic listing browser -- VOD  (item 12: API with proxy fallback)
# (item 14: loops back to listing after action)
# =============================================================================
def list_and_select(proxy_path, menu_title="YouTube", api_titles=None, api_ids=None):
    while 1:
        if api_titles is not None:
            titles = api_titles
            ids    = api_ids
        else:
            lines = proxy_fetch(proxy_path)
            if lines is None:
                return
            titles, ids = parse_lines(lines)
            if not titles and ids:
                xbmcgui.Dialog().ok("Error", str(ids))
                return
            if not titles:
                xbmcgui.Dialog().ok("YouTube", "No results found.")
                return

        sel = xbmcgui.Dialog().select(menu_title, titles + ["[<] Back"])
        if sel == -1 or sel == len(titles):
            return

        v_id = normalize_vid(ids[sel])
        v_t  = titles[sel]
        if not v_id:
            continue

        if v_id.startswith("UC") or v_id.startswith("@"):
            list_and_select("/channel/" + urllib.quote_plus(v_id), "Channel")
            continue

        go_rec = video_action(v_id, v_t)
        if go_rec:
            browse_recommended(v_id, v_t)
        # Loop: return to the same listing

# =============================================================================
# Generic listing browser -- Live
# (item 14: loops back)
# =============================================================================
def list_and_select_live(proxy_path, menu_title="Live Streams"):
    while 1:
        lines = proxy_fetch(proxy_path)
        if lines is None:
            return

        titles, ids = parse_lines(lines)
        if not titles and ids:
            xbmcgui.Dialog().ok("Error", str(ids))
            return
        if not titles:
            xbmcgui.Dialog().ok("Live Streams", "No live streams found.")
            return

        display = [t + "  [LIVE]" for t in titles]
        sel = xbmcgui.Dialog().select(menu_title, display + ["[<] Back"])
        if sel == -1 or sel == len(titles):
            return

        v_id = normalize_vid(ids[sel])
        v_t  = titles[sel]
        if not v_id:
            continue

        live_action(v_id, v_t)
        # Loop back to live listing

# =============================================================================
# List manager  (item 14: loops, item 13: icon prefixes)
# =============================================================================
def manage_list(path, name, allow_clear=0, is_watch_later=0):
    while 1:
        titles, ids = read_list(path)
        if not titles:
            xbmcgui.Dialog().ok(name, "List is empty.")
            return

        titles_r = list(reversed(titles))
        ids_r    = list(reversed(ids))

        display = list(titles_r)
        if allow_clear:
            display.insert(0, "[x]  Remove Duplicates")
            display.insert(0, "[x]  Delete Playlist")
        display.append("[<]  Back")

        sel = xbmcgui.Dialog().select(name, display)
        if sel == -1 or sel == len(display) - 1:
            return

        if allow_clear and sel == 0:
            if xbmcgui.Dialog().yesno(name, "Delete entire playlist?"):
                if os.path.exists(path):
                    os.remove(path)
                xbmcgui.Dialog().ok(name, "Playlist deleted.")
            continue

        if allow_clear and sel == 1:
            removed = dedup_list(path)
            xbmcgui.Dialog().ok(name, str(removed) + " duplicate(s) removed.")
            continue

        if allow_clear:
            real = sel - 2
        else:
            real = sel - 0
        if real < 0 or real >= len(titles_r):
            continue

        # Build action menu based on list type
        if is_watch_later:
            # Watch Later: Play, Download, Download as Audio, Recommended, Delete, Back
            opt = [
                "[>]  Play",
                "[v]  Download to PC",
                "[a]  Download as Audio",
                "[~]  Recommended",
                "[x]  Delete",
                "[<]  Back"
            ]
        else:
            # History: Play, Add to Watch Later, Download, Download as Audio, Recommended, Delete, Back
            opt = [
                "[>]  Play",
                "[+]  Add to Watch Later",
                "[v]  Download to PC",
                "[a]  Download as Audio",
                "[~]  Recommended",
                "[x]  Delete",
                "[<]  Back"
            ]

        choice = xbmcgui.Dialog().select(titles_r[real], opt)

        if choice == 0:  # Play
            play_v(normalize_vid(ids_r[real]), titles_r[real])
        elif choice == 1:  # Add to Watch Later (History only) or Download (Watch Later)
            if is_watch_later:
                download_video(normalize_vid(ids_r[real]), titles_r[real])
            else:
                saved = file_append(WL_FILE, titles_r[real], ids_r[real], check_dupe=1)
                if saved:
                    notify("Watch Later", "Saved: " + titles_r[real])
                    xbmcgui.Dialog().ok("Watch Later", "Saved.")
                else:
                    xbmcgui.Dialog().ok("Watch Later", "Already in Watch Later.")
        elif choice == 2:  # Download (History) or Download as Audio (Watch Later)
            if is_watch_later:
                download_video(normalize_vid(ids_r[real]), titles_r[real], is_audio_only=1)
            else:
                download_video(normalize_vid(ids_r[real]), titles_r[real])
        elif choice == 3:  # Download as Audio (History) or Recommended (Watch Later)
            if is_watch_later:
                # Recommended
                browse_recommended(normalize_vid(ids_r[real]), titles_r[real])
            else:
                download_video(normalize_vid(ids_r[real]), titles_r[real], is_audio_only=1)
        elif choice == 4:  # Recommended (History) or Delete (Watch Later)
            if is_watch_later:
                # Delete
                all_t, all_i = read_list(path)
                vid_del = ids_r[real]
                new_t = [t for t, i in zip(all_t, all_i) if i != vid_del]
                new_i = [i for i in all_i if i != vid_del]
                write_list(path, new_t, new_i)
                notify(name, "Removed.")
            else:
                # Recommended
                browse_recommended(normalize_vid(ids_r[real]), titles_r[real])
        elif choice == 5:  # Delete (History) or Back (Watch Later)
            if is_watch_later:
                # Back
                pass
            else:
                # Delete
                all_t, all_i = read_list(path)
                vid_del = ids_r[real]
                new_t = [t for t, i in zip(all_t, all_i) if i != vid_del]
                new_i = [i for i in all_i if i != vid_del]
                write_list(path, new_t, new_i)
                notify(name, "Removed.")
        # Loop back to list

# =============================================================================
# Channel favourites  (item 7)
# =============================================================================
def do_channel_favourites():
    while 1:
        names, ids = read_list(CH_FILE)
        opts = ["[+]  Add Channel"]
        if names:
            opts.append("[x]  Remove a Channel")
        for n in names:
            opts.append("[CH] " + n)
        opts.append("[<]  Back")

        sel = xbmcgui.Dialog().select("Channel Favourites", opts)
        if sel == -1 or sel == len(opts) - 1:
            return

        if sel == 0:
            kb = xbmc.Keyboard("", "Enter @Handle or Channel ID")
            kb.doModal()
            if not kb.isConfirmed():
                continue
            ch = kb.getText().strip()
            if not ch:
                continue
            kb2 = xbmc.Keyboard(ch, "Channel display name")
            kb2.doModal()
            if kb2.isConfirmed():
                label = kb2.getText().strip()
            else:
                label = ch
            file_append(CH_FILE, label, ch)
            notify("Favourites", "Added: " + label)
            continue

        if sel == 1 and names:
            rem_opts = list(names) + ["[<] Back"]
            r = xbmcgui.Dialog().select("Remove Channel", rem_opts)
            if r == -1 or r == len(names):
                continue
            vid_del = ids[r]
            new_n = [n for n, i in zip(names, ids) if i != vid_del]
            new_i = [i for i in ids if i != vid_del]
            write_list(CH_FILE, new_n, new_i)
            notify("Favourites", "Removed.")
            continue

        # Browse a favourite channel
        if names:
            offset = 2
        else:
            offset = 1
        real   = sel - offset
        if real < 0 or real >= len(names):
            continue
        cid = ids[real]
        list_and_select(
            "/channel/" + urllib.quote_plus(cid), "Channel: " + names[real])

# =============================================================================
# Browse Channel  (item 7: favourites built-in)
# =============================================================================
def do_browse_channel():
    while 1:
        opt = [
            "[CH] Favourites",
            "[CH] Browse by @Handle or ID",
            "[<]  Back",
        ]
        sel = xbmcgui.Dialog().select("Browse Channel", opt)
        if sel == -1 or sel == 2:
            return
        if sel == 0:
            do_channel_favourites()
        elif sel == 1:
            kb = xbmc.Keyboard("", "Enter @Handle or Channel ID")
            kb.doModal()
            if kb.isConfirmed():
                ch = kb.getText().strip()
                if ch:
                    list_and_select(
                        "/channel/" + urllib.quote_plus(ch), "Channel")

# =============================================================================
# Search  (item 11: live search toggle, item 14: loops)
# =============================================================================
def do_search():
    while 1:
        past = read_search_hist()
        menu    = ["[?]  New Search", "[~]  Search Live Streams"]
        offsets = [None, "__live__"]

        if past:
            menu.append("[x]  Clear All History")
            offsets.append("__clear__")

        for q in past:
            menu.append("[>]  " + q)
            offsets.append(q)

        menu.append("[<]  Back")
        offsets.append("__back__")

        sel = xbmcgui.Dialog().select("Search YouTube", menu)
        if sel == -1:
            return

        action = offsets[sel]

        if action == "__back__":
            return

        if action == "__clear__":
            if xbmcgui.Dialog().yesno("Search History", "Clear all search history?"):
                clear_search_hist()
                notify("Search History", "History cleared.")
            continue

        if action is None or action == "__live__":
            is_live = (action == "__live__")
            if is_live:
                label = "Search Live Streams"
            else:
                label = "Search YouTube"
            kb = xbmc.Keyboard("", label)
            kb.doModal()
            if not kb.isConfirmed():
                continue
            q = kb.getText().strip()
            if not q:
                continue
            if not is_live:
                push_search_hist(q)
                # Try API first, fall back to proxy
                api_t, api_i = api_search(q)
                if api_t:
                    list_and_select('', "Search: " + q,
                                    api_titles=api_t, api_ids=api_i)
                else:
                    list_and_select(
                        "/search/" + urllib.quote_plus(q), "Search: " + q)
            else:
                list_and_select_live(
                    "/live_search/" + urllib.quote_plus(q),
                    "Live: " + q)
            continue

        # Past query
        q   = action
        opt = ["[>]  Search Again", "[x]  Delete from History", "[<]  Back"]
        c   = xbmcgui.Dialog().select(q, opt)
        if c == 0:
            push_search_hist(q)
            api_t, api_i = api_search(q)
            if api_t:
                list_and_select('', "Search: " + q,
                                api_titles=api_t, api_ids=api_i)
            else:
                list_and_select(
                    "/search/" + urllib.quote_plus(q), "Search: " + q)
        elif c == 1:
            queries = read_search_hist()
            write_search_hist([x for x in queries if x != q])
            notify("Search History", "Removed: " + q)
        # Loop back to search menu

# =============================================================================
# Trending  (item 14: loops)
# =============================================================================
def do_trending():
    while 1:
        cats = [
            "[^]  Trending (General)",
            "[^]  Trending Music",
            "[^]  Trending Gaming",
            "[<]  Back",
        ]
        sel = xbmcgui.Dialog().select("Trending", cats)
        if sel == -1 or sel == 3:
            return
        if sel == 0:
            api_t, api_i = api_trending()
            if api_t:
                list_and_select('', "Trending", api_titles=api_t, api_ids=api_i)
            else:
                list_and_select("/trending", "Trending")
        elif sel == 1:
            list_and_select("/trending/music", "Trending Music")
        elif sel == 2:
            list_and_select("/trending/gaming", "Trending Gaming")

# =============================================================================
# Live Streams  (item 14: loops)
# =============================================================================
def do_live():
    while 1:
        cats = [
            "[~]  All Live",
            "[~]  Live Music",
            "[~]  Live Gaming",
            "[~]  Live News",
            "[<]  Back",
        ]
        sel = xbmcgui.Dialog().select("Live Streams", cats)
        if sel == -1 or sel == 4:
            return
        if sel == 0:
            list_and_select_live("/live", "Live Streams")
        elif sel == 1:
            list_and_select_live("/live/music", "Live Music")
        elif sel == 2:
            list_and_select_live("/live/gaming", "Live Gaming")
        elif sel == 3:
            list_and_select_live("/live/news", "Live News")

# =============================================================================
# Recommendations  (item 14: loops)
# =============================================================================
def do_recommendations():
    while 1:
        seed_t, seed_id = random.choice(SEED_VIDEOS)
        browse_recommended(seed_id, seed_t)
        opt = ["[>]  Try Another", "[<]  Back"]
        c   = xbmcgui.Dialog().select("Recommendations", opt)
        if c == -1 or c == 1:
            return

# =============================================================================
# API Settings  (item 12)
# =============================================================================
def do_api_settings():
    """Allow user to set or clear YouTube Data API key and account key."""
    cfg = read_config()
    current = cfg.get('api_key', '')
    account_key = cfg.get('api_account_key', '')
    custom_proxy = cfg.get('custom_proxy_url', CUSTOM_PROXY_URL)
    cookies_file = cfg.get('cookies_file', COOKIES_FILE)
    
    # Build status strings
    if current and len(current) > 10:
        api_status = current[:10] + '...'
    else:
        if current:
            api_status = current
        else:
            api_status = '(not set)'
    
    if account_key and len(account_key) > 10:
        account_status = account_key[:10] + '...'
    else:
        if account_key:
            account_status = account_key
        else:
            account_status = '(not set)'
    
    if custom_proxy:
        proxy_status = custom_proxy
    else:
        proxy_status = '(not set)'
    
    if cookies_file and os.path.exists(cookies_file):
        cookies_status = '(exists)'
    else:
        cookies_status = '(not set)'
    
    opt = [
        "[1]  Set Data API Key [" + api_status + "]",
        "[2]  Set Account Key (OAuth) [" + account_status + "]",
        "[3]  Set Custom Proxy URL [" + proxy_status + "]",
        "[4]  Clear Data API Key",
        "[5]  Clear Account Key",
        "[6]  Clear Custom Proxy URL",
        "[<]  Back",
    ]
    sel = xbmcgui.Dialog().select("API Settings", opt)
    
    if sel == 0:
        kb = xbmc.Keyboard()
        kb.setHeading("Enter YouTube Data API v3 key")
        kb.doModal()
        if kb.isConfirmed():
            cfg['api_key'] = kb.getText()
            write_config(cfg)
            xbmcgui.Dialog().ok("API Settings", "API key saved.")
    elif sel == 1:
        kb = xbmc.Keyboard()
        kb.setHeading("Enter YouTube Account Key (OAuth)")
        kb.doModal()
        if kb.isConfirmed():
            cfg['api_account_key'] = kb.getText()
            write_config(cfg)
            xbmcgui.Dialog().ok("API Settings", "Account key saved.")
    elif sel == 2:
        kb = xbmc.Keyboard()
        kb.setHeading("Enter Custom Proxy URL")
        kb.setPlaceholder("e.g., https://yt.lemnoslife.com")
        kb.doModal()
        if kb.isConfirmed():
            cfg['custom_proxy_url'] = kb.getText()
            write_config(cfg)
            xbmcgui.Dialog().ok("API Settings", "Custom proxy URL saved.")
    elif sel == 3:
        if xbmcgui.Dialog().yesno("API Settings", "Clear Data API key?"):
            cfg['api_key'] = ''
            write_config(cfg)
            xbmcgui.Dialog().ok("API Settings", "API key cleared.")
    elif sel == 4:
        if xbmcgui.Dialog().yesno("API Settings", "Clear Account key?"):
            cfg['api_account_key'] = ''
            write_config(cfg)
            xbmcgui.Dialog().ok("API Settings", "Account key cleared.")
    elif sel == 5:
        if xbmcgui.Dialog().yesno("API Settings", "Clear Custom Proxy URL?"):
            cfg['custom_proxy_url'] = ''
            write_config(cfg)
            xbmcgui.Dialog().ok("API Settings", "Custom proxy URL cleared.")

def get_api_key():
    """Get API key from config or global variable."""
    cfg = read_config()
    return cfg.get('api_key', YT_API_KEY)

def get_account_key():
    """Get account key from config or global variable."""
    cfg = read_config()
    return cfg.get('api_account_key', YT_API_ACCOUNT_KEY)

def fetch_notifications():
    """Fetch YouTube notifications using API (max 20)."""
    api_key = get_account_key()
    if not api_key:
        xbmcgui.Dialog().ok("Notifications", "Account key not set.", "Please set it in API Settings.")
        return []
    
    try:
        # YouTube Data API v3 endpoint for notifications
        url = "https://www.googleapis.com/youtube/v3/notifications"
        params = {
            'part': 'snippet',
            'maxResults': 20,
            'key': api_key
        }
        # Build URL with params
        param_list = [k + '=' + urllib.quote_plus(str(v)) for k, v in params.items()]
        query_string = '&'.join(param_list)
        full_url = url + '?' + query_string
        
        response = urllib.urlopen(full_url).read()
        if hasattr(response, 'decode'):
            response = response.decode('utf-8', 'ignore')
        
        data = json.loads(response)
        notifications = []
        
        for item in data.get('items', []):
            snippet = item.get('snippet', {})
            title = snippet.get('title', 'Unknown')
            channel = snippet.get('channelTitle', 'Unknown')
            video_id = snippet.get('resourceId', {}).get('videoId', '')
            notifications.append((title, channel, video_id))
        
        return notifications[:20]
    except Exception, e:
        xbmcgui.Dialog().ok("Notifications Error", "Failed to fetch notifications.", str(e))
        return []

def do_notifications():
    """Display YouTube notifications."""
    notify("YouTube", "Fetching notifications...", 4000)
    xbmc.sleep(4000)
    
    notifications = fetch_notifications()
    if not notifications:
        xbmcgui.Dialog().ok("Notifications", "No notifications found.")
        return
    
    display = []
    for title, channel, vid in notifications:
        display.append(channel + ": " + title[:50])
    
    sel = xbmcgui.Dialog().select("Notifications", display + ["[<]  Back"])
    if sel == -1 or sel == len(display):
        return
    
    # Play selected video
    title, channel, vid = notifications[sel]
    play_v(vid, title)

def post_comment(vid, text):
    """Post a comment to a YouTube video using API."""
    api_key = get_account_key()
    if not api_key:
        xbmcgui.Dialog().ok("Comment Error", "Account key not set.", "Please set it in API Settings.")
        return False
    
    try:
        # YouTube Data API v3 endpoint for posting comments
        url = "https://www.googleapis.com/youtube/v3/commentThreads"
        params = {
            'part': 'snippet',
            'key': api_key
        }
        
        data = {
            'snippet': {
                'topLevelComment': {
                    'snippet': {
                        'textOriginal': text
                    }
                },
                'videoId': vid
            }
        }
        
        param_list = [k + '=' + urllib.quote_plus(str(v)) for k, v in params.items()]
        query_string = '&'.join(param_list)
        full_url = url + '?' + query_string
        
        # POST request with JSON data
        json_data = json.dumps(data)
        if hasattr(json_data, 'encode'):
            json_data = json_data.encode('utf-8')
        
        req = urllib.Request(full_url, data=json_data, headers={'Content-Type': 'application/json'})
        response = urllib.urlopen(req).read()
        
        if hasattr(response, 'decode'):
            response = response.decode('utf-8', 'ignore')
        
        result = json.loads(response)
        if 'error' in result:
            xbmcgui.Dialog().ok("Comment Error", "Failed to post comment.", result['error'].get('message', 'Unknown error'))
            return False
        
        return True
    except Exception, e:
        xbmcgui.Dialog().ok("Comment Error", "Failed to post comment.", str(e))
        return False

def do_post_comment(vid, title):
    """Prompt user to post a comment to a video."""
    kb = xbmc.Keyboard()
    kb.setHeading("Enter your comment for: " + title[:40])
    kb.doModal()
    if not kb.isConfirmed():
        return
    
    text = kb.getText()
    if not text.strip():
        xbmcgui.Dialog().ok("Comment Error", "Comment cannot be empty.")
        return
    
    notify("YouTube", "Posting comment...", 4000)
    xbmc.sleep(4000)
    
    if post_comment(vid, text):
        xbmcgui.Dialog().ok("Comment", "Comment posted successfully.")
    else:
        xbmcgui.Dialog().ok("Comment", "Failed to post comment.")

# =============================================================================
# Main menu  (item 9: welcome notification, item 13: icon prefixes)
# =============================================================================
def main():
    # Welcome notification (item 9)
    try:
        username = xbmc.getInfoLabel("System.ProfileName")
        if not username:
            username = xbmc.getInfoLabel("System.FriendlyName")
    except Exception:
        username = "User"
    if not username:
        username = "User"
    notify("Welcome! " + username, "YouTube is starting..", 4000)
    xbmc.sleep(4000)
    
    while 1:
        wl_count   = count_list(WL_FILE)
        hist_count = count_list(HIST_FILE)
        ch_count   = count_list(CH_FILE)
        music_count = count_list(MUSIC_FILE)

        wl_label   = "[+]  Watch Later"
        hist_label = "[H]  History Manager"
        ch_label   = "[CH] Browse Channel"
        music_label = "[M]  Music Playlist"
        if wl_count > 0:
            wl_label = "[+]  Watch Later (" + str(wl_count) + ")"
        if hist_count > 0:
            hist_label = "[H]  History (" + str(hist_count) + ")"
        if ch_count > 0:
            ch_label = "[CH] Browse Channel (" + str(ch_count) + " favs)"
        if music_count > 0:
            music_label = "[M]  Music Playlist (" + str(music_count) + ")"

        m = [
            "[?]  Search",
            ch_label,
            "[^]  Trending",
            "[#]  Music Charts",
            "[>>] Recommendations",
            "[~]  Live Streams",
            wl_label,
            hist_label,
            music_label,
            "[N]  Notifications",
            "[K]  API Settings",
            "[X]  Exit",
        ]
        s = xbmcgui.Dialog().select("YouTube(TM) Simplified Media.", m)

        if s == 0:
            do_search()
        elif s == 1:
            do_browse_channel()
        elif s == 2:
            do_trending()
        elif s == 3:
            list_and_select("/music_charts", "Music Charts")
        elif s == 4:
            do_recommendations()
        elif s == 5:
            do_live()
        elif s == 6:
            manage_list(WL_FILE, "Watch Later", allow_clear=1, is_watch_later=1)
        elif s == 7:
            manage_list(HIST_FILE, "History", allow_clear=1, is_watch_later=0)
        elif s == 8:
            manage_list(MUSIC_FILE, "Music Playlist", allow_clear=1, is_watch_later=0)
        elif s == 9:
            do_notifications()
        elif s == 10:
            do_api_settings()
        elif s == 11 or s == -1:
            break        

if __name__ == "__main__":
    main()
