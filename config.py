# ============================================
# 办公室点歌台 - 配置文件
# 修改以下选项来自定义行为
# ============================================

# ========== 播放配置 ==========

# Windows 蓝牙音响设备名
# 查看设备名: python -c "import soundcard; [print(s.name) for s in soundcard.all_speakers()]"
# 留空则使用系统默认音频设备
BLUETOOTH_SPEAKER = ""

# 每首歌最长播放时间（秒），0 = 不限制（播完整首）
MAX_SONG_DURATION = 0

# 队列最多同时容纳多少首歌
MAX_QUEUE_SIZE = 500

# ========== 限制配置 ==========

# 每日每人最大点歌次数
MAX_SONGS_PER_USER_PER_DAY = 10

# 同一首歌两次播放之间的最小间隔（秒），防止重复点同一首歌
SAME_SONG_COOLDOWN = 3600

# ========== 缓存配置 ==========

# 下载音频缓存最大占用空间（MB）
CACHE_MAX_SIZE_MB = 2048

# 下载音频缓存最大保留天数
CACHE_MAX_AGE_DAYS = 14

# ========== 管理员配置 ==========

# 管理员密码（用于切歌、顶歌、删除、清空等操作）
# 建议用环境变量 WEBKARAOKE_ADMIN_PASSWORD 覆盖默认值
import os

ADMIN_PASSWORD = os.environ.get("WEBKARAOKE_ADMIN_PASSWORD", "123456")

# 管理员登录会话有效期（秒）
ADMIN_SESSION_TTL_SECONDS = 12 * 60 * 60

# 同一用户/IP 发起搜索或下载请求的最小间隔（秒）
REQUEST_RATE_LIMIT_SECONDS = 3

# ========== 网络配置 ==========

# 服务监听端口
PORT = 9800

# 服务绑定地址（0.0.0.0 = 所有网卡）
HOST = "0.0.0.0"
