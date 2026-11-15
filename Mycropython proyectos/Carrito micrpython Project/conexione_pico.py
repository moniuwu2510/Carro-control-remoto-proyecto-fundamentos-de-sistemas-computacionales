import network, socket, time

SSID = "TU_RED"
PASSWORD = "TU_CLAVE"
PORT = 5000

def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    for _ in range(30):
        if wlan.isconnected():
            break
        time.sleep(1)
    if not wlan.isconnected():
        raise RuntimeError("No se pudo conectar al WiFi")
    print("IP de la Pico:", wlan.ifconfig()[0])

def ejecutar(cmd):
    partes = cmd.split()
    if not partes:
        return "error: comando vacio"
    if partes[0] == "pwm":
        # ... llama a tu función de pwm con partes[1]
        return "ok"
    if partes[0] == "dir":
        # ... llama a tu función de dirección con partes[1]
        return "ok"
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