from machine import Pin, PWM
from time import sleep_ms
#___________________________________________________________________________________________________________________#
# Pines de los motores
PIN_ENA, PIN_IN1, PIN_IN2 = 16, 17, 18   # Motor 1 
PIN_ENB, PIN_IN3, PIN_IN4 = 19, 20, 21   # Motor 2  
print("Sistema listo. MIN_DUTY =", MIN_DUTY)
# hay que confirmar que esos sean los pines por que no me acuerdo como conectamos esa tarjeta

FREQ = 1000 # frecuencia
MIN_DUTY = int(500 / 1023 * 65535)   # ~32000: mínimo para que giren
MAX_DUTY = 65535                      # maximo de giro
TIEMPO_GIRO = 600                    # ms que dura un giro
#_________________________________________________________________________________________________________________________#
class Motor: # aqui si puedo usar poo jejejeje
    def __init__(self, pin_en, pin_a, pin_b): 
        self.en = PWM(Pin(pin_en)); self.en.freq(FREQ)
        self.a = Pin(pin_a, Pin.OUT)
        self.b = Pin(pin_b, Pin.OUT)
        self.mover(0)

    def mover(self, nivel):
        """nivel: -4..4 (signo = sentido, 0 = parado)"""
        if nivel == 0:
            self.a.value(0); self.b.value(0)
            self.en.duty_u16(0)
            print("  motor: parado")
            return
        self.a.value(1 if nivel > 0 else 0)
        self.b.value(0 if nivel > 0 else 1)
        paso = (MAX_DUTY - MIN_DUTY) / 3
        self.en.duty_u16(int(MIN_DUTY + (abs(nivel) - 1) * paso))
        print("  motor: nivel", nivel, "| IN_A =", self.a.value(), "IN_B =", self.b.value(), "| duty =", duty) # para debuguear si no prende
#________________________________________________________________________________________________________________________________________#
izq = Motor(PIN_ENA, PIN_IN1, PIN_IN2)
der = Motor(PIN_ENB, PIN_IN3, PIN_IN4)
nivel_actual = 0

def cmd_pwm(v): # potenica de los motores con listas 
    global nivel_actual
    if v not in range(-4, 5):
        print("pwm fuera de rango (-4 a 4)"); return
    nivel_actual = v
    izq.mover(v); der.mover(v)
    print("pwm", v)

def cmd_dir(v): # direccion
    if v not in (-1, 0, 1, 2):
        print("dir fuera de rango (-1,0,1,2)"); return
    n = nivel_actual if nivel_actual != 0 else 2   # si está parado, usa potencia media
    n = abs(n)
    if v == 0:
        izq.mover(n); der.mover(n)
    elif v == -1:                     # izquierda
        print("girando izquierda...")
        izq.mover(0); der.mover(n)
        sleep_ms(TIEMPO_GIRO); izq.mover(n)
        print("giro terminado")
    elif v == 1:                      # derecha
        print("girando derecha...")
        izq.mover(n); der.mover(0)
        sleep_ms(TIEMPO_GIRO); der.mover(n)
        print("giro terminado")
    elif v == 2:                      # retroceder
        izq.mover(-n); der.mover(-n)
    print("dir", v)

while True: # para que sea un ciclo cada que escribas un valor aceptado en la consola, la consola siempre esperará este entry, si no es un dato valido no hace nada y pide asignar uno nuevo
    partes = input("> ").strip().lower().split()
    print("DEBUG recibido:", partes)
    if len(partes) != 2:
        print("Formato: comando valor (ej: pwm 3)"); continue
    try:
        valor = int(partes[1])
    except ValueError:
        print("El valor debe ser entero"); continue
    if partes[0] == "pwm": cmd_pwm(valor)
    elif partes[0] == "dir": cmd_dir(valor)
    else: print("Comando desconocido")
    
"""
Explicación del código para facilitar la guía.

Pin sirve para controlar pines digitales (encendido/apagado) y PWM para generar la señal modulada. sleep_ms pausa el programa unos milisegundos.
Las constantes definen cómo se comporta el carro:
PIN_ENA, PIN_IN1, PIN_IN2 (y los del motor 2) son los pines de la Pico conectados al L298N.
FREQ = 1000: la señal PWM se repite 1000 veces por segundo.
MIN_DUTY: el enunciado dice que el mínimo es ~500 en escala 0-1023, pero la Pico trabaja en 0-65535, así que se convierte con una regla de tres (≈32000).
MAX_DUTY = 65535: potencia máxima.
TIEMPO_GIRO: cuánto dura un giro, en milisegundos.

La clase Motor
Representa un motor conectado al L298N. Cada motor usa tres pines: uno de Enable (PWM, controla la velocidad) y dos de Input (controlan el sentido).
__init__ crea esos pines, configura la frecuencia del PWM y deja el motor parado.
mover(nivel) recibe un número de -4 a 4:
Si es 0, pone ambos Inputs en 0 y el duty en 0: motor apagado.
Si es positivo, IN_A = 1 y IN_B = 0: gira hacia adelante. Si es negativo, al revés: gira hacia atrás.
La velocidad se calcula así: el nivel 1 corresponde a MIN_DUTY, el nivel 4 a MAX_DUTY, y los niveles 2 y 3
quedan repartidos en partes iguales entre ambos (paso es el tamaño de cada escalón). Se usa abs(nivel) porque el signo solo decide el sentido, no la velocidad.

Se crean dos objetos, uno por rueda. nivel_actual recuerda la última potencia que se pidió con pwm, para que dir sepa con qué fuerza girar.

cmd_pwm(v)
Valida que el valor esté entre -4 y 4. Si es válido, guarda el nivel en nivel_actual y manda ese mismo nivel a ambos motores,
así el carro avanza o retrocede en línea recta. Con pwm 0 se detiene.

cmd_dir(v)
Primero valida que sea -1, 0, 1 o 2. Luego decide la potencia n: usa nivel_actual, y si el carro está parado usa 2 como valor por defecto, para que el giro se note. Después:
0 (recto): los dos motores a la misma velocidad.
-1 (izquierda): el motor izquierdo se detiene y el derecho sigue andando. Esa diferencia hace que el carro gire hacia la izquierda. Se espera TIEMPO_GIRO y se vuelve a
encender el izquierdo, para que el carro siga recto después del giro.
1 (derecha): lo mismo, pero con los motores invertidos.
2 (retroceder): ambos motores con nivel negativo.

El programa se queda esperando que escribas algo en la consola de Thonny. Luego .strip() quita espacios de los extremos, .lower() pasa todo a minúsculas y .split() separa el texto en palabras.
Así "PWM 3" se vuelve ["pwm", "3"].
Si no hay exactamente dos partes, muestra el formato correcto y vuelve a pedir.
El try/except intenta convertir el valor a entero; si escribes pwm abc, avisa del error en vez de que el programa se caiga.
Finalmente, según la primera palabra llama a cmd_pwm o cmd_dir; si no reconoce el comando, lo dice.
"""