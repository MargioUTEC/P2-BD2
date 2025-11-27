# Proyecto 2: Base de Datos 2

| Integrante | % de Participación |
| ---------- | ------------------ |
| Margiory Alvarado Chavez | 100%         |
| Yofer Corne Flores  | 100%               |
| Diana Ñañez Andrés | 100%               |
| Jesús Velarde Tipte | 100%               |
| Franco Roque Castillo | 100%               |

---

## Introducción
aqui voy a escribir el dominio de datos (texto y audio) y del objetivo del proyecto.  
Justificación de la necesidad de una base de datos multimodal orientada a recuperación por contenido.


---

## Arquitectura del Proyecto
(podemos poner un gráfico del procedimiento del proyecto)



---

## Índice Invertido para Texto
### Preprocesamiento
- Tokenización  
- Eliminación de stopwords  
- Limpieza de signos  
- Stemming  

### Construcción del Índice Invertido
- Se realizó el cálculo de TF-IDF (Term Frequency-Inverse Document Frequency)
- Cálculo de norma del documento (aqui faltaria explicar junto con el SPIMI)
- Construcción mediante SPIMI (Single-Pass In-Memory Indexing)
- Merge Blocks utilizando B buffers


### Motor de Consulta
- Entrada: consulta en lenguaje natural
- Scoring hallada con similitud de coseno
- Recuperación del Top-K sin cargar todo el índice en memoria RAM.

### Comparación con PostgreSQL
- Para el proyecto compararemo nuestros resultados con el índice GIN de PostgreSQL.
- Estrategia de ranking (ts_rank, ts_rank_cd, etc.) manejando también **tsquery** y **tsvector**



---

## Índice Invertido para Descriptores Locales para audio
### Extracción de Características
Fue realizado con MFCC (de ahi le pongo más contexto)

### Construcción del Diccionario Acústico
La construcción del diccionario acústico se inicia aplicando el algoritmo K-Means sobre el conjunto de descriptores locales extraídos de los audios de ***FMA: A Dataset For Music Analysis***. Cada descriptor es asignado al clúster más cercano y el centroide resultante representa una acoustic word.

Una vez finalizado el proceso de agrupamiento, el diccionario queda conformado por todos los centroides obtenidos, esto permite mapear cualquier nuevo vector de características hacia una palabra del vocabulario acústico. Finalmente, cada objeto sonoro es representado mediante un histograma que cuantifica la frecuencia relativa de aparición de estas acoustic words dentro del audio, logrando así una representación compacta y comparable que habilita las tareas de recuperación por similitud.

### Búsqueda KNN
| Algoritmo | Descripción |
|----------|-------------|
| KNN Secuencial | Comparación coseno entre histogramas |
| KNN con Indexación Invertida | Optimización basada en codewords + TF-IDF + heap |

## Fronted

El frontend fue desarrollado utilizando Qt para Python, priorizando la usabilidad y la interacción intuitiva con los motores de búsqueda textual y multimedia implementados en el backend. La interfaz cuenta con **dos ventanas** independientes: una destinada a la recuperación basada en texto y otra orientada a la búsqueda de audios. En ambos casos, la aplicación ofrece elementos interactivos que permiten ejecutar querys de manera dinámica. En la ventana de texto, el usuario puede ingresar una consulta libre en un cuadro de texto, seleccionar el valor de Top-K y elegir el tipo de algoritmo de recuperación mediante una barra lateral configurable. Tras la ejecución, los resultados son presentados en un panel que muestra los outputs en lo que se refleja la metadata y la información relevante de cada documento recuperado.

La ventana dedicada a audio replica esta estructura general, pero adaptada al dominio multimedia. El usuario puede cargar un archivo de consulta desde su sistema local y especificar los parámetros para la búsqueda por similitud. Una vez mostrados los resultados, la interfaz permite seleccionar cualquiera de los audios retornados y reproducirlo directamente, lo que facilita la validación subjetiva y objetiva de la similitud entre el archivo de consulta y los elementos recuperados. Esta organización del fronted habilita un flujo de interacción funcional con ambos sistemas de recuperación basados en contenido.


## Análisis Comparativo

## Experimento 1: Búsqueda en Texto (PostgreSQL vs. Implementación Propia)

En esta sección se evalúa el rendimiento de la búsqueda full-text utilizando PostgreSQL como punto de referencia (baseline). Se compararon tiempos de respuesta variando el tamaño de la colección (N) desde 1,000 hasta 32,000 documentos.

### Configuración del Experimento en PostgreSQL
Para la indexación en base de datos, se investigaron y evaluaron dos tipos de índices nativos de PostgreSQL:
* **GIN (Generalized Inverted Index):** Optimizado para lecturas rápidas y búsquedas de texto completo. Es ideal para datos estáticos donde la velocidad de consulta es crítica.
* **GiST (Generalized Search Tree):** Optimizado para datos geométricos y búsquedas difusas, con inserciones más rápidas pero lecturas más lentas en comparación con GIN.

**Decisión de Diseño:**
Tras realizar pruebas preliminares, obtuvimos una diferencia significativa en tiempos de respuesta (lectura). Para N=32,000 registros:
* **Índice GiST:** ~0.1471 segundos.
* **Índice GIN:** ~0.0009 segundos.

Dado que **GIN demostró ser aproximadamente 160 veces más rápido** en operaciones de recuperación para nuestro dataset de letras de canciones, seleccionamos este índice para la arquitectura final del proyecto.

**Manejo de Consultas:**
PostgreSQL gestiona las búsquedas convirtiendo el texto original en un `tsvector` (lista de lexemas normalizados, sin stopwords) y la consulta del usuario en un `tsquery`. La función de ranking utilizada internamente es `ts_rank`, que asigna un puntaje de relevancia basado en la frecuencia y densidad de los términos buscados.

### Resultados de Rendimiento (Texto)

| Tamaño de la colección (N) | MyIndex (Python) | PostgreSQL (GIN) |
|---------------------------|------------------|------------------|
| N = 2000                  | *pendiente* | **0.000686 s** |
| N = 4000                  | *pendiente* | **0.000773 s** | 
| N = 8000                  | *pendiente* | **0.000791 s** | 
| N = 16000                 | *pendiente* | **0.000821 s** |
| N = 32000                 | *pendiente* | **0.000917 s** |

> **Análisis:** El índice GIN mantiene un tiempo de respuesta casi constante (sub-milisegundo) incluso al duplicar el volumen de datos, demostrando una escalabilidad logarítmica ideal para este tipo de aplicaciones.

### Audio
| Tamaño de la colección (N) | KNN-Secuencial | KNN-Indexado | KNN-PostgreSQL |
|---------------------------|----------------|--------------|----------------|
| N = 1000                  |                |              |                |
| N = 2000                  |                |              |                |
| N = 4000                  |                |              |                |
| N = 8000                  |                |              |                |
| N = 16000                 |                |              |                |
| N = 32000                 |                |              |                |
| N = 64000                 |                |              |                |

\* Mantener el valor de K = 8.



## Ejecución del Proyecto
??? aqui me imagino que describimos los pasitos del proyecto
### Requisitos

### Pasos


## Estructura de la Repo

