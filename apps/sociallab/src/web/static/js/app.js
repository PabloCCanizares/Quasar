const API = '/api';
let currentUser = null;
let spamUserIds = new Set();
let spamHighlightEnabled = false;

// --- Init ---
document.addEventListener('DOMContentLoaded', async () => {
    const saved = localStorage.getItem('sociallab_user');
    if (saved) {
        currentUser = normalizeUser(JSON.parse(saved));
        await restoreSession();
    } else {
        showLogin();
    }
});

function docId(doc) {
    return doc?._id || doc?.id;
}

function currentUserId() {
    return docId(currentUser);
}

function normalizeUser(user) {
    if (user && !user._id && user.id) user._id = user.id;
    return user;
}

async function restoreSession() {
    const userId = currentUserId();
    if (!userId) {
        logout();
        return;
    }

    document.getElementById('app').innerHTML = '<div class="loading">Comprobando sesión...</div>';
    try {
        const res = await fetch(`${API}/users/${userId}`);
        if (!res.ok) {
            logout();
            return;
        }
        currentUser = normalizeUser(await res.json());
        localStorage.setItem('sociallab_user', JSON.stringify(currentUser));
        showApp();
    } catch (e) {
        showLogin();
    }
}

// --- Auth ---
function showLogin() {
    document.getElementById('app').innerHTML = `
        <div class="login-container">
            <div class="login-box">
                <h1>SocialLab</h1>
                <p>Red social pedagógica</p>
                <div id="login-mode">
                    <div class="form-group">
                        <label>Username</label>
                        <input type="text" id="login-username" placeholder="Tu usuario">
                    </div>
                    <button class="btn" style="width:100%;margin-bottom:12px" onclick="login()">Entrar</button>
                    <button class="btn" style="width:100%;background:var(--bg-hover)" onclick="showRegister()">Crear cuenta</button>
                </div>
            </div>
        </div>`;
}

function showRegister() {
    document.querySelector('#login-mode').innerHTML = `
        <div class="form-group">
            <label>Username</label>
            <input type="text" id="reg-username" placeholder="ej: pablo_g01">
        </div>
        <div class="form-group">
            <label>Nombre</label>
            <input type="text" id="reg-name" placeholder="ej: Pablo García">
        </div>
        <div class="form-group">
            <label>Email</label>
            <input type="email" id="reg-email" placeholder="ej: pablo@uni.edu">
        </div>
        <div class="form-group">
            <label>Grupo</label>
            <input type="text" id="reg-group" placeholder="ej: g01">
        </div>
        <button class="btn" style="width:100%;margin-bottom:12px" onclick="register()">Crear cuenta</button>
        <button class="btn" style="width:100%;background:var(--bg-hover)" onclick="showLogin()">Volver</button>`;
}

async function login() {
    const username = document.getElementById('login-username').value.trim();
    if (!username) return;
    try {
        const res = await fetch(`${API}/users/by-username/${username}`);
        if (!res.ok) { alert('Usuario no encontrado'); return; }
        currentUser = normalizeUser(await res.json());
        localStorage.setItem('sociallab_user', JSON.stringify(currentUser));
        showApp();
    } catch (e) { alert('Error de conexión'); }
}

async function register() {
    const body = {
        username: document.getElementById('reg-username').value.trim(),
        display_name: document.getElementById('reg-name').value.trim(),
        email: document.getElementById('reg-email').value.trim(),
        group_id: document.getElementById('reg-group').value.trim() || null,
    };
    if (!body.username || !body.display_name || !body.email) { alert('Rellena todos los campos'); return; }
    try {
        const res = await fetch(`${API}/users/`, {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
        });
        if (res.status === 409) { alert('Username ya existe'); return; }
        if (!res.ok) { alert('Error al crear cuenta'); return; }
        currentUser = normalizeUser(await res.json());
        localStorage.setItem('sociallab_user', JSON.stringify(currentUser));
        showApp();
    } catch (e) { alert('Error de conexión'); }
}

function logout() {
    currentUser = null;
    localStorage.removeItem('sociallab_user');
    showLogin();
}

// --- App layout ---
function showApp() {
    const initial = currentUser.display_name?.charAt(0) || currentUser.username.charAt(0);
    document.getElementById('app').innerHTML = `
        <div class="app">
            <aside class="sidebar">
                <div class="logo">SocialLab</div>
                <nav>
                    <a href="#" onclick="loadTimeline()" class="active" id="nav-home"><span>Inicio</span></a>
                    <a href="#" onclick="loadExplore()"><span>Explorar</span></a>
                    <a href="#" onclick="loadProfile('${currentUserId()}')"><span>Perfil</span></a>
                    <a href="#" onclick="loadNeo4jPanel()"><span>Neo4j</span></a>
                    <a href="#" onclick="loadSparkPanel()"><span>Spark/ML</span></a>
                    <a href="#" onclick="logout()"><span>Salir</span></a>
                </nav>
            </aside>
            <main class="feed">
                <div class="feed-header" id="feed-header">Inicio</div>
                <div id="feed-content"></div>
            </main>
            <aside class="right-panel">
                <input class="search-box" placeholder="Buscar usuarios o #hashtags..." id="search-input" onkeydown="if(event.key==='Enter')searchSocial()">
                <div id="trends-container"></div>
                <div id="suggestions-container"></div>
            </aside>
        </div>`;
    loadTimeline();
    loadTrends();
    loadSuggestions();
}

function renderFeedHeader(title) {
    const spamBtnClass = spamHighlightEnabled ? 'active' : '';
    return `<span>${esc(title)}</span>
        <button class="btn-spam-toggle ${spamBtnClass}" id="spam-toggle" onclick="toggleSpamHighlight()" title="Activar/desactivar detector de spam">
            ${spamHighlightEnabled ? 'Ocultar Spam' : 'Detector Spam'}
        </button>`;
}

// --- Timeline ---
async function loadTimeline() {
    document.getElementById('feed-header').innerHTML = renderFeedHeader('Inicio');
    const compose = renderCompose();
    document.getElementById('feed-content').innerHTML = compose + '<div class="loading">Cargando...</div>';

    const res = await fetch(`${API}/posts/timeline/${currentUserId()}?limit=50`);
    const posts = await res.json();

    if (posts.length === 0) {
        document.getElementById('feed-content').innerHTML = compose + `
            <div class="empty-state">
                <p style="font-size:18px;margin-bottom:8px">Tu timeline está vacío</p>
                <p>Sigue a otros usuarios para ver sus posts aquí.</p>
                <button class="btn" style="margin-top:16px" onclick="loadExplore()">Explorar posts</button>
            </div>`;
        return;
    }

    document.getElementById('feed-content').innerHTML = compose + posts.map(p => renderPost(p)).join('');
}

// --- Explore ---
async function loadExplore() {
    document.getElementById('feed-header').innerHTML = renderFeedHeader('Explorar');
    document.getElementById('feed-content').innerHTML = '<div class="loading">Cargando...</div>';
    const res = await fetch(`${API}/posts/?limit=50`);
    const posts = await res.json();
    document.getElementById('feed-content').innerHTML = posts.map(renderPost).join('');
}

// --- Profile ---
async function loadProfile(userId) {
    document.getElementById('feed-header').innerHTML = renderFeedHeader('Perfil');
    document.getElementById('feed-content').innerHTML = '<div class="loading">Cargando...</div>';

    const [userRes, postsRes] = await Promise.all([
        fetch(`${API}/users/${userId}`),
        fetch(`${API}/posts/?user_id=${userId}&limit=50`),
    ]);
    const user = await userRes.json();
    const posts = await postsRes.json();

    const profileUserId = docId(user);
    const isMe = profileUserId === currentUserId();
    const initial = user.display_name?.charAt(0) || user.username?.charAt(0) || '?';

    const followBtn = isMe ? '' :
        `<button class="btn-follow" id="follow-btn-${profileUserId}" onclick="toggleFollow('${profileUserId}')"
            data-following="false">Seguir</button>`;

    document.getElementById('feed-content').innerHTML = `
        <div class="profile-header">
            <div class="profile-banner"></div>
            <div class="profile-avatar">${initial.toUpperCase()}</div>
            <div class="profile-info">
                <div class="profile-name">${esc(user.display_name || user.username)}</div>
                <div class="profile-username">@${esc(user.username)}</div>
                <div class="profile-bio">${esc(user.bio || '')}</div>
                ${followBtn}
                <div class="profile-stats">
                    <span><strong>${user.following_count || 0}</strong> Siguiendo</span>
                    <span><strong>${user.followers_count || 0}</strong> Seguidores</span>
                    <span><strong>${user.posts_count || 0}</strong> Posts</span>
                </div>
            </div>
        </div>
        ${posts.map(renderPost).join('')}`;

    // Check if already following
    if (!isMe) checkFollowing(profileUserId);
}

async function checkFollowing(targetId) {
    const res = await fetch(`${API}/users/${currentUserId()}/following`);
    const follows = await res.json();
    const isFollowing = follows.some(f => f.following_id === targetId);
    const btn = document.getElementById(`follow-btn-${targetId}`);
    if (btn && isFollowing) {
        btn.textContent = 'Siguiendo';
        btn.classList.add('following');
        btn.dataset.following = 'true';
    }
}

// --- Compose ---
function renderCompose() {
    const initial = currentUser.display_name?.charAt(0) || currentUser.username.charAt(0);
    return `
        <div class="compose">
            <div class="avatar">${initial.toUpperCase()}</div>
            <div class="compose-form">
                <textarea id="compose-text" placeholder="¿Qué está pasando?" rows="3"></textarea>
                <div class="compose-actions">
                    <button class="btn" onclick="submitPost()">Publicar</button>
                </div>
            </div>
        </div>`;
}

async function submitPost() {
    const text = document.getElementById('compose-text').value.trim();
    if (!text) return;
    const userId = currentUserId();
    if (!userId) {
        alert('No hay usuario activo. Cierra sesión y vuelve a entrar.');
        return;
    }
    try {
        const res = await fetch(`${API}/posts/?user_id=${encodeURIComponent(userId)}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ text }),
        });
        if (res.ok) {
            document.getElementById('compose-text').value = '';
            loadTimeline();
            return;
        }
        const detail = await res.json().catch(() => ({}));
        alert(detail.detail || detail.error || 'No se pudo publicar el post');
    } catch (e) {
        alert('Error de conexión al publicar');
    }
}

// --- Post rendering ---
function renderPost(post) {
    const initial = post.username?.charAt(0) || '?';
    const time = timeAgo(post.created_at);
    const text = linkifyPost(esc(post.text || ''));
    const isSpam = spamHighlightEnabled && spamUserIds.has(post.user_id);
    const spamClass = isSpam ? ' post-spam' : '';
    const spamBadge = isSpam ? '<span class="spam-badge">SPAM</span>' : '';
    return `
        <div class="post${spamClass}" id="post-${post._id}" data-user-id="${esc(post.user_id || '')}">
            <div class="avatar" onclick="loadProfile('${post.user_id}')"${isSpam ? ' style="background:var(--spam);color:white"' : ''}>${initial.toUpperCase()}</div>
            <div class="post-content">
                <div class="post-header">
                    <span class="name" onclick="loadProfile('${post.user_id}')">${esc(post.username || 'unknown')}</span>
                    <span class="username">@${esc(post.username || 'unknown')}</span>
                    ${spamBadge}
                    <span class="time">${time}</span>
                </div>
                <div class="post-text">${text}</div>
                <div class="post-actions">
                    <button onclick="toggleLike('${post._id}', this)" title="Like">
                        &#9829; <span>${post.likes_count || 0}</span>
                    </button>
                </div>
            </div>
        </div>`;
}

function linkifyPost(text) {
    // Hashtags
    text = text.replace(/#(\w+)/g, '<span class="hashtag" onclick="searchTag(\'$1\')">#$1</span>');
    // Mentions
    text = text.replace(/@(\w+)/g, '<a href="#" onclick="findUser(\'$1\')">@$1</a>');
    return text;
}

// --- Like ---
async function toggleLike(postId, btn) {
    const res = await fetch(`${API}/posts/${postId}/like?user_id=${currentUserId()}`, { method: 'POST' });
    if (res.status === 409) {
        // Unlike
        await fetch(`${API}/posts/${postId}/like?user_id=${currentUserId()}`, { method: 'DELETE' });
        btn.classList.remove('liked');
        const span = btn.querySelector('span');
        span.textContent = Math.max(0, parseInt(span.textContent) - 1);
    } else if (res.ok) {
        btn.classList.add('liked');
        const span = btn.querySelector('span');
        span.textContent = parseInt(span.textContent) + 1;
    }
}

// --- Follow ---
async function toggleFollow(targetId) {
    const btn = document.getElementById(`follow-btn-${targetId}`);
    if (btn.dataset.following === 'true') {
        await fetch(`${API}/users/${targetId}/follow?user_id=${currentUserId()}`, { method: 'DELETE' });
        btn.textContent = 'Seguir';
        btn.classList.remove('following');
        btn.dataset.following = 'false';
    } else {
        await fetch(`${API}/users/${targetId}/follow?user_id=${currentUserId()}`, { method: 'POST' });
        btn.textContent = 'Siguiendo';
        btn.classList.add('following');
        btn.dataset.following = 'true';
    }
}

// --- Search ---
async function searchSocial() {
    const raw = document.getElementById('search-input').value.trim();
    if (!raw) return;
    if (raw.startsWith('#')) {
        searchTag(raw.replace(/^#+/, ''));
        return;
    }
    searchUsers(raw.replace(/^@+/, ''));
}

async function searchTag(tag) {
    document.getElementById('feed-header').textContent = `#${tag}`;
    document.getElementById('feed-content').innerHTML = '<div class="loading">Cargando...</div>';
    const res = await fetch(`${API}/hashtags/${tag}/posts?limit=50`);
    const posts = await res.json();
    document.getElementById('feed-content').innerHTML = posts.length
        ? posts.map(renderPost).join('')
        : '<div class="empty-state">No hay posts con #' + esc(tag) + '</div>';
}

async function searchUsers(query) {
    const q = query.trim();
    if (!q) return;
    document.getElementById('feed-header').textContent = `Buscar usuarios`;
    document.getElementById('feed-content').innerHTML = '<div class="loading">Buscando usuarios...</div>';

    const res = await fetch(`${API}/users/?q=${encodeURIComponent(q)}&limit=30`);
    if (!res.ok) {
        document.getElementById('feed-content').innerHTML = '<div class="empty-state">No se pudo buscar usuarios</div>';
        return;
    }
    const users = await res.json();
    const filtered = users.filter(u => docId(u) !== currentUserId());
    document.getElementById('feed-content').innerHTML = `
        <div class="search-results">
            <div class="panel-card">
                <h3>Usuarios encontrados para "${esc(q)}"</h3>
                ${filtered.length ? `
                    <div class="user-list">
                        ${filtered.map(renderUserSearchResult).join('')}
                    </div>
                ` : `<div class="empty-state">No hay usuarios que coincidan con "${esc(q)}"</div>`}
            </div>
        </div>`;
}

function renderUserSearchResult(u) {
    const userId = docId(u);
    const initial = u.display_name?.charAt(0) || u.username?.charAt(0) || '?';
    return `
        <div class="follow-item" onclick="loadProfile('${userId}')" style="cursor:pointer">
            <div class="avatar">${initial.toUpperCase()}</div>
            <div class="follow-info">
                <div class="follow-name">${esc(u.display_name || u.username)}</div>
                <div class="follow-username">@${esc(u.username)} · ${u.followers_count || 0} seguidores · ${u.posts_count || 0} posts</div>
                ${u.bio ? `<div class="text-secondary" style="font-size:12px;margin-top:2px">${esc(u.bio).slice(0, 120)}</div>` : ''}
            </div>
        </div>`;
}

// --- Trends ---
async function loadTrends() {
    const container = document.getElementById('trends-container');
    if (!container) return;
    try {
        const res = await fetch(`${API}/hashtags/trending`);
        if (!res.ok) return;
        const trends = await res.json();
        container.innerHTML = `
            <div class="trends-panel">
                <div class="panel-title">Tendencias</div>
                ${trends.slice(0, 8).map(t => `
                    <div class="trend-item" onclick="searchTag('${esc(t.hashtag)}')">
                        <div class="trend-name">#${esc(t.hashtag)}</div>
                        <div class="trend-count">${t.post_count} posts</div>
                    </div>`).join('')}
            </div>`;
    } catch (e) {}
}

// --- Suggestions ---
async function loadSuggestions() {
    const container = document.getElementById('suggestions-container');
    if (!container) return;
    try {
        const res = await fetch(`${API}/users/?limit=5`);
        const users = await res.json();
        const filtered = users.filter(u => docId(u) !== currentUserId());
        container.innerHTML = `
            <div class="who-to-follow">
                <div class="panel-title">A quién seguir</div>
                ${filtered.map(u => {
                    const initial = u.display_name?.charAt(0) || u.username?.charAt(0) || '?';
                    const userId = docId(u);
                    return `
                    <div class="follow-item" onclick="loadProfile('${userId}')">
                        <div class="avatar">${initial.toUpperCase()}</div>
                        <div class="follow-info">
                            <div class="follow-name">${esc(u.display_name || u.username)}</div>
                            <div class="follow-username">@${esc(u.username)}</div>
                        </div>
                    </div>`;
                }).join('')}
            </div>`;
    } catch (e) {}
}

async function findUser(username) {
    const res = await fetch(`${API}/users/by-username/${username}`);
    if (res.ok) {
        const user = normalizeUser(await res.json());
        loadProfile(docId(user));
    }
}

// ========================================================
// NEO4J PANEL
// ========================================================

let neo4jData = {};
let neo4jActiveTab = 'overview';

function asList(value) {
    return Array.isArray(value) ? value : [];
}

async function loadNeo4jPanel() {
    document.getElementById('feed-header').textContent = 'Neo4j — Grafo Social';
    document.getElementById('feed-content').innerHTML = '<div class="loading">Consultando Neo4j...</div>';

    try {
        const fetches = {
            stats: fetch(`${API}/analytics/neo4j/stats`).then(r => r.json()).catch(() => null),
            influencers: fetch(`${API}/analytics/neo4j/influencers`).then(r => r.json()).catch(() => null),
            communities: fetch(`${API}/analytics/neo4j/communities`).then(r => r.json()).catch(() => null),
            bridges: fetch(`${API}/analytics/neo4j/bridges?limit=8`).then(r => r.json()).catch(() => null),
            hashgraph: fetch(`${API}/analytics/neo4j/hashtag-graph?limit=20`).then(r => r.json()).catch(() => null),
            ego: fetch(`${API}/analytics/neo4j/ego-network?user_id=${currentUserId()}&depth=2&limit=30`).then(r => r.json()).catch(() => null),
            myCommunities: fetch(`${API}/analytics/neo4j/my-communities?user_id=${currentUserId()}`).then(r => r.json()).catch(() => null),
            overlap: fetch(`${API}/analytics/neo4j/community-overlap?user_id=${currentUserId()}`).then(r => r.json()).catch(() => null),
            reach: fetch(`${API}/analytics/neo4j/reach?user_id=${currentUserId()}`).then(r => r.json()).catch(() => null),
            famousDistances: fetch(`${API}/analytics/neo4j/famous-distances?user_id=${currentUserId()}`).then(r => r.json()).catch(() => null),
            mutual: fetch(`${API}/analytics/neo4j/mutual-interests?user_id=${currentUserId()}&limit=10`).then(r => r.json()).catch(() => null),
            labStatus: fetch(`${API}/analytics/lab/status`).then(r => r.json()).catch(() => null),
        };

        const keys = Object.keys(fetches);
        const values = await Promise.all(Object.values(fetches));
        neo4jData = {};
        keys.forEach((k, i) => neo4jData[k] = values[i]);

        if (neo4jData.stats?.error || !neo4jData.stats) {
            const isExercise = Boolean(neo4jData.stats?.exercise);
            document.getElementById('feed-content').innerHTML = `
                <div class="analytics-panel">
                    <div class="panel-card error-card">
                        <h3>${isExercise ? 'Ejercicios Neo4j sin resolver' : 'Neo4j no disponible'}</h3>
                        ${isExercise ? `
                            <p>Completa los endpoints scaffold en estos archivos:</p>
                            <ul class="exercise-list">
                                <li><strong>Basic:</strong> <code>src/web/routes/neo4j_basic_ex.py</code></li>
                                <li><strong>Intermediate:</strong> <code>src/web/routes/neo4j_intermediate_ex.py</code></li>
                                <li><strong>Advanced:</strong> <code>src/web/routes/neo4j_advanced_ex.py</code></li>
                            </ul>
                            <p>Implementa los ejercicios de Cypher y ejecuta <code>docker compose restart app</code>.</p>
                        ` : '<p>Arranca Neo4j y ejecuta: <code>./lab.sh etl</code></p>'}
                        <p class="error-detail">${neo4jData.stats?.error || 'Connection refused'}</p>
                    </div>
                </div>`;
            return;
        }

        neo4jActiveTab = 'overview';
        renderNeo4jPanel();
    } catch (e) {
        document.getElementById('feed-content').innerHTML = `
            <div class="analytics-panel">
                <div class="panel-card error-card">
                    <h3>No se pudo pintar la vista Neo4j</h3>
                    <p>Recarga la pagina. Si persiste, revisa que los bloques desbloqueados tengan datos cargados.</p>
                    <p class="error-detail">${esc(e.message || String(e))}</p>
                </div>
            </div>`;
    }
}

function renderNeo4jPanel() {
    const flags = neo4jData.labStatus?.neo4j || {};
    const tabs = [
        { id: 'overview', label: 'Resumen', show: flags.basic },
        { id: 'influence', label: 'Influencers', show: flags.basic },
        { id: 'communities', label: 'Mis Comunidades', show: flags.intermediate },
        { id: 'hashgraph', label: 'Mapa Hashtags', show: flags.intermediate },
        { id: 'myNetwork', label: 'Mi Red', show: flags.advanced },
        { id: 'explore', label: 'Explorar Grafo', show: flags.intermediate || flags.advanced },
    ].filter(t => t.show);

    if (!tabs.some(t => t.id === neo4jActiveTab)) {
        neo4jActiveTab = tabs[0]?.id || 'overview';
    }

    const tabsHtml = `
        <div class="ml-tabs">
            ${tabs.map(t => `<button class="ml-tab${neo4jActiveTab === t.id ? ' active' : ''}" onclick="switchNeo4jTab('${t.id}')">${t.label}</button>`).join('')}
        </div>`;

    let content = '';
    switch (neo4jActiveTab) {
        case 'overview': content = renderNeo4jOverview(); break;
        case 'myNetwork': content = renderMyNetwork(); break;
        case 'communities': content = renderMyCommunities(); break;
        case 'influence': content = renderInfluenceBridges(); break;
        case 'explore': content = renderExploreGraph(); break;
        case 'hashgraph': content = renderHashtagMap(); break;
    }

    document.getElementById('feed-content').innerHTML = `
        <div class="analytics-panel">${tabsHtml}${content}</div>`;

    // Post-render: draw canvases
    if (neo4jActiveTab === 'myNetwork') drawEgoGraph();
    if (neo4jActiveTab === 'hashgraph') drawHashtagGraph();
    if (neo4jActiveTab === 'communities') drawCommunityGraph();
}

function switchNeo4jTab(tab) {
    neo4jActiveTab = tab;
    renderNeo4jPanel();
}

function renderReachRadar(reach, stats) {
    var totalUsers = stats.users || 1;
    var hop1 = reach.hop1 || 0;
    var hop2 = reach.hop2 || 0;
    var hop3 = reach.hop3 || 0;
    if (hop1 + hop2 + hop3 === 0) {
        return `
            <div class="empty-state" style="padding:24px">
                <p style="font-size:16px;margin-bottom:8px">Nadie llega a este usuario por FOLLOWS entrantes</p>
                <p>Este grafico cuenta usuarios que pueden llegar a ti siguiendo relaciones <code>FOLLOWS</code> hacia dentro. Si usas una cuenta creada en la web, normalmente nadie del dataset seed te sigue todavia.</p>
                <button class="btn" style="margin-top:16px" onclick="simulateDemoFollowers(this)">Simular audiencia demo</button>
            </div>`;
    }
    var pct1 = Math.min((hop1 / totalUsers) * 100, 100);
    var pct2 = Math.min((hop2 / totalUsers) * 100, 100);
    var pct3 = Math.min((hop3 / totalUsers) * 100, 100);

    // Emoji map for famous profiles
    var emojiMap = {
        'elonmusk': '🚀', 'taylorswift': '🎵', 'leomessi': '⚽', 'ibaboreal': '🎮',
        'rosalia': '🎤', 'auronplay': '😂', 'shakira': '💃', 'jbalvin': '🎶',
    };
    var fieldMap = {
        'elonmusk': 'Tech', 'taylorswift': 'Música', 'leomessi': 'Deporte', 'ibaboreal': 'Streaming',
        'rosalia': 'Música', 'auronplay': 'YouTube', 'shakira': 'Música', 'jbalvin': 'Reggaeton',
    };

    // Use real distances from Neo4j — group by ring and space evenly
    var famousDistances = asList(neo4jData.famousDistances);
    var byRing = {1: [], 2: [], 3: []};
    famousDistances.forEach(function(f) {
        var dist = f.distance;
        if (dist >= 1 && dist <= 3) {
            byRing[dist].push({
                name: f.display_name || f.username,
                emoji: emojiMap[f.username] || '👤',
                field: fieldMap[f.username] || '',
                ring: dist,
            });
        }
    });
    var famousProfiles = [];
    [1, 2, 3].forEach(function(ring) {
        var items = byRing[ring];
        var step = 360 / Math.max(items.length, 1);
        var offset = ring * 30; // stagger start angle per ring
        items.forEach(function(item, i) {
            item.angle = offset + (step * i);
            famousProfiles.push(item);
        });
    });

    // Build SVG radar
    var cx = 200, cy = 200;
    var radii = [55, 115, 175];
    var colors = ['#1da1f2', '#17bf63', '#e67e22'];
    var labels = ['1 salto', '2 saltos', '3 saltos'];
    var values = [hop1, hop2, hop3];
    var pcts = [pct1, pct2, pct3];

    var svg = '<svg viewBox="0 0 400 400" class="reach-radar-svg">';

    // Concentric rings (outermost first for z-order)
    for (var i = 2; i >= 0; i--) {
        var opacity = 0.08 + (i * 0.04);
        svg += '<circle cx="' + cx + '" cy="' + cy + '" r="' + radii[i] + '" ' +
               'fill="' + colors[i] + '" fill-opacity="' + opacity + '" ' +
               'stroke="' + colors[i] + '" stroke-opacity="0.3" stroke-width="1.5" stroke-dasharray="4 3"/>';
    }

    // Ring labels with data
    for (var i = 0; i < 3; i++) {
        var ly = cy - radii[i] + 14;
        svg += '<text x="' + cx + '" y="' + ly + '" text-anchor="middle" ' +
               'fill="' + colors[i] + '" font-size="10" font-weight="bold" opacity="0.9">' +
               labels[i] + ' · ' + values[i].toLocaleString() + ' (' + pcts[i].toFixed(1) + '%)' +
               '</text>';
    }

    // Famous profiles at their REAL BFS distance
    famousProfiles.forEach(function(p) {
        var r = radii[p.ring - 1] - 20;
        var rad = (p.angle * Math.PI) / 180;
        var px = cx + r * Math.cos(rad);
        var py = cy + r * Math.sin(rad);
        svg += '<g class="reach-famous" transform="translate(' + px + ',' + py + ')">' +
               '<circle r="16" fill="var(--bg-card)" stroke="' + colors[p.ring - 1] + '" stroke-width="1.5" opacity="0.9"/>' +
               '<text y="1" text-anchor="middle" font-size="14">' + p.emoji + '</text>' +
               '<text y="28" text-anchor="middle" fill="var(--text-secondary)" font-size="8" font-weight="600">' + p.name + '</text>' +
               '<text y="37" text-anchor="middle" fill="' + colors[p.ring - 1] + '" font-size="7">' + p.field + '</text>' +
               '</g>';
    });

    // Center node (you)
    svg += '<circle cx="' + cx + '" cy="' + cy + '" r="22" fill="#1da1f2" stroke="white" stroke-width="2.5"/>' +
           '<text x="' + cx + '" y="' + (cy + 1) + '" text-anchor="middle" fill="white" font-size="10" font-weight="bold">TÚ</text>';

    // Pulse animation on center
    svg += '<circle cx="' + cx + '" cy="' + cy + '" r="22" fill="none" stroke="#1da1f2" stroke-width="1.5">' +
           '<animate attributeName="r" from="22" to="45" dur="2s" repeatCount="indefinite"/>' +
           '<animate attributeName="opacity" from="0.6" to="0" dur="2s" repeatCount="indefinite"/>' +
           '</circle>';

    svg += '</svg>';

    // Legend
    var legend = '<div class="reach-radar-legend">';
    for (var i = 0; i < 3; i++) {
        legend += '<div class="reach-legend-item">' +
            '<span class="legend-dot" style="background:' + colors[i] + '"></span>' +
            '<span style="color:' + colors[i] + ';font-weight:600">' + labels[i] + '</span>' +
            '<span class="text-secondary" style="font-size:12px">' + values[i].toLocaleString() + ' usuarios (' + pcts[i].toFixed(1) + '%)</span>' +
            '</div>';
    }
    legend += '</div>';

    return '<div class="reach-radar-container">' + svg + legend + '</div>';
}

async function simulateDemoFollowers(btn) {
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Creando audiencia...';
    }
    try {
        const res = await fetch(`${API}/analytics/neo4j/demo-followers/${currentUserId()}`, { method: 'POST' });
        const data = await res.json();
        if (!res.ok || data.error) {
            alert(data.error || 'No se pudo crear la audiencia demo');
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Simular audiencia demo';
            }
            return;
        }
        await loadNeo4jPanel();
    } catch (e) {
        alert('Error creando audiencia demo');
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Simular audiencia demo';
        }
    }
}

// --- Overview tab ---
function renderNeo4jOverview() {
    const stats = asList(neo4jData.stats)[0] || {};
    const reach = asList(neo4jData.reach)[0] || {};
    const communities = asList(neo4jData.communities);
    const advanced = Boolean(neo4jData.labStatus?.neo4j?.advanced);
    return `
        <div class="panel-card">
            <h3>Estadísticas del Grafo</h3>
            <div class="stats-grid">
                <div class="stat-item"><div class="stat-value">${stats.users || 0}</div><div class="stat-label">Nodos User</div></div>
                <div class="stat-item"><div class="stat-value">${stats.hashtags || 0}</div><div class="stat-label">Nodos Hashtag</div></div>
                <div class="stat-item"><div class="stat-value">${(stats.follows || 0).toLocaleString()}</div><div class="stat-label">Relaciones FOLLOWS</div></div>
                <div class="stat-item"><div class="stat-value">${(stats.interests || 0).toLocaleString()}</div><div class="stat-label">Relaciones INTERESTED_IN</div></div>
            </div>
            <p class="card-summary">El grafo social modela la red como nodos (usuarios y hashtags) y relaciones (FOLLOWS e INTERESTED_IN). Estos conteos reflejan el volumen total de entidades y conexiones cargadas en Neo4j tras el ETL de Spark.</p>
        </div>
        ${advanced ? `
        <div class="panel-card">
            <h3>¿Quién te conoce? <span class="query-badge">6 grados</span></h3>
            <div class="reach-radar-wrap">
                ${renderReachRadar(reach, stats)}
            </div>
            <p class="card-summary">Teoría de los 6 grados de separación: ¿cuántas personas te "conocen" a través de cadenas de FOLLOWS entrantes? A 1 salto = te siguen directamente. A 2 saltos = siguen a alguien que te sigue. A 3 saltos llegas a cubrir gran parte de la red — el efecto "mundo pequeño".</p>
        </div>` : ''}
        <div class="panel-card">
            <h3>Comunidades Globales <span class="query-badge">INTERESTED_IN</span></h3>
            <div class="bar-chart">
                ${communities.map(c => {
                    const max = communities[0]?.users || 1;
                    const pct = (c.users / max * 100).toFixed(0);
                    return `
                    <div class="bar-row" onclick="searchTag('${esc(c.hashtag)}')">
                        <span class="bar-label">#${esc(c.hashtag)}</span>
                        <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
                        <span class="bar-value">${c.users}</span>
                    </div>`;
                }).join('')}
            </div>
            <p class="card-summary">Distribución global de comunidades temáticas. Cada barra muestra cuántos usuarios participan en un hashtag. Haz clic en "Mis Comunidades" para ver cómo te posicionas tú en estas comunidades.</p>
        </div>`;
}

// --- My Network tab (ego graph) ---
function renderMyNetwork() {
    const ego = neo4jData.ego || {};
    const center = ego.center;
    const neighbors = ego.neighbors || [];
    const hop1 = neighbors.filter(n => n.dist === 1);
    const hop2 = neighbors.filter(n => n.dist === 2);

    return `
        <div class="panel-card">
            <h3>Tu Red Social <span class="query-badge">Ego Network</span></h3>
            <div class="cyto-container" id="ego-cyto"></div>
            <div class="graph-legend">
                <span><span class="legend-dot" style="background:#1da1f2"></span> Tú</span>
                <span><span class="legend-dot" style="background:#17bf63"></span> 1 salto (${hop1.length})</span>
                <span><span class="legend-dot" style="background:#e67e22"></span> 2 saltos (${hop2.length})</span>
                <span class="text-secondary" style="font-size:11px">Arrastra nodos · Scroll para zoom</span>
            </div>
            <p class="card-summary">Visualización interactiva de tu red ego. Tus conexiones directas (1 salto) en verde y las de tus conexiones (2 saltos) en naranja. Los nodos más grandes tienen más seguidores. Haz clic en un nodo para ver su perfil.</p>
        </div>
        <div class="panel-card">
            <h3>Conexiones Directas</h3>
            <div class="user-list">
                ${hop1.slice(0, 12).map(n => `
                    <div class="follow-item" onclick="loadProfile('${n.id}')" style="cursor:pointer">
                        <div class="avatar" style="background:var(--success);color:white">${(n.username || '?').charAt(0).toUpperCase()}</div>
                        <div class="follow-info">
                            <div class="follow-name">${esc(n.name || n.username)}</div>
                            <div class="follow-username">@${esc(n.username)} · ${n.followers} seguidores · ${n.posts || 0} posts</div>
                        </div>
                    </div>`).join('')}
            </div>
        </div>`;
}

function drawEgoGraph() {
    const container = document.getElementById('ego-cyto');
    if (!container) return;
    const ego = neo4jData.ego || {};
    const center = ego.center;
    const neighbors = ego.neighbors || [];
    const edges = ego.edges || [];

    if (!center) {
        container.innerHTML = '<div class="text-secondary" style="display:flex;align-items:center;justify-content:center;height:100%">No hay datos de red disponibles</div>';
        return;
    }

    const allNodes = [{ ...center, dist: 0 }, ...neighbors];
    const maxF = Math.max(...allNodes.map(n => n.followers || 1), 1);
    const nodeIds = new Set(allNodes.map(n => n.id));

    const elements = [];
    allNodes.forEach(n => {
        const size = n.dist === 0 ? 40 : 14 + ((n.followers || 0) / maxF) * 26;
        const color = n.dist === 0 ? '#1da1f2' : n.dist === 1 ? '#17bf63' : '#e67e22';
        elements.push({
            data: { id: n.id, label: n.dist === 0 ? 'TU' : (n.username || '').split('_')[0], fullname: n.username || '', dist: n.dist, nodeSize: size, nodeColor: color },
        });
    });
    edges.forEach((e, i) => {
        if (nodeIds.has(e.source) && nodeIds.has(e.target)) {
            elements.push({ data: { id: 'e' + i, source: e.source, target: e.target } });
        }
    });

    const cy = cytoscape({
        container,
        elements,
        style: [
            { selector: 'node', style: {
                'width': 'data(nodeSize)', 'height': 'data(nodeSize)',
                'background-color': 'data(nodeColor)',
                'label': 'data(label)', 'font-size': 9, 'color': '#d9d9d9',
                'text-valign': 'bottom', 'text-margin-y': 6,
                'border-width': 1.5, 'border-color': 'rgba(255,255,255,0.2)',
            }},
            { selector: 'node[dist = 0]', style: {
                'font-size': 12, 'font-weight': 'bold', 'color': '#fff',
                'border-width': 3, 'border-color': 'rgba(29,161,242,0.5)',
            }},
            { selector: 'edge', style: {
                'width': 1, 'line-color': 'rgba(56,68,77,0.5)',
                'curve-style': 'bezier', 'target-arrow-shape': 'triangle',
                'target-arrow-color': 'rgba(56,68,77,0.5)', 'arrow-scale': 0.6,
            }},
            { selector: 'node:active', style: { 'overlay-opacity': 0.15 }},
        ],
        layout: { name: 'concentric', concentric: n => n.data('dist') === 0 ? 3 : n.data('dist') === 1 ? 2 : 1, levelWidth: () => 1, minNodeSpacing: 20, animate: true, animationDuration: 600 },
        minZoom: 0.4, maxZoom: 3, userPanningEnabled: true, userZoomingEnabled: true,
    });

    cy.on('tap', 'node', evt => {
        const id = evt.target.id();
        if (id !== currentUserId()) loadProfile(id);
    });
}

// --- My Communities tab ---
function renderMyCommunities() {
    const myCom = asList(neo4jData.myCommunities);
    const overlap = asList(neo4jData.overlap);

    let overlapHtml = '';
    if (!overlap.error && overlap.length) {
        overlapHtml = `
        <div class="panel-card">
            <h3>Afinidad con Usuarios Cercanos <span class="query-badge">Overlap</span></h3>
            <table class="data-table">
                <thead><tr><th>Usuario</th><th>Comunidades compartidas</th><th>Relación</th></tr></thead>
                <tbody>
                    ${overlap.slice(0, 12).map(u => {
                        const rel = u.i_follow && u.follows_me ? 'Mutuo' : u.i_follow ? 'Le sigues' : u.follows_me ? 'Te sigue' : 'Sin conexión';
                        const relColor = u.i_follow && u.follows_me ? 'var(--success)' : u.i_follow || u.follows_me ? 'var(--accent)' : 'var(--text-secondary)';
                        return `
                        <tr onclick="loadProfile('${u.id}')" style="cursor:pointer">
                            <td><strong>${esc(u.username)}</strong></td>
                            <td>
                                <div style="display:flex;align-items:center;gap:8px">
                                    <div class="mini-bar"><div class="mini-bar-fill" style="width:${(u.overlap / (overlap[0]?.overlap || 1) * 100).toFixed(0)}%"></div></div>
                                    <span>${u.overlap}</span>
                                </div>
                                <div class="text-secondary" style="font-size:11px;margin-top:2px">${u.shared.slice(0, 4).map(t => '#' + t).join(' ')}</div>
                            </td>
                            <td><span style="color:${relColor};font-size:12px">${rel}</span></td>
                        </tr>`;
                    }).join('')}
                </tbody>
            </table>
            <p class="card-summary">Los usuarios con más comunidades compartidas contigo son los que más afinidad temática tienen. Si no les sigues, son candidatos ideales para una nueva conexión. La columna "Relación" muestra si ya hay un vínculo FOLLOWS entre vosotros.</p>
        </div>`;
    }

    return `
        <div class="panel-card">
            <h3>Tus Comunidades <span class="query-badge">INTERESTED_IN</span></h3>
            <div class="cyto-container" id="community-cyto"></div>
            <div class="graph-legend">
                <span><span class="legend-dot" style="background:#1da1f2"></span> Tú</span>
                <span><span class="legend-dot" style="background:#9b59b6"></span> Hashtag</span>
                <span><span class="legend-dot" style="background:#17bf63"></span> Miembros</span>
                <span class="text-secondary" style="font-size:11px">Arrastra nodos · Scroll para zoom</span>
            </div>
            ${(myCom.error || !myCom.length) ? '<p class="text-secondary" style="padding:12px">No perteneces a ninguna comunidad aún. Publica posts con hashtags para unirte.</p>' : `
            <div style="margin-top:12px">
                ${myCom.map(c => `
                <div class="community-card">
                    <div class="community-header">
                        <span class="community-tag" onclick="searchTag('${esc(c.hashtag)}')">#${esc(c.hashtag)}</span>
                        <span class="text-secondary">${c.size} miembros</span>
                    </div>
                    <div class="community-members">
                        ${(c.top_members || []).map(m => `<span class="member-chip" onclick="loadProfile('${m.id}')" title="${esc(m.username)}">@${esc(m.username)}</span>`).join('')}
                    </div>
                </div>`).join('')}
            </div>`}
            <p class="card-summary">Cada comunidad es un hashtag que has usado, junto con los usuarios que también lo usan. El grafo muestra tu posición central conectada a cada comunidad temática. Cuanto más grande el nodo hashtag, más miembros tiene la comunidad.</p>
        </div>
        ${overlapHtml}`;
}

function drawCommunityGraph() {
    const container = document.getElementById('community-cyto');
    if (!container) return;
    const myCom = asList(neo4jData.myCommunities);
    if (myCom.error || !myCom.length) {
        container.innerHTML = '<div class="text-secondary" style="display:flex;align-items:center;justify-content:center;height:100%">Publica posts con hashtags para ver tu mapa de comunidades</div>';
        return;
    }

    const elements = [];
    const maxSize = myCom[0]?.size || 1;

    // Center node
    elements.push({ data: { id: 'me', label: 'TU', nodeType: 'me', nodeSize: 40, nodeColor: '#1da1f2' } });

    myCom.forEach(c => {
        const hId = 'h_' + c.hashtag;
        const size = 20 + (c.size / maxSize) * 30;
        elements.push({ data: { id: hId, label: '#' + c.hashtag, nodeType: 'hashtag', nodeSize: size, nodeColor: '#9b59b6' } });
        elements.push({ data: { source: 'me', target: hId } });

        (c.top_members || []).slice(0, 4).forEach(m => {
            const mId = m.id;
            // Avoid duplicate member nodes
            if (!elements.find(e => e.data.id === mId)) {
                elements.push({ data: { id: mId, label: '@' + (m.username || '').split('_')[0], nodeType: 'member', nodeSize: 14, nodeColor: '#17bf63', fullname: m.username } });
            }
            elements.push({ data: { source: hId, target: mId } });
        });
    });

    const cy = cytoscape({
        container,
        elements,
        style: [
            { selector: 'node', style: {
                'width': 'data(nodeSize)', 'height': 'data(nodeSize)',
                'background-color': 'data(nodeColor)',
                'label': 'data(label)', 'font-size': 9, 'color': '#d9d9d9',
                'text-valign': 'bottom', 'text-margin-y': 5,
                'border-width': 1, 'border-color': 'rgba(255,255,255,0.15)',
            }},
            { selector: 'node[nodeType = "me"]', style: {
                'font-size': 13, 'font-weight': 'bold', 'color': '#fff',
                'border-width': 3, 'border-color': 'rgba(29,161,242,0.5)',
            }},
            { selector: 'node[nodeType = "hashtag"]', style: {
                'font-size': 10, 'font-weight': 'bold', 'color': '#c39bd3',
            }},
            { selector: 'edge', style: {
                'width': 1.5, 'line-color': 'rgba(155,89,182,0.3)',
                'curve-style': 'bezier',
            }},
        ],
        layout: { name: 'concentric', concentric: n => n.data('nodeType') === 'me' ? 3 : n.data('nodeType') === 'hashtag' ? 2 : 1, levelWidth: () => 1, minNodeSpacing: 15, animate: true, animationDuration: 600 },
        minZoom: 0.4, maxZoom: 3,
    });

    cy.on('tap', 'node', evt => {
        const n = evt.target;
        if (n.data('nodeType') === 'member') loadProfile(n.id());
        if (n.data('nodeType') === 'hashtag') searchTag(n.data('label').replace('#', ''));
    });
}

// --- Influencers & Bridges tab ---
function renderInfluenceBridges() {
    const influencers = asList(neo4jData.influencers);
    const bridges = asList(neo4jData.bridges);
    const intermediate = Boolean(neo4jData.labStatus?.neo4j?.intermediate);
    return `
        <div class="panel-card">
            <h3>Top Influencers <span class="query-badge">In-degree</span></h3>
            <table class="data-table">
                <thead><tr><th>Usuario</th><th>Seguidores</th><th>Posts</th></tr></thead>
                <tbody>
                    ${influencers.map(u => `
                        <tr onclick="loadProfile('${u.id}')" style="cursor:pointer">
                            <td><strong>${esc(u.username || '')}</strong><br><span class="text-secondary">${esc(u.name || '')}</span></td>
                            <td>${u.followers}</td>
                            <td>${u.posts || 0}</td>
                        </tr>`).join('')}
                </tbody>
            </table>
            <p class="card-summary">Los influencers se identifican contando relaciones entrantes FOLLOWS (in-degree). En grafos reales se usaría PageRank, pero el conteo directo de seguidores ya revela quién concentra más atención en la red.</p>
        </div>
        ${intermediate ? `
        <div class="panel-card">
            <h3>Usuarios Puente <span class="query-badge">Betweenness</span></h3>
            <table class="data-table">
                <thead><tr><th>Usuario</th><th>Temas</th><th>Seguidores</th><th>Tags</th></tr></thead>
                <tbody>
                    ${bridges.map(b => `
                        <tr>
                            <td><strong>${esc(b.username || '')}</strong></td>
                            <td>${b.tag_count}</td>
                            <td>${b.followers}</td>
                            <td class="text-secondary">${(b.tags || []).slice(0, 4).map(t => '#' + t).join(', ')}</td>
                        </tr>`).join('')}
                </tbody>
            </table>
            <p class="card-summary">Los usuarios puente participan en 3+ comunidades temáticas distintas y además tienen seguidores. Son clave para la difusión de información entre grupos: si un usuario puente publica algo, tiene alcance en múltiples comunidades a la vez.</p>
        </div>` : ''}`;
}

// --- Explore Graph tab ---
function renderExploreGraph() {
    const mutual = asList(neo4jData.mutual);
    const intermediate = Boolean(neo4jData.labStatus?.neo4j?.intermediate);
    const advanced = Boolean(neo4jData.labStatus?.neo4j?.advanced);
    return `
        ${advanced ? `
        <div class="panel-card">
            <h3>Camino Más Corto <span class="query-badge">shortestPath</span></h3>
            <div style="display:flex;gap:8px;align-items:center">
                <input class="search-box" id="path-from" placeholder="ID o username" value="${esc(currentUser.username || currentUserId())}" style="flex:1">
                <span style="color:var(--text-secondary)">→</span>
                <input class="search-box" id="path-to" placeholder="ej: rosalia, ibai, shakira" style="flex:1">
                <button class="btn" onclick="findPath()">Buscar</button>
            </div>
            <div id="path-result" style="margin-top:12px"></div>
            <p class="card-summary">Puedes escribir un username como <code>rosalia</code> o un id interno como <code>u_inf_003</code>. Usa shortestPath de Neo4j para encontrar la cadena más corta de relaciones FOLLOWS entre dos usuarios (máx. 6 saltos).</p>
        </div>` : ''}
        ${intermediate ? `
        <div class="panel-card">
            <h3>Intereses en Común <span class="query-badge">Pattern Match</span></h3>
            ${(!mutual.error && mutual.length) ? mutual.map(u => `
                <div class="follow-item" onclick="loadProfile('${u.id}')" style="cursor:pointer">
                    <div class="avatar">${(u.username || '?').charAt(0).toUpperCase()}</div>
                    <div class="follow-info">
                        <div class="follow-name">${esc(u.username)}</div>
                        <div class="follow-username">${u.shared_count} hashtags: ${u.shared_tags.slice(0, 4).map(t => '#' + t).join(', ')}</div>
                    </div>
                </div>`).join('') : '<p class="text-secondary" style="padding:8px">No hay datos de intereses compartidos</p>'}
            <p class="card-summary">Usuarios que comparten hashtags contigo: (tú)-[:INTERESTED_IN]->(hashtag)<-[:INTERESTED_IN]-(otro). Cuantos más hashtags compartan, mayor afinidad temática.</p>
        </div>` : ''}`;
}

async function findPath() {
    const from = document.getElementById('path-from').value.trim();
    const to = document.getElementById('path-to').value.trim();
    if (!from || !to) return;
    const container = document.getElementById('path-result');
    container.innerHTML = '<div class="loading">Buscando...</div>';

    const res = await fetch(`${API}/analytics/neo4j/shortest-path?from_user=${encodeURIComponent(from)}&to_user=${encodeURIComponent(to)}`);
    const data = await res.json();

    if (data.error || !data.length) {
        container.innerHTML = `
            <div class="text-secondary">
                No se encontro camino entre estos usuarios. Si estas usando una cuenta nueva, prueba primero <strong>Simular audiencia demo</strong> en el radar.
            </div>`;
        return;
    }
    const path = data[0].path || [];
    container.innerHTML = `
        <div class="path-display">
            <span class="text-secondary">Distancia: ${data[0].distance} saltos</span><br>
            ${path.map((n, i) => `<span class="path-node" onclick="loadProfile('${n.id}')">${esc(n.username)}</span>${i < path.length - 1 ? ' → ' : ''}`).join('')}
        </div>`;
}

// --- Hashtag Map tab ---
function renderHashtagMap() {
    const hg = asList(neo4jData.hashgraph);
    return `
        <div class="panel-card">
            <h3>Mapa de Co-ocurrencia <span class="query-badge">Graph Pattern</span></h3>
            <div class="cyto-container" id="hashtag-cyto"></div>
            <div class="graph-legend">
                <span><span class="legend-dot" style="background:#9b59b6"></span> Hashtag</span>
                <span class="text-secondary">Línea más gruesa = más usuarios en común · Arrastra nodos · Scroll para zoom</span>
            </div>
            <p class="card-summary">Dos hashtags se conectan cuando los mismos usuarios los usan. Líneas más gruesas indican mayor co-ocurrencia. Los clusters de hashtags cercanos revelan temas relacionados — la base de sistemas de recomendación tipo "si te interesa X, probablemente te interese Y".</p>
        </div>
        <div class="panel-card">
            <h3>Tabla de Co-ocurrencia</h3>
            <table class="data-table">
                <thead><tr><th>Hashtag A</th><th>Hashtag B</th><th>Usuarios en común</th></tr></thead>
                <tbody>
                    ${(hg || []).slice(0, 15).map(h => `
                        <tr>
                            <td onclick="searchTag('${esc(h.tag1)}')" style="cursor:pointer;color:var(--accent)">#${esc(h.tag1)}</td>
                            <td onclick="searchTag('${esc(h.tag2)}')" style="cursor:pointer;color:var(--accent)">#${esc(h.tag2)}</td>
                            <td>${h.shared_users}</td>
                        </tr>`).join('')}
                </tbody>
            </table>
        </div>`;
}

function drawHashtagGraph() {
    const container = document.getElementById('hashtag-cyto');
    if (!container) return;
    const hg = asList(neo4jData.hashgraph);
    if (hg.error || !hg.length) {
        container.innerHTML = '<div class="text-secondary" style="display:flex;align-items:center;justify-content:center;height:100%">No hay datos de co-ocurrencia</div>';
        return;
    }

    const tagDeg = {};
    hg.forEach(h => {
        tagDeg[h.tag1] = (tagDeg[h.tag1] || 0) + h.shared_users;
        tagDeg[h.tag2] = (tagDeg[h.tag2] || 0) + h.shared_users;
    });
    const maxDeg = Math.max(...Object.values(tagDeg), 1);
    const maxShared = Math.max(...hg.map(h => h.shared_users), 1);
    const colors = ['#9b59b6', '#e74c3c', '#3498db', '#e67e22', '#1abc9c', '#f39c12', '#2ecc71', '#e91e63', '#8e44ad', '#16a085'];

    const elements = [];
    const addedTags = new Set();
    let colorIdx = 0;

    hg.forEach(h => {
        [h.tag1, h.tag2].forEach(t => {
            if (!addedTags.has(t)) {
                addedTags.add(t);
                const size = 18 + (tagDeg[t] / maxDeg) * 35;
                elements.push({ data: { id: t, label: '#' + t, nodeSize: size, nodeColor: colors[colorIdx % colors.length] } });
                colorIdx++;
            }
        });
        const w = 1 + (h.shared_users / maxShared) * 6;
        const alpha = 0.2 + (h.shared_users / maxShared) * 0.6;
        elements.push({ data: { source: h.tag1, target: h.tag2, weight: w, edgeAlpha: alpha, shared: h.shared_users } });
    });

    const cy = cytoscape({
        container,
        elements,
        style: [
            { selector: 'node', style: {
                'width': 'data(nodeSize)', 'height': 'data(nodeSize)',
                'background-color': 'data(nodeColor)',
                'label': 'data(label)', 'font-size': 10, 'font-weight': 'bold',
                'color': '#d9d9d9', 'text-valign': 'bottom', 'text-margin-y': 6,
                'border-width': 2, 'border-color': 'rgba(255,255,255,0.15)',
            }},
            { selector: 'edge', style: {
                'width': 'data(weight)',
                'line-color': 'rgba(155,89,182,0.35)',
                'curve-style': 'bezier',
            }},
        ],
        layout: { name: 'cose', idealEdgeLength: 120, nodeRepulsion: 6000, edgeElasticity: 80, gravity: 0.3, animate: true, animationDuration: 800, randomize: true },
        minZoom: 0.3, maxZoom: 3,
    });

    cy.on('tap', 'node', evt => searchTag(evt.target.id()));
}


// ========================================================
// SPARK/ML PANEL
// ========================================================

// ML data cache
let mlData = { metrics: null, spam: null, clusters: null, recs: null, churn: null };
let mlActiveTab = 'overview';

const mlTabs = [
    { id: 'overview', label: 'Resumen' },
    { id: 'spam', label: 'Spam Detector', model: 'spam_detector' },
    { id: 'engagement', label: 'Engagement', model: 'engagement_predictor' },
    { id: 'virality', label: 'Viralidad', model: 'virality_classifier' },
    { id: 'clusters', label: 'Clustering', model: 'user_clustering' },
    { id: 'recommender', label: 'Recomendaciones', model: 'follow_recommender' },
    { id: 'churn', label: 'Churn', model: 'churn_predictor' },
];

function hasModelResult(modelName) {
    const model = mlData.metrics?.[modelName];
    return Boolean(model && !model.error);
}

async function loadSparkPanel() {
    document.getElementById('feed-header').textContent = 'Spark/ML — Modelos';
    document.getElementById('feed-content').innerHTML = '<div class="loading">Cargando métricas...</div>';

    const [metricsRes, spamRes, clustersRes, recsRes, churnRes, examplesRes] = await Promise.all([
        fetch(`${API}/analytics/ml/metrics`).then(r => r.json()).catch(() => null),
        fetch(`${API}/analytics/ml/spam/predictions`).then(r => r.json()).catch(() => null),
        fetch(`${API}/analytics/ml/clusters`).then(r => r.json()).catch(() => null),
        fetch(`${API}/analytics/ml/recommendations/${currentUserId()}`).then(r => r.json()).catch(() => null),
        fetch(`${API}/analytics/ml/churn/at-risk`).then(r => r.json()).catch(() => null),
        fetch(`${API}/analytics/ml/post-examples/${currentUserId()}`).then(r => r.json()).catch(() => null),
    ]);

    if (!metricsRes || metricsRes?.error) {
        document.getElementById('feed-content').innerHTML = `
            <div class="analytics-panel">
                <div class="panel-card error-card">
                    <h3>Modelos no entrenados</h3>
                    <p>Completa los scaffolds de ML en estos archivos:</p>
                    <ul class="exercise-list">
                        <li><strong>Spam detector:</strong> <code>src/spark/models_ex/spam_detector.py</code></li>
                        <li><strong>Engagement predictor:</strong> <code>src/spark/models_ex/engagement_predictor.py</code></li>
                        <li><strong>Virality classifier:</strong> <code>src/spark/models_ex/virality_classifier.py</code></li>
                        <li><strong>Churn predictor:</strong> <code>src/spark/models_ex/churn_predictor.py</code></li>
                        <li><strong>User clustering:</strong> <code>src/spark/models_ex/user_clustering.py</code></li>
                        <li><strong>Follow recommender:</strong> <code>src/spark/models_ex/follow_recommender.py</code></li>
                    </ul>
                    <p>Despues ejecuta <code>./lab.sh train</code> y recarga esta vista.</p>
                    ${metricsRes?.error ? `<p class="error-detail">${esc(metricsRes.error)}</p>` : ''}
                </div>
            </div>`;
        return;
    }

    mlData = { metrics: metricsRes, spam: spamRes, clusters: clustersRes, recs: recsRes, churn: churnRes, examples: examplesRes?.examples || {} };
    mlActiveTab = 'overview';
    renderSparkPanel();
}

function renderSparkPanel() {
    const tabs = mlTabs.filter(t => !t.model || hasModelResult(t.model));
    if (!tabs.some(t => t.id === mlActiveTab)) {
        mlActiveTab = 'overview';
    }

    const tabsHtml = `
        <div class="ml-tabs">
            ${tabs.map(t => `<button class="ml-tab${mlActiveTab === t.id ? ' active' : ''}" onclick="switchMlTab('${t.id}')">${t.label}</button>`).join('')}
        </div>`;

    let content = '';
    switch (mlActiveTab) {
        case 'overview': content = renderMlOverview(); break;
        case 'spam': content = renderSpamTab(); break;
        case 'engagement': content = renderEngagementTab(); break;
        case 'virality': content = renderViralityTab(); break;
        case 'clusters': content = renderClustersTab(); break;
        case 'recommender': content = renderRecommenderTab(); break;
        case 'churn': content = renderChurnTab(); break;
    }

    document.getElementById('feed-content').innerHTML = `
        <div class="analytics-panel">
            ${tabsHtml}
            ${content}
        </div>`;
}

function switchMlTab(tab) {
    mlActiveTab = tab;
    renderSparkPanel();
}

function getModelData(name) {
    if (!mlData.metrics) return null;
    return mlData.metrics[name] || null;
}

function renderModelCard(name, model) {
    if (!model) return '<div class="panel-card"><p class="text-secondary">Modelo no disponible</p></div>';
    if (model.error) {
        return `
            <div class="panel-card error-card">
                <h3>${esc(name)}</h3>
                <p>Este modelo no tiene resultados disponibles.</p>
                <p class="error-detail">${esc(model.message || model.error)}</p>
            </div>`;
    }

    let metric = '', value = '';
    if (model.auc !== undefined) { metric = 'AUC'; value = model.auc; }
    else if (model.r2 !== undefined) { metric = 'R²'; value = model.r2; }
    else if (model.best_k !== undefined) { metric = 'k'; value = model.best_k; }
    else if (model.total_recommendations !== undefined) { metric = 'Recs'; value = model.total_recommendations; }
    const color = typeof value === 'number' ? (value >= 0.8 ? 'var(--success)' : value >= 0.5 ? 'orange' : 'var(--like)') : 'var(--text)';

    let metricsHtml = `
        <div class="stats-grid" style="margin-bottom:16px">
            <div class="stat-item"><div class="stat-value" style="color:${color}">${typeof value === 'number' ? value.toFixed(4) : value}</div><div class="stat-label">${metric}</div></div>
            <div class="stat-item"><div class="stat-value">${esc(model.algorithm || 'N/A')}</div><div class="stat-label">Algoritmo</div></div>
        </div>`;

    // Extra metrics
    const extras = [];
    if (model.accuracy !== undefined) extras.push(['Accuracy', model.accuracy]);
    if (model.precision !== undefined) extras.push(['Precision', model.precision]);
    if (model.recall !== undefined) extras.push(['Recall', model.recall]);
    if (model.f1 !== undefined) extras.push(['F1', model.f1]);
    if (model.rmse !== undefined) extras.push(['RMSE', model.rmse]);
    if (model.mae !== undefined) extras.push(['MAE', model.mae]);
    if (model.best_silhouette !== undefined) extras.push(['Silhouette', model.best_silhouette]);

    if (extras.length) {
        metricsHtml += `
            <div class="stats-grid">
                ${extras.map(([label, val]) => `<div class="stat-item"><div class="stat-value" style="font-size:16px">${typeof val === 'number' ? val.toFixed(4) : val}</div><div class="stat-label">${label}</div></div>`).join('')}
            </div>`;
    }

    // Feature importance
    let fiHtml = '';
    if (model.feature_importance) {
        const entries = Object.entries(model.feature_importance).sort((a, b) => b[1] - a[1]);
        const maxImp = entries[0]?.[1] || 1;
        fiHtml = `
            <h4 style="margin-top:16px">Feature Importance</h4>
            <div class="bar-chart">
                ${entries.map(([feat, imp]) => {
                    const pct = (imp / maxImp * 100).toFixed(0);
                    return `
                    <div class="bar-row">
                        <span class="bar-label">${esc(feat)}</span>
                        <div class="bar-track"><div class="bar-fill accent" style="width:${pct}%"></div></div>
                        <span class="bar-value">${imp.toFixed(4)}</span>
                    </div>`;
                }).join('')}
            </div>`;
    }

    return metricsHtml + fiHtml;
}

const modelDescriptions = {
    spam_detector: 'Clasifica usuarios como spam o legítimos usando RandomForest sobre features de comportamiento (frecuencia de posts, ratio de textos únicos, ratio follow/followers). AUC mide el área bajo la curva ROC: 1.0 = perfecto, 0.5 = azar.',
    engagement_predictor: 'Predice cuántos likes recibirá un post usando GBT (Gradient Boosted Trees). R² indica qué porcentaje de la variación en likes explica el modelo. Un R² bajo significa que los likes son difíciles de predecir — dependen de factores no capturados (timing, contenido).',
    virality_classifier: 'Clasifica posts como virales (likes > percentil 90) o normales usando Regresión Logística. Un AUC de 0.6 indica baja capacidad predictiva: la viralidad es inherentemente impredecible con features estructurales simples.',
    follow_recommender: 'Sistema híbrido (no ML puro): 60% hashtags compartidos + 40% amigos-de-amigos. Genera top-10 recomendaciones por usuario. El score combina afinidad temática con proximidad social.',
    user_clustering: 'Agrupa usuarios por comportamiento similar usando K-Means. La k óptima se elige por silueta (cohesión interna vs separación entre clusters). Los clusters revelan arquetipos: power users, lurkers, creadores, etc.',
    churn_predictor: 'Predice qué usuarios van a abandonar la plataforma (sin posts en 30 días) con GBT. AUC=1.0 indica que la feature days_since_last_post domina — el modelo es trivial pero funciona como ejemplo didáctico.',
};

function renderMlOverview() {
    if (!mlData.metrics) return '';
    const models = Object.entries(mlData.metrics).filter(([_, m]) => !m.error);
    const failed = Object.entries(mlData.metrics).filter(([_, m]) => m.error);

    if (!models.length) {
        return `
            <div class="panel-card error-card">
                <h3>Modelos sin resultados</h3>
                <p>No hay ningun modelo entrenado correctamente todavia.</p>
                ${failed.length ? `
                    <table class="data-table" style="margin-top:12px">
                        <thead><tr><th>Modelo</th><th>Estado</th></tr></thead>
                        <tbody>
                            ${failed.map(([name, m]) => `
                                <tr>
                                    <td><strong>${esc(name)}</strong></td>
                                    <td class="text-secondary">${esc(m.message || m.error)}</td>
                                </tr>`).join('')}
                        </tbody>
                    </table>
                ` : ''}
                <p style="margin-top:12px">Ejecuta <code>./lab.sh train</code> despues de desbloquear o implementar ML.</p>
            </div>`;
    }

    return `
        <div class="panel-card">
            <h3>Resumen de Modelos</h3>
            <p class="text-secondary" style="margin-bottom:12px">Haz clic en una pestaña para ver el análisis detallado de cada modelo.</p>
            <table class="data-table">
                <thead><tr><th>Modelo</th><th>Algoritmo</th><th>Métrica</th><th>Valor</th></tr></thead>
                <tbody>
                    ${models.map(([name, m]) => {
                        let metric = '', value = '';
                        if (m.auc !== undefined) { metric = 'AUC'; value = m.auc; }
                        else if (m.r2 !== undefined) { metric = 'R²'; value = m.r2; }
                        else if (m.best_k !== undefined) { metric = 'k'; value = m.best_k; }
                        else if (m.total_recommendations !== undefined) { metric = 'Recs'; value = m.total_recommendations; }
                        const color = typeof value === 'number' ? (value >= 0.8 ? 'var(--success)' : value >= 0.5 ? 'orange' : 'var(--like)') : 'var(--text)';
                        const tabMap = { spam_detector: 'spam', engagement_predictor: 'engagement', virality_classifier: 'virality', user_clustering: 'clusters', follow_recommender: 'recommender', churn_predictor: 'churn' };
                        return `
                        <tr style="cursor:pointer" onclick="switchMlTab('${tabMap[name] || 'overview'}')">
                            <td><strong>${esc(name)}</strong></td>
                            <td class="text-secondary">${esc(m.algorithm || '')}</td>
                            <td>${metric}</td>
                            <td style="color:${color};font-weight:bold">${typeof value === 'number' ? value.toFixed(4) : value}</td>
                        </tr>`;
                    }).join('')}
                </tbody>
            </table>
            <p class="card-summary">Todos los modelos se entrenan con Spark MLlib sobre los datos gold del data lake. El color indica calidad: verde (>0.8) buena, naranja (0.5-0.8) moderada, rojo (&lt;0.5) baja. Haz clic en cualquier fila para ver el detalle del modelo.</p>
        </div>`;
}

function renderSpamTab() {
    const model = getModelData('spam_detector');
    const spam = mlData.spam;
    let resultsHtml = '';
    if (spam && !spam.error) {
        const total = spam.total_spam + spam.total_legit;
        const spamPct = total > 0 ? ((spam.total_spam / total) * 100).toFixed(1) : 0;
        resultsHtml = `
            <div class="stats-grid" style="margin:16px 0">
                <div class="stat-item"><div class="stat-value" style="color:var(--like)">${spam.total_spam}</div><div class="stat-label">Spam detectado</div></div>
                <div class="stat-item"><div class="stat-value" style="color:var(--success)">${spam.total_legit}</div><div class="stat-label">Legítimos</div></div>
                <div class="stat-item"><div class="stat-value">${spamPct}%</div><div class="stat-label">Ratio spam</div></div>
            </div>
            <h4>Usuarios marcados como spam:</h4>
            <div class="user-list">
                ${(spam.spam_detected || []).slice(0, 10).map(u => `
                    <div class="follow-item">
                        <div class="avatar" style="background:var(--spam);color:white">!</div>
                        <div class="follow-info">
                            <div class="follow-name">${esc(u.username)}</div>
                            <div class="follow-username">Etiqueta real: ${u.label === 1 ? 'spam' : 'legítimo'}</div>
                        </div>
                    </div>`).join('')}
            </div>`;
    }
    // Real post examples
    const spamExamples = (mlData.examples?.spam || []);
    let examplesHtml = '';
    if (spamExamples.length) {
        examplesHtml = `
            <h4 style="margin-top:20px">Ejemplos de tu red</h4>
            <div class="ml-examples">
                ${spamExamples.map(e => `
                    <div class="ml-example ${e.prediction === 'spam' ? 'ml-example-bad' : 'ml-example-good'}">
                        <div class="ml-example-header">
                            <span class="ml-example-user">@${esc(e.username)}</span>
                            <span class="ml-example-tag ${e.prediction === 'spam' ? 'tag-spam' : 'tag-legit'}">${e.prediction === 'spam' ? '🚫 SPAM' : '✅ Legítimo'}</span>
                        </div>
                        <div class="ml-example-text">"${esc(e.text)}"</div>
                        <div class="ml-example-meta">
                            <span>♥ ${e.likes}</span>
                            <span>Confianza: ${(e.confidence * 100).toFixed(0)}%</span>
                        </div>
                        <div class="ml-example-reason">${esc(e.reason)}</div>
                    </div>`).join('')}
            </div>`;
    }
    return `
        <div class="panel-card">
            <h3>Spam Detector <span class="query-badge">RandomForest</span></h3>
            ${renderModelCard('spam_detector', model)}
            ${resultsHtml}
            ${examplesHtml}
            <p class="card-summary">${modelDescriptions.spam_detector}</p>
        </div>`;
}

function renderEngagementTab() {
    const model = getModelData('engagement_predictor');
    const examples = (mlData.examples?.engagement || []);
    let examplesHtml = '';
    if (examples.length) {
        examplesHtml = `
            <h4 style="margin-top:20px">Predicción vs Realidad — Posts de tu red</h4>
            <table class="data-table">
                <thead><tr><th>Post</th><th>Predicho</th><th>Real</th><th>Error</th></tr></thead>
                <tbody>
                    ${examples.map(e => {
                        const diff = e.actual_likes - e.predicted_likes;
                        const diffColor = Math.abs(diff) <= 5 ? 'var(--success)' : Math.abs(diff) <= 15 ? 'orange' : 'var(--like)';
                        return `
                        <tr>
                            <td>
                                <div style="font-weight:600;font-size:12px">@${esc(e.username)}</div>
                                <div class="text-secondary" style="font-size:11px;max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(e.text)}</div>
                            </td>
                            <td style="text-align:center">♥ ${e.predicted_likes}</td>
                            <td style="text-align:center;font-weight:bold">♥ ${e.actual_likes}</td>
                            <td style="text-align:center;color:${diffColor}">${diff > 0 ? '+' : ''}${diff}</td>
                        </tr>`;
                    }).join('')}
                </tbody>
            </table>
            <div class="text-secondary" style="font-size:11px;margin-top:8px">Features: followers_count, num_hashtags, text_length, posts_per_day, avg_likes_received</div>`;
    }
    return `
        <div class="panel-card">
            <h3>Engagement Predictor <span class="query-badge">GBT Regression</span></h3>
            ${renderModelCard('engagement_predictor', model)}
            ${examplesHtml}
            <p class="card-summary">${modelDescriptions.engagement_predictor}</p>
        </div>`;
}

function renderViralityTab() {
    const model = getModelData('virality_classifier');
    const examples = (mlData.examples?.virality || []);
    let examplesHtml = '';
    if (examples.length) {
        examplesHtml = `
            <h4 style="margin-top:20px">Clasificación de Viralidad — Posts de tu red</h4>
            <div class="ml-examples">
                ${examples.map(e => `
                    <div class="ml-example ${e.is_viral ? 'ml-example-viral' : ''}">
                        <div class="ml-example-header">
                            <span class="ml-example-user">@${esc(e.username)}</span>
                            <span class="ml-example-tag ${e.is_viral ? 'tag-viral' : 'tag-normal'}">${e.is_viral ? '🔥 Viral' : '📊 Normal'}</span>
                            <span class="text-secondary" style="font-size:11px">P(viral) = ${(e.viral_probability * 100).toFixed(0)}%</span>
                        </div>
                        <div class="ml-example-text">"${esc(e.text)}"</div>
                        <div class="ml-example-meta">
                            <span>♥ ${e.likes}</span>
                            ${(e.hashtags || []).map(h => '<span class="mini-tag">#' + esc(h) + '</span>').join('')}
                        </div>
                        <div class="ml-example-reason">${esc(e.reason)}</div>
                    </div>`).join('')}
            </div>`;
    }
    return `
        <div class="panel-card">
            <h3>Virality Classifier <span class="query-badge">LogisticRegression</span></h3>
            ${renderModelCard('virality_classifier', model)}
            ${examplesHtml}
            <p class="card-summary">${modelDescriptions.virality_classifier}</p>
        </div>`;
}

function renderClustersTab() {
    const model = getModelData('user_clustering');
    const clusters = mlData.clusters;
    let clustersHtml = '';
    if (clusters && !clusters.error) {
        const totalUsers = (clusters.summary || []).reduce((s, c) => s + c.size, 0);
        clustersHtml = `
            <h4 style="margin-top:16px">Distribución de Clusters</h4>
            <table class="data-table">
                <thead><tr><th>Cluster</th><th>Usuarios</th><th>Avg Posts</th><th>Avg Likes</th><th>Avg Followers</th></tr></thead>
                <tbody>
                    ${(clusters.summary || []).map(c => {
                        const pct = totalUsers > 0 ? ((c.size / totalUsers) * 100).toFixed(0) : 0;
                        return `
                        <tr>
                            <td><strong>Cluster ${c.cluster}</strong> <span class="text-secondary">(${pct}%)</span></td>
                            <td>${c.size}</td>
                            <td>${c.avg_posts}</td>
                            <td>${c.avg_likes}</td>
                            <td>${c.avg_followers}</td>
                        </tr>`;
                    }).join('')}
                </tbody>
            </table>`;
    }
    // Real user examples from network
    const examples = (mlData.examples?.clustering || []);
    let examplesHtml = '';
    if (examples.length) {
        // Group by cluster
        const grouped = {};
        examples.forEach(e => {
            if (!grouped[e.cluster]) grouped[e.cluster] = [];
            grouped[e.cluster].push(e);
        });
        examplesHtml = `
            <h4 style="margin-top:20px">Clasificación de tu red</h4>
            ${Object.entries(grouped).map(([cluster, users]) => `
                <div class="cluster-group">
                    <div class="cluster-group-header" style="border-left:3px solid ${users[0].cluster_color}">
                        <span class="cluster-name" style="color:${users[0].cluster_color}">${cluster.charAt(0).toUpperCase() + cluster.slice(1)}</span>
                        <span class="text-secondary" style="font-size:12px">${users[0].cluster_desc}</span>
                        <span class="cluster-count">${users.length} usuarios</span>
                    </div>
                    <div class="cluster-users">
                        ${users.slice(0, 5).map(u => `
                            <div class="cluster-user-chip">
                                <div class="avatar" style="width:28px;height:28px;font-size:11px;background:${u.cluster_color}">${u.username.charAt(0).toUpperCase()}</div>
                                <div>
                                    <div style="font-weight:600;font-size:12px">@${esc(u.username)}</div>
                                    <div class="text-secondary" style="font-size:11px">${u.posts} posts · ${u.followers} followers</div>
                                </div>
                            </div>`).join('')}
                    </div>
                </div>`).join('')}`;
    }
    return `
        <div class="panel-card">
            <h3>User Clustering <span class="query-badge">K-Means</span></h3>
            ${renderModelCard('user_clustering', model)}
            ${clustersHtml}
            ${examplesHtml}
            <p class="card-summary">${modelDescriptions.user_clustering}</p>
        </div>`;
}

function renderRecommenderTab() {
    const model = getModelData('follow_recommender');
    const recs = mlData.recs;
    let recsHtml = '';
    if (recs && !recs.error && recs.recommendations?.length) {
        recsHtml = `
            <h4 style="margin-top:16px">Recomendaciones (modelo Spark)</h4>
            <div class="user-list">
                ${recs.recommendations.map(r => `
                    <div class="follow-item" onclick="loadProfile('${r.user_id}')" style="cursor:pointer">
                        <div class="avatar">${(r.username || '?').charAt(0).toUpperCase()}</div>
                        <div class="follow-info">
                            <div class="follow-name">${esc(r.display_name || r.username)}</div>
                            <div class="follow-username">@${esc(r.username)} — Score: ${r.score}</div>
                            <div class="text-secondary" style="font-size:12px">${esc(r.reason)}</div>
                        </div>
                    </div>`).join('')}
            </div>`;
    }
    // Real-time recommendations from network analysis
    const examples = (mlData.examples?.recommender || []);
    let examplesHtml = '';
    if (examples.length) {
        examplesHtml = `
            <h4 style="margin-top:20px">Usuarios que podrías seguir — Basado en tu actividad</h4>
            <div class="ml-examples">
                ${examples.map(e => `
                    <div class="ml-example" onclick="loadProfile('${e.user_id}')" style="cursor:pointer">
                        <div class="ml-example-header">
                            <div class="avatar" style="width:32px;height:32px;font-size:13px">${e.username.charAt(0).toUpperCase()}</div>
                            <div>
                                <div style="font-weight:700;font-size:13px">${esc(e.display_name)}</div>
                                <div class="text-secondary" style="font-size:11px">@${esc(e.username)} · ${e.followers} followers · ${e.posts} posts</div>
                            </div>
                            <span class="ml-example-tag tag-legit" style="margin-left:auto">Score: ${e.score}</span>
                        </div>
                        <div class="ml-example-text" style="font-style:normal;font-size:12px">"${esc(e.sample_text)}"</div>
                        <div class="ml-example-meta">
                            ${(e.shared_hashtags || []).map(h => '<span class="mini-tag">#' + esc(h) + '</span>').join('')}
                            <span class="text-secondary" style="font-size:11px;margin-left:auto">${esc(e.reason)}</span>
                        </div>
                    </div>`).join('')}
            </div>`;
    }
    return `
        <div class="panel-card">
            <h3>Follow Recommender <span class="query-badge">Hybrid Model</span></h3>
            ${renderModelCard('follow_recommender', model)}
            ${recsHtml}
            ${examplesHtml}
            <p class="card-summary">${modelDescriptions.follow_recommender}</p>
        </div>`;
}

function renderChurnTab() {
    const model = getModelData('churn_predictor');
    const churn = mlData.churn;
    let churnHtml = '';
    if (churn && !churn.error) {
        const total = churn.total_at_risk + churn.total_safe;
        const riskPct = total > 0 ? ((churn.total_at_risk / total) * 100).toFixed(1) : 0;
        churnHtml = `
            <div class="stats-grid" style="margin:16px 0">
                <div class="stat-item"><div class="stat-value" style="color:orange">${churn.total_at_risk}</div><div class="stat-label">En riesgo</div></div>
                <div class="stat-item"><div class="stat-value" style="color:var(--success)">${churn.total_safe}</div><div class="stat-label">Activos</div></div>
                <div class="stat-item"><div class="stat-value">${riskPct}%</div><div class="stat-label">Ratio churn</div></div>
            </div>
            ${(churn.at_risk || []).length ? `
                <h4>Usuarios en riesgo:</h4>
                <div class="user-list">
                    ${churn.at_risk.slice(0, 8).map(u => `
                        <div class="follow-item">
                            <div class="avatar" style="background:orange;color:white">!</div>
                            <div class="follow-info">
                                <div class="follow-name">${esc(u.username)}</div>
                            </div>
                        </div>`).join('')}
                </div>` : ''}`;
    }
    // Real user examples from network
    const examples = (mlData.examples?.churn || []);
    let examplesHtml = '';
    if (examples.length) {
        examplesHtml = `
            <h4 style="margin-top:20px">Análisis de Retención — Tu red</h4>
            <table class="data-table">
                <thead><tr><th>Usuario</th><th>Posts</th><th>Followers</th><th>P(churn)</th><th>Estado</th></tr></thead>
                <tbody>
                    ${examples.map(e => `
                    <tr>
                        <td style="font-weight:600">@${esc(e.username)}</td>
                        <td style="text-align:center">${e.posts}</td>
                        <td style="text-align:center">${e.followers}</td>
                        <td style="text-align:center">${(e.churn_probability * 100).toFixed(0)}%</td>
                        <td style="text-align:center">
                            <span class="ml-example-tag ${e.at_risk ? 'tag-spam' : 'tag-legit'}">${e.at_risk ? '⚠️ Riesgo' : '✅ Activo'}</span>
                        </td>
                    </tr>`).join('')}
                </tbody>
            </table>
            <div class="text-secondary" style="font-size:11px;margin-top:8px">Features: days_since_last_post, posts_count, followers_count, likes_received, follow_ratio</div>`;
    }
    return `
        <div class="panel-card">
            <h3>Churn Predictor <span class="query-badge">GBTClassifier</span></h3>
            ${renderModelCard('churn_predictor', model)}
            ${churnHtml}
            ${examplesHtml}
            <p class="card-summary">${modelDescriptions.churn_predictor}</p>
        </div>`;
}



// --- Spam highlight ---
async function loadSpamUserIds() {
    try {
        const res = await fetch(`${API}/analytics/ml/spam/user-ids`);
        const data = await res.json();
        spamUserIds = new Set(data.user_ids || []);
    } catch (e) {
        spamUserIds = new Set();
    }
}

async function toggleSpamHighlight() {
    if (spamUserIds.size === 0) await loadSpamUserIds();
    spamHighlightEnabled = !spamHighlightEnabled;
    const btn = document.getElementById('spam-toggle');
    if (btn) {
        btn.textContent = spamHighlightEnabled ? 'Ocultar Spam' : 'Detector Spam';
        btn.classList.toggle('active', spamHighlightEnabled);
    }
    // Re-render current view
    document.querySelectorAll('.post').forEach(el => {
        const userId = el.dataset.userId || '';
        const avatar = el.querySelector('.avatar');
        if (!avatar) return;
        if (spamHighlightEnabled && spamUserIds.has(userId)) {
            el.classList.add('post-spam');
            avatar.style.background = 'var(--spam)';
            avatar.style.color = 'white';
            if (!el.querySelector('.spam-badge')) {
                const header = el.querySelector('.post-header');
                const time = header.querySelector('.time');
                const badge = document.createElement('span');
                badge.className = 'spam-badge';
                badge.textContent = 'SPAM';
                header.insertBefore(badge, time);
            }
        } else {
            el.classList.remove('post-spam');
            avatar.style.background = '';
            avatar.style.color = '';
            el.querySelectorAll('.spam-badge').forEach(b => b.remove());
        }
    });
}

// --- Utils ---
function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

function timeAgo(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = (now - date) / 1000;
    if (diff < 60) return 'ahora';
    if (diff < 3600) return `${Math.floor(diff / 60)}m`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
    if (diff < 2592000) return `${Math.floor(diff / 86400)}d`;
    return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
}
