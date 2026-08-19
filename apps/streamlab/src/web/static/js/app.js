// StreamLab — SPA del centro de control

const BLOQUES = {
    windows: {
        titulo: "Ventanas",
        desc: "Agrupar por tiempo: tumbling, sliding y de sesión. La ventana de sesión es la que detecta que un robot dejó de emitir.",
        fase: 3,
    },
    late: {
        titulo: "Datos tardíos",
        desc: "El watermark: hasta cuándo esperas a una lectura que llega tarde, qué corriges con ella y qué descartas.",
        fase: 4,
    },
    state: {
        titulo: "Estado y checkpoints",
        desc: "Agregar sin releer el histórico, recordar por dónde ibas, y quitar los duplicados que genera el reintento.",
        fase: 5,
    },
};

let ESTADO = null;
let EMISION = null;

async function json(url) {
    const r = await fetch(url);
    return r.json();
}

function vista() {
    return (location.hash || "#inicio").slice(1);
}

function pintarNav() {
    const actual = vista();
    const tabs = [["inicio", "Inicio"], ["ventanas", "Ventanas"],
                  ["tardios", "Tardíos"], ["estado", "Estado"], ["demo", "★ Demo"]];
    document.getElementById("tabs").innerHTML = tabs.map(([k, t]) =>
        `<button class="tab ${k === actual ? "active" : ""}" onclick="location.hash='${k}'">${t}</button>`
    ).join("");
}

// ============================================================
// Inicio
// ============================================================
function panelEmision(e) {
    if (!e || !e.emitido) {
        return `<div class="emision vacia">
            <h2>Todavía no hay telemetría</h2>
            <p>La flota no está emitiendo. Genera una jornada de datos para empezar:</p>
            <pre>./lab.sh streamlab emit</pre>
            <p class="muted">O desde el <a href="http://localhost:8080#status">Hub</a>, botón «Emitir telemetría de la flota».
            Con <code>--intervalo 2</code> los lotes salen a ritmo real y se ve llegar el flujo.</p>
        </div>`;
    }
    const g = e.ground_truth || {};
    const dato = (n, etiqueta, extra) => `<div class="dato">
        <div class="num">${(n ?? 0).toLocaleString("es")}</div>
        <div class="lbl">${etiqueta}</div>
        ${extra ? `<div class="sub">${extra}</div>` : ""}</div>`;
    return `<div class="emision">
        <h2>Telemetría emitida</h2>
        <p class="muted">${e.lotes} lotes · ${e.minutos_simulados} min de jornada ·
        ${e.robots} robots en ${(e.almacenes || []).length} almacenes</p>
        <div class="datos">
            ${dato(g.total, "lecturas", "escritas en raw/")}
            ${dato(g.retrasadas, "llegan tarde", `${g.muy_retrasadas ?? 0} con +3 lotes de retraso`)}
            ${dato(g.duplicadas, "duplicadas", "reintentos del emisor")}
            ${dato(g.mudas_omitidas, "nunca llegaron", "robots averiados")}
            ${dato(g.en_riesgo_real, `sobre ${e.umbral_alerta_c}°C`, "lecturas en riesgo térmico")}
        </div>
        <p class="muted" style="margin-top:14px">Estos recuentos son el <strong>ground truth</strong>:
        cuando implementes los bloques, sabrás si tu detector acierta en vez de creértelo.</p>
    </div>`;
}

function renderInicio() {
    const bloques = Object.entries(BLOQUES).map(([clave, b]) => {
        const abierto = !!(ESTADO.blocks || {})[clave];
        const pedido = !!(ESTADO.flagged || {})[clave];
        let etiqueta = abierto ? "solución" : "ejercicio";
        if (pedido && !abierto) etiqueta = "sin solución";
        return `<div class="block">
            <h3><span class="bdot ${abierto ? "on" : "off"}"></span>${b.titulo}
                <span class="state ${abierto ? "on" : ""}">${etiqueta}</span>
            </h3>
            <p>${b.desc}</p>
            <p class="muted" style="margin-top:8px;font-size:12px">${
                b.fase <= ESTADO.phase ? "disponible" : `llega en la fase ${b.fase}`
            }</p>
        </div>`;
    }).join("");

    return `
        <h1>Centro de control de la flota</h1>
        <p class="lead">Los robots ya no vuelcan su telemetría una vez al día: la emiten mientras trabajan.
        Aquí se aprende a responder preguntas sobre datos que todavía están llegando.</p>

        <div class="scenario">
            <h2>Qué pasó en Rotterdam</h2>
            <p>Hasta ahora la telemetría de la flota se procesaba por lotes, de un día para otro. Así funciona
            <a href="http://localhost:8002">PreproLab</a>: cargas el histórico, lo limpias, entrenas.</p>
            <p>Hasta que un robot ardió en el almacén de Rotterdam. El sobrecalentamiento estaba en los datos —se veía venir—
            pero nadie lo leyó hasta catorce horas después. La respuesta era correcta y llegó tarde, que es otra forma de
            estar equivocada.</p>
            <p>La dirección quiere un centro de control en vivo. Eso es lo que vas a construir.</p>
        </div>

        ${panelEmision(EMISION)}

        <div class="blocks">${bloques}</div>

        <div class="phase-note">
            Fase ${ESTADO.phase} — ${ESTADO.note}
            <br>Los bloques se abren y se cierran desde el
            <a href="http://localhost:8080#config">Hub</a>, sin tocar el código.
        </div>`;
}

// ============================================================
// Ventanas
// ============================================================
function tabla(filas, columnas) {
    if (!filas || !filas.length) return `<p class="muted">Sin resultados.</p>`;
    const cab = columnas.map(c => `<th>${c}</th>`).join("");
    const cuerpo = filas.map(f =>
        `<tr>${columnas.map(c => `<td>${f[c] ?? ""}</td>`).join("")}</tr>`
    ).join("");
    return `<div class="tabla-wrap"><table><thead><tr>${cab}</tr></thead><tbody>${cuerpo}</tbody></table></div>`;
}

function hora(iso) {
    return (iso || "").slice(11, 16);
}

const BLOQUE_DE = {
    tumbling: "windows", sliding: "windows", session: "windows",
    alertas: "windows", comparar: "windows", en_flujo: "windows",
    retraso: "late", descartadas: "late", con_watermark: "late",
    sin_watermark: "late", late_comparar: "late", barrido: "late",
    dedup: "state", incremental: "state", a_mongo: "state",
    reanudar: "state", sin_memoria: "state", recuperacion: "state",
    riesgo: "demo",
};

async function correr(ejercicio) {
    const salida = document.getElementById(`out-${ejercicio}`);
    salida.innerHTML = `<p class="muted">calculando…</p>`;
    const params = {
        tumbling: () => `minutos=${document.getElementById("p-tumbling").value}`,
        sliding: () => `minutos=${document.getElementById("p-sliding-v").value}&paso=${document.getElementById("p-sliding-p").value}`,
        session: () => `gap=${document.getElementById("p-session").value}`,
        alertas: () => `minutos=5&descartar_absurdas=${document.getElementById("p-alertas").checked}`,
        comparar: () => `minutos=${document.getElementById("p-comparar").value}`,
        en_flujo: () => `minutos=5&lotes_por_tanda=${document.getElementById("p-flujo").value}`,
        retraso: () => "",
        descartadas: () => `watermark=${document.getElementById("p-desc-w").value}&ventana=${document.getElementById("p-desc-v").value}`,
        con_watermark: () => `watermark=${document.getElementById("p-cw-w").value}&ventana=${document.getElementById("p-cw-v").value}`,
        sin_watermark: () => `ventana=${document.getElementById("p-sw-v").value}`,
        late_comparar: () => `watermark=${document.getElementById("p-lc-w").value}&ventana=${document.getElementById("p-lc-v").value}`,
        barrido: () => `ventana=${document.getElementById("p-barrido").value}`,
        dedup: () => "",
        incremental: () => `ventana=5&lotes_por_tanda=${document.getElementById("p-inc").value}`,
        a_mongo: () => "ventana=5",
        reanudar: () => `reiniciar=${document.getElementById("p-rean").checked}`,
        sin_memoria: () => "ventana=5",
        recuperacion: () => "ventana=5",
        riesgo: () => `ventana=${document.getElementById("p-demo-v").value}`
            + `&watermark=${document.getElementById("p-demo-w").value}`
            + `&lotes_por_tanda=${document.getElementById("p-demo-t").value}`,
    }[ejercicio]();

    const bloque = BLOQUE_DE[ejercicio];
    const ruta = ejercicio === "late_comparar" ? "comparar" : ejercicio;

    let d;
    try {
        d = await json(`/api/streamlab/${bloque}/${ruta}?${params}`);
    } catch {
        salida.innerHTML = `<p class="err">No se pudo ejecutar. Mira los logs del contenedor.</p>`;
        return;
    }
    if (d.error === "scaffold") {
        salida.innerHTML = `<div class="scaffold-msg"><strong>${d.exercise}</strong> — ${d.hint}</div>`;
        return;
    }
    salida.innerHTML = pintarResultado(ejercicio, d);
}

function pintarResultado(ejercicio, d) {
    if (ejercicio === "riesgo") return pintarDemo(d);
    // --- Bloque STATE ---
    if (ejercicio === "dedup") {
        return `<p><strong>${d.lecturas}</strong> lecturas →
            <strong>${d.tras_deduplicar}</strong> tras deduplicar
            (<strong>${d.duplicados_quitados}</strong> copias fuera)</p>
            <p class="destacado">Marcadas como reintento por el emisor: ${d.marcados_como_reintento}
            ${d.duplicados_quitados === d.marcados_como_reintento ? " — cuadra exacto" : ""}</p>
            ${tabla(d.ejemplos.map(e => ({...e, ts_evento: hora(e.ts_evento)})),
                    ["robot_id", "sensor", "ts_evento", "copias"])}
            <p class="muted" style="margin-top:8px">${d.nota}</p>`;
    }
    if (ejercicio === "incremental") {
        const max = Math.max(...d.por_tanda.map(t => t.estado), 1);
        const barras = d.por_tanda.map((t, i) =>
            `<div class="rx-row"><span class="rx-lbl">tanda ${i}</span>
             <span class="rx-track"><span class="rx-fill" style="width:${Math.max(2, 100 * t.estado / max)}%"></span></span>
             <span class="rx-val">${t.estado}</span></div>`).join("");
        return `<p>Estado retenido por tanda (máximo <strong>${d.estado_maximo}</strong>,
            final <strong>${d.estado_final}</strong>):</p>${barras}
            <p class="muted" style="margin-top:8px">Liberadas del estado:
            ${d.por_tanda.map(t => t.eliminadas_del_estado).join(" · ")}</p>
            <p class="destacado">${d.nota}</p>`;
    }
    if (ejercicio === "a_mongo") {
        return `<p><strong>${d.documentos_en_mongo}</strong> documentos en
            <code>${d.coleccion}</code> · ${d.tandas_escritas} tandas ·
            ${d.operaciones} operaciones</p>
            <p class="destacado">${d.nota}</p>`;
    }
    if (ejercicio === "reanudar" || ejercicio === "sin_memoria") {
        return `<p><strong>${d.lecturas_procesadas}</strong> lecturas procesadas en
            ${d.tandas} tandas${d.empezo_de_cero !== undefined
                ? ` · empezó de cero: <strong>${d.empezo_de_cero}</strong>` : ""}</p>
            <p class="destacado">${d.nota}</p>`;
    }
    if (ejercicio === "recuperacion") {
        return `<div class="tabla-wrap"><table>
            <thead><tr><th>momento</th><th>tandas</th><th>lecturas</th></tr></thead>
            <tbody>
              <tr><td>antes de caer</td><td>${d.primer_arranque.tandas}</td><td>${d.primer_arranque.lecturas}</td></tr>
              <tr><td>tras reanudar</td><td>${d.tras_reanudar.tandas}</td><td>${d.tras_reanudar.lecturas}</td></tr>
              <tr><td><strong>total</strong></td><td></td><td><strong>${d.lecturas_totales}</strong></td></tr>
            </tbody></table></div>
            <p class="destacado" style="margin-top:10px">${d.nota}</p>`;
    }
    // --- Bloque LATE ---
    if (ejercicio === "retraso") {
        const max = Math.max(...d.distribucion.map(p => p.lecturas));
        const barras = d.distribucion.map(p =>
            `<div class="rx-row"><span class="rx-lbl">${p.retraso_min} min</span>
             <span class="rx-track"><span class="rx-fill" style="width:${Math.max(2, 100 * p.lecturas / max)}%"></span></span>
             <span class="rx-val">${p.lecturas}</span></div>`).join("");
        return `<p>Retraso entre medir y llegar:</p>${barras}
            ${tabla(d.por_almacen, ["almacen", "retraso_medio", "retraso_max", "lecturas"])}
            <p class="destacado" style="margin-top:8px">${d.nota}</p>`;
    }
    if (ejercicio === "descartadas") {
        return `<p><strong>${d.descartadas_estimadas}</strong> de ${d.lecturas} lecturas
            (<strong>${d.porcentaje}%</strong>) quedarían fuera con watermark ${d.watermark_min} min
            y ventanas de ${d.ventana_min} min.</p>
            ${tabla(d.ejemplos, ["robot_id", "almacen", "lote", "retraso_min"])}
            <p class="muted" style="margin-top:8px">${d.nota}</p>`;
    }
    if (ejercicio === "con_watermark" || ejercicio === "sin_watermark") {
        return `<p>modo <strong>${d.modo_salida}</strong> · ${d.tandas} tandas ·
            ${d.lecturas_entradas} lecturas</p>
            <p><strong>${d.ventanas}</strong> ventanas emitidas ·
            <strong>${d.descartadas_por_watermark}</strong> descartadas ·
            estado retenido <strong>${d.filas_en_estado}</strong> filas</p>
            ${d.watermark_final ? `<p class="destacado">watermark final: ${d.watermark_final}</p>` : ""}`;
    }
    if (ejercicio === "late_comparar") {
        const c = d.con_watermark, s = d.sin_watermark;
        return `<div class="tabla-wrap"><table>
            <thead><tr><th></th><th>modo</th><th>ventanas</th><th>descartadas</th><th>estado retenido</th></tr></thead>
            <tbody>
              <tr><td><strong>con watermark</strong></td><td>${c.modo_salida}</td><td>${c.ventanas}</td>
                  <td>${c.descartadas_por_watermark}</td><td>${c.filas_en_estado} filas</td></tr>
              <tr><td><strong>sin watermark</strong></td><td>${s.modo_salida}</td><td>${s.ventanas}</td>
                  <td>${s.descartadas_por_watermark}</td><td>${s.filas_en_estado} filas</td></tr>
            </tbody></table></div>
            <p class="destacado" style="margin-top:10px">Estimación a mano: ${d.descartadas_estimadas} ·
            Real de Spark: ${d.descartadas_reales}</p>
            <p class="muted">${d.nota}</p>`;
    }
    if (ejercicio === "barrido") {
        const max = Math.max(...d.puntos.map(p => p.descartadas), 1);
        const barras = d.puntos.map(p =>
            `<div class="rx-row"><span class="rx-lbl">esperar ${p.watermark_min} min</span>
             <span class="rx-track"><span class="rx-fill" style="width:${Math.max(1, 100 * p.descartadas / max)}%"></span></span>
             <span class="rx-val">${p.descartadas}</span></div>`).join("");
        return `<p>Sobre ${d.lecturas} lecturas, con ventanas de ${d.ventana_min} min:</p>
            ${barras}
            <p class="destacado" style="margin-top:10px">${d.nota}</p>`;
    }
    // --- Bloque WINDOWS ---
    if (ejercicio === "comparar") {
        const fila = (k, v) => `<tr><td><strong>${k}</strong></td><td>${v.filas}</td><td>${v.ventanas}</td>
            <td>${v.lecturas_contadas.toLocaleString("es")}</td><td class="nota">${v.nota}</td></tr>`;
        return `<div class="tabla-wrap"><table>
            <thead><tr><th>corte</th><th>filas</th><th>ventanas</th><th>lecturas contadas</th><th></th></tr></thead>
            <tbody>${fila("tumbling", d.tumbling)}${fila("sliding", d.sliding)}${fila("session", d.session)}</tbody>
            </table></div>
            <p class="muted" style="margin-top:10px">Misma telemetría y mismo sensor: solo cambia dónde se corta el tiempo.
            Las tres respuestas son correctas y distintas.</p>`;
    }
    if (ejercicio === "session") {
        return `<p><strong>${d.sesiones}</strong> sesiones · <strong>${d.robots}</strong> robots ·
            gap ${d.gap_min} min</p>
            <p class="destacado">Robots que dejaron de emitir: <strong>${d.robots_mudos.length}</strong>
            ${d.robots_mudos.length ? `— ${d.robots_mudos.join(", ")}` : ""}</p>
            ${tabla(d.filas.slice(0, 12).map(f => ({...f, inicio: hora(f.inicio), fin: hora(f.fin)})),
                    ["robot_id", "inicio", "fin", "lecturas", "media"])}`;
    }
    if (ejercicio === "alertas") {
        return `<p><strong>${d.alertas}</strong> alertas ·
            <strong>${d.robots_en_riesgo.length}</strong> robots en riesgo
            ${d.descartar_absurdas ? "" : `<span class="aviso">sin filtrar el sensor descalibrado</span>`}</p>
            <p class="destacado">${d.robots_en_riesgo.join(", ") || "ninguno"}</p>
            ${tabla(d.filas.slice(0, 12).map(f => ({...f, inicio: hora(f.inicio), fin: hora(f.fin)})),
                    ["robot_id", "inicio", "fin", "temp_max"])}
            <p class="muted" style="margin-top:8px">Desmarca el filtro y compara: el sensor descalibrado
            inventa robots en riesgo que no lo están.</p>`;
    }
    if (ejercicio === "en_flujo") {
        return `<p><strong>${d.tandas}</strong> micro-tandas ·
            lecturas por tanda: ${d.lecturas_por_tanda.join(" · ")}</p>
            <p><strong>${d.total_filas}</strong> filas · <strong>${d.ventanas}</strong> ventanas</p>
            <p class="destacado">${d.nota}</p>
            ${tabla(d.filas.slice(0, 12).map(f => ({...f, inicio: hora(f.inicio), fin: hora(f.fin)})),
                    ["robot_id", "inicio", "fin", "media", "lecturas"])}`;
    }
    // tumbling y sliding
    return `<p><strong>${d.total_filas}</strong> filas · <strong>${d.ventanas}</strong> ventanas</p>
        ${tabla(d.filas.slice(0, 12).map(f => ({...f, inicio: hora(f.inicio), fin: hora(f.fin)})),
                Object.keys(d.filas[0] || {}).map(k => k === "inicio" || k === "fin" ? k : k))}`;
}

function ejercicio(id, num, titulo, desc, controles) {
    return `<div class="ej">
        <div class="ej-head">
            <span class="ej-num">${num}</span>
            <h3>${titulo}</h3>
        </div>
        <p>${desc}</p>
        <div class="ej-ctrl">${controles}
            <button class="run" onclick="correr('${id}')">Ejecutar</button>
        </div>
        <div class="ej-out" id="out-${id}"></div>
    </div>`;
}

function renderVentanas() {
    const abierto = !!(ESTADO.blocks || {}).windows;
    const aviso = abierto ? "" : `<div class="scaffold-msg" style="margin-bottom:18px">
        Este bloque está en modo <strong>ejercicio</strong>: los endpoints devuelven un aviso hasta que
        implementes las funciones en <code>windows_ex.py</code>.
        Para ver la solución, ábrelo desde el <a href="http://localhost:8080#config">Hub</a>.
    </div>`;

    return `
        <h1>Ventanas</h1>
        <p class="lead">En una tabla agrupas por robot o por almacén. En un flujo, además, por <em>cuándo</em>
        pasó cada cosa. Cómo cortes el eje del tiempo cambia la respuesta.</p>
        ${aviso}

        ${ejercicio("tumbling", "WIN-1", "Ventanas fijas (tumbling)",
            "Cortes que no se solapan: cada lectura cae en exactamente una ventana.",
            `<label>minutos <input type="number" id="p-tumbling" value="5" min="1" max="30"></label>`)}

        ${ejercicio("sliding", "WIN-2", "Ventanas deslizantes (sliding)",
            "Se solapan, así que la misma lectura entra en varias. Reaccionan antes, a cambio de contar de más.",
            `<label>ventana <input type="number" id="p-sliding-v" value="10" min="2" max="30"></label>
             <label>paso <input type="number" id="p-sliding-p" value="5" min="1" max="15"></label>`)}

        ${ejercicio("session", "WIN-3", "Ventanas de sesión",
            "Duran lo que dure la actividad. Si un robot calla más del gap, su sesión se cierra: así se ven los averiados.",
            `<label>gap (min) <input type="number" id="p-session" value="3" min="1" max="15"></label>`)}

        ${ejercicio("alertas", "WIN-4", "Riesgo térmico por ventana",
            "La pregunta del centro de control: qué robots pasan del umbral, y en qué ventana.",
            `<label><input type="checkbox" id="p-alertas" checked> descartar lecturas absurdas (1000 °C)</label>`)}

        ${ejercicio("comparar", "WIN-5", "Los tres cortes, lado a lado",
            "Misma telemetría, tres formas de partir el tiempo. Las tres respuestas son correctas y distintas.",
            `<label>minutos <input type="number" id="p-comparar" value="5" min="1" max="30"></label>`)}

        ${ejercicio("en_flujo", "WIN-6", "La misma agregación, como flujo",
            "Structured Streaming no es otra API: es la misma función con la fuente cambiada. El resultado debe coincidir con WIN-1.",
            `<label>lotes por tanda <input type="number" id="p-flujo" value="10" min="1" max="30"></label>`)}
    `;
}

function renderTardios() {
    const abierto = !!(ESTADO.blocks || {}).late;
    const aviso = abierto ? "" : `<div class="scaffold-msg" style="margin-bottom:18px">
        Este bloque está en modo <strong>ejercicio</strong>: implementa las funciones en
        <code>late_ex.py</code>, o ábrelo desde el <a href="http://localhost:8080#config">Hub</a>.
    </div>`;

    return `
        <h1>Datos tardíos</h1>
        <p class="lead">Un flujo no termina nunca. Si quieres cerrar una ventana y dar una respuesta,
        tienes que decidir <strong>hasta cuándo esperas</strong>. Eso es el watermark, y no es gratis.</p>
        ${aviso}

        ${ejercicio("retraso", "LATE-1", "Medir el retraso",
            "El dato solo dice cuándo se midió. Cuándo llegó lo dice el fichero que lo trajo.",
            "")}

        ${ejercicio("descartadas", "LATE-2", "Qué deja fuera un watermark",
            "La regla, calculada a mano: una lectura se pierde si su ventana ya se había cerrado cuando llegó.",
            `<label>watermark <input type="number" id="p-desc-w" value="0" min="0" max="15"></label>
             <label>ventana <input type="number" id="p-desc-v" value="2" min="1" max="15"></label>`)}

        ${ejercicio("con_watermark", "LATE-3", "El stream con watermark",
            "Cierra ventanas y libera estado, a cambio de descartar lo que llega demasiado tarde.",
            `<label>watermark <input type="number" id="p-cw-w" value="0" min="0" max="15"></label>
             <label>ventana <input type="number" id="p-cw-v" value="2" min="1" max="15"></label>`)}

        ${ejercicio("sin_watermark", "LATE-4", "El stream sin watermark",
            "No descarta nada… pero tampoco da nada por terminado, y el estado no se libera nunca.",
            `<label>ventana <input type="number" id="p-sw-v" value="2" min="1" max="15"></label>`)}

        ${ejercicio("late_comparar", "LATE-5", "Los dos, lado a lado",
            "Aquí se ve el intercambio completo: qué ganas al cerrar y qué pagas por ello.",
            `<label>watermark <input type="number" id="p-lc-w" value="0" min="0" max="15"></label>
             <label>ventana <input type="number" id="p-lc-v" value="2" min="1" max="15"></label>`)}

        ${ejercicio("barrido", "LATE-6", "Esperar frente a perder",
            "La curva de la decisión. Dónde cortarla no lo decide Spark.",
            `<label>ventana <input type="number" id="p-barrido" value="2" min="1" max="15"></label>`)}
    `;
}

function renderEstado() {
    const abierto = !!(ESTADO.blocks || {}).state;
    const aviso = abierto ? "" : `<div class="scaffold-msg" style="margin-bottom:18px">
        Este bloque está en modo <strong>ejercicio</strong>: implementa las funciones en
        <code>state_ex.py</code>, o ábrelo desde el <a href="http://localhost:8080#config">Hub</a>.
    </div>`;

    return `
        <h1>Estado y checkpoints</h1>
        <p class="lead">Un flujo tiene memoria. Las cuentas parciales entre tanda y tanda son el
        <strong>estado</strong>; el <strong>checkpoint</strong> es lo que permite retomar donde ibas
        cuando el proceso se para. Juntos son lo que hace que contar una vez signifique una vez.</p>
        ${aviso}

        ${ejercicio("dedup", "STATE-1", "Quitar los duplicados del reintento",
            "El emisor reenvía cuando no recibe confirmación, así que los duplicados llegan sí o sí. La clave es (robot, sensor, ts_evento).",
            "")}

        ${ejercicio("incremental", "STATE-2", "Ver crecer y liberarse el estado",
            "Sube mientras hay ventanas abiertas y baja cuando el watermark las cierra. Por eso un flujo infinito cabe en memoria finita.",
            `<label>lotes por tanda <input type="number" id="p-inc" value="5" min="1" max="30"></label>`)}

        ${ejercicio("a_mongo", "STATE-3", "Escribir a Mongo con foreachBatch",
            "Cada micro-tanda llega como un DataFrame normal, así que dentro se puede escribir donde sea. Con upsert, no insert.",
            "")}

        ${ejercicio("reanudar", "STATE-4", "Reanudar sin repetir trabajo",
            "Con checkpoint fijo: llama con «empezar de cero» marcado y luego sin marcar. La segunda debe leer 0 lecturas.",
            `<label><input type="checkbox" id="p-rean"> empezar de cero</label>`)}

        ${ejercicio("sin_memoria", "STATE-5", "Sin checkpoint, cada pasada rehace todo",
            "Lo mismo pero con un checkpoint nuevo cada vez. Compáralo con STATE-4 llamado dos veces.",
            "")}

        ${ejercicio("recuperacion", "STATE-6", "Recuperación tras una caída (demo)",
            "Procesa media jornada, se cae, y relanza con el mismo checkpoint. El total debe salir igual que en una pasada sin cortes.",
            "")}
    `;
}

// ============================================================
// Demo culminante
// ============================================================
function renderDemo() {
    return `
        <h1>¿Cuántos robots están en riesgo térmico?</h1>
        <p class="lead">La misma pregunta, los mismos datos, dos formas de responderla.
        En <strong>batch</strong> la respuesta es exacta y llega cuando la jornada ha terminado.
        En <strong>streaming</strong> hay respuesta a los pocos segundos, incompleta, que se va
        completando mientras la jornada sigue.</p>

        <div class="scenario" style="margin-top:20px">
            <h2>Esto es lo que falló en Rotterdam</h2>
            <p>El sobrecalentamiento estaba en los datos y el análisis por lotes lo habría
            encontrado. El problema es que lo encontró catorce horas después, cuando el robot
            ya había ardido. La pregunta no es cuál de las dos respuestas es correcta —lo son
            las dos— sino cuándo la necesitas.</p>
        </div>

        ${ejercicio("riesgo", "★", "Ejecutar la comparación",
            "Se responde la pregunta en tabla y en flujo, y se enseña cómo evoluciona la respuesta del stream tanda a tanda.",
            `<label>ventana <input type="number" id="p-demo-v" value="5" min="1" max="15"></label>
             <label>watermark <input type="number" id="p-demo-w" value="2" min="0" max="15"></label>
             <label>lotes por tanda <input type="number" id="p-demo-t" value="3" min="1" max="15"></label>`)}
    `;
}

function pintarDemo(d) {
    const b = d.batch, s = d.streaming;
    const max = Math.max(b.n, s.n, 1);

    const linea = s.evolucion.map(p => {
        const ancho = Math.round(100 * p.n / max);
        const nuevos = p.nuevos.length
            ? `<span class="dm-nuevos">+${p.nuevos.join(", ")}</span>` : "";
        return `<div class="dm-fila">
            <span class="dm-min">min ${p.minuto_jornada}</span>
            <span class="rx-track"><span class="rx-fill" style="width:${Math.max(1, ancho)}%"></span></span>
            <span class="dm-n">${p.n}</span>
            ${nuevos}
        </div>`;
    }).join("");

    return `
        <div class="dm-caras">
            <div class="dm-cara batch">
                <div class="dm-tit">Batch</div>
                <div class="dm-num">${b.n}</div>
                <div class="dm-sub">robots en riesgo</div>
                <div class="dm-cuando">${b.cuando}</div>
                <div class="dm-robots">${b.robots.join(" · ")}</div>
            </div>
            <div class="dm-cara stream">
                <div class="dm-tit">Streaming</div>
                <div class="dm-num">${s.n}</div>
                <div class="dm-sub">robots en riesgo</div>
                <div class="dm-cuando">${s.cuando}</div>
                <div class="dm-robots">${s.robots.join(" · ")}</div>
            </div>
        </div>

        <div class="dm-veredicto ${d.coinciden ? "ok" : "no"}">
            ${d.coinciden ? "✓ Las dos respuestas coinciden" : "✗ Las respuestas difieren"}
        </div>

        <h3 style="margin:22px 0 10px;color:#f0ead8;font-size:15px">
            Cómo evolucionó la respuesta del stream</h3>
        <div class="dm-linea">${linea}</div>

        <p class="dm-conclusion">${d.conclusion}</p>`;
}

// ============================================================
// Arranque
// ============================================================
async function cargar() {
    const el = document.getElementById("content");
    try {
        [ESTADO, EMISION] = await Promise.all([
            json("/api/streamlab/lab/status"),
            json("/api/streamlab/emision/status").catch(() => null),
        ]);
    } catch {
        el.innerHTML = `<h1>Sin conexión con el laboratorio</h1>
            <p class="lead">No se ha podido consultar el estado. Comprueba que el contenedor está arriba.</p>`;
        return;
    }
    pintarNav();
    const v = vista();
    el.innerHTML = v === "demo" ? renderDemo()
                 : v === "ventanas" ? renderVentanas()
                 : v === "tardios" ? renderTardios()
                 : v === "estado" ? renderEstado()
                 : renderInicio();
}

window.addEventListener("hashchange", cargar);
cargar();
