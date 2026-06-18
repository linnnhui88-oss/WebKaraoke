# WebKaraoke - 办公室点歌台

## 项目概述
基于 Web 的办公室点歌系统，同事通过浏览器点歌，自动排队播放。

## 技术栈
- **后端**: Python + Flask
- **前端**: HTML + CSS + JavaScript（响应式，支持日间/夜间模式）
- **播放器**: mpv（通过 scoop 安装）
- **音频来源**: YouTube（通过 yt-dlp 下载音频）

## 文件结构
```
Webkaraoke/
├── app.py              # 主程序入口（Flask + 启动逻辑）
├── config.py           # 配置文件（限制、播放设置等）
├── music_search.py     # 歌曲搜索（yt-dlp 下载 YouTube 音频）
├── player.py           # mpv 播放器控制
├── queue_manager.py    # 队列管理 + 每日限制
├── requirements.txt    # Python 依赖
├── start.bat           # Windows 一键启动脚本
└── CLAUDE.md           # 本文件
```

## 快速开始

### 1. 安装依赖
```powershell
cd WebKaraoke
pip install -r requirements.txt
```

### 2. 安装 mpv
```powershell
scoop bucket add extras
scoop install mpv
```

### 3. 启动
```powershell
python app.py
```

### 4. 使用
- 浏览器打开 http://localhost:9800
- 输入歌名，点击"点歌"
- 歌曲自动下载并加入队列
- 队列中的歌曲会自动播放

## 配置说明

编辑 `config.py` 可自定义：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `MAX_SONGS_PER_USER_PER_DAY` | 每日每人限点 | 10 |
| `MAX_SONG_DURATION` | 每首歌最长播放时间(秒)，0 表示不限制 | 0 |
| `MAX_QUEUE_SIZE` | 队列最大容量 | 500 |
| `CACHE_MAX_SIZE_MB` | 下载音频缓存最大占用空间(MB) | 2048 |
| `CACHE_MAX_AGE_DAYS` | 下载音频缓存最大保留天数 | 14 |
| `BLUETOOTH_SPEAKER` | 蓝牙音响设备名 | 空(默认设备) |
| `ADMIN_SESSION_TTL_SECONDS` | 管理员登录有效期(秒) | 43200 |
| `REQUEST_RATE_LIMIT_SECONDS` | 同一用户/IP 同类请求最小间隔(秒) | 3 |

## 功能特性

- ✅ 浏览器点歌，自动排队
- ✅ 日间/夜间模式切换
- ✅ 播放历史记录
- ✅ 点歌日志
- ✅ 每日点歌限制
- ✅ 队列管理（删除、跳过）
- ✅ 响应式设计（手机/电脑适配）

## 注意事项

1. **音频来源**: 使用 YouTube 搜索，需要网络能访问 YouTube
2. **下载限制**: 单个音频文件限制 5MB
3. **缓存**: 下载的音频保存在 `%TEMP%\jukebox\` 目录，会按配置自动复用和清理
4. **mpv 路径**: 自动搜索 scoop 安装路径

## 常见问题

**Q: 搜索失败？**
A: 检查网络是否能访问 YouTube，检查 yt-dlp 是否安装

**Q: 没有声音？**
A: 检查 mpv 是否安装，检查系统音量

**Q: 下载卡住？**
A: 当前只允许一个下载任务，等待当前下载完成后再点下一首

## 开发历史

- 2026-06-13: 初始版本，从企业微信点歌机器人改为 Web 版
