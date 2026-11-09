# Auditor Inteligente de Contratos, SLAs y Políticas de Compra

Proyecto del programa **Especialización en Desarrollo con IA Generativa (Accenture)**. Se construye de forma incremental, bloque a bloque, hasta la aplicación completa que se entrega en el Gate 3.

El Auditor analiza cláusulas de contratos con proveedores (SLAs, multas, plazos, obligaciones legales) usando un modelo de lenguaje (Gemini), y devuelve un diagnóstico estructurado en JSON: **tipo de cláusula, categoría y nivel de riesgo, montos y plazos extraídos, y observaciones**.

> Este README describe **solo lo que está implementado hoy**. Lo que viene después está en la sección [Hoja de ruta](#hoja-de-ruta-aún-no-implementado).

## Qué está implementado hoy

| Módulo | Qué hace en el Auditor |
|---|---|
| `src/consumir_gemini.py` | Cliente REST de Gemini (`armar_peticion`, `enviar_peticion`, `extraer_texto`), manejo de errores 401/403/429/5xx, costo por tokens (`calcular_costo`), validación del JSON del auditor (`parsear_respuesta_json`) y consulta del valor de la UF/dólar en [mindicador.cl](https://mindicador.cl/api) (`obtener_indicador_economico`) para valorizar multas en pesos. |
| `cliente.py` | `consultar_modelo` con reintentos y backoff exponencial con jitter (`con_reintento`) y control de costo acumulado de la sesión (`registrar_costo`). |
| `src/prompts/banco.py` | Banco de prompts con salida JSON forzada (`responseSchema`): `clasificar_clausula_riesgo` y `extraer_montos_y_plazos`. |
| `src/consistencia.py` | Ejecuta cada prompt del banco 3 veces y registra cuántas respuestas JSON fueron válidas en `src/prompts/registro_resultados.json`. |
| `src/evaluacion_modelos.py` | Compara latencia y costo de varios modelos Gemini sobre una cláusula de prueba (ver `docs/decision_arquitectura_modelo.md`). |
| `pipeline_limpieza.py` | Limpia y tokeniza fragmentos de contratos (`limpiar_texto`, `tokenizar`, `vectorizar`, `procesar_texto`). |
| `pipeline.py` | Mide la calidad de las respuestas del auditor contra una referencia: `precision`, `cobertura` y `f1`; guarda los resultados en `resultados_metricas.json`. |
| `src/cadena.py` | Cadena LangChain simple (`prompt \| modelo \| parser`) que explica una cláusula a un analista de compras. |
| `src/cadena_tres_pasos.py` | Cadena LangChain secuencial de 3 pasos: extrae los puntos clave de una cláusula → los simplifica sin jerga legal → los formatea en viñetas. |
| `test_cliente.py` | 25 pruebas unitarias con mocks (sin red): cliente HTTP, reintentos, costos, limpieza, validación JSON, métricas e indicador económico. |

### Esquema JSON del auditor

Las claves de negocio que usan los prompts y las pruebas (y que reutilizarán las etapas siguientes):

| Clave | Tipo | Valores |
|---|---|---|
| `tipo_clausula` | texto | `Financiera`, `SLA`, `Legal`, `Normativa` |
| `categoria_riesgo` | texto | `Financiero/SLA`, `Legal/Normativo` |
| `nivel_riesgo` | texto | `Bajo`, `Medio`, `Alto` |
| `requiere_revision_legal` | booleano | |
| `observaciones` | texto | |
| `partes` | lista de textos | |
| `montos` | lista de `{valor, moneda, concepto}` | `moneda`: `UF`, `USD`, `CLP` |
| `plazos` | lista de `{cantidad, unidad, concepto}` | |

## Cómo empezar

1. Crea tu entorno virtual de Python (por ejemplo, con `venv`) y actívalo.
2. Instala las dependencias: `pip install -r requirements.txt`.
3. Copia `.env.example` a un archivo nuevo llamado `.env`, y completa ahí tu `GEMINI_API_KEY`. El archivo `.env` nunca se sube al repositorio: ya está excluido en `.gitignore`.

## Cómo ejecutar

Desde la raíz del proyecto:

```bash
python cliente.py              # auditoría rápida de una cláusula SLA
python pipeline_limpieza.py    # limpieza/tokenización de un fragmento de contrato
python pipeline.py             # métricas de calidad del auditor -> resultados_metricas.json
python src/consumir_gemini.py  # clasificación JSON (tipo_clausula, nivel_riesgo) + latencia y costo
python src/cadena.py           # cadena LangChain simple
python src/cadena_tres_pasos.py
```

Desde `src/` (usan imports relativos a esa carpeta):

```bash
cd src
python consistencia.py         # consistencia del banco de prompts -> prompts/registro_resultados.json
python evaluacion_modelos.py   # comparación de modelos
```

> `resultados_metricas.json` y `src/prompts/registro_resultados.json` están vacíos hasta que ejecutes los scripts correspondientes con tu propia llave.

## Pruebas

```bash
python -m pytest -q
```

Las pruebas no consumen la API (usan `unittest.mock`), así que se ejecutan sin red y sin costo.

## Estructura de carpetas

- `src/` : código fuente del Auditor.
- `docs/` : documentación técnica (diagrama, decisión de modelo, límites de la métrica).
- `tests/` : reservado para la suite de pruebas cuando el proyecto crezca (hoy las pruebas viven en `test_cliente.py`).
- `requirements.txt` : dependencias de Python del proyecto.
- `.env.example` : plantilla de las variables de entorno, sin valores reales.
- `.gitignore` : archivos y carpetas que Git ignora (entorno virtual, `.env`, cachés).

## Hoja de ruta (aún no implementado)

Estas piezas se agregarán en los próximos bloques del programa; **no existen todavía en el código**:

- Enrutamiento condicional de la cadena según `categoria_riesgo` (rama Financiero/SLA vs. rama Legal/Normativo).
- Agente con herramienta de cálculo de penalidades/SLA a partir de `montos`, `plazos` y el valor de la UF.
- RAG sobre un manual de políticas internas de compra, con citación de fuentes.
- Mitigación de prompt injection en los textos de contratos recibidos.
- Endpoints con FastAPI y empaquetado con Docker.

## Reglas que se mantienen durante todo el programa

- Ningún secreto (contraseña, llave de API, token) va escrito directamente en el código ni en ningún archivo que se suba al repositorio.
- Cada proyecto nuevo tiene su propio entorno virtual: no se comparten dependencias entre proyectos distintos.
- Todo el trabajo que se entrega en este programa vive en un repositorio de GitHub, sin excepción.
