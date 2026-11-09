estudiante = {
    "nombre": "Ana",
    "edad": 24,
    "curso": {
        "nombre" : "Python",
        "calificacion": 92
    },
    "tareas": [
        {
            "titulo": "Variables",
            "completada": True
        },
        {
            "titulo": "Consumo de APis",
            "completada": False
        }
    ]


}

print( estudiante["nombre"]) #El nombre del estudiante
print( estudiante["curso"]["calificacion"])#La calificación del curso
print(estudiante["tareas"][1]["titulo"]) #La segunda tarea del estudiante
print("La primera tarea está completada" if estudiante["tareas"][0] else "no esta comletada") #Ternario 