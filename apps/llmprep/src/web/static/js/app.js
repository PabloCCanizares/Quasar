// LLM Lab - SPA esqueleto (Fase 12)

const BLOCK_INFO = {
    clean:    { label: "1 · Clean",    desc: "Normalización Unicode, fix encoding, HTML strip, filtro de longitud." },
    dedup:    { label: "2 · Dedup",    desc: "Near-duplicates con MinHash/LSH + grafo SIMILAR_TO en Neo4j." },
    tokenize: { label: "3 · Tokenize", desc: "Tokenizer BPE + shards .bin estilo nanoGPT." },
    train:    { label: "4 · Train",    desc: "nanoGPT + comparativa corpus sucio vs limpio." },
};

let LAB_STATUS = null;

async function loadStatus() {
    try {
        const res = await fetch("/api/llmprep/lab/status");
        return await res.json();
    } catch (e) {
        console.error("status failed", e);
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
    const unlocked = LAB_STATUS.blocks && LAB_STATUS.blocks[key];
    document.getElementById("content").innerHTML = `
        <h1>${info.label}</h1>
        <p>${info.desc}</p>
        <div class="placeholder">
            <h3>Bloque en construcción</h3>
            <p>Este bloque se implementará en las fases siguientes del roadmap Quasar.</p>
            <p class="muted">Estado actual: ${unlocked ? "resuelto" : "scaffold (ejercicio del alumno)"}</p>
            <p class="muted">Para desbloquear: <code>./lab.sh llmprep unlock ${key}</code></p>
        </div>
    `;
}

(async function init() {
    LAB_STATUS = await loadStatus();
    renderBlocks(LAB_STATUS);
})();
