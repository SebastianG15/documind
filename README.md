# DocuMind Financial AI

Motor de inteligencia documental, extraccion multimodal y conciliacion de tres vias (Three-Way Matching) para expedientes de cuentas por pagar.

## Descripcion General

DocuMind Financial AI es un sistema auto-alojado disenado para el procesamiento automatizado de comprobantes financieros escaneados y fotografiados, tales como facturas comerciales, guias de remision y constancias de pago bancario.

El sistema ejecuta modelos de vision y lenguaje de codigo abierto del ecosistema de Hugging Face acelerados por GPU local (NVIDIA GeForce GTX 1660 Ti), almacenamiento relacional y vectorial en PostgreSQL 16 con la extension pgvector, backend en FastAPI y una interfaz de auditoria en Next.js.

## Arquitectura y Tecnologias

* Inteligencia Artificial y Vision: Hugging Face (SmolVLM, sentence-transformers), PaddleOCR, PyTorch CUDA 12.4, OpenCV.
* Backend: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic.
* Base de Datos: PostgreSQL 16 con extension pgvector.
* Frontend: Next.js 15, Tailwind CSS, TypeScript.
* Infraestructura: Docker Compose, uv.

## Estructura del Proyecto

* backend/: Logica del servidor, modelos de datos, migraciones y scripts de inferencia.
* frontend/: Interfaz de usuario para carga, visualizacion y auditoria de documentos.
* docs/: Especificaciones de diseno de software (SDD) y planes de desarrollo.
* docker-compose.yml: Definicion de servicios locales de base de datos e infraestructura.

## Ejecucion Local

```bash
# Iniciar servicios de base de datos
docker compose up -d

# Verificar deteccion de hardware y CUDA en backend
cd backend
python scripts/verify_cuda.py
```
