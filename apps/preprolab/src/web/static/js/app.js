// PreproLab - SPA Fase 1 (esqueleto)
// En fases posteriores cada bloque tendra su propia vista con Plotly.

const BLOCK_INFO = {
    eda:          { label: "EDA",                desc: "Analisis univariable + bivariable + correlaciones." },
    missing:      { label: "Valores perdidos",   desc: "Diagnostico MCAR/MAR/MNAR + imputacion (media, KNN, K-Means, EM, MICE)." },
    outliers:     { label: "Outliers + ruido",   desc: "IQR, Z-score, boxplot + noise filters (EF/CVCF/IPF)." },
    integration:  { label: "Integracion",        desc: "union, joins (4 tipos), correlaciones para deduplicar." },
    transform:    { label: "Transformacion",     desc: "One-hot, ordinal, multi-flag, discretizacion (3 metodos), pivot/groupby." },
    normalize:    { label: "Normalizacion",      desc: "Z-score, Min-Max, Robust, Decimal — comparados sobre mismo modelo." },
    reduce_dim:   { label: "Reduccion dim.",     desc: "PCA, t-SNE, AutoEncoders + feature selection (filter/wrapper/embedded)." },
    reduce_inst:  { label: "Reduccion inst.",    desc: "SRSWOR, estratificado, balanceado, K-Means compresion." },
};

async function loadStatus() {
    try {
        const res = await fetch("/api/preprolab/lab/status");
        return await res.json();
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
        li.addEventListener("click", () => selectBlock(key, status));
        list.appendChild(li);
    });
}

function selectBlock(key, status) {
    document.querySelectorAll("#block-list li").forEach(li => {
        li.classList.toggle("active", li.dataset.block === key);
    });
    const info = BLOCK_INFO[key];
    const unlocked = status.blocks && status.blocks[key];
    const content = document.getElementById("content");
    content.innerHTML = `
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

(async function init() {
    const status = await loadStatus();
    renderBlocks(status);
})();
