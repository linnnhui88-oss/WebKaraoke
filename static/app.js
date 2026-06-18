let userId = localStorage.getItem('userId') || generateUserId();
        localStorage.setItem('userId', userId);
        let logs = [];
        let isAdmin = !!localStorage.getItem('adminToken');
        let searchCandidates = [];
        let taskPollTimer = null;
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

        function setOnlineStatus(isOnline) {
            const banner = document.getElementById('connectionBanner');
            if (banner) {
                banner.classList.toggle('show', !isOnline);
            }
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

        function formatDuration(seconds) {
            if (!seconds) return '未知时长';
            const mins = Math.floor(seconds / 60);
            const secs = String(seconds % 60).padStart(2, '0');
            return `${mins}:${secs}`;
        }

        function renderCandidates(candidates) {
            const box = document.getElementById('searchResults');
            searchCandidates = candidates || [];
            if (searchCandidates.length === 0) {
                box.classList.remove('active');
                box.innerHTML = '';
                return;
            }

            box.classList.add('active');
            box.innerHTML = `
                <ul class="candidate-list">
                    ${searchCandidates.map((song, i) => `
                        <li class="candidate-item">
                            <img class="candidate-thumb" src="${escapeHtml(song.thumbnail || '')}" alt="">
                            <div>
                                <div class="candidate-title">${escapeHtml(song.name)}</div>
                                <div class="candidate-meta">${escapeHtml(song.artist || '未知频道')} · ${escapeHtml(formatDuration(song.duration))}</div>
                            </div>
                            <button onclick="requestCandidate(${i})">点这首</button>
                        </li>
                    `).join('')}
                </ul>
            `;
        }

        function taskStatusText(status) {
            const names = {
                pending: '等待中',
                downloading: '下载中',
                queued: '已入队',
                failed: '失败'
            };
            return names[status] || status || '未知';
        }

        function renderTasks(tasks) {
            const panel = document.getElementById('taskPanel');
            if (!tasks || tasks.length === 0) {
                panel.classList.remove('active');
                panel.innerHTML = '';
                return;
            }

            panel.classList.add('active');
            panel.innerHTML = `
                <ul class="task-list">
                    ${tasks.map(task => `
                        <li class="task-item">
                            <div>
                                <div class="task-title">${escapeHtml(task.song_name || '未知歌曲')}</div>
                                <div class="task-message">${escapeHtml(task.message || '')}</div>
                            </div>
                            <span class="task-status ${escapeHtml(task.status)}">${escapeHtml(taskStatusText(task.status))}</span>
                        </li>
                    `).join('')}
                </ul>
            `;
        }

        async function refreshTasks() {
            try {
                const resp = await fetch(`/api/tasks?user_id=${encodeURIComponent(userId)}`);
                const data = await resp.json();
                setOnlineStatus(true);
                renderTasks(data.tasks || []);
            } catch (e) {
                setOnlineStatus(false);
                console.error('刷新任务失败:', e);
            }
        }

        function startTaskPolling() {
            refreshTasks();
            if (taskPollTimer) return;
            taskPollTimer = setInterval(refreshTasks, 3000);
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
            btn.textContent = '搜索中...';
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
                setOnlineStatus(true);

                if (data.ok) {
                    renderCandidates(data.candidates || []);
                    addLog(`搜索成功: ${query}，找到 ${(data.candidates || []).length} 个候选`, 'success');
                    showToast('请选择要点的歌曲');
                } else {
                    addLog(`搜索失败: ${data.error}`, 'error');
                    showToast(data.error || '点歌失败', true);
                }
            } catch (e) {
                setOnlineStatus(false);
                addLog(`网络错误: ${e.message}`, 'error');
                showToast('网络错误，请重试', true);
            } finally {
                btn.disabled = false;
                btn.textContent = '🎵 点歌';
            }
        }

        async function requestCandidate(index) {
            const candidate = searchCandidates[index];
            if (!candidate) {
                showToast('候选歌曲不存在，请重新搜索', true);
                return;
            }

            addLog(`选择歌曲: ${candidate.name}`, 'info');
            try {
                const resp = await fetch('/api/request', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        candidate,
                        user_id: userId,
                        user_name: getUserName()
                    })
                });
                const data = await resp.json();
                setOnlineStatus(true);
                if (data.ok) {
                    renderCandidates([]);
                    document.getElementById('songInput').value = '';
                    addLog(`开始下载: ${candidate.name}`, 'success');
                    showToast('正在下载，完成后将自动加入队列');
                    startTaskPolling();
                    setTimeout(() => refreshQueue(), 5000);
                    setTimeout(() => refreshQueue(), 15000);
                    setTimeout(() => refreshHistory(), 20000);
                } else {
                    addLog(`点歌失败: ${data.error}`, 'error');
                    showToast(data.error || '点歌失败', true);
                }
            } catch (e) {
                addLog(`网络错误: ${e.message}`, 'error');
                showToast('网络错误，请重试', true);
            }
        }

        async function refreshQueue() {
            try {
                const resp = await fetch(`/api/queue?user_id=${encodeURIComponent(userId)}`);
                const data = await resp.json();
                setOnlineStatus(true);

                // 更新正在播放
                const currentPlay = document.getElementById('currentPlay');
                if (data.current && data.current.is_playing) {
                    currentPlay.classList.add('active');
                    document.getElementById('currentName').textContent = data.current.current_song.name;
                    document.getElementById('currentArtist').textContent = data.current.current_song.artist;
                    document.getElementById('currentRequester').textContent = `点歌人: ${data.current.current_song.user_name || '匿名'}`;
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
                setOnlineStatus(false);
                console.error('刷新队列失败:', e);
            }
        }

        async function refreshHistory() {
            try {
                const resp = await fetch('/api/history');
                const data = await resp.json();
                setOnlineStatus(true);
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
                setOnlineStatus(false);
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
                    const token = localStorage.getItem('adminToken') || '';
                    fetch('/api/admin/logout', {
                        method: 'POST',
                        headers: {'X-Admin-Token': token}
                    }).catch(() => {});
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
        startTaskPolling();

        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                refreshQueue();
                refreshHistory();
                refreshTasks();
            }
        });

        // 页面加载时刷新
        refreshQueue();
        refreshHistory();
