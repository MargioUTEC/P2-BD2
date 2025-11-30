// ======================================================
// BÚSQUEDA DE TEXTO
//  - Modo simple: q directo + k
//  - Modo SQL: parsea SELECT / WHERE lyric @@ '...' / LIMIT
// ======================================================

document.addEventListener("DOMContentLoaded", () => {
    const API_BASE = window.API_BASE_URL || "";


    // Elementos comunes
    const textStatus     = document.getElementById("text-status");
    const textResultsDiv = document.getElementById("text-results");

    // Modo simple
    const textQueryInput = document.getElementById("text-query");
    const textTopKInput  = document.getElementById("text-topk");
    const textSimpleBtn  = document.getElementById("text-simple-btn");

    // Modo SQL
    const textSqlInput   = document.getElementById("text-sql-input");
    const textSqlBtn     = document.getElementById("text-search-btn");

    // columnas seleccionadas (solo aplica al modo SQL)
    let textSelectedColumns = null; // null → mostrar todo; ["*"] → todo; ["title","artist"] → solo esas

    // ------------------------------------------------------
    // Helpers de parseo de SQL
    // ------------------------------------------------------

    function parseTextSelectColumns(sqlText) {
        if (!sqlText) return null;

        const lower = sqlText.toLowerCase();
        const idxSel = lower.indexOf("select");
        const idxFrom = lower.indexOf("from");

        if (idxSel === -1 || idxFrom === -1 || idxFrom <= idxSel) {
            return null;
        }

        const between = sqlText.slice(idxSel + 6, idxFrom).trim();
        if (!between) return null;

        const parts = between
            .split(",")
            .map((p) => p.trim())
            .filter(Boolean);

        if (!parts.length) return null;

        const cols = parts.map((p) =>
            p
                .replace(/\s+as\s+.*$/i, "") // quitar "AS alias"
                .trim()
                .toLowerCase()
        );

        if (cols.includes("*")) return ["*"];
        return cols;
    }

    function extractLyricQueryFromSql(sqlText) {
        if (!sqlText) return "";

        const lower = sqlText.toLowerCase();
        const idxWhere = lower.indexOf("where");
        if (idxWhere === -1) return "";

        const wherePart = sqlText.slice(idxWhere); // desde WHERE ...
        const regex = /lyric\s*@@\s*(['"])(.*?)\1/i;
        const m = regex.exec(wherePart);
        if (!m) return "";

        return m[2].trim();
    }

    function extractTextLimitFromSql(sqlText, fallback) {
        const match = (sqlText || "").match(/limit\s+(\d+)/i);
        if (!match) return fallback;
        const n = parseInt(match[1], 10);
        if (Number.isNaN(n) || n <= 0) return fallback;
        return n;
    }

    function shouldShowTextField(fieldName) {
        if (!textSelectedColumns || textSelectedColumns.length === 0) return true;
        if (textSelectedColumns.includes("*")) return true;

        const f = String(fieldName || "").toLowerCase();
        return textSelectedColumns.includes(f);
    }

    function escapeHtml(str) {
        if (str === null || str === undefined) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    // ======================================================
    // Render de resultados (común a ambos modos)
    // ======================================================

    async function renderTextResults(results) {
        if (!textResultsDiv) return;

        textResultsDiv.innerHTML = "";

        if (!results || results.length === 0) {
            textResultsDiv.innerHTML =
                `<p style="color:#aaa;">Sin resultados.</p>`;
            return;
        }

        for (const res of results) {
            const card = document.createElement("div");
            card.className = "result-card";

            // Campos típicos del backend:
            // title, artist, genre, album, playlist, lyrics_excerpt, elapsed_ms, track_id, score

            let metaHtml = "";

            if (shouldShowTextField("title")) {
                metaHtml += `<div class="result-title">${escapeHtml(res.title || "Título no disponible")}</div>`;
            }
            if (shouldShowTextField("artist")) {
                metaHtml += `<div class="result-artist">Artista: ${escapeHtml(res.artist || "Desconocido")}</div>`;
            }
            if (shouldShowTextField("genre")) {
                metaHtml += `<div class="result-genre">Género: ${escapeHtml(res.genre || "-")}</div>`;
            }
            if (shouldShowTextField("album")) {
                metaHtml += `<div class="result-album">Álbum: ${escapeHtml(res.album || "-")}</div>`;
            }
            if (shouldShowTextField("playlist")) {
                metaHtml += `<div class="result-playlist">Playlist: ${escapeHtml(res.playlist || "-")}</div>`;
            }

            const wantsLyrics =
                shouldShowTextField("lyric") ||
                shouldShowTextField("lyrics") ||
                shouldShowTextField("lyrics_excerpt");

            let lyricsHtml = "";
            if (wantsLyrics && res.lyrics_excerpt) {
                lyricsHtml = `
                    <div class="lyrics-snippet">
                        ${escapeHtml(res.lyrics_excerpt)}...
                    </div>
                `;
            }

            if (!metaHtml) {
                metaHtml = `<div class="result-title">${escapeHtml(res.title || "Resultado")}</div>`;
            }

            const showTrackIdLine = shouldShowTextField("track_id");
            const showTimeLine    = shouldShowTextField("elapsed_ms") || shouldShowTextField("time");

            card.innerHTML = `
                <div class="result-card-header">
                    <div>
                        ${metaHtml}
                    </div>
                    <span class="result-badge">🔎 Texto</span>
                </div>

                <div class="result-score">
                    Score: ${Number(res.score || 0).toFixed(3)}
                </div>

                ${lyricsHtml}

                ${
                    showTimeLine
                        ? `<div class="result-time">Tiempo: ${Number(res.elapsed_ms || 0).toFixed(2)} ms</div>`
                        : ""
                }

                ${
                    showTrackIdLine
                        ? `<div class="result-trackid">Track ID: ${escapeHtml(res.track_id || "")}</div>`
                        : ""
                }
            `;

            textResultsDiv.appendChild(card);
        }
    }

    // ======================================================
    // MODO SIMPLE
    // ======================================================

    if (textSimpleBtn && textQueryInput && textTopKInput && textStatus && textResultsDiv) {
        textSimpleBtn.addEventListener("click", async () => {
            const qRaw = (textQueryInput.value || "").trim();
            if (!qRaw) {
                textStatus.textContent = "Escribe un texto para buscar.";
                return;
            }

            let k = parseInt(textTopKInput.value || "10", 10);
            if (!Number.isFinite(k) || k <= 0) k = 10;

            // En modo simple mostramos todo (no respetamos SELECT)
            textSelectedColumns = null;

            textSimpleBtn.disabled = true;
            textStatus.textContent = `Consultando ${API_BASE}/api2/text/search?q=${qRaw}&k=${k}...`;
            textResultsDiv.innerHTML = "";

            try {
                const url = `${API_BASE}/api2/text/search?q=${encodeURIComponent(qRaw)}&k=${k}`;
                const resp = await fetch(url);
                if (!resp.ok) throw new Error(`Error HTTP ${resp.status}`);

                const data = await resp.json();
                await renderTextResults(data);

                if (!data || data.length === 0) {
                    textStatus.textContent = "Sin resultados.";
                } else {
                    textStatus.textContent = `Mostrando ${data.length} resultados para: "${qRaw}".`;
                }
            } catch (err) {
                console.error(err);
                textStatus.textContent = `Error: ${err}`;
            } finally {
                textSimpleBtn.disabled = false;
            }
        });
    }

    // ======================================================
    // MODO SQL
    // ======================================================

    if (textSqlBtn && textSqlInput && textStatus && textResultsDiv) {
        textSqlBtn.addEventListener("click", async () => {
            const sqlText = (textSqlInput.value || "").trim();
            if (!sqlText) {
                textStatus.textContent = "Escribe una consulta SQL.";
                return;
            }

            // columnas del SELECT
            textSelectedColumns = parseTextSelectColumns(sqlText);

            // query de texto desde WHERE lyric @@ '...'
            let q = extractLyricQueryFromSql(sqlText);
            if (!q) {
                // fallback: si no encontramos lyric @@, usamos todo el SQL como query
                q = sqlText;
            }

            // LIMIT → k
            let k = extractTextLimitFromSql(sqlText, 10);

            textSqlBtn.disabled = true;
            textStatus.textContent = `Consultando ${API_BASE}/api2/text/search?q=${q}&k=${k}...`;
            textResultsDiv.innerHTML = "";

            try {
                const url = `${API_BASE}/api2/text/search?q=${encodeURIComponent(q)}&k=${k}`;
                const resp = await fetch(url);
                if (!resp.ok) throw new Error(`Error HTTP ${resp.status}`);

                const data = await resp.json();
                await renderTextResults(data);

                if (!data || data.length === 0) {
                    textStatus.textContent = "Sin resultados.";
                } else {
                    textStatus.textContent = `Mostrando ${data.length} resultados para: "${q}".`;
                }
            } catch (err) {
                console.error(err);
                textStatus.textContent = `Error: ${err}`;
            } finally {
                textSqlBtn.disabled = false;
            }
        });
    }
});
