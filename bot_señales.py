import time
import requests
import pandas as pd
import yfinance as yf
import os
from datetime import datetime

# =========================
# VARIABLES SEGURAS (RENDER)
# =========================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# =========================
# CONFIGURACIÓN
# =========================
IMPULSO_MINIMO = 30
ZONA_BUFFER = 3
RR = 1.5
CONTRATOS = 3
VALOR_PUNTO = 2

START_HOUR = 9
START_MIN = 30
END_HOUR = 11
END_MIN = 30


# =========================
# TELEGRAM
# =========================
def enviar_mensaje(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }

    try:
        requests.post(url, data=data, timeout=10)
        print("✅ Mensaje enviado")
    except Exception as e:
        print("❌ Error Telegram:", e)


# =========================
# DATOS NQ
# =========================
def obtener_datos():
    try:
        df = yf.download("NQ=F", period="5d", interval="5m", progress=False)

        if df.empty:
            return None

        df = df.reset_index()

        df.rename(columns={
            "Datetime": "Time",
            "Date": "Time"
        }, inplace=True)

        df["Time"] = pd.to_datetime(df["Time"])

        return df.dropna()

    except Exception as e:
        print("❌ Error datos:", e)
        return None


# =========================
# ZONAS S&D
# =========================
def detectar_zonas(df):
    zonas = []
    hoy = datetime.now().date()

    for i in range(2, len(df)-1):
        base = df.iloc[i]
        impulso = df.iloc[i+1]

        if base["Time"].date() != hoy:
            continue

        if not (START_HOUR <= base["Time"].hour <= END_HOUR):
            continue

        cuerpo = abs(impulso["Close"] - impulso["Open"])

        if cuerpo < IMPULSO_MINIMO:
            continue

        tipo = "DEMANDA" if impulso["Close"] > impulso["Open"] else "OFERTA"

        zonas.append({
            "Tipo": tipo,
            "High": round(base["High"],2),
            "Low": round(base["Low"],2),
            "Impulso": round(cuerpo,2)
        })

    return zonas


# =========================
# TOQUE ZONA
# =========================
def tocar_zona(df, zona):
    last = df.iloc[-1]

    if zona["Tipo"] == "DEMANDA":
        return zona["Low"] <= last["Low"] <= zona["High"]
    else:
        return zona["Low"] <= last["High"] <= zona["High"]


# =========================
# MENSAJE
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
    tp = entry + (riesgo * RR) if zona["Tipo"] == "DEMANDA" else entry - (riesgo * RR)

    return f"""
{emoji} <b>NQ SETUP DETECTADO</b>

📊 Dirección: {direc}
🎯 Entry: {round(entry,2)}
🛑 SL: {round(sl,2)}
🎯 TP: {round(tp,2)}

📍 Precio: {round(precio,2)}
⚡ Impulso: {zona['Impulso']}
"""


# =========================
# HORARIO
# =========================
def horario_ok():
    now = datetime.now()
    return (
        (now.hour > START_HOUR or (now.hour == START_HOUR and now.minute >= START_MIN))
        and
        (now.hour < END_HOUR or (now.hour == END_HOUR and now.minute <= END_MIN))
    )


# =========================
# BOT PRINCIPAL
# =========================
def run():
    print("🚀 BOT INICIADO EN RENDER")
    enviar_mensaje("🚀 Bot NQ iniciado en la nube")

    alertas = set()

    while True:
        try:

            if not horario_ok():
                print("😴 Fuera de horario")
                time.sleep(60)
                continue

            df = obtener_datos()
            if df is None:
                time.sleep(30)
                continue

            zonas = detectar_zonas(df)
            precio = df.iloc[-1]["Close"]

            for z in zonas:
                z_id = f"{z['Tipo']}_{z['High']}_{z['Low']}"

                if z_id in alertas:
                    continue

                if tocar_zona(df, z):
                    enviar_mensaje(mensaje(z, precio))
                    alertas.add(z_id)

                    print("🎯 Señal enviada")

            time.sleep(60)

        except Exception as e:
            print("❌ Error:", e)
            time.sleep(10)


if __name__ == "__main__":
    run()
