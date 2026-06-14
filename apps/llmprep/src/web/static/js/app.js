// LLM Lab - SPA (Fase 14: bloque clean operativo)

const BLOCK_INFO = {
    clean:    { label: "1 · Clean",    desc: "Normalización Unicode, fix encoding, HTML strip, filtro de longitud, idioma, PII.", render: renderClean },
    dedup:    { label: "2 · Dedup",    desc: "Near-duplicates con MinHash/LSH + grafo SIMILAR_TO en Neo4j." },
    tokenize: { label: "3 · Tokenize", desc: "Tokenizer BPE + shards .bin estilo nanoGPT." },
    train:    { label: "4 · Train",    desc: "nanoGPT + comparativa corpus sucio vs limpio." },
};

let LAB_STATUS = null;

async function fetchJSON(url) {
    const res = await fetch(url);
    if (!res.ok && res.status !== 503) return { error: `HTTP ${res.status}`, status: res.status };
    return res.json();
}

async function loadStatus() {
    try { return await fetchJSON("/api/llmprep/lab/status"); }
    catch (e) { return { blocks: {} }; }
}

function renderBlocks(status) {
    const list = document.getElementById("block-list");
    list.innerHTML = "";
    Object.entries(BLOCK_INFO).forEach(([key, info]) => {
        const unlocked = status.blocks && status.blocks[key];
        const li = document.createElement("li");
        const dot = document.createElement("span");
        dot.className = "dot " + (unlocked ? "dot-unlocked" : "dot-locked");
        li.appendChild(dot);
        li.appendChild(document.createTextNode(info.label));
        li.dataset.block = key;
        li.addEventListener("click", () => selectBlock(key));
        list.appendChild(li);
    });
}

function selectBlock(key) {
    document.querySelectorAll("#block-list li").forEach(li => {
        li.classList.toggle("active", li.dataset.block === key);
    });
    const info = BLOCK_INFO[key];
    if (info.render) info.render();
    else renderPlaceholder(key, info);
}

function renderPlaceholder(key, info) {
    const unlocked = LAB_STATUS.blocks && LAB_STATUS.blocks[key];
    document.getElementById("content").innerHTML = `
        <h1>${info.label}</h1>
        <p>${info.desc}</p>
        <div class="placeholder">
            <h3>Bloque en construcción</h3>
            <p>Se implementará en las fases siguientes del roadmap.</p>
            <p class="muted">Estado: ${unlocked ? "resuelto" : "scaffold"}</p>
            <p class="muted">Para desbloquear: <code>./lab.sh llmprep unlock ${key}</code></p>
        </div>
    `;
}

function _showError(id, data) {
    document.getElementById(id).innerHTML = `<p class="error">${data.detail || data.error}</p>`;
}

// ============================================================
// Bloque CLEAN
// ============================================================

async function renderClean() {
    const content = document.getElementById("content");
    const unlocked = (LAB_STATUS.blocks || {}).clean;
    content.innerHTML = `
        <h1>1 · Clean — limpieza del corpus</h1>
        <p class="muted">Estado: ${unlocked ? "<strong>resuelto</strong>" : "<strong>scaffold</strong> (los endpoints devuelven placeholder hasta que implementes el ejercicio)"}. Cada técnica se valida contra el ground truth <code>_noise</code> del corpus.</p>

        <section class="card">
            <h2>Estadísticas del corpus crudo</h2>
            <div id="clean-stats" class="loading">cargando...</div>
        </section>

        <section class="card">
            <h2>Técnicas de limpieza</h2>
            <div class="row" style="flex-wrap:wrap;gap:8px">
                <button class="tbtn" onclick="runClean('fix_encoding','CLEAN-1')">CLEAN-1 · fix_encoding</button>
                <button class="tbtn" onclick="runClean('strip_html','CLEAN-2')">CLEAN-2 · strip_html</button>
                <button class="tbtn" onclick="runClean('length_filter','CLEAN-3')">CLEAN-3 · length_filter</button>
                <button class="tbtn" onclick="runClean('language_filter','CLEAN-4')">CLEAN-4 · language_filter</button>
                <button class="tbtn" onclick="runClean('pii_removal','CLEAN-5')">CLEAN-5 · pii_removal</button>
                <button class="tbtn" style="background:#7c3aed;color:#fff;border-color:#7c3aed" onclick="runClean('pipeline','CLEAN-6')">CLEAN-6 · pipeline (las 5)</button>
            </div>
            <div id="clean-result"></div>
        </section>
    `;
    await loadCorpusStats();
}

async function loadCorpusStats() {
    const el = document.getElementById("clean-stats");
    const data = await fetchJSON("/api/llmprep/clean/corpus_stats");
    if (data.error) { el.innerHTML = `<p class="error">${data.detail || data.error}</p>`; return; }
    let html = `
        <table class='kv stats-table'>
            <tr><th>Documentos</th><td>${data.n_docs.toLocaleString()}</td></tr>
            <tr><th>Caracteres totales</th><td>${data.total_chars.toLocaleString()} (media ${data.avg_chars}/doc)</td></tr>
            <tr><th>Limpios / con ruido</th><td>${data.clean_docs.toLocaleString()} / ${data.noisy_docs.toLocaleString()}</td></tr>
        </table>
        <h3 style="margin-top:12px">Distribución de ruido (ground truth)</h3>
    `;
    const div = document.createElement("div");
    div.style.height = "280px";
    el.innerHTML = html;
    el.appendChild(div);
    const entries = Object.entries(data.noise_distribution).sort((a,b)=>b[1]-a[1]);
    Plotly.newPlot(div, [{
        x: entries.map(e=>e[0]), y: entries.map(e=>e[1]), type: "bar",
        marker: { color: "#a78bfa" },
    }], {
        paper_bgcolor: "#1c1630", plot_bgcolor: "#1c1630", font: { color: "#d7d0e6" },
        xaxis: { tickangle: -45 }, yaxis: { title: "docs" },
        margin: { l: 50, r: 20, t: 10, b: 110 },
    }, { displayModeBar: false });
}

async function runClean(technique, exercise) {
    const el = document.getElementById("clean-result");
    el.innerHTML = "<p class='loading'>aplicando...</p>";
    const data = await fetchJSON(`/api/llmprep/clean/${technique}`);
    if (data.error === "scaffold") {
        el.innerHTML = `
            <div class="placeholder" style="text-align:left">
                <p><strong style="color:#fbbf24">Ejercicio ${data.exercise} sin resolver.</strong></p>
                <p class="muted">${data.hint}</p>
                <p class="muted">Implementa en <code>apps/llmprep/src/web/routes/clean_ex.py</code>.</p>
            </div>`;
        return;
    }
    if (data.error) return _showError("clean-result", data);

    // Render genérico de métricas + comparación con ground truth
    let html = `<h3 style="margin-top:14px">${data.technique}</h3><table class='kv stats-table'>`;
    Object.entries(data).forEach(([k, v]) => {
        if (k === "examples" || k === "technique" || k === "note" || k === "detected_distribution") return;
        html += `<tr><th>${k}</th><td>${typeof v === "number" ? v.toLocaleString() : v}</td></tr>`;
    });
    html += "</table>";
    if (data.detected_distribution) {
        html += `<p class="muted">Idiomas detectados: ${JSON.stringify(data.detected_distribution)}</p>`;
    }
    if (data.note) html += `<p class="muted" style="margin-top:8px"><em>${data.note}</em></p>`;
    if (data.examples && data.examples.length) {
        html += "<h3 style='margin-top:12px'>Ejemplos</h3>";
        data.examples.forEach(ex => {
            html += `<div style="background:#14101f;padding:8px;border-radius:6px;margin-bottom:6px;font-size:12px;font-family:monospace">`;
            html += Object.entries(ex).map(([k,v])=>`<div><span style="color:#8b7fa8">${k}:</span> ${String(v).slice(0,140)}</div>`).join("");
            html += `</div>`;
        });
    }
    el.innerHTML = html;
}

(async function init() {
    LAB_STATUS = await loadStatus();
    renderBlocks(LAB_STATUS);
    selectBlock("clean");
    const li = document.querySelector('[data-block="clean"]');
    if (li) li.classList.add("active");
})();
