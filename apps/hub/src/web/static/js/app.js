// Quasar Hub v2 - panel de control completo

let CATALOG = null;
let CURRENT_VIEW = "home";

async function fetchJSON(url, opts) {
    const res = await fetch(url, opts);
    return res.json();
}

// --- Acciones de control (flags, restart, run) ---
// Si la instalación define QUASAR_TEACHER_TOKEN, estas llamadas piden la
// clave y la guardan en el navegador. Sin token configurado (cada alumno
// con su copia) no molesta a nadie.
function teacherToken() { return localStorage.getItem("quasar_token") || ""; }

async function postControl(path, body) {
    const send = () => fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Quasar-Token": teacherToken() },
        body: JSON.stringify(body),
    });
    let res = await send();
    if (res.status === 401) {
        const t = prompt("Esta instalación está protegida.\nIntroduce el token de profesor:");
        if (!t) return { ok: false, data: { detail: "Hace falta el token de profesor." } };
        localStorage.setItem("quasar_token", t.trim());
        res = await send();
        if (res.status === 401) localStorage.removeItem("quasar_token");
    }
    return { ok: res.ok, data: await res.json() };
}

async function getCatalog() {
    if (!CATALOG) CATALOG = await fetchJSON("/api/hub/catalog");
    return CATALOG;
}

const VIEWS = {
    home: () => renderHome(), learn: () => renderLearn(), status: () => renderStatus(),
    config: () => renderConfig(), arch: () => renderArch(), onboarding: () => renderOnboarding(),
};

function showView(view, opts) {
    if (!VIEWS[view]) view = "home";
    CURRENT_VIEW = view;
    document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.view === view));
    // Ruta enlazable: cada vista tiene su #hash, así se puede compartir y
    // sobrevive a un refresco. `fromHash` evita re-escribir el hash en bucle.
    if (!(opts && opts.fromHash) && location.hash.slice(1) !== view) {
        location.hash = view;
        return; // el evento hashchange llamará de nuevo y renderizará.
    }
    Promise.resolve(VIEWS[view]()).catch(err => {
        console.error(err);
        document.getElementById("content").innerHTML =
            `<h1>Algo ha fallado</h1>
             <div class="app-section">
                <p>No se ha podido cargar esta vista. Lo más habitual es que el Hub haya perdido contacto con el ecosistema.</p>
                <p class="muted">Comprueba que los contenedores están arriba (<code>./lab.sh status</code>) y vuelve a intentarlo.</p>
                <button class="action-btn" onclick="showView('${view}',{fromHash:true})" style="margin-top:12px">Reintentar</button>
             </div>`;
    });
}

function routeFromHash() {
    const ruta = (location.hash || "#home").slice(1);
    // Las páginas de tema llevan su número en la ruta: se puede enlazar un
    // tema concreto y sobrevive a un refresco.
    const m = ruta.match(/^tema\/(\d+)$/);
    if (m) {
        CURRENT_VIEW = "tema";
        document.querySelectorAll(".tab").forEach(x =>
            x.classList.toggle("active", x.dataset.view === "home"));
        Promise.resolve(renderTema(parseInt(m[1], 10))).catch(err => {
            console.error(err);
            document.getElementById("content").innerHTML =
                `<h1>No se ha podido cargar el tema</h1>
                 <p class="muted"><a href="#home" style="color:#38bdf8">← Volver al temario</a></p>`;
        });
        return;
    }
    showView(ruta, { fromHash: true });
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

// --- Temas que el alumno marca como hechos ---
// Vive en su navegador y lo pone él. El Hub no sabe quién es nadie ni tiene
// forma de comprobarlo: es un cuaderno, no una nota. Usar los flags LAB_*
// como progreso sería engañoso, porque destapar un bloque significa
// "enséñame la solución", casi lo contrario de haberlo hecho.
function temasHechos() {
    try { return new Set(JSON.parse(localStorage.getItem("quasar_temas") || "[]")); }
    catch { return new Set(); }
}

function marcarTema(n) {
    const hechos = temasHechos();
    hechos.has(n) ? hechos.delete(n) : hechos.add(n);
    localStorage.setItem("quasar_temas", JSON.stringify([...hechos]));
    renderHome();
}

function reiniciarTemas() {
    if (!confirm("¿Desmarcar todos los temas? Solo afecta a tu navegador.")) return;
    localStorage.removeItem("quasar_temas");
    renderHome();
}

function duracion(min) {
    if (!min) return "";
    if (min < 60) return `${min} min`;
    const h = Math.floor(min / 60), m = min % 60;
    return m ? `${h} h ${m} min` : `${h} h`;
}

function paradaTema(tema, hechos, onlineMap, dataMap) {
    const hecho = hechos.has(tema.n);
    const teoria = !tema.app;
    const color = tema.color || "#38bdf8";
    const clases = ["parada", hecho ? "hecho" : "", teoria ? "teoria" : ""].join(" ");

    let insignia, accion;
    if (teoria) {
        insignia = `<span class="chip-teoria">◇ solo teoría</span>`;
        accion = `<a class="parada-link" href="#tema/${tema.n}">Leer el tema →</a>`;
    } else {
        const ds = dataMap[tema.app] || {};
        insignia = `<span class="chip-lab" style="--c:${color}">${dot(onlineMap[tema.app])}${tema.app_nombre}</span>`;
        accion = `<a class="parada-btn" style="--c:${color}" href="#tema/${tema.n}">Ver tema</a>
            <span class="prog">${tema.ejercicios} ejercicios · ${
                ds.seeded ? "datos listos" : "sin datos"}</span>`;
    }

    return `<div class="${clases}" style="--c:${color}">
        <button class="parada-punto" onclick="marcarTema(${tema.n})"
                title="${hecho ? "Marcar como pendiente" : "Marcar como hecho"}"
                aria-label="${hecho ? "Marcar tema como pendiente" : "Marcar tema como hecho"}">
            ${hecho ? "✓" : ""}
        </button>
        <div class="parada-caja">
            <div class="parada-txt">
                <div class="linea">
                    <h3><a class="parada-tit" href="#tema/${tema.n}">${tema.n} · ${tema.titulo}</a></h3>
                    ${insignia}
                    ${tema.minutos ? `<span class="parada-min">${duracion(tema.minutos)}</span>` : ""}</div>
                <p>${tema.resumen}</p>
                ${tema.objetivo ? `<p class="parada-obj"><span>Al terminar sabrás</span> ${tema.objetivo}.</p>` : ""}
            </div>
            <div class="parada-accion">${accion}</div>
        </div>
    </div>`;
}

// ============================================================
// PÁGINA DE UN TEMA
// ============================================================
function parrafosLeccion(teoria) {
    return (teoria || [])
        .map(x => `<p>${x.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")}</p>`)
        .join("");
}

function marcarTemaDesdePagina(n) {
    const hechos = temasHechos();
    hechos.has(n) ? hechos.delete(n) : hechos.add(n);
    localStorage.setItem("quasar_temas", JSON.stringify([...hechos]));
    renderTema(n);
}

// Cuestionario de ensayo. No hay nota ni se envía nada: al pulsar una
// opción se dice si acertaste y, sobre todo, por qué. El valor está en la
// explicación, no en el marcador — los cuestionarios evaluables son otros.
let RESPUESTAS = {};

function responder(idx, opcion) {
    RESPUESTAS[idx] = opcion;
    pintarPregunta(idx);
}

function pintarPregunta(idx) {
    const caja = document.getElementById(`preg-${idx}`);
    if (!caja) return;
    const q = PREGUNTAS_TEMA[idx];
    const elegida = RESPUESTAS[idx];
    const contestada = elegida !== undefined;

    const opciones = q.opciones.map((texto, i) => {
        let clase = "cu-op";
        if (contestada) {
            if (i === q.correcta) clase += " ok";
            else if (i === elegida) clase += " mal";
            else clase += " gris";
        }
        return `<button class="${clase}" ${contestada ? "disabled" : ""}
            onclick="responder(${idx}, ${i})">
            <span class="cu-marca">${contestada && i === q.correcta ? "✓"
                : contestada && i === elegida ? "✗" : ""}</span>${texto}</button>`;
    }).join("");

    caja.innerHTML = `
        <p class="cu-enun"><span>${idx + 1}</span>${q.enunciado}</p>
        <div class="cu-ops">${opciones}</div>
        ${contestada ? `<p class="cu-porque">${q.porque}</p>` : ""}`;
}

let PREGUNTAS_TEMA = [];

function cuestionario(preguntas) {
    PREGUNTAS_TEMA = preguntas;
    RESPUESTAS = {};
    const cajas = preguntas.map((_, i) => `<div class="cu-preg" id="preg-${i}"></div>`).join("");
    return `<h2 class="tb-h">Compruébate</h2>
        <p class="muted" style="margin-bottom:14px">Sin nota y sin enviarse a ningún sitio: es
        para ver si te ha quedado claro antes de seguir. Lo que importa es la explicación de
        después, no acertar a la primera.</p>
        <div class="cuestionario">${cajas}</div>`;
}

async function renderTema(n) {
    const el = document.getElementById("content");
    el.innerHTML = "<div class='loading'>cargando el tema...</div>";
    const [cat, status] = await Promise.all([
        getCatalog(), fetchJSON("/api/hub/status"),
    ]);
    const unidades = cat.temario || [];
    const todos = unidades.flatMap(u => u.temas.map(x => ({ ...x, unidad: u })));
    const tema = todos.find(x => x.n === n);
    if (!tema) { location.hash = "home"; return; }

    const prev = todos.find(x => x.n === n - 1);
    const sig = todos.find(x => x.n === n + 1);
    const color = tema.color || "#38bdf8";
    const hecho = temasHechos().has(tema.n);
    const online = (status.apps.find(a => a.key === tema.app) || {}).online;

    const bloques = (tema.bloques || []).map(b => `
        <div class="tb-bloque">
            <div class="tb-b-cab"><strong>${b.label}</strong>
                <span class="tb-b-n">${b.exercises} ejercicios</span></div>
            <p>${b.desc}</p>
        </div>`).join("");

    const recursos = [
        tema.material ? `<span class="lec-mat">📄 ${tema.material}</span>` : "",
        tema.practica ? `<span class="lec-prac">✎ ${tema.practica}</span>` : "",
        tema.app ? `<a class="tb-abrir" style="--c:${color}" href="${tema.url}" target="_blank">${dot(online)}Abrir ${tema.app_nombre} ↗</a>` : "",
        tema.enlace ? `<a class="parada-link" href="#${tema.enlace.vista}">${tema.enlace.texto} →</a>` : "",
    ].filter(Boolean).join("");

    el.innerHTML = `
        <div class="tb-migas">
            <a href="#home">← Temario</a>
            <span>${tema.unidad.titulo}</span>
            ${tema.unidad.oficial === false ? `<span class="unidad-extra">fuera del programa</span>` : ""}
        </div>

        <div class="tb-cab" style="--c:${color}">
            <div class="tb-num">${tema.n}</div>
            <div class="tb-cab-txt">
                <h1>${tema.titulo}</h1>
                <div class="tb-meta">
                    ${tema.app
                        ? `<span class="chip-lab" style="--c:${color}">${tema.app_nombre}</span>`
                        : `<span class="chip-teoria">◇ solo teoría</span>`}
                    ${tema.minutos ? `<span class="parada-min">${duracion(tema.minutos)}</span>` : ""}
                    ${tema.ejercicios ? `<span class="parada-min">${tema.ejercicios} ejercicios</span>` : ""}
                </div>
            </div>
            <button class="tb-hecho ${hecho ? "si" : ""}" onclick="marcarTemaDesdePagina(${tema.n})">
                ${hecho ? "✓ hecho" : "marcar como hecho"}
            </button>
        </div>

        ${tema.objetivo ? `<p class="tb-obj"><span>Al terminar sabrás</span> ${tema.objetivo}.</p>` : ""}
        <p class="tb-resumen">${tema.resumen}</p>
        ${tema.teoria && tema.teoria.length ? `<div class="tb-leccion">${parrafosLeccion(tema.teoria)}</div>` : ""}
        ${bloques ? `<h2 class="tb-h">Qué se practica</h2><div class="tb-bloques">${bloques}</div>` : ""}
        ${recursos ? `<div class="tb-recursos">${recursos}</div>` : ""}

        ${tema.preguntas && tema.preguntas.length ? cuestionario(tema.preguntas) : ""}

        <div class="tb-nav">
            ${prev ? `<a href="#tema/${prev.n}">← ${prev.n} · ${prev.titulo}</a>` : "<span></span>"}
            ${sig ? `<a href="#tema/${sig.n}">${sig.n} · ${sig.titulo} →</a>` : "<span></span>"}
        </div>`;

    (tema.preguntas || []).forEach((_, i) => pintarPregunta(i));
}

async function renderHome() {
    const el = document.getElementById("content");
    const [cat, status, infra] = await Promise.all([
        getCatalog(), fetchJSON("/api/hub/status"), fetchJSON("/api/hub/infra"),
    ]);
    const onlineMap = {}; status.apps.forEach(a => onlineMap[a.key] = a.online);
    const dataMap = infra.data || {};
    const hechos = temasHechos();
    const unidades = cat.temario || [];
    const totalTemas = unidades.reduce((n, u) => n + u.temas.length, 0);
    const oficialMin = unidades.filter(u => u.oficial !== false)
                               .reduce((n, u) => n + (u.minutos || 0), 0);

    const ruta = unidades.map(u => `
        <div class="unidad-sep ${u.oficial === false ? "extra" : ""}">
            <span class="unidad-num">${u.titulo}</span>
            <span class="unidad-preg">${u.pregunta}</span>
            ${u.oficial === false ? `<span class="unidad-extra">fuera del programa</span>` : ""}
            ${u.minutos ? `<span class="unidad-min">${duracion(u.minutos)}</span>` : ""}
        </div>
        ${u.temas.map(t => paradaTema(t, hechos, onlineMap, dataMap)).join("")}
    `).join("");

    const pct = totalTemas ? Math.round(100 * hechos.size / totalTemas) : 0;

    el.innerHTML = `
        <div class="hero">
            <h1>Tratamiento y Gestión de Datos Masivos</h1>
            <p>Del dato en crudo al modelo entrenado. ${totalTemas} temas, cuatro laboratorios
            y ${cat.total_exercises} ejercicios sobre datos que se parecen a los de verdad:
            sucios, tardíos y a escala.</p>
            <div class="curso-meta">
                <span>${hechos.size} de ${totalTemas} temas marcados</span>
                ${oficialMin ? `<span>· ${duracion(oficialMin)} del programa</span>` : ""}
                <span class="barra-curso"><span style="width:${pct}%"></span></span>
                ${hechos.size ? `<button class="reset-temas" onclick="reiniciarTemas()">reiniciar</button>` : ""}
            </div>
        </div>

        <div class="ruta">${ruta}</div>

        <p class="ruta-nota">
            Los temas los marcas tú, y se guardan solo en este navegador: es tu cuaderno,
            no una nota. <a href="#learn">Las ideas del curso, en detalle →</a>
        </p>

        <div class="infra-strip" style="margin-top:26px">
            ${infraChip("MongoDB", infra.infra.mongodb.online, infra.infra.mongodb.role)}
            ${infraChip("Neo4j", infra.infra.neo4j.online, infra.infra.neo4j.role, "http://localhost:7474")}
            <span class="infra-summary">${status.summary.apps_online}/${status.summary.apps_total} laboratorios activos ·
                ${status.summary.blocks_unlocked}/${status.summary.blocks_total} bloques destapados ·
                <a href="#status" style="color:#38bdf8">Estado →</a></span>
        </div>
        <p class="muted" style="text-align:center;margin-top:16px">
            <a href="#onboarding" style="color:#38bdf8">Primeros pasos →</a> ·
            <a href="#arch" style="color:#38bdf8">Cómo funciona Quasar →</a>
        </p>`;
}

function infraChip(name, online, role, link) {
    const label = link && online ? `<a href="${link}" target="_blank" style="color:inherit">${name} ↗</a>` : name;
    return `<span class="infra-chip ${online?'up':'down'}" title="${role}">${dot(online)}${label}</span>`;
}

// ============================================================
// APRENDE  (introducción viva a la asignatura)
// ============================================================
async function safeJSON(url) {
    try { return await fetchJSON(url); } catch { return {}; }
}

function liveHint() {
    return `<span class="muted">Genera datos y corre el ETL en <a href="#" onclick="showView('status');return false" style="color:#38bdf8">Estado</a> para ver esto con tus propios datos.</span>`;
}

// --- Frescura del perfil (mtime del _profile.json) ---
function freshness(epoch) {
    if (!epoch) return "";
    const s = Math.floor(Date.now() / 1000) - epoch;
    let txt;
    if (s < 90) txt = "hace un momento";
    else if (s < 5400) txt = `hace ${Math.round(s / 60)} min`;
    else if (s < 172800) txt = `hace ${Math.round(s / 3600)} h`;
    else txt = `hace ${Math.round(s / 86400)} días`;
    return ` <span class="rx-fresh">· generado ${txt}</span>`;
}

// --- Radiografía de tus datos (barras desde los perfiles del ETL) ---
function rxBar(label, val, max, color, valLabel) {
    const w = max ? Math.max(3, Math.round(100 * val / max)) : 0;
    return `<div class="rx-row"><span class="rx-lbl">${label}</span>
        <span class="rx-track"><span class="rx-fill" style="width:${w}%;background:${color}"></span></span>
        <span class="rx-val">${valLabel != null ? valLabel : val}</span></div>`;
}

function radiografia(P, gen) {
    const secs = [];
    const llm = P.llmprep;
    if (llm && llm.noise_types && Object.keys(llm.noise_types).length) {
        const entries = Object.entries(llm.noise_types).sort((a, b) => b[1] - a[1]);
        const max = entries[0][1];
        const rows = entries.map(([k, v]) => rxBar(k, v, max, "#a855f7")).join("");
        secs.push(`<div class="rx-sec"><div class="rx-h">Ruido en tu corpus · ${llm.docs} docs${freshness(gen.llmprep)}</div>${rows}</div>`);
    }
    const prep = P.preprolab;
    if (prep) {
        const cols = [];
        for (const [t, tb] of Object.entries(prep))
            for (const [c, info] of Object.entries(tb.columns || {}))
                if (info.nulls > 0) cols.push([`${t}.${c}`, info.null_pct, info.nulls]);
        cols.sort((a, b) => b[1] - a[1]);
        const top = cols.slice(0, 6);
        if (top.length) {
            const max = top[0][1];
            const rows = top.map(([name, pct]) => rxBar(name, pct, max, "#1d9bf0", `${pct}%`)).join("");
            secs.push(`<div class="rx-sec"><div class="rx-h">Valores perdidos por columna · flota de robots${freshness(gen.preprolab)}</div>${rows}</div>`);
        }
    }
    return secs.length ? secs.join("") : liveHint();
}

// --- Bloques self-service: el alumno alterna solución / ejercicio ---
function isUnlocked(flags, flag, key) {
    const v = (flags[flag] || "").toLowerCase();
    return v === "all" || v.split(",").map(s => s.trim()).includes(key);
}

function conceptBlocks(appObj, flags, flagFilter) {
    if (!appObj || !appObj.blocks) return "";
    const blocks = appObj.blocks.filter(b => !flagFilter || b.flag === flagFilter);
    if (!blocks.length) return "";
    const btns = blocks.map(b => {
        const u = isUnlocked(flags, b.flag, b.key);
        return `<button class="lf-btn ${u ? 'sol' : 'ex'}" data-u="${u}" title="${(b.desc || '').replace(/"/g, '&quot;')}"
            onclick="learnFlag(this,'${appObj.key}','${b.flag}','${b.key}')">
            <span class="bdot"></span>${b.label} <span class="lf-state">${u ? 'solución' : 'ejercicio'}</span></button>`;
    }).join("");
    return `<div class="cc-blocks">
        <div class="cc-blocks-h">Tú decides qué ver: pulsa un bloque para mostrarlo <b>resuelto</b> o dejarlo como <b>ejercicio</b>. Reinicia tu copia de la app (~3 s).</div>
        <div class="lf-grid">${btns}</div>
        <a class="cc-go" href="${appObj.url_public}" target="_blank">Abrir ${appObj.name} ↗</a>
    </div>`;
}

async function learnFlag(btn, app, flag, block) {
    const currentlyUnlocked = btn.dataset.u === "true";
    const action = currentlyUnlocked ? "lock" : "unlock";
    btn.disabled = true;
    toast(`${action === "unlock" ? "Mostrando solución de" : "Volviendo a ejercicio"} ${block}… reiniciando ${app}`);
    try {
        const { ok, data } = await postControl("/api/hub/flag", { app, flag, block, action });
        if (!ok) { toast("Error: " + (data.detail || "fallo")); btn.disabled = false; return; }
        const nowU = !currentlyUnlocked;
        btn.dataset.u = String(nowU);
        btn.classList.toggle("sol", nowU);
        btn.classList.toggle("ex", !nowU);
        btn.querySelector(".lf-state").textContent = nowU ? "solución" : "ejercicio";
        toast(`${flag} = ${data.new_value || "(vacío)"}. ${app} reiniciando…`);
    } catch {
        toast("No se pudo cambiar el flag.");
    }
    btn.disabled = false;
}

async function renderLearn() {
    const el = document.getElementById("content");
    el.innerHTML = "<div class='loading'>consultando tus datos...</div>";
    const [cat, prof, flagsResp] = await Promise.all([
        getCatalog(), safeJSON("/api/hub/profiles"), safeJSON("/api/hub/flags"),
    ]);
    const P = (prof && prof.profiles) || {};
    const gen = (prof && prof.generated_at) || {};
    const flags = (flagsResp && flagsResp.flags) || {};

    const bloquesPorApp = cat.apps.map(a =>
        `<div class="ap-app"><h3 style="color:${a.color}">${a.name}</h3>
         ${conceptBlocks(a, flags)}</div>`).join("");

    el.innerHTML = `
        <div class="hero" style="padding-bottom:18px">
            <h1>Cómo funciona este laboratorio</h1>
            <p>La materia está en el <a href="#home" style="color:#38bdf8">temario</a>, un tema por
            página. Aquí queda lo que no es materia: cómo están hechos los ejercicios y qué aspecto
            tienen tus datos ahora mismo.</p>
        </div>

        <h2 class="tb-h">Tus datos, ahora mismo</h2>
        <p class="muted" style="margin-bottom:14px">Lo que el ETL encontró en tu copia. No son
        ejemplos de pizarra: es lo que vas a tener delante al hacer los ejercicios.</p>
        <div class="app-section">${radiografia(P, gen)}</div>

        <h2 class="tb-h" style="margin-top:26px">Ejercicio o solución: mandas tú</h2>
        <div class="app-section">
            <p>Cada algoritmo está dos veces: el hueco a rellenar (<code>_ex.py</code>, con un
            <code>NotImplementedError</code>) y la solución. Un flag decide cuál se sirve, sin tocar
            el código y sin rebuild: basta un reinicio de tres segundos.</p>
            <p class="muted" style="margin-top:8px">Empiezas con el ejercicio en blanco; cuando lo
            implementas, la tarjeta de la app se enciende sola. Y si prefieres estudiar la solución
            primero, la destapas: es tu copia.</p>
            <p class="muted" style="margin-top:8px">Si un bloque aparece como <em>sin solución</em>,
            es que esa solución todavía no está en tu copia. Se publican al cerrar cada entrega.</p>
        </div>

        <h2 class="tb-h" style="margin-top:26px">Los bloques de cada laboratorio</h2>
        <div class="ap-apps">${bloquesPorApp}</div>

        <p class="muted" style="text-align:center;margin-top:26px">
            <a href="#home" style="color:#38bdf8">← Volver al temario</a> ·
            <a href="#arch" style="color:#38bdf8">Cómo encaja todo →</a>
        </p>`;
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
                ${app.online
                    ? `<button class="mini-btn ghost" onclick="restartApp('${app.key}','${app.name}')">reiniciar</button>
                       <button class="mini-btn ghost" onclick="powerApp('${app.key}','${app.name}','stop')">parar</button>`
                    : `<button class="mini-btn" onclick="powerApp('${app.key}','${app.name}','start')">arrancar</button>`}
                <button class="mini-btn ghost" onclick="showLogs('${app.key}','${app.name}')">logs</button>
            </div>
            <pre class="log-box" id="logs-${app.key}" hidden></pre>
            ${app.blocks.length ? `<div class="blocks-grid">${app.blocks.map(b=>`
                <div class="block-chip ${b.unlocked?'unlocked':'locked'}" title="${b.desc}"><span class="bdot"></span>${b.label} <span class="ex">${b.exercises}</span></div>
            `).join("")}</div>` : `<p class="muted">${app.online?'Sin bloques.':'Caída — arráncala con el botón de arriba o <code>./lab.sh '+app.key+' up</code>'}</p>`}
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
    const { ok, data } = await postControl("/api/hub/run", { app, task });
    if (!ok) { toast("Error: " + (data.detail||"fallo")); return; }
    toast(data.detached ? data.note : `"${label}" terminó (exit ${data.exit_code}). Refrescando...`);
    setTimeout(() => { if (CURRENT_VIEW==="status") renderStatus(); }, data.detached ? 4000 : 1500);
}

async function restartApp(app, name) {
    toast(`Reiniciando ${name}...`);
    const { ok, data } = await postControl("/api/hub/restart", { app });
    if (!ok) { toast("Error: "+(data.detail||"fallo")); return; }
    toast(`${name} reiniciado.`);
    setTimeout(() => { if (CURRENT_VIEW==="status") renderStatus(); }, 3000);
}

async function powerApp(app, name, action) {
    toast(`${action === "start" ? "Arrancando" : "Parando"} ${name}...`);
    const { ok, data } = await postControl("/api/hub/power", { app, action });
    if (!ok) { toast("Error: " + (data.detail || "fallo")); return; }
    toast(`${name}: ${data.status}.`);
    // Arrancar lleva unos segundos hasta que la app responde.
    setTimeout(() => { if (CURRENT_VIEW==="status") renderStatus(); }, action === "start" ? 6000 : 2000);
}

async function showLogs(app, name) {
    const box = document.getElementById(`logs-${app}`);
    if (!box) return;
    if (!box.hidden) { box.hidden = true; return; }   // segundo clic: ocultar
    box.hidden = false;
    box.textContent = "leyendo logs...";
    try {
        const data = await fetchJSON(`/api/hub/logs?app=${encodeURIComponent(app)}&lines=120`);
        if (data.detail) { box.textContent = `No se pudieron leer: ${data.detail}`; return; }
        box.textContent = (data.lines || "").trim() || `(${name} no ha escrito nada todavía)`;
        box.scrollTop = box.scrollHeight;   // abajo del todo: lo último es lo que interesa
    } catch {
        box.textContent = "No se pudieron leer los logs.";
    }
}

// ============================================================
// CONFIG
// ============================================================
async function renderConfig() {
    const el = document.getElementById("content");
    el.innerHTML = "<div class='loading'>cargando configuración...</div>";
    const [cat, flagsData] = await Promise.all([getCatalog(), fetchJSON("/api/hub/flags")]);
    const flags = flagsData.flags;

    let html = `
        <h1>Configuración del laboratorio</h1>
        <p class="muted">Cada interruptor muestra un bloque <strong>resuelto</strong> o lo deja como <strong>ejercicio</strong>. Al cambiarlo se reinicia esa app (~3-5 s). Es lo mismo que <code>./lab.sh &lt;app&gt; unlock &lt;bloque&gt;</code>, pero desde la web.</p>
        <div class="config-actions">
            <button class="action-btn" onclick="bulkConfig('unlock')">Ver todo resuelto</button>
            <button class="action-btn secondary" onclick="bulkConfig('lock')">Dejar todo como ejercicio</button>
        </div>`;

    cat.apps.forEach(app => {
        html += `<div class="app-section"><div class="app-section-head"><h2 style="color:${app.color}">${app.name}</h2><span class="muted">${app.exercises} ejercicios</span></div><div class="blocks-grid">`;
        app.blocks.forEach(b => {
            const u = isUnlocked(flags, b.flag, b.key);
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
    toast(`${action==="unlock"?"Mostrando solución de":"Volviendo a ejercicio"} ${block}... reiniciando ${app}`);
    const { ok, data } = await postControl("/api/hub/flag", { app, flag, block, action });
    if (!ok) { toast("Error: "+(data.detail||"fallo")); return; }
    toast(`${flag} = ${data.new_value}. ${data.restarted} reiniciado.`);
    setTimeout(() => renderConfig(), 1500);
}

async function bulkConfig(action) {
    const cat = await getCatalog();
    toast(action==="unlock"?"Mostrando todo resuelto...":"Dejando todo como ejercicio...");
    for (const app of cat.apps) {
        for (const b of app.blocks) {
            const { ok, data } = await postControl("/api/hub/flag",
                { app: app.key, flag: b.flag, block: b.key, action });
            if (!ok) { toast("Error: " + (data.detail || "fallo")); return; }
        }
    }
    toast("Listo. Las apps se reinician.");
    setTimeout(() => renderConfig(), 2000);
}

// ============================================================
// ARQUITECTURA
// ============================================================
function archDiagram(app) {
    // Construye un diagrama de flujo horizontal desde app.architecture.
    // Cada etapa es una caja; un 'split' apila dos cajas en paralelo.
    const stages = (app.architecture || []).map(stage => {
        if (stage.split) {
            const boxes = stage.split.map(s =>
                `<div class="flow-box split-box"><span class="fb-label">${s.label}</span><span class="fb-sub">${s.sub||""}</span></div>`
            ).join("");
            return `<div class="flow-stage"><div class="flow-split">${boxes}</div></div>`;
        }
        return `<div class="flow-stage"><div class="flow-box"><span class="fb-label">${stage.label}</span><span class="fb-sub">${stage.sub||""}</span></div></div>`;
    });
    return `<div class="flow-diagram" style="--accent:${app.color}">${stages.join('<div class="flow-arrow">→</div>')}</div>`;
}

async function renderArch() {
    const cat = await getCatalog();

    const appDiagrams = cat.apps.map(a => `
        <div class="app-section">
            <div class="app-section-head">
                <h2 style="color:${a.color}">${a.name}</h2>
                <span class="muted">${a.tagline} · ${a.exercises} ejercicios</span>
            </div>
            ${archDiagram(a)}
            <div class="arch-foot">
                <span class="tags">${a.tech.map(t=>`<span class="tag">${t}</span>`).join("")}</span>
                <span><a href="${a.readme}" target="_blank" style="color:#38bdf8">README ↗</a> · <a href="${a.docs}" target="_blank" style="color:#38bdf8">API docs ↗</a> · <a href="${a.url_public}" target="_blank" style="color:#38bdf8">abrir ↗</a></span>
            </div>
        </div>`).join("");

    document.getElementById("content").innerHTML = `
        <h1>Cómo funciona Quasar</h1>

        <h2>El patrón scaffold / solución</h2>
        <div class="app-section">
            <p>Cada algoritmo existe en dos versiones: <strong>solución</strong> (implementación completa) y <strong>scaffold</strong> (esqueleto con <code>NotImplementedError</code> que el alumno completa). Un flag <code>LAB_*</code> decide cuál se sirve en runtime.</p>
            <p class="muted">Bloque <strong>desbloqueado</strong> = ves la solución funcionando. <strong>Bloqueado</strong> = lo tienes como ejercicio por implementar. Se cambia desde <a href="#config" style="color:#38bdf8">Configuración</a> o desde cada concepto en <a href="#learn" style="color:#38bdf8">Aprende</a>, sin tocar el código.</p>
        </div>

        <h2>Arquitectura de cada app</h2>
        <p class="muted" style="margin-bottom:14px">Las tres comparten el patrón "del dato crudo a explotable", pero cada una lo aterriza en una pila distinta.</p>
        ${appDiagrams}

        <h2 style="margin-top:24px">Infraestructura compartida</h2>
        <div class="app-section">
            <p>Un solo cluster sirve a las 3 apps: <strong>MongoDB</strong> (base documental), <strong>Neo4j</strong> (grafo), <strong>Spark</strong> (ETL/ML). Cada app tiene su propia base de datos y su data lake; comparten servidor, no datos.</p>
        </div>
    `;
}

// ============================================================
// ONBOARDING
// ============================================================
function renderOnboarding() {
    document.getElementById("content").innerHTML = `
        <h1>Primeros pasos</h1>
        <p class="muted" style="margin-bottom:24px">El ecosistema ya está arrancado: lo estás viendo. Falta <strong>generar los datos</strong> y ponerte con el primer bloque.</p>

        <div class="step"><div class="num">1</div><div class="body">
            <h3>Entiende de qué va esto</h3>
            <p>Pásate por <a href="#learn" style="color:#38bdf8">Aprende</a>: las ideas que resumen la asignatura, cada una con el laboratorio donde se trabaja. Diez minutos que ahorran mucha confusión luego.</p>
        </div></div>

        <div class="step"><div class="num">2</div><div class="body">
            <h3>Genera tus datos</h3>
            <p>En <a href="#status" style="color:#38bdf8">Estado</a>, cada app tiene sus botones para generar los datos (seed) y ejecutar el ETL. No hace falta terminal: el Hub lo lanza dentro del contenedor.</p>
            <p class="muted">Si prefieres la terminal: <code>./lab.sh tour</code> lo hace todo de una vez.</p>
        </div></div>

        <div class="step"><div class="num">3</div><div class="body">
            <h3>Elige qué ver resuelto y qué no</h3>
            <p>Es tu copia del laboratorio, así que mandas tú: en <a href="#config" style="color:#38bdf8">Configuración</a> (o dentro de cada concepto en Aprende) alternas cada bloque entre <strong>solución</strong> y <strong>ejercicio</strong>. Estudia la solución primero o peléate con el hueco en blanco, como prefieras.</p>
        </div></div>

        <div class="step"><div class="num">4</div><div class="body">
            <h3>Ruta sugerida</h3>
            <p><strong>PreproLab</strong> (Tema 5: preprocesamiento) → <strong>SocialLab</strong> (bases poliglotas + ML) → <strong>LLM Lab</strong> (corpus para modelos de lenguaje). Cada una termina con su demo: el Pipeline Studio y el "corpus sucio vs limpio".</p>
            <p class="muted">¿Dudas de cómo encaja todo? <a href="#arch" style="color:#38bdf8">Mira la arquitectura →</a></p>
        </div></div>
    `;
}

window.addEventListener("hashchange", routeFromHash);
routeFromHash();
