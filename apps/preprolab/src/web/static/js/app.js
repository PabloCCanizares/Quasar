// PreproLab - SPA Fase 3 (EDA operativo)
//
// El tab EDA carga overview + schema + missing + univariate + correlations.
// Los otros bloques siguen como placeholder (se irán activando por fase).

const BLOCK_INFO = {
    eda:          { label: "EDA",               desc: "Analisis univariable + missing matrix + correlaciones.",   render: renderEDA },
    missing:      { label: "Valores perdidos",  desc: "Diagnostico MCAR/MAR/MNAR + imputacion (media, KNN, K-Means, EM, MICE).", render: renderMissing },
    outliers:     { label: "Outliers + ruido",  desc: "IQR, Z-score, boxplot + noise filters (EF/CVCF/IPF).", render: renderOutliers },
    integration:  { label: "Integracion",       desc: "union, joins (4 tipos), correlaciones para deduplicar.", render: renderIntegration },
    transform:    { label: "Transformacion",    desc: "One-hot, ordinal, multi-flag, discretizacion, pivot/groupby.", render: renderTransform },
    normalize:    { label: "Normalizacion",     desc: "Z-score, Min-Max, Robust, Decimal - comparados sobre mismo modelo.", render: renderNormalize },
    reduce_dim:   { label: "Reduccion dim.",    desc: "PCA, t-SNE, AutoEncoders + feature selection.", render: renderReduceDim },
    reduce_inst:  { label: "Reduccion inst.",   desc: "SRSWOR, estratificado, balanceado, K-Means compresion.", render: renderReduceInst },
};

const TABLES = ["robots", "sensors_readings", "events", "maintenances"];

let LAB_STATUS = null;
let CURRENT_TABLE = "robots";

async function fetchJSON(url) {
    const res = await fetch(url);
    if (!res.ok && res.status !== 503) {
        return { error: `HTTP ${res.status}`, status: res.status };
    }
    return res.json();
}

async function loadStatus() {
    try {
        return await fetchJSON("/api/preprolab/lab/status");
    } catch (e) {
        console.error("Failed to load lab status", e);
        return { blocks: {} };
    }
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
    if (info.render) {
        info.render();
    } else {
        renderPlaceholder(key, info);
    }
}

function renderPlaceholder(key, info) {
    const unlocked = LAB_STATUS.blocks && LAB_STATUS.blocks[key];
    document.getElementById("content").innerHTML = `
        <h1>${info.label}</h1>
        <p>${info.desc}</p>
        <div class="placeholder">
            <h3>Bloque en construccion</h3>
            <p>Este bloque se implementara en las fases siguientes del roadmap Quasar.</p>
            <p class="muted">Estado actual: ${unlocked ? "resuelto" : "scaffold (ejercicio del alumno)"}</p>
            <p class="muted">Para desbloquear: <code>./lab.sh preprolab unlock ${key}</code></p>
        </div>
    `;
}

// ============================================================
// Render del bloque EDA
// ============================================================

async function renderEDA() {
    const content = document.getElementById("content");
    content.innerHTML = `
        <h1>EDA — Analisis Exploratorio</h1>
        <p class="muted">Bloque eda. Estado: ${(LAB_STATUS.blocks || {}).eda ? "<strong>resuelto</strong>" : "<strong>scaffold</strong> (algunos endpoints devuelven placeholder hasta que implementes el ejercicio)"}</p>

        <section id="eda-overview" class="card">
            <h2>Resumen general</h2>
            <div id="eda-overview-content" class="loading">cargando...</div>
        </section>

        <section class="card">
            <h2>Tabla a explorar</h2>
            <div class="table-selector" id="eda-table-selector"></div>
        </section>

        <section id="eda-schema" class="card">
            <h2>Esquema</h2>
            <div id="eda-schema-content" class="loading">cargando...</div>
        </section>

        <section id="eda-missing" class="card">
            <h2>Missing matrix <span class="badge" id="badge-missing">EDA-2</span></h2>
            <div id="eda-missing-content" class="loading">cargando...</div>
        </section>

        <section id="eda-univariate" class="card">
            <h2>Univariable <span class="badge" id="badge-univariate">EDA-1</span></h2>
            <div class="row">
                <label>Columna:
                    <select id="univariate-column"></select>
                </label>
            </div>
            <div id="eda-univariate-content"></div>
        </section>

        <section id="eda-correlations" class="card">
            <h2>Correlaciones <span class="badge" id="badge-correlations">EDA-3</span></h2>
            <div id="eda-correlations-content" class="loading">cargando...</div>
        </section>
    `;

    renderTableSelector();
    await loadOverview();
    await loadTableViews(CURRENT_TABLE);
}

function renderTableSelector() {
    const sel = document.getElementById("eda-table-selector");
    sel.innerHTML = "";
    TABLES.forEach(t => {
        const btn = document.createElement("button");
        btn.textContent = t;
        btn.className = (t === CURRENT_TABLE) ? "tbtn active" : "tbtn";
        btn.addEventListener("click", () => {
            CURRENT_TABLE = t;
            renderTableSelector();
            loadTableViews(t);
        });
        sel.appendChild(btn);
    });
}

async function loadOverview() {
    const data = await fetchJSON("/api/preprolab/eda/overview");
    const el = document.getElementById("eda-overview-content");
    if (data.error) {
        el.innerHTML = `<p class="error">${data.detail || data.error}</p>`;
        return;
    }
    const t = data.target;
    const totalTarget = Object.values(t.counts).reduce((a, b) => a + b, 0);
    const posPct = (100 * (t.counts["1"] || 0) / totalTarget).toFixed(1);
    let html = "<table class='kv'><thead><tr><th>Tabla</th><th>Filas</th><th>Columnas</th><th>Tipos</th></tr></thead><tbody>";
    Object.entries(data.tables).forEach(([name, info]) => {
        const types = Object.entries(info.types_count).map(([t, c]) => `${t}: ${c}`).join(", ");
        html += `<tr><td><code>${name}</code></td><td>${info.rows.toLocaleString()}</td><td>${info.columns}</td><td>${types}</td></tr>`;
    });
    html += "</tbody></table>";
    html += `<p class="muted" style="margin-top:12px">Variable objetivo: <code>${t.table}.${t.name}</code> — positivos: ${t.counts["1"] || 0} (${posPct}%), negativos: ${t.counts["0"] || 0}</p>`;
    el.innerHTML = html;
}

async function loadTableViews(table) {
    await Promise.all([
        loadSchema(table),
        loadMissing(table),
        loadUnivariate(table),
        loadCorrelations(table),
    ]);
}

async function loadSchema(table) {
    const el = document.getElementById("eda-schema-content");
    el.innerHTML = "<span class='loading'>cargando...</span>";
    const data = await fetchJSON(`/api/preprolab/eda/schema/${table}`);
    if (data.error) {
        el.innerHTML = `<p class="error">${data.detail || data.error}</p>`;
        return;
    }
    const updateUnivariateColumns = () => {
        const sel = document.getElementById("univariate-column");
        sel.innerHTML = "";
        data.columns.forEach(c => {
            const opt = document.createElement("option");
            opt.value = c.name;
            opt.textContent = `${c.name} (${c.type})`;
            sel.appendChild(opt);
        });
        sel.onchange = () => loadUnivariate(table, sel.value);
    };
    let html = `<p class="muted">${data.rows.toLocaleString()} filas, ${data.columns.length} columnas</p>`;
    html += "<table class='kv'><thead><tr><th>Columna</th><th>Tipo</th><th>Únicos</th><th>Nulls</th><th>Muestra</th></tr></thead><tbody>";
    data.columns.forEach(c => {
        const sample = c.sample_values.slice(0, 3).map(v => `<code>${JSON.stringify(v)}</code>`).join(", ");
        html += `<tr><td><strong>${c.name}</strong></td><td>${c.type}</td><td>${c.nunique.toLocaleString()}</td><td>${c.null_count.toLocaleString()}</td><td class='sample'>${sample}</td></tr>`;
    });
    html += "</tbody></table>";
    el.innerHTML = html;
    updateUnivariateColumns();
}

async function loadMissing(table) {
    const el = document.getElementById("eda-missing-content");
    el.innerHTML = "<span class='loading'>cargando...</span>";
    const badge = document.getElementById("badge-missing");
    const data = await fetchJSON(`/api/preprolab/eda/missing/${table}`);
    if (data.error === "scaffold") {
        badge.classList.add("scaffold");
        badge.textContent = "EDA-2 (scaffold)";
        el.innerHTML = `
            <div class="exercise-placeholder">
                <p><strong>Ejercicio ${data.exercise} sin resolver.</strong></p>
                <p class="muted">${data.hint}</p>
                <p class="muted">Implementa <code>missing(tabla)</code> en <code>apps/preprolab/src/web/routes/eda_ex.py</code>.</p>
            </div>
        `;
        return;
    }
    if (data.error) {
        el.innerHTML = `<p class="error">${data.detail || data.error}</p>`;
        return;
    }
    badge.classList.remove("scaffold");
    badge.textContent = "EDA-2 (resuelto)";

    // Bar chart de % null por columna
    const cols = data.per_column.map(c => c.column);
    const nullPcts = data.per_column.map(c => c.null_pct);
    const div = document.createElement("div");
    div.id = "missing-bars";
    div.style.height = "320px";
    el.innerHTML = "";
    el.appendChild(div);
    Plotly.newPlot(div, [{
        x: cols, y: nullPcts, type: "bar",
        marker: { color: nullPcts.map(p => p > 50 ? "#ff6b6b" : p > 10 ? "#ffd166" : "#1da1f2") },
        text: nullPcts.map(p => `${p}%`),
        textposition: "outside",
    }], {
        title: { text: "% de valores null por columna", font: { color: "#e7e9ea" } },
        paper_bgcolor: "#16191c", plot_bgcolor: "#16191c",
        font: { color: "#d7dadc" },
        xaxis: { tickangle: -45 }, yaxis: { title: "% null" },
        margin: { l: 50, r: 20, t: 50, b: 120 },
    }, { displayModeBar: false });

    // Tabla de co-ocurrencia + interpretación
    if (data.co_occurrence && data.co_occurrence.length > 0) {
        let html = "<h3 style='margin-top:20px'>Pares de columnas con nulls simultáneos</h3>";
        html += "<table class='kv'><thead><tr><th>Col A</th><th>Col B</th><th>Ambas null</th><th>%</th></tr></thead><tbody>";
        data.co_occurrence.slice(0, 8).forEach(p => {
            html += `<tr><td><code>${p.col_a}</code></td><td><code>${p.col_b}</code></td><td>${p.both_null_count.toLocaleString()}</td><td>${p.both_null_pct}%</td></tr>`;
        });
        html += "</tbody></table>";
        if (data.interpretation && data.interpretation.hints.length > 0) {
            html += "<div class='hints'><strong>Interpretación heurística:</strong><ul>";
            data.interpretation.hints.forEach(h => { html += `<li>${h}</li>`; });
            html += "</ul></div>";
        }
        const cont = document.createElement("div");
        cont.innerHTML = html;
        el.appendChild(cont);
    }
}

async function loadUnivariate(table, column) {
    const el = document.getElementById("eda-univariate-content");
    const badge = document.getElementById("badge-univariate");

    // Seleccionar primera columna si no se pasó una.
    if (!column) {
        const sel = document.getElementById("univariate-column");
        if (sel && sel.options.length > 0) column = sel.value;
        else return;
    }

    el.innerHTML = "<span class='loading'>cargando...</span>";
    const data = await fetchJSON(`/api/preprolab/eda/univariate/${table}/${column}`);

    if (data.error === "scaffold") {
        badge.classList.add("scaffold");
        badge.textContent = "EDA-1 (scaffold)";
        el.innerHTML = `
            <div class="exercise-placeholder">
                <p><strong>Ejercicio ${data.exercise} sin resolver.</strong></p>
                <p class="muted">${data.hint}</p>
                <p class="muted">Implementa <code>univariate(tabla, columna)</code> en <code>apps/preprolab/src/web/routes/eda_ex.py</code>.</p>
            </div>
        `;
        return;
    }
    if (data.error) {
        el.innerHTML = `<p class="error">${data.detail || data.error}</p>`;
        return;
    }
    badge.classList.remove("scaffold");
    badge.textContent = "EDA-1 (resuelto)";

    el.innerHTML = "";
    const meta = document.createElement("p");
    meta.className = "muted";
    meta.innerHTML = `Tipo: <strong>${data.type}</strong> · Filas: ${data.count.toLocaleString()} · Null: ${data.null_count.toLocaleString()} (${data.null_pct}%)`;
    el.appendChild(meta);

    if (data.type === "numeric" && data.stats && data.histogram) {
        // Stats table
        const stats = data.stats;
        const statsHtml = `
            <table class='kv stats-table'>
                <tr><th>media</th><td>${stats.mean.toFixed(3)}</td><th>mediana</th><td>${stats.median.toFixed(3)}</td></tr>
                <tr><th>std</th><td>${stats.std.toFixed(3)}</td><th>min · max</th><td>${stats.min.toFixed(2)} · ${stats.max.toFixed(2)}</td></tr>
                <tr><th>Q1</th><td>${stats.q1.toFixed(3)}</td><th>Q3</th><td>${stats.q3.toFixed(3)}</td></tr>
            </table>
        `;
        const statsDiv = document.createElement("div");
        statsDiv.innerHTML = statsHtml;
        el.appendChild(statsDiv);

        if (data.outliers_iqr && data.outliers_iqr.count > 0) {
            const o = document.createElement("p");
            o.className = "muted";
            o.innerHTML = `Outliers IQR (1.5×IQR): <strong>${data.outliers_iqr.count.toLocaleString()}</strong> valores fuera de [${data.outliers_iqr.lower_bound.toFixed(2)}, ${data.outliers_iqr.upper_bound.toFixed(2)}]`;
            el.appendChild(o);
        }

        const div = document.createElement("div");
        div.style.height = "320px";
        el.appendChild(div);
        const edges = data.histogram.bin_edges;
        const centers = edges.slice(0, -1).map((e, i) => (e + edges[i + 1]) / 2);
        Plotly.newPlot(div, [{
            x: centers, y: data.histogram.counts, type: "bar",
            marker: { color: "#1d9bf0" },
        }], {
            title: { text: `Histograma de ${column}`, font: { color: "#e7e9ea" } },
            paper_bgcolor: "#16191c", plot_bgcolor: "#16191c",
            font: { color: "#d7dadc" },
            xaxis: { title: column }, yaxis: { title: "Frecuencia" },
            margin: { l: 50, r: 20, t: 50, b: 60 },
        }, { displayModeBar: false });
    } else if (data.type === "categorical" && data.value_counts) {
        const entries = Object.entries(data.value_counts);
        const div = document.createElement("div");
        div.style.height = Math.min(40 + entries.length * 22, 600) + "px";
        el.appendChild(div);
        Plotly.newPlot(div, [{
            y: entries.map(e => e[0]).reverse(),
            x: entries.map(e => e[1]).reverse(),
            type: "bar", orientation: "h",
            marker: { color: "#1d9bf0" },
        }], {
            title: { text: `Distribución de ${column}`, font: { color: "#e7e9ea" } },
            paper_bgcolor: "#16191c", plot_bgcolor: "#16191c",
            font: { color: "#d7dadc" },
            xaxis: { title: "Frecuencia" },
            margin: { l: 200, r: 20, t: 50, b: 50 },
        }, { displayModeBar: false });
    } else {
        el.innerHTML += `<p class="muted">Tipo <code>${data.type}</code> no visualizado.</p>`;
    }
}

async function loadCorrelations(table) {
    const el = document.getElementById("eda-correlations-content");
    el.innerHTML = "<span class='loading'>cargando...</span>";
    const badge = document.getElementById("badge-correlations");
    const data = await fetchJSON(`/api/preprolab/eda/correlations/${table}`);

    if (data.error === "scaffold") {
        badge.classList.add("scaffold");
        badge.textContent = "EDA-3 (scaffold)";
        el.innerHTML = `
            <div class="exercise-placeholder">
                <p><strong>Ejercicio ${data.exercise} sin resolver.</strong></p>
                <p class="muted">${data.hint}</p>
                <p class="muted">Implementa <code>correlations(tabla)</code> en <code>apps/preprolab/src/web/routes/eda_ex.py</code>.</p>
            </div>
        `;
        return;
    }
    if (data.error) {
        el.innerHTML = `<p class="muted">${data.error}</p>`;
        return;
    }
    badge.classList.remove("scaffold");
    badge.textContent = "EDA-3 (resuelto)";

    el.innerHTML = "";
    const div = document.createElement("div");
    div.style.height = "480px";
    el.appendChild(div);
    Plotly.newPlot(div, [{
        z: data.matrix, x: data.columns, y: data.columns,
        type: "heatmap", colorscale: "RdBu", zmin: -1, zmax: 1,
        hovertemplate: "%{x} vs %{y}: %{z:.3f}<extra></extra>",
    }], {
        title: { text: `Correlaciones Pearson — ${table}`, font: { color: "#e7e9ea" } },
        paper_bgcolor: "#16191c", plot_bgcolor: "#16191c",
        font: { color: "#d7dadc" },
        xaxis: { tickangle: -45 },
        margin: { l: 150, r: 20, t: 50, b: 130 },
    }, { displayModeBar: false });

    if (data.redundant_pairs && data.redundant_pairs.length > 0) {
        const cont = document.createElement("div");
        let html = "<h3 style='margin-top:16px'>Pares redundantes (|r| > 0.9)</h3>";
        html += "<table class='kv'><thead><tr><th>Col A</th><th>Col B</th><th>r</th></tr></thead><tbody>";
        data.redundant_pairs.forEach(p => {
            html += `<tr><td><code>${p.col_a}</code></td><td><code>${p.col_b}</code></td><td>${p.corr}</td></tr>`;
        });
        html += "</tbody></table>";
        cont.innerHTML = html;
        el.appendChild(cont);
    }
}

// ============================================================
// Render del bloque MISSING (Fase 4)
// ============================================================

let MISSING_TABLE = "robots";
let MISSING_COLUMN = null;

async function renderMissing() {
    const content = document.getElementById("content");
    content.innerHTML = `
        <h1>Valores perdidos — imputación</h1>
        <p class="muted">Bloque missing. Aplica las 4 técnicas del Tema 5: drop, simple (mean/median/mode), KNN, K-Means. El endpoint <strong>compare</strong> ejecuta todos sobre la misma columna y enseña visualmente cómo cada uno distorsiona la distribución.</p>

        <section class="card">
            <h2>Tabla y columna a imputar</h2>
            <div class="table-selector" id="missing-table-selector"></div>
            <div class="row" style="margin-top:14px">
                <label>Columna con nulls:
                    <select id="missing-column"></select>
                </label>
                <span id="missing-column-info" class="muted"></span>
            </div>
        </section>

        <section class="card">
            <h2>MISSING-1 · Drop <span class="badge" id="badge-drop">DROP</span></h2>
            <div class="row">
                <label>Modo:
                    <select id="drop-mode">
                        <option value="any">any (cualquier null)</option>
                        <option value="all">all (todas null)</option>
                        <option value="thresh">thresh (mín. N no-null)</option>
                    </select>
                </label>
                <label>Thresh: <input type="number" id="drop-thresh" value="1" min="1" max="20" style="width:60px"></label>
                <button class="tbtn" onclick="runDrop()">Ejecutar</button>
            </div>
            <div id="missing-drop-content"></div>
        </section>

        <section class="card">
            <h2>MISSING-2 · Imputación simple <span class="badge" id="badge-simple">SIMPLE</span></h2>
            <div class="row">
                <label>Estrategia:
                    <select id="impute-simple-strategy">
                        <option value="mean">mean</option>
                        <option value="median">median</option>
                        <option value="mode">mode</option>
                    </select>
                </label>
                <button class="tbtn" onclick="runImputeSimple()">Imputar</button>
            </div>
            <div id="missing-simple-content"></div>
        </section>

        <section class="card">
            <h2>MISSING-3 · KNN Imputation <span class="badge" id="badge-knn">KNN</span></h2>
            <div class="row">
                <label>K (vecinos): <input type="number" id="knn-k" value="5" min="1" max="20" style="width:60px"></label>
                <button class="tbtn" onclick="runImputeKnn()">Imputar</button>
                <span class="muted">Necesita features numéricas adicionales para calcular distancia.</span>
            </div>
            <div id="missing-knn-content"></div>
        </section>

        <section class="card">
            <h2>MISSING-4 · K-Means Imputation <span class="badge" id="badge-kmeans">KMEANS</span></h2>
            <div class="row">
                <label>K (clusters): <input type="number" id="kmeans-k" value="5" min="2" max="20" style="width:60px"></label>
                <button class="tbtn" onclick="runImputeKmeans()">Imputar</button>
                <span class="muted">Recomendado por el Tema 5 para Big Data.</span>
            </div>
            <div id="missing-kmeans-content"></div>
        </section>

        <section class="card">
            <h2>MISSING-5 · Comparativa <span class="badge" id="badge-compare">COMPARE</span></h2>
            <div class="row">
                <button class="tbtn" onclick="runCompare()">Comparar todos los métodos</button>
                <span class="muted">Lanza drop + mean + median + KNN + KMeans sobre la misma columna y los pinta superpuestos.</span>
            </div>
            <div id="missing-compare-content"></div>
        </section>
    `;

    renderMissingTableSelector();
    await loadColumnsWithNulls(MISSING_TABLE);
}

function renderMissingTableSelector() {
    const sel = document.getElementById("missing-table-selector");
    sel.innerHTML = "";
    TABLES.forEach(t => {
        const btn = document.createElement("button");
        btn.textContent = t;
        btn.className = (t === MISSING_TABLE) ? "tbtn active" : "tbtn";
        btn.addEventListener("click", () => {
            MISSING_TABLE = t;
            renderMissingTableSelector();
            loadColumnsWithNulls(t);
        });
        sel.appendChild(btn);
    });
}

async function loadColumnsWithNulls(table) {
    const data = await fetchJSON(`/api/preprolab/missing/columns_with_nulls/${table}`);
    const sel = document.getElementById("missing-column");
    const info = document.getElementById("missing-column-info");
    sel.innerHTML = "";
    if (data.error || !data.columns || data.columns.length === 0) {
        const opt = document.createElement("option");
        opt.textContent = "(no hay columnas con nulls en esta tabla)";
        opt.disabled = true;
        sel.appendChild(opt);
        info.textContent = "";
        MISSING_COLUMN = null;
        return;
    }
    data.columns.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.column;
        opt.textContent = `${c.column} (${c.null_pct}% null, ${c.is_numeric ? 'numérica' : 'categórica'})`;
        opt.dataset.numeric = c.is_numeric;
        sel.appendChild(opt);
    });
    sel.onchange = () => {
        MISSING_COLUMN = sel.value;
        info.textContent = `${data.columns.find(c => c.column === sel.value).null_count.toLocaleString()} nulls de ${data.rows.toLocaleString()} filas`;
    };
    MISSING_COLUMN = data.columns[0].column;
    sel.value = MISSING_COLUMN;
    info.textContent = `${data.columns[0].null_count.toLocaleString()} nulls de ${data.rows.toLocaleString()} filas`;
}

function _handleScaffold(data, badge, exercise, file) {
    const el = document.getElementById(`missing-${badge}-content`);
    const badgeEl = document.getElementById(`badge-${badge}`);
    badgeEl.classList.add("scaffold");
    badgeEl.textContent = `${exercise} (scaffold)`;
    el.innerHTML = `
        <div class="exercise-placeholder">
            <p><strong>Ejercicio ${data.exercise} sin resolver.</strong></p>
            <p class="muted">${data.hint}</p>
            <p class="muted">Implementa el endpoint en <code>apps/preprolab/src/web/routes/missing_ex.py</code>.</p>
        </div>
    `;
}

async function runDrop() {
    const mode = document.getElementById("drop-mode").value;
    const thresh = document.getElementById("drop-thresh").value;
    const url = `/api/preprolab/missing/dropna/${MISSING_TABLE}?mode=${mode}&thresh=${thresh}`;
    const data = await fetchJSON(url);
    if (data.error === "scaffold") return _handleScaffold(data, "drop", "MISSING-1", "missing_ex.py");
    const el = document.getElementById("missing-drop-content");
    const badge = document.getElementById("badge-drop");
    badge.classList.remove("scaffold");
    badge.textContent = "MISSING-1 (resuelto)";
    el.innerHTML = `
        <table class='kv stats-table'>
            <tr><th>Filas antes</th><td>${data.rows_before.toLocaleString()}</td></tr>
            <tr><th>Filas después</th><td>${data.rows_after.toLocaleString()}</td></tr>
            <tr><th>Eliminadas</th><td>${data.rows_dropped.toLocaleString()} (${data.rows_dropped_pct}%)</td></tr>
        </table>
    `;
}

async function runImputeSimple() {
    if (!MISSING_COLUMN) return alert("Selecciona una columna primero.");
    const strat = document.getElementById("impute-simple-strategy").value;
    const url = `/api/preprolab/missing/impute_simple/${MISSING_TABLE}/${MISSING_COLUMN}?strategy=${strat}`;
    const data = await fetchJSON(url);
    if (data.error === "scaffold") return _handleScaffold(data, "simple", "MISSING-2", "missing_ex.py");
    if (data.error) return _showError("missing-simple-content", data);

    const badge = document.getElementById("badge-simple");
    badge.classList.remove("scaffold");
    badge.textContent = "MISSING-2 (resuelto)";
    _renderImputationResult("missing-simple-content", data, {label: strat});
}

async function runImputeKnn() {
    if (!MISSING_COLUMN) return alert("Selecciona una columna primero.");
    const k = document.getElementById("knn-k").value;
    const url = `/api/preprolab/missing/impute_knn/${MISSING_TABLE}/${MISSING_COLUMN}?k=${k}`;
    const data = await fetchJSON(url);
    if (data.error === "scaffold") return _handleScaffold(data, "knn", "MISSING-3", "missing_ex.py");
    if (data.error) return _showError("missing-knn-content", data);

    const badge = document.getElementById("badge-knn");
    badge.classList.remove("scaffold");
    badge.textContent = "MISSING-3 (resuelto)";
    _renderImputationResult("missing-knn-content", data, {label: `KNN k=${data.k}`, extra: data.examples});
}

async function runImputeKmeans() {
    if (!MISSING_COLUMN) return alert("Selecciona una columna primero.");
    const k = document.getElementById("kmeans-k").value;
    const url = `/api/preprolab/missing/impute_kmeans/${MISSING_TABLE}/${MISSING_COLUMN}?k=${k}`;
    const data = await fetchJSON(url);
    if (data.error === "scaffold") return _handleScaffold(data, "kmeans", "MISSING-4", "missing_ex.py");
    if (data.error) return _showError("missing-kmeans-content", data);

    const badge = document.getElementById("badge-kmeans");
    badge.classList.remove("scaffold");
    badge.textContent = "MISSING-4 (resuelto)";
    _renderImputationResult("missing-kmeans-content", data, {
        label: `K-Means k=${data.k}`,
        clusters: data.cluster_distribution,
    });
}

function _showError(targetId, data) {
    const el = document.getElementById(targetId);
    el.innerHTML = `<p class="error">${data.detail || data.error}</p>`;
}

function _renderImputationResult(targetId, data, opts) {
    const el = document.getElementById(targetId);
    el.innerHTML = "";

    // Stats table antes/después
    const sb = data.stats_before;
    const sa = data.stats_after;
    if (sb && sa) {
        const html = `
            <table class='kv'>
                <thead><tr><th></th><th>media</th><th>mediana</th><th>std</th><th>min</th><th>max</th><th>nulls</th></tr></thead>
                <tbody>
                    <tr><th>Antes</th><td>${sb.mean.toFixed(3)}</td><td>${sb.median.toFixed(3)}</td><td>${sb.std.toFixed(3)}</td><td>${sb.min.toFixed(2)}</td><td>${sb.max.toFixed(2)}</td><td>${data.null_count_before}</td></tr>
                    <tr><th>Después (${opts.label})</th><td>${sa.mean.toFixed(3)}</td><td>${sa.median.toFixed(3)}</td><td>${sa.std.toFixed(3)}</td><td>${sa.min.toFixed(2)}</td><td>${sa.max.toFixed(2)}</td><td>${data.null_count_after}</td></tr>
                </tbody>
            </table>
        `;
        const tbl = document.createElement("div");
        tbl.innerHTML = html;
        el.appendChild(tbl);

        // Varianza
        const lossPct = (100 * (1 - sa.std / sb.std)).toFixed(1);
        if (Math.abs(parseFloat(lossPct)) > 0.5) {
            const w = document.createElement("p");
            w.className = "muted";
            w.innerHTML = `Variación de std vs original: <strong>${lossPct > 0 ? '-' : '+'}${Math.abs(lossPct)}%</strong> ${lossPct > 0 ? '(método reduce la dispersión)' : '(método aumenta la dispersión)'}`;
            el.appendChild(w);
        }
    }

    // Histograma superpuesto (antes vs después)
    if (data.histogram_before && data.histogram_after) {
        const div = document.createElement("div");
        div.style.height = "300px";
        el.appendChild(div);
        const eb = data.histogram_before.bin_edges;
        const ea = data.histogram_after.bin_edges;
        const cb = eb.slice(0, -1).map((e, i) => (e + eb[i + 1]) / 2);
        const ca = ea.slice(0, -1).map((e, i) => (e + ea[i + 1]) / 2);
        Plotly.newPlot(div, [
            {x: cb, y: data.histogram_before.counts, type: "bar", name: "Antes", marker: {color: "#71767b"}, opacity: 0.6},
            {x: ca, y: data.histogram_after.counts,  type: "bar", name: `Después (${opts.label})`, marker: {color: "#1d9bf0"}, opacity: 0.8},
        ], {
            title: { text: `Distribución antes vs después — ${MISSING_COLUMN}`, font: { color: "#e7e9ea" } },
            paper_bgcolor: "#16191c", plot_bgcolor: "#16191c",
            font: { color: "#d7dadc" },
            barmode: "overlay",
            xaxis: { title: MISSING_COLUMN }, yaxis: { title: "Frecuencia" },
            margin: { l: 50, r: 20, t: 50, b: 60 },
        }, { displayModeBar: false });
    }

    // Distribución por cluster (solo KMeans)
    if (opts.clusters) {
        let html = "<h3 style='margin-top:16px'>Distribución por cluster</h3>";
        html += "<table class='kv'><thead><tr><th>Cluster</th><th>Tamaño</th><th>Filas imputadas</th><th>Valor centroide</th></tr></thead><tbody>";
        Object.entries(opts.clusters).forEach(([c, info]) => {
            html += `<tr><td>${c}</td><td>${info.size.toLocaleString()}</td><td>${info.imputed_count}</td><td>${info.centroid_value}</td></tr>`;
        });
        html += "</tbody></table>";
        const cont = document.createElement("div");
        cont.innerHTML = html;
        el.appendChild(cont);
    }

    // Ejemplos (KNN, KMeans)
    if (opts.extra && opts.extra.length > 0) {
        let html = "<h3 style='margin-top:16px'>Ejemplos de imputaciones (primeras 5)</h3>";
        html += "<table class='kv'><thead><tr><th>row_id</th><th>valor imputado</th><th>contexto</th></tr></thead><tbody>";
        opts.extra.slice(0, 5).forEach(ex => {
            const ctx = Object.entries(ex.other_features || {}).map(([k, v]) => `${k}=${v}`).join(", ");
            html += `<tr><td>${ex.row_id}</td><td>${ex.imputed_value}</td><td class='sample'>${ctx}</td></tr>`;
        });
        html += "</tbody></table>";
        const cont = document.createElement("div");
        cont.innerHTML = html;
        el.appendChild(cont);
    }
}

async function runCompare() {
    if (!MISSING_COLUMN) return alert("Selecciona una columna primero.");
    const el = document.getElementById("missing-compare-content");
    el.innerHTML = "<span class='loading'>ejecutando los 4 métodos...</span>";
    const url = `/api/preprolab/missing/compare/${MISSING_TABLE}/${MISSING_COLUMN}`;
    const data = await fetchJSON(url);
    if (data.error === "scaffold") return _handleScaffold(data, "compare", "MISSING-5", "missing_ex.py");
    if (data.warning) {
        el.innerHTML = `<p class="muted">${data.warning}</p>`;
        return;
    }
    if (data.error) return _showError("missing-compare-content", data);

    const badge = document.getElementById("badge-compare");
    badge.classList.remove("scaffold");
    badge.textContent = "MISSING-5 (resuelto)";

    // Histogramas superpuestos
    const traces = [];
    const colors = { drop: "#71767b", mean: "#ffd166", median: "#06d6a0", knn: "#1d9bf0", kmeans: "#ef476f" };
    Object.entries(data.methods).forEach(([name, info]) => {
        const e = info.histogram.bin_edges;
        const centers = e.slice(0, -1).map((x, i) => (x + e[i + 1]) / 2);
        traces.push({
            x: centers, y: info.histogram.counts, type: "bar",
            name: `${name} — ${info.note}`,
            marker: { color: colors[name] }, opacity: 0.55,
        });
    });

    el.innerHTML = "";
    const div = document.createElement("div");
    div.style.height = "380px";
    el.appendChild(div);
    Plotly.newPlot(div, traces, {
        title: { text: `Comparativa de imputación — ${MISSING_COLUMN}`, font: { color: "#e7e9ea" } },
        paper_bgcolor: "#16191c", plot_bgcolor: "#16191c",
        font: { color: "#d7dadc" },
        barmode: "overlay",
        xaxis: { title: MISSING_COLUMN }, yaxis: { title: "Frecuencia" },
        legend: { orientation: "h", y: -0.3 },
        margin: { l: 50, r: 20, t: 50, b: 100 },
    }, { displayModeBar: false });

    // Tabla de variance loss
    let html = "<h3 style='margin-top:16px'>Pérdida de varianza vs drop (referencia)</h3>";
    html += "<table class='kv'><thead><tr><th>Método</th><th>std</th><th>variance_loss</th></tr></thead><tbody>";
    const dropStd = data.methods.drop.stats.std;
    Object.entries(data.methods).forEach(([name, info]) => {
        if (name === "drop") {
            html += `<tr><td><strong>drop</strong></td><td>${info.stats.std.toFixed(3)}</td><td>0.0 (ref)</td></tr>`;
        } else {
            const loss = data.variance_loss_vs_drop[name];
            const pct = (loss * 100).toFixed(1);
            const cls = Math.abs(loss) < 0.05 ? "" : (loss > 0 ? "warn" : "info");
            html += `<tr><td><strong>${name}</strong></td><td>${info.stats.std.toFixed(3)}</td><td class='${cls}'>${pct}%</td></tr>`;
        }
    });
    html += "</tbody></table>";
    if (data.interpretation) {
        html += `<p class="muted"><strong>Mejor preserva varianza:</strong> ${data.interpretation.best_preserve_variance} · <strong>Peor:</strong> ${data.interpretation.worst_preserve_variance}</p>`;
    }
    const cont = document.createElement("div");
    cont.innerHTML = html;
    el.appendChild(cont);
}

// ============================================================
// Render del bloque OUTLIERS (Fase 5)
// ============================================================

let OUTLIERS_TABLE = "robots";
let OUTLIERS_COLUMN = null;
let OUTLIERS_NUMERIC_COLS = [];

async function renderOutliers() {
    const content = document.getElementById("content");
    content.innerHTML = `
        <h1>Outliers + class noise</h1>
        <p class="muted">Detección de outliers numéricos (IQR / Z-score) + gestión (remove/cap/log) + class noise filters del Tema 5 (EF/CVCF/IPF).</p>

        <section class="card">
            <h2>Tabla y columna numérica</h2>
            <div class="table-selector" id="outliers-table-selector"></div>
            <div class="row" style="margin-top:14px">
                <label>Columna:
                    <select id="outliers-column"></select>
                </label>
            </div>
        </section>

        <section class="card">
            <h2>OUTLIERS-1 · IQR <span class="badge" id="badge-iqr">IQR</span></h2>
            <div class="row">
                <label>Multiplicador: <input type="number" id="iqr-mult" value="1.5" step="0.5" min="0.5" max="5" style="width:60px"></label>
                <button class="tbtn" onclick="runIQR()">Detectar</button>
                <span class="muted">1.5 = clásico · 3.0 = solo extremos</span>
            </div>
            <div id="outliers-iqr-content"></div>
        </section>

        <section class="card">
            <h2>OUTLIERS-2 · Z-score <span class="badge" id="badge-zscore">ZSCORE</span></h2>
            <div class="row">
                <label>Threshold: <input type="number" id="z-thresh" value="3.0" step="0.5" min="1" max="5" style="width:60px"></label>
                <button class="tbtn" onclick="runZscore()">Detectar</button>
                <span class="muted">|z| > threshold = outlier</span>
            </div>
            <div id="outliers-zscore-content"></div>
        </section>

        <section class="card">
            <h2>OUTLIERS-3 · Gestión <span class="badge" id="badge-handle">HANDLE</span></h2>
            <div class="row">
                <label>Estrategia:
                    <select id="handle-strategy">
                        <option value="cap">cap (winsorize)</option>
                        <option value="remove">remove</option>
                        <option value="log">log (log1p)</option>
                    </select>
                </label>
                <label>Detección:
                    <select id="handle-method">
                        <option value="iqr">IQR</option>
                        <option value="zscore">Z-score</option>
                    </select>
                </label>
                <button class="tbtn" onclick="runHandle()">Aplicar</button>
            </div>
            <div id="outliers-handle-content"></div>
        </section>

        <section class="card">
            <h2>OUTLIERS-4 · Class noise filter <span class="badge" id="badge-noise">NOISE</span></h2>
            <p class="muted">Detecta etiquetas <code>failure_next_48h</code> sospechosamente incorrectas usando ensemble de clasificadores.</p>
            <div class="row">
                <label>Método:
                    <select id="noise-method">
                        <option value="ef">EF (conservador, 3 clasificadores)</option>
                        <option value="cvcf">CVCF (moderado, k DT mayoría)</option>
                        <option value="ipf">IPF (agresivo, iterativo)</option>
                    </select>
                </label>
                <label>k: <input type="number" id="noise-k" value="5" min="3" max="10" style="width:60px"></label>
                <label>Inyectar ruido %: <input type="number" id="noise-inject" value="0" step="1" min="0" max="30" style="width:60px"></label>
                <button class="tbtn" onclick="runNoiseFilter()">Ejecutar</button>
            </div>
            <p class="muted" style="font-size:12px">Si <code>inject &gt; 0</code>, flippea N% de etiquetas antes del filter para que veas precision/recall del detector.</p>
            <div id="outliers-noise-content"></div>
        </section>
    `;

    renderOutliersTableSelector();
    await loadNumericColumns(OUTLIERS_TABLE);
}

function renderOutliersTableSelector() {
    const sel = document.getElementById("outliers-table-selector");
    sel.innerHTML = "";
    TABLES.forEach(t => {
        const btn = document.createElement("button");
        btn.textContent = t;
        btn.className = (t === OUTLIERS_TABLE) ? "tbtn active" : "tbtn";
        btn.addEventListener("click", () => {
            OUTLIERS_TABLE = t;
            renderOutliersTableSelector();
            loadNumericColumns(t);
        });
        sel.appendChild(btn);
    });
}

async function loadNumericColumns(table) {
    const data = await fetchJSON(`/api/preprolab/eda/schema/${table}`);
    const sel = document.getElementById("outliers-column");
    sel.innerHTML = "";
    if (data.error || !data.columns) {
        sel.innerHTML = "<option disabled>(error cargando)</option>";
        return;
    }
    const numericCols = data.columns.filter(c => c.type === "numeric");
    OUTLIERS_NUMERIC_COLS = numericCols.map(c => c.name);
    numericCols.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.name;
        opt.textContent = `${c.name} (${c.dtype})`;
        sel.appendChild(opt);
    });
    sel.onchange = () => { OUTLIERS_COLUMN = sel.value; };
    if (numericCols.length > 0) {
        OUTLIERS_COLUMN = numericCols[0].name;
        sel.value = OUTLIERS_COLUMN;
    }
}

function _handleOutliersScaffold(targetId, badgeId, data, exercise) {
    const el = document.getElementById(targetId);
    const badge = document.getElementById(badgeId);
    badge.classList.add("scaffold");
    badge.textContent = `${exercise} (scaffold)`;
    el.innerHTML = `
        <div class="exercise-placeholder">
            <p><strong>Ejercicio ${data.exercise} sin resolver.</strong></p>
            <p class="muted">${data.hint}</p>
            <p class="muted">Implementa en <code>apps/preprolab/src/web/routes/outliers_ex.py</code>.</p>
        </div>
    `;
}

async function runIQR() {
    if (!OUTLIERS_COLUMN) return;
    const mult = document.getElementById("iqr-mult").value;
    const data = await fetchJSON(`/api/preprolab/outliers/detect_iqr/${OUTLIERS_TABLE}/${OUTLIERS_COLUMN}?multiplier=${mult}`);
    if (data.error === "scaffold") return _handleOutliersScaffold("outliers-iqr-content", "badge-iqr", data, "OUTLIERS-1");
    if (data.error) return _showError("outliers-iqr-content", data);

    const badge = document.getElementById("badge-iqr");
    badge.classList.remove("scaffold");
    badge.textContent = "OUTLIERS-1 (resuelto)";

    const el = document.getElementById("outliers-iqr-content");
    let html = `
        <table class='kv stats-table'>
            <tr><th>bounds</th><td>[${data.bounds.lower.toFixed(3)}, ${data.bounds.upper.toFixed(3)}]</td></tr>
            <tr><th>Q1 / Q3 / IQR</th><td>${data.stats.q1.toFixed(3)} / ${data.stats.q3.toFixed(3)} / ${data.stats.iqr.toFixed(3)}</td></tr>
            <tr><th>outliers</th><td><strong>${data.outlier_count.toLocaleString()}</strong> (${data.outlier_pct}%)</td></tr>
        </table>
    `;
    if (data.outlier_samples.length > 0) {
        html += "<h3 style='margin-top:14px'>Muestras (primeras 10)</h3>";
        html += "<table class='kv'><thead><tr><th>row_id</th><th>valor</th></tr></thead><tbody>";
        data.outlier_samples.forEach(s => {
            html += `<tr><td>${s.row_id}</td><td>${s.value}</td></tr>`;
        });
        html += "</tbody></table>";
    }
    el.innerHTML = html;

    // Boxplot visual
    if (data.boxplot_data) {
        const div = document.createElement("div");
        div.style.height = "200px";
        el.appendChild(div);
        const b = data.boxplot_data;
        Plotly.newPlot(div, [{
            type: "box",
            x: [b.q1, b.median, b.q3],
            q1: [b.q1], median: [b.median], q3: [b.q3],
            lowerfence: [b.lower_whisker], upperfence: [b.upper_whisker],
            mean: [b.median],
            orientation: "h",
            name: OUTLIERS_COLUMN,
            marker: { color: "#1d9bf0" },
        }], {
            paper_bgcolor: "#16191c", plot_bgcolor: "#16191c",
            font: { color: "#d7dadc" },
            xaxis: { title: OUTLIERS_COLUMN },
            margin: { l: 80, r: 20, t: 20, b: 50 },
        }, { displayModeBar: false });
    }
}

async function runZscore() {
    if (!OUTLIERS_COLUMN) return;
    const t = document.getElementById("z-thresh").value;
    const data = await fetchJSON(`/api/preprolab/outliers/detect_zscore/${OUTLIERS_TABLE}/${OUTLIERS_COLUMN}?threshold=${t}`);
    if (data.error === "scaffold") return _handleOutliersScaffold("outliers-zscore-content", "badge-zscore", data, "OUTLIERS-2");
    if (data.error) return _showError("outliers-zscore-content", data);

    const badge = document.getElementById("badge-zscore");
    badge.classList.remove("scaffold");
    badge.textContent = "OUTLIERS-2 (resuelto)";

    const el = document.getElementById("outliers-zscore-content");
    if (data.warning) { el.innerHTML = `<p class="muted">${data.warning}</p>`; return; }
    let html = `
        <table class='kv stats-table'>
            <tr><th>mean / std</th><td>${data.stats.mean.toFixed(3)} / ${data.stats.std.toFixed(3)}</td></tr>
            <tr><th>threshold</th><td>${data.threshold}</td></tr>
            <tr><th>outliers</th><td><strong>${data.outlier_count.toLocaleString()}</strong> (${data.outlier_pct}%)</td></tr>
        </table>
    `;
    if (data.outlier_samples.length > 0) {
        html += "<h3 style='margin-top:14px'>Muestras (con z-score)</h3>";
        html += "<table class='kv'><thead><tr><th>row_id</th><th>valor</th><th>z</th></tr></thead><tbody>";
        data.outlier_samples.forEach(s => {
            html += `<tr><td>${s.row_id}</td><td>${s.value}</td><td>${s.z_score}</td></tr>`;
        });
        html += "</tbody></table>";
    }
    el.innerHTML = html;
}

async function runHandle() {
    if (!OUTLIERS_COLUMN) return;
    const strategy = document.getElementById("handle-strategy").value;
    const method = document.getElementById("handle-method").value;
    const url = `/api/preprolab/outliers/handle/${OUTLIERS_TABLE}/${OUTLIERS_COLUMN}?strategy=${strategy}&method=${method}`;
    const data = await fetchJSON(url);
    if (data.error === "scaffold") return _handleOutliersScaffold("outliers-handle-content", "badge-handle", data, "OUTLIERS-3");
    if (data.error) return _showError("outliers-handle-content", data);

    const badge = document.getElementById("badge-handle");
    badge.classList.remove("scaffold");
    badge.textContent = "OUTLIERS-3 (resuelto)";

    const el = document.getElementById("outliers-handle-content");
    el.innerHTML = "";
    const sb = data.stats_before, sa = data.stats_after;
    const html = `
        <table class='kv'>
            <thead><tr><th></th><th>mean</th><th>std</th><th>min</th><th>max</th><th>filas</th></tr></thead>
            <tbody>
                <tr><th>Antes</th><td>${sb.mean.toFixed(3)}</td><td>${sb.std.toFixed(3)}</td><td>${sb.min.toFixed(2)}</td><td>${sb.max.toFixed(2)}</td><td>${data.rows_before}</td></tr>
                <tr><th>Después (${strategy})</th><td>${sa.mean.toFixed(3)}</td><td>${sa.std.toFixed(3)}</td><td>${sa.min.toFixed(2)}</td><td>${sa.max.toFixed(2)}</td><td>${data.rows_after}</td></tr>
            </tbody>
        </table>
    `;
    const tbl = document.createElement("div");
    tbl.innerHTML = html;
    el.appendChild(tbl);
    const info = document.createElement("p");
    info.className = "muted";
    info.innerHTML = `bounds: [${data.bounds.lower.toFixed(3)}, ${data.bounds.upper.toFixed(3)}] · outliers detectados: ${data.outlier_count_before}`;
    el.appendChild(info);

    // Histograma antes vs después
    if (data.histogram_before && data.histogram_after) {
        const div = document.createElement("div");
        div.style.height = "300px";
        el.appendChild(div);
        const eb = data.histogram_before.bin_edges;
        const ea = data.histogram_after.bin_edges;
        Plotly.newPlot(div, [
            { x: eb.slice(0, -1).map((e, i) => (e + eb[i + 1]) / 2),
              y: data.histogram_before.counts, type: "bar", name: "Antes",
              marker: { color: "#71767b" }, opacity: 0.6 },
            { x: ea.slice(0, -1).map((e, i) => (e + ea[i + 1]) / 2),
              y: data.histogram_after.counts, type: "bar", name: `Después (${strategy})`,
              marker: { color: "#1d9bf0" }, opacity: 0.8 },
        ], {
            paper_bgcolor: "#16191c", plot_bgcolor: "#16191c",
            font: { color: "#d7dadc" },
            barmode: "overlay",
            xaxis: { title: OUTLIERS_COLUMN }, yaxis: { title: "Frecuencia" },
            margin: { l: 50, r: 20, t: 20, b: 60 },
        }, { displayModeBar: false });
    }
}

async function runNoiseFilter() {
    const method = document.getElementById("noise-method").value;
    const k = document.getElementById("noise-k").value;
    const inject = document.getElementById("noise-inject").value;
    const inject_pct = parseFloat(inject) / 100.0;
    const el = document.getElementById("outliers-noise-content");
    el.innerHTML = "<span class='loading'>ejecutando k-fold CV...</span>";

    const url = `/api/preprolab/outliers/noise_filter/${OUTLIERS_TABLE}?method=${method}&k=${k}&inject_noise_pct=${inject_pct}`;
    const data = await fetchJSON(url);
    if (data.error === "scaffold") return _handleOutliersScaffold("outliers-noise-content", "badge-noise", data, "OUTLIERS-4");
    if (data.error) return _showError("outliers-noise-content", data);

    const badge = document.getElementById("badge-noise");
    badge.classList.remove("scaffold");
    badge.textContent = "OUTLIERS-4 (resuelto)";

    el.innerHTML = "";
    let html = `
        <table class='kv stats-table'>
            <tr><th>Método</th><td>${data.method.toUpperCase()}${data.iterations > 1 ? ` (${data.iterations} iteraciones)` : ""}</td></tr>
            <tr><th>n_samples</th><td>${data.n_samples.toLocaleString()} (con ${data.n_features} features numéricas)</td></tr>
            <tr><th>Detectados como ruido</th><td><strong>${data.noisy_count.toLocaleString()}</strong> (${data.noisy_pct}%)</td></tr>
        </table>
    `;

    if (data.per_classifier_failures) {
        html += "<h3 style='margin-top:14px'>Errores por clasificador</h3>";
        html += "<table class='kv'><tbody>";
        Object.entries(data.per_classifier_failures).forEach(([clf, n]) => {
            html += `<tr><th>${clf}</th><td>${n}</td></tr>`;
        });
        html += "</tbody></table>";
    }

    html += "<h3 style='margin-top:14px'>Distribución por clase</h3>";
    html += "<table class='kv'><thead><tr><th>Clase</th><th>Total</th><th>Ruidosas</th><th>%</th></tr></thead><tbody>";
    Object.entries(data.by_class).forEach(([cls, info]) => {
        html += `<tr><td><code>${cls}</code></td><td>${info.total.toLocaleString()}</td><td>${info.noisy.toLocaleString()}</td><td>${info.pct}%</td></tr>`;
    });
    html += "</tbody></table>";

    if (data.validation_metrics) {
        const m = data.validation_metrics;
        html += "<h3 style='margin-top:14px'>Validación contra ground truth</h3>";
        html += "<div class='hints'>";
        html += `<p><strong>Inyectadas</strong>: ${m.injected} · <strong>Detectadas</strong>: ${m.detected}</p>`;
        html += `<p>TP: ${m.true_positives} · FP: ${m.false_positives} · FN: ${m.false_negatives}</p>`;
        html += `<p><strong>Precision</strong>: ${m.precision} · <strong>Recall</strong>: ${m.recall} · <strong>F1</strong>: ${m.f1}</p>`;
        html += "</div>";
    }
    el.innerHTML = html;
}

// ============================================================
// Render del bloque INTEGRATION (Fase 6)
// ============================================================

let INTEG_TABLE_A = "robots";
let INTEG_TABLE_B = "events";

async function renderIntegration() {
    const content = document.getElementById("content");
    content.innerHTML = `
        <h1>Integración de datos</h1>
        <p class="muted">Concatenación vertical (union), 4 tipos de join, y detección de redundancia con Pearson + Cramér's V.</p>

        <section class="card">
            <h2>INTEG-1 · Union <span class="badge" id="badge-union">UNION</span></h2>
            <div class="row">
                <label>Tabla A:
                    <select id="union-table-a">${TABLES.map(t => `<option value="${t}">${t}</option>`).join("")}</select>
                </label>
                <label>Tabla B:
                    <select id="union-table-b">${TABLES.map(t => `<option value="${t}" ${t === "events" ? "selected" : ""}>${t}</option>`).join("")}</select>
                </label>
                <label><input type="checkbox" id="union-strict" checked> mismo schema únicamente</label>
                <button class="tbtn" onclick="runUnion()">Probar</button>
            </div>
            <div id="integ-union-content"></div>
        </section>

        <section class="card">
            <h2>INTEG-2 · Join <span class="badge" id="badge-join">JOIN</span></h2>
            <div class="row">
                <label>Tabla A:
                    <select id="join-table-a">${TABLES.map(t => `<option value="${t}" ${t === "robots" ? "selected" : ""}>${t}</option>`).join("")}</select>
                </label>
                <label>Tabla B:
                    <select id="join-table-b">${TABLES.map(t => `<option value="${t}" ${t === "events" ? "selected" : ""}>${t}</option>`).join("")}</select>
                </label>
                <label>Columna clave: <input type="text" id="join-on" value="id" style="width:120px"></label>
                <label>Tipo:
                    <select id="join-how">
                        <option value="inner">inner</option>
                        <option value="left">left</option>
                        <option value="right">right</option>
                        <option value="outer">outer</option>
                    </select>
                </label>
                <button class="tbtn" onclick="runJoin()">Ejecutar</button>
            </div>
            <p class="muted" style="font-size:12px">Ojo: en robots la PK es <code>id</code>; en las otras 3 es <code>robot_id</code>. Para hacer join robots↔events usa la columna apropiada en cada lado (necesitamos misma columna en ambos — renombra si hace falta o usa la API completa con left_on/right_on).</p>
            <div id="integ-join-content"></div>
        </section>

        <section class="card">
            <h2>INTEG-3 · Redundancia (Pearson + Cramér's V) <span class="badge" id="badge-redun">REDUN</span></h2>
            <div class="row">
                <label>Tabla:
                    <select id="redun-table">${TABLES.map(t => `<option value="${t}" ${t === "robots" ? "selected" : ""}>${t}</option>`).join("")}</select>
                </label>
                <label>Threshold: <input type="number" id="redun-threshold" value="0.9" step="0.05" min="0.5" max="1" style="width:60px"></label>
                <button class="tbtn" onclick="runRedundancy()">Analizar</button>
            </div>
            <div id="integ-redun-content"></div>
        </section>

        <section class="card">
            <h2>INTEG-4 · Dedup por correlación <span class="badge" id="badge-dedup">DEDUP</span></h2>
            <div class="row">
                <label>Tabla:
                    <select id="dedup-table">${TABLES.map(t => `<option value="${t}" ${t === "robots" ? "selected" : ""}>${t}</option>`).join("")}</select>
                </label>
                <label>Threshold: <input type="number" id="dedup-threshold" value="0.9" step="0.05" min="0.5" max="1" style="width:60px"></label>
                <button class="tbtn" onclick="runDedup()">Simular</button>
            </div>
            <div id="integ-dedup-content"></div>
        </section>
    `;
}

function _handleIntegScaffold(targetId, badgeId, data, exercise) {
    const el = document.getElementById(targetId);
    const badge = document.getElementById(badgeId);
    badge.classList.add("scaffold");
    badge.textContent = `${exercise} (scaffold)`;
    el.innerHTML = `
        <div class="exercise-placeholder">
            <p><strong>Ejercicio ${data.exercise} sin resolver.</strong></p>
            <p class="muted">${data.hint}</p>
            <p class="muted">Implementa en <code>apps/preprolab/src/web/routes/integration_ex.py</code>.</p>
        </div>
    `;
}

async function runUnion() {
    const a = document.getElementById("union-table-a").value;
    const b = document.getElementById("union-table-b").value;
    const strict = document.getElementById("union-strict").checked;
    const data = await fetchJSON(`/api/preprolab/integration/union/${a}/${b}?same_schema_only=${strict}`);
    if (data.error === "scaffold") return _handleIntegScaffold("integ-union-content", "badge-union", data, "INTEG-1");
    if (data.error) return _showError("integ-union-content", data);

    const badge = document.getElementById("badge-union");
    badge.classList.remove("scaffold");
    badge.textContent = "INTEG-1 (resuelto)";

    const el = document.getElementById("integ-union-content");
    let html = `
        <table class='kv stats-table'>
            <tr><th>Schemas coinciden</th><td>${data.schemas_match ? "Sí" : "No"}</td></tr>
            <tr><th>Filas A / B</th><td>${data.rows_a} / ${data.rows_b}</td></tr>
            <tr><th>Modo</th><td><strong>${data.mode}</strong></td></tr>
    `;
    if ("unioned_rows" in data) {
        html += `<tr><th>Filas resultantes</th><td><strong>${data.unioned_rows}</strong></td></tr>`;
    }
    html += "</table>";
    if (data.warning) html += `<p class="muted">${data.warning}</p>`;
    if (data.error_msg) html += `<p class="error">${data.error_msg}</p>`;
    html += `<p class="muted">Comunes (${data.common_columns.length}): <code>${data.common_columns.join(", ") || "(ninguna)"}</code></p>`;
    if (data.only_in_a.length) html += `<p class="muted">Solo en A: <code>${data.only_in_a.join(", ")}</code></p>`;
    if (data.only_in_b.length) html += `<p class="muted">Solo en B: <code>${data.only_in_b.join(", ")}</code></p>`;
    el.innerHTML = html;
}

async function runJoin() {
    const a = document.getElementById("join-table-a").value;
    const b = document.getElementById("join-table-b").value;
    const on = document.getElementById("join-on").value;
    const how = document.getElementById("join-how").value;
    const data = await fetchJSON(`/api/preprolab/integration/join/${a}/${b}?on=${on}&how=${how}`);
    if (data.error === "scaffold") return _handleIntegScaffold("integ-join-content", "badge-join", data, "INTEG-2");
    if (data.error) return _showError("integ-join-content", data);

    const badge = document.getElementById("badge-join");
    badge.classList.remove("scaffold");
    badge.textContent = "INTEG-2 (resuelto)";

    const el = document.getElementById("integ-join-content");
    let html = `
        <table class='kv stats-table'>
            <tr><th>Modo / Clave</th><td><strong>${data.how.toUpperCase()}</strong> sobre <code>${data.on}</code></td></tr>
            <tr><th>Filas A → B → resultantes</th><td>${data.rows_a} → ${data.rows_b} → <strong>${data.rows_joined.toLocaleString()}</strong></td></tr>
            <tr><th>Keys (A / B / comunes)</th><td>${data.keys_in_a} / ${data.keys_in_b} / ${data.keys_in_common}</td></tr>
            <tr><th>Keys solo A / solo B</th><td>${data.keys_only_in_a} / ${data.keys_only_in_b}</td></tr>
        </table>
        <p class="muted" style="margin-top:10px">Columnas resultantes (${data.columns_after_join.length}): <code>${data.columns_after_join.join(", ")}</code></p>
    `;
    if (data.sample && data.sample.length > 0) {
        html += "<h3 style='margin-top:14px'>Muestra (5 primeras filas)</h3>";
        const cols = Object.keys(data.sample[0]);
        html += "<table class='kv'><thead><tr>" + cols.map(c => `<th>${c}</th>`).join("") + "</tr></thead><tbody>";
        data.sample.forEach(row => {
            html += "<tr>" + cols.map(c => `<td class='sample'>${row[c] === null ? "<em>null</em>" : JSON.stringify(row[c])}</td>`).join("") + "</tr>";
        });
        html += "</tbody></table>";
    }
    el.innerHTML = html;
}

async function runRedundancy() {
    const table = document.getElementById("redun-table").value;
    const th = document.getElementById("redun-threshold").value;
    const data = await fetchJSON(`/api/preprolab/integration/find_redundancy/${table}?threshold=${th}`);
    if (data.error === "scaffold") return _handleIntegScaffold("integ-redun-content", "badge-redun", data, "INTEG-3");
    if (data.error) return _showError("integ-redun-content", data);

    const badge = document.getElementById("badge-redun");
    badge.classList.remove("scaffold");
    badge.textContent = "INTEG-3 (resuelto)";

    const el = document.getElementById("integ-redun-content");
    let html = `
        <p class="muted">${data.numeric_columns_analyzed.length} columnas numéricas, ${data.categorical_columns_analyzed.length} categóricas analizadas. Threshold = ${data.threshold}.</p>
    `;
    if (data.redundant_numeric_pairs.length > 0) {
        html += "<h3 style='margin-top:14px'>Pares numéricos redundantes (Pearson)</h3>";
        html += "<table class='kv'><thead><tr><th>Col A</th><th>Col B</th><th>r</th></tr></thead><tbody>";
        data.redundant_numeric_pairs.forEach(p => {
            html += `<tr><td><code>${p.col_a}</code></td><td><code>${p.col_b}</code></td><td><strong>${p.corr}</strong></td></tr>`;
        });
        html += "</tbody></table>";
    } else {
        html += "<p class='muted'>No hay pares numéricos por encima del threshold.</p>";
    }
    if (data.redundant_categorical_pairs.length > 0) {
        html += "<h3 style='margin-top:14px'>Pares categóricos redundantes (Cramér's V)</h3>";
        html += "<table class='kv'><thead><tr><th>Col A</th><th>Col B</th><th>V</th></tr></thead><tbody>";
        data.redundant_categorical_pairs.forEach(p => {
            html += `<tr><td><code>${p.col_a}</code></td><td><code>${p.col_b}</code></td><td><strong>${p.cramers_v}</strong></td></tr>`;
        });
        html += "</tbody></table>";
    }
    if (data.drop_candidates.length > 0) {
        html += "<h3 style='margin-top:14px'>Sugerencias de eliminación</h3>";
        html += "<table class='kv'><thead><tr><th>Eliminar</th><th>Mantener</th><th>Razón</th></tr></thead><tbody>";
        data.drop_candidates.forEach(s => {
            html += `<tr><td><code>${s.drop}</code></td><td><code>${s.keep}</code></td><td class='sample'>${s.reason}</td></tr>`;
        });
        html += "</tbody></table>";
    }
    el.innerHTML = html;
}

async function runDedup() {
    const table = document.getElementById("dedup-table").value;
    const th = document.getElementById("dedup-threshold").value;
    const data = await fetchJSON(`/api/preprolab/integration/dedup_by_correlation/${table}?threshold=${th}`);
    if (data.error === "scaffold") return _handleIntegScaffold("integ-dedup-content", "badge-dedup", data, "INTEG-4");
    if (data.error) return _showError("integ-dedup-content", data);

    const badge = document.getElementById("badge-dedup");
    badge.classList.remove("scaffold");
    badge.textContent = "INTEG-4 (resuelto)";

    const el = document.getElementById("integ-dedup-content");
    let html = `
        <table class='kv stats-table'>
            <tr><th>Columnas antes</th><td>${data.columns_before}</td></tr>
            <tr><th>Columnas después</th><td>${data.columns_after}</td></tr>
            <tr><th>Eliminadas</th><td><strong>${data.columns_dropped.length}</strong> (${data.reduction_pct}%)</td></tr>
        </table>
        <p class="muted" style="margin-top:10px">A eliminar: <code>${data.columns_dropped.join(", ") || "(ninguna)"}</code></p>
        <p class="muted">Conservadas: <code>${data.columns_kept.join(", ")}</code></p>
    `;
    el.innerHTML = html;
}

// ============================================================
// Render del bloque TRANSFORM (Fase 7)
// ============================================================

let TRANS_TABLE = "robots";

async function renderTransform() {
    const content = document.getElementById("content");
    content.innerHTML = `
        <h1>Transformación de variables</h1>
        <p class="muted">Conversiones (one-hot, ordinal, multivaluada) + discretización (equal-width, equal-freq, MDLP) + agregación con groupby.</p>

        <section class="card">
            <h2>Tabla activa</h2>
            <div class="table-selector" id="trans-table-selector"></div>
        </section>

        <section class="card">
            <h2>TRANS-1 · One-hot <span class="badge" id="badge-onehot">ONEHOT</span></h2>
            <div class="row">
                <label>Columna nominal: <input type="text" id="onehot-col" value="fabricante" style="width:160px"></label>
                <label>Max categorías: <input type="number" id="onehot-max" value="20" min="2" max="100" style="width:60px"></label>
                <button class="tbtn" onclick="runOnehot()">Codificar</button>
            </div>
            <div id="trans-onehot-content"></div>
        </section>

        <section class="card">
            <h2>TRANS-2 · Ordinal <span class="badge" id="badge-ordinal">ORDINAL</span></h2>
            <div class="row">
                <label>Columna: <input type="text" id="ord-col" value="severidad" style="width:160px"></label>
                <label>Orden CSV: <input type="text" id="ord-order" value="INFO,WARN,ERROR,CRITICAL" style="width:280px"></label>
                <button class="tbtn" onclick="runOrdinal()">Codificar</button>
            </div>
            <p class="muted" style="font-size:12px">Ej. para events.severidad: <code>INFO,WARN,ERROR,CRITICAL</code>. Probar tabla=events.</p>
            <div id="trans-ordinal-content"></div>
        </section>

        <section class="card">
            <h2>TRANS-3 · Multivaluada <span class="badge" id="badge-multi">MULTI</span></h2>
            <div class="row">
                <label>Columna CSV: <input type="text" id="multi-col" value="sensores_activos" style="width:200px"></label>
                <label>Separador: <input type="text" id="multi-sep" value="," style="width:50px"></label>
                <button class="tbtn" onclick="runMultivalued()">Descomponer</button>
            </div>
            <p class="muted" style="font-size:12px">Ideal para robots.sensores_activos (lista de sensores por robot).</p>
            <div id="trans-multi-content"></div>
        </section>

        <section class="card">
            <h2>TRANS-4 · Discretización <span class="badge" id="badge-disc">DISC</span></h2>
            <div class="row">
                <label>Columna numérica: <input type="text" id="disc-col" value="bateria_pct" style="width:160px"></label>
                <label>Método:
                    <select id="disc-method">
                        <option value="equal_width">equal_width</option>
                        <option value="equal_freq">equal_freq</option>
                        <option value="mdlp">mdlp (supervisado)</option>
                    </select>
                </label>
                <label>Bins: <input type="number" id="disc-bins" value="5" min="2" max="20" style="width:60px"></label>
                <button class="tbtn" onclick="runDiscretize()">Discretizar</button>
            </div>
            <div id="trans-disc-content"></div>
        </section>

        <section class="card">
            <h2>TRANS-5 · GroupBy <span class="badge" id="badge-grp">GROUP</span></h2>
            <div class="row">
                <label>By: <input type="text" id="grp-by" value="fabricante" style="width:140px"></label>
                <label>Agregar columna: <input type="text" id="grp-agg-col" value="bateria_pct" style="width:140px"></label>
                <label>Función:
                    <select id="grp-agg">
                        <option value="mean">mean</option>
                        <option value="median">median</option>
                        <option value="sum">sum</option>
                        <option value="count">count</option>
                        <option value="min">min</option>
                        <option value="max">max</option>
                        <option value="std">std</option>
                    </select>
                </label>
                <button class="tbtn" onclick="runGroupby()">Agrupar</button>
            </div>
            <div id="trans-grp-content"></div>
        </section>
    `;

    renderTransTableSelector();
}

function renderTransTableSelector() {
    const sel = document.getElementById("trans-table-selector");
    sel.innerHTML = "";
    TABLES.forEach(t => {
        const btn = document.createElement("button");
        btn.textContent = t;
        btn.className = (t === TRANS_TABLE) ? "tbtn active" : "tbtn";
        btn.addEventListener("click", () => {
            TRANS_TABLE = t;
            renderTransTableSelector();
        });
        sel.appendChild(btn);
    });
}

function _handleTransScaffold(targetId, badgeId, data, exercise) {
    const el = document.getElementById(targetId);
    const badge = document.getElementById(badgeId);
    badge.classList.add("scaffold");
    badge.textContent = `${exercise} (scaffold)`;
    el.innerHTML = `
        <div class="exercise-placeholder">
            <p><strong>Ejercicio ${data.exercise} sin resolver.</strong></p>
            <p class="muted">${data.hint}</p>
            <p class="muted">Implementa en <code>apps/preprolab/src/web/routes/transform_ex.py</code>.</p>
        </div>
    `;
}

async function runOnehot() {
    const col = document.getElementById("onehot-col").value;
    const max = document.getElementById("onehot-max").value;
    const data = await fetchJSON(`/api/preprolab/transform/onehot/${TRANS_TABLE}/${col}?max_categories=${max}`);
    if (data.error === "scaffold") return _handleTransScaffold("trans-onehot-content", "badge-onehot", data, "TRANS-1");
    if (data.error) return _showError("trans-onehot-content", data);

    const badge = document.getElementById("badge-onehot");
    badge.classList.remove("scaffold");
    badge.textContent = "TRANS-1 (resuelto)";

    const el = document.getElementById("trans-onehot-content");
    let html = `
        <table class='kv stats-table'>
            <tr><th>Valores únicos</th><td>${data.n_unique}</td></tr>
            <tr><th>Categorías codificadas</th><td>${data.n_categories_kept}${data.grouped_minor_into_OTROS ? " (incluye OTROS)" : ""}</td></tr>
            <tr><th>Columnas creadas</th><td><code>${data.new_columns.join(", ")}</code></td></tr>
        </table>
    `;
    // Distribución top 10
    const top = Object.entries(data.distribution).slice(0, 10);
    if (top.length > 0) {
        html += "<h3 style='margin-top:14px'>Distribución original (top 10)</h3>";
        html += "<table class='kv'><thead><tr><th>Valor</th><th>Frecuencia</th></tr></thead><tbody>";
        top.forEach(([k, v]) => { html += `<tr><td><code>${k}</code></td><td>${v}</td></tr>`; });
        html += "</tbody></table>";
    }
    el.innerHTML = html;
}

async function runOrdinal() {
    const col = document.getElementById("ord-col").value;
    const order = encodeURIComponent(document.getElementById("ord-order").value);
    const data = await fetchJSON(`/api/preprolab/transform/ordinal/${TRANS_TABLE}/${col}?order=${order}`);
    if (data.error === "scaffold") return _handleTransScaffold("trans-ordinal-content", "badge-ordinal", data, "TRANS-2");
    if (data.error) return _showError("trans-ordinal-content", data);

    const badge = document.getElementById("badge-ordinal");
    badge.classList.remove("scaffold");
    badge.textContent = "TRANS-2 (resuelto)";

    const el = document.getElementById("trans-ordinal-content");
    let html = "";
    if (data.warning) html += `<p class="muted"><em>${data.warning}</em></p>`;
    html += "<h3>Mapeo</h3><table class='kv'><thead><tr><th>Valor original</th><th>Encoded</th><th>Frecuencia</th></tr></thead><tbody>";
    Object.entries(data.mapping).forEach(([k, v]) => {
        const freq = data.value_counts_original[k] || 0;
        html += `<tr><td><code>${k}</code></td><td><strong>${v}</strong></td><td>${freq}</td></tr>`;
    });
    html += "</tbody></table>";
    const s = data.stats_encoded;
    html += `<p class="muted" style="margin-top:10px">Encoded stats: media=${s.mean.toFixed(2)} · mediana=${s.median} · rango [${s.min}, ${s.max}]</p>`;
    el.innerHTML = html;
}

async function runMultivalued() {
    const col = document.getElementById("multi-col").value;
    const sep = encodeURIComponent(document.getElementById("multi-sep").value);
    const data = await fetchJSON(`/api/preprolab/transform/multivalued/${TRANS_TABLE}/${col}?separator=${sep}`);
    if (data.error === "scaffold") return _handleTransScaffold("trans-multi-content", "badge-multi", data, "TRANS-3");
    if (data.error) return _showError("trans-multi-content", data);

    const badge = document.getElementById("badge-multi");
    badge.classList.remove("scaffold");
    badge.textContent = "TRANS-3 (resuelto)";

    const el = document.getElementById("trans-multi-content");
    const c = data.cardinality_stats;
    let html = `
        <table class='kv stats-table'>
            <tr><th>Vocabulario</th><td><strong>${data.n_unique_values}</strong> valores únicos</td></tr>
            <tr><th>Cardinalidad por fila</th><td>media=${c.mean} · mediana=${c.median} · rango [${c.min}, ${c.max}]</td></tr>
        </table>
        <h3 style='margin-top:14px'>Frecuencia de cada flag</h3>
        <table class='kv'><thead><tr><th>Flag</th><th>Filas con flag</th><th>%</th></tr></thead><tbody>
    `;
    Object.entries(data.flag_frequency).forEach(([k, v]) => {
        const pct = data.flag_pct[k];
        html += `<tr><td><code>${k}</code></td><td>${v}</td><td>${pct}%</td></tr>`;
    });
    html += "</tbody></table>";
    el.innerHTML = html;
}

async function runDiscretize() {
    const col = document.getElementById("disc-col").value;
    const method = document.getElementById("disc-method").value;
    const bins = document.getElementById("disc-bins").value;
    const data = await fetchJSON(`/api/preprolab/transform/discretize/${TRANS_TABLE}/${col}?method=${method}&bins=${bins}`);
    if (data.error === "scaffold") return _handleTransScaffold("trans-disc-content", "badge-disc", data, "TRANS-4");
    if (data.error) return _showError("trans-disc-content", data);

    const badge = document.getElementById("badge-disc");
    badge.classList.remove("scaffold");
    badge.textContent = "TRANS-4 (resuelto)";

    const el = document.getElementById("trans-disc-content");
    let html = "";
    if (data.warning) html += `<p class="muted"><em>${data.warning}</em></p>`;
    html += `
        <table class='kv stats-table'>
            <tr><th>Método</th><td><strong>${data.method}</strong></td></tr>
            <tr><th>Bins resultantes</th><td>${data.n_bins_resulting}</td></tr>
            <tr><th>Edges</th><td><code>${data.edges.map(e => e.toFixed(2)).join(", ")}</code></td></tr>
        </table>
    `;
    if (data.distribution && Object.keys(data.distribution).length > 0) {
        html += "<h3 style='margin-top:14px'>Distribución</h3>";
        html += "<table class='kv'><thead><tr><th>Intervalo</th><th>Filas</th></tr></thead><tbody>";
        Object.entries(data.distribution).forEach(([k, v]) => {
            html += `<tr><td><code>${k}</code></td><td>${v}</td></tr>`;
        });
        html += "</tbody></table>";

        // Bar chart de la distribución
        const div = document.createElement("div");
        div.style.height = "260px";
        el.innerHTML = html;
        el.appendChild(div);
        Plotly.newPlot(div, [{
            x: Object.keys(data.distribution), y: Object.values(data.distribution), type: "bar",
            marker: { color: "#1d9bf0" },
        }], {
            title: { text: `Distribución por bin — ${col}`, font: { color: "#e7e9ea" } },
            paper_bgcolor: "#16191c", plot_bgcolor: "#16191c",
            font: { color: "#d7dadc" },
            xaxis: { tickangle: -45 }, yaxis: { title: "Filas" },
            margin: { l: 50, r: 20, t: 50, b: 100 },
        }, { displayModeBar: false });
        return;
    }
    el.innerHTML = html;
}

async function runGroupby() {
    const by = document.getElementById("grp-by").value;
    const aggCol = document.getElementById("grp-agg-col").value;
    const agg = document.getElementById("grp-agg").value;
    const data = await fetchJSON(`/api/preprolab/transform/groupby/${TRANS_TABLE}?by=${by}&agg_col=${aggCol}&agg=${agg}`);
    if (data.error === "scaffold") return _handleTransScaffold("trans-grp-content", "badge-grp", data, "TRANS-5");
    if (data.error) return _showError("trans-grp-content", data);

    const badge = document.getElementById("badge-grp");
    badge.classList.remove("scaffold");
    badge.textContent = "TRANS-5 (resuelto)";

    const el = document.getElementById("trans-grp-content");
    let html = `
        <p class="muted">Agrupado por <code>${data.by}</code>, agregando <code>${data.agg_col}</code> con <strong>${data.agg}</strong>. ${data.n_groups} grupos.</p>
    `;
    html += "<table class='kv'><thead><tr><th>" + data.by + "</th><th>" + data.agg + "(" + data.agg_col + ")</th></tr></thead><tbody>";
    Object.entries(data.result).forEach(([k, v]) => {
        const val = (v === null) ? "<em>null</em>" : (typeof v === "number" ? v.toFixed(3) : v);
        html += `<tr><td><code>${k}</code></td><td>${val}</td></tr>`;
    });
    html += "</tbody></table>";
    el.innerHTML = html;
}

// ============================================================
// Render del bloque NORMALIZE (Fase 8)
// ============================================================

let NORM_TABLE = "robots";
let NORM_COLUMN = "bateria_pct";

async function renderNormalize() {
    const content = document.getElementById("content");
    content.innerHTML = `
        <h1>Normalización / Escalado</h1>
        <p class="muted">Z-score (StandardScaler) · Min-Max ([0,1]) · Robust (mediana+IQR) · Decimal Scaling — y un comparador que muestra la vulnerabilidad Min-Max a outliers.</p>

        <section class="card">
            <h2>Tabla y columna numérica</h2>
            <div class="table-selector" id="norm-table-selector"></div>
            <div class="row" style="margin-top:14px">
                <label>Columna: <input type="text" id="norm-col" value="bateria_pct" style="width:200px"></label>
                <span class="muted">Prueba con <code>sensors_readings.temperatura</code> (tiene 491 valores=1000°C → demuestra el problema Min-Max).</span>
            </div>
        </section>

        <section class="card">
            <h2>NORM-1 · Z-score <span class="badge" id="badge-zscore-norm">ZSCORE</span></h2>
            <div class="row"><button class="tbtn" onclick="runNorm('zscore')">Aplicar (x - μ) / σ</button></div>
            <div id="norm-zscore-content"></div>
        </section>

        <section class="card">
            <h2>NORM-2 · Min-Max <span class="badge" id="badge-minmax">MINMAX</span></h2>
            <div class="row"><button class="tbtn" onclick="runNorm('minmax')">Aplicar (x - min) / (max - min)</button></div>
            <div id="norm-minmax-content"></div>
        </section>

        <section class="card">
            <h2>NORM-3 · Robust <span class="badge" id="badge-robust">ROBUST</span></h2>
            <div class="row"><button class="tbtn" onclick="runNorm('robust')">Aplicar (x - mediana) / IQR</button></div>
            <div id="norm-robust-content"></div>
        </section>

        <section class="card">
            <h2>NORM-4 · Decimal Scaling <span class="badge" id="badge-decimal">DECIMAL</span></h2>
            <div class="row"><button class="tbtn" onclick="runNorm('decimal')">Aplicar x / 10^j</button></div>
            <div id="norm-decimal-content"></div>
        </section>

        <section class="card">
            <h2>NORM-5 · Comparativa <span class="badge" id="badge-compare-norm">COMPARE</span></h2>
            <div class="row">
                <button class="tbtn" onclick="runNormCompare()">Aplicar los 4 y comparar</button>
                <span class="muted">Tabla resumen + interpretación automática.</span>
            </div>
            <div id="norm-compare-content"></div>
        </section>
    `;

    renderNormTableSelector();
    document.getElementById("norm-col").onchange = (e) => { NORM_COLUMN = e.target.value; };
}

function renderNormTableSelector() {
    const sel = document.getElementById("norm-table-selector");
    sel.innerHTML = "";
    TABLES.forEach(t => {
        const btn = document.createElement("button");
        btn.textContent = t;
        btn.className = (t === NORM_TABLE) ? "tbtn active" : "tbtn";
        btn.addEventListener("click", () => { NORM_TABLE = t; renderNormTableSelector(); });
        sel.appendChild(btn);
    });
}

function _handleNormScaffold(targetId, badgeId, data, exercise) {
    const el = document.getElementById(targetId);
    const badge = document.getElementById(badgeId);
    badge.classList.add("scaffold");
    badge.textContent = `${exercise} (scaffold)`;
    el.innerHTML = `
        <div class="exercise-placeholder">
            <p><strong>Ejercicio ${data.exercise} sin resolver.</strong></p>
            <p class="muted">${data.hint}</p>
            <p class="muted">Implementa en <code>apps/preprolab/src/web/routes/normalize_ex.py</code>.</p>
        </div>
    `;
}

async function runNorm(method) {
    NORM_COLUMN = document.getElementById("norm-col").value;
    const data = await fetchJSON(`/api/preprolab/normalize/${method}/${NORM_TABLE}/${NORM_COLUMN}`);
    const exerciseMap = {zscore: "NORM-1", minmax: "NORM-2", robust: "NORM-3", decimal: "NORM-4"};
    const badgeId = method === "zscore" ? "badge-zscore-norm" : `badge-${method}`;
    if (data.error === "scaffold") return _handleNormScaffold(`norm-${method}-content`, badgeId, data, exerciseMap[method]);
    if (data.error) return _showError(`norm-${method}-content`, data);

    const badge = document.getElementById(badgeId);
    badge.classList.remove("scaffold");
    badge.textContent = `${exerciseMap[method]} (resuelto)`;

    const el = document.getElementById(`norm-${method}-content`);
    el.innerHTML = "";
    if (data.warning) { el.innerHTML = `<p class="muted">${data.warning}</p>`; return; }

    const sb = data.stats_before, sa = data.stats_after;
    let html = `
        <table class='kv'>
            <thead><tr><th></th><th>mean</th><th>median</th><th>std</th><th>min</th><th>max</th></tr></thead>
            <tbody>
                <tr><th>Antes</th><td>${sb.mean.toFixed(3)}</td><td>${sb.median.toFixed(3)}</td><td>${sb.std.toFixed(3)}</td><td>${sb.min.toFixed(2)}</td><td>${sb.max.toFixed(2)}</td></tr>
                <tr><th>Después</th><td>${sa.mean.toFixed(3)}</td><td>${sa.median.toFixed(3)}</td><td>${sa.std.toFixed(3)}</td><td>${sa.min.toFixed(3)}</td><td>${sa.max.toFixed(3)}</td></tr>
            </tbody>
        </table>
        <p class="muted" style="margin-top:8px">Parámetros: <code>${JSON.stringify(data.parameters)}</code></p>
    `;
    if (data.compression_diagnostic) {
        html += `<div class="hints">${data.compression_diagnostic.interpretation}</div>`;
    }
    if (data.outlier_sensitivity_note) {
        html += `<p class="muted" style="font-size:12px"><em>${data.outlier_sensitivity_note}</em></p>`;
    }
    el.innerHTML = html;

    if (data.histogram_after) {
        const div = document.createElement("div");
        div.style.height = "260px";
        el.appendChild(div);
        const ea = data.histogram_after.bin_edges;
        Plotly.newPlot(div, [{
            x: ea.slice(0, -1).map((e, i) => (e + ea[i + 1]) / 2),
            y: data.histogram_after.counts, type: "bar",
            marker: { color: "#1d9bf0" },
        }], {
            title: { text: `Distribución normalizada (${method})`, font: { color: "#e7e9ea" } },
            paper_bgcolor: "#16191c", plot_bgcolor: "#16191c",
            font: { color: "#d7dadc" },
            xaxis: { title: "valor normalizado" }, yaxis: { title: "Frecuencia" },
            margin: { l: 50, r: 20, t: 50, b: 50 },
        }, { displayModeBar: false });
    }
}

async function runNormCompare() {
    NORM_COLUMN = document.getElementById("norm-col").value;
    const el = document.getElementById("norm-compare-content");
    el.innerHTML = "<span class='loading'>aplicando los 4 métodos...</span>";
    const data = await fetchJSON(`/api/preprolab/normalize/compare/${NORM_TABLE}/${NORM_COLUMN}`);
    if (data.error === "scaffold") return _handleNormScaffold("norm-compare-content", "badge-compare-norm", data, "NORM-5");
    if (data.error) return _showError("norm-compare-content", data);

    const badge = document.getElementById("badge-compare-norm");
    badge.classList.remove("scaffold");
    badge.textContent = "NORM-5 (resuelto)";

    el.innerHTML = "";
    let html = `
        <h3>Tabla resumen sobre ${data.n.toLocaleString()} filas</h3>
        <table class='kv'><thead><tr><th>Método</th><th>min</th><th>max</th><th>std</th><th>% en [0, 0.1]</th></tr></thead><tbody>
    `;
    data.summary_table.forEach(r => {
        const pct = r["pct_in_0_0.1"];
        html += `<tr><td><strong>${r.method}</strong></td><td>${r.min}</td><td>${r.max}</td><td>${r.std}</td><td>${pct}%</td></tr>`;
    });
    html += "</tbody></table>";
    if (data.interpretation && data.interpretation.length > 0) {
        html += "<div class='hints'><strong>Interpretación automática:</strong><ul>";
        data.interpretation.forEach(t => { html += `<li>${t}</li>`; });
        html += "</ul></div>";
    }
    el.innerHTML = html;

    const div = document.createElement("div");
    div.style.height = "360px";
    el.appendChild(div);
    const colors = { zscore: "#1d9bf0", minmax: "#ffd166", robust: "#06d6a0", decimal: "#ef476f" };
    const traces = Object.entries(data.methods).map(([name, info]) => {
        const e = info.histogram.bin_edges;
        const centers = e.slice(0, -1).map((x, i) => (x + e[i + 1]) / 2);
        return {
            x: centers, y: info.histogram.counts, type: "bar", name,
            marker: { color: colors[name] }, opacity: 0.6,
        };
    });
    Plotly.newPlot(div, traces, {
        title: { text: `Distribuciones normalizadas — ${NORM_COLUMN}`, font: { color: "#e7e9ea" } },
        paper_bgcolor: "#16191c", plot_bgcolor: "#16191c",
        font: { color: "#d7dadc" },
        barmode: "overlay",
        legend: { orientation: "h", y: -0.2 },
        xaxis: { title: "valor normalizado" }, yaxis: { title: "Frecuencia" },
        margin: { l: 50, r: 20, t: 50, b: 80 },
    }, { displayModeBar: false });
}

// ============================================================
// Render del bloque REDUCE_DIM (Fase 9)
// ============================================================

async function renderReduceDim() {
    const content = document.getElementById("content");
    content.innerHTML = `
        <h1>Reducción de dimensionalidad + Feature Selection</h1>
        <p class="muted">PCA (proyección lineal) · t-SNE (visualización 2D) · 3 familias de feature selection: Filter, Wrapper, Embedded.</p>
        <p class="muted">Trabaja siempre sobre <code>robots</code> con target <code>failure_next_48h</code>.</p>

        <section class="card">
            <h2>REDDIM-1 · PCA <span class="badge" id="badge-pca">PCA</span></h2>
            <div class="row">
                <label>n_components: <input type="number" id="pca-n" value="0" min="0" max="20" style="width:60px"></label>
                <span class="muted">0 = auto (≥95% varianza acumulada)</span>
                <button class="tbtn" onclick="runPCA()">Aplicar PCA</button>
            </div>
            <div id="reddim-pca-content"></div>
        </section>

        <section class="card">
            <h2>REDDIM-2 · t-SNE <span class="badge" id="badge-tsne">TSNE</span></h2>
            <div class="row">
                <label>perplexity: <input type="number" id="tsne-p" value="30" min="5" max="50" style="width:60px"></label>
                <label>max_rows: <input type="number" id="tsne-rows" value="1500" min="200" max="5000" style="width:80px"></label>
                <button class="tbtn" onclick="runTSNE()">Aplicar t-SNE (lento, ~15-30s)</button>
            </div>
            <div id="reddim-tsne-content"></div>
        </section>

        <section class="card">
            <h2>REDDIM-3 · Filter <span class="badge" id="badge-filter">FILTER</span></h2>
            <div class="row">
                <label>Método:
                    <select id="filter-method">
                        <option value="mutual_info">mutual_info</option>
                        <option value="chi2">chi²</option>
                        <option value="pearson">pearson</option>
                        <option value="variance">variance</option>
                    </select>
                </label>
                <label>k: <input type="number" id="filter-k" value="5" min="1" max="20" style="width:60px"></label>
                <button class="tbtn" onclick="runFilter()">Aplicar</button>
            </div>
            <div id="reddim-filter-content"></div>
        </section>

        <section class="card">
            <h2>REDDIM-4 · Wrapper <span class="badge" id="badge-wrapper">WRAP</span></h2>
            <div class="row">
                <label>Método:
                    <select id="wrapper-method">
                        <option value="rfe">RFE (más rápido)</option>
                        <option value="forward">forward</option>
                        <option value="backward">backward</option>
                    </select>
                </label>
                <label>k: <input type="number" id="wrapper-k" value="5" min="1" max="20" style="width:60px"></label>
                <button class="tbtn" onclick="runWrapper()">Aplicar (~10-20s)</button>
            </div>
            <div id="reddim-wrapper-content"></div>
        </section>

        <section class="card">
            <h2>REDDIM-5 · Embedded <span class="badge" id="badge-emb">EMB</span></h2>
            <div class="row">
                <label>Método:
                    <select id="emb-method">
                        <option value="rf_importance">RF feature_importances_</option>
                        <option value="lasso">Lasso L1</option>
                    </select>
                </label>
                <label>threshold: <input type="number" id="emb-threshold" value="0.05" step="0.01" min="0" max="1" style="width:80px"></label>
                <button class="tbtn" onclick="runEmbedded()">Aplicar</button>
            </div>
            <div id="reddim-emb-content"></div>
        </section>

        <section class="card">
            <h2>REDDIM-6 · Comparativa <span class="badge" id="badge-cmp-rd">COMPARE</span></h2>
            <div class="row">
                <label>k: <input type="number" id="cmp-k" value="5" min="1" max="20" style="width:60px"></label>
                <button class="tbtn" onclick="runReduceCompare()">Comparar las 3 familias</button>
            </div>
            <div id="reddim-cmp-content"></div>
        </section>
    `;
}

function _handleReduceScaffold(targetId, badgeId, data, exercise) {
    const el = document.getElementById(targetId);
    const badge = document.getElementById(badgeId);
    badge.classList.add("scaffold");
    badge.textContent = `${exercise} (scaffold)`;
    el.innerHTML = `
        <div class="exercise-placeholder">
            <p><strong>Ejercicio ${data.exercise} sin resolver.</strong></p>
            <p class="muted">${data.hint}</p>
            <p class="muted">Implementa en <code>apps/preprolab/src/web/routes/reduce_dim_ex.py</code>.</p>
        </div>
    `;
}

async function runPCA() {
    const n = document.getElementById("pca-n").value;
    const el = document.getElementById("reddim-pca-content");
    el.innerHTML = "<span class='loading'>computando PCA...</span>";
    const data = await fetchJSON(`/api/preprolab/reduce_dim/pca/robots?n_components=${n}`);
    if (data.error === "scaffold") return _handleReduceScaffold("reddim-pca-content", "badge-pca", data, "REDDIM-1");
    if (data.error) return _showError("reddim-pca-content", data);
    document.getElementById("badge-pca").classList.remove("scaffold");
    document.getElementById("badge-pca").textContent = "REDDIM-1 (resuelto)";

    el.innerHTML = "";
    let html = `
        <table class='kv stats-table'>
            <tr><th>Features originales</th><td>${data.n_features}</td></tr>
            <tr><th>Componentes elegidos</th><td><strong>${data.n_components_requested}</strong></td></tr>
            <tr><th>Varianza acumulada</th><td>${(data.cumulative_variance[data.cumulative_variance.length-1] * 100).toFixed(2)}%</td></tr>
        </table>
        <p class="muted" style="margin-top:8px">Features: <code>${data.features.join(", ")}</code></p>
    `;
    el.innerHTML = html;

    // Bar chart de explained_variance
    const bar = document.createElement("div");
    bar.style.height = "260px";
    el.appendChild(bar);
    Plotly.newPlot(bar, [
        { y: data.all_components_cumvar.map(v => v * 100), type: "scatter", mode: "lines+markers",
          marker: { color: "#1d9bf0" }, name: "% varianza acumulada" },
    ], {
        title: { text: "Varianza acumulada por componente", font: { color: "#e7e9ea" } },
        paper_bgcolor: "#16191c", plot_bgcolor: "#16191c",
        font: { color: "#d7dadc" },
        xaxis: { title: "componente #" }, yaxis: { title: "%", range: [0, 105] },
        margin: { l: 50, r: 20, t: 50, b: 50 },
        shapes: [{ type: "line", x0: 0, x1: data.all_components_cumvar.length-1, y0: 95, y1: 95,
                   line: { color: "#ef476f", dash: "dash" } }],
    }, { displayModeBar: false });

    // Scatter 2D PC1 vs PC2 coloreado por target
    const sc = document.createElement("div");
    sc.style.height = "360px";
    el.appendChild(sc);
    const s = data.scatter_2d;
    const class0 = s.pc1.map((_, i) => s.target[i] === 0 ? i : -1).filter(i => i >= 0);
    const class1 = s.pc1.map((_, i) => s.target[i] === 1 ? i : -1).filter(i => i >= 0);
    Plotly.newPlot(sc, [
        { x: class0.map(i => s.pc1[i]), y: class0.map(i => s.pc2[i]), mode: "markers",
          marker: { color: "#1d9bf0", size: 5, opacity: 0.6 }, name: "no fallo (0)", type: "scatter" },
        { x: class1.map(i => s.pc1[i]), y: class1.map(i => s.pc2[i]), mode: "markers",
          marker: { color: "#ef476f", size: 5, opacity: 0.7 }, name: "fallo (1)", type: "scatter" },
    ], {
        title: { text: "Proyección PCA 2D coloreada por target", font: { color: "#e7e9ea" } },
        paper_bgcolor: "#16191c", plot_bgcolor: "#16191c",
        font: { color: "#d7dadc" },
        xaxis: { title: "PC1" }, yaxis: { title: "PC2" },
        margin: { l: 50, r: 20, t: 50, b: 50 },
    }, { displayModeBar: false });
}

async function runTSNE() {
    const p = document.getElementById("tsne-p").value;
    const rows = document.getElementById("tsne-rows").value;
    const el = document.getElementById("reddim-tsne-content");
    el.innerHTML = "<span class='loading'>computando t-SNE (puede tardar 15-30s)...</span>";
    const data = await fetchJSON(`/api/preprolab/reduce_dim/tsne/robots?perplexity=${p}&max_rows=${rows}`);
    if (data.error === "scaffold") return _handleReduceScaffold("reddim-tsne-content", "badge-tsne", data, "REDDIM-2");
    if (data.error) return _showError("reddim-tsne-content", data);
    document.getElementById("badge-tsne").classList.remove("scaffold");
    document.getElementById("badge-tsne").textContent = "REDDIM-2 (resuelto)";

    el.innerHTML = `<p class="muted">${data.n_samples_used} filas usadas · perplexity=${data.perplexity} · KL divergence=${data.kl_divergence.toFixed(3)}</p>`;
    const sc = document.createElement("div");
    sc.style.height = "420px";
    el.appendChild(sc);
    const s = data.scatter_2d;
    const class0 = s.x.map((_, i) => s.target[i] === 0 ? i : -1).filter(i => i >= 0);
    const class1 = s.x.map((_, i) => s.target[i] === 1 ? i : -1).filter(i => i >= 0);
    Plotly.newPlot(sc, [
        { x: class0.map(i => s.x[i]), y: class0.map(i => s.y[i]), mode: "markers",
          marker: { color: "#1d9bf0", size: 4, opacity: 0.6 }, name: "no fallo (0)", type: "scatter" },
        { x: class1.map(i => s.x[i]), y: class1.map(i => s.y[i]), mode: "markers",
          marker: { color: "#ef476f", size: 4, opacity: 0.7 }, name: "fallo (1)", type: "scatter" },
    ], {
        title: { text: "t-SNE 2D coloreado por target", font: { color: "#e7e9ea" } },
        paper_bgcolor: "#16191c", plot_bgcolor: "#16191c",
        font: { color: "#d7dadc" },
        xaxis: { title: "t-SNE 1" }, yaxis: { title: "t-SNE 2" },
        margin: { l: 50, r: 20, t: 50, b: 50 },
    }, { displayModeBar: false });
}

function _renderRanking(targetId, data) {
    const el = document.getElementById(targetId);
    let html = `<p class="muted">Seleccionadas (${data.selected.length}): <strong>${data.selected.join(", ")}</strong></p>`;
    html += "<h3>Ranking de features</h3>";
    html += "<table class='kv'><thead><tr><th>#</th><th>feature</th><th>score</th>";
    if (data.ranking[0] && "pvalue" in data.ranking[0]) html += "<th>p-value</th>";
    html += "</tr></thead><tbody>";
    data.ranking.forEach((r, i) => {
        const selected = data.selected.includes(r.feature);
        html += `<tr class='${selected ? "" : ""}'>`;
        html += `<td>${i+1}</td><td><strong style='${selected ? "color:#06d6a0" : ""}'>${r.feature}</strong></td>`;
        html += `<td>${r.score.toFixed(4)}</td>`;
        if ("pvalue" in r) html += `<td>${r.pvalue !== null ? r.pvalue.toExponential(2) : "—"}</td>`;
        html += "</tr>";
    });
    html += "</tbody></table>";
    el.innerHTML = html;
}

async function runFilter() {
    const m = document.getElementById("filter-method").value;
    const k = document.getElementById("filter-k").value;
    const el = document.getElementById("reddim-filter-content");
    el.innerHTML = "<span class='loading'>computando...</span>";
    const data = await fetchJSON(`/api/preprolab/reduce_dim/filter/robots?method=${m}&k=${k}`);
    if (data.error === "scaffold") return _handleReduceScaffold("reddim-filter-content", "badge-filter", data, "REDDIM-3");
    if (data.error) return _showError("reddim-filter-content", data);
    document.getElementById("badge-filter").classList.remove("scaffold");
    document.getElementById("badge-filter").textContent = "REDDIM-3 (resuelto)";
    _renderRanking("reddim-filter-content", data);
}

async function runWrapper() {
    const m = document.getElementById("wrapper-method").value;
    const k = document.getElementById("wrapper-k").value;
    const el = document.getElementById("reddim-wrapper-content");
    el.innerHTML = "<span class='loading'>computando con cross-validation (~10-20s)...</span>";
    const data = await fetchJSON(`/api/preprolab/reduce_dim/wrapper/robots?method=${m}&k=${k}`);
    if (data.error === "scaffold") return _handleReduceScaffold("reddim-wrapper-content", "badge-wrapper", data, "REDDIM-4");
    if (data.error) return _showError("reddim-wrapper-content", data);
    document.getElementById("badge-wrapper").classList.remove("scaffold");
    document.getElementById("badge-wrapper").textContent = "REDDIM-4 (resuelto)";
    el.innerHTML = `
        <p class="muted">Método: <code>${data.method}</code></p>
        <p>Seleccionadas (${data.selected.length}): <strong style='color:#06d6a0'>${data.selected.join(", ")}</strong></p>
        <p class="muted">Eliminadas: <code>${data.dropped.join(", ")}</code></p>
    `;
}

async function runEmbedded() {
    const m = document.getElementById("emb-method").value;
    const t = document.getElementById("emb-threshold").value;
    const el = document.getElementById("reddim-emb-content");
    el.innerHTML = "<span class='loading'>computando...</span>";
    const data = await fetchJSON(`/api/preprolab/reduce_dim/embedded/robots?method=${m}&threshold=${t}`);
    if (data.error === "scaffold") return _handleReduceScaffold("reddim-emb-content", "badge-emb", data, "REDDIM-5");
    if (data.error) return _showError("reddim-emb-content", data);
    document.getElementById("badge-emb").classList.remove("scaffold");
    document.getElementById("badge-emb").textContent = "REDDIM-5 (resuelto)";
    _renderRanking("reddim-emb-content", data);
}

async function runReduceCompare() {
    const k = document.getElementById("cmp-k").value;
    const el = document.getElementById("reddim-cmp-content");
    el.innerHTML = "<span class='loading'>aplicando las 3 familias (~30s)...</span>";
    const data = await fetchJSON(`/api/preprolab/reduce_dim/compare/robots?k=${k}`);
    if (data.error === "scaffold") return _handleReduceScaffold("reddim-cmp-content", "badge-cmp-rd", data, "REDDIM-6");
    if (data.error) return _showError("reddim-cmp-content", data);
    document.getElementById("badge-cmp-rd").classList.remove("scaffold");
    document.getElementById("badge-cmp-rd").textContent = "REDDIM-6 (resuelto)";

    let html = "<h3>Features por familia (k=" + data.k + ")</h3>";
    html += "<table class='kv'><thead><tr><th>Familia</th><th>Features elegidas</th></tr></thead><tbody>";
    Object.entries(data.selected_by_family).forEach(([fam, feats]) => {
        html += `<tr><td><strong>${fam}</strong></td><td><code>${feats.join(", ")}</code></td></tr>`;
    });
    html += "</tbody></table>";

    html += "<h3 style='margin-top:14px'>Consenso entre familias</h3>";
    html += "<table class='kv'><thead><tr><th>Feature</th><th>Elegida por</th></tr></thead><tbody>";
    data.cross_family_agreement.forEach(r => {
        const color = r.selected_by_n_families === 3 ? "#06d6a0" : (r.selected_by_n_families === 2 ? "#ffd166" : "#71767b");
        html += `<tr><td><strong style='color:${color}'>${r.feature}</strong></td><td>${r.selected_by_n_families}/3 — ${r.families.join(", ")}</td></tr>`;
    });
    html += "</tbody></table>";
    html += `<div class="hints" style="margin-top:12px"><em>${data.interpretation}</em></div>`;
    el.innerHTML = html;
}

// ============================================================
// Render del bloque REDUCE_INST (Fase 10)
// ============================================================

async function renderReduceInst() {
    const content = document.getElementById("content");
    content.innerHTML = `
        <h1>Reducción de instancias</h1>
        <p class="muted">SRSWOR · estratificado · balanceado · por clusters · K-Means compresión. Trabaja sobre <code>robots</code> con target <code>failure_next_48h</code>.</p>

        <section class="card">
            <h2>INST-1 · SRSWOR <span class="badge" id="badge-srswor">SRSWOR</span></h2>
            <div class="row">
                <label>Fracción: <input type="number" id="srswor-frac" value="0.3" step="0.1" min="0.01" max="1" style="width:70px"></label>
                <button class="tbtn" onclick="runInst('srswor')">Muestrear</button>
            </div>
            <div id="inst-srswor-content"></div>
        </section>

        <section class="card">
            <h2>INST-2 · Estratificado <span class="badge" id="badge-stratified">STRAT</span></h2>
            <div class="row">
                <label>Fracción: <input type="number" id="strat-frac" value="0.3" step="0.1" min="0.01" max="1" style="width:70px"></label>
                <button class="tbtn" onclick="runInst('stratified')">Muestrear preservando clases</button>
            </div>
            <div id="inst-stratified-content"></div>
        </section>

        <section class="card">
            <h2>INST-3 · Balanceado <span class="badge" id="badge-balanced">BAL</span></h2>
            <div class="row">
                <label>Estrategia:
                    <select id="bal-strategy">
                        <option value="undersample">undersample (reduce mayoritaria)</option>
                        <option value="oversample">oversample (duplica minoritaria)</option>
                    </select>
                </label>
                <button class="tbtn" onclick="runInst('balanced')">Forzar balance</button>
            </div>
            <div id="inst-balanced-content"></div>
        </section>

        <section class="card">
            <h2>INST-4 · Por clusters <span class="badge" id="badge-bycluster">CLUST</span></h2>
            <div class="row">
                <label>n_clusters: <input type="number" id="bc-nc" value="10" min="2" max="50" style="width:60px"></label>
                <label>a seleccionar: <input type="number" id="bc-sel" value="3" min="1" max="50" style="width:60px"></label>
                <button class="tbtn" onclick="runInst('by_clusters')">Aplicar</button>
            </div>
            <div id="inst-by_clusters-content"></div>
        </section>

        <section class="card">
            <h2>INST-5 · K-Means compresión <span class="badge" id="badge-kmc">KMC</span></h2>
            <div class="row">
                <label>K centroides: <input type="number" id="kmc-k" value="50" min="5" max="500" style="width:80px"></label>
                <button class="tbtn" onclick="runInst('kmeans_compress')">Comprimir</button>
            </div>
            <div id="inst-kmeans_compress-content"></div>
        </section>
    `;
}

function _handleInstScaffold(targetId, badgeId, data, exercise) {
    const el = document.getElementById(targetId);
    const badge = document.getElementById(badgeId);
    badge.classList.add("scaffold");
    badge.textContent = `${exercise} (scaffold)`;
    el.innerHTML = `
        <div class="exercise-placeholder">
            <p><strong>Ejercicio ${data.exercise} sin resolver.</strong></p>
            <p class="muted">${data.hint}</p>
            <p class="muted">Implementa en <code>apps/preprolab/src/web/routes/reduce_inst_ex.py</code>.</p>
        </div>
    `;
}

async function runInst(method) {
    const params = new URLSearchParams();
    if (method === "srswor") params.set("fraction", document.getElementById("srswor-frac").value);
    if (method === "stratified") params.set("fraction", document.getElementById("strat-frac").value);
    if (method === "balanced") params.set("strategy", document.getElementById("bal-strategy").value);
    if (method === "by_clusters") {
        params.set("n_clusters", document.getElementById("bc-nc").value);
        params.set("n_clusters_to_select", document.getElementById("bc-sel").value);
    }
    if (method === "kmeans_compress") params.set("k", document.getElementById("kmc-k").value);

    const el = document.getElementById(`inst-${method}-content`);
    el.innerHTML = "<span class='loading'>computando...</span>";
    const data = await fetchJSON(`/api/preprolab/reduce_inst/${method}/robots?${params}`);
    const exMap = {srswor: "INST-1", stratified: "INST-2", balanced: "INST-3", by_clusters: "INST-4", kmeans_compress: "INST-5"};
    const badgeMap = {srswor: "badge-srswor", stratified: "badge-stratified", balanced: "badge-balanced", by_clusters: "badge-bycluster", kmeans_compress: "badge-kmc"};
    if (data.error === "scaffold") return _handleInstScaffold(`inst-${method}-content`, badgeMap[method], data, exMap[method]);
    if (data.error) return _showError(`inst-${method}-content`, data);
    document.getElementById(badgeMap[method]).classList.remove("scaffold");
    document.getElementById(badgeMap[method]).textContent = `${exMap[method]} (resuelto)`;

    let html = `
        <table class='kv stats-table'>
            <tr><th>Filas</th><td>${data.rows_before.toLocaleString()} → <strong>${data.rows_after.toLocaleString()}</strong></td></tr>
    `;
    if (data.compression_ratio) html += `<tr><th>Ratio compresión</th><td>${data.compression_ratio}x</td></tr>`;
    if ("ratio_preserved" in data) html += `<tr><th>Ratio target preservado</th><td>${data.ratio_preserved}</td></tr>`;
    if (data.chosen_clusters) html += `<tr><th>Clusters elegidos</th><td>${data.chosen_clusters.join(", ")}</td></tr>`;
    if (data.target_size_per_class) html += `<tr><th>Tamaño por clase</th><td>${data.target_size_per_class}</td></tr>`;
    html += "</table>";

    // Distribución antes vs después
    const distB = data.class_distribution_before;
    const distA = data.class_distribution_after;
    html += "<h3 style='margin-top:14px'>Distribución por clase</h3>";
    html += "<table class='kv'><thead><tr><th>clase</th><th>antes</th><th>después</th></tr></thead><tbody>";
    Object.keys(distB).forEach(k => {
        const before = distB[k];
        const after = distA[k] || 0;
        const pctB = (100 * before / data.rows_before).toFixed(1);
        const pctA = data.rows_after > 0 ? (100 * after / data.rows_after).toFixed(1) : "0";
        html += `<tr><td><code>${k}</code></td><td>${before.toLocaleString()} (${pctB}%)</td><td>${after.toLocaleString()} (${pctA}%)</td></tr>`;
    });
    html += "</tbody></table>";

    if (data.cluster_size_stats) {
        const s = data.cluster_size_stats;
        html += `<p class="muted">Tamaño de clusters: min=${s.min} · max=${s.max} · mean=${s.mean} · median=${s.median}</p>`;
    }

    el.innerHTML = html;
}

// ============================================================
// Boot
// ============================================================

(async function init() {
    LAB_STATUS = await loadStatus();
    renderBlocks(LAB_STATUS);
    // Selección por defecto: EDA si el seed está listo
    selectBlock("eda");
    // Marca el item activo
    const eda_li = document.querySelector('[data-block="eda"]');
    if (eda_li) eda_li.classList.add("active");
})();
