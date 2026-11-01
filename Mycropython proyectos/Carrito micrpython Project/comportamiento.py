from time import sleep_ms
import motores   # usa los motores ya creados en motores.py: motores.izq, motores.der y motores.parar()
                 # recibe -4..4, pero AQUÍ SOLO SE USA 0..4 no usa reversas
DEBUG = True   # True = imprime además el nivel numérico de cada paso (rueda izq, rueda der, ms)
# --- Giros en las esquinas (zigzag y especial): SOLO HACIA ADELANTE ---
# El carro gira pivotando sobre una rueda: la de adentro se queda parada y la de afuera avanza.
NIVEL_GIRO = 3             # potencia de la rueda de afuera al girar
TIEMPO_90 = 1200           # ms para girar 90° pivotando sobre una rueda
TIEMPO_PAUSA = 250         # ms de pausa entre movimientos (evita que patine)

# --- circle: un círculo hacia adelante ---
CIRCLE_INTERNO = 3         # rueda izquierda (adentro): parada, el carro pivota sobre ella
CIRCLE_EXTERNO = 5         # rueda derecha (afuera)
TIEMPO_CIRCLE = 5000       # ms para dar una vuelta completa

# --- infinite:
INF_PRIMER_LAZO = -1       # -1 = empieza curvando a la izquierda, 1 = empieza curvando a la derecha (el 8 sale al revés)
INF_INTERNO = 1            # potencia de la rueda de adentro en cada lazo
INF_EXTERNO = 3            # potencia de la rueda de afuera en cada lazo
INF_RECTA = 2              # potencia en las rectas (≈ promedio de INTERNO y EXTERNO)
TIEMPO_LAZO_IZQ = 6000     # ms que tardaría en dar una vuelta COMPLETA curvando a la izquierda
TIEMPO_LAZO_DER = 6000     # ms que tardaría en dar una vuelta COMPLETA curvando a la derecha
                           # (separados porque los dos motores casi nunca rinden igual)
TIEMPO_RECTA = 950         # ms de cada recta ≈ TIEMPO_LAZO / 6.28 (si cambias el lazo, cambia este)

# --- Avances (zigzag y especial) ---
NIVEL_LADO = 2             # potencia al avanzar en línea recta

# --- Zigzag ---
ZIGZAG_TRAMOS = 6          # cantidad de tramos rectos en diagonal
TIEMPO_TRAMO = 1000        # ms que avanza cada tramo

# --- Especial (cuadrado) ---
TIEMPO_LADO = 1500         # ms que avanza cada lado del cuadrado
#___________________________________________________________________________________________________________________#
def _rueda(nivel):
    """Texto que describe hacia dónde gira una rueda según su nivel."""
    return "adelante" if nivel > 0 else "parada"

def _direccion(nivel_izq, nivel_der):
    """Devuelve el nombre del movimiento del carro según el nivel de cada rueda."""
    if nivel_izq == 0 and nivel_der == 0:
        return "PARADO"
    if nivel_izq == nivel_der:
        return "RECTO ADELANTE"
    if nivel_izq > 0 and nivel_der == 0:
        return "GIRO A LA DERECHA (pivotando sobre la rueda derecha)"
    if nivel_izq == 0 and nivel_der > 0:
        return "GIRO A LA IZQUIERDA (pivotando sobre la rueda izquierda)"
    # las dos ruedas avanzan pero con distinta fuerza: curva hacia el lado de la rueda más lenta
    if nivel_izq < nivel_der:
        return "CURVA A LA IZQUIERDA"
    return "CURVA A LA DERECHA"

_ultima_dir = ""   # último movimiento impreso, para avisar solo cuando cambia

def _tramo(nivel_izq, nivel_der, tiempo):
    """Mueve cada rueda con su nivel durante 'tiempo' ms. NUNCA va en reversa:
    cualquier nivel negativo se convierte en 0.
    Imprime un aviso cada vez que el carro cambia de dirección."""
    global _ultima_dir
    nivel_izq = max(0, nivel_izq)
    nivel_der = max(0, nivel_der)
    nueva = _direccion(nivel_izq, nivel_der)
    if nueva != _ultima_dir:
        print(">> DIRECCION:", nueva,
              "| rueda izq:", _rueda(nivel_izq),
              "| rueda der:", _rueda(nivel_der))
        _ultima_dir = nueva
    if DEBUG:
        print("  paso -> izq:", nivel_izq, "| der:", nivel_der, "|", tiempo, "ms")
    motores.izq.mover(nivel_izq)
    motores.der.mover(nivel_der)
    sleep_ms(tiempo)

def _pausa():
    _tramo(0, 0, TIEMPO_PAUSA)

def _avanzar(tiempo):
    """Avanza recto y hace una pausa."""
    _tramo(NIVEL_LADO, NIVEL_LADO, tiempo)
    _pausa()

def _giro(sentido, grados):
    """Gira pivotando sobre una rueda, siempre hacia adelante (sin reversa).
    sentido = 1 gira a la derecha (rueda derecha parada), sentido = -1 a la izquierda.
    El tiempo sale de TIEMPO_90: 45° = mitad, 90° = TIEMPO_90."""
    print("   giro de", grados, "grados a la", "derecha" if sentido == 1 else "izquierda")
    if sentido == 1:
        _tramo(NIVEL_GIRO, 0, TIEMPO_90 * grados // 90)
    else:
        _tramo(0, NIVEL_GIRO, TIEMPO_90 * grados // 90)
    _pausa()

def _detener():
    """Para los motores (motores.parar también deja nivel_actual en 0) y avisa."""
    global _ultima_dir
    motores.parar()
    print(">> DIRECCION: PARADO (motores detenidos)")
    _ultima_dir = ""   # así el próximo patrón siempre imprime su primera dirección
#___________________________________________________________________________________________________________________#
def circle():
    """Un círculo completo hacia adelante (curvando a la izquierda) y se detiene."""
    print("circle: iniciando")
    try:
        print("circle: vuelta completa a la izquierda")
        _tramo(CIRCLE_INTERNO, CIRCLE_EXTERNO, TIEMPO_CIRCLE)
    finally:
        _detener()          
    print("circle: terminado")

def infinite():
    """Dibuja un 8 acostado (∞) solo hacia adelante: el carro se cruza a sí mismo en el centro.
    Recorrido: recta -> lazo (3/4 de vuelta) -> recta que cruza el centro ->
    lazo al lado contrario (3/4 de vuelta) -> recta de regreso. Se detiene al terminar.
    INF_PRIMER_LAZO decide si empieza hacia la izquierda o hacia la derecha."""
    print("infinite: iniciando")
    lazo_izq = (INF_INTERNO, INF_EXTERNO, TIEMPO_LAZO_IZQ * 3 // 4, "izquierdo")   # 270°
    lazo_der = (INF_EXTERNO, INF_INTERNO, TIEMPO_LAZO_DER * 3 // 4, "derecho")     # 270°
    if INF_PRIMER_LAZO == 1:
        primero, segundo = lazo_der, lazo_izq
    else:
        primero, segundo = lazo_izq, lazo_der
    try:
        print("infinite: 1) recta hacia el primer lazo")
        _tramo(INF_RECTA, INF_RECTA, TIEMPO_RECTA)
        _pausa()
        print("infinite: 2) lazo", primero[3])
        _tramo(primero[0], primero[1], primero[2])
        _pausa()
        print("infinite: 3) recta que cruza el centro")
        _tramo(INF_RECTA, INF_RECTA, TIEMPO_RECTA * 2)
        _pausa()
        print("infinite: 4) lazo", segundo[3])
        _tramo(segundo[0], segundo[1], segundo[2])
        _pausa()
        print("infinite: 5) recta de regreso al inicio")
        _tramo(INF_RECTA, INF_RECTA, TIEMPO_RECTA)
    finally:
        _detener()
    print("infinite: terminado")

def zigzag():
    """Avanza ZIGZAG_TRAMOS tramos en diagonales alternadas, solo hacia adelante:
    gira 45° a la izquierda y luego alterna giros de 90° (derecha, izquierda, derecha...)."""
    print("zigzag: iniciando")
    try:
        _giro(-1, 45)                                  # primer giro: 45° a la izquierda
        for i in range(ZIGZAG_TRAMOS):
            print("zigzag: tramo", i + 1, "de", ZIGZAG_TRAMOS)
            _avanzar(TIEMPO_TRAMO)
            if i < ZIGZAG_TRAMOS - 1:                  # después del último tramo no gira
                _giro(1 if i % 2 == 0 else -1, 90)
    finally:
        _detener()
    print("zigzag: terminado")

def especial():
    """Patrón propio: un cuadrado (4 lados con giros de 90°) solo hacia adelante."""
    print("especial: iniciando (cuadrado)")
    try:
        for i in range(4):
            print("especial: lado", i + 1, "de 4")
            _avanzar(TIEMPO_LADO)
            _giro(1, 45)                               # 90° a la derecha pivotando sobre la rueda derecha
    finally:
        _detener()
    print("especial: terminado")
"""
TODO LO QUE ESTA CON PRINTS EN SUS MAYORÍAS ES SOLO PARA DEBUGUEO EN LA CONSOLA VISIBLES
"""
