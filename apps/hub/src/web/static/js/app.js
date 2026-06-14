// Quasar Hub v2 - panel de control completo

let CATALOG = null;
let CURRENT_VIEW = "home";

async function fetchJSON(url, opts) {
    const res = await fetch(url, opts);
    return res.json();
}

async function getCatalog() {
    if (!CATALOG) CATALOG = await fetchJSON("/api/hub/catalog");
    return CATALOG;
}

function showView(view) {
    CURRENT_VIEW = view;
    document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.view === view));
    ({ home: renderHome, status: renderStatus, config: renderConfig, arch: renderArch, onboarding: renderOnboarding }[view])();
}

function toast(msg) {
    let t = document.getElementById("toast");
    if (!t) { t = document.createElement("div"); t.id = "toast"; t.className = "toast"; document.body.appendChild(t); }
    t.textContent = msg; t.classList.add("show");
    setTimeout(() => t.classList.remove("show"), 3800);
}

function dot(online) { return `<span class="status-dot ${online ? 'dot-online':'dot-offline'}"></span>`; }

// ============================================================
// HOME
// ============================================================
async function renderHome() {
    const el = document.getElementById("content");
    const [cat, status, infra] = await Promise.all([
        getCatalog(), fetchJSON("/api/hub/status"), fetchJSON("/api/hub/infra"),
    ]);
    const onlineMap = {}; status.apps.forEach(a => onlineMap[a.key] = a.online);

    const cards = cat.apps.map(app => `
        <div class="app-card" style="--accent:${app.color}">
            <div class="accent-bar"></div>
            <h2>${app.name}</h2>
            <div class="tagline">${app.tagline}</div>
            <p>${app.description}</p>
            <div class="tags">${app.tech.map(t=>`<span class="tag">${t}</span>`).join("")}</div>
            <div class="card-foot">
                <span class="port">${dot(onlineMap[app.key])}${app.url_public.replace('http://localhost','')} · ${app.exercises} ejercicios</span>
                <a class="open-btn" href="${app.url_public}" target="_blank">Abrir →</a>
            </div>
        </div>`).join("");

    el.innerHTML = `
        <div class="hero">
            <h1>✦ QUASAR</h1>
            <p>Plataforma docente de Big Data + IA. Un único stack poliglota que aloja <strong>tres laboratorios</strong> con ${cat.total_exercises} ejercicios, sobre infraestructura compartida (MongoDB · Neo4j · Spark).</p>
        </div>
        <div class="infra-strip">
            ${infraChip("MongoDB", infra.infra.mongodb.online, infra.infra.mongodb.role)}
            ${infraChip("Neo4j", infra.infra.neo4j.online, infra.infra.neo4j.role, "http://localhost:7474")}
            <span class="infra-summary">${status.summary.apps_online}/${status.summary.apps_total} apps · ${status.summary.blocks_unlocked}/${status.summary.blocks_total} bloques destapados</span>
        </div>
        <div class="app-grid">${cards}</div>
        <p class="muted" style="text-align:center;margin-top:24px">
            <a href="#" onclick="showView('arch');return false" style="color:#38bdf8">¿Cómo funciona Quasar? →</a> ·
            <a href="#" onclick="showView('onboarding');return false" style="color:#38bdf8">Primeros pasos →</a>
        </p>`;
}

function infraChip(name, online, role, link) {
    const label = link && online ? `<a href="${link}" target="_blank" style="color:inherit">${name} ↗</a>` : name;
    return `<span class="infra-chip ${online?'up':'down'}" title="${role}">${dot(online)}${label}</span>`;
}

// ============================================================
// STATUS  (infra + datos + bloques + acciones)
// ============================================================
async function renderStatus() {
    const el = document.getElementById("content");
    el.innerHTML = "<div class='loading'>consultando ecosistema...</div>";
    const [status, infra, cat] = await Promise.all([
        fetchJSON("/api/hub/status"), fetchJSON("/api/hub/infra"), getCatalog(),
    ]);
    const taskMap = {}; cat.apps.forEach(a => taskMap[a.key] = a.tasks);

    let html = `
        <h1>Estado del ecosistema</h1>
        <div class="summary-row">
            <div class="stat-box"><div class="num">${status.summary.apps_online}/${status.summary.apps_total}</div><div class="lbl">apps online</div></div>
            <div class="stat-box"><div class="num">${status.summary.blocks_unlocked}</div><div class="lbl">bloques destapados</div></div>
            <div class="stat-box"><div class="num">${status.summary.blocks_total}</div><div class="lbl">bloques totales</div></div>
        </div>

        <h2>Infraestructura</h2>
        <div class="app-section" style="display:flex;gap:28px;flex-wrap:wrap">
            <div>${dot(infra.infra.mongodb.online)}<strong>MongoDB</strong> :${infra.infra.mongodb.port}<br><span class="muted" style="font-size:12px">${infra.infra.mongodb.role}</span></div>
            <div>${dot(infra.infra.neo4j.online)}<strong>Neo4j</strong> :${infra.infra.neo4j.port} · <a href="${infra.infra.neo4j.browser}" target="_blank" style="color:#38bdf8">browser ↗</a><br><span class="muted" style="font-size:12px">${infra.infra.neo4j.role}</span></div>
        </div>
        <h2 style="margin-top:24px">Apps</h2>`;

    status.apps.forEach(app => {
        const ds = infra.data[app.key] || {};
        const tasks = taskMap[app.key] || {};
        const taskBtns = Object.entries(tasks).map(([t, label]) =>
            `<button class="mini-btn" onclick="runTask('${app.key}','${t}','${label}')">${label}</button>`).join("");
        html += `
        <div class="app-section">
            <div class="app-section-head">
                ${dot(app.online)}
                <h2 style="color:${app.color}">${app.name}</h2>
                <span class="muted">${app.online?'online':'offline'} · <a href="${app.url_public}" target="_blank" style="color:#38bdf8">${app.url_public.replace('http://localhost','')}</a></span>
            </div>
            <div class="data-line">
                <span class="data-badge ${ds.seeded?'ok':'no'}">${ds.seeded ? '✓ '+ds.seed_label+' ('+ds.seed_size_mb+' MB)' : '○ '+(ds.seed_label||'datos')+' sin generar'}</span>
                ${ds.db_loaded ? `<span class="data-badge ok">✓ ${dbSummary(ds.db_counts)}</span>` : ''}
                <span class="task-btns">${taskBtns}</span>
                <button class="mini-btn ghost" onclick="restartApp('${app.key}','${app.name}')">reiniciar</button>
            </div>
            ${app.blocks.length ? `<div class="blocks-grid">${app.blocks.map(b=>`
                <div class="block-chip ${b.unlocked?'unlocked':'locked'}" title="${b.desc}"><span class="bdot"></span>${b.label} <span class="ex">${b.exercises}</span></div>
            `).join("")}</div>` : `<p class="muted">${app.online?'Sin bloques.':'Caída — arráncala con ./lab.sh '+app.key+' up'}</p>`}
        </div>`;
    });
    html += `<p class="muted" style="text-align:center;margin-top:8px"><button class="mini-btn ghost" onclick="renderStatus()">↻ refrescar</button></p>`;
    el.innerHTML = html;
}

function dbSummary(counts) {
    if (!counts) return "datos en Mongo";
    const parts = Object.entries(counts).filter(([k,v])=>v>0).slice(0,3).map(([k,v])=>`${v.toLocaleString()} ${k}`);
    return parts.length ? parts.join(" · ") : "datos en Mongo";
}

async function runTask(app, task, label) {
    toast(`Ejecutando "${label}" en ${app}...`);
    const res = await fetch("/api/hub/run", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({app, task}) });
    const data = await res.json();
    if (!res.ok) { toast("Error: " + (data.detail||"fallo")); return; }
    toast(data.detached ? data.note : `"${label}" terminó (exit ${data.exit_code}). Refrescando...`);
    setTimeout(() => { if (CURRENT_VIEW==="status") renderStatus(); }, data.detached ? 4000 : 1500);
}

async function restartApp(app, name) {
    toast(`Reiniciando ${name}...`);
    // reusar /flag con un toggle nulo no aplica; usamos /run? No. Hacemos restart vía un lock+unlock no.
    // El restart directo lo hace el endpoint de flag al cambiar; para un restart puro reutilizamos run con tarea inexistente no.
    // Mejor: pedir al backend reiniciar vía un endpoint dedicado.
    const res = await fetch("/api/hub/restart", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({app}) });
    const data = await res.json();
    if (!res.ok) { toast("Error: "+(data.detail||"fallo")); return; }
    toast(`${name} reiniciado.`);
    setTimeout(() => { if (CURRENT_VIEW==="status") renderStatus(); }, 3000);
}

// ============================================================
// CONFIG
// ============================================================
async function renderConfig() {
    const el = document.getElementById("content");
    el.innerHTML = "<div class='loading'>cargando configuración...</div>";
    const [cat, flagsData] = await Promise.all([getCatalog(), fetchJSON("/api/hub/flags")]);
    const flags = flagsData.flags;
    const isUnlocked = (flag, block) => {
        const v = (flags[flag]||"").toLowerCase();
        return v === "all" || v.split(",").map(s=>s.trim()).includes(block);
    };

    let html = `
        <h1>Configuración del laboratorio</h1>
        <p class="muted">Cada interruptor destapa (solución) o esconde (ejercicio) un bloque. Al cambiarlo se reinicia la app (~3-5s). Equivale a <code>./lab.sh &lt;app&gt; unlock &lt;bloque&gt;</code> pero desde la web.</p>
        <div class="config-actions">
            <button class="action-btn" onclick="bulkConfig('unlock')">Desbloquear todo (modo demo)</button>
            <button class="action-btn secondary" onclick="bulkConfig('lock')">Bloquear todo (modo alumno)</button>
        </div>`;

    cat.apps.forEach(app => {
        html += `<div class="app-section"><div class="app-section-head"><h2 style="color:${app.color}">${app.name}</h2><span class="muted">${app.exercises} ejercicios</span></div><div class="blocks-grid">`;
        app.blocks.forEach(b => {
            const u = isUnlocked(b.flag, b.key);
            html += `<button class="toggle-btn ${u?'is-unlocked':'is-locked'}" title="${b.desc}"
                onclick="toggleBlock('${app.key}','${b.flag}','${b.key}',${u})">
                <span class="bdot"></span>${b.label} <span class="ex">${b.exercises}</span></button>`;
        });
        html += `</div></div>`;
    });
    el.innerHTML = html;
}

async function toggleBlock(app, flag, block, currentlyUnlocked) {
    const action = currentlyUnlocked ? "lock" : "unlock";
    toast(`${action==="unlock"?"Desbloqueando":"Bloqueando"} ${block}... reiniciando ${app}`);
    const res = await fetch("/api/hub/flag", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({app, flag, block, action}) });
    const data = await res.json();
    if (!res.ok) { toast("Error: "+(data.detail||"fallo")); return; }
    toast(`${flag} = ${data.new_value}. ${data.restarted} reiniciado.`);
    setTimeout(() => renderConfig(), 1500);
}

async function bulkConfig(action) {
    const cat = await getCatalog();
    toast(action==="unlock"?"Desbloqueando todo...":"Bloqueando todo...");
    for (const app of cat.apps)
        for (const b of app.blocks)
            await fetch("/api/hub/flag", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({app:app.key, flag:b.flag, block:b.key, action}) });
    toast("Listo. Las apps se reinician.");
    setTimeout(() => renderConfig(), 2000);
}

// ============================================================
// ARQUITECTURA
// ============================================================
async function renderArch() {
    const cat = await getCatalog();
    const techByApp = cat.apps.map(a => `<tr><td style="color:${a.color}"><strong>${a.name}</strong></td><td>${a.tech.join(" · ")}</td><td><a href="${a.readme}" target="_blank" style="color:#38bdf8">README ↗</a> · <a href="${a.docs}" target="_blank" style="color:#38bdf8">API docs ↗</a></td></tr>`).join("");
    document.getElementById("content").innerHTML = `
        <h1>Cómo funciona Quasar</h1>

        <h2>El patrón scaffold / solución</h2>
        <div class="app-section">
            <p>Cada algoritmo existe en dos versiones: <strong>solución</strong> (implementación completa) y <strong>scaffold</strong> (esqueleto con <code>NotImplementedError</code> que el alumno completa). Un flag <code>LAB_*</code> decide cuál se sirve en runtime.</p>
            <p class="muted">Bloque <strong>desbloqueado</strong> = el alumno ve la solución funcionando. <strong>Bloqueado</strong> = la ve como ejercicio a implementar. El profesor lo controla desde la pestaña Configuración, sin tocar el código.</p>
        </div>

        <h2>Flujo de datos</h2>
        <div class="app-section">
            <pre class="flow">
  seed            ETL (Spark)          carga                 web
 ───────►  raw  ──────────►  silver/gold  ──────►  MongoDB / Neo4j  ──────►  FastAPI + UI
 (datos          (limpieza,    (parquet)    (documentos      (grafo)        (dashboards,
  sucios)         joins, agg)               + métricas)                      visualizaciones)
            </pre>
            <p class="muted">El mismo patrón se repite en las 3 apps. Es exactamente lo que el ecosistema enseña: el recorrido del dato de crudo a explotable.</p>
        </div>

        <h2>Infraestructura compartida</h2>
        <div class="app-section">
            <p>Un solo cluster sirve a las 3 apps: <strong>MongoDB</strong> (base documental), <strong>Neo4j</strong> (grafo), <strong>Spark</strong> (ETL/ML). Cada app tiene su propia base de datos y su data lake; comparten servidor, no datos.</p>
        </div>

        <h2>Tecnologías por app</h2>
        <div class="app-section"><table class="kv">${techByApp}</table></div>
    `;
}

// ============================================================
// ONBOARDING
// ============================================================
function renderOnboarding() {
    document.getElementById("content").innerHTML = `
        <h1>Primeros pasos</h1>
        <p class="muted" style="margin-bottom:24px">El ecosistema ya está arrancado (estás viéndolo). Lo que falta es <strong>generar datos</strong> y, opcionalmente, destapar ejercicios.</p>

        <div class="step"><div class="num">1</div><div class="body">
            <h3>Genera los datos desde la pestaña Estado</h3>
            <p>En <strong>Estado</strong>, cada app tiene botones para generar sus datos (seed) y, en SocialLab, ejecutar el ETL. No hace falta terminal: el Hub lo lanza por ti dentro del contenedor.</p>
            <p class="muted">Alternativa por terminal: <code>./lab.sh tour</code> hace todo de una vez.</p>
        </div></div>

        <div class="step"><div class="num">2</div><div class="body">
            <h3>Abre las apps</h3>
            <p>Desde <strong>Inicio</strong>, cada tarjeta abre su app. Indicador verde = online. Empieza por la que toque en tu temario.</p>
        </div></div>

        <div class="step"><div class="num">3</div><div class="body">
            <h3>Destapa ejercicios según avanza el curso</h3>
            <p>En <strong>Configuración</strong>, un clic destapa cada bloque (los alumnos ven la solución) o lo esconde (lo ven como ejercicio). Cada bloque indica cuántos ejercicios incluye.</p>
        </div></div>

        <div class="step"><div class="num">4</div><div class="body">
            <h3>Ruta pedagógica sugerida</h3>
            <p><strong>PreproLab</strong> (Tema 5: preprocesamiento) → <strong>SocialLab</strong> (bases poliglotas + ML) → <strong>LLM Lab</strong> (corpus para modelos de lenguaje). Cada una cierra con una demo: Pipeline Studio y "corpus sucio vs limpio".</p>
            <p class="muted">¿Dudas de cómo encaja todo? <a href="#" onclick="showView('arch');return false" style="color:#38bdf8">Mira la arquitectura →</a></p>
        </div></div>
    `;
}

showView("home");
