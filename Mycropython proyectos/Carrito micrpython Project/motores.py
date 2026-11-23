from machine import Pin, PWM
from time import sleep_ms
DEBUG = False   # True para mostrar mensajes de depuración

def log(*args):
    if DEBUG:
        print(*args)
#___________________________________________________________________________________________________________________#
# El carro es tipo control remoto: un motor de TRACCION (mueve las ruedas) y un motor de DIRECCION
# (dobla las ruedas de adelante; un resorte las regresa al centro cuando el motor se apaga).
#
# Pines de la Pico conectados al L298N (numeros GP, no pines fisicos)
PIN_ENA, PIN_IN1, PIN_IN2 = 16, 17, 18   # Motor 1 -> OUT1 / OUT2
PIN_ENB, PIN_IN3, PIN_IN4 = 19, 20, 21   # Motor 2 -> OUT3 / OUT4

# ---- AJUSTES (cambialos segun lo que veas al probar) ----
TRACCION_ES_MOTOR = 2          # 1 o 2: cual motor mueve el carro. El otro es la direccion.
INVERTIR_TRACCION = False      # True si con pwm positivo el carro va hacia atras
INVERTIR_DIRECCION = False     # True si dir -1 dobla a la derecha en vez de a la izquierda

FREQ = 1000                           # frecuencia del PWM en Hz
MIN_DUTY = int(500 / 1023 * 65535)    # ~32000: minimo para que gire la traccion (nivel 1)
MAX_DUTY = 65535                      # maximo (nivel 4)
DUTY_DIRECCION = 65535                # fuerza del motor de direccion (100 % = dobla hasta el tope)
TIEMPO_GIRO = 1000                    # ms que se mantienen dobladas las ruedas con dir -1 / dir 1
TIEMPO_CENTRADO = 60                  # ms del empujon al lado contrario al volver a recto (0 = sin empujon)
                                      # sube si las ruedas quedan torcidas hacia el ultimo giro;
                                      # baja si se pasan del centro hacia el otro lado
POTENCIA_DEFECTO = 2                  # potencia que usa dir si el carro esta parado
#___________________________________________________________________________________________________________________#
class Motor:
    def __init__(self, pin_en, pin_a, pin_b, invertir=False):
        self.en = PWM(Pin(pin_en)); self.en.freq(FREQ)
        self.a = Pin(pin_a, Pin.OUT)
        self.b = Pin(pin_b, Pin.OUT)
        self.invertir = invertir
        self.mover(0)

    def _sentido(self, adelante):
        if self.invertir:
            adelante = not adelante
        self.a.value(1 if adelante else 0)
        self.b.value(0 if adelante else 1)

    def mover(self, nivel):
        """Traccion. nivel: -4..4 (signo = sentido, 0 = parado)"""
        if nivel == 0:
            self.apagar()
            return
        self._sentido(nivel > 0)
        paso = (MAX_DUTY - MIN_DUTY) / 3
        duty = int(MIN_DUTY + (abs(nivel) - 1) * paso)
        self.en.duty_u16(duty)
        log("  motor: nivel", nivel, "| duty =", duty)

    def empujar(self, lado):
        """Direccion. lado: -1 = izquierda, 1 = derecha, 0 = suelta (el resorte centra las ruedas)"""
        if lado == 0:
            self.apagar()
            return
        self._sentido(lado < 0)
        self.en.duty_u16(DUTY_DIRECCION)
        log("  direccion:", "izquierda" if lado < 0 else "derecha")

    def apagar(self):
        self.a.value(0); self.b.value(0)
        self.en.duty_u16(0)
#___________________________________________________________________________________________________________________#
_m1 = Motor(PIN_ENA, PIN_IN1, PIN_IN2)
_m2 = Motor(PIN_ENB, PIN_IN3, PIN_IN4)
traccion, direccion = (_m1, _m2) if TRACCION_ES_MOTOR == 1 else (_m2, _m1)
traccion.invertir = INVERTIR_TRACCION
direccion.invertir = INVERTIR_DIRECCION

nivel_actual = 0   # ultima potencia de traccion (negativa = reversa)
lado_actual = 0    # hacia donde estan dobladas las ruedas (-1, 0, 1)


# ---------------------------------------------------------------- funciones para los patrones
def avanzar(nivel):
    """Traccion a ese nivel (-4..4) sin tocar la direccion."""
    global nivel_actual
    nivel_actual = nivel
    traccion.mover(nivel)


def doblar(lado):
    """Ruedas de adelante: -1 izquierda, 0 recto, 1 derecha. Se quedan asi hasta que se cambie.
    Al volver a recto despues de un giro, da un empujon corto al lado contrario para centrarlas."""
    global lado_actual
    if lado == 0 and lado_actual != 0 and TIEMPO_CENTRADO > 0:
        direccion.empujar(-lado_actual)
        sleep_ms(TIEMPO_CENTRADO)
    direccion.empujar(lado)
    lado_actual = lado


def parar():
    """Detiene todo: traccion parada y ruedas al centro (lo usan el servidor y los patrones)."""
    avanzar(0)
    doblar(0)


# ---------------------------------------------------------------- comandos pwm y dir
def cmd_pwm(v):
    if v not in range(-4, 5):
        print("pwm fuera de rango (-4 a 4)"); return
    avanzar(v)                        # solo la traccion: la direccion queda como estaba
    print("pwm", v)


def cmd_dir(v):
    if v not in (-1, 0, 1, 2):
        print("dir fuera de rango (-1,0,1,2)"); return
    n = abs(nivel_actual) if nivel_actual != 0 else POTENCIA_DEFECTO
    if v == 0:                        # recto
        doblar(0)
        avanzar(n)
    elif v in (-1, 1):                # izquierda / derecha: dobla, avanza y vuelve a recto
        print("girando", "izquierda..." if v == -1 else "derecha...")
        doblar(v)
        avanzar(n)
        sleep_ms(TIEMPO_GIRO)
        doblar(0)
        print("giro terminado")
    elif v == 2:                      # retroceder, con las ruedas rectas
        doblar(0)
        avanzar(-n)
    print("dir", v)

"""
Explicacion del codigo

El carro es tipo control remoto: un motor de traccion (el que mueve el carro hacia adelante o atras) y un
motor de direccion (el que dobla las ruedas de adelante). Los dos estan conectados al L298N: uno en
OUT1/OUT2 (motor 1) y el otro en OUT3/OUT4 (motor 2). TRACCION_ES_MOTOR dice cual es cual.

Clase Motor
- mover(nivel): para la traccion. El signo decide el sentido y el valor la velocidad: el nivel 1 usa
  MIN_DUTY, el 4 usa MAX_DUTY y el 2 y 3 quedan repartidos en partes iguales entre ambos.
- empujar(lado): para la direccion. Le da toda la fuerza (DUTY_DIRECCION) hacia un lado para doblar las
  ruedas hasta el tope. Con lado 0 se apaga y el resorte del carro regresa las ruedas al centro.
- TIEMPO_CENTRADO: el resorte de la direccion a veces no endereza del todo las ruedas despues de un giro.
  Por eso, al volver a recto, el motor de direccion empuja un instante hacia el lado contrario.
- INVERTIR_TRACCION / INVERTIR_DIRECCION corrigen el sentido si los cables del motor quedaron al reves,
  sin tener que cambiarlos en el L298N.

Comandos
- pwm v (-4 a 4): solo cambia la velocidad de la traccion. Ya no mueve la direccion.
- dir 0: ruedas rectas y avanza (si estaba parado, con POTENCIA_DEFECTO).
- dir -1 / dir 1: dobla a la izquierda / derecha, avanza durante TIEMPO_GIRO y regresa las ruedas a recto.
- dir 2: ruedas rectas y retrocede.

Funciones para los patrones: avanzar(nivel), doblar(lado) y parar().
"""
