// Quasar Hub - SPA con 4 vistas: home, status, config, onboarding

let CATALOG = null;
let CURRENT_VIEW = "home";

async function fetchJSON(url, opts) {
    const res = await fetch(url, opts);
    return res.json();
}

function showView(view) {
    CURRENT_VIEW = view;
    document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.view === view));
    const render = { home: renderHome, status: renderStatus, config: renderConfig, onboarding: renderOnboarding }[view];
    render();
}

function toast(msg) {
    let t = document.getElementById("toast");
    if (!t) { t = document.createElement("div"); t.id = "toast"; t.className = "toast"; document.body.appendChild(t); }
    t.textContent = msg;
    t.classList.add("show");
    setTimeout(() => t.classList.remove("show"), 3500);
}

// ============================================================
// HOME / landing
// ============================================================
async function renderHome() {
    const el = document.getElementById("content");
    if (!CATALOG) CATALOG = await fetchJSON("/api/hub/catalog");
    const status = await fetchJSON("/api/hub/status");
    const onlineMap = {};
    status.apps.forEach(a => onlineMap[a.key] = a.online);

    let cards = CATALOG.apps.map(app => {
        const online = onlineMap[app.key];
        return `
        <div class="app-card" style="--accent:${app.color}">
            <div class="accent-bar"></div>
            <h2>${app.name}</h2>
            <div class="tagline">${app.tagline}</div>
            <p>${app.description}</p>
            <div class="card-foot">
                <span class="port"><span class="status-dot ${online ? 'dot-online' : 'dot-offline'}"></span>${app.url_public.replace('http://localhost','')}</span>
                <a class="open-btn" href="${app.url_public}" target="_blank">Abrir →</a>
            </div>
        </div>`;
    }).join("");

    el.innerHTML = `
        <div class="hero">
            <h1>✦ QUASAR</h1>
            <p>Plataforma docente de Big Data + IA. Un único stack poliglota (MongoDB · Neo4j · Spark · FastAPI) que aloja <strong>tres laboratorios independientes</strong>, cada uno enseñando un caso de uso distinto del temario.</p>
        </div>
        <div class="app-grid">${cards}</div>
        <p class="muted" style="text-align:center;margin-top:28px">
            ${status.summary.apps_online}/${status.summary.apps_total} apps online ·
            ${status.summary.blocks_unlocked}/${status.summary.blocks_total} bloques desbloqueados ·
            <a href="#" onclick="showView('onboarding');return false" style="color:#38bdf8">¿Primera vez? Empieza aquí →</a>
        </p>
    `;
}

// ============================================================
// STATUS / dashboard agregado
// ============================================================
async function renderStatus() {
    const el = document.getElementById("content");
    el.innerHTML = "<div class='loading'>consultando las 3 apps...</div>";
    const data = await fetchJSON("/api/hub/status");

    let html = `
        <h1>Estado del ecosistema</h1>
        <div class="summary-row">
            <div class="stat-box"><div class="num">${data.summary.apps_online}/${data.summary.apps_total}</div><div class="lbl">apps online</div></div>
            <div class="stat-box"><div class="num">${data.summary.blocks_unlocked}</div><div class="lbl">bloques desbloqueados</div></div>
            <div class="stat-box"><div class="num">${data.summary.blocks_total}</div><div class="lbl">bloques totales</div></div>
        </div>
    `;

    data.apps.forEach(app => {
        const blocks = Object.entries(app.blocks);
        html += `
        <div class="app-section">
            <div class="app-section-head">
                <span class="status-dot ${app.online ? 'dot-online':'dot-offline'}"></span>
                <h2 style="color:${app.color}">${app.name}</h2>
                <span class="muted">${app.online ? 'online' : 'offline'} · <a href="${app.url_public}" target="_blank" style="color:#38bdf8">${app.url_public.replace('http://localhost','')}</a></span>
            </div>
            ${blocks.length ? `<div class="blocks-grid">${blocks.map(([b,v])=>`
                <div class="block-chip ${v?'unlocked':'locked'}"><span class="bdot"></span>${b}</div>
            `).join("")}</div>` : `<p class="muted">${app.online ? 'Sin bloques reportados.' : 'App caída — arráncala con ./lab.sh '+app.key+' up'}</p>`}
        </div>`;
    });
    el.innerHTML = html;
}

// ============================================================
// CONFIG / panel del profesor
// ============================================================
async function renderConfig() {
    const el = document.getElementById("content");
    el.innerHTML = "<div class='loading'>cargando configuración...</div>";
    if (!CATALOG) CATALOG = await fetchJSON("/api/hub/catalog");
    const flagsData = await fetchJSON("/api/hub/flags");
    const flags = flagsData.flags;

    function isUnlocked(flag, block) {
        const v = (flags[flag] || "").toLowerCase();
        if (v === "all") return true;
        return v.split(",").map(s=>s.trim()).includes(block);
    }

    let html = `
        <h1>Configuración del laboratorio</h1>
        <p class="muted">Desbloquea o bloquea cada bloque desde aquí. Al cambiar un flag se reinicia el contenedor de la app (~3-5s) y los alumnos verán el bloque como solución (desbloqueado) o ejercicio (bloqueado).</p>
        <div class="config-actions">
            <button class="action-btn" onclick="bulkConfig('unlock')">Desbloquear todo</button>
            <button class="action-btn secondary" onclick="bulkConfig('lock')">Bloquear todo (modo alumno)</button>
        </div>
    `;

    CATALOG.apps.forEach(app => {
        html += `<div class="app-section"><div class="app-section-head"><h2 style="color:${app.color}">${app.name}</h2></div>`;
        Object.entries(app.flags).forEach(([flag, blocks]) => {
            html += `<h3>${flag}</h3><div class="blocks-grid" style="margin-bottom:14px">`;
            blocks.forEach(block => {
                const unlocked = isUnlocked(flag, block);
                html += `<button class="toggle-btn ${unlocked?'is-unlocked':'is-locked'}"
                    onclick="toggleBlock('${app.key}','${flag}','${block}',${unlocked})">
                    <span class="bdot"></span>${block}</button>`;
            });
            html += `</div>`;
        });
        html += `</div>`;
    });
    el.innerHTML = html;
}

async function toggleBlock(app, flag, block, currentlyUnlocked) {
    const action = currentlyUnlocked ? "lock" : "unlock";
    toast(`${action === "unlock" ? "Desbloqueando" : "Bloqueando"} ${block}... reiniciando ${app}`);
    const res = await fetch("/api/hub/flag", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ app, flag, block, action }),
    });
    const data = await res.json();
    if (!res.ok) { toast("Error: " + (data.detail || "fallo")); return; }
    toast(`${flag} = ${data.new_value}. ${data.restarted} reiniciado.`);
    setTimeout(() => renderConfig(), 1500);
}

async function bulkConfig(action) {
    if (!CATALOG) CATALOG = await fetchJSON("/api/hub/catalog");
    toast(action === "unlock" ? "Desbloqueando todo..." : "Bloqueando todo...");
    for (const app of CATALOG.apps) {
        for (const [flag, blocks] of Object.entries(app.flags)) {
            for (const block of blocks) {
                await fetch("/api/hub/flag", {
                    method: "POST", headers: {"Content-Type":"application/json"},
                    body: JSON.stringify({ app: app.key, flag, block, action }),
                });
            }
        }
    }
    toast("Listo. Las apps se están reiniciando.");
    setTimeout(() => renderConfig(), 2000);
}

// ============================================================
// ONBOARDING
// ============================================================
function renderOnboarding() {
    document.getElementById("content").innerHTML = `
        <h1>Primeros pasos</h1>
        <p class="muted" style="margin-bottom:24px">De cero a las tres apps con datos cargados. Todo desde el terminal con <code>./lab.sh</code>.</p>

        <div class="step"><div class="num">1</div><div class="body">
            <h3>Arranca todo el ecosistema</h3>
            <p>Un solo comando levanta MongoDB, Neo4j y las 4 apps (incluido este Hub), genera los datos sucios y ejecuta el ETL.</p>
            <pre>./lab.sh tour</pre>
            <p class="muted">Tarda ~2-3 min la primera vez (construye imágenes). Las siguientes, segundos.</p>
        </div></div>

        <div class="step"><div class="num">2</div><div class="body">
            <h3>Explora las apps desde el Estado</h3>
            <p>La pestaña <strong>Estado</strong> de este Hub te muestra las 3 apps, si están online y qué bloques tienen desbloqueados. Cada tarjeta de Inicio abre la app en una pestaña nueva.</p>
        </div></div>

        <div class="step"><div class="num">3</div><div class="body">
            <h3>Destapa ejercicios según avanza el curso</h3>
            <p>En la pestaña <strong>Configuración</strong> activas/desactivas cada bloque con un clic (no hace falta terminal). Desbloqueado = los alumnos ven la solución; bloqueado = la ven como ejercicio a implementar.</p>
            <p class="muted">Equivale a <code>./lab.sh &lt;app&gt; unlock &lt;bloque&gt;</code> pero desde la web.</p>
        </div></div>

        <div class="step"><div class="num">4</div><div class="body">
            <h3>Ruta pedagógica sugerida</h3>
            <p><strong>PreproLab</strong> (Tema 5: preprocesamiento) → <strong>SocialLab</strong> (bases poliglotas + ML aplicado) → <strong>LLM Lab</strong> (preparación de corpus para modelos de lenguaje). Cada app cierra con una demo culminante: Pipeline Studio en PreproLab y "corpus sucio vs limpio" en LLM Lab.</p>
        </div></div>
    `;
}

// boot
showView("home");
