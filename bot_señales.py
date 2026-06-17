import time
import requests
import pandas as pd
import yfinance as yf
import os

from datetime import datetime
from zoneinfo import ZoneInfo

# =========================
# VARIABLES SEGURAS (RENDER)
# =========================
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# =========================
# CONFIGURACIÓN
# =========================
IMPULSO_MINIMO = 30
ZONA_BUFFER = 3
RR = 1.5

CONTRATOS = 3
VALOR_PUNTO = 2

# HORARIO NUEVA YORK
START_HOUR = 8
START_MIN = 0

END_HOUR = 15
END_MIN = 0

NY_TZ = ZoneInfo("America/New_York")

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
        "text": mensaje,
        "parse_mode": "HTML"
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
            print("❌ Error Telegram")

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

        df = df.reset_index()

        if len(df.columns) >= 6:
            df.columns = [
                "Time",
                "Close",
                "High",
                "Low",
                "Open",
                "Volume"
            ]

        df["Time"] = pd.to_datetime(df["Time"])

        print(f"✅ Datos descargados: {len(df)} velas")

        return df.dropna()

    except Exception as e:

        print("❌ Error datos:", e)
        return None

# =========================
# DETECCIÓN S&D
# =========================
def detectar_zonas(df):

    zonas = []

    hoy = datetime.now(NY_TZ).date()

    for i in range(2, len(df) - 1):

        base = df.iloc[i]
        impulso = df.iloc[i + 1]

        try:

            if base["Time"].date() != hoy:
                continue

            cuerpo = abs(
                impulso["Close"] -
                impulso["Open"]
            )

            if cuerpo < IMPULSO_MINIMO:
                continue

            tipo = (
                "DEMANDA"
                if impulso["Close"] > impulso["Open"]
                else "OFERTA"
            )

            zonas.append({
                "Tipo": tipo,
                "High": round(base["High"], 2),
                "Low": round(base["Low"], 2),
                "Impulso": round(cuerpo, 2)
            })

        except Exception:
            continue

    return zonas

# =========================
# TOQUE DE ZONA
# =========================
def tocar_zona(df, zona):

    last = df.iloc[-1]

    if zona["Tipo"] == "DEMANDA":

        return (
            zona["Low"]
            <= last["Low"]
            <= zona["High"]
        )

    else:

        return (
            zona["Low"]
            <= last["High"]
            <= zona["High"]
        )

# =========================
# MENSAJE TELEGRAM
# =========================
def mensaje(zona, precio):

    if zona["Tipo"] == "DEMANDA":

        entry = zona["High"]
        sl = zona["Low"] - ZONA_BUFFER

        emoji = "🟢"
        direc = "LONG"

    else:

        entry = zona["Low"]
        sl = zona["High"] + ZONA_BUFFER

        emoji = "🔴"
        direc = "SHORT"

    riesgo = abs(entry - sl)

    tp = (
        entry + (riesgo * RR)
        if zona["Tipo"] == "DEMANDA"
        else entry - (riesgo * RR)
    )

    riesgo_usd = round(
        riesgo * CONTRATOS * VALOR_PUNTO,
        2
    )

    ganancia_usd = round(
        riesgo * RR * CONTRATOS * VALOR_PUNTO,
        2
    )

    return f"""
{emoji} <b>NQ SETUP DETECTADO</b>

📊 Dirección: {direc}

🎯 Entry: {round(entry,2)}
🛑 Stop: {round(sl,2)}
🎯 TP: {round(tp,2)}

💰 Riesgo: ${riesgo_usd}
💵 Potencial: ${ganancia_usd}

📍 Precio actual: {round(precio,2)}

⚡ Impulso: {zona['Impulso']}
🕐 Hora NY: {datetime.now(NY_TZ).strftime('%H:%M')}
"""

# =========================
# HORARIO
# =========================
def horario_ok():

    now = datetime.now(NY_TZ)

    return (
        (
            now.hour > START_HOUR
            or
            (
                now.hour == START_HOUR
                and now.minute >= START_MIN
            )
        )
        and
        (
            now.hour < END_HOUR
            or
            (
                now.hour == END_HOUR
                and now.minute <= END_MIN
            )
        )
    )

# =========================
# BOT PRINCIPAL
# =========================
def run():

    print("🚀 BOT INICIADO EN RENDER")

    enviar_mensaje(
        "🚀 BOT NQ ARRANCADO EN RENDER"
    )

    alertas = set()

    while True:

        try:

            if not horario_ok():

                print(
                    f"😴 Fuera de horario NY "
                    f"{datetime.now(NY_TZ).strftime('%H:%M')}"
                )

                time.sleep(60)
                continue

            print(
                f"🔍 Revisando mercado "
                f"{datetime.now(NY_TZ).strftime('%H:%M:%S')}"
            )

            df = obtener_datos()

            if df is None:

                time.sleep(30)
                continue

            precio = float(
                df.iloc[-1]["Close"]
            )

            zonas = detectar_zonas(df)

            print(
                f"📊 Zonas detectadas: {len(zonas)}"
            )

            for z in zonas:

                z_id = (
                    f"{z['Tipo']}_"
                    f"{z['High']}_"
                    f"{z['Low']}"
                )

                if z_id in alertas:
                    continue

                if tocar_zona(df, z):

                    enviar_mensaje(
                        mensaje(z, precio)
                    )

                    alertas.add(z_id)

                    print(
                        f"🎯 Señal enviada: {z_id}"
                    )

            time.sleep(60)

        except Exception as e:

            print("❌ Error:", e)

            time.sleep(30)

if __name__ == "__main__":
    run()
