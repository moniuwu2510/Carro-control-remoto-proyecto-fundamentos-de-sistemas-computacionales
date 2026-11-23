from time import sleep_ms
import motores   # usa motores.avanzar(nivel), motores.doblar(lado) y motores.parar()
                 # AQUI SOLO SE USAN niveles 0..4: los patrones no usan reversa
DEBUG = True   # True = imprime ademas el nivel, la direccion y el tiempo de cada paso

# El carro es tipo control remoto: la traccion lo mueve y la direccion dobla las ruedas de adelante
# hasta el tope (izquierda o derecha) o las deja rectas. Por eso los giros son curvas hacia adelante:
# el carro no puede girar sobre su eje. Todos los tiempos se calibran en el suelo.

# --- Cancelacion (la usa servidor.py para el comando "stop" desde la interfaz) ---
class Cancelado(Exception):
    """Se lanza para interrumpir un patron en curso."""
    pass

hook = None   # funcion que el servidor asigna; se llama cada 50 ms mientras un patron espera

# --- Generales ---
NIVEL_RECTA = 2            # potencia al avanzar recto
NIVEL_GIRO = 2             # potencia mientras dobla
TIEMPO_PAUSA = 250         # ms de pausa entre movimientos (evita que patine)
TIEMPO_90 = 1200           # ms doblando (a NIVEL_GIRO) para cambiar 90 grados de rumbo

# --- circle: un circulo completo con las ruedas dobladas ---
CIRCLE_LADO = -1           # -1 = circulo hacia la izquierda, 1 = hacia la derecha
NIVEL_CIRCLE = 2
TIEMPO_CIRCLE = 5000       # ms para dar una vuelta completa (calibrar: debe volver al punto de inicio)

# --- infinite: un 8 = un circulo hacia un lado y otro hacia el otro; termina donde empezo ---
INF_PRIMER_LAZO = -1       # -1 = empieza a la izquierda, 1 = a la derecha
NIVEL_INF = 2
TIEMPO_LAZO_IZQ = 5000     # ms de una vuelta completa doblando a la izquierda
TIEMPO_LAZO_DER = 5000     # ms de una vuelta completa doblando a la derecha
                           # (separados porque casi nunca dobla igual hacia los dos lados)

# --- zigzag ---
ZIGZAG_TRAMOS = 6          # cantidad de tramos rectos en diagonal
TIEMPO_TRAMO = 1000        # ms que avanza cada tramo

# --- especial (cuadrado) ---
TIEMPO_LADO = 1500         # ms que avanza cada lado del cuadrado
#___________________________________________________________________________________________________________________#
_NOMBRE_LADO = {-1: "izquierda", 0: "recto", 1: "derecha"}


def _direccion(nivel, lado):
    """Nombre del movimiento del carro segun la potencia y hacia donde estan las ruedas."""
    if nivel == 0:
        return "PARADO"
    if lado == 0:
        return "RECTO ADELANTE"
    return "CURVA A LA " + _NOMBRE_LADO[lado].upper()

_ultima_dir = ""   # ultimo movimiento impreso, para avisar solo cuando cambia


def _tramo(nivel, lado, tiempo):
    """Avanza con potencia 'nivel' y las ruedas hacia 'lado' durante 'tiempo' ms.
    NUNCA va en reversa: cualquier nivel negativo se convierte en 0.
    Imprime un aviso cada vez que el carro cambia de direccion."""
    global _ultima_dir
    nivel = max(0, nivel)
    nueva = _direccion(nivel, lado)
    if nueva != _ultima_dir:
        print(">> DIRECCION:", nueva)
        _ultima_dir = nueva
    if DEBUG:
        print("  paso -> potencia:", nivel, "| ruedas:", _NOMBRE_LADO[lado], "|", tiempo, "ms")
    motores.doblar(lado)
    motores.avanzar(nivel)
    _esperar(tiempo)


def _esperar(ms):
    """Como sleep_ms, pero en pasos de 50 ms para poder revisar si llego un "stop"."""
    restante = ms
    while restante > 0:
        paso = 50 if restante > 50 else restante
        sleep_ms(paso)
        restante -= paso
        if hook:
            hook()          # puede lanzar Cancelado; el finally de cada patron detiene los motores


def _pausa():
    _tramo(0, 0, TIEMPO_PAUSA)


def _avanzar(tiempo):
    """Avanza recto y hace una pausa."""
    _tramo(NIVEL_RECTA, 0, tiempo)
    _pausa()


def _giro(sentido, grados):
    """Curva hacia adelante con las ruedas dobladas hasta cambiar 'grados' de rumbo.
    sentido = 1 derecha, -1 izquierda. El tiempo sale de TIEMPO_90: 45 grados = mitad."""
    print("   giro de", grados, "grados a la", _NOMBRE_LADO[sentido])
    _tramo(NIVEL_GIRO, sentido, TIEMPO_90 * grados // 90)
    _pausa()


def _detener():
    """Para la traccion, centra las ruedas y avisa."""
    global _ultima_dir
    motores.parar()
    print(">> DIRECCION: PARADO (motores detenidos)")
    _ultima_dir = ""   # asi el proximo patron siempre imprime su primera direccion
#___________________________________________________________________________________________________________________#
def circle():
    """Un circulo completo hacia adelante con las ruedas dobladas, y se detiene."""
    print("circle: iniciando")
    try:
        print("circle: vuelta completa a la", _NOMBRE_LADO[CIRCLE_LADO])
        _tramo(NIVEL_CIRCLE, CIRCLE_LADO, TIEMPO_CIRCLE)
    finally:
        _detener()
    print("circle: terminado")


def infinite():
    """Dibuja un 8: una vuelta completa hacia un lado y otra hacia el lado contrario.
    Los dos circulos se tocan en el punto de partida, asi que termina donde empezo."""
    print("infinite: iniciando")
    lazo_izq = (-1, TIEMPO_LAZO_IZQ, "izquierdo")
    lazo_der = (1, TIEMPO_LAZO_DER, "derecho")
    primero, segundo = (lazo_der, lazo_izq) if INF_PRIMER_LAZO == 1 else (lazo_izq, lazo_der)
    try:
        print("infinite: 1) lazo", primero[2])
        _tramo(NIVEL_INF, primero[0], primero[1])
        print("infinite: 2) lazo", segundo[2])
        _tramo(NIVEL_INF, segundo[0], segundo[1])
    finally:
        _detener()
    print("infinite: terminado")


def zigzag():
    """Avanza ZIGZAG_TRAMOS tramos en diagonales alternadas, solo hacia adelante:
    gira 45 grados a la izquierda y luego alterna giros de 90 (derecha, izquierda, derecha...)."""
    print("zigzag: iniciando")
    try:
        _giro(-1, 45)                                  # primer giro: 45 grados a la izquierda
        for i in range(ZIGZAG_TRAMOS):
            print("zigzag: tramo", i + 1, "de", ZIGZAG_TRAMOS)
            _avanzar(TIEMPO_TRAMO)
            if i < ZIGZAG_TRAMOS - 1:                  # despues del ultimo tramo no gira
                _giro(1 if i % 2 == 0 else -1, 90)
    finally:
        _detener()
    print("zigzag: terminado")


def especial():
    """Patron propio: un cuadrado (4 lados con curvas de 90 grados a la derecha) solo hacia adelante.
    Como el carro dobla en curva, las esquinas quedan redondeadas."""
    print("especial: iniciando (cuadrado)")
    try:
        for i in range(4):
            print("especial: lado", i + 1, "de 4")
            _avanzar(TIEMPO_LADO)
            _giro(1, 90)
    finally:
        _detener()
    print("especial: terminado")
"""
TODO LO QUE ESTA CON PRINTS EN SU MAYORIA ES SOLO PARA DEPURACION EN LA CONSOLA

Como calibrar (en el suelo, con las baterias que se van a usar en la defensa):
1. TIEMPO_90: manda zigzag o especial y ajusta hasta que cada curva cambie el rumbo 90 grados.
2. TIEMPO_CIRCLE: ajusta hasta que el circulo cierre en el punto de partida.
3. TIEMPO_LAZO_IZQ / TIEMPO_LAZO_DER: igual que el circulo, cada uno por separado.
Si cambias NIVEL_GIRO, NIVEL_CIRCLE o NIVEL_INF, los tiempos cambian y hay que calibrarlos otra vez.
"""
