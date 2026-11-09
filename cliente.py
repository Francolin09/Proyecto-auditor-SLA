# import time
# from typing import Callable, Any

from src.consumir_gemini import armar_peticion, enviar_peticion, extraer_texto, modelo

# def con_reintento(
#     funcion: Callable[[], Any],
#     intentos: int = 3,
#     espera_segundos: int = 2
# ) -> Any:
#     for intento in range(intentos):
#         try:
#             return funcion()
#         except TimeoutError:
#             if intento == intentos-1:
#                 raise
#             print(f"Intento {intento+1} de {intentos} falló por límite de uso/servidor. Reintentando...")
#             time.sleep(espera_segundos)


# #Cómo ejecuto esto?
# if __name__ == "__main__":
#     url, cuerpo = armar_peticion("Hola", "gemini-3.5-flash-lite", "Eres un asistente amigable")
#     respuesta = con_reintento(lambda: enviar_peticion(url, cuerpo))
#     print(respuesta)


import time
import random
from typing import Callable, Any



def con_reintento(
    funcion: Callable[[], Any],
    intentos: int = 3,
    espera_base: float = 2,
    espera_maxima: float = 30,
) -> Any:
    for intento in range(1, intentos + 1):
        try:
            return funcion()
        except TimeoutError:
            if intento == intentos:
                raise
            espera = min(espera_base * (2 ** (intento - 1)), espera_maxima)
            espera_con_jitter = espera + random.uniform(0, espera * 0.1)
            print(f"Intento {intento} de {intentos} falló. Reintentando en {espera_con_jitter:.1f}s...")
            time.sleep(espera_con_jitter)


COSTO_POR_1000_TOKENS = 0.002  # referencial, ajusta según el modelo que uses
costo_total_sesion = 0.0


def registrar_costo(respuesta: dict) -> float:
    global costo_total_sesion
    uso = respuesta.get("usageMetadata", {})
    total_tokens = uso.get("totalTokenCount", 0)
    costo_estimado = (total_tokens / 1000) * COSTO_POR_1000_TOKENS
    costo_total_sesion += costo_estimado
    print(f"Operación: {total_tokens} tokens, costo estimado: ${costo_estimado:.5f} (acumulado: ${costo_total_sesion:.5f})")
    return costo_estimado


def consultar_modelo(pregunta: str, system_instruction: str = "") -> str:
    url,cuerpo = armar_peticion(pregunta,modelo, system_instruction)
    try:
        respuesta = con_reintento(lambda: enviar_peticion(url,cuerpo))
    except TimeoutError:
        raise RuntimeError("El servicio no respondió tras varios intentos. Intenta más tarde.")
    registrar_costo(respuesta)
    return extraer_texto(respuesta)


if __name__ == "__main__":
    resultado = consultar_modelo(
        "Analiza esta cláusula e indica su tipo, nivel de riesgo y la multa aplicable: "
        "'El Proveedor garantiza una disponibilidad mensual del servicio de 99,5%. "
        "Por cada hora adicional de indisponibilidad se aplicará una multa de 2 UF, "
        "con un tope del 10% del valor mensual del contrato.'",
        "Eres un auditor de contratos, SLAs y políticas de compra. Responde en máximo 3 líneas.",
    )#acá podemos pasar o no pasar el system instruction
    print(resultado)
    # for i in range(15): ESTE ES PARA PROBAR EL RATE LIMIT
    #     try:
    #         respuesta = consultar_modelo(f"Pregunta de prueba número {i}")
    #         print(f"Respuesta {i}: {respuesta[:40]}...")
    #     except RuntimeError as error:
    #         print(f"Respuesta {i} falló definitivamente: {error}")
    #         print(f"Costo total del ensayo: ${costo_total_sesion:.5f}")
