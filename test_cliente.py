import cliente
from cliente import con_reintento, consultar_modelo
from pipeline import *
from unittest.mock import patch, Mock

import pytest

from src.consumir_gemini import enviar_peticion, parsear_respuesta_json, obtener_indicador_economico


CLAUSULA_SLA = (
    "El Proveedor garantiza una disponibilidad mensual del servicio de 99,5%. "
    "Por cada hora adicional de indisponibilidad se aplicará una multa de 2 UF, "
    "con un tope del 10% del valor mensual del contrato."
)
CUERPO_CLAUSULA = {"contents": [{"parts": [{"text": CLAUSULA_SLA}]}]}
RESPUESTA_AUDITOR = {
    "tipo_clausula": "SLA",
    "categoria_riesgo": "Financiero/SLA",
    "nivel_riesgo": "Alto",
    "requiere_revision_legal": False,
    "observaciones": "Multa de 2 UF por hora con tope del 10% mensual.",
}
RESPUESTA_MINDICADOR_UF = {
    "version": "1.7.0",
    "autor": "mindicador.cl",
    "codigo": "uf",
    "nombre": "Unidad de fomento (UF)",
    "unidad_medida": "Pesos",
    "serie": [
        {"fecha": "2026-11-05T03:00:00.000Z", "valor": 39500.25},
        {"fecha": "2026-11-04T03:00:00.000Z", "valor": 39495.10},
    ],
}


# ---------- Cliente HTTP del modelo (src/consumir_gemini.py) ----------

def test_enviar_peticion_credencial_invalida():
    respuesta_falsa = Mock(status_code=401)
    #patch remplaza la funcion requests.post por nuestra respuesta falsa
    with patch("src.consumir_gemini.requests.post", return_value=respuesta_falsa):
        with pytest.raises(ValueError):
            enviar_peticion("https://auditor.invalido/clasificar", CUERPO_CLAUSULA)
            #Entonces acá al final se ejecuta nuestra respuesta falsa 

def test_enviar_peticion_limite_de_uso():
    respuesta_falsa = Mock(status_code=429)

    with patch("src.consumir_gemini.requests.post", return_value = respuesta_falsa):
        with pytest.raises(TimeoutError):
            enviar_peticion("https://auditor.limite/clasificar", CUERPO_CLAUSULA)

def test_enviar_peticion_exito():
    respuesta_falsa = Mock(status_code = 200)
    respuesta_falsa.json.return_value = RESPUESTA_AUDITOR

    with patch("src.consumir_gemini.requests.post", return_value = respuesta_falsa):
        resultado = enviar_peticion("https://auditor.ok/clasificar", CUERPO_CLAUSULA)

    assert resultado == RESPUESTA_AUDITOR


# ---------- Reintentos y costos (cliente.py) ----------

def test_con_reintento_agota_intentos():
    def siempre_falla():
        raise TimeoutError("simulado: proveedor saturado al auditar cláusula")

    with patch("cliente.time.sleep"):
        with pytest.raises(TimeoutError):
            con_reintento(siempre_falla, intentos=3)    

def test_con_reintento_no_reintenta_otra_excepcion():
    funcion_falsa = Mock(side_effect=ValueError("credencial invalida"))
    with patch("cliente.time.sleep"):
        with pytest.raises(ValueError):
            con_reintento(funcion_falsa, intentos=3)
    assert funcion_falsa.call_count == 1

def test_consultar_modelo_convierte_error():
    error_simulado = TimeoutError("simulado")

    with patch("cliente.con_reintento", side_effect=error_simulado):
        with pytest.raises(RuntimeError):
            consultar_modelo(f"Clasifica el riesgo de esta cláusula: {CLAUSULA_SLA}")

def test_registrar_costo_acumula():
    cliente.costo_total_sesion = 0
    respuesta_falsa = {"usageMetadata": {"totalTokenCount": 1000}}
    costo = cliente.registrar_costo(respuesta_falsa)

    assert costo == cliente.COSTO_POR_1000_TOKENS
    assert cliente.costo_total_sesion == cliente.COSTO_POR_1000_TOKENS


# ---------- Pipeline de limpieza de cláusulas (pipeline_limpieza.py) ----------

def test_procesar_texto_normaliza_mayusculas_y_puntuacion():
    resultado = procesar_texto("Multa: 2 UF por HORA!")

    assert resultado == ["multa", "2", "uf", "por", "hora"]

def test_procesar_texto_solo_puntuacion_devuelve_lista_vacia():
    resultado = procesar_texto("§§ ¡¡...!! ––")

    assert resultado == []

def test_procesar_texto_une_decimales_limite_conocido():
    # Límite documentado en docs/limites_metrica.md: la coma decimal se elimina
    resultado = procesar_texto("Multa de 0,5 UF y disponibilidad de 99,5%.")

    assert resultado == ["multa", "de", "05", "uf", "y", "disponibilidad", "de", "995"]


# ---------- Validación de la salida JSON del auditor ----------

def test_parsear_respuesta_json_auditor_valido():
    texto = json.dumps(RESPUESTA_AUDITOR)

    datos = parsear_respuesta_json(texto, ["tipo_clausula", "nivel_riesgo"])

    assert datos["tipo_clausula"] == "SLA"
    assert datos["nivel_riesgo"] == "Alto"

def test_parsear_respuesta_json_con_bloque_markdown():
    texto = "```json\n" + json.dumps(RESPUESTA_AUDITOR) + "\n```"

    datos = parsear_respuesta_json(texto, ["tipo_clausula", "categoria_riesgo"])

    assert datos["categoria_riesgo"] == "Financiero/SLA"

def test_parsear_respuesta_json_invalido():
    with pytest.raises(ValueError):
        parsear_respuesta_json("Riesgo alto, cláusula SLA", ["tipo_clausula"])

def test_parsear_respuesta_json_falta_nivel_riesgo():
    texto = json.dumps({"tipo_clausula": "Legal"})

    with pytest.raises(ValueError):
        parsear_respuesta_json(texto, ["tipo_clausula", "nivel_riesgo"])


# ---------- Métricas de calidad del auditor (pipeline.py) ----------

def test_metricas_respuesta_exacta():
    referencia = "Cláusula SLA de riesgo alto con multa de 2 UF por hora."

    metricas = calcular_metricas(referencia, referencia)

    assert metricas == {"precision": 1.0, "cobertura": 1.0, "f1": 1.0}

def test_metricas_respuesta_parcial():
    tokens_ref = ["multa", "2", "uf", "por", "hora"]
    tokens_resp = ["multa", "2", "uf"]

    metricas = calcular_precision_cobertura_f1(tokens_ref, tokens_resp)

    assert metricas["precision"] == 1.0
    assert metricas["cobertura"] == pytest.approx(0.6)
    assert metricas["f1"] == pytest.approx(0.75)

def test_metricas_respuesta_vacia():
    metricas = calcular_metricas("Cláusula legal de riesgo medio.", "")

    assert metricas == {"precision": 0.0, "cobertura": 0.0, "f1": 0.0}

def test_resumir_metricas_promedia_casos():
    resultados = [
        {"precision": 1.0, "cobertura": 0.5, "f1": 0.6},
        {"precision": 0.5, "cobertura": 1.0, "f1": 0.8},
    ]

    resumen = resumir_metricas(resultados)

    assert resumen["precision_promedio"] == pytest.approx(0.75)
    assert resumen["cobertura_promedio"] == pytest.approx(0.75)
    assert resumen["f1_promedio"] == pytest.approx(0.7)

def test_resumir_metricas_sin_resultados():
    assert resumir_metricas([]) == {
        "precision_promedio": 0,
        "cobertura_promedio": 0,
        "f1_promedio": 0,
    }


# ---------- Indicador económico para valorizar multas (mindicador.cl) ----------

def test_obtener_indicador_economico_exito():
    respuesta_falsa = Mock(status_code=200)
    respuesta_falsa.json.return_value = RESPUESTA_MINDICADOR_UF

    with patch("src.consumir_gemini.requests.get", return_value=respuesta_falsa) as get_falso:
        resultado = obtener_indicador_economico("uf")

    get_falso.assert_called_once_with("https://mindicador.cl/api/uf")
    assert resultado == {
        "codigo": "uf",
        "unidad_medida": "Pesos",
        "fecha": "2026-11-05T03:00:00.000Z",
        "valor": 39500.25,
    }

def test_obtener_indicador_economico_codigo_vacio():
    with pytest.raises(ValueError):
        obtener_indicador_economico("")

def test_obtener_indicador_economico_acceso_denegado():
    with patch("src.consumir_gemini.requests.get", return_value=Mock(status_code=403)):
        with pytest.raises(ValueError):
            obtener_indicador_economico("dolar")

def test_obtener_indicador_economico_limite_de_uso():
    respuesta_falsa = Mock(status_code=429, headers={"Retry-After": "30"})

    with patch("src.consumir_gemini.requests.get", return_value=respuesta_falsa):
        with pytest.raises(TimeoutError):
            obtener_indicador_economico("uf")

def test_obtener_indicador_economico_servicio_caido():
    with patch("src.consumir_gemini.requests.get", return_value=Mock(status_code=503)):
        with pytest.raises(TimeoutError):
            obtener_indicador_economico("uf")

def test_obtener_indicador_economico_serie_vacia():
    respuesta_falsa = Mock(status_code=200)
    respuesta_falsa.json.return_value = {"codigo": "uf", "unidad_medida": "Pesos", "serie": []}

    with patch("src.consumir_gemini.requests.get", return_value=respuesta_falsa):
        with pytest.raises(RuntimeError):
            obtener_indicador_economico("uf")
