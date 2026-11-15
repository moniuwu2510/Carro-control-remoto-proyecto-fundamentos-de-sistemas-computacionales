import socket

class Carro:
    def __init__(self, ip, puerto=5000):
        self.sock = socket.create_connection((ip, puerto), timeout=3)
        self.archivo = self.sock.makefile("rw", newline="\n")

    def enviar(self, comando):
        self.archivo.write(comando + "\n")
        self.archivo.flush()
        return self.archivo.readline().strip()

    def cerrar(self):
        self.sock.close()

# Prueba rápida
carro = Carro("IP_DE_LA_PICO")
print(carro.enviar("pwm 50"))
carro.cerrar()