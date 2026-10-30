
import cv2
import mss
import numpy as np

# Ventana de Ragnarok
REGION = {
    "left": 10,
    "top": 5,
    "width": 1918,
    "height": 1105
}

# Rango de verde chillón en HSV
VERDE_MIN = np.array([35, 100, 100])
VERDE_MAX = np.array([95, 255, 255])

# Ignorar áreas pequeñas, como la barra de vida
AREA_MINIMA = 1500

with mss.MSS() as sct:
    print("Detector iniciado. Pulsa Q para salir.")

    while True:
        captura = np.array(sct.grab(REGION))
        pantalla = cv2.cvtColor(captura, cv2.COLOR_BGRA2BGR)

        hsv = cv2.cvtColor(pantalla, cv2.COLOR_BGR2HSV)
        mascara = cv2.inRange(hsv, VERDE_MIN, VERDE_MAX)

        # Eliminar pequeños puntos aislados
        mascara = cv2.medianBlur(mascara, 5)

        contornos, _ = cv2.findContours(
            mascara,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        vista = pantalla.copy()

        for contorno in contornos:
            area = cv2.contourArea(contorno)

            # Ignorar objetos verdes pequeños
            if area < AREA_MINIMA:
                continue

            x, y, ancho, alto = cv2.boundingRect(contorno)
            centro_x = x + ancho // 2
            centro_y = y + alto // 2

            # Dibujar el rectángulo detectado
            cv2.rectangle(
                vista,
                (x, y),
                (x + ancho, y + alto),
                (0, 0, 255),
                2
            )

            # Marcar el centro
            cv2.circle(
                vista,
                (centro_x, centro_y),
                5,
                (255, 0, 0),
                -1
            )

            cv2.putText(
                vista,
                f"Mi Gao ({centro_x}, {centro_y})",
                (x, max(20, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2
            )

        cv2.imshow("Detector verde - Mi Gao", vista)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

cv2.destroyAllWindows()
