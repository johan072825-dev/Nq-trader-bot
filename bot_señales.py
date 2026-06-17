import time
import requests
import pandas as pd
import yfinance as yf
import os
from datetime import datetime

# =========================
# VARIABLES RENDER
# =========================
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# =========================
# CONFIGURACIÓN
# =========================
IMPULSO_MINIMO = 30
ZONA_BUFFER = 3
RR = 1.5
START_HOUR = 9
START_MIN = 30
END_HOUR = 11
END_MIN = 30

# =========================
# TELEGRAM
# =========================
def enviar_mensaje(mensaje):

    if not TOKEN:
        print("❌ TOKEN no encontrado")
        return

    if not CHAT_ID:
        print("❌ CHAT_ID no encontrado")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": mensaje
    }

    try:

        response = requests.post(
            url,
            data=data,
            timeout=15
        )

        print("STATUS:", response.status_code)
        print("RESPUESTA:", response.text)

        if response.status_code == 200:
            print("✅ Mensaje enviado")
        else:
            print("❌ Telegram respondió error")

    except Exception as e:
        print("❌ Error Telegram:", e)

# =========================
# DATOS NQ
# =========================
def obtener_datos():

    try:

        df = yf.download(
            "NQ=F",
            period="5d",
            interval="5m",
            progress=False
        )

        if df.empty:
            print("⚠️ No llegaron datos")
            return None

        print(f"✅ Datos descargados: {len(df)} velas")

        return df

    except Exception as e:

        print("❌ Error descargando datos:", e)
        return None

# =========================
# HORARIO
# =========================
def horario_ok():

    ahora = datetime.now()

    return (
        (
            ahora.hour > START_HOUR
            or
            (
                ahora.hour == START_HOUR
                and ahora.minute >= START_MIN
            )
        )
        and
        (
            ahora.hour < END_HOUR
            or
            (
                ahora.hour == END_HOUR
                and ahora.minute <= END_MIN
            )
        )
    )

# =========================
# BOT
# =========================
def run():

    print("🚀 BOT INICIADO EN RENDER")

    enviar_mensaje("🚀 BOT ARRANCADO EN RENDER")

    while True:

        try:

            if not horario_ok():

                print("😴 Fuera de horario")

                time.sleep(60)
                continue

            print(
                f"🔍 Revisando mercado {datetime.now().strftime('%H:%M:%S')}"
            )

            df = obtener_datos()

            if df is None:

                time.sleep(60)
                continue

            precio = float(df["Close"].iloc[-1])

            print(f"📈 Precio actual NQ: {precio}")

            time.sleep(60)

        except KeyboardInterrupt:

            print("⛔ Bot detenido")
            break

        except Exception as e:

            print("❌ ERROR GENERAL:", e)

            time.sleep(30)

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    run()
