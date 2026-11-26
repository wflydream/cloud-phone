# cloud-phone 进度（2026-11-25）

## 已完成（有实测证据）
- 仓库 `wflydream/cloud-phone`（私有）：GitHub Actions 起 Android 14 x86_64 模拟器 + scrcpy → Xvfb → x11vnc → noVNC → cloudflared 快速隧道。
- 面板：nginx 同域反代 noVNC(6080) + control.py(8090)，`/panel.html` 左侧按钮（返回/桌面/任务/旋转/音量/电源/截图/Chrome/YouTube/TikTok）。
- 接口：`/api/cmd`、`/api/app`、`/api/tap`、`/api/swipe`、`/api/shot`、`/api/sh`（guest adb shell）、`/api/run`（runner shell）。
- 性能：720x1280/320dpi、scrcpy `--max-size 720 --max-fps 30 --video-bit-rate 2M`、Xvfb 1000x900、x11vnc 开 XDamage。
- 延迟实测：输入→画面 79–509ms，中位 149ms（6 次旋转取样）。
- 网络：guest wifi VALIDATED、默认路由 10.0.2.2、DNS 10.0.2.3；Chrome 打开 tiktok.com 有内容（`TikTok - Make Your Day` / `Open app` / 评论 2169 / 206.5K）。
- `ping 8.8.8.8` 从 adb shell 必失败（无 raw socket 权限），不是断网 —— 判网用 dumpsys connectivity。
- TikTok 47.9.3 (APKPure, 483MB) 在 guest 内下载并 `pm install` 成功（`com.zhiliaoapp.musically` 出现在 pm list），App 启动到注册页；Skip 后进入生日门（Continue 默认 disabled）。

## 未完成
- TikTok App 内容：47.9.3（美区）不登录只有登录墙（`pm clear` 后直达 `Log in to TikTok`，注册页无 Skip）；
  TikTok Lite（com.zhiliaoapp.musically.go）装得上但提示 "TikTok Lite not available in your country"（美区限制）。
  结论：App 内内容必须登录；登录态已用 actions cache 持久化（tiktok-data-*），下次机器自动恢复。
- 网页版 tiktok.com 在 Chrome 里能出内容，两次实测：v7 机器（作者名 + 2169 评论 + 206.5K 赞）；
  v16 机器（视频页、20.9K 赞 / 3030 评论 / 594 分享、Home/Discover/Inbox/Profile 全在）。
- 自定义滚轮必须用 `input motionevent DOWN/MOVE/UP` 序列拖拽，`tap`/`swipe` 都不生效。
- URL 发布机制：ntfy（`report_topic` 输入）+ state 分支 contents API + git push 三路，任一成功即可。

## 黑屏根因（2026-11-25 定位并修复）
- 现象：noVNC 连上但画面全黑、`xwininfo -root -tree` 显示 0 children。
- 根因：workflow 先起 scrcpy，之后才 `adb shell wm size 720x1280` 改分辨率，scrcpy 因 display 变化退出，X 桌面就没窗口了。
- 修复：分辨率/动画 demote 到 scrcpy 之前；scrcpy 用 `while true` 守护自动重启（v16）。旧机器上手动重跑 scrcpy 即恢复。

## 性能调优（2026-11-25）
- 现状链路：模拟器(swiftshader) → scrcpy → Xvfb → x11vnc → websockify → nginx → cloudflared → noVNC。
- 生效参数：540x960/240dpi、scrcpy `--max-size 540 --max-fps 30 --video-bit-rate 1M`、x11vnc `-wait 2 -defer 0`。
- 实测输入→画面：280–624 ms（中位 ~290），API RTT 1.0–1.9 s（含 adb 启动开销）。
- 两条无效/有害尝试：cloudflared `--protocol quic` 会让 WebSocket 连不上（noVNC 报 Failed to connect）；x11vnc 没有 `-threads` 选项，写了直接退出（表现为同一报错）。
- 判断 WS 是否正常：runner 上 `curl -H 'Upgrade: websocket' ... http://127.0.0.1:8080/websockify` 应 101；同时 `pgrep x11vnc` 必须 ≥1。
- 下一步空间：换 ws-scrcpy（浏览器直接收 H.264，跳过 Xvfb/x11vnc 两层），预计能把链路砍掉一半。

## 关键坑
- scrcpy 3.x 用 `--video-bit-rate`，`--bit-rate` 已移除。
- `-dns-server` 别加；Android shell 的 ping 不能当网络判据。
- job 未结束时 GitHub `/logs` 接口 404，页面扒日志会被反爬挡住 → 用 state 分支/contents API 传 URL。
- `/sdcard` 下 APK 不能直接 `pm install`（fuse 权限），先 `cp` 到 `/data/local/tmp`。
- 同一 ego taskSpace 的页面会被后台脚本抢占，测量和轮询要用不同 page 名。
- `adb install` 要求文件后缀 `.apk`/`.apex`，`/tmp/tiktok.bin` 会报 `filename doesn't end .apk`。
- 等 URL 别扒 GitHub job 页面（反爬后只剩 80 字符骨架），用 ntfy 或 state 分支。
- 网络等待不要用 `svc wifi enable` 反复拨，会把 wifi 拨断并让 phone 步骤卡 20 分钟；用 `dumpsys connectivity` 判 VALIDATED。
