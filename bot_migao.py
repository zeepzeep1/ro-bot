import time

import cv2
import mss
import numpy as np
import pydirectinput


# Zona de captura y color verde de Mi Gao (los valores que ya validamos)
REGION = {"left": 10, "top": 5, "width": 1918, "height": 1105}
VERDE_MIN = np.array([35, 100, 100], dtype=np.uint8)
VERDE_MAX = np.array([95, 255, 255], dtype=np.uint8)
AREA_MINIMA = 1500

INTERVALO_ATAQUE = 0.45       # F1 + clic cada 450 ms
INTERVALO_FLY_WING = 1.50     # F2 cada 1,5 s si no hay objetivo
TOLERANCIA_PERDIDA = 0.30     # evita usar F2 por un fallo puntual de deteccion

pydirectinput.PAUSE = 0


def buscar_mi_gao(sct):
    captura = np.array(sct.grab(REGION))
    imagen = cv2.cvtColor(captura, cv2.COLOR_BGRA2BGR)
    hsv = cv2.cvtColor(imagen, cv2.COLOR_BGR2HSV)
    mascara = cv2.inRange(hsv, VERDE_MIN, VERDE_MAX)
    mascara = cv2.medianBlur(mascara, 5)

    contornos, _ = cv2.findContours(
        mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    objetivos = []
    for contorno in contornos:
        if cv2.contourArea(contorno) < AREA_MINIMA:
            continue

        x, y, ancho, alto = cv2.boundingRect(contorno)
        centro = (x + ancho // 2, y + alto // 2)
        objetivos.append(centro)

    if not objetivos:
        return None

    # Si hay varios, elige el verde mas cercano al centro de la pantalla.
    centro_pantalla = (REGION["width"] // 2, REGION["height"] // 2)
    return min(
        objetivos,
        key=lambda p: (p[0] - centro_pantalla[0]) ** 2
        + (p[1] - centro_pantalla[1]) ** 2,
    )


def main():
    ultimo_ataque = 0.0
    ultima_fly_wing = 0.0
    sin_objetivo_desde = None

    print("RO Mi Gao Bot iniciado.")
    print("Deja Ragnarok en primer plano. Pulsa Ctrl+C para salir.")

    with mss.MSS() as sct:
        while True:
            ahora = time.perf_counter()
            objetivo = buscar_mi_gao(sct)

            if objetivo is not None:
                sin_objetivo_desde = None

                if ahora - ultimo_ataque >= INTERVALO_ATAQUE:
                    x = REGION["left"] + objetivo[0]
                    y = REGION["top"] + objetivo[1]

                    pydirectinput.press("f1")
                    pydirectinput.click(x, y)
                    ultimo_ataque = time.perf_counter()
                    print(f"ATACANDO: clic en ({x}, {y})")

            else:
                if sin_objetivo_desde is None:
                    sin_objetivo_desde = ahora

                if (
                    ahora - sin_objetivo_desde >= TOLERANCIA_PERDIDA
                    and ahora - ultima_fly_wing >= INTERVALO_FLY_WING
                ):
                    pydirectinput.press("f2")
                    ultima_fly_wing = time.perf_counter()
                    print("SIN MI GAO: F2 (Fly Wing)")

            time.sleep(0.01)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBot detenido.")
