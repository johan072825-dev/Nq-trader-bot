//@version=5
strategy("SMC Bot NQ V5 - SIGNAL SYSTEM", overlay=true, default_qty_type=strategy.fixed, default_qty_value=1)

// ============================================================
// INPUTS
// ============================================================
hora_inicio = input.int(18, "NY Start Hour")
hora_fin    = input.int(23, "NY End Hour")
swing_len   = input.int(3, "Swing Length")
atr_mult    = input.float(1.0, "ATR Multiplier")

// ============================================================
// SESSION NY
// ============================================================
hora_ny    = hour(time, "America/New_York")
en_sesion  = hora_ny >= hora_inicio and hora_ny < hora_fin

// ============================================================
// ATR + IMPULSE FILTER
// ============================================================
atr = ta.atr(14)
cuerpo = math.abs(close - open)
impulso = cuerpo >= atr * atr_mult

// ============================================================
// SWING STRUCTURE
// ============================================================
ph = ta.pivothigh(high, swing_len, swing_len)
pl = ta.pivotlow(low, swing_len, swing_len)

var float last_high = na
var float last_low  = na

if not na(ph)
    last_high := ph

if not na(pl)
    last_low := pl

// ============================================================
// CONTEXT (SIMPLE & STABLE)
// ============================================================
trend_up = not na(last_high) and close > last_high
trend_dn = not na(last_low)  and close < last_low

// ============================================================
// ZONE LOGIC (SIMPLIFIED SMC)
// ============================================================
toca_demanda = not na(last_low) and low <= last_low
toca_oferta  = not na(last_high) and high >= last_high

// ============================================================
// BOS LOGIC
// ============================================================
bos_alcista = en_sesion and trend_up and impulso and close > open
bos_bajista = en_sesion and trend_dn and impulso and close < open

// ============================================================
// SIGNALS FINAL
// ============================================================
long_signal  = bos_alcista and toca_demanda
short_signal = bos_bajista and toca_oferta

// ============================================================
// ALERT MESSAGES (WEBHOOK READY)
// ============================================================
long_msg =
 '{"signal":"BUY","symbol":"' + syminfo.ticker + '","price":"' + str.tostring(close) + '"}'

short_msg =
 '{"signal":"SELL","symbol":"' + syminfo.ticker + '","price":"' + str.tostring(close) + '"}'

// ============================================================
// ALERT TRIGGERS
// ============================================================
if long_signal
    alert(long_msg, alert.freq_once_per_bar_close)

if short_signal
    alert(short_msg, alert.freq_once_per_bar_close)

// ============================================================
// VISUALS
// ============================================================
plotshape(long_signal, title="BUY", location=location.belowbar, color=color.green, style=shape.labelup, text="BUY")
plotshape(short_signal, title="SELL", location=location.abovebar, color=color.red, style=shape.labeldown, text="SELL")

plot(last_high, "Last High", color=color.red)
plot(last_low, "Last Low", color=color.green)
