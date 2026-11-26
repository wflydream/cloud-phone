# cloud-phone —— 免费云端安卓机（GitHub Actions）

在 GitHub Actions 的免费 Linux runner 上起一台 Android 14 模拟器，用 scrcpy 镜像到虚拟桌面，经 noVNC + cloudflared 隧道给一个浏览器地址。本机只开一个标签页，不占内存。

远端仓库：<https://github.com/wflydream/cloud-phone>（public）；隧道链接写在私有仓库 `wflydream/cloud-phone-state`。

---

## 架构

```
Android 14 AVD (x86_64, KVM, 540x960)
  └─ scrcpy --max-size 540 --max-fps 30 --video-bit-rate 1M
       └─ Xvfb :99 (1000x900)
            ├─ x11vnc :5900 (-wait 2 -defer 0)
            │    └─ websockify :6080 (+ /usr/share/novnc 静态页)
            ├─ control.py :8090   ← 面板 API（按键/启动 App/截图/adb shell/runner shell）
            └─ nginx :8080        ← basic auth + 同域反代（/ → 6080，/api、/shots → 8090）
                 └─ cloudflared 快速隧道 → https://xxx.trycloudflare.com/panel.html
```

面板左侧按钮走 `adb shell input`（不依赖 VNC）：返回 / 桌面 / 任务 / 左右转 / 音量 / 电源 / 截图 / Chrome / YouTube / TikTok / TikTok 网页版。

## 用法

```bash
./phone.sh 50          # 起一台，约 6 分钟后打印链接和面板账号
```

等价的底层命令：

```bash
gh workflow run cloud-phone.yml -R wflydream/cloud-phone -f minutes=50
```

链接从私有 state 仓库读（`state/url.txt`），同时写 actions cache 保存 TikTok 登录态。

## 文件

| 文件 | 作用 |
|---|---|
| `.github/workflows/cloud-phone.yml` | 全部流水线：KVM、AVD、scrcpy/x11vnc/websockify/nginx、隧道、链接发布、TikTok 安装、登录态缓存 |
| `control.py` | 面板后端（HTTP，端口 8090）：`/api/cmd`、`/api/app`、`/api/open`、`/api/tap`、`/api/swipe`、`/api/shot`、`/api/sh`（guest shell）、`/api/run`（runner shell） |
| `panel.html` | 面板前端，iframe 内嵌 noVNC，左侧按钮 |
| `nginx.conf` | basic auth + 同域反代；访问日志到 `/tmp/nginx-access.log`（含 `user=`） |
| `phone.sh` | 本机一键起机并打印链接、面板账号 |
| `poll_url.sh` | 轮询私有 state 仓库拿新链接（job 未结束时 GitHub `/logs` 404，别扒日志） |
| `drive.py` | 本机驱动脚本（sh/run/tap/drag/key/app/dump/shot） |
| `finish_tiktok.py`, `tiktok_install.sh` | TikTok 过门脚本与安装命令（历史用途，保留） |

## HTTP 接口

```
GET /api/cmd?c=back|home|recents|rotl|rotr|volup|voldown|power
GET /api/app?pkg=<package>
GET /api/open?url=<https://...>        # 用 Chrome 打开网址
GET /api/tap?x=<px>&y=<px>             # 设备像素
GET /api/swipe?x1=&y1=&x2=&y2=
GET /api/shot                          # 截图，结果在 /shots/latest.png
GET /api/sh?cmd=<adb shell 命令>        # guest 内执行
GET /api/run?cmd=<shell 命令>           # runner 上执行（下载、adb install）
```

## 性能（实测）

- 输入 → 画面变化：**280–624 ms**，中位 ~290 ms（5 次取样）。
- API 往返（含 adb 启动）：1.0–1.9 s。
- 参数：540x960/240dpi、scrcpy 540/30fps/1M、`x11vnc -wait 2 -defer 0`、Xvfb 1000x900。
- 无效尝试：cloudflared `--protocol quic`（WebSocket 连不上）；x11vnc `-threads`（没这个选项，进程直接退出）。
- 再快一档：换 ws-scrcpy（浏览器直接收 H.264，砍掉 Xvfb/x11vnc/websockify 三层）。

## 公开仓库下的保密

- 公开仓库的 Actions 日志和 Summary **不出现隧道 URL**：只写进私有仓库 `wflydream/cloud-phone-state`（repo secret `STATE_PAT`）。
- 面板与所有 API 走 nginx basic auth（repo secrets `BASIC_USER` / `BASIC_PASS`），无凭据一律 401。
- 账号密码保存在本机 `.secrets/github/cloud-phone.json`，不提交进仓库。
- 结论：只泄露 URL 进不去，需要账号密码；两者都泄露才等于拿到这台机。

## 免费额度与时长

- 公共仓库 + 标准 Linux runner **不限分钟**；私有仓库才计入 2,000 分钟/月免费额度（本仓库已转 public）。
- 单 job 硬上限 6 小时，workflow 设 `timeout-minutes: 350`。
- 到点 VM 整体销毁，链接失效；数据只保留 actions cache 里的 TikTok 登录态。
- GitHub Acceptable Use 要求任务与仓库构建/测试相关，长期常驻有账号风险，建议按需短开。

## 踩坑记录（都踩过并修了）

| 现象 | 根因 | 修法 |
|---|---|---|
| noVNC「Failed to connect」 | cloudflared `--protocol quic` 下 WebSocket 失败；或 x11vnc 因非法 `-threads` 退出 | 保持 http2；判活 `pgrep x11vnc` + runner 内 curl websockify 应 101 |
| 画面全黑、`xwininfo` 0 children | scrcpy 启动后才 `wm size` 改分辨率，scrcpy 退出 | 分辨率在 scrcpy 之前设；`while true` 守护并加 `|| true`（`set -e` 会带走整个循环） |
| 画面冻在最后一帧 | `adb root` 重启 adbd，踢掉 scrcpy 连接 | `adb root` 放到 scrcpy 之前；后续按需判断 `adb shell id` |
| 点击没反应 | 上述冻结 + SystemUI ANR 弹窗吃点击 | 修冻结；`settings put global hide_error_dialogs 1` |
| `adb install` 报 `filename doesn't end .apk` | 下载文件名用了 `.bin` | 保存成 `.apk` |
| `pm install /sdcard/...` 打不开文件 | fuse 权限 | 先 `cp` 到 `/data/local/tmp` |
| guest ping 不通 | Android shell 无 raw socket 权限，ICMP 必失败 | 用 `dumpsys connectivity` 看 `VALIDATED`，别用 ping 判网 |
| `-dns-server` 后 guest 丢路由 | 模拟器参数覆盖 | 不加，用默认 NAT/DNS |
| job 未结束时扒日志拿 URL 失败 | GitHub `/logs` 返回 404，页面反爬 | URL 走私有 state 仓库 / ntfy；不再扒日志 |
| TikTok 无游客浏览 | 美区 47.9.3 强制登录；TikTok Lite 提示 "not available in your country" | App 内容需登录（登录态用 actions cache 持久化）；网页版 tiktok.com 可免登录观看 |

## 证据

- `screenshots/web2.png`：云手机 Chrome 里 tiktok.com 视频页（20.9K 赞 / 3030 评论）。
- `screenshots/panel_now2.png`：TikTok App 登录墙 + TikTok Lite 区域限制提示。
- `screenshots/after_scrcpy.png`：画面恢复后的实时桌面。
- `EXPERIMENTS.md`：完整实验记录与排查过程。
