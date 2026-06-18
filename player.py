"""
播放器模块
使用 mpv 播放音乐，支持指定蓝牙音频设备
"""

import subprocess
import time
import threading
import os
import shutil
from config import BLUETOOTH_SPEAKER, MAX_SONG_DURATION


def find_mpv():
    """
    查找 mpv 可执行文件的路径
    """
    # 搜索常见路径
    common_paths = [
        os.path.expanduser(r"~\scoop\apps\mpv\current\mpv.exe"),
        os.path.expanduser(r"~\scoop\apps\mpv\0.41.0\mpv.exe"),
        os.path.expanduser(r"~\scoop\shims\mpv.exe"),
        r"C:\Program Files\mpv\mpv.exe",
        r"C:\Program Files (x86)\mpv\mpv.exe",
        r"D:\Program Files\mpv\mpv.exe",
    ]

    # 也搜索 scoop 下所有版本
    scoop_base = os.path.expanduser(r"~\scoop\apps\mpv")
    if os.path.exists(scoop_base):
        for folder in os.listdir(scoop_base):
            exe = os.path.join(scoop_base, folder, "mpv.exe")
            if os.path.exists(exe):
                common_paths.insert(0, exe)

    for path in common_paths:
        if os.path.exists(path):
            return path

    # 最后尝试系统 PATH
    mpv_path = shutil.which('mpv')
    if mpv_path:
        return mpv_path

    return None


class MusicPlayer:
    def __init__(self):
        self.current_process = None
        self.current_song = None
        self.is_playing = False
        self.stop_event = threading.Event()
        self.skip_event = threading.Event()
        self._lock = threading.Lock()
        self.mpv_path = None
        self.mpv_available = False

        # 检查 mpv 是否可用
        self._check_mpv()

    def _check_mpv(self):
        """检查 mpv 是否已安装"""
        self.mpv_path = find_mpv()

        if self.mpv_path:
            try:
                result = subprocess.run(
                    [self.mpv_path, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version = result.stdout.split('\n')[0]
                    print(f"[播放器] mpv 已找到: {version}")
                    print(f"[播放器] 路径: {self.mpv_path}")
                    self.mpv_available = True
                else:
                    print("[播放器] ⚠️ mpv 版本检查失败")
                    self.mpv_available = False
            except Exception as e:
                print(f"[播放器] 检查 mpv 失败: {e}")
                self.mpv_available = False
        else:
            print("[播放器] ⚠️ 未找到 mpv！")
            print("[播放器] 安装方法: scoop bucket add extras && scoop install mpv")
            print("[播放器] 或下载: https://mpv.io/installation/")
            self.mpv_available = False

    def play_loop(self, queue_mgr):
        """
        常驻播放循环
        从队列取歌并自动播放
        """
        print("[播放器] 播放线程已启动，等待歌曲...")

        while not self.stop_event.is_set():
            # 从队列取下一首
            next_song = queue_mgr.pop_next()

            if next_song:
                self._play_song(next_song)
            else:
                # 队列空，等待新歌曲或退出
                self.skip_event.wait(timeout=2)
                self.skip_event.clear()

        print("[播放器] 播放线程已停止")

    def _play_song(self, song):
        """播放一首歌"""
        if not self.mpv_available:
            print(f"[播放器] ⚠️ mpv 不可用，跳过: {song['name']}")
            return

        with self._lock:
            self.current_song = song
            self.is_playing = True

        print(f"▶️ 正在播放: {song['name']} - {song['artist']} "
              f"(点歌人: {song.get('user_name', '未知')})")

        try:
            # 构建 mpv 命令
            cmd = [
                self.mpv_path,
                '--no-video',                    # 无视频
                '--no-terminal',                 # 无终端控制界面
                '--really-quiet',                # 静默输出
            ]

            # 指定音频设备（蓝牙音响）
            if BLUETOOTH_SPEAKER:
                cmd.extend([
                    f'--audio-device=wasapi/{BLUETOOTH_SPEAKER}',
                ])

            # 限制播放时长
            if MAX_SONG_DURATION > 0:
                cmd.extend([f'--length={MAX_SONG_DURATION}'])

            # 单曲循环关闭，播完自动结束
            cmd.append('--loop=no')

            # 播放地址
            cmd.append(song['url'])

            # 启动播放进程
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )

            # 等待播放完成
            start_time = time.time()
            max_wait = (MAX_SONG_DURATION if MAX_SONG_DURATION > 0 else 600) + 30

            while self.current_process.poll() is None:
                # 检查是否被要求跳过
                if self.skip_event.is_set():
                    print(f"⏭️ 跳过: {song['name']}")
                    self.current_process.kill()
                    self.skip_event.clear()
                    break

                # 检查是否被要求停止
                if self.stop_event.is_set():
                    self.current_process.kill()
                    break

                # 超时保护
                if time.time() - start_time > max_wait:
                    print(f"⏱️ 超时，强制结束: {song['name']}")
                    self.current_process.kill()
                    break

                time.sleep(0.5)

        except Exception as e:
            print(f"[播放器] 播放异常: {e}")

        finally:
            with self._lock:
                self.current_process = None
                self.current_song = None
                self.is_playing = False

    def skip_current(self):
        """跳过当前歌曲"""
        self.skip_event.set()

    def stop(self):
        """停止播放"""
        self.stop_event.set()
        self.skip_event.set()
        if self.current_process:
            try:
                self.current_process.kill()
            except:
                pass

    def get_status(self):
        """获取当前播放状态"""
        return {
            'is_playing': self.is_playing,
            'current_song': self.current_song,
        }


# 测试
if __name__ == '__main__':
    player = MusicPlayer()

    if player.mpv_available:
        # 测试播放一首 YouTube 歌曲
        test_song = {
            'name': '测试歌曲',
            'artist': '测试歌手',
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        }
        player._play_song(test_song)
        print("测试完成")
    else:
        print("mpv 未安装，无法测试播放")
