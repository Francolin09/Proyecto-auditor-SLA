# try: intentar, puede causar error 
#except: si sucede ese error haz X
#finally: ejecuta SIEMPRE sin importar si hubo o no excepcion, normalmente para cerrar conexiones 
#raise: levantar error, lanza explicitamente una excepcion
#else: lo que se ejecuta si NO hubo ningun error 

'''
SINTAXIS:
try:
   #Bloque de codigo que quiero intentar de realizar
except Error:
  #Bloque de codigo que quiero que se ejecute si ocurre la excepcion   
'''

try:
    x = 10
    y = 0
    resultado = x/y
except ZeroDivisionError:
    print("No puedo dividir entre cero")    


def dividir ():
    try:
        num1 = int(input("ingresa el primer numero: "))
        num2 = int(input("ingresa el segundo numero: "))
        resultado = num1/num2
        print(f"el resultado es {resultado}")
    except ValueError:
        print("La calculadora solo permite números enteros")
    except ZeroDivisionError:
        print("La calculadora no puede dividir entre cero")
    except Exception as error:
        print(f"Ocurrió un error inesperado {error}")
    finally:
        print("Gracias por usar esta calculadora") 
        
dividir()   

try:
    bebidas = ["Coca-cola", "Fanta", "Sprite"]
    bebida_deseada = input("Ingresa tu bebida deseada: ")
    if bebida_deseada not in bebidas:
        raise ValueError(f"Esa bebida no está disponible") #Lanza error
    else:
        print(f"tu bebida {bebida_deseada} está lista")
except ValueError as error: #Manejamos el error que lanzamos
    print(f"Error: {error}")        