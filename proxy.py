# proxy.py  -  YouTube proxy for XBMC 9.11  (Python 2.4 / 3.x compatible)
#
# Endpoints
# ---------
#  /play/<vid>/<fmt>          resolve VOD CDN URL (returns plain-text URL)
#  /live_stream/<vid>         stream live MPEG-TS to XBMC
#  /search/<q>                search videos
#  /live_search/<q>           search live streams only
#  /trending[/music|/gaming]  trending videos
#  /music_charts              music chart videos
#  /recommended/<vid>/<title> recommendations
#  /live[/music|/gaming|/news]live stream listings
#  /channel/<id>              channel video listing
#  /comments/<vid>            top comments
#  /download/<vid>/<fmt>/<sub>download video (fire-and-forget)
#  /formats/<vid>             list available formats (title|fmt_key pairs)

import os
import sys
import subprocess
import time
import threading
import json

PY3 = sys.version_info[0] >= 3

if PY3:
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from socketserver import ThreadingMixIn
    from urllib.parse import unquote_plus, quote_plus
    import urllib.request as _urllib
else:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    from SocketServer import ThreadingMixIn
    from urllib import unquote_plus, quote_plus
    import urllib as _urllib

# =============================================================================
# CONFIGURATION
# =============================================================================
YT_DLP        = None    # e.g. r'C:\tools\yt-dlp.exe'  -- None = auto-detect
RESULT_LIMIT  = 10
COMMENT_LIMIT = 20
PORT          = 8080
LIVE_CHUNK    = 188 * 512   # ~96KB aligned to MPEG-TS packet boundary (188 bytes) - increased for better buffering

# Timeout settings (in seconds)
STREAM_PREBUFFER_TIMEOUT = 15
DOWNLOAD_TIMEOUT = 120
SOCKET_TIMEOUT = 15

# Custom proxy settings (e.g., yt2009, Invidious, etc.)
CUSTOM_PROXY_URL = None  # e.g., "https://yt.lemnoslife.com"

# Cookies file path for authentication
COOKIES_FILE = None  # e.g., r'C:\path\to\cookies.txt'

# Downloaded audio directory
DOWNLOADED_AUDIOS_DIR = None  # Will be set from default.py if needed

# VOD Playback Method (read from default.py config)
VOD_PLAYBACK_METHOD = "conversion"  # default, will be read from config if available

# YT-DLP-EJS settings for external JavaScript runtime
# Set to None to use default (deno), or specify path to your preferred JS runtime
YT_DLP_EJS_RUNTIME = None  # e.g., r'C:\tools\node.exe' or None for deno
# =============================================================================

HERE     = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(HERE, 'proxy.log')

# Module-level — set by startup before server starts
YTDLP_BIN = None

# ---------------------------------------------------------------------------
# Format map  (key -> yt-dlp format string)
# ---------------------------------------------------------------------------
FORMAT_MAP = {
    '144p': ('bestvideo[height<=144][ext=mp4]+bestaudio[ext=m4a]'
             '/best[height<=144][ext=mp4]/best[height<=144]/best[ext=mp4]/best'),
    '240p': ('bestvideo[height<=240][ext=mp4]+bestaudio[ext=m4a]'
             '/best[height<=240][ext=mp4]/best[height<=240]/best[ext=mp4]/best'),
    '360p': ('bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]'
             '/best[height<=360][ext=mp4]/best[height<=360]/best[ext=mp4]/best'),
    '480p': ('bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]'
             '/best[height<=480][ext=mp4]/best[height<=480]/best[ext=mp4]/best'),
    '720p': ('bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]'
             '/best[height<=720][ext=mp4]/best[height<=720]/best[ext=mp4]/best'),
    'best_mp4': 'best[ext=mp4]/best',
    'best':     'best',
}
# Format displayed in the menu (ordered)
FORMAT_LABELS = ['144p', '240p', '360p', '480p', '720p', 'best_mp4', 'best']

# ---------------------------------------------------------------------------
# Subtitle options
# ---------------------------------------------------------------------------
SUB_MAP = {
    'none': [],
    'en':   ['--write-subs', '--sub-langs', 'en', '--convert-subs', 'srt'],
    'auto': ['--write-auto-subs', '--sub-langs', 'en', '--convert-subs', 'srt'],
}

# =============================================================================
# Logging
# =============================================================================
def log(msg):
    line = time.strftime('[%H:%M:%S] ') + str(msg)
    try:
        f = open(LOG_FILE, 'a')
        f.write(line + '\n')
        f.close()
    except Exception:
        pass
    try:
        sys.stdout.write(line + '\n')
        sys.stdout.flush()
    except Exception:
        pass

def _print(msg):
    sys.stdout.write(str(msg) + '\n')
    sys.stdout.flush()

def _input(prompt):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    return sys.stdin.readline().strip()

# =============================================================================
# yt-dlp auto-detect
# =============================================================================
def find_ytdlp():
    if YT_DLP and os.path.isfile(YT_DLP):
        return YT_DLP
    candidates = [
        os.path.join(HERE, 'yt-dlp.exe'),
        os.path.join(HERE, 'yt-dlp', 'yt-dlp.exe'),
        os.path.join(HERE, 'yt-dlp'),
        r'C:\yt-dlp\yt-dlp.exe',
        r'C:\tools\yt-dlp.exe',
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    for name in ('yt-dlp', 'yt-dlp.exe'):
        for d in os.environ.get('PATH', '').split(os.pathsep):
            full = os.path.join(d, name)
            if os.path.isfile(full):
                return full
    return None

# =============================================================================
# yt-dlp download when missing
# =============================================================================
YTDLP_DL_URL = (
    'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe'
)

def download_ytdlp():
    dest = os.path.join(HERE, 'yt-dlp.exe')
    _print('Downloading yt-dlp.exe from GitHub...')
    try:
        if PY3:
            req  = _urllib.Request(YTDLP_DL_URL, headers={'User-Agent': 'Mozilla/5.0'})
            resp = _urllib.urlopen(req, timeout=120)
            data = resp.read()
        else:
            opener = _urllib.FancyURLopener()
            opener.addheader('User-Agent', 'Mozilla/5.0')
            resp = opener.open(YTDLP_DL_URL)
            data = resp.read()
        f = open(dest, 'wb')
        f.write(data)
        f.close()
        if sys.platform != 'win32':
            try:
                import stat
                os.chmod(dest, os.stat(dest).st_mode | stat.S_IEXEC | stat.S_IXGRP)
            except Exception:
                pass
        _print('Downloaded: ' + dest)
        log('yt-dlp downloaded: ' + dest)
        return dest
    except Exception:
        e = sys.exc_info()[1]
        _print('Download failed: ' + repr(e))
        log('yt-dlp download failed: ' + repr(e))
        return None

# =============================================================================
# Auto-update  (background thread — server starts immediately)
#
# Runs yt-dlp -U, logs result, then prints the 'Proxy active' banner
# so users see it only AFTER the update attempt completes. (item 1)
# =============================================================================
_update_done = threading.Event()

def _update_worker(bin_path):
    try:
        log('Update check: yt-dlp -U ...')
        p = subprocess.Popen(
            [bin_path, '-U'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        out, _ = p.communicate()
        result = to_str(out).strip()
        if result:
            log('Update result: ' + result[:200])
        else:
            log('Update result: (no output)')
    except Exception:
        e = sys.exc_info()[1]
        log('Update check failed: ' + repr(e))
    finally:
        _update_done.set()
        # Print the 'server active' banner now that update check is done
        _print('')
        _print('=' * 100)
        _print('  The Server is Activated Successfully! Now, Go back to XBMC.')
        _print('  INFORMATIONS:')
        _print('    Proxy active on port ' + str(PORT))
        _print('    The Method: ' + VOD_PLAYBACK_METHOD.upper())
        _print('=' * 100)

def start_update_check(bin_path):
    t = threading.Thread(target=_update_worker, args=(bin_path,))
    t.daemon = True
    t.start()

# =============================================================================
# Helpers
# =============================================================================
def to_str(b):
    if b is None:
        return ''
    if isinstance(b, bytes):
        return b.decode('utf-8', 'ignore')
    return str(b)

def to_bytes(s):
    if isinstance(s, bytes):
        return s
    if PY3:
        return s.encode('utf-8')
    try:
        if isinstance(s, unicode):
            return s.encode('utf-8')
    except NameError:
        pass
    return s

def run(cmd):
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        return to_str(out), to_str(err)
    except Exception:
        e = sys.exc_info()[1]
        log('run() exception: ' + repr(e))
        return '', repr(e)

# =============================================================================
# yt-dlp base flags
# No --recode-video, no -x, no conversion flags — fetch real data only. (item 6)
# =============================================================================
BASE_FLAGS = [
    '--no-check-certificate',
    '--geo-bypass',
    '--no-warnings',
]

# Add cookies file if specified
if COOKIES_FILE and os.path.isfile(COOKIES_FILE):
    BASE_FLAGS.extend(['--cookies', COOKIES_FILE])

# Add custom proxy if specified (with validation)
if CUSTOM_PROXY_URL:
    # Validate proxy URL format
    if CUSTOM_PROXY_URL.startswith('http://') or CUSTOM_PROXY_URL.startswith('https://') or CUSTOM_PROXY_URL.startswith('socks'):
        BASE_FLAGS.extend(['--proxy', CUSTOM_PROXY_URL])
        log('Custom proxy enabled: ' + CUSTOM_PROXY_URL)
    else:
        log('WARNING: Invalid custom proxy URL format: ' + CUSTOM_PROXY_URL)
        log('Proxy URL must start with http://, https://, or socks')

BASE_FLAGS.extend(['--socket-timeout', str(SOCKET_TIMEOUT),])

# =============================================================================
# Listing helpers
# =============================================================================
def ytdlp_search(query, limit):
    if not YTDLP_BIN:
        return ''
    cmd = [YTDLP_BIN] + BASE_FLAGS + [
        '--flat-playlist',
        '--playlist-end', str(limit),
        '--print', '%(title)s',
        '--print', '%(id)s',
        'ytsearch' + str(limit) + ':' + query,
    ]
    log('search: ' + query)
    out, err = run(cmd)
    if err.strip():
        log('search stderr: ' + err.strip()[:200])
    return out

def ytdlp_list(url, limit):
    if not YTDLP_BIN:
        return ''
    cmd = [YTDLP_BIN] + BASE_FLAGS + [
        '--flat-playlist',
        '--playlist-end', str(limit),
        '--print', '%(title)s',
        '--print', '%(id)s',
        url,
    ]
    log('list: ' + url[:80])
    out, err = run(cmd)
    if err.strip():
        log('list stderr: ' + err.strip()[:200])
    return out

def parse_listing(raw, exclude_id=None):
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    out   = []
    i     = 0
    while i + 1 < len(lines):
        title = lines[i]
        vid   = lines[i + 1]
        if vid and vid != exclude_id:
            out.append(title)
            out.append(vid)
        i += 2
    return '\n'.join(out[:RESULT_LIMIT * 2])

def live_search_url(query):
    # sp=EgJAAQ%3D%3D = YouTube LIVE filter
    return ('https://www.youtube.com/results?search_query='
            + quote_plus(query) + '&sp=EgJAAQ%3D%3D')

# =============================================================================
# Threaded server  (item 5: live streams don't block listing requests)
# =============================================================================
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

# =============================================================================
# HTTP handler
# =============================================================================
class Proxy(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass

    def send_text(self, body, code=200):
        data = to_bytes(body)
        self.send_response(code)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Connection', 'close')
        self.end_headers()
        try:
            self.wfile.write(data)
            self.wfile.flush()
        except Exception:
            pass

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', '0')
        self.send_header('Connection', 'close')
        self.end_headers()

    def do_GET(self):
        path = self.path or '/'
        log('GET ' + path)

        if not YTDLP_BIN:
            self.send_text('Failed\nyt-dlp not found.', 500)
            return

        try:
            # ================================================================
            # FORMATS  /formats/<vid>
            # Returns pipe-separated label|key pairs, one per line.
            # default.py uses this to build the quality picker.
            # ================================================================
            if path.startswith('/formats/'):
                vid = unquote_plus(path[9:]).strip()
                lines_out = []
                for key in FORMAT_LABELS:
                    lines_out.append(key)
                self.send_text('\n'.join(lines_out))
                return

            # ================================================================
            # PIPE  /pipe/<vid>/<fmt_key>
            #
            # Streams video data directly through proxy without CDN resolution.
            # Uses yt-dlp to stream to stdout, which proxy forwards to XBMC.
            # Similar to live streaming but for VOD content.
            #
            # fmt_key: 144p | 240p | 360p | 480p | 720p | best_mp4 | best
            # Defaults to 360p if fmt_key is missing or unrecognised.
            # ================================================================
            elif path.startswith('/pipe/'):
                rest    = path[6:]
                slash   = rest.find('/')
                if slash == -1:
                    vid     = unquote_plus(rest).strip()
                    fmt_key = '360p'
                else:
                    vid     = unquote_plus(rest[:slash]).strip()
                    fmt_key = unquote_plus(rest[slash + 1:]).strip()

                fmt_str = FORMAT_MAP.get(fmt_key, FORMAT_MAP['360p'])
                url     = 'https://www.youtube.com/watch?v=' + vid
                cmd     = [YTDLP_BIN] + BASE_FLAGS + [
                    '-f', fmt_str,
                    '--no-playlist',
                    '-o', '-',
                    '--extractor-args', 'youtube:player_client=android',
                    '--no-check-certificates',
                    '--ignore-errors',
                    url,
                ]
                log('pipe stream start: ' + vid + ' (' + fmt_key + ')')
                proc = None
                try:
                    proc = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except Exception:
                    e = sys.exc_info()[1]
                    log('pipe popen error: ' + repr(e))
                    self.send_text('Failed\nCould not start yt-dlp.', 500)
                    return

                # Pre-buffer: wait up to STREAM_PREBUFFER_TIMEOUT for yt-dlp to produce first bytes
                first_chunk = b''
                deadline    = time.time() + STREAM_PREBUFFER_TIMEOUT
                while time.time() < deadline:
                    chunk = proc.stdout.read(LIVE_CHUNK)
                    if chunk:
                        first_chunk = chunk
                        break
                    # Check if process died with an error
                    if proc.poll() is not None:
                        break
                    time.sleep(0.1)

                if not first_chunk:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    log('pipe stream: no bytes in ' + str(STREAM_PREBUFFER_TIMEOUT) + 's for ' + vid)
                    self.send_text(
                        'Failed\nPipe stream produced no data.\n'
                        'Video may be unavailable or geo-blocked.', 500)
                    return

                # Send headers NOW — first bytes are ready
                self.send_response(200)
                self.send_header('Content-Type', 'video/mp4')
                self.send_header('Connection', 'close')
                self.end_headers()

                # Write pre-buffered chunk then continue streaming
                try:
                    self.wfile.write(first_chunk)
                    self.wfile.flush()
                    while True:
                        chunk = proc.stdout.read(LIVE_CHUNK)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        self.wfile.flush()
                except Exception:
                    pass  # XBMC closed socket (user stopped)
                finally:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    log('pipe stream ended: ' + vid)
                return

            # ================================================================
            # PLAY  /play/<vid>/<fmt_key>
            #
            # Resolves the direct CDN URL with yt-dlp -g and returns it as
            # plain text.  default.py calls player.play(url) directly.
            # NO conversion flags — fetches real stream data. (item 6)
            #
            # fmt_key: 144p | 240p | 360p | 480p | 720p | best_mp4 | best
            # Defaults to 360p if fmt_key is missing or unrecognised.
            # ================================================================
            elif path.startswith('/play/'):
                rest    = path[6:]
                slash   = rest.find('/')
                if slash == -1:
                    vid     = unquote_plus(rest).strip()
                    fmt_key = '360p'
                else:
                    vid     = unquote_plus(rest[:slash]).strip()
                    fmt_key = unquote_plus(rest[slash + 1:]).strip()

                fmt_str = FORMAT_MAP.get(fmt_key, FORMAT_MAP['360p'])
                url     = 'https://www.youtube.com/watch?v=' + vid
                cmd     = [YTDLP_BIN] + BASE_FLAGS + [
                    '-f', fmt_str,
                    '--no-playlist',
                    '-g',
                    '--extractor-args', 'youtube:player_client=android',
                    '--no-check-certificates',
                    '--ignore-errors',
                    url,
                ]
                log('resolve VOD (' + fmt_key + '): ' + vid)
                out, err = run(cmd)

                direct = ''
                for line in out.strip().splitlines():
                    line = line.strip()
                    if line.startswith('http'):
                        direct = line
                        break

                if not direct:
                    log('VOD resolve failed: ' + err.strip()[:300])
                    # Try fallback without extractor args
                    cmd_fallback = [YTDLP_BIN] + BASE_FLAGS + [
                        '-f', fmt_str,
                        '--no-playlist',
                        '-g',
                        '--no-check-certificates',
                        '--ignore-errors',
                        url,
                    ]
                    out, err = run(cmd_fallback)
                    for line in out.strip().splitlines():
                        line = line.strip()
                        if line.startswith('http'):
                            direct = line
                            break
                    
                    if not direct:
                        self.send_text(
                            'Failed\nCould not resolve stream URL.\n'
                            + err.strip()[:200], 500)
                        return

                log('VOD resolved: ' + direct[:100])
                self.send_text(direct)
                return

            # ================================================================
            # LIVE STREAM  /live_stream/<vid>
            #
            # Resolves the CDN URL for live stream and returns it as plain text.
            # XBMC handles m3u playback natively.
            # ================================================================
            elif path.startswith('/live_stream/'):
                vid = unquote_plus(path[13:]).strip()
                url = 'https://www.youtube.com/watch?v=' + vid
                
                # Format selection for live streams (m3u8 preferred)
                cmd = [YTDLP_BIN] + BASE_FLAGS + [
                    '-f', ('best[protocol=m3u8_native]'
                           '/best[protocol=m3u8]'
                           '/best[protocol=http]'
                           '/best'),
                    '-g',
                    '--no-playlist',
                    '--extractor-args', 'youtube:player_client=android',
                    '--no-check-certificates',
                    '--ignore-errors',
                    url,
                ]
                log('resolve live stream: ' + vid)
                out, err = run(cmd)

                direct = ''
                for line in out.strip().splitlines():
                    line = line.strip()
                    if line.startswith('http'):
                        direct = line
                        break

                if not direct:
                    log('live stream resolve failed: ' + err.strip()[:300])
                    # Try fallback without extractor args
                    cmd_fallback = [YTDLP_BIN] + BASE_FLAGS + [
                        '-f', ('best[protocol=m3u8_native]'
                               '/best[protocol=m3u8]'
                               '/best'),
                        '-g',
                        '--no-playlist',
                        '--no-check-certificates',
                        '--ignore-errors',
                        url,
                    ]
                    out, err = run(cmd_fallback)
                    for line in out.strip().splitlines():
                        line = line.strip()
                        if line.startswith('http'):
                            direct = line
                            break
                    
                    if not direct:
                        self.send_text(
                            'Failed\nCould not resolve live stream URL.\n'
                            'Stream may be geo-blocked or unavailable.\n'
                            'Try using a custom proxy (e.g., yt2009, Invidious)\n'
                            'by setting CUSTOM_PROXY_URL in proxy.py configuration.\n'
                            + err.strip()[:200], 500)
                        return

                log('live stream resolved: ' + direct[:100])
                self.send_text(direct)
                return

            # ================================================================
            # COMMENTS  /comments/<vid>
            # FIX: Improved comment extraction without creating .info.json files
            # All data is logged to proxy.log instead
            # ================================================================
            elif path.startswith('/comments/'):
                vid = unquote_plus(path[10:]).strip()
                comments = []
                error_msg = ''

                # Method 1: Try with --dump-json (no file creation)
                cmd = [YTDLP_BIN] + BASE_FLAGS + [
                    '--no-playlist',
                    '--dump-json',
                    '--skip-download',
                    '--ignore-errors',
                    '--extractor-args', 'youtube:player_client=android',
                    'https://www.youtube.com/watch?v=' + vid,
                ]
                log('comments request (method 1): ' + vid)
                try:
                    proc = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = proc.communicate()
                    if proc.returncode == 0:
                        try:
                            data = json.loads(stdout.decode('utf-8', 'ignore'))
                            comment_data = data.get('comments', [])
                            if not comment_data:
                                comment_data = data.get('comment_threads', [])

                            for c in comment_data[:COMMENT_LIMIT]:
                                if isinstance(c, dict):
                                    author = c.get('author', c.get('author_name', 'Unknown'))
                                    text = c.get('text', c.get('content', c.get('body', '')))
                                    if text:
                                        comments.append(author + '|' + text)
                            log('comments extracted via method 1: ' + str(len(comments)) + ' comments')
                        except Exception as e:
                            log('comments parse error (method 1): ' + repr(e))
                    else:
                        error_msg = stderr.decode('utf-8', 'ignore')[:200]
                        log('comments error (method 1): ' + error_msg)
                except Exception as e:
                    log('comments request error (method 1): ' + repr(e))

                # Method 2: Try without extractor args if method 1 failed
                if not comments:
                    cmd = [YTDLP_BIN] + BASE_FLAGS + [
                        '--no-playlist',
                        '--dump-json',
                        '--skip-download',
                        '--ignore-errors',
                        'https://www.youtube.com/watch?v=' + vid,
                    ]
                    log('comments request (method 2): ' + vid)
                    try:
                        proc = subprocess.Popen(
                            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        stdout, stderr = proc.communicate()
                        if proc.returncode == 0:
                            try:
                                data = json.loads(stdout.decode('utf-8', 'ignore'))
                                comment_data = data.get('comments', [])
                                if not comment_data:
                                    comment_data = data.get('comment_threads', [])

                                for c in comment_data[:COMMENT_LIMIT]:
                                    if isinstance(c, dict):
                                        author = c.get('author', c.get('author_name', 'Unknown'))
                                        text = c.get('text', c.get('content', c.get('body', '')))
                                        if text:
                                            comments.append(author + '|' + text)
                                log('comments extracted via method 2: ' + str(len(comments)) + ' comments')
                            except Exception as e:
                                log('comments parse error (method 2): ' + repr(e))
                        else:
                            error_msg = stderr.decode('utf-8', 'ignore')[:200]
                            log('comments error (method 2): ' + error_msg)
                    except Exception as e:
                        log('comments request error (method 2): ' + repr(e))

                if not comments:
                    if error_msg:
                        self.send_text('Failed\nCould not fetch comments.\nError: ' + error_msg, 500)
                    else:
                        self.send_text('Failed\nNo comments found or comments disabled for this video.', 500)
                    log('comments failed: no comments extracted for ' + vid)
                else:
                    self.send_text('\n'.join(comments))
                    log('comments returned: ' + str(len(comments)))
                return

            # ================================================================
            # SEARCH  /search/<query>
            # ================================================================
            elif path.startswith('/search/'):
                q   = unquote_plus(path[8:])
                raw = ytdlp_search(q, RESULT_LIMIT)
                res = parse_listing(raw)

            # ================================================================
            # LIVE SEARCH  /live_search/<query>  (item 11)
            # ================================================================
            elif path.startswith('/live_search/'):
                q   = unquote_plus(path[13:])
                raw = ytdlp_list(live_search_url(q), RESULT_LIMIT)
                if not raw.strip():
                    raw = ytdlp_search(q + ' live stream', RESULT_LIMIT)
                res = parse_listing(raw)

            # ================================================================
            # TRENDING
            # ================================================================
            elif path in ('/trending', '/trending/'):
                raw = ytdlp_list(
                    'https://www.youtube.com/feed/trending', RESULT_LIMIT)
                if not raw.strip():
                    raw = ytdlp_search('trending videos', RESULT_LIMIT)
                res = parse_listing(raw)

            elif path in ('/trending/music', '/trending/music/'):
                raw = ytdlp_search('trending music videos', RESULT_LIMIT)
                res = parse_listing(raw)

            elif path in ('/trending/gaming', '/trending/gaming/'):
                raw = ytdlp_search('trending gaming videos', RESULT_LIMIT)
                res = parse_listing(raw)

            # ================================================================
            # MUSIC CHARTS
            # ================================================================
            elif path in ('/music_charts', '/music_charts/'):
                raw = ytdlp_search('top music chart hits', RESULT_LIMIT)
                res = parse_listing(raw)

            # ================================================================
            # RECOMMENDED  /recommended/<enc_vid>/<enc_title>
            # ================================================================
            elif path.startswith('/recommended/'):
                rest  = path[13:]
                slash = rest.find('/')
                if slash == -1:
                    vid   = unquote_plus(rest).strip()
                    query = vid
                else:
                    vid   = unquote_plus(rest[:slash]).strip()
                    query = unquote_plus(rest[slash + 1:]).strip()
                    if not query:
                        query = vid
                log('recommended for: ' + query)
                raw = ytdlp_search(query, RESULT_LIMIT + 2)
                res = parse_listing(raw, exclude_id=vid)

            # ================================================================
            # LIVE LISTINGS
            # ================================================================
            elif path in ('/live', '/live/'):
                raw = ytdlp_list(live_search_url('live stream'), RESULT_LIMIT)
                if not raw.strip():
                    raw = ytdlp_search('live stream now', RESULT_LIMIT)
                res = parse_listing(raw)

            elif path in ('/live/music', '/live/music/'):
                raw = ytdlp_list(live_search_url('music live'), RESULT_LIMIT)
                if not raw.strip():
                    raw = ytdlp_search('live music stream now', RESULT_LIMIT)
                res = parse_listing(raw)

            elif path in ('/live/gaming', '/live/gaming/'):
                raw = ytdlp_list(live_search_url('gaming live'), RESULT_LIMIT)
                if not raw.strip():
                    raw = ytdlp_search('live gaming stream now', RESULT_LIMIT)
                res = parse_listing(raw)

            elif path in ('/live/news', '/live/news/'):
                raw = ytdlp_list(live_search_url('news live'), RESULT_LIMIT)
                if not raw.strip():
                    raw = ytdlp_search('live news stream now', RESULT_LIMIT)
                res = parse_listing(raw)

            # ================================================================
            # CHANNEL  /channel/<id_or_handle>
            # ================================================================
            elif path.startswith('/channel/'):
                cid = unquote_plus(path[9:]).strip()
                if not cid.startswith('@') and not cid.startswith('UC'):
                    cid = '@' + cid
                raw = ytdlp_list(
                    'https://www.youtube.com/' + cid + '/videos', RESULT_LIMIT)
                res = parse_listing(raw)

            # ================================================================
            # DOWNLOAD  /download/<vid>/<fmt_key>/<sub_key>/<format>/<audio_quality>  (item 4, 9)
            # fmt_key: 144p | 240p | 360p | 480p | 720p | best_mp4 | best
            # sub_key: none | en | auto
            # format: mp4 | mkv | avi | webm
            # audio_quality: low | medium | best
            # ================================================================
            elif path.startswith('/download/'):
                rest   = path[10:]
                parts  = rest.split('/', 4)
                vid     = unquote_plus(parts[0]).strip()
                if len(parts) > 1:
                    fmt_key = unquote_plus(parts[1]).strip()
                else:
                    fmt_key = '480p'
                if len(parts) > 2:
                    sub_key = unquote_plus(parts[2]).strip()
                else:
                    sub_key = 'none'
                if len(parts) > 3:
                    format_ext = unquote_plus(parts[3]).strip()
                else:
                    format_ext = 'mp4'
                if len(parts) > 4:
                    audio_quality = unquote_plus(parts[4]).strip()
                else:
                    audio_quality = 'best'

                fmt_str  = FORMAT_MAP.get(fmt_key, FORMAT_MAP['480p'])
                sub_flags = SUB_MAP.get(sub_key, [])

                dl_dir = os.path.join(HERE, 'downloaded_videos')
                if not os.path.exists(dl_dir):
                    os.makedirs(dl_dir)
                
                # Build output filename with requested format
                output_template = os.path.join(dl_dir, '%(title)s.' + format_ext)
                
                # Add format conversion if needed
                cmd = [YTDLP_BIN] + BASE_FLAGS + [
                    '-f', fmt_str,
                    '-o', output_template,
                ] + sub_flags
                
                # Add format conversion if not mp4 (mp4 is default)
                if format_ext != 'mp4':
                    cmd.extend(['--merge-output-format', format_ext])
                
                # Add audio quality option
                if audio_quality == 'low':
                    cmd.extend(['--audio-quality', '0'])
                elif audio_quality == 'medium':
                    cmd.extend(['--audio-quality', '5'])
                elif audio_quality == 'best':
                    cmd.extend(['--audio-quality', '10'])
                
                cmd.append('https://www.youtube.com/watch?v=' + vid)
                
                try:
                    subprocess.Popen(cmd)
                    self.send_text('Download started')
                    log('download started: ' + vid + ' fmt=' + fmt_key
                        + ' subs=' + sub_key + ' format=' + format_ext
                        + ' audio=' + audio_quality)
                except Exception:
                    e = sys.exc_info()[1]
                    self.send_text('Failed\n' + repr(e), 500)
                return

            # ================================================================
            # DOWNLOAD AUDIO  /download_audio/<vid>/<format>/<audio_quality>
            # For audio-only downloads
            # format: mp3 | m4a | wav | flac
            # audio_quality: low | medium | best
            # ================================================================
            elif path.startswith('/download_audio/'):
                rest   = path[15:]
                parts  = rest.split('/', 2)
                vid     = unquote_plus(parts[0]).strip()
                if len(parts) > 1:
                    format_ext = unquote_plus(parts[1]).strip()
                else:
                    format_ext = 'mp3'
                if len(parts) > 2:
                    audio_quality = unquote_plus(parts[2]).strip()
                else:
                    audio_quality = 'best'

                # Use DOWNLOADED_AUDIOS_DIR if set, otherwise use downloaded_videos
                if DOWNLOADED_AUDIOS_DIR and os.path.isdir(DOWNLOADED_AUDIOS_DIR):
                    dl_dir = DOWNLOADED_AUDIOS_DIR
                else:
                    dl_dir = os.path.join(HERE, 'downloaded_videos')

                # Auto-create directory if it doesn't exist
                if not os.path.exists(dl_dir):
                    try:
                        os.makedirs(dl_dir)
                    except Exception:
                        pass

                # Build output filename with requested format
                output_template = os.path.join(dl_dir, '%(title)s.' + format_ext)
                
                # Audio-only download command
                cmd = [YTDLP_BIN] + BASE_FLAGS + [
                    '-x',  # Extract audio
                    '--audio-format', format_ext,
                    '-o', output_template,
                ]
                
                # Add audio quality option
                if audio_quality == 'low':
                    cmd.extend(['--audio-quality', '0'])
                elif audio_quality == 'medium':
                    cmd.extend(['--audio-quality', '5'])
                elif audio_quality == 'best':
                    cmd.extend(['--audio-quality', '10'])
                
                cmd.append('https://www.youtube.com/watch?v=' + vid)
                
                try:
                    subprocess.Popen(cmd)
                    self.send_text('Audio download started')
                    log('audio download started: ' + vid + ' format=' + format_ext
                        + ' audio=' + audio_quality)
                except Exception:
                    e = sys.exc_info()[1]
                    self.send_text('Failed\n' + repr(e), 500)
                return

            # ================================================================
            # DOWNLOAD TO TEMP  /download_to_temp/<vid>/<fmt_key>/<sub_key>?path=<temp_path>
            # For conversion-based playback: downloads to specified temp path
            # BUG FIX: use query parameters for temp path to handle Windows backslashes
            # ================================================================
            elif path.startswith('/download_to_temp/'):
                rest   = path[17:]
                # Split path and query string
                if '?' in rest:
                    path_part, query_part = rest.split('?', 1)
                else:
                    path_part = rest
                    query_part = ''
                
                parts  = path_part.split('/', 2)
                vid     = unquote_plus(parts[0]).strip()
                if len(parts) > 1:
                    fmt_key = unquote_plus(parts[1]).strip()
                else:
                    fmt_key = '480p'
                if len(parts) > 2:
                    sub_key = unquote_plus(parts[2]).strip()
                else:
                    sub_key = 'none'
                
                # Extract temp_path from query parameter
                temp_path = ''
                if query_part:
                    for param in query_part.split('&'):
                        if param.startswith('path='):
                            temp_path = unquote_plus(param[5:]).strip()
                            break

                fmt_str  = FORMAT_MAP.get(fmt_key, FORMAT_MAP['480p'])
                sub_flags = SUB_MAP.get(sub_key, [])

                if not temp_path:
                    self.send_text('Failed\nNo temp path specified', 500)
                    return

                cmd = [YTDLP_BIN] + BASE_FLAGS + [
                    '-f', fmt_str,
                    '-o', temp_path,
                    '--extractor-args', 'youtube:player_client=android',
                    '--no-check-certificates',
                    '--ignore-errors',
                ] + sub_flags + [
                    'https://www.youtube.com/watch?v=' + vid,
                ]
                try:
                    # Use synchronous call to ensure download completes
                    proc = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = proc.communicate()
                    
                    if proc.returncode != 0:
                        log('download_to_temp error: ' + stderr.decode('utf-8', 'ignore'))
                        # Try fallback without extractor args
                        cmd_fallback = [YTDLP_BIN] + BASE_FLAGS + [
                            '-f', fmt_str,
                            '-o', temp_path,
                            '--no-check-certificates',
                            '--ignore-errors',
                        ] + sub_flags + [
                            'https://www.youtube.com/watch?v=' + vid,
                        ]
                        proc = subprocess.Popen(
                            cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        stdout, stderr = proc.communicate()
                        
                        if proc.returncode != 0:
                            self.send_text('Failed\nDownload failed: ' + stderr.decode('utf-8', 'ignore')[:200], 500)
                            return
                    
                    # Check if file was created and has content
                    if os.path.exists(temp_path) and os.path.getsize(temp_path) > 100000:
                        self.send_text('Download completed')
                        log('download_to_temp completed: ' + vid + ' to ' + temp_path)
                    else:
                        self.send_text('Failed\nDownload incomplete or file not created', 500)
                        log('download_to_temp incomplete: ' + vid)
                except Exception:
                    e = sys.exc_info()[1]
                    self.send_text('Failed\n' + repr(e), 500)
                return

            else:
                self.send_text('Unknown endpoint: ' + path, 404)
                return

            # ----------------------------------------------------------------
            # Send listing result
            # ----------------------------------------------------------------
            if not res or not res.strip():
                log('empty result for: ' + path)
                res = 'Failed\nNo results. Check proxy.log for details.'
            self.send_text(res)

        except Exception:
            e = sys.exc_info()[1]
            log('do_GET error: ' + repr(e))
            try:
                self.send_text('Failed\n' + repr(e), 500)
            except Exception:
                pass


# =============================================================================
# Dependency checks
# =============================================================================
def check_ffmpeg():
    """Check if ffmpeg is available in PATH."""
    try:
        proc = subprocess.Popen(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.communicate()
        return proc.returncode == 0
    except Exception:
        return False

def check_deno():
    """Check if deno is available in PATH."""
    try:
        proc = subprocess.Popen(['deno', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.communicate()
        return proc.returncode == 0
    except Exception:
        return False

def check_node():
    """Check if node is available in PATH."""
    try:
        proc = subprocess.Popen(['node', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.communicate()
        return proc.returncode == 0
    except Exception:
        return False

# =============================================================================
# Startup
# =============================================================================
if __name__ == '__main__':

    # Step 1: locate yt-dlp
    YTDLP_BIN = find_ytdlp()

    if not YTDLP_BIN:
        _print('')
        _print('yt-dlp was not found. It is required for this proxy.')
        _print('')
        ans = _input('Download yt-dlp.exe now? (yes/no): ').lower()
        if ans in ('y', 'yes'):
            YTDLP_BIN = download_ytdlp()
            if not YTDLP_BIN:
                _print('Could not download yt-dlp. Exiting.')
                sys.exit(1)
        else:
            _print('Place yt-dlp.exe next to proxy.py and restart.')
            _print('Download from: https://github.com/yt-dlp/yt-dlp/releases')
            sys.exit(1)
    else:
        log('yt-dlp found: ' + YTDLP_BIN)

    # Step 1.5: Check for ffmpeg (required for video conversion)
    if not check_ffmpeg():
        _print('')
        _print('WARNING: ffmpeg was not found.')
        _print('ffmpeg is required for video conversion and some download features.')
        _print('Install from: https://ffmpeg.org/download.html')
        _print('Continuing without ffmpeg may limit functionality.')
        _print('')
        log('ffmpeg not found - some features may not work')
    else:
        log('ffmpeg found')

    # Step 1.6: Check for deno or node (for yt-dlp-ejs if needed)
    if YT_DLP_EJS_RUNTIME:
        # User specified custom runtime
        if os.path.isfile(YT_DLP_EJS_RUNTIME):
            log('Custom JS runtime found: ' + YT_DLP_EJS_RUNTIME)
        else:
            _print('')
            _print('WARNING: Custom JS runtime not found: ' + YT_DLP_EJS_RUNTIME)
            _print('Falling back to deno if available.')
            if not check_deno():
                _print('deno not found either. yt-dlp-ejs features may not work.')
            log('Custom JS runtime not found')
    else:
        # Check for deno (default for yt-dlp-ejs)
        if check_deno():
            log('deno found - yt-dlp-ejs compatible')
        elif check_node():
            log('node found - can be used for yt-dlp-ejs')
        else:
            _print('')
            _print('INFO: deno was not found.')
            _print('deno is optional but recommended for yt-dlp-ejs features.')
            _print('Install from: https://deno.land/')
            _print('Continuing without deno.')
            _print('')
            log('deno not found - yt-dlp-ejs features may not work')

    # Step 2: start server immediately (don't block on update check)
    try:
        server = ThreadedHTTPServer(('0.0.0.0', PORT), Proxy)
        # Socket keep-alive for better live stream reliability (item 5)
        try:
            import socket
            server.socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        except Exception:
            pass
    except Exception:
        e = sys.exc_info()[1]
        _print('Could not start server on port ' + str(PORT) + ': ' + repr(e))
        sys.exit(1)

    # Step 3: start background update check.
    # The worker prints the 'Proxy active' banner when done. (item 1)
    _print('Checking for yt-dlp updates...')
    start_update_check(YTDLP_BIN)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        _print('Stopped.')
        log('Server stopped.')
