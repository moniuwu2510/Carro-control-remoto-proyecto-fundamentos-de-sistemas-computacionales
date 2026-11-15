import network, socket, time
import motores
SSID = "Dióxido de Zinc"
PASSWORD = "Stefano25"
PORT = 5000

def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    for _ in range(30):
        if wlan.isconnected(): # si esta conectada a la red y la contraseña los dos muestra la IP de la pico
            break
        time.sleep(1)
    if not wlan.isconnected():
        raise RuntimeError("No se pudo conectar al WiFi")
    print("IP de la Pico:", wlan.ifconfig()[0]) # obtenemos la IP de la Pico para la GUI

def ejecutar(cmd):
    partes = cmd.split()
    if not partes:
        return "error: comando vacio" 
    try:
        if partes[0] == "pwm":
            v = int(partes[1])
            if v not in range(-4, 5):
                return "error: pwm fuera de rango (-4 a 4)"
            motores.cmd_pwm(v)
            return "ok"
        if partes[0] == "dir":
            v = int(partes[1])
            if v not in (-1, 0, 1, 2):
                return "error: dir fuera de rango (-1,0,1,2)"
            motores.cmd_dir(v)
            return "ok"
        if partes[0] == "stop":
            motores.parar()
            return "ok"
    except (ValueError, IndexError):
        return "error: formato invalido"
    return "error: comando desconocido"
    
def servidor():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", PORT))
    s.listen(1)
    while True:
        conn, addr = s.accept()
        print("Cliente conectado:", addr)
        buf = b""
        try:
            while True:
                data = conn.recv(64)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    linea, buf = buf.split(b"\n", 1)
                    resp = ejecutar(linea.decode().strip())
                    conn.send((resp + "\n").encode())
        except OSError:
            pass
        finally:
            conn.close()

conectar_wifi()
servidor()
