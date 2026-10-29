from machine import Pin, PWM
from time import sleep_ms

DEBUG = False   # True = mensajes de depuración; False = consola limpia

def log(*args):
    if DEBUG:
        print(*args)
#___________________________________________________________________________________________________________________#
# Pines de los motores (números GP de la Pico, no pines físicos)
PIN_ENA, PIN_IN1, PIN_IN2 = 16, 17, 18   # Motor 1 (izquierdo)
PIN_ENB, PIN_IN3, PIN_IN4 = 19, 20, 21   # Motor 2 (derecho)

FREQ = 1000                           # frecuencia del PWM en Hz
MIN_DUTY = int(500 / 1023 * 65535)    # ~32000: mínimo para que giren
MAX_DUTY = 65535                      # máximo de giro
TIEMPO_GIRO = 600                     # ms que dura un giro
POTENCIA_DEFECTO = 2                  # potencia de dir si el carro está parado
#___________________________________________________________________________________________________________________#
class Motor:
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
            log("  motor: parado")
            return
        self.a.value(1 if nivel > 0 else 0)
        self.b.value(0 if nivel > 0 else 1)
        paso = (MAX_DUTY - MIN_DUTY) / 3
        duty = int(MIN_DUTY + (abs(nivel) - 1) * paso)
        self.en.duty_u16(duty)
        log("  motor: nivel", nivel, "| IN_A =", self.a.value(), "IN_B =", self.b.value(), "| duty =", duty)
#___________________________________________________________________________________________________________________#
izq = Motor(PIN_ENA, PIN_IN1, PIN_IN2)
der = Motor(PIN_ENB, PIN_IN3, PIN_IN4)
nivel_actual = 0   # última potencia pedida (negativa = reversa)

def parar():
    """Detiene los dos motores (lo usan otros módulos, como comportamiento)."""
    global nivel_actual
    nivel_actual = 0
    izq.mover(0); der.mover(0)

def cmd_pwm(v):
    global nivel_actual
    if v not in range(-4, 5):
        print("pwm fuera de rango (-4 a 4)"); return
    nivel_actual = v
    izq.mover(v); der.mover(v)
    print("pwm", v)

def cmd_dir(v):
    global nivel_actual
    if v not in (-1, 0, 1, 2):
        print("dir fuera de rango (-1,0,1,2)"); return
    n = abs(nivel_actual) if nivel_actual != 0 else POTENCIA_DEFECTO
    if v == 0:                        # recto
        nivel_actual = n
        izq.mover(n); der.mover(n)
    elif v == -1:                     # izquierda
        print("girando izquierda...")
        izq.mover(0); der.mover(n)
        sleep_ms(TIEMPO_GIRO); izq.mover(n)
        nivel_actual = n
        print("giro terminado")
    elif v == 1:                      # derecha
        print("girando derecha...")
        izq.mover(n); der.mover(0)
        sleep_ms(TIEMPO_GIRO); der.mover(n)
        nivel_actual = n
        print("giro terminado")
    elif v == 2:                      # retroceder
        nivel_actual = -n
        izq.mover(-n); der.mover(-n)
    print("dir", v)

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

NOTA: AL FINALIZAR ESTE CODIGO SE HICIERON MAS CAMBIOS PARA QUE QUEDE TODO TIPO DE INPUT EN UN SOLO CODIGO, TODO SE EJECUTA CON MAIN MENU
"""