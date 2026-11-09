from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI #Modelo
from langchain_core.prompts import PromptTemplate #Plantilla - prompt dinámico
from langchain_core.output_parsers import StrOutputParser #Parsea la respuesta y transforma en solo texto útil
from langchain_core.prompts import ChatPromptTemplate #Plantilla que incluye rol de sistema e instruccion
from consumir_gemini import parsear_respuesta_json #Valida que la respuesta final sea el JSON del auditor

load_dotenv()

modelo = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite")

#Claves del reporte final (las mismas del esquema JSON del auditor en el README)
claves_reporte = [
    "tipo_clausula",
    "categoria_riesgo",
    "nivel_riesgo",
    "requiere_revision_legal",
    "montos",
    "plazos",
    "observaciones",
    "resumen_simple",
]

#Paso 1: Extracción -> saca TODOS los datos de la cláusula, copiando las cifras tal cual
plantilla_extraccion = PromptTemplate.from_template(
    "Eres un auditor de contratos, SLAs y políticas de compra. Lee la siguiente cláusula "
    "contractual y extrae, uno por línea y sin desarrollarlos: las partes involucradas, "
    "la obligación principal, cada monto o multa (con su moneda), cada plazo, los topes "
    "y la forma de cobro. Copia las cifras exactamente como aparecen. Si un dato no "
    "aparece, escribe 'No indicado':\n\n {texto}"
)

paso_extraccion = plantilla_extraccion | modelo | StrOutputParser()

texto_prueba = (
    "El Proveedor garantiza una disponibilidad mensual "

    "del servicio de 99,5%. Por cada hora adicional "

    "de indisponibilidad se aplicará una multa de 2 UF, "

    "con un tope del 10% del valor mensual del contrato. "

    "La multa se descontará de la factura del mes "

    "siguiente al incumplimiento."
    )
#Paso 1
#extraccion = paso_extraccion.invoke({"texto": texto_prueba})

#print(extraccion)

#Paso 2: Clasificación y riesgo -> decide tipo de cláusula, categoría y nivel de riesgo
#Como cada paso solo ve la salida del anterior, se le pide repetir los datos extraídos
#para que el paso 3 no los pierda.
plantilla_clasificacion_riesgo = PromptTemplate.from_template(
    "Eres un auditor de contratos. A partir de estos datos extraídos de una cláusula:\n\n"
    "{extraccion}\n\n"
    "1. Repite los datos extraídos tal cual, sin cambiar ninguna cifra.\n"
    "2. Indica el tipo de cláusula: Financiera, SLA, Legal o Normativa.\n"
    "3. Indica la categoría de riesgo: Financiero/SLA o Legal/Normativo.\n"
    "4. Indica el nivel de riesgo para la empresa que compra: Bajo, Medio o Alto, "
    "y justifícalo en una línea.\n"
    "5. Indica si requiere revisión legal (sí o no).\n"
    "6. Anota observaciones de auditoría: vacíos, ambigüedades o condiciones desfavorables."
)

paso_clasificacion_riesgo = plantilla_clasificacion_riesgo | modelo | StrOutputParser()

# evaluacion = paso_clasificacion_riesgo.invoke(
#     {"extraccion": extraccion}
# )

# print(evaluacion) #El segundo paso utiliza la respuesta del primer paso

#Paso 3: Reporte -> convierte la evaluación al JSON del auditor (incluye un resumen simple para el analista)
plantilla_reporte = PromptTemplate.from_template(
    "Convierte esta evaluación de auditoría en un JSON válido, sin texto adicional, con "
    "las claves: 'tipo_clausula' (texto), 'categoria_riesgo' (texto), 'nivel_riesgo' "
    "(texto), 'requiere_revision_legal' (boolean), 'montos' (lista de objetos con "
    "'valor' numérico, 'moneda' y 'concepto'), 'plazos' (lista de objetos con 'cantidad' "
    "numérica, 'unidad' y 'concepto'), 'observaciones' (texto) y 'resumen_simple' "
    "(máximo 2 frases sin jerga legal para un analista de compras, sin cambiar las cifras):"
    "\n\n{evaluacion}"
)

paso_reporte = plantilla_reporte | modelo | StrOutputParser()

# reporte = paso_reporte.invoke(
#     {"evaluacion": evaluacion}
# )

# print(reporte)

#Ahora haremos todos los 3 pasos pero en uno encadenando resultados y respuestas

cadena_tres_pasos = (
    plantilla_extraccion
    |modelo
    |StrOutputParser()
    |(lambda extraccion : {"extraccion": extraccion}) #sintaxis lamba = lambda argumentos: expresion o retorno
    |plantilla_clasificacion_riesgo #acá necesito la extracción del paso anterior, para eso usamos la funcion que la tome y la devuelva como un dicc.
    |modelo
    |StrOutputParser()
    |(lambda evaluacion : {"evaluacion": evaluacion})
    |plantilla_reporte
    |modelo 
    |StrOutputParser()
    |(lambda reporte : parsear_respuesta_json(reporte, claves_reporte)) #valida que el JSON traiga todas las claves
)

respuesta = cadena_tres_pasos.invoke(
    {"texto": texto_prueba}
)#se pasa el primer texto

print(respuesta)
