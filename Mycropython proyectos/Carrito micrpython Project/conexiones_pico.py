import network, socket, time
from machine import Pin
import motores                     # motores.py (debe estar en la Pico)
import luces                        # luces.py: registro de corrimiento + LDR
import comportamientoMod            # comportamientoMod.py: circle, infinite, zigzag, especial

SSID = "Dióxido de Zinc"            # nombre de tu red WiFi (2.4 GHz)
PASSWORD = "Stefano25"              # contraseña del WiFi
PUERTO = 5000                       # puerto donde escucha la Pico

# Errores de "tiempo agotado" al esperar datos (no significan que se cayó la conexión)
ERRORES_TIMEOUT = (110, 11)         # ETIMEDOUT, EAGAIN

PATRONES = {
    "circle": comportamientoMod.circle,
    "infinite": comportamientoMod.infinite,
    "zigzag": comportamientoMod.zigzag,
    "especial": comportamientoMod.especial,
}

buf = b""                           # datos recibidos que aun no forman un comando completo

# ---------------------------------------------------------------- decrementador
# Entradas A, B, C del circuito (salidas de la Pico; A = bit mas significativo)
dec_a = Pin(3, Pin.OUT)             # GP3
dec_b = Pin(4, Pin.OUT)             # GP4
dec_c = Pin(5, Pin.OUT)             # GP5 (GP2 no se usa)
# Salidas x, y, z del circuito (entradas de la Pico, llegan por el divisor de 10k/20k)
# Sin pull-down: los chips siempre empujan 0 o 1.
dec_x = Pin(6, Pin.IN)              # GP6
dec_y = Pin(7, Pin.IN)              # GP7
dec_z = Pin(8, Pin.IN)              # GP8

dec_activo = False                  # True mientras los LED muestran la salida del decrementador


def dec_escribir(n):
    """Pone el valor n (0 a 7) en las entradas A, B, C del decrementador."""
    dec_a.value((n >> 2) & 1)
    dec_b.value((n >> 1) & 1)
    dec_c.value(n & 1)


def dec_leer():
    """Lee las salidas del circuito y devuelve (x, y, z)."""
    return dec_x.value(), dec_y.value(), dec_z.value()


def dec_mostrar(x, y, z):
    """Muestra la salida en los LED: delanteras = x, direccionales = y, traseras = z."""
    luces.cmd_lf(x)
    luces.cmd_ll(y)
    luces.cmd_lr(y)
    luces.cmd_lb(z)


def dec_probar(n):
    """Escribe n, lee la salida del circuito, la muestra en los LED y arma la respuesta."""
    global dec_activo
    if not dec_activo:
        if luces.modo_ldr:
            luces.cmd_ldr(0)        # el modo automatico de luces usaria los mismos LED
        dec_activo = True
    dec_escribir(n)
    time.sleep_ms(2)                # tiempo para que las compuertas cambien
    x, y, z = dec_leer()
    dec_mostrar(x, y, z)
    print("dec", n, "-> ABC", "{:03b}".format(n), "salida", x, y, z)
    return "dec %d %s %d%d%d" % (n, "{:03b}".format(n), x, y, z)


def dec_apagar():
    """Deja el decrementador en 111 (salida 000) y apaga los LED."""
    global dec_activo
    dec_escribir(7)
    if dec_activo:
        dec_mostrar(0, 0, 0)
    dec_activo = False


dec_escribir(7)                     # 111 = decrementador "apagado": su salida es 000


# LED integrado de la Pico W / 2W: indica el estado cuando no hay consola
#   parpadeo lento = conectando al WiFi
#   parpadeo rapido = no se pudo conectar (lo vuelve a intentar solo)
#   encendido fijo = listo, esperando o atendiendo la interfaz
led = Pin("LED", Pin.OUT)


def parpadear(veces, pausa):
    for _ in range(veces):
        led.toggle()
        time.sleep(pausa)
    led.off()


def conectar_wifi():
    """Conecta la Pico a la red y devuelve su IP. Si falla, reintenta sin detenerse."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    while not wlan.isconnected():
        wlan.connect(SSID, PASSWORD)
        for _ in range(30):                 # hasta unos 30 s por intento
            if wlan.isconnected():
                break
            print("Conectando al WiFi...")
            parpadear(2, 0.5)               # parpadeo lento
        if not wlan.isconnected():
            print("No se pudo conectar al WiFi (revisa SSID, clave y que sea de 2.4 GHz). Reintentando...")
            parpadear(20, 0.1)              # parpadeo rapido
            wlan.disconnect()
    ip = wlan.ifconfig()[0]
    print("IP de la Pico:", ip)
    led.on()                                # encendido fijo: listo
    return ip


def ejecutar(cmd):
    """Interpreta un comando de texto (que no sea un patron) y devuelve la respuesta."""
    partes = cmd.split()
    if not partes:
        return "error: comando vacio"
    nombre = partes[0]
    try:
        if nombre == "ping":
            return "pong"

        # ---------- motores ----------
        if nombre == "pwm":
            v = int(partes[1])
            if v not in range(-4, 5):
                return "error: pwm fuera de rango (-4 a 4)"
            motores.cmd_pwm(v)
            return "ok"
        if nombre == "dir":
            v = int(partes[1])
            if v not in (-1, 0, 1, 2):
                return "error: dir fuera de rango (-1,0,1,2)"
            motores.cmd_dir(v)
            return "ok"
        if nombre == "stop":
            motores.parar()
            return "ok"

        # ---------- decrementador ----------
        if nombre == "dec":                 # dec 0..7 prueba una entrada; dec off lo apaga
            if partes[1] == "off":
                dec_apagar()
                return "ok"
            v = int(partes[1])
            if v not in range(0, 8):
                return "error: dec fuera de rango (0 a 7)"
            return dec_probar(v)            # responde: dec <n> <ABC> <xyz>, ej. "dec 3 011 010"

        # ---------- luces ----------
        if nombre in ("lf", "lb", "ll", "lr"):
            v = int(partes[1])
            if v not in (0, 1):
                return "error: el valor debe ser 0 o 1"
            if dec_activo:
                return "error: decrementador activo (usa dec off para control manual)"
            if luces.modo_ldr:
                return "error: modo ldr activo (usa ldr 0 para control manual)"
            if nombre == "lf":
                luces.cmd_lf(v)
            elif nombre == "lb":
                luces.cmd_lb(v)
            elif nombre == "ll":
                luces.cmd_ll(v)
            else:
                luces.cmd_lr(v)
            return "ok"

        # ---------- LDR ----------
        if nombre == "ldr":                 # modo automatico de luces: ldr 1 / ldr 0
            v = int(partes[1])
            if v not in (0, 1):
                return "error: el valor debe ser 0 o 1"
            if v == 1 and dec_activo:
                return "error: decrementador activo (usa dec off primero)"
            luces.cmd_ldr(v)
            return "ok"
        if nombre == "ldrval":              # lectura cruda del sensor (0 a 65535)
            return str(luces.leer_ldr())

    except (ValueError, IndexError):
        return "error: formato invalido"
    return "error: comando desconocido"


def revisar_stop(conn):
    """Se llama cada 50 ms mientras corre un patron: atiende el LDR y busca un "stop"."""
    global buf
    luces.actualizar_ldr()
    conn.settimeout(0)                      # sin esperar: solo mira si llego algo
    try:
        data = conn.recv(64)
    except OSError:
        data = None
    conn.settimeout(0.2)
    if data == b"":                         # el cliente cerro la conexion
        raise comportamientoMod.Cancelado()
    if data:
        buf += data
        while b"\n" in buf:
            linea, buf = buf.split(b"\n", 1)
            if linea.decode().strip() == "stop":
                raise comportamientoMod.Cancelado()
            conn.send(b"error: patron en curso (usa stop)\n")


def correr_patron(conn, nombre):
    """Responde de inmediato, corre el patron (se puede cancelar con stop) y avisa al terminar."""
    conn.send(("ok iniciado " + nombre + "\n").encode())
    comportamientoMod.hook = lambda: revisar_stop(conn)
    try:
        PATRONES[nombre]()
        conn.send(("fin " + nombre + "\n").encode())
    except comportamientoMod.Cancelado:
        conn.send(("cancelado " + nombre + "\n").encode())
    except OSError:
        raise                                   # conexion perdida: la maneja servidor()
    except Exception as e:                      # error dentro del patron: avisar sin tumbar el servidor
        motores.parar()
        print("Error en el patron", nombre, ":", repr(e))
        conn.send(("cancelado " + nombre + " (error: " + repr(e) + ")\n").encode())
    finally:
        comportamientoMod.hook = None


def servidor():
    """Espera un cliente, atiende sus comandos y vuelve a esperar."""
    global buf
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", PUERTO))
    s.listen(1)
    print("Esperando conexion en el puerto", PUERTO)
    while True:
        conn, addr = s.accept()
        print("Cliente conectado:", addr)
        conn.settimeout(0.2)            # asi el ciclo puede revisar el LDR aunque no lleguen comandos
        buf = b""
        try:
            while True:
                luces.actualizar_ldr()  # si el modo ldr esta activo, ajusta las luces
                try:
                    data = conn.recv(64)
                except OSError as e:
                    if e.args and e.args[0] in ERRORES_TIMEOUT:
                        continue        # no llego nada todavia: seguir esperando
                    break               # conexion perdida
                if not data:            # el cliente cerro la conexion
                    break
                buf += data
                while b"\n" in buf:     # un comando termina en salto de linea
                    linea, buf = buf.split(b"\n", 1)
                    texto = linea.decode().strip()
                    if texto in PATRONES:
                        correr_patron(conn, texto)
                    else:
                        conn.send((ejecutar(texto) + "\n").encode())
        except OSError:
            pass                        # conexion perdida al enviar
        finally:
            motores.parar()             # seguridad: si se cae la conexion, el carro se detiene
            dec_apagar()                # y el decrementador queda apagado
            conn.close()
            print("Cliente desconectado")


conectar_wifi()
servidor()
