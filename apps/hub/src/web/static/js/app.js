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
    showView((location.hash || "#home").slice(1), { fromHash: true });
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
// Qué conceptos se practican en cada laboratorio. Los títulos salen de
// buildConcepts, así que si allí cambia el nombre de una idea, aquí cambia
// solo: esto solo dice qué número va con qué app.
const APP_CONCEPTS = {
    sociallab: [2, 3, 7],
    preprolab: [1, 5, 6],
    llmprep:   [5, 8],
};

// El hilo del curso: cuatro paradas, de los datos crudos al modelo.
function courseArc(P) {
    const noisy = P.llmprep ? (P.llmprep.docs || 0) - (P.llmprep.clean_docs || 0) : null;
    const steps = [
        { k: "Empiezas aquí", t: "Datos sucios",
          d: noisy ? `${noisy.toLocaleString('es')} problemas esperándote` : "nulls, duplicados, encoding roto…",
          c: "#38bdf8" },
        { k: "Los limpias", t: "Preprocesamiento",
          d: "las técnicas del Tema 5, una a una", c: "#1d9bf0" },
        { k: "Los explotas", t: "Bases poliglotas + ML",
          d: "MongoDB, Neo4j y seis modelos", c: "#34d399" },
        { k: "Y das el salto", t: "Datos para LLMs",
          d: "corpus sucio vs limpio", c: "#a78bfa" },
    ];
    return steps.map((s, i) => `
        <a class="arc-step" href="#learn" style="--accent:${s.c}">
            <span class="arc-k">${s.k}</span>
            <span class="arc-t">${s.t}</span>
            <span class="arc-d">${s.d}</span>
        </a>${i < steps.length - 1 ? '<span class="arc-sep">→</span>' : ''}`).join("");
}

async function renderHome() {
    const el = document.getElementById("content");
    const [cat, status, infra, prof] = await Promise.all([
        getCatalog(), fetchJSON("/api/hub/status"), fetchJSON("/api/hub/infra"),
        safeJSON("/api/hub/profiles"),
    ]);
    const P = (prof && prof.profiles) || {};
    const onlineMap = {}; status.apps.forEach(a => onlineMap[a.key] = a.online);

    // Títulos de los conceptos, para etiquetar cada laboratorio con lo que enseña.
    const appMap = {}; cat.apps.forEach(a => appMap[a.key] = a);
    const titles = {};
    buildConcepts({ app: appMap, P }, infra, k => (appMap[k] || {}).url_public || "#")
        .forEach(c => titles[c.n] = c.title);

    const cards = cat.apps.map(app => {
        const ds = (infra.data || {})[app.key] || {};
        const learns = (APP_CONCEPTS[app.key] || []).map(n =>
            `<a class="lc-chip" href="#learn">${titles[n] || ""}</a>`).join("");
        return `
        <div class="app-card" style="--accent:${app.color}">
            <div class="accent-bar"></div>
            <h2>${app.name}</h2>
            <div class="tagline">${app.tagline}</div>
            <p>${app.description}</p>
            <div class="lc-what">Aquí practicas</div>
            <div class="lc-chips">${learns}</div>
            <div class="tags">${app.tech.map(t=>`<span class="tag">${t}</span>`).join("")}</div>
            <div class="card-foot">
                <span class="port">${dot(onlineMap[app.key])}${app.url_public.replace('http://localhost','')} · ${app.exercises} ejercicios
                    ${ds.seeded ? '· <span style="color:#34d399">datos listos</span>' : '· <span style="color:#64748b">sin datos</span>'}</span>
                <a class="open-btn" href="${app.url_public}" target="_blank">Abrir →</a>
            </div>
        </div>`;
    }).join("");

    el.innerHTML = `
        <div class="hero">
            <h1>✦ QUASAR</h1>
            <p>Del dato crudo al modelo entrenado. Tres laboratorios y ${cat.total_exercises} ejercicios sobre un mismo stack: MongoDB, Neo4j y Spark.</p>
        </div>

        <div class="arc">${courseArc(P)}</div>
        <p class="arc-foot-link">
            <a href="#learn">Las ${Object.keys(titles).length} ideas del curso, en detalle →</a>
        </p>

        <h2 class="home-h">Dónde se practica</h2>
        <div class="app-grid">${cards}</div>

        <div class="infra-strip" style="margin-top:24px">
            ${infraChip("MongoDB", infra.infra.mongodb.online, infra.infra.mongodb.role)}
            ${infraChip("Neo4j", infra.infra.neo4j.online, infra.infra.neo4j.role, "http://localhost:7474")}
            <span class="infra-summary">${status.summary.apps_online}/${status.summary.apps_total} apps · ${status.summary.blocks_unlocked}/${status.summary.blocks_total} bloques destapados</span>
        </div>
        <p class="muted" style="text-align:center;margin-top:18px">
            <a href="#onboarding" style="color:#38bdf8">Primeros pasos →</a> ·
            <a href="#arch" style="color:#38bdf8">Cómo funciona Quasar →</a> ·
            <a href="#status" style="color:#38bdf8">Estado del ecosistema →</a>
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

// --- Helpers de "datos vivos" para las tarjetas de concepto ---
function liveDirtSummary(prof) {
    const llm = prof.llmprep, prep = prof.preprolab;
    if (!llm && !prep) return liveHint();
    let noisy = 0, nulls = 0;
    if (llm) noisy = (llm.docs || 0) - (llm.clean_docs || 0);
    if (prep) for (const t of Object.values(prep))
        for (const c of Object.values(t.columns || {})) nulls += c.nulls || 0;
    return `<span class="cc-live-num">${noisy.toLocaleString('es')}</span> docs con ruido en tu corpus ·
            <span class="cc-live-num">${nulls.toLocaleString('es')}</span> valores perdidos en tu flota de robots`;
}

function liveInfra(infra) {
    const i = infra.infra; if (!i) return liveHint();
    const chip = (o, name) => `<span class="cc-chip ${o?'up':'down'}">${dot(o)}${name}</span>`;
    return `${chip(i.mongodb.online, "MongoDB")} ${chip(i.neo4j.online, "Neo4j")}
            ${i.neo4j.online ? `<a href="${i.neo4j.browser}" target="_blank" style="color:#38bdf8">abrir grafo ↗</a>` : ''}`;
}

function liveLayers(infra, prof) {
    const d = infra.data || {};
    const row = (key, name) => {
        const s = d[key] || {};
        const mark = ok => ok ? '<span style="color:#34d399">✓</span>' : '<span style="color:#64748b">·</span>';
        return `<div class="cc-layer"><span>${name}</span>
            <span>${mark(s.seeded)} raw ${mark(s.has_silver)} silver ${mark(s.has_gold)} gold</span></div>`;
    };
    return row('sociallab','SocialLab') + row('preprolab','PreproLab') + row('llmprep','LLM Lab');
}

function liveNoise(prof) {
    const llm = prof.llmprep;
    if (!llm || !llm.noise_types) return liveHint();
    const chips = Object.entries(llm.noise_types)
        .sort((a,b) => b[1]-a[1]).slice(0,7)
        .map(([k,v]) => `<span class="cc-chip"><b>${v}</b> ${k}</span>`).join("");
    return `En tu corpus ahora mismo: ${chips}`;
}

function liveHint() {
    return `<span class="muted">Genera datos y corre el ETL en <a href="#" onclick="showView('status');return false" style="color:#38bdf8">Estado</a> para ver esto con tus propios datos.</span>`;
}

function practiceLink(p) {
    if (!p) return "";
    if (p.href) return `<a class="cc-go" href="${p.href}" target="_blank">${p.label} →</a>`;
    return `<a class="cc-go" href="#" onclick="showView('${p.view}');return false">${p.label} →</a>`;
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

function conceptCard(c, ctx) {
    let drill = "";
    const parts = [];
    if (c.more) parts.push(`<div class="cc-lesson">${c.more}</div>`);
    if (c.radiografia) parts.push(`<div class="cc-rx">${radiografia(ctx.P, ctx.gen)}</div>`);
    if (c.blocksOf) parts.push(conceptBlocks(ctx.app[c.blocksOf], ctx.flags, c.flagFilter));
    if (parts.length) {
        drill = `<details class="cc-more"><summary>Ampliar</summary><div class="cc-more-body">${parts.join("")}</div></details>`;
    }
    return `<div class="concept-card" style="--accent:${c.color}">
        <div class="cc-head"><span class="cc-num">${c.n}</span><span class="cc-tag">${c.tag}</span></div>
        <h3 class="cc-title">${c.title}</h3>
        <p class="cc-what">${c.what}</p>
        <div class="cc-idea"><span class="cc-idea-k">IDEA CLAVE</span> ${c.idea}</div>
        ${c.live ? `<div class="cc-live">${c.live}</div>` : ""}
        ${drill}
        ${practiceLink(c.practice)}
    </div>`;
}

async function renderLearn() {
    const el = document.getElementById("content");
    el.innerHTML = "<div class='loading'>preparando la introducción...</div>";
    const [cat, infra, prof, flagsResp] = await Promise.all([
        getCatalog(), safeJSON("/api/hub/infra"), safeJSON("/api/hub/profiles"), safeJSON("/api/hub/flags"),
    ]);
    const P = (prof && prof.profiles) || {};
    const gen = (prof && prof.generated_at) || {};
    const flags = (flagsResp && flagsResp.flags) || {};
    const app = {};
    cat.apps.forEach(a => app[a.key] = a);
    const url = k => (app[k] || {}).url_public || "#";
    const ctx = { app, flags, P, gen };

    const concepts = buildConcepts(ctx, infra, url);

    el.innerHTML = `
        <div class="hero" style="padding-bottom:20px">
            <h1>La asignatura en 10 ideas</h1>
            <p>De los datos en crudo al modelo entrenado. Cada idea te lleva al laboratorio donde se trabaja, y varias las verás con <strong>tus propios datos</strong>, no con ejemplos de pizarra.</p>
        </div>
        <div class="concept-grid">${concepts.map(c => conceptCard(c, ctx)).join("")}</div>
        <p class="muted" style="text-align:center;margin-top:26px">
            ¿Listo para empezar? <a href="#onboarding" style="color:#38bdf8">Primeros pasos →</a> ·
            <a href="#arch" style="color:#38bdf8">Cómo encaja todo →</a>
        </p>`;
}

// Fuente única de los conceptos: los usan Aprende (completos) y la
// portada (en versión resumida). Definirlos dos veces era garantía de
// que acabaran diciendo cosas distintas.
function buildConcepts(ctx, infra, url) {
    const { app, P } = ctx;
    return [
        { n:1, color:"#38bdf8", tag:"Punto de partida", title:"Datos masivos = datos sucios a escala",
          what:"Los datos reales no vienen limpios: faltan campos, se repiten registros, las fechas aparecen en cinco formatos y hay demasiados para abrirlos en Excel.",
          idea:"Nadie va a tener datos limpios en su carrera. Aprender a arreglarlos es de lo que va todo esto.",
          live: liveDirtSummary(P) },
        { n:2, color:"#10b981", tag:"Almacenamiento", title:"Persistencia poliglota",
          what:"Ninguna base es buena en todo, así que aquí conviven dos: MongoDB para documentos que cambian de forma y Neo4j para las relaciones entre ellos.",
          idea:"Pídele a Mongo el camino más corto entre dos usuarios, o sus comunidades, y sufrirás. Neo4j lo resuelve en una línea de Cypher.",
          more:"MongoDB guarda cada usuario como un documento JSON, y dos usuarios pueden tener campos distintos sin migrar nada. Neo4j guarda lo mismo pero como nodos y aristas, y ahí las preguntas cambian de naturaleza: «¿a quién sigue la gente que sigue a X?» es un recorrido de grafo, no una tabla con JOINs. Por eso conviven las dos.",
          blocksOf:"sociallab", flagFilter:"LAB_NEO4J",
          live: liveInfra(infra), practice:{label:"Practica en SocialLab", href:url('sociallab')} },
        { n:3, color:"#fbbf24", tag:"Ingeniería de datos", title:"El ciclo de vida del dato: raw → silver → gold",
          what:"El data lake se organiza en tres capas: <b>raw</b> es lo que llega tal cual, <b>silver</b> ya está limpio y normalizado, y <b>gold</b> está agregado y listo para consumir.",
          idea:"raw es materia prima, gold es lo servible. Entre medias no se tira nada: cada capa se apoya en la de antes.",
          more:"raw se escribe una vez y no se toca: es tu copia fiel de lo que llegó, con su suciedad incluida. silver aplica la limpieza y fija tipos estables. gold agrega y da forma a lo que consume la app o el modelo. Si algo sale raro más adelante, siempre puedes volver a raw y rehacer el pipeline entero.",
          live: liveLayers(infra, P), practice:{label:"Mira la arquitectura", view:"arch"} },
        { n:4, color:"#e75a9c", tag:"Procesamiento", title:"ETL con Spark",
          what:"El pipeline que lleva de raw a gold. Lo escribes en PySpark y corre igual en tu portátil que en un cluster de Databricks: mismo código, distinta escala.",
          idea:"Si el ETL está mal, la app enseña basura, por bonita que sea la interfaz.",
          more:"El ETL es código, no clics: cada transformación queda escrita y se puede volver a ejecutar tal cual. En local corres PySpark sobre tu máquina; cuando el volumen crece, el mismo script se lanza en un cluster sin reescribirlo. Cambia la escala, no la lógica.",
          practice:{label:"Corre el ETL en Estado", view:"status"} },
        { n:5, color:"#a855f7", tag:"Calidad de datos", title:"La suciedad, catalogada",
          what:"Cada problema tiene su nombre: fechas en cinco formatos, encoding roto, duplicados, referencias huérfanas, ruido en las etiquetas, PII, casi-duplicados…",
          idea:"Antes de arreglar nada hay que saber qué tienes delante. A cada tipo de suciedad le toca una técnica distinta.",
          more:"Ninguna de estas suciedades es casual: el generador de datos las inyecta a propósito para que aprendas a detectarlas y a medir cuánta hay. Esta es la radiografía de lo que tienes ahora mismo en tus datos:",
          radiografia:true, blocksOf:"llmprep",
          live: liveNoise(P), practice:{label:"Detéctala en LLM Lab", href:url('llmprep')} },
        { n:6, color:"#1d9bf0", tag:"Tema 5", title:"Preprocesamiento sistemático",
          what:"El Tema 5 al completo: valores perdidos (media, KNN, K-Means), outliers, normalización, discretización y reducción de dimensiones e instancias.",
          idea:"Para cada decisión hay un criterio, y una forma de comprobar si el cambio mejoró el modelo o solo lo movió de sitio.",
          more:"PreproLab trabaja sobre una flota de robots con mantenimiento predictivo: cuatro tablas con catorce problemas plantados a mano (nulls MCAR/MAR/MNAR, outliers, ruido en las etiquetas, duplicados, fechas en varios formatos, columnas redundantes…). Recorres las técnicas del tema en orden y, al final, el Pipeline Studio te deja componer tu propio preprocesamiento y ver qué modelo sale mejor.",
          blocksOf:"preprolab",
          practice:{label:`PreproLab · ${(app.preprolab||{}).exercises||37} ejercicios`, href:url('preprolab')} },
        { n:7, color:"#34d399", tag:"Modelado", title:"Machine Learning sobre los datos",
          what:"Con los datos ya limpios entrenas los modelos: supervisados (spam, churn), no supervisados (clustering) y sobre grafo (a quién seguir).",
          idea:"Ojo con el churn_predictor: lleva una fuga de datos puesta a propósito, para que aprendas a oler cuándo un modelo es sospechosamente bueno.",
          more:"Seis modelos en tres familias. Supervisado: predecir spam, engagement o abandono a partir de ejemplos etiquetados. No supervisado: agrupar usuarios parecidos sin decirle antes cuántos grupos hay. Sobre grafo: recomendar a quién seguir usando la forma de la red, no solo el contenido.",
          blocksOf:"sociallab", flagFilter:"LAB_ML",
          practice:{label:"SocialLab · 6 modelos", href:url('sociallab')} },
        { n:8, color:"#a78bfa", tag:"IA / LLMs", title:"Preparar datos para modelos de lenguaje",
          what:"Un modelo de lenguaje se entrena con un corpus. Prepararlo es limpiarlo, quitar duplicados (MinHash/LSH), tokenizarlo (BPE) y comprobar que ha quedado mejor.",
          idea:"El mismo modelo, con el corpus sucio y con el limpio: la perplejidad baja. No cambió el modelo, cambiaron los datos.",
          more:"LLM Lab parte de un corpus tipo Wikipedia en español, sucio a propósito. Lo limpias (encoding, HTML, idioma, PII), le quitas los casi-duplicados con MinHash/LSH y guardas el parecido como grafo en Neo4j, lo tokenizas con un BPE hecho a mano y entrenas un modelo pequeño. La demo final entrena el mismo modelo con el corpus sucio y con el limpio para que veas la diferencia.",
          blocksOf:"llmprep",
          practice:{label:"LLM Lab · corpus", href:url('llmprep')} },
        { n:9, color:"#7dd3fc", tag:"Buenas prácticas", title:"Reproducibilidad y gobernanza",
          what:"Toda la lógica de transformación vive en el ETL, versionado en git, no en pasos manuales que nadie recuerda. Se puede regenerar todo desde cero.",
          idea:"Si no puedes reconstruir un dato desde su origen, no lo controlas: lo estás improvisando.",
          more:"Versionar el ETL en git significa que el dato no depende de que alguien recuerde qué tocó a mano un martes por la tarde. Cualquiera clona el repo, ejecuta el pipeline y obtiene exactamente lo mismo. Eso es lo que separa un análisis que se sostiene de uno que no se puede repetir." },
        { n:10, color:"#f472b6", tag:"Cómo se aprende aquí", title:"Método scaffold / solución",
          what:"Cada algoritmo está dos veces: el hueco a rellenar (scaffold, con un NotImplementedError) y la solución. Un flag decide cuál se sirve, sin tocar el código.",
          idea:"Empiezas con el ejercicio en blanco; cuando lo implementas, la tarjeta de la app se enciende sola.",
          more:"En cualquier concepto de arriba puedes pulsar «Ampliar» y alternar cada bloque entre solución y ejercicio tú mismo: es tu copia de la app, así que mandas tú. Ver la solución primero para estudiarla, o dejarla en blanco para pelearte con ella, lo eliges según te venga.",
          practice:{label:"Cómo funciona Quasar", view:"arch"} },
    ];
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
            <p>Pásate por <a href="#learn" style="color:#38bdf8">Aprende</a>: diez ideas que resumen la asignatura, cada una con el laboratorio donde se trabaja. Diez minutos que ahorran mucha confusión luego.</p>
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
