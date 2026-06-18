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
