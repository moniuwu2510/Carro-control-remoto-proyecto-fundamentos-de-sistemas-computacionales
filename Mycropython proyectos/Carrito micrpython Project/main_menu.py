# Comandos validos
#   pwm <-4..4>   -> avanzar/retroceder en línea recta con esa potencia  POTENCIA INVERSA ACTIVA REVERSA
#   dir <-1,0,1,2>-> -1 izquierda, 1 derecha, 0 recto, 2 retroceder        
#   lf, lb, ll, lr, ldr <valor> -> comandos de las luces (los define luces.py)
#   circle, infinite, zigzag, especial -> patrones de movimiento, SIN valor
# _______________________________________________________________________________
from time import sleep_ms      
import sys, select             
import motores                 # control de las ruedas: cmd_pwm, cmd_dir, parar, etc.
import luces                   # control de las luces y del sensor LDR
import comportamiento          # los 4 patrones: circle, infinite, zigzag, especial
# ---------- Tabla de patrones ----------
PATRONES = {
    "circle": comportamiento.circle,
    "infinite": comportamiento.infinite,
    "zigzag": comportamiento.zigzag,
    "especial": comportamiento.especial,
}

def procesar(linea):
    """Recibe una línea escrita en la consola, decide qué comando es y lo ejecuta."""

    # Limpia el texto: strip() quita espacios y el salto de línea de los extremos,
    # lower() pasa todo a minúsculas y split() separa en palabras.
    # Ej: "  PWM 3 \n"  ->  ["pwm", "3"]      "Circle"  ->  ["circle"]
    partes = linea.strip().lower().split()

    # Caso 1: una sola palabra y es un patrón (circle, infinite, zigzag o especial).
    # Los patrones no llevan valor, por eso solo se revisa una palabra.
    if len(partes) == 1 and partes[0] in PATRONES:
        PATRONES[partes[0]]()      # busca la función en el diccionario y la ejecuta (los paréntesis la llaman)
        return                     # termina aquí; no sigue con el resto de la función

    # Caso 2: cualquier otra cosa debe tener exactamente 2 partes: comando y valor.
    # Si no, muestra el formato correcto y vuelve a esperar.
    if len(partes) != 2:
        print("Formato: comando valor (ej: pwm 3) | circle, infinite, zigzag, especial")
        return

    # El valor llega como texto ("3"); int() lo convierte a número entero.
    # Si escribes algo que no es número (ej: pwm abc), int() da error (ValueError);
    # el try/except lo captura para que el programa NO se caiga.
    try:
        valor = int(partes[1])
    except ValueError:
        print("El valor debe ser entero")
        return

    # Según la primera palabra se llama a la función del módulo correspondiente.
    # Cada función (cmd_pwm, cmd_dir, cmd_lf...) valida su propio rango de valores. Se valida con las simples condicionales y los valores ya existentes en otro código
    comando = partes[0]
    if comando == "pwm": motores.cmd_pwm(valor)        # potencia recta de las dos ruedas
    elif comando == "dir": motores.cmd_dir(valor)      # giro / recto / retroceder
    elif comando == "lf": luces.cmd_lf(valor)          # comandos de luces: los define luces.py
    elif comando == "lb": luces.cmd_lb(valor)
    elif comando == "ll": luces.cmd_ll(valor)
    elif comando == "lr": luces.cmd_lr(valor)
    elif comando == "ldr": luces.cmd_ldr(valor)        # modo del sensor de luz (LDR)
    else: print("Comando desconocido:", comando)       # ninguna opción coincidió entonces solicitará un valor valido con su respectivo formato

# ---------- Preparar la lectura de la consola ----------
# input() se queda congelado esperando el ingreso de un valor
poll = select.poll()
poll.register(sys.stdin, select.POLLIN)   # vigila la entrada de la consola

# ---------- Programa principal ----------
print("Sistema listo. Comandos: pwm, dir, lf, lb, ll, lr, ldr, circle, infinite, zigzag, especial")
print("> ", end="")                       # end="" evita el salto de línea: el cursor queda junto al ">"

while True:                               # ciclo infinito: el programa nunca termina solo (Ctrl+C lo detiene)
    if poll.poll(0):                      # poll(0) pregunta sin esperar
        procesar(sys.stdin.readline())    # lee la línea completa y la manda a procesar
        print("> ", end="")               # vuelve a mostrar el prompt para el siguiente comando
    luces.actualizar_ldr()                # en cada vuelta revisa el sensor de luz, así el modo LDR sigue funcionando
    sleep_ms(50)                          # descansa 50 ms para no saturar la Pico

# NOTA: mientras corre un patrón (circle, infinite, zigzag, especial) el ciclo queda ocupado
# dentro de procesar(), por eso luces.actualizar_ldr() no se ejecuta hasta que el patrón termina.
