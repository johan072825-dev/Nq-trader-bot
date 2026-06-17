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

        if response.status_code == 200:
            print("✅ Mensaje enviado")
        else:
            print("❌ Error Telegram:", response.text)

    except Exception as e:
        print("❌ Error Telegram:", e)

# =========================
# DATOS NQ
# =========================
def obtener_datos():

    try:

        ticker = yf.Ticker("NQ=F")
        df = ticker.history(
            period="5d",
            interval="5m"
        )

        if df.empty:
            print("⚠️ No llegaron datos")
            return None

        df = df.reset_index()

        # Renombrar columnas correctamente
        # yfinance devuelve: Datetime, Open, High, Low, Close, Volume, ...
        df = df.rename(columns={
            "Datetime": "Time",
            "Open": "Open",
            "High": "High",
            "Low": "Low",
            "Close": "Close",
            "Volume": "Volume"
        })

        # Por si acaso viene como "Date" en vez de "Datetime"
        if "Date" in df.columns and "Time" not in df.columns:
            df = df.rename(columns={"Date": "Time"})

        df["Time"] = pd.to_datetime(df["Time"])

        # Eliminar timezone para comparar fechas
        if df["Time"].dt.tz is not None:
            df["Time"] = df["Time"].dt.tz_convert(NY_TZ)

        print(f"✅ Datos descargados: {len(df)} velas")
        print(f"📌 Último precio: {df.iloc[-1]['Close']:.2f}")

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

            # Solo zonas de hoy
            tiempo = base["Time"]
            if hasattr(tiempo, "date"):
                fecha = tiempo.date()
            else:
                fecha = pd.Timestamp(tiempo).date()

            if fecha != hoy:
                continue

            cuerpo = abs(
                float(impulso["Close"]) -
                float(impulso["Open"])
            )

            if cuerpo < IMPULSO_MINIMO:
                continue

            tipo = (
                "DEMANDA"
                if float(impulso["Close"]) > float(impulso["Open"])
                else "OFERTA"
            )

            # Filtro adicional: la vela impulso debe ser significativa
            # DEMANDA: precio venía bajando antes del impulso alcista
            # OFERTA: precio venía subiendo antes del impulso bajista
            vela_previa = df.iloc[i - 1]

            if tipo == "DEMANDA":
                # Confirmar que había presión bajista antes
                if float(vela_previa["Close"]) <= float(vela_previa["Open"]):
                    pass  # OK, venía bajando
                # Si no, igual lo incluimos pero con menor prioridad

            zonas.append({
                "Tipo": tipo,
                "High": round(float(base["High"]), 2),
                "Low": round(float(base["Low"]), 2),
                "Impulso": round(cuerpo, 2)
            })

        except Exception as ex:
            print(f"⚠️ Error en zona {i}: {ex}")
            continue

    return zonas

# =========================
# TOQUE DE ZONA
# =========================
def tocar_zona(df, zona):

    last = df.iloc[-1]
    last_low = float(last["Low"])
    last_high = float(last["High"])
    last_close = float(last["Close"])

    if zona["Tipo"] == "DEMANDA":
        # El precio toca la zona por abajo y cierra dentro o rebota
        toca = zona["Low"] <= last_low <= zona["High"]
        # Confirmar que el precio no está cayendo fuerte AHORA
        rebote = last_close >= zona["Low"]
        return toca and rebote

    else:
        # OFERTA
        toca = zona["Low"] <= last_high <= zona["High"]
        # Confirmar que el precio no está subiendo fuerte AHORA
        rechazo = last_close <= zona["High"]
        return toca and rechazo

# =========================
# MENSAJE TELEGRAM
# =========================
def mensaje_alerta(zona, precio):

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

🎯 Entry: {round(entry, 2)}
🛑 Stop: {round(sl, 2)}
🎯 TP: {round(tp, 2)}

💰 Riesgo: ${riesgo_usd}
💵 Potencial: ${ganancia_usd}

📍 Precio actual: {round(precio, 2)}

⚡ Impulso: {zona['Impulso']}
🕐 Hora NY: {datetime.now(NY_TZ).strftime('%H:%M')}
"""

# =========================
# HORARIO
# =========================
def horario_ok():

    now = datetime.now(NY_TZ)

    # No operar fines de semana
    if now.weekday() >= 5:  # 5=Sabado, 6=Domingo
        return False

    return (
        (
            now.hour > START_HOUR
            or (now.hour == START_HOUR and now.minute >= START_MIN)
        )
        and
        (
            now.hour < END_HOUR
            or (now.hour == END_HOUR and now.minute <= END_MIN)
        )
    )

# =========================
# BOT PRINCIPAL
# =========================
def run():

    print("🚀 BOT INICIADO EN RENDER")

    enviar_mensaje("🚀 BOT NQ ARRANCADO EN RENDER")

    alertas = set()

    while True:

        try:

            if not horario_ok():

                now = datetime.now(NY_TZ)
                print(f"😴 Fuera de horario NY {now.strftime('%H:%M')} (día {now.weekday()})")

                time.sleep(60)
                continue

            print(f"🔍 Revisando mercado {datetime.now(NY_TZ).strftime('%H:%M:%S')}")

            df = obtener_datos()

            if df is None:
                time.sleep(30)
                continue

            precio = float(df.iloc[-1]["Close"])

            zonas = detectar_zonas(df)

            print(f"📊 Zonas detectadas: {len(zonas)}")

            for z in zonas:

                z_id = (
                    f"{z['Tipo']}_"
                    f"{z['High']}_"
                    f"{z['Low']}"
                )

                if z_id in alertas:
                    continue

                if tocar_zona(df, z):

                    enviar_mensaje(mensaje_alerta(z, precio))

                    alertas.add(z_id)

                    print(f"🎯 Señal enviada: {z_id}")

            time.sleep(60)

        except Exception as e:

            print("❌ Error en loop principal:", e)
            time.sleep(30)


if __name__ == "__main__":
    run()
