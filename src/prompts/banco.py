BANCO_DE_PROMPT = [
    {
        "nombre": "clasificar_clausula_riesgo",
        "system_instruction": (
            "Eres un auditor de contratos, SLAs y políticas de compra. Analiza la cláusula "
            "y responde únicamente con un JSON con las claves 'tipo_clausula' ('Financiera', "
            "'SLA', 'Legal' o 'Normativa'), 'categoria_riesgo' ('Financiero/SLA' o "
            "'Legal/Normativo'), 'nivel_riesgo' ('Bajo', 'Medio' o 'Alto'), "
            "'requiere_revision_legal' (boolean) y 'observaciones' (texto breve)."
        ),
        "ejemplo_usuario": (
            "El Proveedor garantiza una disponibilidad mensual del servicio de 99,5%. "
            "Por cada hora adicional de indisponibilidad se aplicará una multa de 2 UF, "
            "con un tope del 10% del valor mensual del contrato."
        ),
        "claves_esperadas": [
            "tipo_clausula",
            "categoria_riesgo",
            "nivel_riesgo",
            "requiere_revision_legal",
            "observaciones",
        ],
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "tipo_clausula": {"type": "STRING", "enum": ["Financiera", "SLA", "Legal", "Normativa"]},
                "categoria_riesgo": {"type": "STRING", "enum": ["Financiero/SLA", "Legal/Normativo"]},
                "nivel_riesgo": {"type": "STRING", "enum": ["Bajo", "Medio", "Alto"]},
                "requiere_revision_legal": {"type": "BOOLEAN"},
                "observaciones": {"type": "STRING"},
            },
            "required": [
                "tipo_clausula",
                "categoria_riesgo",
                "nivel_riesgo",
                "requiere_revision_legal",
                "observaciones",
            ],
        },
    },
    {
        "nombre": "extraer_montos_y_plazos",
        "system_instruction": (
            "Extrae de la cláusula contractual las partes involucradas, los montos "
            "(multas, topes, pagos) y los plazos que se mencionen. Responde únicamente "
            "con un JSON con las claves 'partes' (lista de textos), 'montos' (lista de "
            "objetos con 'valor' numérico, 'moneda' ('UF', 'USD' o 'CLP') y 'concepto') y "
            "'plazos' (lista de objetos con 'cantidad' numérica, 'unidad' y 'concepto'). "
            "Usa listas vacías si no hay ninguno."
        ),
        "ejemplo_usuario": (
            "Servicios TI Andes SpA deberá entregar los equipos en un plazo de 15 días "
            "hábiles desde la emisión de la orden de compra. El retraso dará lugar a una "
            "multa de 0,5 UF por día, hasta un máximo de 30 UF."
        ),
        "claves_esperadas": ["partes", "montos", "plazos"],
        "response_schema": {
            "type": "OBJECT",
            "properties": {
                "partes": {"type": "ARRAY", "items": {"type": "STRING"}},
                "montos": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "valor": {"type": "NUMBER"},
                            "moneda": {"type": "STRING", "enum": ["UF", "USD", "CLP"]},
                            "concepto": {"type": "STRING"},
                        },
                        "required": ["valor", "moneda", "concepto"],
                    },
                },
                "plazos": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "cantidad": {"type": "NUMBER"},
                            "unidad": {"type": "STRING"},
                            "concepto": {"type": "STRING"},
                        },
                        "required": ["cantidad", "unidad", "concepto"],
                    },
                },
            },
            "required": ["partes", "montos", "plazos"],
        },
    },
]
