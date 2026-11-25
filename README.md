# cloud-phone

在 GitHub Actions 免费 runner 上起一台 Android 14 模拟器（Pixel 6），用 scrcpy 镜像到虚拟桌面（Xvfb + x11vnc + noVNC），经 cloudflared 快速隧道给出浏览器地址。本机只开一个网页标签，不占内存。

## 用法

```bash
./phone.sh 45        # 起一台，约 4 分钟后打印链接
```

或直接：

```bash
gh workflow run cloud-phone.yml -R wflydream/cloud-phone -f minutes=45
```

链接在 run 的 Summary 和日志 `OPEN:` 行里，每次随机。浏览器打开后打开即连：鼠标=手指，拖动=滑动，滚轮=滚动。

## 限制

- 单次最长约 55 分钟（job 上限 70 分钟，模拟器启动 ~4 分钟），到期机器连同数据销毁。
- 隧道无密码：拿到 URL 的人都能操作这台机器。只发给自己；需要更安全就换 Tailscale 私有网 + 本机 scrcpy，或给 x11vnc 加 `-rfbauth`。
- google_apis 镜像无 Play 商店；送 F-Droid 用。
