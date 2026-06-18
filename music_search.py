"""
歌曲搜索模块
使用 YouTube + yt-dlp 搜索并下载音频
"""

import subprocess
import sys
import json
import time
import os
import tempfile
import shutil


def find_mpv():
    """查找 mpv 路径"""
    scoop_base = os.path.expanduser(r"~\scoop\apps\mpv")
    if os.path.exists(scoop_base):
        for folder in os.listdir(scoop_base):
            exe = os.path.join(scoop_base, folder, "mpv.exe")
            if os.path.exists(exe):
                return exe
    return shutil.which('mpv')


class MusicSearcher:
    def __init__(self):
        self._cache = {}
        self._temp_dir = os.path.join(tempfile.gettempdir(), 'jukebox')
        os.makedirs(self._temp_dir, exist_ok=True)
        self.mpv_path = find_mpv()
        self._downloading = False

    def search(self, query):
        """搜索歌曲并下载第一个候选，保留旧调用方式。"""
        cache_key = query
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached.get('time', 0) < 600:
                return cached['result']

        candidates = self.search_candidates(query, limit=1)
        result = self.download_candidate(candidates[0]) if candidates else None

        if result:
            self._cache[cache_key] = {
                'result': result,
                'time': time.time()
            }

        return result

    def search_candidates(self, query, limit=5):
        """用 yt-dlp 搜索 YouTube 候选，不下载音频。"""
        limit = max(1, min(int(limit or 5), 10))
        try:
            cmd = [
                sys.executable, '-m', 'yt_dlp',
                f'ytsearch{limit}:{query} music audio',
                '--dump-json',
                '--no-download',
                '--no-playlist',
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace',
                env={**os.environ, 'PYTHONHTTPSVERIFY': '0'}
            )

            if result.returncode != 0 or not result.stdout.strip():
                print(f"[搜索] yt-dlp 错误: {result.stderr[:200]}")
                return []

            candidates = []
            for line in result.stdout.strip().splitlines():
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                video_id = data.get('id', '')
                title = data.get('title', '')
                uploader = data.get('uploader', '') or data.get('channel', '')
                if not video_id or not title:
                    continue

                candidates.append({
                    'id': video_id,
                    'name': title,
                    'artist': uploader,
                    'duration': data.get('duration'),
                    'thumbnail': data.get('thumbnail') or '',
                    'webpage_url': data.get('webpage_url') or f'https://www.youtube.com/watch?v={video_id}',
                })

            return candidates

        except subprocess.TimeoutExpired:
            print("[搜索] 超时")
            return []
        except Exception as e:
            print(f"[搜索] 失败: {e}")
            return []

    def download_candidate(self, candidate):
        """下载选中的 YouTube 候选音频。"""
        if self._downloading:
            print("[搜索] 正在下载中，请稍候...")
            return None

        self._downloading = True

        try:
            video_id = candidate.get('id', '')
            title = candidate.get('name') or candidate.get('title', '')
            uploader = candidate.get('artist') or candidate.get('uploader', '')

            if not video_id:
                print("[搜索] 未找到视频")
                return None

            print(f"[搜索] 找到: {title} - {uploader}")

            # 下载音频到本地
            output_file = os.path.join(self._temp_dir, f"{video_id}.m4a")

            if os.path.exists(output_file) and os.path.getsize(output_file) > 100000:
                return {'name': title, 'artist': uploader, 'url': output_file}

            # 用 yt-dlp 直接下载（它会自动处理重定向和 cookies）
            print(f"[搜索] 下载中...")
            cmd = [
                sys.executable, '-m', 'yt_dlp',
                candidate.get('webpage_url') or f'https://www.youtube.com/watch?v={video_id}',
                '-f', 'bestaudio[ext=m4a]/bestaudio',
                '-o', output_file,
                '--no-playlist',
                '--quiet',
                '--no-warnings',
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                encoding='utf-8',
                errors='replace',
                env={**os.environ, 'PYTHONHTTPSVERIFY': '0'}
            )

            if os.path.exists(output_file) and os.path.getsize(output_file) > 100000:
                size_mb = os.path.getsize(output_file) / (1024 * 1024)
                print(f"[搜索] 完成: {size_mb:.1f} MB")
                return {'name': title, 'artist': uploader, 'url': output_file}

            print("[搜索] 下载失败")
            return None

        except subprocess.TimeoutExpired:
            print("[搜索] 超时")
            return None
        except Exception as e:
            print(f"[搜索] 失败: {e}")
            return None
        finally:
            self._downloading = False

    def search_youtube(self, query):
        """兼容旧方法名：搜索并下载第一个候选。"""
        candidates = self.search_candidates(query, limit=1)
        if not candidates:
            return None
        return self.download_candidate(candidates[0])


if __name__ == '__main__':
    searcher = MusicSearcher()
    result = searcher.search("稻香 周杰伦")
    print(f"结果: {result}")
