from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (RunnableBranch, RunnablePassthrough, RunnableLambda )
import logging
import json

from consumir_gemini import parsear_respuesta_json #Valida el JSON que devuelve cada rama
from cadena_tres_pasos import paso_extraccion, claves_reporte #Reutilizamos el paso 1 y las claves del reporte

logging.basicConfig(
    level= logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s:%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="error.log",
    filemode="a",
    encoding="utf-8",
    force=True
)

logger = logging.getLogger(__name__)

load_dotenv()
modelo = ChatGoogleGenerativeAI(model = "gemini-3.1-flash-lite")

#Flujo del auditor:
#  Paso 1 (extracción)    -> paso_extraccion de cadena_tres_pasos.py
#  Paso 2 (clasificación) -> decide la categoría de riesgo: financiero/sla o legal/normativo
#  Paso 3 (análisis)      -> RunnableBranch elige la rama especializada, que devuelve el JSON del auditor

plantilla_clasificacion = PromptTemplate.from_template(
    "Eres un auditor de contratos. Clasifica la siguiente cláusula según su categoría de riesgo: "
    "Financiero/SLA (multas, montos, pagos, niveles de servicio, plazos de entrega) o "
    "Legal/Normativo (jurisdicción, arbitraje, leyes, confidencialidad, protección de datos, "
    "responsabilidad). Responde solo con Financiero/SLA o Legal/Normativo.\n\n"
    "Cláusula:\n{texto}\n\nDatos extraídos:\n{extraccion}"
)

paso_clasificacion = (
    plantilla_clasificacion
    | modelo
    |StrOutputParser()
    |(lambda texto:texto.strip().strip(".").replace(" ", "").lower()) #"Financiero / SLA." -> "financiero/sla"
)
# clausula_prueba = "Por cada hora de indisponibilidad se aplicará una multa de 2 UF"
# clasificacion = paso_clasificacion.invoke({"texto": clausula_prueba, "extraccion": "multa de 2 UF por hora"})

# print(clasificacion)

#Formato JSON que deben devolver ambas ramas (mismas claves que el reporte de cadena_tres_pasos.py)
formato_reporte = (
    "Responde únicamente con un JSON válido, sin texto adicional, con las claves: "
    "'tipo_clausula' (Financiera, SLA, Legal o Normativa), 'categoria_riesgo' (texto), "
    "'nivel_riesgo' (Bajo, Medio o Alto), 'requiere_revision_legal' (boolean), "
    "'montos' (lista de objetos con 'valor' numérico, 'moneda' y 'concepto'), "
    "'plazos' (lista de objetos con 'cantidad' numérica, 'unidad' y 'concepto'), "
    "'observaciones' (texto) y 'resumen_simple' (máximo 2 frases sin jerga legal "
    "para un analista de compras, sin cambiar las cifras)."
)

cadena_financiera_sla = (
    PromptTemplate.from_template(
        "Eres un auditor financiero de contratos y SLAs. Analiza la cláusula poniendo foco en "
        "montos, multas, topes, forma de cobro, niveles de servicio comprometidos y plazos. "
        "Evalúa si las penalidades protegen a la empresa que compra o si los topes las dejan "
        "sin efecto. Usa 'Financiero/SLA' como categoria_riesgo. " + formato_reporte +
        "\n\nCláusula:\n{texto}\n\nDatos extraídos:\n{extraccion}"
    )
    |modelo
    |StrOutputParser()
    |(lambda texto: parsear_respuesta_json(texto, claves_reporte))
)

cadena_legal_normativa = (
    PromptTemplate.from_template(
        "Eres un auditor legal de contratos y políticas de compra. Analiza la cláusula poniendo "
        "foco en jurisdicción, mecanismo de resolución de conflictos, cumplimiento de leyes y "
        "normativas, confidencialidad, protección de datos y responsabilidad de las partes. "
        "Señala obligaciones ambiguas o desequilibradas. Usa 'Legal/Normativo' como "
        "categoria_riesgo. " + formato_reporte +
        "\n\nCláusula:\n{texto}\n\nDatos extraídos:\n{extraccion}"
    )
    |modelo
    |StrOutputParser()
    |(lambda texto: parsear_respuesta_json(texto, claves_reporte))
)

def reporte_revision_manual(motivo):
    #Reporte con las mismas claves del auditor, para cuando no se puede analizar automáticamente
    return {
        "tipo_clausula": "No determinado",
        "categoria_riesgo": "No determinada",
        "nivel_riesgo": "No determinado",
        "requiere_revision_legal": True,
        "montos": [],
        "plazos": [],
        "observaciones": motivo,
        "resumen_simple": "Esta cláusula debe ser revisada manualmente por el equipo de auditoría.",
    }

def clasificacion_no_reconocida(x):
    logger.warning("Clasificación no reconocida: %r. Se deriva a revisión manual", x.get("clasificacion"))
    return reporte_revision_manual(
        f"El modelo no pudo clasificar la cláusula (respondió: {x.get('clasificacion')!r})."
    )

#Condiciones de la bifurcación (cada condicion debe ser una funcion)
def es_financiero_sla(x):
    return x["clasificacion"] == "financiero/sla"

def es_legal_normativo(x):
    return x["clasificacion"] == "legal/normativo"

#RunnableBranch permite generar una condicional para saber que camino elegir
# caminos = RunnableBranch(
#     (condicion1, rama1), IF
#     (condicion2, rama2),ELIF
#     (condicion3, rama3),ELIF
#     rama_por_defecto    ELSE
# ) cada condicion debe ser una funcion 

bifurcacion = RunnableBranch(
    (es_financiero_sla, cadena_financiera_sla),
    (es_legal_normativo, cadena_legal_normativa),
    RunnableLambda(clasificacion_no_reconocida) #ELSE: no gastamos otra petición, va a revisión manual
)

cadena_con_enrutamiento = (
    RunnablePassthrough.assign(extraccion = paso_extraccion)#Passthrough permite agregar propiedades y generar un dicc
    |
    RunnablePassthrough.assign(clasificacion = paso_clasificacion)#el dicc ahora tiene texto, extraccion y clasificacion
    |
    bifurcacion
)

def fallback_con_log(x):
    logger.warning("Cadena principal falló. Activando reporte de revisión manual")
    return reporte_revision_manual("El análisis automático falló; se requiere revisión manual.")

#Fallback: cadena de respaldo. Captura las caidas de mi LLM (rateLimitError, 401, apiconnectionerror, respuestas vacias)
#y también un JSON inválido de las ramas (parsear_respuesta_json lanza ValueError)
respuesta_generica = RunnableLambda(fallback_con_log)

cadena_robusta = cadena_con_enrutamiento.with_fallbacks([respuesta_generica])

#Aca en vez de esto, haremos una funcion para separar responsabilidades y modularizar el proceso
# resultado = cadena_robusta.invoke(
#     {"texto": "Cualquier controversia será resuelta por arbitraje en Santiago"}
# )

# print(resultado)

def procesar_mensaje_seguro(cadena, mensaje):
    #mensaje: texto de la cláusula contractual a auditar
    try:
        return cadena.invoke({"texto": mensaje})
    except Exception as error:
        logger.error("Error procesando cláusula: %s", error)
        return reporte_revision_manual("No pudimos procesar la cláusula en este momento, por favor intenta más tarde.")

#Con este codigo le diremos solamente ejecuta el siguiente codigo si la ejecucion es directa del archivo (python enrutamiento.py). No ejecutes si es import.
if __name__ == "__main__":
    clausulas = [
        (
            "El Proveedor garantiza una disponibilidad mensual del servicio de 99,5%. "
            "Por cada hora adicional de indisponibilidad se aplicará una multa de 2 UF, "
            "con un tope del 10% del valor mensual del contrato."
        ),
        (
            "Cualquier controversia será resuelta por arbitraje en Santiago. El Proveedor "
            "deberá cumplir la Ley 19.628 sobre protección de datos personales."
        ),
    ]
    for mensaje in clausulas:
        print(json.dumps(procesar_mensaje_seguro(cadena_robusta, mensaje), indent=2, ensure_ascii=False))
