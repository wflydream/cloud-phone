# cloud-phone

在 GitHub Actions 免费 runner 上起一台 Android 14 模拟器（Pixel 6 规格，720x1280），用 scrcpy 镜像到虚拟桌面（Xvfb + x11vnc + noVNC），经 cloudflared 快速隧道给出一个浏览器地址。本机只开一个标签页，不占内存。

## 用法

```bash
./phone.sh 50        # 起一台，约 5 分钟后打印链接
```

或手动：

```bash
gh workflow run cloud-phone.yml -R wflydream/cloud-phone -f minutes=50
```

链接形如 `https://xxx.trycloudflare.com/panel.html`，每次随机，在 run 的 Summary 和日志 `OPEN:` 行。

## 面板

左侧按钮全部走 `adb shell input`：

| 按钮 | 说明 |
|---|---|
| 返回 / 桌面 / 任务 | 导航键 |
| 左转 / 右转 | 屏幕方向 |
| 音量 + / − | 音量键 |
| 电源 | 亮屏 / 灭屏 |
| 截图 | 存到 `/shots/latest.png` 并新窗口打开 |
| Chrome / YouTube / TikTok | 启动对应 App |

scrcpy 快捷键（点一下手机画面后可用）：`Alt+H` 桌面、`Alt+B` 返回、`Alt+S` 最近任务、`Alt+P` 电源、`Alt+R` / `Alt+Shift+R` 旋转、`Alt+↑/↓` 音量。

## HTTP 接口

同域下（nginx 反代到 control.py，:8090）：

```
GET /api/cmd?c=back|home|recents|rotl|rotr|volup|voldown|power
GET /api/app?pkg=<package>
GET /api/tap?x=<px>&y=<px>          # 设备像素
GET /api/swipe?x1=&y1=&x2=&y2=
GET /api/shot                       # 截图，返回 /shots/latest.png
GET /api/sh?cmd=<adb shell 命令>     # 返回命令输出（guest 内）
GET /api/run?cmd=<shell 命令>        # runner 上执行（下载 APK、adb install）
```

## 本机驱动脚本

```
python3 drive.py https://xxx.trycloudflare.com sh "pm list packages | grep music"
python3 drive.py <url> tap 360 1044
python3 drive.py <url> drag 551 788 551 688      # 自定义滚轮要真拖拽
python3 drive.py <url> dump                       # UI 文本 + bounds
python3 drive.py <url> shot out.png
```

## 性能取舍

- 模拟器 720x1280 / 320dpi：runner 无 GPU，swiftshader 软件渲染，像素越少越快。
- scrcpy `--max-size 720 --max-fps 30 --video-bit-rate 2M`（scrcpy 3.x 参数名是 `--video-bit-rate`）。
- Xvfb 1000x900，x11vnc 用 XDamage 只传变化区域（别加 `-noxdamage`）。
- 已知下限：VNC 不是视频协议，跨洲快链路 RTT ~200ms；实测键盘/点击到画面变化约 100–225ms。
- 想要更顺：换 ws-scrcpy（浏览器直接收 H.264，跳过 VNC 一层）。

## 网络

- guest 用模拟器默认 NAT/DNS（不要加 `-dns-server`）。
- 判断 guest 有没有网不要用 `ping 8.8.8.8`：Android 的 shell 没有原始套接字权限，ICMP 必失败，看起来像断网。看 `dumpsys connectivity | grep -i NetworkAgentInfo` 里的 `VALIDATED` 和 `Routes: 0.0.0.0/0 -> 10.0.2.2`，或者直接在 Chrome 里开页面。
- 中文语言：`settings put system system_locales zh-CN`；时区 `setprop persist.sys.timezone Asia/Shanghai`。
- 出口 IP 是 GitHub（Azure 美国机房）：普通站点能上；风控严格的 App 可能被判定为机房流量。

## 限制

- 单次最长约 5 小时（job 上限 350 分钟），到期机器连同数据销毁。
- 隧道无密码：拿到 URL 的人都能操作这台机器。只发自己；要更安全换 Tailscale 私有网 + 本机 scrcpy，或给 x11vnc 加 `-rfbauth`。
- google_apis 镜像无 Play 商店；装 App 靠侧载 APK（APKPure）。
- 模拟器没有 Play Integrity 硬件证明，TikTok 这类强风控 App 可能无法登录或推荐流为空。
