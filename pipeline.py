from pipeline_limpieza import procesar_texto
from pipeline_limpieza import *
from cliente import consultar_modelo
import json

# referencia = "El cielo es azul."
# respuesta = "el cielo es azul"

# tokens_referencia = referencia.split()
# tokens_respuesta = respuesta.split()

# comunes = set(tokens_referencia) & set(tokens_respuesta)
# print(comunes)

# if tokens_referencia:
#     proporcion = len(comunes) / len(set(tokens_referencia))
#     #2/4 = 0.5 = 50%
# else:
#     proporcion = 0.0

# print(f"Coincidencia: {proporcion:.0%}")        

############################################


# referencia = "El cielo es azul."
# respuesta = "el cielo es azul"

# tokens_referencia = procesar_texto(referencia)
# tokens_respuesta = procesar_texto(respuesta)

# comunes = set(tokens_referencia) & set(tokens_respuesta)
# print(comunes)

# if tokens_referencia:
#     proporcion = len(comunes) / len(set(tokens_referencia))
#     #2/4 = 0.5 = 50%
# else:
#     proporcion = 0.0

# print(f"Coincidencia: {proporcion:.0%}")

###################################################

# Las funciones de métricas quedan a nivel de módulo para poder importarlas (y probarlas)
# sin disparar peticiones al modelo. La ejecución del ensayo está al final, en __main__.

def contar_coincidencias(tokens_referencia:list[str], tokens_respuesta:list[str]) -> int:
    conteo_referencia = Counter(tokens_referencia)
    conteo_respuesta = Counter(tokens_respuesta)
    interseccion = conteo_referencia & conteo_respuesta
    print("Interseccion: ", interseccion)
    return sum(interseccion.values())

def calcular_precision_cobertura_f1(tokens_referencia: list[str],tokens_respuesta: list[str],) -> dict[str, float]:
    """Calcula precisión, cobertura y F1 de dos listas de tokens."""
    coincidencias = contar_coincidencias(tokens_referencia, tokens_respuesta)

    if not tokens_respuesta or not tokens_referencia:
        return {"precision": 0.0, "cobertura": 0.0, "f1": 0.0}

    precision = coincidencias / len(tokens_respuesta)
    cobertura = coincidencias / len(tokens_referencia)

    if precision + cobertura == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * cobertura / (precision + cobertura)

    resultado = {
        "precision": precision,
        "cobertura": cobertura,
        "f1": f1,
    }

    return resultado

def calcular_metricas(texto_referencia, texto_respuesta):

    tokens_referencia = procesar_texto(texto_referencia)
    tokens_respuesta = procesar_texto(texto_respuesta)

    return calcular_precision_cobertura_f1(tokens_referencia, tokens_respuesta)

def resumir_metricas(resultados):

    if not resultados:
        return {
            "precision_promedio": 0,
            "cobertura_promedio": 0,
            "f1_promedio": 0,
        }

    n = len(resultados)

    return {
        "precision_promedio": sum(
            r["precision"] for r in resultados
        ) / n,

        "cobertura_promedio": sum(
            r["cobertura"] for r in resultados
        ) / n,

        "f1_promedio": sum(r["f1"] for r in resultados) / n,
    }

# Casos de evaluación del auditor: (consulta con la cláusula, referencia esperada)
casos = [

    (
        "Clasifica en una frase el tipo, el riesgo y la multa de esta cláusula: "
        "'Por cada hora de indisponibilidad bajo el 99,5% mensual se aplicará "
        "una multa de 2 UF, con tope del 10% del valor mensual del contrato.'",
        "Cláusula SLA de riesgo alto con multa de 2 UF por hora y tope del 10% mensual.",
    ),

    (
        "Indica en una frase el plazo y la multa de esta cláusula: "
        "'Servicios TI Andes SpA deberá entregar los equipos en 15 días hábiles "
        "desde la orden de compra; el retraso tendrá una multa de 0,5 UF por día, "
        "hasta un máximo de 30 UF.'",
        "Plazo de entrega de 15 días hábiles con multa de 0,5 UF por día y máximo de 30 UF.",
    ),

    (
        "Clasifica en una frase el tipo y el riesgo de esta cláusula: "
        "'Cualquier controversia será resuelta por arbitraje en Santiago y el "
        "Proveedor deberá cumplir la Ley 19.628 de protección de datos personales.'",
        "Cláusula legal normativa de riesgo medio sobre arbitraje y protección de datos.",
    ),

]


if __name__ == "__main__":

    consulta = casos[0][0]

    referencia = casos[0][1]

    respuesta = consultar_modelo(consulta)

    texto_crudo_ref = referencia.split()
    texto_crudo_resp = respuesta.split()

    comunes_crudo = set(texto_crudo_ref) & set(texto_crudo_resp)

    proporcion_crudos = len(comunes_crudo)/ len(set(texto_crudo_ref))

    tokens_ref = procesar_texto(referencia)
    tokens_resp = procesar_texto(respuesta)

    comunes = set(tokens_ref) & set(tokens_resp)
    proporcion_procesados = len(comunes) / len(set(tokens_ref))

    print(f"[Caso 1] Coincidencia texto crudo {proporcion_crudos:.1%}")
    print(f"[Caso 2] Coincidencia texto procesado {proporcion_procesados:.1%}")
    #Este funciona pero omite cuando una palabra se repite y eso puede generar problemas entendiendo el contexto

    print("token respuesta: ",tokens_resp)
    print("token referencia: ",tokens_ref)    
    print(contar_coincidencias(tokens_ref,tokens_resp))

    calcular_precision_cobertura_f1(tokens_ref,tokens_resp)    

    resultados = []
    for consulta, referencia in casos:

        respuesta = consultar_modelo(consulta)
        metricas = calcular_metricas(referencia, respuesta)
        print(consulta, metricas)
        resultados.append({
            "consulta": consulta,
            "respuesta": respuesta,
            **metricas,
        })


    with open(
        "resultados_metricas.json", "w", encoding="utf-8"
    ) as archivo:

        json.dump(resultados, archivo, indent=2, ensure_ascii=False)

    peores_casos = sorted(resultados, key=lambda r: r["f1"])
    muestra_para_revisar = peores_casos[:5] + peores_casos[-5:]
    for caso in peores_casos[:3]:
        print(caso["consulta"], caso["f1"])
# Output esperado: sobre un conjunto ilustrativo de 12 resultados ya calculados (con "f1" entre 0.12 y 0.93), 
# la muestra combina los 5 peores y los 5 mejores, sin los del medio:

# Consulta 1 0.12

# Consulta 2 0.18

# Consulta 3 0.25

# Consulta 4 0.31

# Consulta 5 0.33

# Consulta 8 0.62

# Consulta 9 0.68

# Consulta 10 0.74

# Consulta 11 0.81

# Consulta 12 0.93
# Los primeros cinco ("f1" más bajo) te muestran dónde tu cliente falla de verdad. Los últimos cinco ("f1" más alto) 
# confirman que un puntaje casi perfecto también significa una respuesta casi perfecta, y no un falso positivo como los del Bloque 16.
