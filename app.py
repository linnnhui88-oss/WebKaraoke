"""
办公室点歌台 - 主程序
Web 版点歌系统，浏览器打开即用
"""

import sys
import os
import socket
import threading
import time
import uuid
from flask import Flask, request, jsonify, render_template

from config import *
from queue_manager import QueueManager
from player import MusicPlayer
from music_search import MusicSearcher


# ==================== 编码兼容 ====================

def safe_print(*args, **kwargs):
    """兼容 Windows GBK 终端的打印函数，遇到无法编码的字符时自动替换"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        text = ' '.join(str(a) for a in args)
        # 替换常见 emoji
        replacements = {
            '✅': '[OK]', '❌': '[FAIL]', '⚠️': '[!]',
            '🎵': '', '📋': '', '📜': '', '▶️': '',
            '⏭️': '', '⏱️': '', '📍': '', '📊': '',
            '🔍': '', '🔄': '', '🌙': '', '☀️': '',
        }
        for emoji, replacement in replacements.items():
            text = text.replace(emoji, replacement)
        print(text, **kwargs)


# ==================== 管理员鉴权 ====================

def require_admin():
    """验证请求是否来自管理员，返回 None 通过，或返回错误响应"""
    token = request.headers.get('X-Admin-Token', '')
    if token != ADMIN_PASSWORD:
        return jsonify({'ok': False, 'error': '需要管理员权限'}), 403
    return None


# ==================== 初始化 ====================

app = Flask(__name__)

queue_mgr = QueueManager()
player = MusicPlayer()
searcher = MusicSearcher()
tasks_lock = threading.RLock()
download_tasks = {}


def create_task(user_id, user_name, candidate):
    task_id = uuid.uuid4().hex
    now = time.time()
    task = {
        'id': task_id,
        'user_id': user_id,
        'user_name': user_name,
        'candidate': candidate,
        'status': 'pending',
        'message': '等待下载',
        'created_at': now,
        'updated_at': now,
    }
    with tasks_lock:
        download_tasks[task_id] = task
        cleanup_tasks_locked()
    return task


def update_task(task_id, status, message, **extra):
    with tasks_lock:
        task = download_tasks.get(task_id)
        if not task:
            return
        task.update(extra)
        task['status'] = status
        task['message'] = message
        task['updated_at'] = time.time()


def cleanup_tasks_locked():
    if len(download_tasks) <= 50:
        return
    oldest = sorted(download_tasks.values(), key=lambda item: item['created_at'])
    for task in oldest[:-50]:
        download_tasks.pop(task['id'], None)


def public_task(task):
    candidate = task.get('candidate') or {}
    return {
        'id': task.get('id'),
        'status': task.get('status'),
        'message': task.get('message'),
        'song_name': candidate.get('name', ''),
        'artist': candidate.get('artist', ''),
        'user_name': task.get('user_name', '匿名'),
        'created_at': task.get('created_at'),
        'updated_at': task.get('updated_at'),
    }

# ==================== 前端页面 ====================

# ==================== 路由 ====================

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/search', methods=['POST'])
def api_search():
    """搜索歌曲候选，不立即下载。"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        user_id = data.get('user_id', '')

        print(f"[搜索] 收到请求: query={query}")

        if not query:
            return jsonify({'ok': False, 'error': '请输入歌名'})

        # 检查每日限制
        count = queue_mgr.get_today_count(user_id)
        if count >= MAX_SONGS_PER_USER_PER_DAY:
            return jsonify({
                'ok': False,
                'error': f'你今天已经点了 {count} 首歌，达到上限了！'
            })

        # 检查是否正在下载
        if searcher._downloading:
            return jsonify({
                'ok': False,
                'error': '正在下载中，请稍候再试...'
            })

        candidates = searcher.search_candidates(query, limit=5)
        if not candidates:
            return jsonify({'ok': False, 'error': '没有找到可用歌曲'})

        return jsonify({
            'ok': True,
            'candidates': candidates,
            'remaining': queue_mgr.get_today_remaining(user_id)
        })

    except Exception as e:
        import traceback
        print(f"[搜索] 异常: {e}")
        traceback.print_exc()
        return jsonify({'ok': False, 'error': f'搜索失败: {str(e)}'}), 500


@app.route('/api/request', methods=['POST'])
def api_request():
    """下载选中的候选并加入队列。"""
    try:
        data = request.json
        candidate = data.get('candidate') or {}
        user_id = data.get('user_id', '')
        user_name = data.get('user_name', '匿名')

        if not candidate.get('id'):
            return jsonify({'ok': False, 'error': '请选择歌曲'})

        count = queue_mgr.get_today_count(user_id)
        if count >= MAX_SONGS_PER_USER_PER_DAY:
            return jsonify({
                'ok': False,
                'error': f'你今天已经点了 {count} 首歌，达到上限了！'
            })

        if searcher._downloading:
            return jsonify({
                'ok': False,
                'error': '正在下载中，请稍候再试...'
            })

        task = create_task(user_id, user_name, candidate)

        def do_download():
            update_task(task['id'], 'downloading', '正在下载音频')
            result = searcher.download_candidate(candidate)
            if not result:
                update_task(task['id'], 'failed', '下载失败，请换一个候选或稍后重试')
                return

            try:
                was_empty = len(queue_mgr.get_queue()) == 0 and not player.is_playing
                song = queue_mgr.add_to_queue(
                    user_id=user_id,
                    song_name=result['name'],
                    artist=result['artist'],
                    url=result['url'],
                    user_name=user_name
                )
                if song:
                    update_task(task['id'], 'queued', '已加入播放队列', song_id=song['id'])
                    if was_empty:
                        player.skip_event.set()
                        print(f"[搜索] 立即播放: {result['name']}")
                    else:
                        print(f"[搜索] 已加入队列: {result['name']}")
                else:
                    update_task(task['id'], 'failed', '加入队列失败，可能已达到限制')
            except Exception as exc:
                update_task(task['id'], 'failed', f'加入队列失败: {exc}')

        thread = threading.Thread(target=do_download, daemon=True)
        thread.start()

        return jsonify({
            'ok': True,
            'task': public_task(task),
            'message': '正在下载，完成后将自动加入队列',
            'remaining': queue_mgr.get_today_remaining(user_id)
        })

    except Exception as e:
        import traceback
        print(f"[点歌] 异常: {e}")
        traceback.print_exc()
        return jsonify({'ok': False, 'error': f'点歌失败: {str(e)}'}), 500


@app.route('/api/tasks', methods=['GET'])
def api_tasks():
    """查看最近下载任务。"""
    user_id = request.args.get('user_id', '')
    with tasks_lock:
        tasks = list(download_tasks.values())
    if user_id:
        tasks = [task for task in tasks if task.get('user_id') == user_id]
    tasks.sort(key=lambda item: item.get('created_at', 0), reverse=True)
    return jsonify({
        'tasks': [public_task(task) for task in tasks[:10]]
    })


@app.route('/api/queue', methods=['GET'])
def api_queue():
    """查看当前队列"""
    user_id = request.args.get('user_id', '')
    return jsonify({
        'queue': queue_mgr.get_queue(),
        'current': player.get_status(),
        'stats': queue_mgr.get_stats(user_id)
    })


@app.route('/api/history', methods=['GET'])
def api_history():
    """查看播放历史"""
    limit = request.args.get('limit', 20, type=int)
    return jsonify({
        'history': queue_mgr.get_history(limit)
    })


@app.route('/api/admin/login', methods=['POST'])
def api_admin_login():
    """管理员登录，验证密码"""
    data = request.json
    password = data.get('password', '')
    if password == ADMIN_PASSWORD:
        return jsonify({'ok': True, 'token': ADMIN_PASSWORD})
    return jsonify({'ok': False, 'error': '密码错误'}), 401


@app.route('/api/remove', methods=['POST'])
def api_remove():
    """从队列移除歌曲（管理员可删任意，普通用户只能删自己的）"""
    data = request.json
    song_id = data.get('song_id')
    user_id = data.get('user_id', '')

    if song_id:
        # 检查权限：管理员 token 或歌曲所有者
        admin_err = require_admin()
        if admin_err is None:
            # 管理员，可以删除任意歌曲
            queue_mgr.remove_song(song_id)
        else:
            # 非管理员，只能删除自己的歌曲
            song = queue_mgr.get_song(song_id)
            if song and song.get('user_id') == user_id:
                queue_mgr.remove_song(song_id)
            else:
                return jsonify({'ok': False, 'error': '只能删除自己点的歌'}), 403

    return jsonify({'ok': True})


@app.route('/api/move_top', methods=['POST'])
def api_move_top():
    """将歌曲移到队列最前面（管理员专用）"""
    admin_err = require_admin()
    if admin_err:
        return admin_err

    data = request.json
    song_id = data.get('song_id')
    if song_id:
        queue_mgr.move_to_top(song_id)
    return jsonify({'ok': True})


@app.route('/api/skip', methods=['POST'])
def api_skip():
    """跳过当前歌曲（管理员专用）"""
    admin_err = require_admin()
    if admin_err:
        return admin_err
    player.skip_current()
    return jsonify({'ok': True})


@app.route('/api/clear', methods=['POST'])
def api_clear():
    """清空队列（管理员专用）"""
    admin_err = require_admin()
    if admin_err:
        return admin_err
    queue_mgr.clear_queue()
    return jsonify({'ok': True})


# ==================== 启动 ====================

def print_banner():
    safe_print("""
╔══════════════════════════════════════╗
║       🎵 办公室点歌台 🎵              ║
╠══════════════════════════════════════╣
║                                      ║
║  正在启动...                          ║
║                                      ║
╚══════════════════════════════════════╝
""")


def get_lan_ip():
    """尽量获取当前机器的局域网 IP，失败时回退到 127.0.0.1。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def main():
    print_banner()

    if not player.mpv_available:
        safe_print("[!] 未检测到 mpv 播放器！")
        safe_print("   安装: scoop bucket add extras && scoop install mpv")
        safe_print("   或从 https://mpv.io 下载")
        safe_print()
        input("按回车继续（播放功能将不可用）...")

    # 启动播放线程
    player_thread = threading.Thread(
        target=player.play_loop,
        args=(queue_mgr,),
        daemon=True
    )
    player_thread.start()
    safe_print("[主程序] 播放线程已启动")

    # 启动 Flask
    safe_print(f"[主程序] 点歌台地址: http://localhost:{PORT}")
    safe_print(f"[主程序] 局域网地址: http://{get_lan_ip()}:{PORT}")
    safe_print()
    safe_print("[主程序] [OK] 点歌台已就绪！")
    safe_print("[主程序] 让同事在浏览器打开上面的地址即可点歌")
    safe_print()

    app.run(
        host=HOST,
        port=PORT,
        debug=False,
        use_reloader=False
    )


if __name__ == '__main__':
    main()
