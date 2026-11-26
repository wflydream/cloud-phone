#!/usr/bin/env python3
"""一次性把 TikTok 从启动推过注册/生日门，直到看到推荐流。

用法：python3 finish_tiktok.py <base_url>
每步打印实际界面文本，失败就停在该步并给出当前 dump。
"""
import re
import sys
import time

sys.path.insert(0, "/Users/wfly/Documents/code/wfly/bolierplate/other/temp/cloud-phone")
import drive  # noqa: E402


def ui():
    xml = drive.dump()
    items = []
    for m in re.finditer(r'text="([^"]*)"[^>]*?(?:enabled="(true|false)")?[^>]*?bounds="(\[[^"]+\])"', xml):
        t, en, b = m.group(1), m.group(2), m.group(3)
        if t:
            items.append((t, b, en))
    return xml, items


def center(b):
    nums = [int(n) for n in re.findall(r"-?\d+", b)]
    return (nums[0] + nums[2]) // 2, (nums[1] + nums[3]) // 2


def find(items, *names):
    for t, b, en in items:
        for n in names:
            if n.lower() in t.lower():
                return t, b, en
    return None


def main():
    drive.BASE = sys.argv[1].rstrip("/")
    print("pkgs:", drive.sh("pm list packages | grep music").strip())
    drive.sh("monkey -p com.zhiliaoapp.musically -c android.intent.category.LAUNCHER 1")
    time.sleep(12)

    for round_ in range(6):
        xml, items = ui()
        print("round", round_, "texts:", [t for t, _, _ in items][:12])
        hit = find(items, "Skip", "Not now", "Got it")
        if hit:
            t, b, _ = hit
            x, y = center(b)
            print("tap", t, x, y)
            drive.tap(x, y)
            time.sleep(8)
            continue
        hit = find(items, "Continue")
        if hit:
            t, b, en = hit
            if en == "true":
                x, y = center(b)
                drive.sh(f"input tap {x} {y}")
                print("tapped Continue", x, y)
                time.sleep(12)
                continue
            # 生日门：点 Birthday 字段试原生选择器
            fb = find(items, "Birthday")
            if fb:
                x, y = center(fb[1])
                print("tap Birthday field", x, y)
                drive.tap(x, y)
                time.sleep(4)
                xml2, items2 = ui()
                print("after field:", [t for t, _, _ in items2][:10])
                continue
        # 可能已在推荐流
        if any(k in t for k in ("For You", "Following", "Home") for t, _, _ in items):
            print("feed visible")
            break
        time.sleep(5)
    drive.api("/api/shot")
    open("/Users/wfly/Documents/code/wfly/bolierplate/other/temp/cloud-phone/tiktok_state.png", "wb").write(
        drive.api("/shots/latest.png", raw=True))
    print("saved tiktok_state.png")


if __name__ == "__main__":
    main()
