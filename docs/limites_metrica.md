# Límites de la métrica de evaluación del Auditor


## Qué mide

Coincidencia de tokens normalizados (`procesar_texto`) entre
la referencia esperada del auditor y la respuesta del modelo,
contando repeticiones con `Counter` para calcular `precision`,
`cobertura` y `f1` (`pipeline.py`).


## Modos de falla conocidos

- Respuestas extensas (el modelo explica la cláusula completa)
  hunden `precision` y `f1` aunque la `cobertura` sea alta.
- Sinónimos del dominio puntúan bajo al exigir coincidencia
  exacta tras `limpiar_texto` (ej. `UF` vs. `unidades de
  fomento`, `multa` vs. `penalidad`, `SLA` vs. `nivel de
  servicio`).
- `limpiar_texto` elimina la coma decimal y el símbolo `%`:
  `0,5 UF` → `05 uf` y `99,5%` → `995`. Montos y porcentajes
  pierden su formato y pueden coincidir con números distintos
  (cubierto por `test_procesar_texto_une_decimales_limite_conocido`).
- Montos, plazos o niveles de riesgo erróneos (ej. `2 UF` vs.
  `20 UF`, `Alto` vs. `Bajo`) y negaciones (`no aplica multa`)
  cambian pocos tokens sin reflejar el error en el puntaje.


## Muestra revisada

Pendiente de regenerar: `resultados_metricas.json` se reinició
al cambiar al dominio de contratos. Ejecutar `python pipeline.py`
para evaluar los 3 casos de `casos` (SLA, plazo de compra y
cláusula legal) y revisar los extremos con `peores_casos[:3]` y
`peores_casos[:5] + peores_casos[-5:]`.


## Recomendación de uso

Usar `resumir_metricas` (`f1_promedio`) pidiendo respuestas de
una frase en `consultar_modelo`, y revisar a mano montos, plazos
y nivel de riesgo: la métrica no detecta errores numéricos.
