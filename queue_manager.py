"""
队列管理模块
管理播放队列、每日点歌限制、播放历史
"""

import json
import os
import time
from datetime import datetime, date
from config import MAX_SONGS_PER_USER_PER_DAY, MAX_QUEUE_SIZE, SAME_SONG_COOLDOWN

QUEUE_FILE = "playlist.json"
HISTORY_FILE = "play_history.json"
DAILY_FILE = "daily_counts.json"


class QueueManager:
    def __init__(self):
        self._lock = False  # 简单项目不需要真锁
        self.queue = []
        self.daily_counts = {}  # {date_str: {user_id: count}}
        self.played_songs = []  # 用于冷却检测
        self._load_all()

    def _load_all(self):
        """加载所有数据"""
        # 加载队列
        try:
            if os.path.exists(QUEUE_FILE):
                with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
                    self.queue = json.load(f)
        except Exception as e:
            print(f"[队列] 加载队列失败: {e}")
            self.queue = []

        # 加载每日计数
        try:
            if os.path.exists(DAILY_FILE):
                with open(DAILY_FILE, 'r', encoding='utf-8') as f:
                    self.daily_counts = json.load(f)
        except Exception as e:
            print(f"[队列] 加载每日计数失败: {e}")
            self.daily_counts = {}

        # 清理过期的每日计数（只保留最近7天）
        self._cleanup_old_counts()

    def _save_queue(self):
        """保存队列到文件"""
        try:
            with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.queue, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[队列] 保存队列失败: {e}")

    def _save_daily_counts(self):
        """保存每日计数到文件"""
        try:
            with open(DAILY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.daily_counts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[队列] 保存每日计数失败: {e}")

    def _cleanup_old_counts(self):
        """清理过期的每日计数"""
        today = date.today()
        keys_to_remove = []
        for date_str in self.daily_counts:
            try:
                d = date.fromisoformat(date_str)
                if (today - d).days > 7:
                    keys_to_remove.append(date_str)
            except:
                keys_to_remove.append(date_str)

        for key in keys_to_remove:
            del self.daily_counts[key]

        if keys_to_remove:
            self._save_daily_counts()

    def _today_str(self):
        """获取今天的日期字符串"""
        return date.today().isoformat()

    # ==================== 队列操作 ====================

    def add_to_queue(self, user_id, song_name, artist, url, user_name=None):
        """
        添加歌曲到队列
        返回: song dict 或 None（如果被拒绝）
        """
        # 检查每日限制
        if not self._check_daily_limit(user_id):
            return None

        # 检查队列是否已满
        if len(self.queue) >= MAX_QUEUE_SIZE:
            return None

        # 检查冷却（同一首歌不能太频繁）
        if not self._check_cooldown(song_name, artist):
            return None

        song = {
            'id': int(time.time() * 1000),
            'user_id': user_id,
            'user_name': user_name or user_id,
            'name': song_name,
            'artist': artist,
            'url': url,
            'time': datetime.now().isoformat()
        }

        self.queue.append(song)
        self._save_queue()

        # 增加每日计数
        self._increment_daily_count(user_id)

        return song

    def pop_next(self):
        """取出队列中的下一首歌"""
        if not self.queue:
            return None

        song = self.queue.pop(0)
        self._save_queue()

        # 记录历史
        self._add_to_history(song)

        return song

    def get_queue(self):
        """获取当前队列（返回副本）"""
        return list(self.queue)

    def get_queue_position(self, song_id):
        """获取歌曲在队列中的位置（从1开始）"""
        for i, song in enumerate(self.queue):
            if song['id'] == song_id:
                return i + 1
        return -1

    def clear_queue(self):
        """清空队列"""
        self.queue = []
        self._save_queue()

    def get_song(self, song_id):
        """根据 ID 获取歌曲信息"""
        for song in self.queue:
            if song['id'] == song_id:
                return song
        return None

    def remove_song(self, song_id):
        """从队列中移除指定歌曲"""
        self.queue = [s for s in self.queue if s['id'] != song_id]
        self._save_queue()

    def move_to_top(self, song_id):
        """将歌曲移到队列最前面"""
        for i, song in enumerate(self.queue):
            if song['id'] == song_id:
                self.queue.insert(0, self.queue.pop(i))
                self._save_queue()
                return True
        return False

    # ==================== 每日限制 ====================

    def _check_daily_limit(self, user_id):
        """检查用户是否超过每日限制"""
        today = self._today_str()
        user_counts = self.daily_counts.get(today, {})
        count = user_counts.get(user_id, 0)
        return count < MAX_SONGS_PER_USER_PER_DAY

    def _increment_daily_count(self, user_id):
        """增加用户今日点歌计数"""
        today = self._today_str()
        if today not in self.daily_counts:
            self.daily_counts[today] = {}

        current = self.daily_counts[today].get(user_id, 0)
        self.daily_counts[today][user_id] = current + 1
        self._save_daily_counts()

    def get_today_count(self, user_id):
        """获取用户今日点歌次数"""
        today = self._today_str()
        user_counts = self.daily_counts.get(today, {})
        return user_counts.get(user_id, 0)

    def get_today_remaining(self, user_id):
        """获取用户今日剩余可点次数"""
        return MAX_SONGS_PER_USER_PER_DAY - self.get_today_count(user_id)

    # ==================== 冷却检测 ====================

    def _check_cooldown(self, song_name, artist):
        """检查歌曲是否在冷却期（防止刷屏同一首歌）"""
        now = time.time()
        for played in self.played_songs:
            if (played['name'] == song_name and
                played['artist'] == artist and
                now - played['time'] < SAME_SONG_COOLDOWN):
                return False  # 还在冷却期
        return True

    # ==================== 播放历史 ====================

    def _add_to_history(self, song):
        """添加到播放历史"""
        try:
            history = []
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    history = json.load(f)

            history.append({
                **song,
                'played_at': datetime.now().isoformat()
            })

            # 只保留最近 200 条
            history = history[-200:]

            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)

            # 同时更新冷却列表
            self.played_songs.append({
                'name': song['name'],
                'artist': song['artist'],
                'time': time.time()
            })
            # 只保留最近 50 条冷却记录
            self.played_songs = self.played_songs[-50:]

        except Exception as e:
            print(f"[队列] 保存历史失败: {e}")

    def get_history(self, limit=20):
        """获取最近播放历史"""
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                return history[-limit:]
        except:
            pass
        return []

    # ==================== 统计 ====================

    def get_stats(self, user_id=None):
        """获取统计信息"""
        today = self._today_str()
        today_counts = self.daily_counts.get(today, {})
        remaining = MAX_SONGS_PER_USER_PER_DAY
        if user_id:
            remaining = self.get_today_remaining(user_id)

        return {
            'queue_length': len(self.queue),
            'today_total': sum(today_counts.values()),
            'today_users': len(today_counts),
            'max_per_user': MAX_SONGS_PER_USER_PER_DAY,
            'remaining': remaining,
        }


# 测试
if __name__ == '__main__':
    qm = QueueManager()

    # 模拟点歌
    song = qm.add_to_queue(
        user_id="user_001",
        song_name="稻香",
        artist="周杰伦",
        url="https://example.com/daoxiang.mp3",
        user_name="张三"
    )

    if song:
        pos = qm.get_queue_position(song['id'])
        print(f"点歌成功！队列位置: {pos}")
    else:
        print("点歌被拒绝")

    print(f"今日已点: {qm.get_today_count('user_001')}/10")
    print(f"今日剩余: {qm.get_today_remaining('user_001')}")
    print(f"统计: {qm.get_stats()}")
