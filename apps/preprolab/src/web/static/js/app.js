// PreproLab - SPA Fase 3 (EDA operativo)
//
// El tab EDA carga overview + schema + missing + univariate + correlations.
// Los otros bloques siguen como placeholder (se irán activando por fase).

const BLOCK_INFO = {
    eda:          { label: "EDA",               desc: "Analisis univariable + missing matrix + correlaciones.",   render: renderEDA },
    missing:      { label: "Valores perdidos",  desc: "Diagnostico MCAR/MAR/MNAR + imputacion (media, KNN, K-Means, EM, MICE).", render: renderMissing },
    outliers:     { label: "Outliers + ruido",  desc: "IQR, Z-score, boxplot + noise filters (EF/CVCF/IPF).", render: renderOutliers },
    integration:  { label: "Integracion",       desc: "union, joins (4 tipos), correlaciones para deduplicar." },
    transform:    { label: "Transformacion",    desc: "One-hot, ordinal, multi-flag, discretizacion, pivot/groupby." },
    normalize:    { label: "Normalizacion",     desc: "Z-score, Min-Max, Robust, Decimal - comparados sobre mismo modelo." },
    reduce_dim:   { label: "Reduccion dim.",    desc: "PCA, t-SNE, AutoEncoders + feature selection." },
    reduce_inst:  { label: "Reduccion inst.",   desc: "SRSWOR, estratificado, balanceado, K-Means compresion." },
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
