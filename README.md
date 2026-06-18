# 办公室点歌台

基于 Web 的办公室点歌系统，同事通过浏览器点歌，自动排队播放。

## 功能

- 浏览器点歌，自动排队
- 日间/夜间模式切换
- 播放历史记录
- 点歌日志
- 每日点歌限制
- 队列管理（删除歌曲）
- 响应式设计（手机/电脑适配）

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Python + Flask |
| 前端 | HTML + CSS + JavaScript（响应式，支持日间/夜间模式） |
| 播放器 | mpv（通过 scoop 安装） |
| 音频来源 | YouTube（通过 yt-dlp 下载音频） |

## 快速开始

### 1. 安装依赖

```powershell
cd WebKaraoke
pip install -r requirements.txt
```

可选：启动前设置管理员密码环境变量，避免使用默认密码：

```powershell
$env:WEBKARAOKE_ADMIN_PASSWORD="你的强密码"
```

### 2. 安装 mpv 播放器

```powershell
scoop bucket add extras
scoop install mpv
```

如果 scoop 安装失败，也可以从 [mpv.io](https://mpv.io/installation/) 下载安装。

### 3. 启动

```powershell
python app.py
```

或者在 Windows 上直接双击 `start.bat` 一键启动。

### 4. 使用

- 浏览器打开 http://localhost:9800
- 输入歌名，点击"点歌"
- 歌曲自动下载并加入队列
- 队列中的歌曲会自动播放

## 文件结构

```
WebKaraoke/
├── app.py              # 主程序入口（Flask + 启动逻辑）
├── config.py           # 配置文件（限制、播放设置等）
├── music_search.py     # 歌曲搜索（yt-dlp 下载 YouTube 音频）
├── player.py           # mpv 播放器控制
├── queue_manager.py    # 队列管理 + 每日限制
├── requirements.txt    # Python 依赖
├── start.bat           # Windows 一键启动脚本
├── daily_counts.json   # 每日点歌计数（自动生成）
├── play_history.json   # 播放历史（自动生成）
└── playlist.json       # 当前队列（自动生成）
```

## 配置说明

编辑 `config.py` 可自定义：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `MAX_SONGS_PER_USER_PER_DAY` | 每日每人限点 | 10 |
| `MAX_SONG_DURATION` | 每首歌最长播放时间(秒)，0 表示不限制 | 0 |
| `MAX_QUEUE_SIZE` | 队列最大容量 | 500 |
| `SAME_SONG_COOLDOWN` | 同一首歌最小间隔(秒) | 3600 |
| `CACHE_MAX_SIZE_MB` | 下载音频缓存最大占用空间(MB) | 2048 |
| `CACHE_MAX_AGE_DAYS` | 下载音频缓存最大保留天数 | 14 |
| `BLUETOOTH_SPEAKER` | 蓝牙音响设备名 | 空(默认设备) |
| `WEBKARAOKE_ADMIN_PASSWORD` | 管理员密码环境变量 | 123456 |
| `ADMIN_SESSION_TTL_SECONDS` | 管理员登录有效期(秒) | 43200 |
| `REQUEST_RATE_LIMIT_SECONDS` | 同一用户/IP 同类请求最小间隔(秒) | 3 |
| `PORT` | 服务端口 | 9800 |

### 配置蓝牙音响

查看音频设备名：

```powershell
pip install soundcard
python -c "import soundcard; [print(s.name) for s in soundcard.all_speakers()]"
```

把设备名填入 `config.py` 的 `BLUETOOTH_SPEAKER`。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 主页面 |
| POST | `/api/search` | 搜索并点歌，参数：`{query, user_id, user_name}` |
| GET | `/api/queue` | 获取当前队列和播放状态 |
| GET | `/api/history` | 获取播放历史，参数：`?limit=20` |
| POST | `/api/remove` | 删除队列中的歌曲，参数：`{song_id}` |
| POST | `/api/skip` | 跳过当前歌曲 |
| POST | `/api/clear` | 清空队列 |

## 注意事项

1. 音频来源使用 YouTube，需要网络能访问 YouTube
2. 下载的音频保存在 `%TEMP%\jukebox\` 目录，会按配置自动复用和清理
3. 当前只允许一个下载任务，需要等待当前下载完成后再点下一首
4. mpv 路径会自动搜索 scoop 安装路径

## 常见问题

**Q: 搜索失败？**
A: 检查网络是否能访问 YouTube，检查 yt-dlp 是否安装。可以手动测试：
```powershell
python -m yt_dlp --version
```

**Q: 没有声音？**
A: 检查 mpv 是否安装，检查系统音量。确认 `config.py` 中 `BLUETOOTH_SPEAKER` 设备名正确。

**Q: 下载卡住？**
A: 当前只允许一个下载任务，等待当前下载完成后再点下一首。

**Q: 如何重启服务？**
A: 直接关闭终端重新运行 `python app.py` 即可。队列和历史数据会自动保留。

## 开发历史

- 2026-06-13: 初始版本，从企业微信点歌机器人改为 Web 版
