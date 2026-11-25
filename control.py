#!/usr/bin/env python3
"""云端安卓机控制面板后端：按钮 -> adb shell input，截图 -> /shots/。"""
import os
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

SHOTS = os.environ.get("SHOTS_DIR", "/opt/panel/shots")
os.makedirs(SHOTS, exist_ok=True)

ADB = ["adb", "shell"]


def sh(*args, timeout=15):
    try:
        return subprocess.run(ADB + list(args), capture_output=True, timeout=timeout).stdout.decode(errors="replace")
    except Exception as e:  # adb 短暂不可用不应让面板崩溃
        return f"ERR {e}"


def rotate(step):
    cur = sh("settings", "get", "system", "user_rotation").strip()
    cur = int(cur) if cur.isdigit() else 0
    sh("settings", "put", "system", "accelerometer_rotation", "0")
    sh("settings", "put", "system", "user_rotation", str((cur + step) % 4))


def cmd(name):
    if name in ("back", "home", "recents", "power", "wake", "volup", "voldown"):
        key = {"back": 4, "home": 3, "recents": 187, "power": 26, "wake": 224, "volup": 24, "voldown": 25}[name]
        sh("input", "keyevent", str(key))
    elif name in ("rotl", "rotr"):
        rotate(-1 if name == "rotl" else 1)
    elif name == "shot":
        png = subprocess.run(["adb", "exec-out", "screencap", "-p"], capture_output=True, timeout=20).stdout
        open(os.path.join(SHOTS, "latest.png"), "wb").write(png)
    elif name == "screenoff":
        sh("input", "keyevent", "26")
    else:
        return f"unknown {name}"
    return "ok"


class H(BaseHTTPRequestHandler):
    def _send(self, body, ctype="application/json"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/cmd":
            c = (parse_qs(u.query).get("c") or [""])[0]
            self._send('{"r":"%s"}' % cmd(c))
        elif u.path.startswith("/shots/"):
            f = os.path.join(SHOTS, os.path.basename(u.path))
            if os.path.exists(f):
                self._send(open(f, "rb").read(), "image/png")
            else:
                self.send_error(404)
        elif u.path == "/api/sh":
            c = (parse_qs(u.query).get("cmd") or [""])[0]
            out = subprocess.run(["adb","shell",c], capture_output=True, timeout=30).stdout.decode(errors="replace")
            self._send(out or "(no output)", "text/plain")
        elif u.path == "/api/app":
            pkg = (parse_qs(u.query).get("pkg") or [""])[0]
            sh("monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1")
            self._send('{"r":"ok"}')
        elif u.path == "/api/run":
            c = (parse_qs(u.query).get("cmd") or [""])[0]
            r = subprocess.run(c, shell=True, capture_output=True, timeout=280)
            self._send((r.stdout + r.stderr).decode(errors="replace")[-4000:] or "(no output)", "text/plain")
        elif u.path == "/api/open":
            url = (parse_qs(u.query).get("url") or [""])[0]
            sh("am", "start", "-a", "android.intent.action.VIEW", "-d", url, "-p", "com.android.chrome")
            self._send('{"r":"ok"}')
        elif u.path == "/api/tap":
            q = parse_qs(u.query)
            cx, cy = int(q["x"][0]), int(q["y"][0])
            sh("input", "tap", str(cx), str(cy))
            self._send('{"r":"ok"}')
        elif u.path == "/api/swipe":
            q = parse_qs(u.query)
            a = [int(q[k][0]) for k in ("x1","y1","x2","y2")]
            sh("input", "swipe", *map(str, a), "300")
            self._send('{"r":"ok"}')
        elif u.path == "/api/shot":
            cmd("shot")
            self._send('{"r":"ok","url":"/shots/latest.png?%d"}' % time.time())
        else:
            self.send_error(404)

    def log_message(self, *a):
        pass


ThreadingHTTPServer(("127.0.0.1", 8090), H).serve_forever()
