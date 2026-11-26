#!/usr/bin/env python3
"""驱动云端安卓机：python3 drive.py <base_url> <命令...>

命令：
  sh <cmd>           guest adb shell
  run <cmd>          runner shell
  tap x y
  drag x1 y1 x2 y2   真拖拽（motionevent 序列，给自定义滚轮用）
  key <code>
  app <pkg>
  dump               打印 UI 文本与 bounds
  shot <file>        截图存本地
"""
import base64
import json
import sys
import time
import urllib.parse
import urllib.request

BASE = ""


def api(path, timeout=120, raw=False):
    for i in range(3):
        try:
            with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
                b = r.read()
                return b if raw else b.decode(errors="replace")
        except Exception as e:
            if i == 2:
                raise
            time.sleep(2)


def sh(cmd):
    return api("/api/sh?cmd=" + urllib.parse.quote(cmd))


def run(cmd):
    return api("/api/run?cmd=" + urllib.parse.quote(cmd), timeout=280)


def tap(x, y):
    return api(f"/api/tap?x={x}&y={y}")


def drag(x1, y1, x2, y2, steps=8, hold=0.02):
    sh(f"input motionevent DOWN {x1} {y1}")
    for i in range(1, steps + 1):
        time.sleep(hold)
        sh(f"input motionevent MOVE {x1 + (x2-x1)*i//steps} {y1 + (y2-y1)*i//steps}")
    sh(f"input motionevent UP {x2} {y2}")


def dump():
    sh("uiautomator dump /sdcard/ui.xml >/dev/null 2>&1")
    xml = sh("cat /sdcard/ui.xml")
    return xml


def main():
    global BASE
    BASE = sys.argv[1].rstrip("/")
    args = sys.argv[2:]
    if not args:
        print(__doc__)
        return
    c = args[0]
    if c == "sh":
        print(sh(" ".join(args[1:])))
    elif c == "run":
        print(run(" ".join(args[1:])))
    elif c == "tap":
        print(tap(args[1], args[2]))
    elif c == "drag":
        drag(*map(int, args[1:5]))
        print("ok")
    elif c == "key":
        print(sh("input keyevent " + args[1]))
    elif c == "app":
        print(sh("monkey -p %s -c android.intent.category.LAUNCHER 1" % args[1]))
    elif c == "dump":
        xml = dump()
        import re
        for m in re.finditer(r'text="([^"]*)"[^>]*bounds="(\[[^"]+\])"', xml):
            if m.group(1):
                print(m.group(1), m.group(2))
    elif c == "shot":
        api("/api/shot")
        open(args[1], "wb").write(api("/shots/latest.png", raw=True))
        print("saved", args[1])
    else:
        print("unknown", c)


if __name__ == "__main__":
    main()
