import sys
import time
from PyQt5 import QtWidgets, QtCore, QtGui
from pathlib import Path
import requests

API_URL = "http://127.0.0.1:8000"

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Sistema de búsqueda - Proyecto 2")
        self.resize(1100, 700)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)

        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        # Inicializar pestañas
        self._init_text_tab()
        self._init_multimedia_tab()

    # primera parte : query textual
    def _init_text_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        group_query = QtWidgets.QGroupBox("Consulta textual")
        form = QtWidgets.QFormLayout(group_query)

        self.txtQuery = QtWidgets.QPlainTextEdit()
        self.txtQuery.setFixedHeight(100)
        self.txtQuery.setPlaceholderText( #aqui puse la query de ejemplo del doc nomas xd
            "SELECT title, artist, lyric\n"
            "FROM Audio\n"
            "WHERE lyric @@ 'amor en tiempos de guerra'\n"
            "LIMIT 10;"
        )
        form.addRow("Consulta:", self.txtQuery)

        # Motor (ComboBox)
        self.comboMotor = QtWidgets.QComboBox()
        self.comboMotor.addItems(["Índice invertido", "Secuencial"])
        form.addRow("KNN:", self.comboMotor)

        # Top-K (SpinBox)
        self.spinTopK = QtWidgets.QSpinBox()
        self.spinTopK.setRange(1, 1000)
        self.spinTopK.setValue(5)
        form.addRow("Top-K:", self.spinTopK)

        # Botón Buscar
        self.btnBuscarTexto = QtWidgets.QPushButton("Buscar")
        form.addRow("", self.btnBuscarTexto)

        layout.addWidget(group_query)

        # Label de estado
        self.lblEstadoTexto = QtWidgets.QLabel("Listo.")
        self.lblEstadoTexto.setStyleSheet("color: gray;")
        layout.addWidget(self.lblEstadoTexto)

        # ── GroupBox: Resultados ──
        group_results = QtWidgets.QGroupBox("Resultados")
        vres = QtWidgets.QVBoxLayout(group_results)

        self.tblResultadosTexto = QtWidgets.QTableWidget()
        self.tblResultadosTexto.setColumnCount(5)
        self.tblResultadosTexto.setHorizontalHeaderLabels(
            ["ID", "Título", "Autor", "Fragmento", "Score"] #uso esas variables de ejemplo nomas
        )
        header = self.tblResultadosTexto.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.tblResultadosTexto.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self.tblResultadosTexto.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )
        vres.addWidget(self.tblResultadosTexto)

        layout.addWidget(group_results)

        # Agregar tab
        self.tabs.addTab(tab, "Texto")

        # Conectar señal
        self.btnBuscarTexto.clicked.connect(self.on_buscar_texto)

# para audio
    def _init_multimedia_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        group_query = QtWidgets.QGroupBox("Consulta por audio")
        form = QtWidgets.QFormLayout(group_query)

        # Archivo: lineEdit + botón "Examinar"
        file_layout = QtWidgets.QHBoxLayout()
        self.txtRutaArchivo = QtWidgets.QLineEdit()
        self.txtRutaArchivo.setReadOnly(True)
        self.btnBuscarArchivo = QtWidgets.QPushButton("Examinar…")
        file_layout.addWidget(self.txtRutaArchivo)
        file_layout.addWidget(self.btnBuscarArchivo)
        form.addRow("Importa archivo de audio:", file_layout)

        # Top-K Multimedia
        self.spinTopKMultimedia = QtWidgets.QSpinBox()
        self.spinTopKMultimedia.setRange(1, 1000)
        self.spinTopKMultimedia.setValue(8)
        form.addRow("Top-K:", self.spinTopKMultimedia)

        # Consulta SQL de ejemplo (solo lectura)
        self.txtSQLMultimedia = QtWidgets.QPlainTextEdit()
        self.txtSQLMultimedia.setReadOnly(True)
        self.txtSQLMultimedia.setFixedHeight(90)
        self.txtSQLMultimedia.setPlaceholderText(
            "SELECT id, title\n"
            "FROM Audio\n"
            "WHERE audio_sim <-> 'ruta/a/tu/audio.extension'\n"
            "LIMIT 8;"
        )
        form.addRow("Consulta SQL (ejemplo):", self.txtSQLMultimedia)

        # Botón buscar similares
        self.btnBuscarMultimedia = QtWidgets.QPushButton("Buscar similares")
        form.addRow("", self.btnBuscarMultimedia)

        layout.addWidget(group_query)

        # Label de estado
        self.lblEstadoMultimedia = QtWidgets.QLabel("Listo.")
        self.lblEstadoMultimedia.setStyleSheet("color: gray;")
        layout.addWidget(self.lblEstadoMultimedia)

        # ── GroupBox: Resultados multimedia ──
        group_results = QtWidgets.QGroupBox("RESULTADOS DE AUDIOS SIMILARES")
        vres = QtWidgets.QVBoxLayout(group_results)

        # ScrollArea con grid interno
        self.scrollMultimedia = QtWidgets.QScrollArea()
        self.scrollMultimedia.setWidgetResizable(True)

        self.multimediaContainer = QtWidgets.QWidget()
        self.gridMultimedia = QtWidgets.QGridLayout(self.multimediaContainer)
        self.gridMultimedia.setContentsMargins(5, 5, 5, 5)
        self.gridMultimedia.setHorizontalSpacing(10)
        self.gridMultimedia.setVerticalSpacing(10)

        self.scrollMultimedia.setWidget(self.multimediaContainer)
        vres.addWidget(self.scrollMultimedia)

        layout.addWidget(group_results)

        self.tabs.addTab(tab, "Audio")

        self.btnBuscarArchivo.clicked.connect(self.on_elegir_archivo)
        self.btnBuscarMultimedia.clicked.connect(self.on_buscar_multimedia)

    # logica sin backend aun
    def on_buscar_texto(self):
        query = self.txtQuery.toPlainText().strip()
        top_k = self.spinTopK.value()
        motor = self.comboMotor.currentText()

        if not query:
            self.lblEstadoTexto.setText("Por favor, ingrese una consulta.")
            return

        # Simular tiempo de búsqueda, faltaria conectar al postgres
        start = time.time()
        time.sleep(0.2)

        # esto para generar resultados dummy
        results = []
        for i in range(top_k):
            results.append({
                "id": i + 1,
                "title": f"Documento de prueba {i + 1}",
                "author": "Autor M",
                "snippet": f"Este es un fragmento de texto donde aparece la consulta: «{query[:30]}...»",
                "score": 1.0 - i * 0.05, #aqui el scoring deb eser el qe usamos
            })

        elapsed = time.time() - start

        self.actualizar_tabla_texto(results)
        self.lblEstadoTexto.setText(
            f"Se encontraron {len(results)} documentos en {elapsed:.3f} s con el motor: {motor}."
        )

    def actualizar_tabla_texto(self, results):
        self.tblResultadosTexto.setRowCount(len(results))
        for row, doc in enumerate(results):
            self.tblResultadosTexto.setItem(row, 0, QtWidgets.QTableWidgetItem(str(doc["id"])))
            self.tblResultadosTexto.setItem(row, 1, QtWidgets.QTableWidgetItem(doc["title"]))
            self.tblResultadosTexto.setItem(row, 2, QtWidgets.QTableWidgetItem(doc["author"]))
            self.tblResultadosTexto.setItem(row, 3, QtWidgets.QTableWidgetItem(doc["snippet"]))
            self.tblResultadosTexto.setItem(row, 4, QtWidgets.QTableWidgetItem(f"{doc['score']:.3f}"))

    def on_elegir_archivo(self):

        filtro = "Audio (*.wav *.mp3 *.flac *.m4a)"

        archivo, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de audio",
            "",
            filtro
        )
        if archivo:
            self.txtRutaArchivo.setText(archivo)

            track_id = self._extract_track_id(archivo)
            top_k = self.spinTopKMultimedia.value()

            plantilla = (
                "SELECT id, title\n"
                "FROM Audio\n"
                f"WHERE audio_sim <-> '{track_id}'\n"
                f"LIMIT {top_k};"
            )
            self.txtSQLMultimedia.setPlainText(plantilla)

    def on_buscar_multimedia(self):
        ruta = self.txtRutaArchivo.text().strip()
        top_k = self.spinTopKMultimedia.value()

        if not ruta:
            self.lblEstadoMultimedia.setText("Por favor, seleccione un archivo de audio.")
            return
        
        track_id = self._extract_track_id(ruta)
        if not track_id:
            self.lblEstadoMultimedia.setText("No se pudo extraer el track_id del archivo seleccionado.")
            return

        self.lblEstadoMultimedia.setText("Consultando API…")

        start = time.time()
        try:
            response = requests.get(
                f"{API_URL}/audio/search/{track_id}",
                params={"k": top_k},
                timeout=30,
            )
            response.raise_for_status()
            api_results = response.json()

            results = self._enrich_results(api_results)
       

            elapsed = time.time() - start

            self.mostrar_resultados_multimedia(results)
            self.lblEstadoMultimedia.setText(
                f"Mostrando {len(results)} resultados en {elapsed:.3f} s (consulta: track {track_id})."
            )
        except requests.RequestException as exc:
            self.lblEstadoMultimedia.setText(f"Error consultando API: {exc}")


    def limpiar_grid_multimedia(self):
        # Eliminar widgets anteriores del grid
        while self.gridMultimedia.count():
            item = self.gridMultimedia.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def mostrar_resultados_multimedia(self, results):
        self.limpiar_grid_multimedia()

        cols = 4  # número de columnas en la grilla
        for idx, res in enumerate(results):
            row = idx // cols
            col = idx % cols

            card = QtWidgets.QFrame()
            card.setFrameShape(QtWidgets.QFrame.StyledPanel)
            card.setStyleSheet("background-color: #f7f7f7; border-radius: 6px;")
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setContentsMargins(8, 8, 8, 8)

            title_label = QtWidgets.QLabel(res["title"])
            title_label.setWordWrap(True)
            title_label.setStyleSheet("font-weight: bold;")

            artist_label = QtWidgets.QLabel(f"Artista: {res.get('artist', 'N/A')}")
            tipo_label = QtWidgets.QLabel("Tipo: Audio")
            score_label = QtWidgets.QLabel(f"Score: {res['score']:.3f}")

            icon_label = QtWidgets.QLabel()
            icon_label.setAlignment(QtCore.Qt.AlignCenter)
            icon_label.setFixedHeight(80)
            icon_label.setText("🎵")

            card_layout.addWidget(icon_label)
            card_layout.addWidget(title_label)
            card_layout.addWidget(artist_label)
            card_layout.addWidget(tipo_label)
            card_layout.addWidget(score_label)

            self.gridMultimedia.addWidget(card, row, col)

  # =====================
    # Helpers backend audio
    # =====================
    def _extract_track_id(self, file_path: str) -> str:
        """Obtiene el track_id desde el nombre del archivo."""
        try:
            return Path(file_path).stem
        except Exception:
            return ""

    def _fetch_metadata(self, track_id: str):
        """Obtiene metadata opcional para mostrar título/artista."""
        try:
            resp = requests.get(
                f"{API_URL}/metadata/track/{track_id}", timeout=10
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                track = data.get("track", {})
                artist = data.get("artist", {})
                title = track.get("title") or f"Track {track_id}"
                artist_name = artist.get("name") or "Artista desconocido"
                return title, artist_name
        except requests.RequestException:
            pass
        return None, None

    def _enrich_results(self, api_results):
        """Convierte la respuesta de la API en la estructura usada por la UI."""
        enriched = []
        for result in api_results:
            track_id = str(result.get("track_id", ""))
            score = float(result.get("score", 0.0))
            title, artist = self._fetch_metadata(track_id)
            if title is None:
                title = f"Track {track_id}"
            if artist is None:
                artist = "Artista no disponible"

            enriched.append({
                "id": track_id,
                "title": title,
                "artist": artist,
                "score": score,
            })
        return enriched



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

# Apuntes 
# jalar tiempo de ejecución de POSTGRESQL!
# que la query de audio sea editable
# agregar boton de knn invertido o secuencial

# debo descargar dataset audio, grupo small.zip y metadata.zip del tercer dataset del informe
#averiguar sobre maldición de la dimensionalidad
#que tipos de gráficos se pueden usar para representar audio (MFCC, espectrograma, etc)?
#preguntar que dataset se usa, el de github el de spotify o ambas? 
# mejorar interfaz gráfica (colores, estilos, etc)


#actualizar topk junto con el limit del query que se ponga en texto 