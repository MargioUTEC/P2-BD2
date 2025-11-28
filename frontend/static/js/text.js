// ======================================================
// BÚSQUEDA DE TEXTO
// ======================================================

const textQueryInput = document.getElementById("text-query");
const textMetadataExample = document.getElementById("text-sql-example");
const textKInput = document.getElementById("text-topk");
const textSearchBtn = document.getElementById("text-search-btn");
const textStatus = document.getElementById("text-status");
const textResultsDiv = document.getElementById("text-results");

textSearchBtn.addEventListener("click", async () => {
    const query = (textQueryInput.value || "").trim();
    const k = parseInt(textKInput.value || "5", 10);

    if (!query) {
        textStatus.textContent = "Ingresa una consulta textual.";
        return;
    }

    textSearchBtn.disabled = true;
    textStatus.textContent = `Consultando /api2/text/search?q=${query}&k=${k}...`;
    textResultsDiv.innerHTML = "";

    try {
        const url = `/api2/text/search?q=${encodeURIComponent(query)}&k=${k}`;

        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`Error HTTP ${resp.status}`);

        const data = await resp.json();

        await renderTextResults(data);

        if (!data || data.length === 0) {
            textStatus.textContent = "Sin resultados.";
        } else {
            textStatus.textContent = `Mostrando ${data.length} resultados.`;
        }

    } catch (err) {
        console.error(err);
        textStatus.textContent = `Error: ${err}`;
    } finally {
        textSearchBtn.disabled = false;
    }
});

function updateTextSqlExample() {
    const rawQuery = (textQueryInput.value || "").trim();
    const k = parseInt(textKInput.value || "5", 10);

    // Si está vacío, pon un ejemplo cualquiera:
    const safeQuery = rawQuery
        ? rawQuery.replace(/'/g, "''")
        : "amor en tiempos de guerra";

    const example =
`SELECT title, artist, lyric
FROM Audio
WHERE lyric @@ '${safeQuery}'
LIMIT ${k};`;

    textMetadataExample.value = example;
}

textQueryInput.addEventListener("input", updateTextSqlExample);
textKInput.addEventListener("input", updateTextSqlExample);

updateTextSqlExample();

async function renderTextResults(results) {
    textResultsDiv.innerHTML = "";

    if (!results || results.length === 0) {
        textResultsDiv.innerHTML =
            `<p style="color:#aaa;">Sin resultados.</p>`;
        return;
    }

    for (const res of results) {
        const card = document.createElement("div");
        card.className = "result-card";

        card.innerHTML = `
            <div class="result-card-header">
                <div>
                    <div class="result-title">${escapeHtml(res.title || "Título no disponible")}</div>
                    <div class="result-artist">Artista: ${escapeHtml(res.artist || "Desconocido")}</div>
                    <div class="result-genre">Género: ${escapeHtml(res.genre || "-")}</div>
                    <div class="result-album">Álbum: ${escapeHtml(res.album || "-")}</div>
                    <div class="result-playlist">Playlist: ${escapeHtml(res.playlist || "-")}</div>
                </div>
                <span class="result-badge">🔎 Texto</span>
            </div>

            <div class="result-score">Score: ${Number(res.score || 0).toFixed(3)}</div>

            <div class="lyrics-snippet">
                ${escapeHtml(res.lyrics_excerpt || "")}...
            </div>

            <div class="result-time">
                Tiempo: ${Number(res.elapsed_ms || 0).toFixed(2)} ms
            </div>

            <div class="result-trackid">Track ID: ${escapeHtml(res.track_id || "")}</div>
        `;

        textResultsDiv.appendChild(card);
    }
}

// ======================================================
// HTML SAFE
// ======================================================

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}
