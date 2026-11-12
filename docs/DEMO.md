# 录一段 20 秒的 demo GIF

仓库首页的 GIF 是 star 转化率最高的单个资产：陌生人给你 8 秒，GIF 决定他点不点 star。

## 录制内容（严格按这个顺序，别加片头）

| 秒 | 画面 | 目的 |
| --- | --- | --- |
| 0-3 | RViz：地图 + 机器人 + Nav2 全局路径 | 证明"真的在跑" |
| 3-12 | 机器人穿过货架通道，避障/绕行 | 证明不是静态贴图 |
| 12-17 | 终端滚出 `mission/state` 的 JSON 迁移日志 | 证明有任务层，不只是 turtlebot3 demo |
| 17-20 | `mission/report` 一行总结（success + 耗时） | 证明有度量 |

## 环境准备

```bash
sudo apt install -y ffmpeg

# 1. 起全栈（本机，不要 headless）
ros2 launch warehouse_amr_description bringup_sim.launch.py
# 2. 任务跑起来
ros2 launch warehouse_amr_mission mission.launch.py \
    metrics_path:=/tmp/amr_missions.jsonl
```

## 录制

```bash
# 录 RViz 窗口（x11grab，按实际分辨率和位置调整）
ffmpeg -f x11grab -framerate 30 -video_size 1920x1080 -i :0.0+0,0 \
       -t 20 -c:v libx264 -preset ultrafast -crf 23 /tmp/demo.mp4

# 剪掉开头等待 Nav2 lifecycle 的空窗，转 GIF
ffmpeg -ss 8 -i /tmp/demo.mp4 -t 20 \
       -vf "fps=12,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" \
       docs/media/demo.gif

ls -lh docs/media/demo.gif   # 目标 < 8 MB，超过就降 fps 到 10 或宽到 800
```

Wayland 桌面用 `wf-recorder`；macOS 用 `screencapture -V 20 -x /tmp/demo.mov`。

## 放到 README

```markdown
![warehouse AMR demo](docs/media/demo.gif)
```

## 社交预览图（GitHub 仓库右上角的卡片）

`Settings → General → Social preview` 上传 1280×640 的 PNG。用 RViz 截图 + 一句
`ROS 2 Humble · Nav2 · 任务状态机 · 可复现基准` 拼一张即可，比默认头像点击率高得多。
