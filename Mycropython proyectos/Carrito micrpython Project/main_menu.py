from time import sleep_ms
import sys, select

import motores
import luces
import comportamiento

PATRONES = {
    "circle": comportamiento.circle,
    "infinite": comportamiento.infinite,
    "zigzag": comportamiento.zigzag,
    "especial": comportamiento.especial,
}

def procesar(linea):
    partes = linea.strip().lower().split()
    if len(partes) == 1 and partes[0] in PATRONES:   # los patrones no llevan valor
        PATRONES[partes[0]](); return
    if len(partes) != 2:
        print("Formato: comando valor (ej: pwm 3) | circle, infinite, zigzag, especial"); return
    try:
        valor = int(partes[1])
    except ValueError:
        print("El valor debe ser entero"); return
    comando = partes[0]
    if comando == "pwm": motores.cmd_pwm(valor)
    elif comando == "dir": motores.cmd_dir(valor)
    elif comando == "lf": luces.cmd_lf(valor)
    elif comando == "lb": luces.cmd_lb(valor)
    elif comando == "ll": luces.cmd_ll(valor)
    elif comando == "lr": luces.cmd_lr(valor)
    elif comando == "ldr": luces.cmd_ldr(valor)
    else: print("Comando desconocido:", comando)

poll = select.poll()
poll.register(sys.stdin, select.POLLIN)

print("Sistema listo. Comandos: pwm, dir, lf, lb, ll, lr, ldr, circle, infinite, zigzag, especial")
print("> ", end="")
while True:
    if poll.poll(0):                  # ¿hay algo escrito en la consola?
        procesar(sys.stdin.readline())
        print("> ", end="")
    luces.actualizar_ldr()            # mantiene vivo el modo LDR
    sleep_ms(50)