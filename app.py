"""
办公室点歌台 - 主程序
Web 版点歌系统，浏览器打开即用
"""

import sys
import os
import socket
import threading
import time
from flask import Flask, request, jsonify, render_template_string

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

# ==================== 前端页面 ====================

HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎵 办公室点歌台</title>
    <style>
        :root {
            --bg: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            --text: #fff;
            --text-secondary: #888;
            --card-bg: rgba(255,255,255,0.03);
            --card-hover: rgba(255,255,255,0.08);
            --border: rgba(255,255,255,0.1);
            --accent: #e94560;
            --accent2: #f39c12;
            --input-bg: rgba(255,255,255,0.1);
            --toast-success: #27ae60;
            --toast-error: #e74c3c;
        }

        [data-theme="light"] {
            --bg: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 50%, #d1d8e0 100%);
            --text: #333;
            --text-secondary: #666;
            --card-bg: rgba(0,0,0,0.03);
            --card-hover: rgba(0,0,0,0.08);
            --border: rgba(0,0,0,0.1);
            --input-bg: rgba(0,0,0,0.05);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            min-height: 100vh;
            color: var(--text);
            transition: all 0.3s ease;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            padding: 30px 0;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #e94560, #f39c12);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .header p {
            color: var(--text-secondary);
            font-size: 0.9em;
        }

        .search-box {
            display: flex;
            gap: 10px;
            margin: 20px 0;
        }

        .search-box input {
            flex: 1;
            padding: 15px 20px;
            border: 2px solid var(--border);
            border-radius: 25px;
            font-size: 1em;
            background: var(--input-bg);
            color: var(--text);
            outline: none;
            transition: all 0.3s;
        }

        .search-box input:focus {
            border-color: var(--accent);
        }

        .search-box input::placeholder {
            color: var(--text-secondary);
        }

        .search-box button {
            padding: 15px 30px;
            border: none;
            border-radius: 25px;
            background: linear-gradient(90deg, #e94560, #f39c12);
            color: var(--text);
            font-size: 1em;
            cursor: pointer;
            transition: transform 0.2s;
        }

        .search-box button:hover {
            transform: scale(1.05);
        }

        .search-box button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .current-play {
            background: var(--card-bg);
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            display: none;
        }

        .current-play.active {
            display: block;
        }

        .current-play .label {
            font-size: 0.8em;
            color: #e94560;
            margin-bottom: 5px;
        }

        .current-play .song-name {
            font-size: 1.5em;
            font-weight: bold;
        }

        .current-play .artist {
            color: var(--text-secondary);
            margin-top: 5px;
        }

        .section-title {
            font-size: 1.2em;
            margin: 30px 0 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border);
        }

        .queue-list {
            list-style: none;
        }

        .queue-item {
            display: flex;
            align-items: center;
            padding: 15px;
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
            margin-bottom: 10px;
            transition: background 0.2s;
        }

        .queue-item:hover {
            background: rgba(255,255,255,0.08);
        }

        .queue-item .num {
            width: 30px;
            height: 30px;
            background: rgba(233,69,96,0.2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 15px;
            font-size: 0.9em;
            color: #e94560;
        }

        .queue-item .info {
            flex: 1;
        }

        .queue-item .name {
            font-weight: bold;
        }

        .queue-item .meta {
            font-size: 0.85em;
            color: var(--text-secondary);
            margin-top: 3px;
        }

        .queue-item .actions {
            display: flex;
            gap: 5px;
        }

        .queue-item .actions button {
            padding: 5px 10px;
            border: none;
            border-radius: 5px;
            background: rgba(255,255,255,0.1);
            color: var(--text);
            cursor: pointer;
            font-size: 0.8em;
        }

        .queue-item .actions button:hover {
            background: rgba(255,255,255,0.2);
        }

        .empty-queue {
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
        }

        .stats {
            display: flex;
            gap: 20px;
            margin-top: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
        }

        .stats .stat-item {
            flex: 1;
            text-align: center;
        }

        .stats .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #e94560;
        }

        .stats .stat-label {
            font-size: 0.8em;
            color: var(--text-secondary);
            margin-top: 5px;
        }

        .section {
            margin-top: 30px;
        }

        .section-title {
            font-size: 1.2em;
            margin: 20px 0 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .section-title .badge {
            font-size: 0.7em;
            padding: 3px 8px;
            background: rgba(233,69,96,0.2);
            border-radius: 10px;
            color: #e94560;
        }

        .history-list {
            list-style: none;
        }

        .history-item {
            display: flex;
            align-items: center;
            padding: 12px;
            background: rgba(255,255,255,0.02);
            border-radius: 8px;
            margin-bottom: 8px;
            font-size: 0.9em;
        }

        .history-item .time {
            color: var(--text-secondary);
            font-size: 0.8em;
            width: 60px;
            flex-shrink: 0;
        }

        .history-item .info {
            flex: 1;
            margin-left: 10px;
        }

        .history-item .name {
            color: var(--text);
        }

        .history-item .meta {
            color: var(--text-secondary);
            font-size: 0.85em;
        }

        .log-list {
            max-height: 200px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.85em;
        }

        .log-item {
            padding: 8px 12px;
            border-left: 3px solid #333;
            margin-bottom: 5px;
            background: rgba(0,0,0,0.2);
            border-radius: 0 5px 5px 0;
        }

        .log-item.success { border-color: #27ae60; }
        .log-item.error { border-color: #e74c3c; }
        .log-item.info { border-color: #3498db; }

        .log-item .time {
            color: var(--text-secondary);
            font-size: 0.8em;
        }

        .empty-state {
            text-align: center;
            padding: 30px;
            color: var(--text-secondary);
            font-size: 0.9em;
        }

        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            background: #27ae60;
            border-radius: 10px;
            color: var(--text);
            font-weight: bold;
            transform: translateX(150%);
            transition: transform 0.3s;
            z-index: 1000;
        }

        .toast.show {
            transform: translateX(0);
        }

        .toast.error {
            background: #e74c3c;
        }

        .user-info {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }

        .user-info input {
            padding: 10px 15px;
            border: 2px solid var(--border);
            border-radius: 20px;
            background: var(--input-bg);
            color: var(--text);
            outline: none;
            transition: all 0.3s;
        }

        .user-info input:focus {
            border-color: var(--accent);
        }

        .user-info input::placeholder {
            color: var(--text-secondary);
        }

        /* 管理员按钮 */
        .admin-btn {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            border: 2px solid var(--border);
            background: var(--card-bg);
            font-size: 1.2em;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
            margin-left: 8px;
        }
        .admin-btn:hover {
            border-color: var(--accent);
        }
        .admin-btn.logged-in {
            border-color: #27ae60;
            background: rgba(39, 174, 96, 0.15);
            color: #27ae60;
        }

        /* 管理面板 */
        .admin-panel {
            display: none;
            gap: 10px;
            margin: 15px 0;
            padding: 12px 15px;
            background: rgba(39, 174, 96, 0.08);
            border: 1px solid rgba(39, 174, 96, 0.2);
            border-radius: 10px;
            align-items: center;
            flex-wrap: wrap;
        }
        .admin-panel.active {
            display: flex;
        }
        .admin-panel .panel-label {
            font-size: 0.85em;
            color: #27ae60;
            font-weight: bold;
            margin-right: 5px;
        }
        .admin-panel button {
            padding: 8px 16px;
            border: none;
            border-radius: 8px;
            font-size: 0.9em;
            cursor: pointer;
            transition: all 0.2s;
            background: rgba(255, 255, 255, 0.1);
            color: var(--text);
        }
        .admin-panel button:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        .admin-panel .btn-skip {
            background: rgba(233, 69, 96, 0.15);
            color: #e94560;
        }
        .admin-panel .btn-skip:hover {
            background: rgba(233, 69, 96, 0.3);
        }
        .admin-panel .btn-clear {
            background: rgba(231, 76, 60, 0.15);
            color: #e74c3c;
        }
        .admin-panel .btn-clear:hover {
            background: rgba(231, 76, 60, 0.3);
        }

        /* 管理员登录弹窗 */
        .admin-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.6);
            z-index: 2000;
            align-items: center;
            justify-content: center;
        }
        .admin-modal.show {
            display: flex;
        }
        .admin-modal .modal-box {
            background: #1a1a2e;
            border: 1px solid var(--border);
            border-radius: 15px;
            padding: 30px;
            width: 320px;
            text-align: center;
        }
        [data-theme="light"] .admin-modal .modal-box {
            background: #fff;
        }
        .admin-modal .modal-box h3 {
            margin-bottom: 20px;
            color: var(--text);
        }
        .admin-modal .modal-box input {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid var(--border);
            border-radius: 10px;
            background: var(--input-bg);
            color: var(--text);
            font-size: 1em;
            outline: none;
            margin-bottom: 15px;
            box-sizing: border-box;
        }
        .admin-modal .modal-box input:focus {
            border-color: #27ae60;
        }
        .admin-modal .modal-box .modal-actions {
            display: flex;
            gap: 10px;
            justify-content: center;
        }
        .admin-modal .modal-box .modal-actions button {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 0.9em;
            cursor: pointer;
        }
        .admin-modal .modal-box .btn-login {
            background: #27ae60;
            color: #fff;
        }
        .admin-modal .modal-box .btn-cancel {
            background: rgba(255,255,255,0.1);
            color: var(--text);
        }

        /* 队列项管理员操作按钮 */
        .queue-item .admin-actions {
            display: flex;
            gap: 4px;
            margin-left: 5px;
        }
        .queue-item .admin-actions button {
            padding: 4px 8px;
            border: none;
            border-radius: 5px;
            background: rgba(255,255,255,0.08);
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 0.75em;
            transition: all 0.2s;
        }
        .queue-item .admin-actions button:hover {
            background: rgba(255,255,255,0.15);
            color: var(--text);
        }
        .queue-item .admin-actions .btn-move-top:hover {
            color: #f39c12;
        }
        .queue-item .admin-actions .btn-remove:hover {
            color: #e74c3c;
        }

        @media (max-width: 600px) {
            .header h1 {
                font-size: 1.8em;
            }
            .search-box {
                flex-direction: column;
            }
            .stats {
                flex-direction: column;
                gap: 10px;
            }
            .admin-panel {
                flex-direction: column;
                align-items: stretch;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <h1>🎵 办公室点歌台</h1>
                    <p>输入歌名，自动排队播放</p>
                </div>
                <div style="display:flex;align-items:center;">
                    <button id="themeToggle" onclick="toggleTheme()" style="width:44px;height:44px;border-radius:50%;border:2px solid var(--border);background:var(--card-bg);font-size:1.4em;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all 0.3s;">🌙</button>
                    <button id="adminBtn" class="admin-btn" onclick="toggleAdminModal()" title="管理员登录">🔒</button>
                </div>
            </div>
        </div>

        <div class="user-info">
            <input type="text" id="userName" placeholder="你的昵称（选填）" maxlength="20">
        </div>

        <div class="search-box">
            <input type="text" id="songInput" placeholder="输入歌名，如：稻香、周杰伦、起风了..." onkeypress="if(event.key==='Enter')searchSong()">
            <button id="searchBtn" onclick="searchSong()">🎵 点歌</button>
        </div>

        <!-- 管理员面板（仅管理员可见） -->
        <div class="admin-panel" id="adminPanel">
            <span class="panel-label">🛠 管理</span>
            <button class="btn-skip" onclick="skipSong()">⏭️ 切歌</button>
            <button class="btn-clear" onclick="clearQueue()">🗑️ 清空队列</button>
        </div>

        <div class="current-play" id="currentPlay">
            <div class="label">▶️ 正在播放</div>
            <div class="song-name" id="currentName">-</div>
            <div class="artist" id="currentArtist">-</div>
        </div>

        <div class="section-title">📋 播放队列</div>
        <ul class="queue-list" id="queueList">
            <li class="empty-queue">队列是空的，快来点首歌吧！</li>
        </ul>

        <div class="stats">
            <div class="stat-item">
                <div class="stat-value" id="todayCount">0</div>
                <div class="stat-label">今日已点</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="queueCount">0</div>
                <div class="stat-label">排队中</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="remainingCount">10</div>
                <div class="stat-label">剩余额度</div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">
                📜 最近播放
                <span class="badge" id="historyCount">0</span>
            </div>
            <ul class="history-list" id="historyList">
                <li class="empty-state">还没有播放记录</li>
            </ul>
        </div>

        <div class="section">
            <div class="section-title">
                📋 点歌日志
                <button onclick="clearLog()" style="font-size:0.7em;padding:3px 8px;background:rgba(255,255,255,0.1);border:none;border-radius:5px;color:#888;cursor:pointer;">清空</button>
            </div>
            <div class="log-list" id="logList">
                <li class="empty-state">暂无日志</li>
            </div>
        </div>
    </div>

    <!-- 管理员登录弹窗 -->
    <div class="admin-modal" id="adminModal">
        <div class="modal-box">
            <h3>🔐 管理员登录</h3>
            <input type="password" id="adminPassword" placeholder="请输入管理员密码" onkeypress="if(event.key==='Enter')doAdminLogin()">
            <div class="modal-actions">
                <button class="btn-login" onclick="doAdminLogin()">登录</button>
                <button class="btn-cancel" onclick="closeAdminModal()">取消</button>
            </div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        let userId = localStorage.getItem('userId') || generateUserId();
        localStorage.setItem('userId', userId);
        let logs = [];
        let isAdmin = !!localStorage.getItem('adminToken');
        updateAdminUI();

        // 主题切换
        function initTheme() {
            const savedTheme = localStorage.getItem('theme') || 'dark';
            document.documentElement.setAttribute('data-theme', savedTheme);
            updateThemeIcon(savedTheme);
        }

        function toggleTheme() {
            const current = document.documentElement.getAttribute('data-theme') || 'dark';
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
            updateThemeIcon(next);
        }

        function updateThemeIcon(theme) {
            const btn = document.getElementById('themeToggle');
            btn.textContent = theme === 'dark' ? '🌙' : '☀️';
        }

        // 初始化主题
        initTheme();

        function generateUserId() {
            return 'user_' + Math.random().toString(36).substr(2, 9);
        }

        function getUserName() {
            return document.getElementById('userName').value.trim() || '匿名';
        }

        function escapeHtml(value) {
            return String(value ?? '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function showToast(msg, isError = false) {
            const toast = document.getElementById('toast');
            toast.textContent = msg;
            toast.className = 'toast' + (isError ? ' error' : '');
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }

        function addLog(msg, type = 'info') {
            const now = new Date();
            const time = now.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit', second: '2-digit'});
            logs.unshift({time, msg, type});
            if (logs.length > 50) logs.pop();
            renderLogs();
        }

        function renderLogs() {
            const list = document.getElementById('logList');
            if (logs.length === 0) {
                list.innerHTML = '<li class="empty-state">暂无日志</li>';
                return;
            }
            list.innerHTML = logs.map(log =>
                `<li class="log-item ${escapeHtml(log.type)}"><span class="time">${escapeHtml(log.time)}</span> ${escapeHtml(log.msg)}</li>`
            ).join('');
        }

        function clearLog() {
            logs = [];
            renderLogs();
        }

        async function searchSong() {
            const input = document.getElementById('songInput');
            const btn = document.getElementById('searchBtn');
            const query = input.value.trim();

            if (!query) {
                showToast('请输入歌名', true);
                return;
            }

            btn.disabled = true;
            btn.textContent = '下载中...';
            addLog(`开始搜索: ${query}`, 'info');

            try {
                const resp = await fetch('/api/search', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        query: query,
                        user_id: userId,
                        user_name: getUserName()
                    })
                });

                const data = await resp.json();

                if (data.ok) {
                    addLog(`搜索成功: ${query}，正在下载...`, 'success');
                    showToast(`🔄 ${query} 正在下载，完成后将自动加入队列`);
                    input.value = '';
                    // 等待下载完成后刷新队列
                    setTimeout(() => refreshQueue(), 5000);
                    setTimeout(() => refreshQueue(), 15000);
                    setTimeout(() => refreshHistory(), 20000);
                } else {
                    addLog(`搜索失败: ${data.error}`, 'error');
                    showToast(data.error || '点歌失败', true);
                }
            } catch (e) {
                addLog(`网络错误: ${e.message}`, 'error');
                showToast('网络错误，请重试', true);
            } finally {
                btn.disabled = false;
                btn.textContent = '🎵 点歌';
            }
        }

        async function refreshQueue() {
            try {
                const resp = await fetch(`/api/queue?user_id=${encodeURIComponent(userId)}`);
                const data = await resp.json();

                // 更新正在播放
                const currentPlay = document.getElementById('currentPlay');
                if (data.current && data.current.is_playing) {
                    currentPlay.classList.add('active');
                    document.getElementById('currentName').textContent = data.current.current_song.name;
                    document.getElementById('currentArtist').textContent = data.current.current_song.artist;
                } else {
                    currentPlay.classList.remove('active');
                }

                // 更新队列列表
                const queueList = document.getElementById('queueList');
                if (data.queue.length === 0) {
                    queueList.innerHTML = '<li class="empty-queue">队列是空的，快来点首歌吧！</li>';
                } else {
                    queueList.innerHTML = data.queue.map((song, i) => {
                        let actionsHtml = '';
                        if (isAdmin) {
                            // 管理员：显示顶歌 + 删除
                            actionsHtml = `
                                <div class="admin-actions">
                                    <button class="btn-move-top" onclick="moveTop(${song.id})" title="置顶">⬆️</button>
                                    <button class="btn-remove" onclick="removeSong(${song.id})" title="删除">🗑️</button>
                                </div>
                            `;
                        }
                        return `
                            <li class="queue-item">
                                <div class="num">${i + 1}</div>
                                <div class="info">
                                    <div class="name">${escapeHtml(song.name)}</div>
                                    <div class="meta">${escapeHtml(song.artist)} · ${escapeHtml(song.user_name)}</div>
                                </div>
                                ${actionsHtml}
                            </li>
                        `;
                    }).join('');
                }

                // 更新统计
                document.getElementById('queueCount').textContent = data.queue.length;
                document.getElementById('todayCount').textContent = data.stats.today_total;
                document.getElementById('remainingCount').textContent = data.stats.remaining;

            } catch (e) {
                console.error('刷新队列失败:', e);
            }
        }

        async function refreshHistory() {
            try {
                const resp = await fetch('/api/history');
                const data = await resp.json();
                const history = data.history || [];

                const list = document.getElementById('historyList');
                document.getElementById('historyCount').textContent = history.length;

                if (history.length === 0) {
                    list.innerHTML = '<li class="empty-state">还没有播放记录</li>';
                    return;
                }

                list.innerHTML = history.map(song => {
                    const time = song.played_at ? new Date(song.played_at).toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'}) : '';
                    return `
                        <li class="history-item">
                            <span class="time">${escapeHtml(time)}</span>
                            <div class="info">
                                <div class="name">${escapeHtml(song.name)}</div>
                                <div class="meta">${escapeHtml(song.artist)} · ${escapeHtml(song.user_name || '匿名')}</div>
                            </div>
                        </li>
                    `;
                }).join('');
            } catch (e) {
                console.error('刷新历史失败:', e);
            }
        }

        async function removeSong(songId) {
            try {
                const headers = {'Content-Type': 'application/json'};
                if (isAdmin) {
                    headers['X-Admin-Token'] = localStorage.getItem('adminToken') || '';
                }
                const resp = await fetch('/api/remove', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({song_id: songId, user_id: userId})
                });
                const data = await resp.json();
                if (!data.ok) {
                    showToast(data.error || '删除失败', true);
                } else {
                    refreshQueue();
                }
            } catch (e) {
                showToast('删除失败', true);
            }
        }

        async function moveTop(songId) {
            try {
                const resp = await fetch('/api/move_top', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Admin-Token': localStorage.getItem('adminToken') || ''
                    },
                    body: JSON.stringify({song_id: songId})
                });
                const data = await resp.json();
                if (!data.ok) {
                    showToast(data.error || '操作失败', true);
                } else {
                    showToast('已置顶');
                    refreshQueue();
                }
            } catch (e) {
                showToast('操作失败', true);
            }
        }

        async function skipSong() {
            try {
                const resp = await fetch('/api/skip', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Admin-Token': localStorage.getItem('adminToken') || ''
                    }
                });
                const data = await resp.json();
                if (!data.ok) {
                    showToast(data.error || '操作失败', true);
                }
            } catch (e) {
                showToast('操作失败', true);
            }
        }

        async function clearQueue() {
            if (!confirm('确定要清空整个队列吗？')) return;
            try {
                const resp = await fetch('/api/clear', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Admin-Token': localStorage.getItem('adminToken') || ''
                    }
                });
                const data = await resp.json();
                if (!data.ok) {
                    showToast(data.error || '操作失败', true);
                } else {
                    showToast('队列已清空');
                    refreshQueue();
                }
            } catch (e) {
                showToast('操作失败', true);
            }
        }

        // 管理员登录/登出
        function toggleAdminModal() {
            if (isAdmin) {
                // 登出
                if (confirm('确定要退出管理员账号吗？')) {
                    localStorage.removeItem('adminToken');
                    isAdmin = false;
                    updateAdminUI();
                    refreshQueue();
                    showToast('已退出管理员');
                }
            } else {
                // 显示登录弹窗
                document.getElementById('adminModal').classList.add('show');
                document.getElementById('adminPassword').value = '';
                document.getElementById('adminPassword').focus();
            }
        }

        function closeAdminModal() {
            document.getElementById('adminModal').classList.remove('show');
        }

        async function doAdminLogin() {
            const pwd = document.getElementById('adminPassword').value;
            if (!pwd) {
                showToast('请输入密码', true);
                return;
            }
            try {
                const resp = await fetch('/api/admin/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({password: pwd})
                });
                const data = await resp.json();
                if (data.ok) {
                    localStorage.setItem('adminToken', data.token);
                    isAdmin = true;
                    closeAdminModal();
                    updateAdminUI();
                    refreshQueue();
                    showToast('管理员登录成功');
                } else {
                    showToast(data.error || '密码错误', true);
                }
            } catch (e) {
                showToast('登录失败', true);
            }
        }

        function updateAdminUI() {
            const btn = document.getElementById('adminBtn');
            const panel = document.getElementById('adminPanel');
            if (isAdmin) {
                btn.textContent = '🔓';
                btn.classList.add('logged-in');
                btn.title = '管理员已登录（点击退出）';
                panel.classList.add('active');
            } else {
                btn.textContent = '🔒';
                btn.classList.remove('logged-in');
                btn.title = '管理员登录';
                panel.classList.remove('active');
            }
        }

        // 每5秒自动刷新队列
        setInterval(refreshQueue, 5000);
        setInterval(refreshHistory, 10000);

        // 页面加载时刷新
        refreshQueue();
        refreshHistory();
    </script>
</body>
</html>
"""

# ==================== 路由 ====================

@app.route('/')
def index():
    """主页"""
    return render_template_string(HTML_PAGE)


@app.route('/api/search', methods=['POST'])
def api_search():
    """搜索并点歌"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        user_id = data.get('user_id', '')
        user_name = data.get('user_name', '匿名')

        print(f"[搜索] 收到请求: query={query}, user={user_name}")

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

        # 在后台线程中搜索和下载
        def do_search():
            result = searcher.search(query)
            if result:
                # 检查播放器和队列状态
                was_empty = len(queue_mgr.get_queue()) == 0 and not player.is_playing

                song = queue_mgr.add_to_queue(
                    user_id=user_id,
                    song_name=result['name'],
                    artist=result['artist'],
                    url=result['url'],
                    user_name=user_name
                )
                if song:
                    # 只有队列为空且没有在播放时，才立即播放
                    if was_empty:
                        player.skip_event.set()
                        print(f"[搜索] 立即播放: {result['name']}")
                    else:
                        print(f"[搜索] 已加入队列: {result['name']}")

        thread = threading.Thread(target=do_search, daemon=True)
        thread.start()

        return jsonify({
            'ok': True,
            'message': '正在搜索和下载，请稍候...',
            'remaining': queue_mgr.get_today_remaining(user_id)
        })

    except Exception as e:
        import traceback
        print(f"[搜索] 异常: {e}")
        traceback.print_exc()
        return jsonify({'ok': False, 'error': f'搜索失败: {str(e)}'}), 500


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
