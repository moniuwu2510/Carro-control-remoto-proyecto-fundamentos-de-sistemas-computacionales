"""Carro GUI: interfaz grafica para controlar el carro por WiFi (se ejecuta en la computadora, con Python 3).

Que hace este programa
- Se conecta a la Raspberry Pi Pico 2W del carro por WiFi (socket TCP, puerto 5000).
- Envia comandos de texto (pwm, dir, stop, lf, lb, ll, lr, ldr, ldrval, dec, patrones) y muestra las respuestas.
- Esta dividida en secciones: menu principal, Movimiento, Luces, Decrementador y Acerca de.

Teclas en la seccion Movimiento: flechas = direccion, W / S = subir / bajar potencia, Espacio = STOP.
Esc vuelve al menu desde cualquier seccion.

Archivos que usa (en la misma carpeta que este script):
- fondo.jpg (o la imagen elegida con "Cambiar fondo", guardada en fondo.txt)
- la foto de cada integrante indicada en INTEGRANTES
"""
import os
import queue
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import filedialog
from tkinter import font as tkfont

try:
    from PIL import Image, ImageOps, ImageTk   # Pillow: permite fotos y fondo de cualquier formato y tamano
    HAY_PIL = True
except ImportError:                             # sin Pillow solo sirven PNG o GIF y no se reescalan
    HAY_PIL = False

# ================================================================ datos editables (seccion Acerca de)
NOMBRE_PROGRAMA = "Carro GUI"
VERSION = "2.0"
INSTITUCION = "Tecnológico de Costa Rica"
INTEGRANTES = [                                 # nombre, institucion y foto (la foto va en esta misma carpeta)
    {"nombre": "Mónica Blanco", "institucion": INSTITUCION, "foto": "foto.jpeg"},
]

# ================================================================ configuracion
PUERTO = 5000                   # puerto donde escucha el servidor de la Pico
PERIODO_MS = 500                # cada cuanto se pide la lectura del LDR (ms)
LDR_MIN_DEF = 6000              # calibracion: lectura con la LDR tapada (con margen)
LDR_MAX_DEF = 40000             # calibracion: lectura con linterna (con margen)
PATRONES = ["circle", "infinite", "zigzag", "especial"]
FONDO_IMAGEN = "fondo.jpg"      # imagen de fondo por defecto (en la misma carpeta)
CARPETA = os.path.dirname(os.path.abspath(__file__))     # carpeta donde esta este script
ARCHIVO_FONDO = os.path.join(CARPETA, "fondo.txt")       # guarda la ruta del fondo elegido con "Cambiar fondo"
# Tabla del decrementador circular de 5 (entrada -> salida), para comparar lo que lee la Pico
TABLA_DEC = {0: 5, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 0}

# ================================================================ colores de paneles, botones y textos
# FONDO solo se ve si no se encuentra la imagen de fondo.
FONDO = "#1c1f23"
PANEL = "#2a2d32"
PANEL_OSC = "#202327"
CAMPO = "#15171a"
BOTON = "#4a7298"
BOTON_HOVER = "#5d88b3"
BOTON_ON = "#2f9e6e"
BOTON_OFF = "#3a3e44"
BORDE_BOTON = "#8fb0cf"
TEXTO = "#ffffff"
TENUE = "#9aa4ae"
LAVANDA = "#aaa4cc"
CIAN = "#38c8f2"
ROJO = "#ff4d4d"
AMBAR = "#ffb22e"
VERDE = "#4cd47c"
LINEA = "#3a3e44"
APAGADA = "#3a3e44"

ANCHO, ALTO_CUERPO = 1040, 500          # tamano del area de las secciones (sin la barra de arriba ni el registro)


def rect_redondo(c, x1, y1, x2, y2, r, **kw):
    """Rectangulo con esquinas redondeadas en un Canvas."""
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


def dibujar_carro(c, cx, cy, s, luces, nota=None):
    """Dibuja el carro visto desde arriba (frente hacia arriba) con sus luces.

    luces: dict con lf (delanteras), lb (traseras), ll (direccional izq.), lr (direccional der.)
    """
    c.delete("carro")
    t = "carro"
    # ruedas
    for dx in (-1, 1):
        for dy in (-1, 1):
            x = cx + dx * 66 * s
            y = cy + dy * 62 * s
            c.create_rectangle(x - 9 * s, y - 22 * s, x + 9 * s, y + 22 * s, fill="#0e0f11", outline="#55595f", tags=t)
    # carroceria
    rect_redondo(c, cx - 58 * s, cy - 112 * s, cx + 58 * s, cy + 112 * s, 34 * s,
                 fill=BOTON, outline=BORDE_BOTON, width=2, tags=t)
    rect_redondo(c, cx - 42 * s, cy - 62 * s, cx + 42 * s, cy - 22 * s, 12 * s, fill="#2d4a66", outline="", tags=t)
    rect_redondo(c, cx - 40 * s, cy + 40 * s, cx + 40 * s, cy + 70 * s, 10 * s, fill="#2d4a66", outline="", tags=t)

    def luz(x, y, r, encendida, color, halo):
        """Dibuja una luz del carro: un circulo encendido (con halo) o apagado."""
        if encendida:
            c.create_oval(x - r * 2, y - r * 2, x + r * 2, y + r * 2, fill=halo, outline="", tags=t)
        c.create_oval(x - r, y - r, x + r, y + r, fill=color if encendida else APAGADA,
                      outline="#111", tags=t)

    # delanteras (lf) y traseras (lb)
    for dx in (-1, 1):
        luz(cx + dx * 34 * s, cy - 104 * s, 10 * s, luces.get("lf"), "#fff3b0", "#5c5530")
        luz(cx + dx * 34 * s, cy + 104 * s, 10 * s, luces.get("lb"), ROJO, "#5a2222")
    # direccionales: izquierda (ll) y derecha (lr), como flechas a los lados
    for dx, clave in ((-1, "ll"), (1, "lr")):
        on = luces.get(clave)
        x = cx + dx * 60 * s
        y = cy - 8 * s
        if on:
            c.create_oval(x - 18 * s, y - 18 * s, x + 18 * s, y + 18 * s, fill="#5a4416", outline="", tags=t)
        c.create_polygon(x, y - 10 * s, x, y + 10 * s, x + dx * 14 * s, y,
                         fill=AMBAR if on else APAGADA, outline="#111", tags=t)
    c.create_text(cx, cy - 135 * s, text="frente", fill=TENUE, font=("Segoe UI", 10), tags=t)
    if nota:
        c.create_text(cx, cy + 140 * s, text=nota, fill=TENUE, font=("Segoe UI", 10), tags=t)


class Conexion:
    """Maneja el socket y un hilo que recibe lo que envia la Pico."""

    def __init__(self, cola):
        """Guarda la cola donde se dejan los mensajes recibidos; empieza sin conexion."""
        self.sock = None
        self.cola = cola

    @property
    def activa(self):
        """True si hay una conexion abierta con la Pico."""
        return self.sock is not None

    def conectar(self, ip):
        """Abre la conexion TCP con la Pico (espera hasta 3 s) y arranca el hilo que recibe sus respuestas."""
        sock = socket.create_connection((ip, PUERTO), timeout=3)
        sock.settimeout(None)
        self.sock = sock
        threading.Thread(target=self._leer, args=(sock,), daemon=True).start()

    def _leer(self, sock):
        """Hilo aparte: lee linea por linea lo que envia la Pico y lo deja en la cola.

        Al cerrarse la conexion avisa con ("cerrada", sock) para que la ventana actualice su estado.
        """
        try:
            for linea in sock.makefile("r", newline="\n"):
                self.cola.put(("rx", linea.strip()))
        except (OSError, ValueError):
            pass
        self.cola.put(("cerrada", sock))

    def enviar(self, cmd):
        """Envia un comando terminado en salto de linea. Devuelve False si no se pudo (y cierra la conexion)."""
        if not self.sock:
            return False
        try:
            self.sock.sendall((cmd + "\n").encode())
            return True
        except OSError:
            self.cerrar()
            return False

    def cerrar(self):
        """Cierra la conexion si estaba abierta."""
        sock, self.sock = self.sock, None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()


class App(tk.Tk):
    """Ventana principal. Organiza las secciones y traduce lo que hace el usuario en comandos para la Pico.

    Estado que guarda:
    - patron: True mientras la Pico ejecuta un patron (solo se permite STOP).
    - dec_modo: None (apagado), "ldr" (entrada por fotorresistencia) o "manual" (prueba por teclado).
    - luz / luz_dec: luces encendidas en control manual / las que muestra el decrementador.
    - ldr_auto: True si el modo automatico de luces por LDR esta activo.
    """
    def __init__(self):
        """Crea la ventana: fuentes, estado inicial, barra de conexion, secciones, registro, teclado y ciclos."""
        super().__init__()
        self.title(NOMBRE_PROGRAMA)
        self.configure(bg=FONDO)
        self.resizable(False, False)

        familias = set(tkfont.families())
        letra_boton = "Impact" if "Impact" in familias else "Segoe UI"
        self.f_titulo = ("Segoe UI", 20, "bold")
        self.f_boton = (letra_boton, 15)
        self.f_boton_peq = (letra_boton, 12)
        self.f_texto = ("Segoe UI", 12)
        self.f_peq = ("Segoe UI", 10)
        self.f_mono = ("Consolas", 10)

        self.cola = queue.Queue()
        self.con = Conexion(self.cola)
        self.patron = False             # True mientras la Pico ejecuta un patron
        self.dec_modo = None            # None = apagado, "ldr" = entrada por LDR, "manual" = prueba por teclado
        self.ok_silenciosos = 0         # respuestas "ok" que no se muestran en el registro
        self.pwm_enviado = 0
        self.dir_actual = None
        self.teclas = set()             # teclas presionadas (para no repetir al mantenerlas)
        self.luz = {"lf": 0, "lb": 0, "ll": 0, "lr": 0}      # luces en control manual
        self.luz_dec = {"lf": 0, "lb": 0, "ll": 0, "lr": 0}  # luces que muestra el decrementador
        self.ldr_auto = False
        self.actual = None
        self.lbl_fondos = []            # una etiqueta con la imagen de fondo por pantalla
        self.img_fondo = self._cargar_fondo(self._ruta_fondo_guardada())

        self._barra_superior()
        self.cuerpo = tk.Frame(self, bg=FONDO, width=ANCHO, height=ALTO_CUERPO)
        self.cuerpo.pack()
        self._registro()

        self.pantallas = {
            "menu": self._pantalla_menu(),
            "mov": self._pantalla_movimiento(),
            "luces": self._pantalla_luces(),
            "dec": self._pantalla_decrementador(),
            "about": self._pantalla_about(),
        }
        self._aplicar_fondo()
        self._estado_conexion()
        self._refrescar_luces()
        self._mostrar("menu")

        self.bind_all("<KeyPress>", self._tecla_abajo)
        self.bind_all("<KeyRelease>", self._tecla_arriba)
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.after(100, self._procesar_cola)
        self.after(PERIODO_MS, self._ciclo)

    # ================================================================ piezas de estilo
    def _boton(self, padre, texto, cmd, ancho=20, color=BOTON, hover=BOTON_HOVER, fuente=None):
        """Crea un boton con el estilo de la interfaz y efecto al pasar el mouse por encima."""
        b = tk.Button(padre, text=texto, command=cmd, font=fuente or self.f_boton, width=ancho,
                      bg=color, fg=TEXTO, activebackground=hover, activeforeground=TEXTO,
                      disabledforeground="#7d8691", relief="flat", bd=0, pady=5, cursor="hand2",
                      takefocus=0, highlightthickness=1, highlightbackground=BORDE_BOTON)
        b.base, b.hover = color, hover
        b.bind("<Enter>", lambda e: b.config(bg=b.hover) if str(b["state"]) != "disabled" else None)
        b.bind("<Leave>", lambda e: b.config(bg=b.base))
        return b

    def _color_boton(self, b, color, habilitado=True):
        """Cambia el color de un boton y lo habilita o deshabilita (deshabilitado se ve gris)."""
        b.base = color if habilitado else BOTON_OFF
        b.config(bg=b.base, state="normal" if habilitado else "disabled")

    def _panel(self, x, y, w, h, titulo=None, padre=None):
        """Crea un panel (recuadro) en la pantalla que se esta construyendo, con un titulo opcional."""
        p = tk.Frame(padre or self.cuerpo_actual, bg=PANEL, width=w, height=h)
        p.place(x=x, y=y)
        if titulo:
            tk.Label(p, text=titulo, font=("Segoe UI", 14, "bold"), bg=PANEL, fg=TEXTO).place(x=16, y=10)
        return p

    def _etiqueta(self, padre, texto, fuente=None, color=TEXTO, bg=PANEL, **kw):
        """Crea un texto (Label) con la fuente y colores de la interfaz."""
        return tk.Label(padre, text=texto, font=fuente or self.f_texto, fg=color, bg=bg, **kw)

    def _campo(self, padre, var, ancho, fuente=None):
        """Crea un campo de texto (Entry) oscuro, centrado, ligado a una variable de tkinter."""
        return tk.Entry(padre, textvariable=var, width=ancho, font=fuente or self.f_texto, bg=CAMPO, fg=TEXTO,
                        insertbackground=TEXTO, relief="flat", highlightthickness=1,
                        highlightbackground=LINEA, highlightcolor=CIAN, justify="center")

    def _nueva_pantalla(self):
        """Crea el marco de una seccion con la imagen de fondo detras; los paneles se agregan encima."""
        f = tk.Frame(self.cuerpo, bg=FONDO, width=ANCHO, height=ALTO_CUERPO)
        f.place(x=0, y=0)
        fondo = tk.Label(f, bd=0, bg=FONDO)      # se crea primero para que quede detras de los paneles
        fondo.place(x=0, y=0, width=ANCHO, height=ALTO_CUERPO)
        self.lbl_fondos.append(fondo)
        self.cuerpo_actual = f
        return f

    # ================================================================ imagen de fondo
    @staticmethod
    def _ruta_fondo_guardada():
        """Ruta elegida la ultima vez (fondo.txt) o la imagen por defecto."""
        try:
            with open(ARCHIVO_FONDO, encoding="utf-8") as f:
                ruta = f.read().strip()
            if ruta:
                return ruta
        except OSError:
            pass
        return os.path.join(CARPETA, FONDO_IMAGEN)

    @staticmethod
    def _cargar_fondo(ruta):
        """Carga la imagen ajustada al area de las secciones (1040 x 500). None si no se puede."""
        if not ruta or not os.path.exists(ruta):
            return None
        try:
            if HAY_PIL:                          # recorta y escala para llenar todo el espacio
                img = ImageOps.fit(Image.open(ruta).convert("RGB"), (ANCHO, ALTO_CUERPO))
                return ImageTk.PhotoImage(img)
            img = tk.PhotoImage(file=ruta)       # sin Pillow solo sirven PNG o GIF, sin reescalar
            factor = max(1, img.width() // ANCHO)
            return img.subsample(factor) if factor > 1 else img
        except Exception:
            return None

    def _aplicar_fondo(self):
        """Pone la imagen de fondo en todas las secciones y en el menu."""
        img = self.img_fondo or ""
        for lbl in self.lbl_fondos:
            lbl.config(image=img)
        self.can_menu.itemconfigure(self.item_fondo, image=img)

    def _elegir_fondo(self):
        """Abre una ventana para elegir una imagen, la aplica como fondo y guarda su ruta en fondo.txt."""
        ruta = filedialog.askopenfilename(
            title="Elegir imagen de fondo",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp"), ("Todos los archivos", "*.*")])
        if not ruta:
            return
        img = self._cargar_fondo(ruta)
        if img is None:
            self._log("No se pudo abrir la imagen" + ("" if HAY_PIL else " (sin Pillow solo sirven PNG o GIF)"))
            return
        self.img_fondo = img
        self._aplicar_fondo()
        self._guardar_fondo(ruta)
        self._log("Fondo cambiado: " + os.path.basename(ruta))

    @staticmethod
    def _guardar_fondo(ruta):
        """Guarda la ruta de la imagen de fondo en fondo.txt para la proxima vez que se abra la interfaz."""
        try:
            with open(ARCHIVO_FONDO, "w", encoding="utf-8") as f:
                f.write(ruta)
        except OSError:
            pass

    # ================================================================ barra superior y registro
    def _barra_superior(self):
        """Barra de arriba (siempre visible): IP, Buscar carro, Conectar, estado, seccion actual y boton Menu."""
        barra = tk.Frame(self, bg=PANEL_OSC, width=ANCHO, height=54)
        barra.pack()
        barra.pack_propagate(False)
        self._etiqueta(barra, "IP de la Pico:", bg=PANEL_OSC).pack(side="left", padx=(18, 6))
        self.var_ip = tk.StringVar()
        e = self._campo(barra, self.var_ip, 16)
        e.pack(side="left", ipady=3)
        e.bind("<Return>", lambda ev: self._alternar_conexion())
        self.btn_buscar = self._boton(barra, "Buscar carro", self._buscar_carro, ancho=11, fuente=self.f_boton_peq)
        self.btn_buscar.pack(side="left", padx=(10, 0))
        self.btn_con = self._boton(barra, "Conectar", self._alternar_conexion, ancho=11, fuente=self.f_boton_peq)
        self.btn_con.pack(side="left", padx=10)
        self.lbl_estado = tk.Label(barra, text="", font=("Segoe UI", 11, "bold"), bg=PANEL_OSC)
        self.lbl_estado.pack(side="left", padx=6)
        self.btn_menu = self._boton(barra, "← Menú", lambda: self._mostrar("menu"), ancho=9, fuente=self.f_boton_peq)
        self.lbl_seccion = tk.Label(barra, text="", font=("Segoe UI", 13, "bold"), bg=PANEL_OSC, fg=LAVANDA)
        self.lbl_seccion.pack(side="right", padx=18)

    def _registro(self):
        """Registro de abajo (siempre visible): muestra los comandos enviados y las respuestas de la Pico."""
        f = tk.Frame(self, bg=PANEL_OSC, width=ANCHO, height=130)
        f.pack()
        f.pack_propagate(False)
        tk.Label(f, text="Registro", font=("Segoe UI", 10, "bold"), bg=PANEL_OSC, fg=TENUE).pack(anchor="w", padx=18, pady=(6, 0))
        cont = tk.Frame(f, bg=PANEL_OSC)
        cont.pack(fill="both", expand=True, padx=18, pady=(2, 10))
        self.txt = tk.Text(cont, height=5, font=self.f_mono, bg=CAMPO, fg="#c9d3dc", relief="flat",
                           state="disabled", highlightthickness=0, takefocus=0)
        sb = tk.Scrollbar(cont, command=self.txt.yview)
        self.txt.config(yscrollcommand=sb.set)
        self.txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    # ================================================================ pantallas
    def _pantalla_menu(self):
        """Menu principal: botones de las secciones, carrito de ejemplo, instrucciones y Cambiar fondo."""
        f = self._nueva_pantalla()
        c = tk.Canvas(f, width=ANCHO, height=ALTO_CUERPO, bg=FONDO, highlightthickness=0)
        c.place(x=0, y=0)
        self.can_menu = c
        self.item_fondo = c.create_image(0, 0, anchor="nw")

        titulo = tk.Label(f, text="Seleccione una sección", font=self.f_titulo, bg=PANEL, fg=TEXTO, padx=22, pady=6)
        c.create_window(270, 50, window=titulo)
        opciones = [("Movimiento", "mov"), ("Luces", "luces"), ("Decrementador", "dec"), ("Acerca de", "about")]
        for i, (texto, clave) in enumerate(opciones):
            b = self._boton(f, texto, lambda k=clave: self._mostrar(k), ancho=20)
            c.create_window(270, 140 + i * 72, window=b)
        c.create_window(270, 450, window=self._boton(f, "Salir", self._cerrar, ancho=20))
        c.create_window(960, 478, window=self._boton(f, "Cambiar fondo", self._elegir_fondo, ancho=12,
                                                     fuente=self.f_boton_peq))

        dibujar_carro(c, 690, 150, 0.62, {"lf": 1, "lb": 1, "ll": 1, "lr": 0})
        c.create_text(850, 120, text="Control", font=("Segoe UI", 34, "bold"), fill=LAVANDA)
        c.create_text(850, 170, text="del Carro", font=("Segoe UI", 34, "bold"), fill=LAVANDA)

        caja = tk.Frame(f, bg=PANEL, padx=18, pady=10)
        lineas = ["Instrucciones de uso:",
                  "1. Pulsa Buscar carro (o escribe la IP y Conectar)",
                  "2. Elige una sección",
                  "Flechas = dirección   ·   W / S = potencia",
                  "Espacio = STOP   ·   Esc = volver al menú"]
        for i, l in enumerate(lineas):
            tk.Label(caja, text=l, font=("Segoe UI", 13, "bold") if i == 0 else self.f_texto,
                     bg=PANEL, fg=TEXTO).pack()
        c.create_window(775, 372, window=caja)
        return f

    def _pantalla_movimiento(self):
        """Seccion Movimiento: flechas de direccion, STOP, potencia (deslizador y W/S) y modos demo."""
        f = self._nueva_pantalla()

        # --- direccion
        p = self._panel(30, 18, 470, 320, "Dirección  (flechas del teclado)")
        self.btn_dir = {}
        teclado = tk.Frame(p, bg=PANEL)
        teclado.place(x=235, y=150, anchor="center")
        flechas = [(0, "▲", 0, 1), (-1, "◀", 1, 0), (2, "▼", 1, 1), (1, "▶", 1, 2)]
        for valor, simbolo, fila, col in flechas:
            b = self._boton(teclado, simbolo, lambda v=valor: self._direccion(v), ancho=4,
                            fuente=("Segoe UI", 20, "bold"))
            b.grid(row=fila, column=col, padx=5, pady=5)
            self.btn_dir[valor] = b
        self.lbl_dir = self._etiqueta(p, "Dirección: --", fuente=("Segoe UI", 12, "bold"), color=TENUE)
        self.lbl_dir.place(x=235, y=232, anchor="center")
        stop = self._boton(p, "STOP  (espacio)", self._stop, ancho=24, color="#c62828", hover="#e04848")
        stop.place(x=235, y=280, anchor="center")

        # --- potencia
        p = self._panel(530, 18, 480, 320, "Potencia (pwm)")
        self.lbl_pwm = self._etiqueta(p, "0", fuente=("Segoe UI", 44, "bold"))
        self.lbl_pwm.place(x=240, y=95, anchor="center")
        self.lbl_pwm_txt = self._etiqueta(p, "detenido", color=TENUE)
        self.lbl_pwm_txt.place(x=240, y=140, anchor="center")
        self.var_pwm = tk.IntVar(value=0)
        esc = tk.Scale(p, from_=-4, to=4, orient="horizontal", length=400, variable=self.var_pwm,
                       tickinterval=1, showvalue=False, bg=PANEL, fg=TEXTO, troughcolor=CAMPO,
                       activebackground=CIAN, highlightthickness=0, bd=0, sliderrelief="flat",
                       font=self.f_peq, takefocus=0, command=lambda v: self._mostrar_pwm())
        esc.place(x=240, y=200, anchor="center")
        esc.bind("<ButtonRelease-1>", lambda e: self._enviar_pwm())
        self._etiqueta(p, "W  sube      ·      S  baja", fuente=("Segoe UI", 13, "bold"), color=CIAN).place(
            x=240, y=255, anchor="center")
        self._etiqueta(p, "-4 = reversa máxima   ·   0 = detenido   ·   4 = máxima", fuente=self.f_peq,
                       color=TENUE).place(x=240, y=288, anchor="center")

        # --- modos demo
        p = self._panel(30, 352, 980, 132, "Modos demo")
        for i, nombre in enumerate(PATRONES):
            b = self._boton(p, nombre, lambda n=nombre: self._iniciar_patron(n), ancho=14)
            b.place(x=130 + i * 240, y=68, anchor="center")
        self.lbl_patron = self._etiqueta(p, "Sin patrón en curso  ·  STOP lo cancela", color=TENUE)
        self.lbl_patron.place(x=490, y=110, anchor="center")
        return f

    def _pantalla_luces(self):
        """Seccion Luces: botones de cada grupo de luces, modo automatico por LDR, barra del LDR y carrito."""
        f = self._nueva_pantalla()
        p = self._panel(30, 18, 560, 466, "Luces")
        self.btn_luz = {}
        opciones = [("lf", "Frontales"), ("lb", "Traseras"), ("ll", "Direccional izq."), ("lr", "Direccional der.")]
        for i, (clave, texto) in enumerate(opciones):
            b = self._boton(p, texto, lambda k=clave: self._alternar_luz(k), ancho=17)
            b.place(x=145 + (i % 2) * 270, y=80 + (i // 2) * 62, anchor="center")
            self.btn_luz[clave] = b
        self.btn_ldr_auto = self._boton(p, "Modo automático por luz (LDR)", self._alternar_ldr_auto, ancho=36)
        self.btn_ldr_auto.place(x=280, y=212, anchor="center")
        self.lbl_aviso_luces = self._etiqueta(p, "", fuente=self.f_peq, color=AMBAR)
        self.lbl_aviso_luces.place(x=280, y=250, anchor="center")

        self._etiqueta(p, "Fotorresistencia", fuente=("Segoe UI", 13, "bold")).place(x=20, y=290)
        self.lbl_ldr = self._etiqueta(p, "Lectura LDR: --", color=TENUE)
        self.lbl_ldr.place(x=20, y=322)
        self.can_ldr = tk.Canvas(p, width=520, height=34, bg=PANEL, highlightthickness=0)
        self.can_ldr.place(x=20, y=356)
        self._etiqueta(p, "0", fuente=self.f_peq, color=TENUE).place(x=20, y=394)
        self._etiqueta(p, "65535", fuente=self.f_peq, color=TENUE).place(x=540, y=394, anchor="ne")
        self._dibujar_barra_ldr(None)

        p = self._panel(620, 18, 390, 466, "Vista del carro")
        self.can_carro_luces = tk.Canvas(p, width=360, height=400, bg=PANEL, highlightthickness=0)
        self.can_carro_luces.place(x=15, y=50)
        return f

    def _pantalla_decrementador(self):
        """Seccion Decrementador: modo por LDR (8 intervalos), prueba manual por teclado y resultado."""
        f = self._nueva_pantalla()
        p = self._panel(30, 18, 600, 466, "Decrementador circular de 5")

        # --- modo LDR
        self.btn_dec = self._boton(p, "Activar decrementador (entrada = LDR)", self._alternar_dec, ancho=36)
        self.btn_dec.place(x=300, y=70, anchor="center")
        fila = tk.Frame(p, bg=PANEL)
        fila.place(x=300, y=112, anchor="center")
        self._etiqueta(fila, "LDR mín:").pack(side="left")
        self.var_min = tk.StringVar(value=str(LDR_MIN_DEF))
        self._campo(fila, self.var_min, 7).pack(side="left", padx=(4, 18), ipady=2)
        self._etiqueta(fila, "máx:").pack(side="left")
        self.var_max = tk.StringVar(value=str(LDR_MAX_DEF))
        self._campo(fila, self.var_max, 7).pack(side="left", padx=4, ipady=2)
        self.can_int = tk.Canvas(p, width=560, height=58, bg=PANEL, highlightthickness=0)
        self.can_int.place(x=20, y=136)
        self._dibujar_intervalos(None)

        # --- prueba manual
        tk.Frame(p, bg=LINEA, width=560, height=1).place(x=20, y=206)
        self._etiqueta(p, "Prueba manual por teclado", fuente=("Segoe UI", 13, "bold")).place(x=20, y=216)
        fila = tk.Frame(p, bg=PANEL)
        fila.place(x=20, y=252)
        self._etiqueta(fila, "Entrada (0 a 7):").pack(side="left")
        self.var_manual = tk.StringVar()
        self.ent_manual = self._campo(fila, self.var_manual, 3, fuente=("Segoe UI", 16, "bold"))
        self.ent_manual.pack(side="left", padx=8)
        self.ent_manual.bind("<Return>", lambda e: self._probar_manual())
        self._boton(fila, "Probar", self._probar_manual, ancho=9, fuente=self.f_boton_peq).pack(side="left", padx=6)
        self._etiqueta(fila, "o presiona Enter", fuente=self.f_peq, color=TENUE).pack(side="left", padx=6)

        # --- resultado
        self.can_bits = tk.Canvas(p, width=560, height=110, bg=PANEL, highlightthickness=0)
        self.can_bits.place(x=20, y=300)
        self.lbl_dec = self._etiqueta(p, "Apagado (A B C = 111, salida 000)", fuente=("Segoe UI", 12, "bold"),
                                      color=TENUE)
        self.lbl_dec.place(x=300, y=432, anchor="center")
        self._dibujar_bits(None, None)

        p = self._panel(660, 18, 350, 466, "LED del carro")
        self.can_carro_dec = tk.Canvas(p, width=320, height=330, bg=PANEL, highlightthickness=0)
        self.can_carro_dec.place(x=15, y=46)
        leyenda = ("Delanteras = x  (MSB)\n"
                   "Direccionales = y\n"
                   "Traseras = z  (LSB)")
        self._etiqueta(p, leyenda, fuente=self.f_peq, color=TENUE, justify="center").place(x=175, y=418, anchor="center")
        return f

    def _pantalla_about(self):
        """Seccion Acerca de: nombre, version, guia de uso e integrantes con foto e institucion."""
        f = self._nueva_pantalla()
        p = self._panel(30, 18, 980, 466)
        self._etiqueta(p, NOMBRE_PROGRAMA, fuente=("Segoe UI", 24, "bold"), color=LAVANDA).place(x=30, y=20)
        self._etiqueta(p, "Versión " + VERSION, color=TENUE).place(x=32, y=66)
        guia = ("Guía básica\n"
                "1. Enciende el carro: la Pico arranca sola (main.py). LED fijo = lista.\n"
                "2. Pulsa Buscar carro, o escribe la IP arriba y pulsa Conectar.\n"
                "3. Movimiento: flechas para la dirección, W / S para la potencia,\n"
                "    Espacio para STOP. Los modos demo están en la misma sección.\n"
                "4. Luces: enciende cada grupo o usa el modo automático por LDR.\n"
                "5. Decrementador: prueba manual (0 a 7 + Enter) o entrada por LDR\n"
                "    (8 intervalos). La salida se ve en los LED del carro.\n"
                "6. Esc vuelve al menú desde cualquier sección.")
        self._etiqueta(p, guia, fuente=("Segoe UI", 11), justify="left").place(x=30, y=105)

        self._etiqueta(p, "Integrantes", fuente=("Segoe UI", 14, "bold")).place(x=600, y=20)
        self.fotos = []                          # guarda las imagenes para que no las borre Python
        for i, persona in enumerate(INTEGRANTES):
            col = tk.Frame(p, bg=PANEL)
            col.place(x=600 + i * 190, y=60)
            foto = self._cargar_foto(persona["foto"])
            if foto:
                self.fotos.append(foto)
                tk.Label(col, image=foto, bg=PANEL).pack()
            else:
                tk.Label(col, text="[sin foto]", width=16, height=8, bg=CAMPO, fg=TENUE).pack()
            self._etiqueta(col, persona["nombre"], fuente=("Segoe UI", 11, "bold"), wraplength=170).pack(pady=(8, 0))
            self._etiqueta(col, persona["institucion"], fuente=self.f_peq, color=TENUE, wraplength=170).pack()
        return f

    @staticmethod
    def _cargar_foto(nombre):
        """Carga la foto de un integrante (maximo 160 x 160). Devuelve None si no existe o no se puede abrir."""
        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), nombre)
        if not os.path.exists(ruta):
            return None
        try:
            if HAY_PIL:
                img = Image.open(ruta)
                img.thumbnail((160, 160))
                return ImageTk.PhotoImage(img)
            img = tk.PhotoImage(file=ruta)       # sin Pillow solo sirven PNG o GIF
            factor = max(1, max(img.width(), img.height()) // 160)
            return img.subsample(factor) if factor > 1 else img
        except Exception:
            return None

    def _mostrar(self, clave):
        """Muestra la seccion indicada, actualiza la barra superior y decide quien recibe el teclado."""
        nombres = {"menu": "", "mov": "Movimiento", "luces": "Luces", "dec": "Decrementador", "about": "Acerca de"}
        self.actual = clave
        self.pantallas[clave].tkraise()
        self.lbl_seccion.config(text=nombres[clave])
        if clave == "menu":
            self.btn_menu.pack_forget()
        else:
            self.btn_menu.pack(side="right", padx=4)
        self.teclas.clear()
        if clave == "dec":
            self.ent_manual.focus_set()
        else:
            self.focus_set()                     # quita el foco de los campos para que las teclas lleguen

    # ================================================================ teclado
    def _tecla_abajo(self, e):
        """Atiende una tecla presionada: Esc vuelve al menu; en Movimiento, flechas, W, S y Espacio.

        Una tecla mantenida no se repite: se guarda en self.teclas hasta que se suelta.
        """
        k = e.keysym
        if k == "Escape":
            if self.actual != "menu":
                self._mostrar("menu")
            return
        if self.actual != "mov" or k in self.teclas:     # mantener una tecla no la repite
            return
        if isinstance(self.focus_get(), tk.Entry):        # escribiendo en un campo (por ejemplo la IP)
            return
        self.teclas.add(k)
        if k in ("Up", "Left", "Down", "Right"):
            self._direccion({"Up": 0, "Left": -1, "Down": 2, "Right": 1}[k])
        elif k in ("w", "W"):
            self._cambiar_pwm(1)
        elif k in ("s", "S"):
            self._cambiar_pwm(-1)
        elif k == "space":
            self._stop()

    def _tecla_arriba(self, e):
        """Al soltar una tecla, la quita de las presionadas para que se pueda volver a usar."""
        self.teclas.discard(e.keysym)

    # ================================================================ conexion
    def _alternar_conexion(self):
        """Boton Conectar / Desconectar: abre la conexion con la IP escrita o la cierra (enviando stop)."""
        if self.con.activa:
            self._enviar("stop")
            self.con.cerrar()
            self._al_desconectar()
            self._log("Desconectado")
        else:
            ip = self.var_ip.get().strip()
            if not ip:
                self._log("Escribe la IP de la Pico")
                return
            self._log("Conectando a %s ..." % ip)
            self.update_idletasks()
            try:
                self.con.conectar(ip)
                self.ok_silenciosos = 0
                self._log("Conectado")
            except OSError as e:
                self._log("No se pudo conectar: %s" % e)
        self._estado_conexion()

    def _al_desconectar(self):
        """Deja la interfaz en estado 'sin conexion': sin patron ni decrementador activo."""
        self.patron = False
        self.dec_modo = None
        self.lbl_patron.config(text="Sin patrón en curso  ·  STOP lo cancela")
        self._actualizar_dec()
        self._refrescar_luces()

    # ---------------------------------------------------------------- buscar la Pico en la red
    def _buscar_carro(self):
        """Prueba todas las IP de la red local en el puerto 5000 y se conecta a la que responda pong."""
        if self.con.activa:
            self._log("Ya hay conexión")
            return
        propia = self._ip_propia()
        if not propia:
            self._log("No se pudo saber la IP de esta computadora (¿estás conectado al WiFi?)")
            return
        red = propia.rsplit(".", 1)[0]
        self._log("Buscando el carro en %s.1 a %s.254 ..." % (red, red))
        self._color_boton(self.btn_buscar, BOTON, habilitado=False)
        threading.Thread(target=self._hilo_buscar, args=(red, propia), daemon=True).start()

    @staticmethod
    def _ip_propia():
        """Averigua la IP de esta computadora en la red WiFi (para saber que red revisar)."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))           # no envia nada: solo elige la interfaz de red
            ip = s.getsockname()[0]
            s.close()
            return ip
        except OSError:
            try:
                return socket.gethostbyname(socket.gethostname())
            except OSError:
                return None

    @staticmethod
    def _probar_ip(ip):
        """True si en esa IP hay un servidor del carro (responde pong a ping)."""
        try:
            with socket.create_connection((ip, PUERTO), timeout=0.6) as s:
                s.settimeout(1.5)
                s.sendall(b"ping\n")
                return s.recv(32).startswith(b"pong")
        except OSError:
            return False

    def _hilo_buscar(self, red, propia):
        """Hilo aparte: prueba las 254 direcciones de la red (64 a la vez) y avisa por la cola cual respondio."""
        candidatas = ["%s.%d" % (red, i) for i in range(1, 255) if "%s.%d" % (red, i) != propia]
        encontrada = None
        with ThreadPoolExecutor(max_workers=64) as ex:
            for ip, ok in zip(candidatas, ex.map(self._probar_ip, candidatas)):
                if ok:
                    encontrada = ip
                    break
        self.cola.put(("busqueda", encontrada))

    def _fin_busqueda(self, ip):
        """Termina la busqueda: si encontro el carro escribe su IP y se conecta; si no, lo avisa."""
        self._color_boton(self.btn_buscar, BOTON)
        if not ip:
            self._log("No se encontró el carro. Revisa que la Pico tenga el LED fijo y que estén en la misma red.")
            return
        self._log("Carro encontrado en " + ip)
        self.var_ip.set(ip)
        if not self.con.activa:
            self._alternar_conexion()

    def _estado_conexion(self):
        """Actualiza el indicador Conectado / Desconectado y el texto del boton."""
        if self.con.activa:
            self.lbl_estado.config(text="● Conectado", fg=VERDE)
            self.btn_con.config(text="Desconectar")
        else:
            self.lbl_estado.config(text="● Desconectado", fg=ROJO)
            self.btn_con.config(text="Conectar")

    def _enviar(self, cmd, log=True):
        """Envia un comando a la Pico y lo anota en el registro.

        No envia nada si no hay conexion, ni (salvo stop) mientras corre un patron,
        porque en ese momento la Pico solo atiende stop.
        """
        if not self.con.activa:
            self._log("No hay conexión")
            return False
        if self.patron and cmd != "stop":       # durante un patron la Pico solo atiende stop
            if log:
                self._log("Patrón en curso: presiona STOP (espacio) para cancelarlo")
            return False
        ok = self.con.enviar(cmd)
        if ok and log:
            self._log("→ " + cmd)
        if not ok:
            self._log("Se perdió la conexión")
            self._estado_conexion()
        return ok

    # ================================================================ movimiento
    def _direccion(self, valor):
        """Envia dir con el valor indicado (-1 izquierda, 0 recto, 1 derecha, 2 retroceder)."""
        if self._enviar("dir %d" % valor):
            self.dir_actual = valor
        self._pintar_direccion()

    def _pintar_direccion(self):
        """Resalta el boton de la direccion actual y escribe su nombre."""
        nombres = {0: "Recto", -1: "Izquierda", 1: "Derecha", 2: "Retroceder", None: "--"}
        for v, b in self.btn_dir.items():
            self._color_boton(b, "#2d8fb8" if v == self.dir_actual else BOTON)
        self.lbl_dir.config(text="Dirección: " + nombres[self.dir_actual])

    def _mostrar_pwm(self):
        """Muestra la potencia elegida en grande (adelante, reversa o detenido)."""
        v = self.var_pwm.get()
        self.lbl_pwm.config(text=str(v), fg=CIAN if v > 0 else (AMBAR if v < 0 else TEXTO))
        self.lbl_pwm_txt.config(text="adelante" if v > 0 else ("reversa" if v < 0 else "detenido"))

    def _cambiar_pwm(self, paso):
        """Sube o baja la potencia un paso (teclas W / S), sin salir del rango -4 a 4, y la envia."""
        v = max(-4, min(4, self.var_pwm.get() + paso))
        self.var_pwm.set(v)
        self._mostrar_pwm()
        self._enviar_pwm()

    def _enviar_pwm(self):
        """Envia la potencia del deslizador solo si cambio respecto a la ultima enviada."""
        v = self.var_pwm.get()
        if v != self.pwm_enviado and self._enviar("pwm %d" % v):
            self.pwm_enviado = v

    def _iniciar_patron(self, nombre):
        """Envia un patron (circle, infinite, zigzag o especial) si no hay otro en curso.

        Marca el patron en curso de inmediato para dejar de pedir el LDR y no cruzar comandos.
        """
        if self.patron:
            self._log("Ya hay un patrón en curso: presiona STOP (espacio) para cancelarlo")
            return
        if self._enviar(nombre):
            self.patron = True                   # desde ya: deja de pedir el LDR para no cruzar comandos
            self.lbl_patron.config(text="Iniciando " + nombre + " ...", fg=CIAN)

    def _stop(self):
        """STOP: potencia a 0, sin direccion, y envia stop (tambien cancela un patron en curso)."""
        self.patron = False                      # la Pico responde "cancelado" (o "ok" si no habia patron)
        self.var_pwm.set(0)
        self._mostrar_pwm()
        self.pwm_enviado = 0
        self.dir_actual = None
        self._pintar_direccion()
        self._enviar("stop")

    # ================================================================ luces
    def _alternar_luz(self, clave):
        """Enciende o apaga un grupo de luces (lf, lb, ll, lr) si el control manual esta permitido."""
        if self.ldr_auto or self.dec_modo is not None:
            return
        nuevo = 1 - self.luz[clave]
        if self._enviar("%s %d" % (clave, nuevo)):
            self.luz[clave] = nuevo
        self._refrescar_luces()

    def _alternar_ldr_auto(self):
        """Activa o desactiva el modo automatico de luces por LDR (comando ldr 1 / ldr 0)."""
        nuevo = not self.ldr_auto
        if self._enviar("ldr %d" % int(nuevo)):
            self.ldr_auto = nuevo
        self._refrescar_luces()

    def _refrescar_luces(self):
        """Colores y bloqueos de la seccion Luces, y los dos dibujos del carro."""
        dec = self.dec_modo is not None
        for clave, b in self.btn_luz.items():
            self._color_boton(b, BOTON_ON if self.luz[clave] else BOTON, habilitado=not (dec or self.ldr_auto))
        self._color_boton(self.btn_ldr_auto, BOTON_ON if self.ldr_auto else BOTON, habilitado=not dec)
        if dec:
            aviso = "Los LED están en uso por el decrementador"
        elif self.ldr_auto:
            aviso = "Modo automático: la Pico decide según la luz"
        else:
            aviso = ""
        self.lbl_aviso_luces.config(text=aviso)
        if dec:
            dibujar_carro(self.can_carro_luces, 180, 200, 1.15, self.luz_dec, "mostrando el decrementador")
        elif self.ldr_auto:
            dibujar_carro(self.can_carro_luces, 180, 200, 1.15, {}, "modo automático por LDR")
        else:
            dibujar_carro(self.can_carro_luces, 180, 200, 1.15, self.luz)
        dibujar_carro(self.can_carro_dec, 160, 170, 0.95, self.luz_dec if dec else {},
                      None if dec else "decrementador apagado")

    def _dibujar_barra_ldr(self, valor):
        """Dibuja la barra con la lectura del LDR (0 a 65535) en la seccion Luces."""
        c = self.can_ldr
        c.delete("all")
        rect_redondo(c, 2, 4, 518, 30, 10, fill=CAMPO, outline=LINEA)
        if valor is not None:
            ancho = max(14, int(516 * min(valor, 65535) / 65535))
            rect_redondo(c, 2, 4, ancho, 30, 10, fill=CIAN, outline="")

    # ================================================================ decrementador
    def _alternar_dec(self):
        """Activa el modo LDR, o apaga el decrementador si ya estaba activo (LDR o manual)."""
        if self.dec_modo is None:
            if not self.con.activa:
                self._log("No hay conexión")
                return
            self.dec_modo = "ldr"
            self.ldr_auto = False                # el servidor apaga el modo ldr de luces al activarlo
            self._log("Decrementador activado (entrada = LDR)")
        else:
            self._apagar_dec()
        self._actualizar_dec()

    def _apagar_dec(self):
        """Apaga el decrementador: envia dec off (la Pico deja A B C = 111 y apaga los LED)."""
        self.dec_modo = None
        if self._enviar("dec off", log=False):
            self.ok_silenciosos += 1
        self.luz = {"lf": 0, "lb": 0, "ll": 0, "lr": 0}   # el servidor deja los LED apagados
        self._log("Decrementador apagado")

    def _actualizar_dec(self):
        """Actualiza el boton y los textos del decrementador segun su modo (apagado, LDR o manual)."""
        activo = self.dec_modo is not None
        if self.dec_modo == "ldr":
            texto, color = "Desactivar decrementador (LDR)", BOTON_ON
        elif self.dec_modo == "manual":
            texto, color = "Apagar decrementador (prueba manual)", BOTON_ON
        else:
            texto, color = "Activar decrementador (entrada = LDR)", BOTON
        self.btn_dec.config(text=texto)
        self._color_boton(self.btn_dec, color)
        if not activo:
            self.luz_dec = {"lf": 0, "lb": 0, "ll": 0, "lr": 0}
            self.lbl_dec.config(text="Apagado (A B C = 111, salida 000)", fg=TENUE)
            self._dibujar_bits(None, None)
        self._refrescar_luces()

    def _probar_manual(self):
        """Programa de pruebas manuales: envia la entrada escrita (0 a 7)."""
        if self.dec_modo == "ldr":
            self._log("Desactiva el decrementador por LDR para probar a mano")
            return
        texto = self.var_manual.get().strip()
        if texto not in [str(i) for i in range(8)]:
            self._log("Escribe un número de 0 a 7")
            return
        if not self.con.activa:
            self._log("No hay conexión")
            return
        self.ldr_auto = False
        self.dec_modo = "manual"
        self._actualizar_dec()
        self._enviar("dec " + texto)
        self.ent_manual.select_range(0, "end")   # para escribir el siguiente caso directo

    def _nivel(self, valor):
        """Divide el rango del sensor en 8 intervalos (0 a 7)."""
        lo, hi = self._rango()
        v = min(max(valor, lo), hi)
        return min(7, (v - lo) * 8 // (hi - lo + 1))

    def _rango(self):
        """Lee los campos LDR min y max; si no son validos usa la calibracion por defecto."""
        try:
            lo, hi = int(self.var_min.get()), int(self.var_max.get())
        except ValueError:
            lo, hi = LDR_MIN_DEF, LDR_MAX_DEF
        if hi <= lo:
            hi = lo + 1
        return lo, hi

    def _dibujar_intervalos(self, valor):
        """Barra con los 8 intervalos del LDR; marca el intervalo actual."""
        c = self.can_int
        c.delete("all")
        lo, hi = self._rango()
        actual = self._nivel(valor) if valor is not None else None
        w = 556 / 8
        for i in range(8):
            x1 = 2 + i * w
            on = i == actual
            c.create_rectangle(x1, 4, x1 + w - 3, 34, fill=CIAN if on else CAMPO, outline=LINEA)
            c.create_text(x1 + w / 2, 19, text=str(i), fill=FONDO if on else TENUE, font=("Segoe UI", 11, "bold"))
        c.create_text(2, 48, text=str(lo), anchor="w", fill=TENUE, font=self.f_peq)
        c.create_text(556, 48, text=str(hi), anchor="e", fill=TENUE, font=self.f_peq)
        if valor is not None:
            c.create_text(280, 48, text="lectura actual: %d" % valor, fill=TENUE, font=self.f_peq)

    def _dibujar_bits(self, abc, xyz):
        """Bolitas con los bits de entrada (A B C) y de salida (x y z)."""
        c = self.can_bits
        c.delete("all")
        grupos = [("Entrada", "ABC", abc, 40), ("Salida", "xyz", xyz, 330)]
        for titulo, letras, bits, x0 in grupos:
            c.create_text(x0, 12, text=titulo, anchor="w", fill=TEXTO, font=("Segoe UI", 11, "bold"))
            for i, letra in enumerate(letras):
                x = x0 + 22 + i * 64
                bit = bits[i] if bits else None
                color = (VERDE if bit == "1" else APAGADA) if bit else CAMPO
                c.create_oval(x - 20, 34, x + 20, 74, fill=color, outline=LINEA, width=2)
                c.create_text(x, 54, text=bit or "-", fill=FONDO if bit == "1" else TEXTO,
                              font=("Segoe UI", 14, "bold"))
                c.create_text(x, 92, text=letra, fill=TENUE, font=("Segoe UI", 11, "bold"))
        c.create_text(280, 54, text="→", fill=LAVANDA, font=("Segoe UI", 26, "bold"))

    def _respuesta_dec(self, linea):
        """Muestra lo que leyó la Pico en x, y, z y lo compara con la tabla."""
        if self.dec_modo is None:                # respuesta atrasada que llegó después de apagarlo
            return
        _, n, abc, xyz = linea.split()
        n, sal = int(n), int(xyz, 2)
        esperado = TABLA_DEC[n]
        correcto = sal == esperado
        origen = "Intervalo LDR" if self.dec_modo == "ldr" else "Entrada"
        estado = "correcto" if correcto else "NO coincide (esperado %s)" % format(esperado, "03b")
        self.lbl_dec.config(text="%s %d → salida %d   ·   %s" % (origen, n, sal, estado),
                            fg=VERDE if correcto else ROJO)
        self._dibujar_bits(abc, xyz)
        x, y, z = (int(b) for b in xyz)
        self.luz_dec = {"lf": x, "ll": y, "lr": y, "lb": z}
        self._refrescar_luces()
        if self.dec_modo != "ldr":               # en modo LDR llega cada 500 ms: no llenar el registro
            self._log("← entrada %d (%s) → salida %s (%d), %s" % (n, abc, xyz, sal, estado))

    # ================================================================ ciclo y cola
    def _ciclo(self):
        """Cada 500 ms pide la lectura del LDR (si no hay un patron en curso)."""
        if self.con.activa and not self.patron:
            self._enviar("ldrval", log=False)
        self.after(PERIODO_MS, self._ciclo)

    def _nuevo_ldr(self, valor):
        """Llego una lectura del LDR: la muestra y, en modo LDR, envia el intervalo al decrementador."""
        self.lbl_ldr.config(text="Lectura LDR: %d" % valor)
        self._dibujar_barra_ldr(valor)
        self._dibujar_intervalos(valor)
        if self.dec_modo == "ldr":
            self._enviar("dec %d" % self._nivel(valor), log=False)   # la Pico responde "dec n ABC xyz"

    def _procesar_cola(self):
        """Cada 100 ms revisa la cola: respuestas de la Pico, fin de la busqueda o conexion cerrada.

        Asi la ventana nunca se congela esperando datos de la red.
        """
        try:
            while True:
                tipo, dato = self.cola.get_nowait()
                if tipo == "rx":
                    self._recibido(dato)
                elif tipo == "busqueda":
                    self._fin_busqueda(dato)
                elif tipo == "cerrada" and self.con.sock is dato:
                    self.con.cerrar()
                    self._al_desconectar()
                    self._estado_conexion()
                    self._log("La Pico cerró la conexión")
        except queue.Empty:
            pass
        self.after(100, self._procesar_cola)

    def _recibido(self, linea):
        """Decide que hacer con cada linea que responde la Pico.

        - Un numero: lectura del LDR.
        - "dec n ABC xyz": resultado del decrementador.
        - "ok" esperado: no se muestra.
        - Lo demas se anota en el registro; tambien detecta inicio y fin de los patrones.
        """
        if linea.isdigit():                      # unica respuesta numerica: lectura del LDR
            self._nuevo_ldr(int(linea))
            return
        if linea.startswith("dec ") and len(linea.split()) == 4:
            self._respuesta_dec(linea)
            return
        if linea == "ok" and self.ok_silenciosos > 0:
            self.ok_silenciosos -= 1
            return
        self._log("← " + linea)
        if linea.startswith("ok iniciado"):
            self.patron = True
            self.lbl_patron.config(text="Patrón en curso: " + linea.split()[-1], fg=CIAN)
        elif linea.startswith(("fin", "cancelado")):
            self.patron = False
            self.lbl_patron.config(text="Sin patrón en curso  ·  STOP lo cancela", fg=TENUE)

    def _log(self, texto):
        """Agrega una linea al registro (guarda como maximo unas 300 lineas)."""
        self.txt.config(state="normal")
        self.txt.insert("end", texto + "\n")
        if int(self.txt.index("end-1c").split(".")[0]) > 300:
            self.txt.delete("1.0", "50.0")
        self.txt.see("end")
        self.txt.config(state="disabled")

    def _cerrar(self):
        """Al cerrar la ventana: envia stop, cierra la conexion y termina el programa."""
        if self.con.activa:
            self.con.enviar("stop")
            self.con.cerrar()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
