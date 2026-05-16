#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generate_cookies.py - YouTube Cookies Generator for XBMC YouTube Script

This script helps users generate a cookies.txt file for YouTube authentication.
The cookies.txt file can be used for:
- Viewing comments that require authentication
- Getting personalized recommendations
- Accessing age-restricted content
- Using custom proxy services

Usage:
    python generate_cookies.py

Requirements:
    - Python 2.4+ or Python 3.x
    - A web browser to export cookies
"""

import os
import sys
import time
import json   # FIX: was missing — caused 'NameError: name json is not defined'

# Python 2/3 compatibility
PY3 = sys.version_info[0] >= 3
if PY3:
    input_func = input
else:
    input_func = raw_input

# =============================================================================
# Configuration
# =============================================================================
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(SCRIPT_DIR, "yt_cookies.txt")
CONFIG_FILE  = os.path.join(SCRIPT_DIR, "yt_config.json")

VERSION = "v1.0"

# =============================================================================
# ANSI helpers  (Windows cmd fallback: no colour but still works)
# =============================================================================
try:
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(
            ctypes.windll.kernel32.GetStdHandle(-11), 7)
    _ANSI = True
except Exception:
    _ANSI = False

def _c(code, text):
    if _ANSI:
        return '\033[' + code + 'm' + text + '\033[0m'
    return text

def green(t):  return _c('92', t)
def yellow(t): return _c('93', t)
def red(t):    return _c('91', t)
def cyan(t):   return _c('96', t)
def bold(t):   return _c('1',  t)
def dim(t):    return _c('2',  t)

# =============================================================================
# Transition / wait helpers
# =============================================================================
SPINNER = ['|', '/', '-', '\\']

def spinner_wait(seconds, message='Working'):
    """Show a spinner for `seconds` seconds."""
    deadline = time.time() + seconds
    i = 0
    while time.time() < deadline:
        sys.stdout.write('\r  ' + cyan(SPINNER[i % 4]) + '  ' + message + ' ')
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write('\r' + ' ' * (len(message) + 8) + '\r')
    sys.stdout.flush()

def step_pause(msg='', delay=0.6):
    """Print a message then pause briefly."""
    if msg:
        sys.stdout.write('  ' + msg + '\n')
        sys.stdout.flush()
    time.sleep(delay)

def sep(char='=', width=70):
    return char * width

def banner():
    print('')
    print(cyan(sep()))
    print(cyan('  YouTube Cookies Generator  ') + dim(VERSION))
    print(cyan(sep()))
    print('')

# =============================================================================
# Instructions text
# =============================================================================
INSTRUCTIONS = """
  {bold}METHOD 1 — Browser Export  (Recommended){reset}
  ─────────────────────────────────────────
  1. Install a browser extension to export cookies:
       Chrome/Edge : "Get cookies.txt LOCALLY"
       Firefox     : "Cookie Quick Manager" or "Export Cookies"

  2. Visit  youtube.com  and log in.

  3. Use the extension to export cookies in Netscape format.

  4. Save the file as:  {file}

  5. Place it next to this script.

  {bold}METHOD 2 — Developer Tools  (Advanced){reset}
  ──────────────────────────────────────
  1. Log in to youtube.com in your browser.
  2. Open DevTools (F12) › Application › Cookies › youtube.com
  3. Export cookies in Netscape format → save as  {file}

  {bold}METHOD 3 — yt-dlp  (Alternative){reset}
  ─────────────────────────────────
  1.  pip install yt-dlp
  2.  yt-dlp --cookies-from-browser chrome --print cookies
  3.  Save the output as  {file}
""".format(
    bold='\033[1m' if _ANSI else '',
    reset='\033[0m' if _ANSI else '',
    file=yellow('yt_cookies.txt') if _ANSI else 'yt_cookies.txt',
)

# =============================================================================
# Config template
# =============================================================================
CONFIG_TEMPLATE = {
    "api_key": "",
    "api_account_key": "",
    "custom_proxy_url": "",
    "cookies_file": "yt_cookies.txt",
    "vod_playback_method": "pipe",
    "downloaded_audio_dir": "downloaded_audios",
    "fetch_cookies_from_proxy": False,
    "proxy_cookies_url": ""
}

# =============================================================================
# Config read / write
# =============================================================================
def read_config():
    """Read yt_config.json; return dict (empty on any error)."""
    try:
        if os.path.exists(CONFIG_FILE):
            f = open(CONFIG_FILE, 'r')
            content = f.read()
            f.close()
            if content.strip():
                return json.loads(content)
    except Exception:
        e = sys.exc_info()[1]
        print(red('  [ERROR] Could not read config: ') + str(e))
    return {}

def write_config(cfg):
    """Write dict to yt_config.json; return True on success."""
    try:
        f = open(CONFIG_FILE, 'w')
        f.write(json.dumps(cfg, indent=4))
        f.close()
        return True
    except Exception:
        e = sys.exc_info()[1]
        print(red('  [ERROR] Could not write config: ') + str(e))
        return False

def get_config_value(key, default=None):
    cfg = read_config()
    return cfg.get(key, default)

def set_config_value(key, value):
    cfg = read_config()
    cfg[key] = value
    return write_config(cfg)

# =============================================================================
# Cookies helpers
# =============================================================================
def check_cookies_file():
    """Return True and print status if cookies file exists."""
    if os.path.exists(COOKIES_FILE):
        size = os.path.getsize(COOKIES_FILE)
        print(green('  [OK]  ') + 'Cookies file found: ' + COOKIES_FILE)
        print(dim('        Size: ' + str(size) + ' bytes'))
        return True
    else:
        print(yellow('  [--]  ') + 'Cookies file not found: ' + COOKIES_FILE)
        return False

def create_empty_cookies_file():
    """Create a placeholder cookies.txt for the user to fill in."""
    if os.path.exists(COOKIES_FILE):
        print(yellow('  [!]  File already exists: ') + COOKIES_FILE)
        ans = input_func('        Overwrite? (y/n): ').strip().lower()
        if ans != 'y':
            print(dim('  Skipped.'))
            return False

    spinner_wait(0.8, 'Creating file')
    try:
        lines = [
            '# Netscape HTTP Cookie File',
            '# Export cookies from YouTube and paste them below.',
            '# Format:  domain  flag  path  secure  expiry  name  value',
            '#',
            '# Example:',
            '# .youtube.com\tTRUE\t/\tFALSE\t1234567890\tSAPISID\t<value>',
            '',
        ]
        f = open(COOKIES_FILE, 'w')
        f.write('\n'.join(lines))
        f.close()
        print(green('  [OK]  ') + 'Created: ' + COOKIES_FILE)
        print(dim('  Fill it in using one of the methods above.'))
        return True
    except Exception:
        e = sys.exc_info()[1]
        print(red('  [ERROR] ') + str(e))
        return False

# =============================================================================
# Config file helpers
# =============================================================================
def create_config_file():
    """Create yt_config.json with sensible defaults."""
    if os.path.exists(CONFIG_FILE):
        print(yellow('  [!]  Config already exists: ') + CONFIG_FILE)
        ans = input_func('        Overwrite with defaults? (y/n): ').strip().lower()
        if ans != 'y':
            print(dim('  Skipped.'))
            return False

    spinner_wait(0.8, 'Writing config')
    if write_config(CONFIG_TEMPLATE):
        print(green('  [OK]  ') + 'Config created: ' + CONFIG_FILE)
        return True
    return False

# =============================================================================
# Fetch cookies from proxy  (optional, persistent toggle)
# =============================================================================
def show_proxy_cookie_status():
    enabled = get_config_value('fetch_cookies_from_proxy', False)
    url     = get_config_value('proxy_cookies_url', '')
    if enabled:
        print(green('  [ON]  ') + 'Proxy cookie fetching is ENABLED')
        print(dim('        URL: ') + (url or '(none set)'))
    else:
        print(yellow('  [OFF] ') + 'Proxy cookie fetching is DISABLED')
    return enabled

def configure_proxy_cookies():
    """
    Let the user toggle the proxy cookie fetch option on/off,
    and set the proxy URL.  Settings persist in yt_config.json.
    """
    print('')
    print(bold('  Fetch Cookies from Custom Proxy'))
    print(dim('  ' + sep('-', 40)))
    print('')
    print('  This optional feature lets the proxy server supply YouTube cookies')
    print('  automatically.  It requires a compatible proxy API (e.g. yt2009,')
    print('  Invidious, or a custom server you control).')
    print('')

    enabled = get_config_value('fetch_cookies_from_proxy', False)
    url     = get_config_value('proxy_cookies_url', '')

    print('  Current state: ' + (green('ENABLED') if enabled else yellow('DISABLED')))
    if url:
        print('  Current URL  : ' + url)
    print('')

    while True:
        print('  [1]  ' + ('Disable' if enabled else 'Enable') + ' proxy cookie fetching')
        print('  [2]  Set / change proxy URL')
        print('  [3]  Back')
        print('')
        choice = input_func('  Option (1-3): ').strip()

        if choice == '1':
            new_state = not enabled
            spinner_wait(0.6, 'Saving')
            if set_config_value('fetch_cookies_from_proxy', new_state):
                enabled = new_state
                state_str = green('ENABLED') if enabled else yellow('DISABLED')
                print(green('  [OK]  ') + 'Proxy cookie fetching is now ' + state_str)
            step_pause()

        elif choice == '2':
            print('')
            new_url = input_func('  Enter proxy URL (e.g. https://yt.lemnoslife.com): ').strip()
            if new_url:
                spinner_wait(0.6, 'Saving')
                set_config_value('proxy_cookies_url', new_url)
                url = new_url
                print(green('  [OK]  ') + 'Proxy URL saved: ' + url)
            else:
                print(yellow('  [!]  No URL entered — skipped.'))
            step_pause()

        elif choice == '3':
            break
        else:
            print(red('  [?]  Invalid option.'))

# =============================================================================
# Status summary
# =============================================================================
def show_status():
    print('')
    print(bold('  Status'))
    print(dim('  ' + sep('-', 40)))
    has_cookies = check_cookies_file()

    cfg = read_config()
    if cfg:
        api = cfg.get('api_key', '')
        account = cfg.get('api_account_key', '')
        proxy = cfg.get('custom_proxy_url', '')
        method = cfg.get('vod_playback_method', 'pipe')
        fetch  = cfg.get('fetch_cookies_from_proxy', False)
        purl   = cfg.get('proxy_cookies_url', '')

        def _mask(s):
            if s and len(s) > 6:
                return s[:6] + '...'
            return s or '(not set)'

        print(dim('  Config file  : ') + green('found'))
        print(dim('  API key      : ') + _mask(api))
        print(dim('  Account key  : ') + _mask(account))
        print(dim('  Custom proxy : ') + (proxy or dim('(none)')))
        print(dim('  VOD method   : ') + method)
        print(dim('  Proxy cookies: ')
              + (green('ON — ' + purl) if fetch else yellow('OFF')))
    else:
        print(yellow('  [--]  Config file not found — run option [2] to create it.'))
    print('')

# =============================================================================
# Main menu
# =============================================================================
def main():
    banner()
    show_status()

    while True:
        print(bold('  Options'))
        print(dim('  ' + sep('-', 40)))
        print('  [1]  Create empty cookies.txt  (manual fill)')
        print('  [2]  Create / reset yt_config.json  (default settings)')
        print('  [3]  Check cookies file status')
        print('  [4]  Configure proxy cookie fetching  (optional)')
        print('  [5]  View browser export instructions')
        print('  [6]  Exit')
        print('')

        choice = input_func('  Select option (1-6): ').strip()
        print('')

        if choice == '1':
            create_empty_cookies_file()

        elif choice == '2':
            create_config_file()

        elif choice == '3':
            show_status()

        elif choice == '4':
            configure_proxy_cookies()

        elif choice == '5':
            print(INSTRUCTIONS)

        elif choice == '6':
            spinner_wait(0.5, 'Exiting')
            print(cyan('  Goodbye!'))
            print('')
            break

        else:
            print(red('  [?]  Invalid option — please enter 1 to 6.'))

        print('')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n' + dim('  Interrupted. Bye.'))
        sys.exit(0)
