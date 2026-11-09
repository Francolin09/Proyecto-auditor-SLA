import importlib
import json
import logging
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

pytest.importorskip("langchain_core") #requiere el entorno del proyecto (.venv) con LangChain

from langchain_core.language_models import FakeListChatModel
from langchain_core.runnables import RunnableLambda

sys.path.insert(0, str(Path(__file__).parent / "src")) #enrutamiento.py importa módulos de src/ por nombre

CLAUSULA_SLA = (
    "El Proveedor garantiza una disponibilidad mensual del servicio de 99,5%. "
    "Por cada hora adicional de indisponibilidad se aplicará una multa de 2 UF, "
    "con un tope del 10% del valor mensual del contrato."
)
CLAUSULA_LEGAL = (
    "Cualquier controversia será resuelta por arbitraje en Santiago. El Proveedor "
    "deberá cumplir la Ley 19.628 sobre protección de datos personales."
)
EXTRACCION = "Partes: Proveedor\nMulta: 2 UF por hora\nTope: 10% del valor mensual"
REPORTE_FINANCIERO = {
    "tipo_clausula": "SLA",
    "categoria_riesgo": "Financiero/SLA",
    "nivel_riesgo": "Medio",
    "requiere_revision_legal": False,
    "montos": [{"valor": 2, "moneda": "UF", "concepto": "multa por hora de indisponibilidad"}],
    "plazos": [],
    "observaciones": "El tope del 10% limita la compensación.",
    "resumen_simple": "Si el servicio falla, el proveedor paga 2 UF por hora, hasta el 10% mensual.",
}
REPORTE_LEGAL = {
    "tipo_clausula": "Legal",
    "categoria_riesgo": "Legal/Normativo",
    "nivel_riesgo": "Medio",
    "requiere_revision_legal": True,
    "montos": [],
    "plazos": [],
    "observaciones": "No define el reglamento ni el centro de arbitraje.",
    "resumen_simple": "Los conflictos se resuelven por arbitraje en Santiago y el proveedor debe proteger los datos personales.",
}


@pytest.fixture
def cargar_enrutamiento(tmp_path, monkeypatch):
    """Importa enrutamiento.py con un modelo simulado en vez de Gemini (sin red ni costo)."""
    monkeypatch.chdir(tmp_path) #error.log se escribe en una carpeta temporal

    def _cargar(modelo_simulado):
        for nombre in ("enrutamiento", "cadena_tres_pasos"):
            sys.modules.pop(nombre, None)
        with patch("langchain_google_genai.ChatGoogleGenerativeAI", return_value=modelo_simulado):
            return importlib.import_module("enrutamiento")

    yield _cargar

    raiz = logging.getLogger()
    for handler in list(raiz.handlers):
        handler.close()
        raiz.removeHandler(handler)


def leer_log(tmp_path):
    ruta = tmp_path / "error.log"
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


# ---------- Condiciones de la bifurcación ----------

def test_condiciones_de_la_bifurcacion(cargar_enrutamiento):
    enrutamiento = cargar_enrutamiento(FakeListChatModel(responses=["x"]))

    assert enrutamiento.es_financiero_sla({"clasificacion": "financiero/sla"})
    assert not enrutamiento.es_financiero_sla({"clasificacion": "legal/normativo"})
    assert enrutamiento.es_legal_normativo({"clasificacion": "legal/normativo"})
    assert not enrutamiento.es_legal_normativo({"clasificacion": "otra"})


# ---------- Enrutamiento completo: extracción -> clasificación -> rama ----------

def test_clausula_financiera_va_a_rama_financiera_sla(cargar_enrutamiento):
    modelo = FakeListChatModel(responses=[EXTRACCION, "Financiero/SLA", json.dumps(REPORTE_FINANCIERO)])
    enrutamiento = cargar_enrutamiento(modelo)

    resultado = enrutamiento.procesar_mensaje_seguro(enrutamiento.cadena_robusta, CLAUSULA_SLA)

    assert resultado == REPORTE_FINANCIERO

def test_clausula_legal_va_a_rama_legal_normativa_y_normaliza_clasificacion(cargar_enrutamiento):
    reporte_con_markdown = "```json\n" + json.dumps(REPORTE_LEGAL, ensure_ascii=False) + "\n```"
    modelo = FakeListChatModel(responses=[EXTRACCION, " Legal / Normativo. ", reporte_con_markdown])
    enrutamiento = cargar_enrutamiento(modelo)

    resultado = enrutamiento.procesar_mensaje_seguro(enrutamiento.cadena_robusta, CLAUSULA_LEGAL)

    assert resultado == REPORTE_LEGAL

def test_clasificacion_no_reconocida_va_a_revision_manual(cargar_enrutamiento, tmp_path):
    modelo = FakeListChatModel(responses=[EXTRACCION, "No estoy seguro"])
    enrutamiento = cargar_enrutamiento(modelo)

    resultado = enrutamiento.procesar_mensaje_seguro(enrutamiento.cadena_robusta, CLAUSULA_SLA)

    assert resultado["nivel_riesgo"] == "No determinado"
    assert resultado["requiere_revision_legal"] is True
    assert "noestoyseguro" in resultado["observaciones"]
    assert "Clasificación no reconocida" in leer_log(tmp_path)


# ---------- Fallback y manejo de errores ----------

def test_json_invalido_de_la_rama_activa_fallback(cargar_enrutamiento, tmp_path):
    modelo = FakeListChatModel(responses=[EXTRACCION, "Financiero/SLA", "Riesgo alto, multa de 2 UF"])
    enrutamiento = cargar_enrutamiento(modelo)

    resultado = enrutamiento.procesar_mensaje_seguro(enrutamiento.cadena_robusta, CLAUSULA_SLA)

    assert set(resultado) == set(enrutamiento.claves_reporte)
    assert "falló" in resultado["observaciones"]
    assert "Cadena principal falló" in leer_log(tmp_path)

def test_caida_del_modelo_activa_fallback(cargar_enrutamiento, tmp_path):
    def modelo_caido(_):
        raise RuntimeError("429 Límite excedido")

    enrutamiento = cargar_enrutamiento(RunnableLambda(modelo_caido))

    resultado = enrutamiento.procesar_mensaje_seguro(enrutamiento.cadena_robusta, CLAUSULA_SLA)

    assert resultado["requiere_revision_legal"] is True
    assert "Cadena principal falló" in leer_log(tmp_path)

def test_procesar_mensaje_seguro_captura_error_de_la_cadena(cargar_enrutamiento, tmp_path):
    enrutamiento = cargar_enrutamiento(FakeListChatModel(responses=["x"]))
    cadena_falsa = Mock()
    cadena_falsa.invoke.side_effect = ValueError("error simulado")

    resultado = enrutamiento.procesar_mensaje_seguro(cadena_falsa, CLAUSULA_LEGAL)

    assert "intenta más tarde" in resultado["observaciones"]
    assert "Error procesando cláusula: error simulado" in leer_log(tmp_path)

def test_procesar_mensaje_seguro_envia_la_clausula_como_texto(cargar_enrutamiento):
    enrutamiento = cargar_enrutamiento(FakeListChatModel(responses=["x"]))
    cadena_falsa = Mock()
    cadena_falsa.invoke.return_value = REPORTE_LEGAL

    resultado = enrutamiento.procesar_mensaje_seguro(cadena_falsa, CLAUSULA_LEGAL)

    cadena_falsa.invoke.assert_called_once_with({"texto": CLAUSULA_LEGAL})
    assert resultado == REPORTE_LEGAL

