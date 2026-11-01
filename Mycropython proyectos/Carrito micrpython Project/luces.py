from machine import Pin, ADC 

DEBUG = False  # ignore el copy paste todas lo tienen 

def log(*args):
    """Como print, pero solo imprime si DEBUG = True."""
    if DEBUG:
        print(*args)
#___________________________________________________________________________________________________________________#
# ---------- LUCES (registro de corrimiento) ----------

# Pines de la Pico (números GP, no los números físicos del pin)
PIN_DATOS = 13    # GP13: por aquí salen los bits hacia el registro (confirmar contra el cableado)
PIN_RELOJ = 12    # GP12: cada pulso aquí le dice al registro "lee el bit que hay en datos" (confirmar contra el cableado)
PIN_LDR = 26      # GP26 = ADC0 (confirmar; solo sirven GP26, GP27 o GP28 porque son los pines analógicos)

# Cada salida del registro es un bit de un número de 8 bits (0b = escrito en binario).
# El 1 está en la posición de la salida: bit 0 = QA, bit 1 = QB, ... bit 5 = QF
QA = 0b00000001
QB = 0b00000010
QC = 0b00000100
QD = 0b00001000
QE = 0b00010000
QF = 0b00100000

# Una MÁSCARA es un grupo de LEDs. Con el operador | (O binario) se suman varios bits en un solo número, este se hizo con esa variable por recomendación de la IA
# Ej: QA | QB = 0b00000011 -> enciende QA y QB a la vez.
MASCARA_FRONTAL = QA | QB    # luces de adelante: QA derecha, QB izquierda
MASCARA_TRASERA = QE | QF    # luces de atrás: QE derecha, QF izquierda
MASCARA_IZQ     = QC         # direccional izquierda
MASCARA_DER     = QD         # direccional derecha 

# Opciones de claro y oscuro
# esa zona intermedia evita que las luces parpadeen cuando la luz está justo en el límite.
OSCURO = 10000    # por debajo de esto se considera oscuro 
CLARO = 20000     # por encima de esto se considera claro 

datos = Pin(PIN_DATOS, Pin.OUT)   # pin de datos configurado como salida
reloj = Pin(PIN_RELOJ, Pin.OUT)   # pin de reloj configurado como salida
estado = 0        # guarda qué LEDs están encendidos (un número de 8 bits, un bit por LED)
                  # sirve para recordar el estado y no apagar sin querer los demás LEDs

def enviar(valor):
    """Manda 8 bits al registro, del bit 7 al 0, un pulso de reloj por bit."""
    for i in range(7, -1, -1):           # i = 7, 6, 5, ... 0 (empieza por el bit más alto)
        datos.value((valor >> i) & 1)    # (valor >> i) & 1 saca el bit número i: da 0 o 1
        reloj.value(1)                   # el pulso de reloj (subir y bajar) hace que el registro
        reloj.value(0)                   # lea el bit y lo meta al final los 8 bits quedan en QA..QH

def poner_luces(mascara, encender):
    """Enciende o apaga solo los LEDs de la máscara sin tocar los demás."""
    global estado
    if encender:
        estado |= mascara            # |= pone en 1 los bits de la máscara (enciende esos LEDs)
    else:
        estado &= ~mascara & 0xFF    # ~mascara invierte los bits y &= pone en 0 solo los de la máscara
                                     # (apaga esos LEDs); & 0xFF limita el resultado a 8 bits
    enviar(estado)                   # manda el nuevo estado completo al registro

enviar(0)   # todas las luces apagadas al importar el módulo (así no arrancan con basura)
#___________________________________________________________________________________________________________________#
# ---------- FOTORRESISTENCIA (LDR) ----------
ldr = ADC(Pin(PIN_LDR))   # configura el pin como entrada analógica
modo_ldr = False   # True = las luces frontales y traseras las controla el LDR automáticamente
auto_on = None     # último estado automático (True/False)

def leer_ldr():
    """Lee el sensor: devuelve un número de 0 (oscuro) a 65535 (claro)."""
    return ldr.read_u16()   # 0 a 65535 siguiendo el ejemplo

def actualizar_ldr():
    """Hay que llamarla seguido desde el ciclo principal (main_menu.py).
    Si el modo LDR está activo, enciende o apaga las luces según la luz del ambiente."""
    global auto_on
    if not modo_ldr:      # si el modo LDR está apagado, no hace nada
        return
    valor = leer_ldr()
    # "auto_on is not True" evita repetir la orden: solo actúa cuando el estado CAMBIA.
    # Así no manda datos al registro ni imprime en cada vuelta del ciclo.
    if valor < OSCURO and auto_on is not True:
        poner_luces(MASCARA_FRONTAL | MASCARA_TRASERA, True)    # oscuro -> enciende frontales y traseras
        auto_on = True
        print("LDR: oscuro (", valor, ") -> luces ON")
    elif valor > CLARO and auto_on is not False:
        poner_luces(MASCARA_FRONTAL | MASCARA_TRASERA, False)   # claro -> las apaga
        auto_on = False
        print("LDR: claro (", valor, ") -> luces OFF")
#___________________________________________________________________________________________________________________#
# ---------- COMANDOS LLAMADOS EN MAIN MENU ----------
def validar_bool(v):
    """Revisa que el valor sea 0 o 1. Si no, avisa y devuelve False."""
    if v not in (0, 1):
        print("El valor debe ser 0 o 1")
        return False
    return True

def cmd_luz(nombre, mascara, v):
    """Sirve para lf, lb, ll y lr: solo cambia el nombre y la máscara."""
    if not validar_bool(v): return          # valor inválido: ya avisó, no hace nada
    if modo_ldr:                            # con el modo LDR activo las luces las manda el sensor,
        print("Modo LDR activo (se desactiva con ldr 0)"); return   # así que no se aceptan comandos manuales
    poner_luces(mascara, v == 1)            # v == 1 da True (encender) o False (apagar)
    print(nombre, v)

# Cada comando solo llama a cmd_luz con su nombre y su máscara
def cmd_lf(v): cmd_luz("lf", MASCARA_FRONTAL, v) # FRONT: luces frontales
def cmd_lb(v): cmd_luz("lb", MASCARA_TRASERA, v) # BACK: luces traseras
def cmd_ll(v): cmd_luz("ll", MASCARA_IZQ, v) # LEFT: direccional izquierda
def cmd_lr(v): cmd_luz("lr", MASCARA_DER, v) # RIGHT: direccional derecha

def cmd_ldr(v):
    """ldr 1 = activa el modo automático por luz; ldr 0 = lo desactiva (control manual)."""
    global modo_ldr, auto_on
    if not validar_bool(v): return
    modo_ldr = (v == 1)
    auto_on = None    # fuerza a volver a leer la luz: al activarlo decide de inmediato según la luz actual pero si detecta mucha luz no prende practicamente debo dejarlo a oscuras
    print("ldr", v) 
