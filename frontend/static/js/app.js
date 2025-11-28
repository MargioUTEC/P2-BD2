// ======================================================
// Utilidades
// ======================================================

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

function updateAudioSqlExample(trackId, topK) {
    if (!trackId) {
        audioSqlTextarea.value =
            "SELECT id, title\n" +
            "FROM Audio\n" +
            "WHERE audio_sim <-> 'ruta/a/tu/audio.extension'\n" +
            `LIMIT ${topK};`;
        return;
    }

    audioSqlTextarea.value =
        "SELECT id, title\n" +
        "FROM Audio\n" +
        `WHERE audio_sim <-> '${trackId}'\n` +
        `LIMIT ${topK};`;
}

audioFileInput.addEventListener("change", () => {
    const file = audioFileInput.files[0];
    const topK = parseInt(audioTopKInput.value || "8", 10);

    if (!file) {
        updateAudioSqlExample("", topK);
        return;
    }

    const name = file.name || "";
    const stem = name.includes(".") ? name.slice(0, name.lastIndexOf(".")) : name;
    const tid = normalizeTid(stem);

    updateAudioSqlExample(tid, topK);
});


audioSearchBtn.addEventListener("click", async () => {
    const file = audioFileInput.files[0];
    const topK = parseInt(audioTopKInput.value || "8", 10);
    const alpha = 0.7;

    if (!file) {
        audioStatus.textContent = "Selecciona un archivo de audio primero.";
        return;
    }

    const name = file.name || "";
    const stem = name.includes(".") ? name.slice(0, name.lastIndexOf(".")) : name;
    const rawTid = stem;
    const tid = normalizeTid(rawTid);

    if (!tid) {
        audioStatus.textContent = "No se pudo extraer un track_id válido.";
        return;
    }

    updateAudioSqlExample(tid, topK);

    audioSearchBtn.disabled = true;
    audioStatus.textContent = `Consultando /api/fusion/${tid}?k=${topK}&alpha=${alpha}...`;
    audioResultsDiv.innerHTML = "";

    try {
        const url = `/api/fusion/${tid}?k=${topK}&alpha=${alpha}`;
        const searchResp = await fetch(url);

        if (!searchResp.ok) {
            throw new Error(`Error HTTP ${searchResp.status}`);
        }

        const rawResults = await searchResp.json();
        if (!Array.isArray(rawResults)) {
            throw new Error("Respuesta inesperada del endpoint de fusión.");
        }

        // Enriquecer metadata
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

await renderOriginalAudio(tid);
renderAudioResults(enriched);

audioStatus.textContent = `Mostrando ${enriched.length} resultados similares a ${tid}.`;

    } catch (err) {
        console.error(err);
        audioStatus.textContent = `Error consultando API: ${err}`;
    } finally {
        audioSearchBtn.disabled = false;
    }
});

// ======================================================
// Renderizar resultados (ACTUALIZADO CON AUDIO)
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

        card.innerHTML = `
            <div class="result-card-header">
                <div>
                    <div class="result-title">${escapeHtml(res.title)}</div>
                    <div class="result-artist">Artista: ${escapeHtml(res.artist)}</div>
                    <div class="result-genre">Género: ${escapeHtml(res.genre)}</div>
                    <div class="result-year">Año: ${escapeHtml(res.year)}</div>
                </div>
                <span class="result-badge">🎵 Audio</span>
            </div>

            <div class="result-score">Score: ${res.score.toFixed(3)}</div>
            <div class="result-trackid">Track ID: ${escapeHtml(res.track_id)}</div>

            <!-- 🎧 AUDIO PLAYER -->
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


// HTML safe
function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

// ======================================================
// Búsqueda directa de metadata
// ======================================================

const metaTrackInput = document.getElementById("meta-trackid");
const metadataBtn = document.getElementById("metadata-search-btn");
const metadataStatus = document.getElementById("metadata-status");
const metadataResultDiv = document.getElementById("metadata-result");

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
