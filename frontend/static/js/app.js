// ======================================================
// Utilidades
// ======================================================
const audioOriginalDiv = document.getElementById("audio-original");

function renderExternalOriginalAudio(file) {
    if (!audioOriginalDiv) return;
    audioOriginalDiv.innerHTML = "";

    const blobUrl = URL.createObjectURL(file);

    audioOriginalDiv.innerHTML = `
        <div class="audio-original-card">
            <p><strong>Audio de consulta (archivo local):</strong> ${file.name}</p>
            <audio controls src="${blobUrl}" style="width: 100%; margin-top: 8px;"></audio>
        </div>
    `;
}

function isFmaFileNameStem(stem) {
    const s = String(stem || "").trim();
    // Números de 1 a 6 dígitos: 1, 23, 34996, 000141, etc.
    return /^\d{1,6}$/.test(s);
}

function normalizeTid(tid) {
    const s = (tid || "").trim();
    if (/^\d+$/.test(s)) {
        // Zero-pad siempre a 6 dígitos (como en tu backend)
        return s.padStart(6, "0");
    }
    return s;
}

function setActiveTab(tabId) {
    document.querySelectorAll(".tab-button").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.tab === tabId);
    });
    document.querySelectorAll(".tab-content").forEach((sec) => {
        sec.classList.toggle("active", sec.id === tabId);
    });
}

// HTML safe
function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

// ======================================================
// Tabs
// ======================================================

document.querySelectorAll(".tab-button").forEach((btn) => {
    btn.addEventListener("click", () => {
        const tabId = btn.dataset.tab;
        setActiveTab(tabId);
    });
});

// ======================================================
// Búsqueda por Audio
// ======================================================

const audioFileInput = document.getElementById("audio-file");
const audioTopKInput = document.getElementById("audio-topk");
const audioSqlTextarea = document.getElementById("audio-sql-example");
const audioSearchBtn = document.getElementById("audio-search-btn");
const audioStatus = document.getElementById("audio-status");
const audioResultsDiv = document.getElementById("audio-results");

// 🔹 NUEVO: input para filtro de metadata (si existe en tu HTML)
const audioMetadataFilterInput = document.getElementById("audio-metadata-filter");

// 🔹 NUEVO: columnas seleccionadas en el SELECT del textarea de audio
let audioSelectedColumns = null; // null → mostrar todo; ["*"] → todo; ["title","artist"] → solo esas

/**
 * Actualiza el ejemplo SQL mostrado en el textarea,
 * combinando similitud de audio + filtro de metadata (si existe).
 */
function updateAudioSqlExample(trackId, topK, fileName) {
    const limit = topK || 8;
    const audioRef = fileName || (trackId ? `${trackId}.mp3` : "ruta/a/tu/audio.extension");

    if (!audioSqlTextarea) return;

    audioSqlTextarea.value =
        "SELECT track_id, title, artist, genre, year\n" +
        "FROM Multimedia\n" +
        `WHERE audio_sim <-> '${audioRef}'\n` +
        "-- Puedes añadir filtros de metadata, por ejemplo:\n" +
        "--   AND genre = \"Electronic\" AND year >= 2010\n" +
        `LIMIT ${limit};`;
}

/**
 * Extrae SOLO la parte de metadata del WHERE del SQL de audio:
 *   - Ignora SELECT, FROM, LIMIT
 *   - Ignora la parte de audio_sim <-> ...
 *   - Devuelve únicamente la conjunción de condiciones sobre metadata.
 */
function extractMetadataConditionFromSql(sqlText) {
    const lines = (sqlText || "").split(/\r?\n/);
    const metaParts = [];
    let seenWhere = false;

    for (let line of lines) {
        let t = line.trim();
        if (!t || t.startsWith("--")) continue;

        const lower = t.toLowerCase();

        // Ignorar SELECT / FROM / LIMIT
        if (lower.startsWith("select") || lower.startsWith("from") || lower.startsWith("limit")) {
            continue;
        }

        // WHERE ...
        if (lower.startsWith("where")) {
            seenWhere = true;

            // Caso 1: WHERE solo metadata (sin audio_sim)
            if (!lower.includes("audio_sim")) {
                const cond = t.replace(/^where\s+/i, "").trim();
                if (cond) metaParts.push(cond);
                continue;
            }

            // Caso 2: WHERE audio_sim <-> ... [AND ...]
            const andIndex = lower.indexOf(" and ");
            if (andIndex !== -1) {
                const origIndex = t.toLowerCase().indexOf(" and ");
                const cond = t.slice(origIndex + 4).trim(); // después de AND
                if (cond) metaParts.push(cond);
            }
            continue;
        }

        // Líneas posteriores que empiezan con AND / OR
        if (seenWhere && (lower.startsWith("and ") || lower.startsWith("or "))) {
            const cond = t.replace(/^(and|or)\s+/i, "").trim();
            if (cond) metaParts.push(cond);
            continue;
        }
    }

    if (!metaParts.length) return "";
    return metaParts.join(" AND ");
}

/**
 * 🔹 NUEVO:
 * Parsea la lista de columnas del SELECT en el textarea de audio.
 *
 * Ej:
 *   SELECT track_id, title, artist FROM Multimedia ...
 *   → ["track_id", "title", "artist"]
 *
 *   SELECT * FROM ...
 *   → ["*"]
 *
 * Si no encuentra SELECT/FROM válidos, devuelve null → mostrar todo.
 */
function parseSelectColumns(sqlText) {
    if (!sqlText) return null;

    const lower = sqlText.toLowerCase();
    const idxSel = lower.indexOf("select");
    const idxFrom = lower.indexOf("from");

    if (idxSel === -1 || idxFrom === -1 || idxFrom <= idxSel) {
        return null;
    }

    // Entre SELECT y FROM
    const between = sqlText.slice(idxSel + 6, idxFrom).trim();
    if (!between) return null;

    const parts = between.split(",").map((p) => p.trim()).filter(Boolean);
    if (!parts.length) return null;

    const cols = parts.map((p) =>
        p
            .replace(/\s+as\s+.*$/i, "") // quitar alias "AS ..."
            .trim()
            .toLowerCase()
    );

    if (cols.includes("*")) return ["*"];
    return cols;
}

/**
 * 🔹 NUEVO:
 * Decide si mostrar un campo de metadata en las tarjetas de audio
 * según lo que haya en el SELECT del textarea de audio.
 *
 * - Si audioSelectedColumns es null → mostrar todo.
 * - Si incluye "*" → mostrar todo.
 * - Si tiene ["title","artist"] → solo esos.
 */
function shouldShowAudioField(fieldName) {
    if (!audioSelectedColumns || audioSelectedColumns.length === 0) return true;
    if (audioSelectedColumns.includes("*")) return true;
    return audioSelectedColumns.includes(String(fieldName).toLowerCase());
}

// Cuando se selecciona archivo, solo actualizamos el ejemplo SQL
if (audioFileInput) {
    audioFileInput.addEventListener("change", () => {
        const file = audioFileInput.files[0];
        const topK = parseInt(audioTopKInput.value || "8", 10);

        if (!file) {
            updateAudioSqlExample("", topK, "");
            return;
        }

        const name = file.name || "";
        const stem = name.includes(".") ? name.slice(0, name.lastIndexOf(".")) : name;
        const tid = normalizeTid(stem);

        updateAudioSqlExample(tid, topK, file.name);
    });
}

// ======================================================
// Extraer LIMIT del SQL
// ======================================================
function extractLimitFromSql(sqlText, fallback) {
    const match = (sqlText || "").match(/limit\s+(\d+)/i);
    if (!match) return fallback;
    const n = parseInt(match[1], 10);
    if (Number.isNaN(n) || n <= 0) return fallback;
    return n;
}

// ======================================================
// Handler de búsqueda por audio (con fusión + filtro)
// ======================================================
if (audioSearchBtn) {
    audioSearchBtn.addEventListener("click", async () => {
        const file = audioFileInput.files[0];
        let topK = parseInt(audioTopKInput.value || "8", 10);
        const alpha = 0.2;

        if (!file) {
            audioStatus.textContent = "Selecciona un archivo de audio primero.";
            return;
        }

        const name = file.name || "";
        const stem = name.includes(".") ? name.slice(0, name.lastIndexOf(".")) : name;
        const isFma = isFmaFileNameStem(stem);  // <- ¿parece un track de FMA?
        const rawTid = stem;
        const tid = normalizeTid(rawTid);

        // Si es FMA pero falló el normalize, no seguimos
        if (isFma && !tid) {
            audioStatus.textContent = "No se pudo extraer un track_id válido.";
            return;
        }

        // 1) Leer la consulta SQL completa del textarea
        const sqlText = audioSqlTextarea ? (audioSqlTextarea.value || "") : "";

        // 2) Extraer solo la parte de metadata (WHERE sin audio_sim)
        const metadataQuery = extractMetadataConditionFromSql(sqlText);

        // 3) 🔹 NUEVO: guardar columnas del SELECT para las tarjetas
        audioSelectedColumns = parseSelectColumns(sqlText);

        // 4) Extraer LIMIT del SQL y usarlo como topK
        topK = extractLimitFromSql(sqlText, topK);
        audioTopKInput.value = String(topK); // sincronizar con el input visible

        audioSearchBtn.disabled = true;
        audioResultsDiv.innerHTML = "";

        let rawResults = [];
        try {
            if (isFma) {
                // ==============================
                // MODO FMA: usamos /api/fusion/{track_id}
                // ==============================
                const params = new URLSearchParams({
                    k: String(topK),
                    alpha: String(alpha),
                });

                if (metadataQuery) {
                    params.set("q", metadataQuery);
                }

                const url = `/api/fusion/${tid}?${params.toString()}`;
                audioStatus.textContent = `Consultando ${url}...`;

                const searchResp = await fetch(url);
                if (!searchResp.ok) {
                    throw new Error(`Error HTTP ${searchResp.status}`);
                }

                rawResults = await searchResp.json();
                if (!Array.isArray(rawResults)) {
                    throw new Error("Respuesta inesperada del endpoint de fusión.");
                }

                // Audio original: el track de FMA
                await renderOriginalAudio(tid);
            } else {
                // ==============================
                // MODO AUDIO EXTERNO: usamos /api/audio/search_file
                // ==============================
                const url = `/api/audio/search_file?k=${topK}`;
                audioStatus.textContent = `Consultando ${url}...`;

                const formData = new FormData();
                formData.append("file", file);

                const searchResp = await fetch(url, {
                    method: "POST",
                    body: formData,
                });
                if (!searchResp.ok) {
                    throw new Error(`Error HTTP ${searchResp.status}`);
                }

                rawResults = await searchResp.json();
                if (!Array.isArray(rawResults)) {
                    throw new Error("Respuesta inesperada de /api/audio/search_file.");
                }

                // Audio original: el archivo local subido
                renderExternalOriginalAudio(file);
            }

            // Enriquecer metadata con /api/metadata/track/{id}
            const enriched = [];
            for (const item of rawResults) {
                const rTid = String(item.track_id || "");
                const score = Number(item.score || 0);

                let title = "", artist = "", genre = "", year = "";

                try {
                    const metaResp = await fetch(`/api/metadata/track/${rTid}`);
                    if (metaResp.ok) {
                        const meta = await metaResp.json();
                        const data = meta.data || {};
                        title  = data.title  || "";
                        artist = data.artist || "";
                        genre  = data.genre  || "";
                        year   = data.year   || "";
                    }
                } catch (err) {
                    console.warn("Error al obtener metadata para", rTid, err);
                }

                if (!title) title = `Track ${rTid}`;
                if (!artist) artist = "Artista desconocido";

                enriched.push({ track_id: rTid, score, title, artist, genre, year });
            }

            renderAudioResults(enriched);

            // Mensaje final
            if (isFma) {
                audioStatus.textContent =
                    `Mostrando ${enriched.length} resultados similares a ${tid}` +
                    (metadataQuery ? ` (filtrados por: ${metadataQuery}).` : ".");
            } else {
                audioStatus.textContent =
                    `Mostrando ${enriched.length} resultados similares al archivo subido.` +
                    (metadataQuery ? " (Por ahora, los filtros SQL solo se aplican a audios FMA)." : "");
            }

        } catch (err) {
            console.error(err);
            audioStatus.textContent = `Error consultando API: ${err}`;
        } finally {
            audioSearchBtn.disabled = false;
        }
    });
}

// ======================================================
// Renderizar resultados (con audio, respetando SELECT)
// ======================================================

function renderAudioResults(results) {
    audioResultsDiv.innerHTML = "";
    if (!results || results.length === 0) {
        audioResultsDiv.innerHTML = `<p style="color:#9ca3af;font-size:0.9rem;">Sin resultados.</p>`;
        return;
    }

    for (const res of results) {
        const card = document.createElement("div");
        card.className = "result-card";

        // Construimos solo los campos de metadata que el SELECT permita
        let metaHtml = "";

        if (shouldShowAudioField("title")) {
            metaHtml += `<div class="result-title">${escapeHtml(res.title)}</div>`;
        }
        if (shouldShowAudioField("artist")) {
            metaHtml += `<div class="result-artist">Artista: ${escapeHtml(res.artist)}</div>`;
        }
        if (shouldShowAudioField("genre")) {
            metaHtml += `<div class="result-genre">Género: ${escapeHtml(res.genre)}</div>`;
        }
        if (shouldShowAudioField("year")) {
            metaHtml += `<div class="result-year">Año: ${escapeHtml(res.year)}</div>`;
        }

        // Si el usuario pidió algo raro (solo track_id, por ejemplo), y metaHtml queda vacío,
        // mostramos al menos un título genérico.
        if (!metaHtml) {
            metaHtml = `<div class="result-title">Track ${escapeHtml(res.track_id)}</div>`;
        }

        const showTrackIdLine = shouldShowAudioField("track_id");

        card.innerHTML = `
            <div class="result-card-header">
                <div>
                    ${metaHtml}
                </div>
                <span class="result-badge">🎵 Audio</span>
            </div>

            <div class="result-score">Score: ${res.score.toFixed(3)}</div>
            ${
                showTrackIdLine
                    ? `<div class="result-trackid">Track ID: ${escapeHtml(res.track_id)}</div>`
                    : ""
            }

            <audio controls style="margin-top:10px; width:100%;">
                <source src="/api/audio/file/${escapeHtml(res.track_id)}" type="audio/mpeg">
                Tu navegador no soporta audio.
            </audio>
        `;

        audioResultsDiv.appendChild(card);
    }
}

// ======================================================
// Renderizar Audio Original + Metadata
// (para el original mantenemos siempre toda la metadata)
// ======================================================

async function renderOriginalAudio(trackId) {
    const container = document.getElementById("audio-original");

    // 1) Obtener metadata del track original
    let title = "";
    let artist = "";
    let genre = "";
    let year = "";

    try {
        const metaResp = await fetch(`/api/metadata/track/${trackId}`);
        if (metaResp.ok) {
            const meta = await metaResp.json();
            const data = meta.data || {};

            title  = data.title  || `Track ${trackId}`;
            artist = data.artist || "Artista desconocido";
            genre  = data.genre  || "";
            year   = data.year   || "";
        }
    } catch (err) {
        console.warn("Error obteniendo metadata del original:", err);
        title = `Track ${trackId}`;
        artist = "Artista desconocido";
    }

    // 2) Render del card del audio original
    container.innerHTML = `
        <div class="result-card" style="border: 2px solid #3b82f6;">
            <div class="result-card-header">
                <div>
                    <div class="result-title">${escapeHtml(title)}</div>
                    <div class="result-artist">Artista: ${escapeHtml(artist)}</div>
                    <div class="result-genre">Género: ${escapeHtml(genre)}</div>
                    <div class="result-year">Año: ${escapeHtml(year)}</div>
                </div>
                <span class="result-badge">🎧 Original</span>
            </div>

            <div class="result-trackid">Track ID: ${escapeHtml(trackId)}</div>

            <audio controls style="margin-top:10px; width:100%;">
                <source src="/api/audio/file/${escapeHtml(trackId)}" type="audio/mpeg">
                Tu navegador no soporta audio.
            </audio>
        </div>
    `;
}

// ======================================================
// Búsqueda directa de metadata por track_id
// ======================================================

const metaTrackInput = document.getElementById("meta-trackid");
const metadataBtn = document.getElementById("metadata-search-btn");
const metadataStatus = document.getElementById("metadata-status");
const metadataResultDiv = document.getElementById("metadata-result");

if (metadataBtn) {
    metadataBtn.addEventListener("click", async () => {
        const rawTid = (metaTrackInput.value || "").trim();
        if (!rawTid) {
            metadataStatus.textContent = "Ingresa un track_id.";
            return;
        }

        const tid = normalizeTid(rawTid);
        metadataStatus.textContent = `Consultando /api/metadata/track/${tid}...`;
        metadataResultDiv.innerHTML = "";
        metadataBtn.disabled = true;

        try {
            const resp = await fetch(`/api/metadata/track/${tid}`);
            if (resp.status === 404) {
                metadataStatus.textContent = `No se encontró metadata para ${tid}.`;
                metadataResultDiv.innerHTML =
                    `<p style="color:#fca5a5;">Sin resultados para ${tid}.</p>`;
                return;
            }
            if (!resp.ok) {
                throw new Error(`Error HTTP ${resp.status}`);
            }

            const meta = await resp.json();
            const data = meta.data || {};

            metadataResultDiv.innerHTML = `
                <div class="metadata-row">
                    <span class="metadata-label">Track ID:</span> ${escapeHtml(meta.track_id || tid)}
                </div>
                <div class="metadata-row">
                    <span class="metadata-label">Título:</span> ${escapeHtml(data.title || "")}
                </div>
                <div class="metadata-row">
                    <span class="metadata-label">Artista:</span> ${escapeHtml(data.artist || "")}
                </div>
                <div class="metadata-row">
                    <span class="metadata-label">Género:</span> ${escapeHtml(data.genre || "")}
                </div>
                <div class="metadata-row">
                    <span class="metadata-label">Año:</span> ${escapeHtml(data.year || "")}
                </div>
            `;

            metadataStatus.textContent = "Metadata cargada correctamente.";
        } catch (err) {
            console.error(err);
            metadataStatus.textContent = `Error consultando metadata: ${err}`;
            metadataResultDiv.innerHTML = "";
        } finally {
            metadataBtn.disabled = false;
        }
    });
}

// ======================================================
// Consulta SQL sobre metadata (parser propio)
// ======================================================

const metadataSqlInput = document.getElementById("metadata-sql-input");
const metadataSqlBtn = document.getElementById("metadata-sql-btn");
const metadataSqlStatus = document.getElementById("metadata-sql-status");
const metadataSqlResults = document.getElementById("metadata-sql-results");

if (metadataSqlBtn) {
    metadataSqlBtn.addEventListener("click", async () => {
        if (!metadataSqlInput || !metadataSqlStatus || !metadataSqlResults) return;

        const queryText = (metadataSqlInput.value || "").trim();
        if (!queryText) {
            metadataSqlStatus.textContent = "Escribe una consulta SQL.";
            metadataSqlResults.innerHTML = "";
            return;
        }

        metadataSqlBtn.disabled = true;
        metadataSqlStatus.textContent = "Ejecutando consulta...";
        metadataSqlResults.innerHTML = "";

        try {
            const resp = await fetch("/api/metadata/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: queryText }),
            });

            if (!resp.ok) {
                const errData = await resp.json().catch(() => ({}));
                throw new Error(errData.detail || `Error HTTP ${resp.status}`);
            }

            const data = await resp.json();
            const rows = data.rows || [];

            if (!Array.isArray(rows) || rows.length === 0) {
                metadataSqlResults.innerHTML = "<p>Sin resultados.</p>";
                metadataSqlStatus.textContent = "Consulta ejecutada (0 filas).";
                return;
            }

            // Inferir columnas a partir de la primera fila
            const cols = Object.keys(rows[0]);

            let html = "<div class='card'><table class='sql-table'><thead><tr>";
            for (const c of cols) {
                html += `<th>${escapeHtml(c)}</th>`;
            }
            html += "</tr></thead><tbody>";

            for (const row of rows) {
                html += "<tr>";
                for (const c of cols) {
                    html += `<td>${escapeHtml(row[c])}</td>`;
                }
                html += "</tr>";
            }

            html += "</tbody></table></div>";
            metadataSqlResults.innerHTML = html;

            const finalSql = data.sql || "";
            if (finalSql) {
                metadataSqlStatus.textContent = `Consulta ejecutada (${rows.length} filas). SQL final: ${finalSql}`;
            } else {
                metadataSqlStatus.textContent = `Consulta ejecutada (${rows.length} filas).`;
            }
        } catch (err) {
            console.error(err);
            metadataSqlStatus.textContent = `Error en la consulta: ${err}`;
            metadataSqlResults.innerHTML = "";
        } finally {
            metadataSqlBtn.disabled = false;
        }
    });
}
