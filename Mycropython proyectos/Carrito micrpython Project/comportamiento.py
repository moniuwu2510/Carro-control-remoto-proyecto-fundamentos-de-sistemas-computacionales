from time import sleep_ms
import motores   # usa los motores ya creados en motores.py

# TODO LO DE ABAJO SE CALIBRA con el carro armado y la batería de la revisión
NIVEL_EXTERNO = 3        # potencia de la rueda de afuera de la curva
NIVEL_INTERNO = 1        # potencia de la rueda de adentro de la curva
TIEMPO_CIRCULO = 6000    # ms que tarda en dar una vuelta completa

ZIGZAG_TRAMOS = 6        # cantidad de curvas (usar número PAR para que termine derecho)
TIEMPO_TRAMO = 700       # ms que dura cada curva del zigzag

NIVEL_LADO = 2           # potencia al avanzar en "especial" (cuadrado)
TIEMPO_LADO = 1500       # ms que avanza cada lado del cuadrado
TIEMPO_90 = 500          # ms que tarda en girar 90 grados sobre su eje
TIEMPO_PAUSA = 250       # ms de pausa entre movimientos del cuadrado

def _tramo(nivel_izq, nivel_der, tiempo):
    """Mueve cada rueda con su nivel durante 'tiempo' ms."""
    motores.izq.mover(nivel_izq)
    motores.der.mover(nivel_der)
    sleep_ms(tiempo)

def circle():
    """Una vuelta circular hacia la izquierda y se detiene en el punto de partida."""
    print("circle: iniciando")
    _tramo(NIVEL_INTERNO, NIVEL_EXTERNO, TIEMPO_CIRCULO)
    motores.parar()
    print("circle: terminado")

def infinite():
    """Recorrido en 8 (infinito): un lazo a la izquierda y otro a la derecha.
    Cada lazo es un círculo completo, así que termina donde empezó."""
    print("infinite: iniciando")
    _tramo(NIVEL_INTERNO, NIVEL_EXTERNO, TIEMPO_CIRCULO)   # lazo izquierdo
    _tramo(NIVEL_EXTERNO, NIVEL_INTERNO, TIEMPO_CIRCULO)   # lazo derecho
    motores.parar()
    print("infinite: terminado")

def zigzag():
    """Curvas alternadas izquierda-derecha durante un tiempo fijo."""
    print("zigzag: iniciando")
    for i in range(ZIGZAG_TRAMOS):
        if i % 2 == 0:
            _tramo(NIVEL_INTERNO, NIVEL_EXTERNO, TIEMPO_TRAMO)   # curva a la izquierda
        else:
            _tramo(NIVEL_EXTERNO, NIVEL_INTERNO, TIEMPO_TRAMO)   # curva a la derecha
    motores.parar()
    print("zigzag: terminado")

def especial():
    """Patrón propio: un cuadrado (4 lados con giros de 90 grados) y vuelve al inicio."""
    print("especial: iniciando")
    for _ in range(4):
        _tramo(NIVEL_LADO, NIVEL_LADO, TIEMPO_LADO)       # avanzar un lado
        _tramo(0, 0, TIEMPO_PAUSA)
        _tramo(NIVEL_LADO, -NIVEL_LADO, TIEMPO_90)        # girar 90° a la derecha sobre su eje
        _tramo(0, 0, TIEMPO_PAUSA)
    motores.parar()
    print("especial: terminado")