from machine import Pin, ADC
DEBUG = False   # True = mensajes de depuración; False = consola limpia
def log(*args):
    if DEBUG:
        print(*args)
#___________________________________________________________________________________________________________________#
# LUCES (registro de corrimiento)
PIN_DATOS = 13    # GP13 (confirmar contra el cableado)
PIN_RELOJ = 12    # GP12 (confirmar contra el cableado)
PIN_LDR = 26      # GP26 = ADC0 (confirmar; solo sirven GP26, GP27 o GP28)

# Qué bit del registro controla cada LED (CONFIRMAR con la prueba de bits)
MASCARA_FRONTAL = 0b00001100
MASCARA_TRASERA = 0b00000011
MASCARA_IZQ     = 0b00010000
MASCARA_DER     = 0b00100000

OSCURO = 10000    # por debajo de esto se considera oscuro (AJUSTAR midiendo)
CLARO = 20000     # por encima de esto se considera claro (AJUSTAR midiendo)

datos = Pin(PIN_DATOS, Pin.OUT)
reloj = Pin(PIN_RELOJ, Pin.OUT)
estado = 0        # guarda qué LEDs están encendidos

def enviar(valor):
    """Manda 8 bits al registro, del bit 7 al 0, un pulso de reloj por bit."""
    for i in range(7, -1, -1):
        datos.value((valor >> i) & 1)
        reloj.value(1)
        reloj.value(0)

def poner_luces(mascara, encender):
    """Enciende o apaga solo los LEDs de la máscara sin tocar los demás."""
    global estado
    if encender:
        estado |= mascara
    else:
        estado &= ~mascara & 0xFF
    enviar(estado)

enviar(0)   # todas las luces apagadas al importar el módulo
#___________________________________________________________________________________________________________________#
# FOTORRESISTENCIA
ldr = ADC(Pin(PIN_LDR))
modo_ldr = False   # True = las luces frontales y traseras las controla el LDR
auto_on = None     # último estado automático (True/False); None = aún no decidido

def leer_ldr():
    return ldr.read_u16()   # 0 a 65535

def actualizar_ldr():
    """Hay que llamarla seguido desde el ciclo principal (main.py)."""
    global auto_on
    if not modo_ldr:
        return
    valor = leer_ldr()
    if valor < OSCURO and auto_on is not True:
        poner_luces(MASCARA_FRONTAL | MASCARA_TRASERA, True)
        auto_on = True
        print("LDR: oscuro (", valor, ") -> luces ON")
    elif valor > CLARO and auto_on is not False:
        poner_luces(MASCARA_FRONTAL | MASCARA_TRASERA, False)
        auto_on = False
        print("LDR: claro (", valor, ") -> luces OFF")
#___________________________________________________________________________________________________________________#
# COMANDOS
def validar_bool(v):
    if v not in (0, 1):
        print("El valor debe ser 0 o 1")
        return False
    return True

def cmd_luz(nombre, mascara, v):
    """Sirve para lf, lb, ll y lr: solo cambia el nombre y la máscara."""
    if not validar_bool(v): return
    if modo_ldr:
        print("Modo LDR activo (se desactiva con ldr 0)"); return
    poner_luces(mascara, v == 1)
    print(nombre, v)

def cmd_lf(v): cmd_luz("lf", MASCARA_FRONTAL, v) # FRONT
def cmd_lb(v): cmd_luz("lb", MASCARA_TRASERA, v) # BACK
def cmd_ll(v): cmd_luz("ll", MASCARA_IZQ, v) # LEFT
def cmd_lr(v): cmd_luz("lr", MASCARA_DER, v) # RIGHT

def cmd_ldr(v):
    global modo_ldr, auto_on
    if not validar_bool(v): return
    modo_ldr = (v == 1)
    auto_on = None    # fuerza a volver a leer la luz
    print("ldr", v)     