#!/usr/bin/env bash
# 这就是通过 /api/run 在 runner 上跑的那条命令，单独放一份方便复用/排查。
# 用法：curl --get --data-urlencode "cmd=$(cat this)" $URL/api/run
set -x
for u in \
  'https://d.apkpure.com/b/APK/com.zhiliaoapp.musically?version=latest' \
  'https://d.apkpure.net/b/APK/com.zhiliaoapp.musically?version=latest' \
  'https://d.apkpure.com/b/XAPK/com.zhiliaoapp.musically?version=latest'; do
  curl -sL --max-time 240 -A 'Mozilla/5.0 (Linux; Android 14)' -o /tmp/tt.bin "$u"
  sz=$(stat -c%s /tmp/tt.bin 2>/dev/null || echo 0)
  echo "src=$u bytes=$sz"
  [ "$sz" -gt 20000000 ] && break
done
file /tmp/tt.bin
if [ "$(head -c 2 /tmp/tt.bin)" = "PK" ]; then
  rm -rf /tmp/ttx && mkdir /tmp/ttx && unzip -oq /tmp/tt.bin -d /tmp/ttx
  apks=$(find /tmp/ttx -name '*.apk' | tr '\n' ' ')
  echo "apks: $(echo $apks | wc -w)"
  timeout 300 adb install-multiple -r $apks 2>&1 | tail -5
else
  timeout 300 adb install -r /tmp/tt.bin 2>&1 | tail -5
fi
adb shell pm list packages | grep -i music || echo "not installed"
adb shell monkey -p com.zhiliaoapp.musically -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
sleep 8
adb shell dumpsys activity activities | grep -m2 -E 'mResumedActivity|topResumedActivity'
adb exec-out screencap -p > /tmp/tt_shot.png; ls -l /tmp/tt_shot.png
