# Guia Oficial de Demostracion y Auditoria - DocuMind Financial AI

Esta guia describe el paso a paso para evaluar y auditar la plataforma **DocuMind Financial AI**, con especial enfasis en su **Interfaz Grafica de Usuario (Next.js 15)** y su motor de **Conciliacion Contable de 3 Vias (Three-Way Matching)**.

---

## 1. Inicio Rapido de la Plataforma

Para levantar el entorno completo con interfaz web, backend y base de datos:

### Opcion Recomendada: Docker Compose (1 solo comando)
```bash
docker compose up --build -d
```
* **Interfaz Grafica Web:** [http://localhost:3000](http://localhost:3000)
* **Documentacion Interactiva Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Health Check del Backend:** [http://localhost:8000/health](http://localhost:8000/health)

### Opcion Desarrollo Local
```bash
# Terminal 1: Backend
cd backend
source .venv/bin/activate  # o .venv\Scripts\activate en Windows
uvicorn src.main:app --port 8000 --reload

# Terminal 2: Frontend Web
cd frontend
npm run dev
```

---

## 2. Walkthrough: Experiencia Paso a Paso en la Interfaz Grafica

### Paso 1: Obtener los Comprobantes de Muestra
El sistema incluye un generador automatico de expedientes contables de prueba con rotacion angular sintetica para evaluar la correccion de imagen (*deskewing*). Los archivos se encuentran generados en:

```
backend/data/samples/demo_expediente/
├── 1_factura_f001_0008492.png       # Factura electronica comercial con 3 line items
├── 2_guia_remision_t001_000412.png  # Guia de remision con sello de almacen
└── 3_voucher_banco_bcp.png          # Constancia de transferencia BCP liquidada
```
*(Si los archivos no existen, ejecutalos en 1 segundo con `python backend/scripts/demo_pipeline.py`).*

---

### Paso 2: Carga Inteligente de Expediente (Drag & Drop)
1. Navega a **[http://localhost:3000](http://localhost:3000)** en tu navegador web.
2. En el panel superior **"Cargar Nuevo Expediente Contable"**:
   * Ingresa un titulo para el expediente, por ejemplo: `Expediente Repuestos Industriales - Octubre 2026`.
   * Arrastra los 3 archivos (`.png`, `.jpg` o `.pdf`) directamente sobre la zona punteada de carga.
3. Observa la validacion en tiempo real: la interfaz valida la extension, tamano y cantidad de comprobantes (max. 10 archivos por expediente).
4. Haz clic en el boton **"Procesar y Auditar Expediente"**.

---

### Paso 3: Vista Dividida de Auditoria y Visor Documental SVG
Una vez procesado el expediente, el sistema redirige automaticamente a la vista detallada de auditoria (`/dossier/[id]`):

* **Panel Izquierdo - Visor de Comprobantes:**
  * Muestra el escaneo original corregido geometricamente por el preprocesador OpenCV (enderezado afina de angulo y realce adaptativo CLAHE).
  * Selector de paginas/documentos en la barra superior para alternar instantaneamente entre la **Factura**, la **Guia de Remision** y el **Voucher Bancario**.
  * Lienzo vectorial con tecnologia `<svg viewBox="0 0 1000 1000">` que proyecta con precision milimetrica las coordenadas espaciales detectadas por EasyOCR CRAFT sobre hardware acelerado.

* **Codificacion Visual por Color de Cajas Delimitadoras:**
  * **Verde esmeralda:** Importes monetarios, subtotales, impuestos y totales.
  * **Azul zafiro:** Identificadores tributarios (RUC emisor/receptor) y datos corporativos.
  * **Morado / Indigo:** Series y numeraciones de comprobante (`F001-0008492`, `T001-000412`).
  * **Naranja ambar:** Lineas de detalle de items, codigos SKU y cantidades transportadas.

---

### Paso 4: La Joya Tecnica: Sincronizacion Bidireccional Hover-to-Bbox
Para verificar la fidelidad de la extraccion contra el documento original:

1. Desplaza el cursor sobre cualquiera de las filas en la **Tabla de Line Items** (lado derecho).
2. **Observa el escaneo en tiempo real:** La caja delimitadora correspondiente a esa linea de compra se iluminara de inmediato en el documento escaneado con un borde resaltado y un efecto de resplandor (*glow effect*).
3. Esta funcionalidad elimina por completo la necesidad de que el auditor contable busque visualmente montos o items en escaneos densos o de baja calidad.

---

### Paso 5: Panel Semáforo de 3 Pilares Contables
En la seccion inferior derecha, el **ReconciliationPanel** evalua simultaneamente los tres requisitos indispensables de auditoria financiera:

1. **Pilar 1: Integridad Matematica:**
   * Verifica la ecuacion fundamental: $\sum \text{Line Items} == \text{Subtotal}$ y $\text{Subtotal} + \text{IGV (18\%)} == \text{Total Facturado}$.
   * Muestra un indicador verde con badge `VALIDADO` si la suma coincide con una tolerancia estricta de $\pm 0.05$ PEN.
2. **Pilar 2: Coincidencia Fisica de Almacen (Factura vs. Guia de Remision):**
   * Compara los items facturados contra las cantidades efectivamente recepcionadas en almacen mediante las guias de remision.
   * Si existe mercaderia no entregada, el semaforo marca `DISCREPANCIA` y desglosa la alerta con la cantidad faltante (`QUANTITY_SHORTAGE`).
3. **Pilar 3: Liquidacion Financiera (Factura vs. Voucher Bancario):**
   * Compara el total a pagar contra la suma de transferencias bancarias asociadas al expediente.
   * Valida la coincidencia de moneda (`PEN` vs `USD`).
   * Calcula de forma automatica el **Saldo Pendiente** por pagar.

---

### Paso 6: Busqueda Semantica en Lenguaje Natural con pgvector
En la parte superior de la aplicacion, la barra de busqueda semantica permite localizar comprobantes sin necesidad de conocer numeros exactos de serie:

1. Escribe consultas en lenguaje natural, tales como:
   * *"valvulas de control y manometros industriales"*
   * *"transferencia bancaria a distribuidora del sur"*
   * *"guia de remision planta carretera central"*
2. Presiona Enter o haz clic en **Buscar**.
3. El motor convertira tu consulta a un vector denso de 384 dimensiones (`all-MiniLM-L6-v2`) y ejecutara un ordenamiento por distancia coseno (`<=>`) en PostgreSQL 16 con indices HNSW.
4. Los resultados se desplegaran con su miniatura visual, titulo de expediente y **Score de Similitud Semantica en tiempo real**.

---

## 3. Demostracion Alternativa por Consola (CLI)

Si deseas verificar el rendimiento computacional de todo el pipeline directamente en consola:

```bash
cd backend
python scripts/demo_pipeline.py
```

El script ejecutara en vivo la generacion de los comprobantes, el deskewing por transformada de Hough, la inferencia espacial en GPU NVIDIA GTX 1660 Ti, la vectorizacion y la emision del dictamen contable estructurado.

---

## 4. Resumen Tecnico de la Plataforma

| Capa | Tecnologia Principal | Caracteristica Clave |
| :--- | :--- | :--- |
| **Frontend UI** | Next.js 15 + TypeScript + Tailwind | Lienzo vectorial SVG responsivo y sincronizacion hover bidireccional |
| **Backend REST** | FastAPI 0.115 + Pydantic v2 | Validacion de Magic Bytes, cuotas anti-DoS y cabeceras OWASP |
| **Vision & OCR** | OpenCV + EasyOCR (CRAFT) | Aceleracion CUDA, coordenadas normalizadas [0, 1000] |
| **NLP & Semantica** | Sentence-Transformers 384d | Modelo `all-MiniLM-L6-v2` integrado |
| **Persistencia** | PostgreSQL 16 + pgvector | Consultas hibridas relacionales y vectoriales con indices HNSW |
| **Auditoria** | ThreeWayReconciler | Validacion matematica, fisica y bancaria en < 1 ms |
