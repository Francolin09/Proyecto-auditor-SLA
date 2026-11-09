from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables import RunnableBranch
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (RunnableBranch, RunnablePassthrough, RunnableLambda )

load_dotenv()
modelo = ChatGoogleGenerativeAI(model = "gemini-3.1-flash-lite")
plantilla_clasificacion = PromptTemplate.from_template(
    "Clasifica el siguiente mensaje de soporte en una sola palabra: "
    "pregunta, queja o sugerencia. Responde solo con esa palabra. \n\n {mensaje}"
)

paso_clasificacion = (
    plantilla_clasificacion
    | modelo
    |StrOutputParser()
    |(lambda texto:texto.strip().lower())
)
# mensaje_prueba = "Mi telefono no está funcionando"
# clasificacion = paso_clasificacion.invoke({"mensaje": mensaje_prueba})

# print(clasificacion)

cadena_pregunta = (
    PromptTemplate.from_template("Responde a esta pregunta técnica con precision: \n\n {mensaje}")
    |modelo
    |StrOutputParser()
)

cadena_queja = (
    PromptTemplate.from_template("Responde a esta queja con empatía, reconociendo el problema antes de ofrecer una solución y sin opciones, solo la respuesta: \n\n {mensaje}")
    |modelo
    |StrOutputParser()
)

cadena_sugerencia = (
    PromptTemplate.from_template("agradece esta sugerencia y explica cómo se evaluará dentro del producto: \n\n {mensaje}")
    |modelo
    |StrOutputParser()
)

#RunnableBranch permite generar una condicional para saber que camino elegir
# caminos = RunnableBranch(
#     (condicion1, rama1), IF
#     (condicion2, rama2),ELIF
#     (condicion3, rama3),ELIF
#     rama_por_defecto    ELSE
# ) cada condicion debe ser una funcion 

bifurcacion = RunnableBranch(
    (lambda x: x["clasificacion"] == "queja", cadena_queja),
    (lambda x: x["clasificacion"] == "sugerencia", cadena_sugerencia),
    cadena_pregunta
)

cadena_con_enrutamiento = (
    RunnablePassthrough.assign(clasificacion = paso_clasificacion)#Passthrough permite agregar propiedades y generar un dicc
    |
    bifurcacion
)

#Fallback: cadena de respaldo. Captura las caidas de mi LLM (rateLimitError, 401, apiconnectionerror, respuestas vacias)
respuesta_generica = RunnableLambda( lambda x: ("Gracias por tu mensaje, un mimebro de nuestro equipo te responderá pronto"))

cadena_robusta = cadena_con_enrutamiento.with_fallbacks([respuesta_generica])

#Aca en vez de esto, haremos una funcion para separar responsabilidades y modularizar el proceso
# resultado = cadena_robusta.invoke(
#     {"mensaje": "Deberían tener más agentes disponibles"}
# )

# print(resultado)

def procesar_mensaje_seguro(cadena, mensaje):
    try:
        return cadena.invoke({"mensaje": mensaje})
    except Exception as error:
        return "No pudimos procesar tu mensaje en este momento, por favor intenta más tarde"

#Con este codigo le diremos solamente ejecuta el siguiente codigo si la ejecucion es directa del archivo (python enrutamiento.py). No ejecutes si es import.
if __name__ == "__main__":
    mensaje = "Llevo varios dias sin poder entrar a mi cuenta"
    print(procesar_mensaje_seguro(cadena_robusta,mensaje))


