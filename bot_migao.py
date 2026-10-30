import tkinter as tk
from tkinter import ttk
import time

import cv2
import mss
import numpy as np
import pydirectinput


# ============================================================
# CONFIGURACION: mantenemos los valores del detector validado
# ============================================================

REGION = {
    "left": 10,
    "top": 5,
    "width": 1918,
    "height": 1105
}

VERDE_MIN = np.array([35, 100, 100])
VERDE_MAX = np.array([95, 255, 255])
AREA_MINIMA = 1500

INTERVALO_MS = 20

# Acciones del bot (segundos)
INTERVALO_ATAQUE = 0.45
INTERVALO_FLY_WING = 1.50
ESPERA_TRAS_F1 = 0.06
PERDIDA_OBJETIVO = 0.30

NOMBRE_VENTANA = "RO Bot - Detector Mi Gao"


class MiGaoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RO Bot - Mi Gao")
        self.root.resizable(False, False)

        self.activo = False
        self.cerrando = False
        self.sct = mss.MSS()

        self.ultimo_tiempo = time.perf_counter()
        self.fps = 0.0
        self.ultimo_ataque = 0.0
        self.ultima_fly_wing = 0.0
        self.sin_objetivo_desde = None
        pydirectinput.PAUSE = 0

        contenedor = ttk.Frame(root, padding=16)
        contenedor.grid(row=0, column=0, sticky="nsew")

        ttk.Label(
            contenedor,
            text="MI GAO FARMER",
            font=("Segoe UI", 16, "bold")
        ).grid(row=0, column=0, columnspan=2, pady=(0, 12))

        self.estado_var = tk.StringVar(value="DETENIDO")
        self.coords_var = tk.StringVar(value="Objetivo: —")
        self.fps_var = tk.StringVar(value="Detector: — FPS")

        ttk.Label(contenedor, text="Estado:").grid(
            row=1, column=0, sticky="w"
        )
        self.estado_label = ttk.Label(
            contenedor,
            textvariable=self.estado_var,
            font=("Segoe UI", 11, "bold")
        )
        self.estado_label.grid(row=1, column=1, sticky="w")

        ttk.Label(
            contenedor, textvariable=self.coords_var
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

        ttk.Label(
            contenedor, textvariable=self.fps_var
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 12))

        botones = ttk.Frame(contenedor)
        botones.grid(row=4, column=0, columnspan=2, sticky="ew")

        self.iniciar_btn = ttk.Button(
            botones, text="Iniciar", command=self.iniciar
        )
        self.iniciar_btn.grid(row=0, column=0, padx=(0, 6))

        self.pausar_btn = ttk.Button(
            botones, text="Pausar", command=self.pausar, state="disabled"
        )
        self.pausar_btn.grid(row=0, column=1, padx=6)

        self.detener_btn = ttk.Button(
            botones, text="Detener", command=self.detener, state="disabled"
        )
        self.detener_btn.grid(row=0, column=2, padx=(6, 0))

        ttk.Label(
            contenedor,
            text="Automatico: F2 para buscar; F1 + clic para atacar.",
            foreground="#666666",
            wraplength=340
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 0))

        self.root.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.root.after(INTERVALO_MS, self.actualizar)

    def iniciar(self):
        if self.cerrando:
            return
        self.activo = True
        ahora = time.perf_counter()
        self.ultimo_ataque = ahora
        self.ultima_fly_wing = 0.0
        self.sin_objetivo_desde = ahora
        self.estado_var.set("BUSCANDO")
        self.iniciar_btn.configure(state="disabled")
        self.pausar_btn.configure(state="normal", text="Pausar")
        self.detener_btn.configure(state="normal")

    def pausar(self):
        if not self.activo:
            return
        self.activo = False
        self.sin_objetivo_desde = None
        self.estado_var.set("PAUSADO")
        self.coords_var.set("Objetivo: —")
        self.iniciar_btn.configure(state="normal")
        self.pausar_btn.configure(state="disabled", text="Pausar")

    def detener(self):
        self.activo = False
        self.sin_objetivo_desde = None
        self.estado_var.set("DETENIDO")
        self.coords_var.set("Objetivo: —")
        self.iniciar_btn.configure(state="normal")
        self.pausar_btn.configure(state="disabled", text="Pausar")
        self.detener_btn.configure(state="disabled")
        cv2.destroyWindow(NOMBRE_VENTANA)

    def detectar(self):
        captura = np.array(self.sct.grab(REGION))
        pantalla = cv2.cvtColor(captura, cv2.COLOR_BGRA2BGR)

        hsv = cv2.cvtColor(pantalla, cv2.COLOR_BGR2HSV)
        mascara = cv2.inRange(hsv, VERDE_MIN, VERDE_MAX)
        mascara = cv2.medianBlur(mascara, 5)

        contornos, _ = cv2.findContours(
            mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        vista = pantalla.copy()
        candidatos = []

        for contorno in contornos:
            area = cv2.contourArea(contorno)
            if area < AREA_MINIMA:
                continue

            x, y, ancho, alto = cv2.boundingRect(contorno)
            candidatos.append((area, x, y, ancho, alto))

        objetivo = None
        if candidatos:
            # Priorizamos el Mi Gao mas cercano al centro de la pantalla,
            # que usamos como referencia aproximada de la posicion del personaje.
            centro_pantalla_x = REGION["width"] // 2
            centro_pantalla_y = REGION["height"] // 2

            def distancia_al_personaje(candidato):
                _, x, y, ancho, alto = candidato
                cx = x + ancho // 2
                cy = y + alto // 2
                return (cx - centro_pantalla_x) ** 2 + (cy - centro_pantalla_y) ** 2

            area, x, y, ancho, alto = min(
                candidatos, key=distancia_al_personaje
            )
            centro_x = x + ancho // 2
            centro_y = y + alto // 2
            objetivo = (centro_x, centro_y)

            # Marca el centro de referencia y resalta el objetivo elegido.
            cv2.drawMarker(
                vista,
                (centro_pantalla_x, centro_pantalla_y),
                (0, 255, 255),
                cv2.MARKER_CROSS,
                18,
                1
            )
            cv2.rectangle(
                vista, (x, y), (x + ancho, y + alto), (0, 0, 255), 2
            )
            cv2.circle(vista, objetivo, 5, (255, 0, 0), -1)
            cv2.putText(
                vista,
                f"Mi Gao prioritario ({centro_x}, {centro_y})",
                (x, max(20, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2
            )

        return vista, objetivo

    def gestionar_acciones(self, objetivo, ahora):
        """Ataca al objetivo elegido o usa Fly Wing cuando no hay ninguno."""
        if objetivo is not None:
            self.sin_objetivo_desde = None

            if ahora - self.ultimo_ataque >= INTERVALO_ATAQUE:
                cx, cy = objetivo
                abs_x = REGION["left"] + cx
                abs_y = REGION["top"] + cy

                # Orden confirmado: primero F1 y despues clic izquierdo.
                pydirectinput.press("f1")
                time.sleep(ESPERA_TRAS_F1)
                pydirectinput.click(abs_x, abs_y)
                self.ultimo_ataque = time.perf_counter()
            return

        # Toleramos pequeños fallos puntuales del detector.
        if self.sin_objetivo_desde is None:
            self.sin_objetivo_desde = ahora

        if ahora - self.sin_objetivo_desde >= PERDIDA_OBJETIVO:
            if ahora - self.ultima_fly_wing >= INTERVALO_FLY_WING:
                pydirectinput.press("f2")
                self.ultima_fly_wing = time.perf_counter()

    def actualizar(self):
        if self.cerrando:
            return

        if self.activo:
            try:
                vista, objetivo = self.detectar()

                ahora = time.perf_counter()
                delta = ahora - self.ultimo_tiempo
                self.ultimo_tiempo = ahora
                if delta > 0:
                    fps_actual = 1.0 / delta
                    self.fps = fps_actual if self.fps == 0 else (
                        self.fps * 0.8 + fps_actual * 0.2
                    )

                self.gestionar_acciones(objetivo, ahora)

                if objetivo is None:
                    self.estado_var.set("BUSCANDO")
                    self.coords_var.set("Objetivo: no detectado")
                else:
                    cx, cy = objetivo
                    abs_x = REGION["left"] + cx
                    abs_y = REGION["top"] + cy
                    self.estado_var.set("OBJETIVO DETECTADO")
                    self.coords_var.set(
                        f"Centro ventana: ({cx}, {cy}) | Pantalla: ({abs_x}, {abs_y})"
                    )

                self.fps_var.set(f"Detector: {self.fps:.1f} FPS")
                cv2.imshow(NOMBRE_VENTANA, vista)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    self.detener()

            except Exception as error:
                self.activo = False
                self.sin_objetivo_desde = None
                self.estado_var.set("ERROR")
                self.coords_var.set(str(error))
                self.iniciar_btn.configure(state="normal")
                self.pausar_btn.configure(state="disabled")
                self.detener_btn.configure(state="disabled")

        self.root.after(INTERVALO_MS, self.actualizar)

    def cerrar(self):
        self.cerrando = True
        self.activo = False
        try:
            self.sct.close()
        finally:
            cv2.destroyAllWindows()
            self.root.destroy()


if __name__ == "__main__":
    ventana = tk.Tk()
    app = MiGaoApp(ventana)
    ventana.mainloop()
