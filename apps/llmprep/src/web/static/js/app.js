// LLM Lab - SPA (Fase 14: bloque clean operativo)

const BLOCK_INFO = {
    clean:    { label: "1 · Clean",    desc: "Normalización Unicode, fix encoding, HTML strip, filtro de longitud, idioma, PII.", render: renderClean },
    dedup:    { label: "2 · Dedup",    desc: "Near-duplicates con MinHash/LSH + grafo SIMILAR_TO en Neo4j.", render: renderDedup },
    tokenize: { label: "3 · Tokenize", desc: "Tokenizer BPE + shards .bin estilo nanoGPT.", render: renderTokenize },
    train:    { label: "4 · Train ★",  desc: "Modelo de lenguaje + comparativa corpus sucio vs limpio.", render: renderTrain },
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

// ============================================================
// Bloque DEDUP
// ============================================================

async function renderDedup() {
    const unlocked = (LAB_STATUS.blocks || {}).dedup;
    document.getElementById("content").innerHTML = `
        <h1>2 · Dedup — duplicados y near-duplicates</h1>
        <p class="muted">Estado: ${unlocked ? "<strong>resuelto</strong>" : "<strong>scaffold</strong>"}. MinHash + LSH para detectar casi-duplicados, y carga del grafo <code>:Document -[:SIMILAR_TO]-> :Document</code> a Neo4j (la pata poliglota de LLM Lab).</p>

        <section class="card">
            <h2>Detección</h2>
            <div class="row" style="flex-wrap:wrap;gap:8px">
                <button class="tbtn" onclick="runDedup('exact','DEDUP-1','GET')">DEDUP-1 · exact</button>
                <button class="tbtn" onclick="runDedup('minhash','DEDUP-2','GET')">DEDUP-2 · minhash</button>
                <button class="tbtn" onclick="runDedup('lsh_candidates','DEDUP-3','GET')">DEDUP-3 · lsh_candidates</button>
            </div>
            <div id="dedup-result"></div>
        </section>

        <section class="card">
            <h2>Grafo Neo4j</h2>
            <div class="row" style="flex-wrap:wrap;gap:8px">
                <button class="tbtn" style="background:#7c3aed;color:#fff;border-color:#7c3aed" onclick="runDedup('build_graph','DEDUP-4','POST')">DEDUP-4 · build_graph</button>
                <button class="tbtn" onclick="runDedup('graph_clusters','DEDUP-5','GET')">DEDUP-5 · graph_clusters</button>
                <span class="muted">Explora el grafo en el Neo4j browser: <code>http://localhost:7474</code></span>
            </div>
            <div id="dedup-graph-result"></div>
        </section>
    `;
}

async function runDedup(technique, exercise, method) {
    const targetId = (technique === "build_graph" || technique === "graph_clusters") ? "dedup-graph-result" : "dedup-result";
    const el = document.getElementById(targetId);
    el.innerHTML = "<p class='loading'>computando (MinHash/LSH puede tardar ~10s)...</p>";
    const res = await fetch(`/api/llmprep/dedup/${technique}`, { method });
    const data = await res.json();
    if (data.error === "scaffold") {
        el.innerHTML = `<div class="placeholder" style="text-align:left">
            <p><strong style="color:#fbbf24">Ejercicio ${data.exercise} sin resolver.</strong></p>
            <p class="muted">${data.hint}</p>
            <p class="muted">Implementa en <code>apps/llmprep/src/web/routes/dedup_ex.py</code>.</p>
        </div>`;
        return;
    }
    if (data.error) { el.innerHTML = `<p class="error">${data.detail || data.error}</p>`; return; }

    let html = `<h3 style="margin-top:14px">${data.technique}</h3><table class='kv stats-table'>`;
    Object.entries(data).forEach(([k, v]) => {
        if (["examples","top_pairs","high_similarity_pairs","top_documents_by_neighbors","technique","note","graph_stats"].includes(k)) return;
        html += `<tr><th>${k}</th><td>${typeof v === "number" ? v.toLocaleString() : (typeof v === "object" ? JSON.stringify(v) : v)}</td></tr>`;
    });
    html += "</table>";
    if (data.graph_stats) html += `<p class="muted">Grafo: ${data.graph_stats.nodes} nodos, ${data.graph_stats.edges} aristas SIMILAR_TO.</p>`;

    const listKey = ["top_pairs","high_similarity_pairs","examples","top_documents_by_neighbors"].find(k => data[k] && data[k].length);
    if (listKey) {
        html += `<h3 style="margin-top:12px">${listKey}</h3>`;
        html += "<table class='kv'><thead><tr>" + Object.keys(data[listKey][0]).map(k=>`<th>${k}</th>`).join("") + "</tr></thead><tbody>";
        data[listKey].forEach(row => {
            html += "<tr>" + Object.values(row).map(v=>`<td>${typeof v === "number" ? v : String(v).slice(0,40)}</td>`).join("") + "</tr>";
        });
        html += "</tbody></table>";
    }
    if (data.note) html += `<p class="muted" style="margin-top:8px"><em>${data.note}</em></p>`;
    el.innerHTML = html;
}

// ============================================================
// Bloque TOKENIZE
// ============================================================

async function renderTokenize() {
    const unlocked = (LAB_STATUS.blocks || {}).tokenize;
    document.getElementById("content").innerHTML = `
        <h1>3 · Tokenize — BPE</h1>
        <p class="muted">Estado: ${unlocked ? "<strong>resuelto</strong>" : "<strong>scaffold</strong>"}. Entrena un tokenizer BPE desde cero sobre el corpus limpio y genera los shards binarios que alimentan el entrenamiento.</p>

        <section class="card">
            <h2>Pipeline de tokenización</h2>
            <div class="row" style="flex-wrap:wrap;gap:8px;align-items:center">
                <label>merges: <input type="number" id="tok-merges" value="500" min="50" max="2000" style="width:70px"></label>
                <button class="tbtn" onclick="runTok('train','TOK-1','GET','tok-merges')">TOK-1 · train</button>
                <button class="tbtn" onclick="runTok('encode','TOK-2','GET')">TOK-2 · encode</button>
                <button class="tbtn" onclick="runTok('vocab_stats','TOK-3','GET')">TOK-3 · vocab_stats</button>
                <button class="tbtn" style="background:#7c3aed;color:#fff;border-color:#7c3aed" onclick="runTok('build_shards','TOK-4','POST')">TOK-4 · build_shards</button>
            </div>
            <p class="muted" style="font-size:12px">Ejecuta TOK-1 primero (entrena y cachea el tokenizer). Luego encode/vocab_stats/build_shards lo reutilizan.</p>
            <div id="tok-result"></div>
        </section>
    `;
}

async function runTok(technique, exercise, method, mergesId) {
    const el = document.getElementById("tok-result");
    el.innerHTML = "<p class='loading'>procesando (BPE puede tardar ~10-20s)...</p>";
    let url = `/api/llmprep/tokenize/${technique}`;
    if (technique === "train" && mergesId) url += `?num_merges=${document.getElementById(mergesId).value}`;
    const res = await fetch(url, { method });
    const data = await res.json();
    if (data.error === "scaffold") {
        el.innerHTML = `<div class="placeholder" style="text-align:left">
            <p><strong style="color:#fbbf24">Ejercicio ${data.exercise} sin resolver.</strong></p>
            <p class="muted">${data.hint}</p>
            <p class="muted">Implementa en <code>apps/llmprep/src/web/routes/tokenize_ex.py</code>.</p>
        </div>`;
        return;
    }
    if (data.error) { el.innerHTML = `<p class="error">${data.detail || data.error}</p>`; return; }

    let html = `<h3 style="margin-top:14px">${data.technique}</h3><table class='kv stats-table'>`;
    Object.entries(data).forEach(([k, v]) => {
        if (["technique","note","first_merges","tokens","ids","most_common_tokens","files"].includes(k)) return;
        html += `<tr><th>${k}</th><td>${typeof v === "number" ? v.toLocaleString() : (typeof v === "object" ? JSON.stringify(v) : v)}</td></tr>`;
    });
    html += "</table>";
    if (data.first_merges) html += `<p class="muted">Primeros merges: <code>${data.first_merges.join(" · ")}</code></p>`;
    if (data.tokens) html += `<p class="muted">Tokens: <code>${data.tokens.join(" ")}</code></p>`;
    if (data.files) html += `<p class="muted">Shards generados: <code>${JSON.stringify(data.files)}</code></p>`;
    if (data.most_common_tokens) {
        html += "<h3 style='margin-top:12px'>Tokens más frecuentes</h3>";
        html += "<table class='kv'><thead><tr><th>token</th><th>count</th></tr></thead><tbody>";
        data.most_common_tokens.forEach(t => { html += `<tr><td><code>${t.token}</code></td><td>${t.count.toLocaleString()}</td></tr>`; });
        html += "</tbody></table>";
    }
    if (data.note) html += `<p class="muted" style="margin-top:8px"><em>${data.note}</em></p>`;
    el.innerHTML = html;
}

// ============================================================
// Bloque TRAIN
// ============================================================

async function renderTrain() {
    const unlocked = (LAB_STATUS.blocks || {}).train;
    document.getElementById("content").innerHTML = `
        <h1>4 · Train ★ — modelo de lenguaje</h1>
        <p class="muted">Estado: ${unlocked ? "<strong>resuelto</strong>" : "<strong>scaffold</strong>"}. Entrena un modelo de lenguaje sobre el corpus y comprueba el impacto de la limpieza. <strong>TRAIN-3 es la demo culminante de LLM Lab.</strong></p>

        <section class="card">
            <h2>TRAIN-1 · Entrenar + TRAIN-2 · Generar</h2>
            <div class="row" style="flex-wrap:wrap;gap:8px;align-items:center">
                <button class="tbtn" onclick="runTrain('train','TRAIN-1','GET')">TRAIN-1 · train</button>
                <label>prompt: <input type="text" id="train-prompt" value="la fotosíntesis" style="width:160px"></label>
                <label>temp: <input type="number" id="train-temp" value="0.8" step="0.1" min="0.1" max="2" style="width:60px"></label>
                <button class="tbtn" onclick="runTrain('generate','TRAIN-2','GET')">TRAIN-2 · generate</button>
            </div>
            <div id="train-result"></div>
        </section>

        <section class="card" style="border-color:#7c3aed">
            <h2>TRAIN-3 ★ · Demo: corpus sucio vs limpio</h2>
            <p class="muted">Entrena dos modelos idénticos —uno sobre el corpus crudo, otro sobre el limpio— y compara perplexity + generación. Tarda ~5-10s.</p>
            <div class="row">
                <label>prompt: <input type="text" id="cmp-prompt" value="la" style="width:120px"></label>
                <button class="tbtn" style="background:#7c3aed;color:#fff;border-color:#7c3aed" onclick="runCompareTrain()">▶ Ejecutar comparativa</button>
            </div>
            <div id="train-compare"></div>
        </section>
    `;
}

async function runTrain(technique, exercise, method) {
    const el = document.getElementById("train-result");
    el.innerHTML = "<p class='loading'>procesando...</p>";
    let url = `/api/llmprep/train/${technique}`;
    if (technique === "generate") {
        const p = encodeURIComponent(document.getElementById("train-prompt").value);
        const t = document.getElementById("train-temp").value;
        url += `?prompt=${p}&temperature=${t}`;
    }
    const data = await (await fetch(url, { method })).json();
    if (data.error === "scaffold") {
        el.innerHTML = `<div class="placeholder" style="text-align:left">
            <p><strong style="color:#fbbf24">Ejercicio ${data.exercise} sin resolver.</strong></p>
            <p class="muted">${data.hint}</p>
            <p class="muted">Implementa en <code>apps/llmprep/src/web/routes/train_ex.py</code>.</p>
        </div>`;
        return;
    }
    if (data.error) { el.innerHTML = `<p class="error">${data.detail || data.error}</p>`; return; }

    if (technique === "generate") {
        el.innerHTML = `
            <h3 style="margin-top:14px">Generación (prompt: "${data.prompt}", temp ${data.temperature})</h3>
            <div style="background:#14101f;padding:14px;border-radius:8px;color:#d7d0e6;line-height:1.6">${data.generated}</div>`;
        return;
    }
    // train
    let html = `<h3 style="margin-top:14px">${data.model}</h3><table class='kv stats-table'>`;
    Object.entries(data).forEach(([k, v]) => {
        if (["technique","note","model"].includes(k)) return;
        html += `<tr><th>${k}</th><td>${typeof v === "number" ? v.toLocaleString() : v}</td></tr>`;
    });
    html += "</table>";
    if (data.note) html += `<p class="muted" style="margin-top:8px"><em>${data.note}</em></p>`;
    el.innerHTML = html;
}

async function runCompareTrain() {
    const el = document.getElementById("train-compare");
    el.innerHTML = "<p class='loading'>entrenando 2 modelos (sucio + limpio)...</p>";
    const p = encodeURIComponent(document.getElementById("cmp-prompt").value);
    const data = await (await fetch(`/api/llmprep/train/compare?prompt=${p}`)).json();
    if (data.error === "scaffold") {
        el.innerHTML = `<div class="placeholder" style="text-align:left">
            <p><strong style="color:#fbbf24">Ejercicio ${data.exercise} sin resolver.</strong></p>
            <p class="muted">${data.hint}</p>
        </div>`;
        return;
    }
    if (data.error) { el.innerHTML = `<p class="error">${data.detail || data.error}</p>`; return; }

    const d = data.dirty, c = data.clean;
    el.innerHTML = `
        <div style="display:flex;gap:16px;margin-top:14px;flex-wrap:wrap">
            <div style="flex:1;min-width:280px;background:#2a1620;border:1px solid #5a2a3a;border-radius:10px;padding:16px">
                <h3 style="color:#f87171">Corpus SUCIO</h3>
                <p class="muted">vocab: ${d.vocab_size.toLocaleString()} · perplexity: <strong style="color:#f87171;font-size:18px">${d.perplexity}</strong></p>
                <div style="background:#14101f;padding:10px;border-radius:6px;margin-top:8px;font-size:13px;line-height:1.5">${d.generated}</div>
            </div>
            <div style="flex:1;min-width:280px;background:#142a1f;border:1px solid #2a5a3a;border-radius:10px;padding:16px">
                <h3 style="color:#34d399">Corpus LIMPIO</h3>
                <p class="muted">vocab: ${c.vocab_size.toLocaleString()} · perplexity: <strong style="color:#34d399;font-size:18px">${c.perplexity}</strong></p>
                <div style="background:#14101f;padding:10px;border-radius:6px;margin-top:8px;font-size:13px;line-height:1.5">${c.generated}</div>
            </div>
        </div>
        <p style="margin-top:14px;text-align:center;font-size:16px">Mejora de perplexity con limpieza: <strong style="color:#a78bfa">${data.perplexity_improvement_pct}%</strong></p>
        <div class="placeholder" style="text-align:left;margin-top:12px"><p class="muted"><em>${data.conclusion}</em></p></div>
    `;
}

(async function init() {
    LAB_STATUS = await loadStatus();
    renderBlocks(LAB_STATUS);
    selectBlock("clean");
    const li = document.querySelector('[data-block="clean"]');
    if (li) li.classList.add("active");
})();
