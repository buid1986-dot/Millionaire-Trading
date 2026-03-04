"""
Estrategia de Trading: GAP FILL + Indicadores
VERSION 4.0 — Optimizaciones aplicadas:
  ✓ CCXT (Binance) reemplaza yfinance — datos 24/7 sin gaps artificiales
  ✓ ATR separado: atr_5m para SL/TP granular, atr_1d para comparar niveles diarios
  ✓ strong_resistance/support: tolerancia 1%→3%
  ✓ Eliminadas penalizaciones negativas de indicator_score (ya no bloquea señales válidas)
  ✓ Consolidación pura: confidence_adjustment 0.5→0.75
  ✓ Proximidad a gaps históricos: 2%→4%
  ✓ Modo señal por indicadores puros (RSI+MACD sin necesidad de gap)
  ✓ Pivot Points calculados con datos Binance 1d
"""

import ccxt
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, timedelta
import time

# Zonas horarias
NY_TIMEZONE     = pytz.timezone('America/New_York')
TIJUANA_TIMEZONE = pytz.timezone('America/Tijuana')

# Símbolos para CCXT/Binance
SYMBOL_MAP = {
    "BTC-USD": "BTC/USDT",
    "ETH-USD": "ETH/USDT",
    "SOL-USD": "SOL/USDT",
    "BNB-USD": "BNB/USDT",
    "XRP-USD": "XRP/USDT",
}

# =======================================================================
# CLIENTE CCXT
# =======================================================================

def get_exchange():
    """Binance spot, sin API key (solo datos públicos)"""
    return ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })


def fetch_ohlcv_df(exchange, symbol, timeframe='1h', limit=200):
    """
    Descarga velas desde Binance y retorna DataFrame con columnas OHLCV.
    Más fiable que yfinance para crypto: sin gaps artificiales, datos 24/7.
    """
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not ohlcv:
            return pd.DataFrame()

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df.set_index('timestamp', inplace=True)
        df = df.astype(float)
        return df

    except Exception as e:
        print(f"  ⚠️  CCXT error [{symbol} {timeframe}]: {e}")
        return pd.DataFrame()


# =======================================================================
# FUNCIONES BÁSICAS
# =======================================================================

def safe_float(x):
    try:
        if isinstance(x, pd.Series):
            if len(x) == 0:
                return np.nan
            val = x.iloc[-1]
        else:
            val = x
        if pd.isna(val):
            return np.nan
        if isinstance(val, (np.integer, np.floating)):
            return float(val)
        if hasattr(val, 'item'):
            return float(val.item())
        return float(val)
    except:
        return np.nan


def check_high_volume(df, period=20, multiplier=1.5):
    if len(df) < period:
        return False
    try:
        last_vol = safe_float(df['Volume'].iloc[-1])
        avg_vol  = df['Volume'].iloc[-period:-1].mean()
        return last_vol > (safe_float(avg_vol) * multiplier)
    except:
        return False


def safe_atr(df, period=14):
    """ATR estándar sobre el DataFrame que se le pase"""
    if len(df) < period + 1:
        return np.nan
    try:
        hl  = df['High'] - df['Low']
        hc  = np.abs(df['High'] - df['Close'].shift())
        lc  = np.abs(df['Low']  - df['Close'].shift())
        tr  = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        return safe_float(tr.rolling(period).mean().iloc[-1])
    except:
        return np.nan


# =======================================================================
# PIVOT POINTS (con datos Binance 1d)
# =======================================================================

def calculate_pivot_points(exchange, ccxt_symbol):
    """
    Calcula Pivot Point clásico usando la vela diaria anterior de Binance.
    Retorna: PP, R1, S1, df_1d, error_msg
    """
    try:
        df_1d = fetch_ohlcv_df(exchange, ccxt_symbol, timeframe='1d', limit=400)

        if df_1d.empty or len(df_1d) < 2:
            return np.nan, np.nan, np.nan, df_1d, "Datos insuficientes 1d"

        H = safe_float(df_1d['High'].iloc[-2])
        L = safe_float(df_1d['Low'].iloc[-2])
        C = safe_float(df_1d['Close'].iloc[-2])

        if any(np.isnan([H, L, C])):
            return np.nan, np.nan, np.nan, df_1d, "Valores inválidos en vela anterior"

        PP = (H + L + C) / 3
        R1 = (2 * PP) - L
        S1 = (2 * PP) - H
        return PP, R1, S1, df_1d, None

    except Exception as e:
        return np.nan, np.nan, np.nan, pd.DataFrame(), f"Error: {e}"


def find_historical_level(df_1d, last_price, is_resistance=True, lookback_days=100):
    if df_1d.empty or len(df_1d) < 3:
        return np.nan
    df_h = df_1d.iloc[-lookback_days:-2]
    if df_h.empty:
        return np.nan
    try:
        if is_resistance:
            rel = df_h[df_h['High'] > last_price]['High']
            return safe_float(rel.min()) if not rel.empty else np.nan
        else:
            rel = df_h[df_h['Low'] < last_price]['Low']
            return safe_float(rel.max()) if not rel.empty else np.nan
    except:
        return np.nan


# =======================================================================
# INDICADORES TÉCNICOS
# =======================================================================

def calculate_rsi(df, period=14):
    if len(df) < period + 1:
        return np.nan
    try:
        delta = df['Close'].diff()
        gain  = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss  = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs    = gain / loss
        return safe_float((100 - (100 / (1 + rs))).iloc[-1])
    except:
        return np.nan


def calculate_macd(df, fast=12, slow=26, signal=9):
    if len(df) < slow + signal:
        return np.nan, np.nan, np.nan, "NEUTRAL"
    try:
        exp1      = df['Close'].ewm(span=fast, adjust=False).mean()
        exp2      = df['Close'].ewm(span=slow, adjust=False).mean()
        macd_line = exp1 - exp2
        sig_line  = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - sig_line

        mc  = safe_float(macd_line.iloc[-1])
        sc  = safe_float(sig_line.iloc[-1])
        mp  = safe_float(macd_line.iloc[-2])
        sp  = safe_float(sig_line.iloc[-2])

        if   mp <= sp and mc > sc: cross = "BULLISH_CROSS"
        elif mp >= sp and mc < sc: cross = "BEARISH_CROSS"
        elif mc > sc:              cross = "BULLISH"
        elif mc < sc:              cross = "BEARISH"
        else:                      cross = "NEUTRAL"

        return mc, sc, safe_float(histogram.iloc[-1]), cross
    except:
        return np.nan, np.nan, np.nan, "NEUTRAL"


def calculate_ema(df, period=200):
    if len(df) < period:
        return np.nan
    try:
        return safe_float(df['Close'].ewm(span=period, adjust=False).mean().iloc[-1])
    except:
        return np.nan


def analyze_technical_indicators(exchange, ccxt_symbol, last_price):
    """
    RSI y MACD sobre velas 1h (proxy de 4h), EMA200 sobre 1d.
    Usa datos de Binance via CCXT.
    """
    indicators = {
        'rsi_4h':       np.nan,
        'rsi_signal':   'NEUTRAL',
        'macd_4h':      np.nan,
        'macd_signal':  'NEUTRAL',
        'macd_histogram': np.nan,
        'ema200_1d':    np.nan,
        'ema_signal':   'NEUTRAL',
        'total_score':  0.0,
    }

    try:
        # ── 1h data para RSI y MACD (720 velas ≈ 30 días) ──────────────
        df_1h = fetch_ohlcv_df(exchange, ccxt_symbol, timeframe='1h', limit=720)

        if not df_1h.empty and len(df_1h) > 30:
            rsi = calculate_rsi(df_1h, period=14)
            indicators['rsi_4h'] = rsi

            if not np.isnan(rsi):
                if rsi < 30:
                    indicators['rsi_signal'] = 'OVERSOLD';    indicators['total_score'] += 1.0
                elif rsi > 70:
                    indicators['rsi_signal'] = 'OVERBOUGHT';  indicators['total_score'] += 1.0
                elif 30 <= rsi <= 40:
                    indicators['rsi_signal'] = 'BULLISH_ZONE'; indicators['total_score'] += 0.5
                elif 60 <= rsi <= 70:
                    indicators['rsi_signal'] = 'BEARISH_ZONE'; indicators['total_score'] += 0.5

            _, _, hist, cross = calculate_macd(df_1h)
            indicators['macd_4h']       = _
            indicators['macd_histogram'] = hist
            indicators['macd_signal']   = cross

            if   cross == "BULLISH_CROSS": indicators['total_score'] += 1.0
            elif cross == "BEARISH_CROSS": indicators['total_score'] += 1.0
            elif cross == "BULLISH":       indicators['total_score'] += 0.5
            elif cross == "BEARISH":       indicators['total_score'] += 0.5

        # ── 1d data para EMA200 ─────────────────────────────────────────
        df_1d = fetch_ohlcv_df(exchange, ccxt_symbol, timeframe='1d', limit=400)

        if not df_1d.empty and len(df_1d) > 200:
            ema200 = calculate_ema(df_1d, period=200)
            indicators['ema200_1d'] = ema200

            if not np.isnan(ema200):
                dist_pct = ((last_price - ema200) / ema200) * 100
                if last_price > ema200:
                    indicators['ema_signal'] = 'ABOVE_STRONG' if dist_pct > 2 else 'ABOVE'
                    indicators['total_score'] += 1.0 if dist_pct > 2 else 0.5
                else:
                    indicators['ema_signal'] = 'BELOW_STRONG' if dist_pct < -2 else 'BELOW'
                    indicators['total_score'] += 1.0 if dist_pct < -2 else 0.5

    except Exception:
        pass

    return indicators


# =======================================================================
# ESTRUCTURA DE MERCADO
# =======================================================================

def detect_consolidation(df_1d, lookback=20):
    if len(df_1d) < lookback:
        return False, 0.0, np.nan, np.nan
    recent   = df_1d.iloc[-lookback:]
    highest  = recent['High'].max()
    lowest   = recent['Low'].min()
    range_pct = ((highest - lowest) / lowest) * 100
    return range_pct < 5.0, range_pct, highest, lowest


def detect_accumulation(df_1d, lookback=60):
    if len(df_1d) < lookback:
        return False, "NONE", 0.0, [], ""
    recent = df_1d.iloc[-lookback:]

    price_trend   = (recent['Close'].iloc[-1] - recent['Close'].iloc[0]) / recent['Close'].iloc[0]
    vol_first     = recent['Volume'].iloc[:lookback//2].mean()
    vol_second    = recent['Volume'].iloc[lookback//2:].mean()
    vol_decreasing = vol_second < vol_first

    last20    = recent.iloc[-20:]
    rng_recent = ((last20['High'].max() - last20['Low'].min()) / last20['Low'].min()) * 100
    forming_base = rng_recent < 8.0

    rsi_vals, price_vals = [], []
    for i in range(-10, 0, 2):
        r = calculate_rsi(df_1d.iloc[:len(df_1d)+i], period=14)
        p = safe_float(df_1d['Close'].iloc[i])
        if not np.isnan(r):
            rsi_vals.append(r); price_vals.append(p)

    bull_div = (len(rsi_vals) >= 3 and
                rsi_vals[-1] > rsi_vals[0] and price_vals[-1] < price_vals[0])

    score, signals = 0, []
    if price_trend < 0 or abs(price_trend) < 0.05: score += 1;   signals.append("Precio zona baja")
    if vol_decreasing:                              score += 1;   signals.append("Volumen decreciente")
    if forming_base:                                score += 1.5; signals.append("Formando base")
    if bull_div:                                    score += 1.5; signals.append("Divergencia RSI alcista")

    if score >= 3.0:   phase, action = "STRONG_ACCUMULATION",   "ACUMULACION FUERTE - Preparar LONG"
    elif score >= 2.0: phase, action = "POSSIBLE_ACCUMULATION", "Posible acumulacion - Monitorear"
    else:              phase, action = "NONE", ""

    return score >= 2.0, phase, score, signals, action


def detect_distribution(df_1d, lookback=60):
    if len(df_1d) < lookback:
        return False, "NONE", 0.0, [], ""
    recent = df_1d.iloc[-lookback:]

    price_trend   = (recent['Close'].iloc[-1] - recent['Close'].iloc[0]) / recent['Close'].iloc[0]
    vol_first     = recent['Volume'].iloc[:lookback//2].mean()
    vol_second    = recent['Volume'].iloc[lookback//2:].mean()
    vol_decreasing = vol_second < vol_first

    last20    = recent.iloc[-20:]
    rng_recent = ((last20['High'].max() - last20['Low'].min()) / last20['Low'].min()) * 100
    forming_top = rng_recent < 8.0

    rsi_vals, price_vals = [], []
    for i in range(-10, 0, 2):
        r = calculate_rsi(df_1d.iloc[:len(df_1d)+i], period=14)
        p = safe_float(df_1d['Close'].iloc[i])
        if not np.isnan(r):
            rsi_vals.append(r); price_vals.append(p)

    bear_div = (len(rsi_vals) >= 3 and
                rsi_vals[-1] < rsi_vals[0] and price_vals[-1] > price_vals[0])

    score, signals = 0, []
    if price_trend > 0 or abs(price_trend) < 0.05: score += 1;   signals.append("Precio zona alta")
    if vol_decreasing:                              score += 1;   signals.append("Volumen decreciente")
    if forming_top:                                 score += 1.5; signals.append("Formando techo")
    if bear_div:                                    score += 1.5; signals.append("Divergencia RSI bajista")

    if score >= 3.0:   phase, action = "STRONG_DISTRIBUTION",   "DISTRIBUCION FUERTE - Preparar SHORT"
    elif score >= 2.0: phase, action = "POSSIBLE_DISTRIBUTION", "Posible distribucion - Monitorear"
    else:              phase, action = "NONE", ""

    return score >= 2.0, phase, score, signals, action


def analyze_market_structure(df_1d, last_price):
    is_cons, range_pct, resistance, support = detect_consolidation(df_1d)
    is_accum, accum_phase, accum_score, accum_signals, accum_action   = detect_accumulation(df_1d)
    is_dist,  dist_phase,  dist_score,  dist_signals,  dist_action    = detect_distribution(df_1d)

    if is_cons:
        dist_res = ((resistance - last_price) / last_price) * 100
        dist_sup = ((last_price - support)    / last_price) * 100
        position = ('NEAR_RESISTANCE' if dist_res < 1.0
                    else 'NEAR_SUPPORT' if dist_sup < 1.0
                    else 'MID_RANGE')

        if is_accum and accum_score > dist_score:
            phase  = 'ACCUMULATION_IN_RANGE'
            rec    = 'Consolidacion con acumulacion - ESPERAR breakout'
            adj    = 0.8
        elif is_dist and dist_score > accum_score:
            phase  = 'DISTRIBUTION_IN_RANGE'
            rec    = 'Consolidacion con distribucion - ESPERAR breakdown'
            adj    = 0.8
        else:
            phase  = 'PURE_CONSOLIDATION'
            rec    = 'CONSOLIDACION PURA - Señales con cautela'
            # ── FIX: reducido de 0.5 a 0.75 para no cancelar señales válidas ──
            adj    = 0.75

    elif is_accum and not is_dist:
        phase = accum_phase; rec = accum_action
        adj   = 1.2 if 'STRONG' in accum_phase else 1.1
        is_cons = False; position = 'ACCUMULATION_ZONE'
        range_pct = 0.0; resistance = support = np.nan

    elif is_dist and not is_accum:
        phase = dist_phase; rec = dist_action
        adj   = 1.2 if 'STRONG' in dist_phase else 1.1
        is_cons = False; position = 'DISTRIBUTION_ZONE'
        range_pct = 0.0; resistance = support = np.nan

    else:
        phase = 'TRENDING'; rec = 'Tendencia clara - Operar normal'
        adj   = 1.0; is_cons = False; position = 'TRENDING'
        range_pct = 0.0; resistance = support = np.nan

    return {
        'primary_phase':        phase,
        'recommendation':       rec,
        'confidence_adjustment': adj,
        'consolidation': {
            'is_consolidating': is_cons,
            'range_pct':  range_pct,
            'resistance': resistance,
            'support':    support,
            'position':   position if is_cons else 'N/A',
        },
        'accumulation': {'detected': is_accum, 'phase': accum_phase,
                         'score': accum_score, 'signals': accum_signals},
        'distribution':  {'detected': is_dist,  'phase': dist_phase,
                         'score': dist_score,  'signals': dist_signals},
    }


# =======================================================================
# DETECCIÓN DE GAPS
# Nota: crypto spot es 24/7, los "gaps" reales son infrecuentes.
# El código detecta discontinuidades entre cierre anterior y apertura
# actual que superan el umbral, que pueden ocurrir tras noticias bruscas.
# =======================================================================

def find_all_gaps_comprehensive(df_1d, current_price, lookback_days=120):
    gaps_above, gaps_below = [], []
    if df_1d.empty or len(df_1d) < 3:
        return gaps_above, gaps_below

    df_r = df_1d.iloc[-lookback_days:] if len(df_1d) >= lookback_days else df_1d

    for i in range(1, len(df_r)):
        try:
            ph = safe_float(df_r['High'].iloc[i-1])
            pl = safe_float(df_r['Low'].iloc[i-1])
            cl = safe_float(df_r['Close'].iloc[i-1])
            oh = safe_float(df_r['High'].iloc[i])
            ol = safe_float(df_r['Low'].iloc[i])

            if any(np.isnan([ph, pl, cl, oh, ol])):
                continue

            # Gap alcista
            if ol > ph:
                gb, gt = ph, ol
                filled = any(
                    not np.isnan(safe_float(df_r['Low'].iloc[j]))
                    and safe_float(df_r['Low'].iloc[j]) <= gb
                    for j in range(i, len(df_r))
                )
                if not filled:
                    mid  = (gb + gt) / 2
                    size = ((gt - gb) / gb) * 100
                    info = {'level': mid, 'bottom': gb, 'top': gt, 'type': 'GAP_UP',
                            'age_days': len(df_r)-i, 'size_pct': size,
                            'strength': 'STRONG' if size > 2 else 'MEDIUM' if size > 1 else 'WEAK'}
                    (gaps_above if mid > current_price else gaps_below).append(info)

            # Gap bajista
            elif oh < pl:
                gt, gb = pl, oh
                filled = any(
                    not np.isnan(safe_float(df_r['High'].iloc[j]))
                    and safe_float(df_r['High'].iloc[j]) >= gt
                    for j in range(i, len(df_r))
                )
                if not filled:
                    mid  = (gb + gt) / 2
                    size = ((gt - gb) / gb) * 100
                    info = {'level': mid, 'bottom': gb, 'top': gt, 'type': 'GAP_DOWN',
                            'age_days': len(df_r)-i, 'size_pct': size,
                            'strength': 'STRONG' if size > 2 else 'MEDIUM' if size > 1 else 'WEAK'}
                    (gaps_above if mid > current_price else gaps_below).append(info)
        except:
            continue

    gaps_above = sorted(gaps_above, key=lambda x: x['level'])
    gaps_below = sorted(gaps_below, key=lambda x: x['level'], reverse=True)
    return gaps_above, gaps_below


def detect_gap_improved(df_1d, last_price, threshold_pct=0.3):
    """
    Busca gaps sin rellenar en los últimos 7 días.
    threshold_pct=0.3 → mínimo 0.3% para contar como gap real.
    """
    if df_1d.empty or len(df_1d) < 5:
        return "NO_GAP", np.nan, []

    recent_gaps = []

    for i in range(-7, 0):
        try:
            if abs(i) > len(df_1d):
                continue
            ph = safe_float(df_1d['High'].iloc[i-1])
            pl = safe_float(df_1d['Low'].iloc[i-1])
            oh = safe_float(df_1d['High'].iloc[i])
            ol = safe_float(df_1d['Low'].iloc[i])

            if any(np.isnan([ph, pl, oh, ol])):
                continue

            # Gap alcista sin rellenar
            if ol > ph:
                size = ((ol - ph) / ph) * 100
                if size > threshold_pct:
                    filled = any(
                        safe_float(df_1d['Low'].iloc[j]) <= ph
                        for j in range(i, 0)
                        if not np.isnan(safe_float(df_1d['Low'].iloc[j]))
                    )
                    if not filled and ph < last_price:
                        recent_gaps.append({'level': ph, 'type': 'GAP_UP',
                                            'size_pct': size, 'age_days': abs(i),
                                            'direction': 'DOWN_TO_FILL'})

            # Gap bajista sin rellenar
            elif oh < pl:
                size = ((pl - oh) / oh) * 100
                if size > threshold_pct:
                    filled = any(
                        safe_float(df_1d['High'].iloc[j]) >= pl
                        for j in range(i, 0)
                        if not np.isnan(safe_float(df_1d['High'].iloc[j]))
                    )
                    if not filled and pl > last_price:
                        recent_gaps.append({'level': pl, 'type': 'GAP_DOWN',
                                            'size_pct': size, 'age_days': abs(i),
                                            'direction': 'UP_TO_FILL'})
        except:
            continue

    if not recent_gaps:
        return "NO_GAP", np.nan, []

    recent_gaps = sorted(recent_gaps, key=lambda x: abs(x['level'] - last_price))
    closest = recent_gaps[0]

    if closest['direction'] == 'DOWN_TO_FILL': return "SHORT_TO_FILL", closest['level'], recent_gaps
    if closest['direction'] == 'UP_TO_FILL':   return "LONG_TO_FILL",  closest['level'], recent_gaps
    return "NO_GAP", np.nan, []


# =======================================================================
# VALIDACIÓN DE NIVELES
# =======================================================================

def validate_levels(decision, entry_p, sl_p, tp1_p, tp2_p, atr, last_price):
    if np.isnan(entry_p) or np.isnan(atr):
        return entry_p, sl_p, tp1_p, tp2_p

    if "SHORT" in decision:
        if not np.isnan(sl_p)  and sl_p <= entry_p:  sl_p  = entry_p + atr * 1.5
        if not np.isnan(tp1_p) and tp1_p >= entry_p: tp1_p = entry_p - atr * 1.0
        if not np.isnan(tp2_p):
            if tp2_p >= entry_p:                      tp2_p = entry_p - atr * 2.0
            if not np.isnan(tp1_p) and tp2_p >= tp1_p: tp2_p = tp1_p - atr * 1.0

    elif "LONG" in decision:
        if not np.isnan(sl_p)  and sl_p >= entry_p:  sl_p  = entry_p - atr * 1.5
        if not np.isnan(tp1_p) and tp1_p <= entry_p: tp1_p = entry_p + atr * 1.0
        if not np.isnan(tp2_p):
            if tp2_p <= entry_p:                      tp2_p = entry_p + atr * 2.0
            if not np.isnan(tp1_p) and tp2_p <= tp1_p: tp2_p = tp1_p + atr * 1.0

    return entry_p, sl_p, tp1_p, tp2_p


# =======================================================================
# ANÁLISIS PRINCIPAL
# =======================================================================

def analyze_pre_ny(symbol_yf, exchange):
    """
    symbol_yf: formato original "BTC-USD" (se convierte a "BTC/USDT" para CCXT)
    """
    ccxt_symbol = SYMBOL_MAP.get(symbol_yf, symbol_yf.replace("-", "/").replace("USD", "USDT"))

    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']

    # ── Descargar datos ───────────────────────────────────────────────
    try:
        # 5m: últimos 7 días ≈ 2016 velas (Binance limite 1000, usamos 1000)
        data_5m = fetch_ohlcv_df(exchange, ccxt_symbol, timeframe='5m',  limit=1000)
        data_1h = fetch_ohlcv_df(exchange, ccxt_symbol, timeframe='1h',  limit=720)

        if data_5m.empty or not all(c in data_5m.columns for c in required_cols):
            return f"❌ Error Datos 5m para {symbol_yf}: DataFrame vacío o incompleto."
        data_5m = data_5m.dropna(subset=required_cols)

    except Exception as e:
        return f"❌ Error de conexión CCXT (5m) para {symbol_yf}: {e}"

    PP, R1, S1, data_1d, error_1d = calculate_pivot_points(exchange, ccxt_symbol)
    if error_1d:
        return f"❌ Error Pivotes (1D) para {symbol_yf}: {error_1d}"

    if data_5m.empty or np.isnan(PP) or len(data_5m) < 3:
        return f"❌ Datos insuficientes para {symbol_yf}."

    # ── Tiempo y precio ───────────────────────────────────────────────
    try:
        if data_5m.index.tz is not None:
            data_5m_ny = data_5m.tz_convert(NY_TIMEZONE)
        else:
            data_5m_ny = data_5m.tz_localize('UTC').tz_convert(NY_TIMEZONE)

        last_candle_time  = data_5m_ny.index[-1]
        next_candle_time  = last_candle_time + pd.Timedelta(minutes=5)
        last_ts_tj        = last_candle_time.astimezone(TIJUANA_TIMEZONE)
        next_ts_tj        = next_candle_time.astimezone(TIJUANA_TIMEZONE)
        last_timestamp    = last_ts_tj.strftime('%Y-%m-%d %H:%M:%S')
        entry_time_display = next_ts_tj.strftime('%H:%M:%S')

        last_price = safe_float(data_5m["Close"].iloc[-1])
        if np.isnan(last_price):
            raise ValueError("Precio final inválido.")
    except Exception as e:
        return f"❌ Error extrayendo precio/tiempo para {symbol_yf}: {e}"

    # ── ATR DUAL — FIX CLAVE ─────────────────────────────────────────
    # atr_5m: para SL/TP granulares en escala de vela de 5 minutos
    # atr_1d: para comparar con niveles pivote/históricos en escala diaria
    atr_5m = safe_atr(data_5m)
    atr_1d = safe_atr(data_1d) if not data_1d.empty else np.nan

    # Usar atr_1d para comparaciones de nivel; fallback a % del precio
    atr_for_levels = atr_1d if not np.isnan(atr_1d) else last_price * 0.015

    # Tolerancia para entrada: precio vs PP (usa escala diaria)
    ATR_TOLERANCE = atr_for_levels * 0.3

    high_volume  = check_high_volume(data_5m)
    gap_signal, gap_level, all_recent_gaps = detect_gap_improved(data_1d, last_price)
    indicators   = analyze_technical_indicators(exchange, ccxt_symbol, last_price)
    market_structure = analyze_market_structure(data_1d, last_price)
    gaps_above, gaps_below = find_all_gaps_comprehensive(data_1d, last_price, lookback_days=120)

    R2_hist = find_historical_level(data_1d, last_price, is_resistance=True)
    S2_hist = find_historical_level(data_1d, last_price, is_resistance=False)

    # ── FIX: tolerancia ampliada a 3% (antes 1%) ─────────────────────
    strong_resistance = not np.isnan(R2_hist) and abs(last_price - R2_hist) / last_price < 0.03
    strong_support    = not np.isnan(S2_hist) and abs(last_price - S2_hist) / last_price < 0.03

    decision = "NO_OPERAR (Sin Señal Clara)"
    confidence = 0.0
    entry_p, sl_p, tp1_p, tp2_p, tp3_p = np.nan, np.nan, np.nan, np.nan, np.nan
    indicator_score = 0.0
    max_score = 6.0

    # ── LÓGICA DE DECISIÓN ────────────────────────────────────────────

    if gap_signal == "SHORT_TO_FILL":
        confidence += 2.0
        sl_p  = R1 if R1 > last_price else (R2_hist if not np.isnan(R2_hist) and R2_hist > last_price else last_price + atr_for_levels * 1.5)
        tp1_p = gap_level
        tp2_p = S1
        tp3_p = (next((g['level'] for g in gaps_below if g['strength'] in ['STRONG','MEDIUM'] and g['level'] < tp2_p), None)
                 or (S2_hist if not np.isnan(S2_hist) and S2_hist < tp2_p else tp2_p - atr_for_levels * 2.0))

        if last_price > PP: confidence += 1.0
        else:               confidence -= 0.5

        # ── FIX: sin penalizaciones negativas — solo sumar o quedar en 0 ──
        if indicators['rsi_signal'] in ['OVERBOUGHT']:     indicator_score += 1.0
        elif indicators['rsi_signal'] in ['BEARISH_ZONE']: indicator_score += 0.5

        if indicators['macd_signal'] == 'BEARISH_CROSS':   indicator_score += 1.0
        elif indicators['macd_signal'] == 'BEARISH':       indicator_score += 0.5

        if indicators['ema_signal'] in ['BELOW_STRONG', 'BELOW']: indicator_score += 0.5

        confidence += max(0.0, indicator_score)  # nunca resta
        confidence += 1.0 if high_volume else 0.0

        if confidence >= 3.0:
            if last_price >= PP or abs(last_price - PP) < ATR_TOLERANCE:
                entry_p  = last_price
                decision = "SHORT_FUERTE (Activacion Inmediata)" if confidence >= 4.5 else "SHORT_MODERADO (Activacion Inmediata)"
            else:
                entry_p  = PP
                decision = "SHORT_PENDIENTE (Esperar Retroceso a PP)"
        else:
            decision = f"NO_OPERAR (Gap SHORT detectado — confianza baja: {confidence:.1f}/{max_score:.0f})"

    elif gap_signal == "LONG_TO_FILL":
        confidence += 2.0
        sl_p  = S1 if S1 < last_price else (S2_hist if not np.isnan(S2_hist) and S2_hist < last_price else last_price - atr_for_levels * 1.5)
        tp1_p = gap_level
        tp2_p = R1
        tp3_p = (next((g['level'] for g in gaps_above if g['strength'] in ['STRONG','MEDIUM'] and g['level'] > tp2_p), None)
                 or (R2_hist if not np.isnan(R2_hist) and R2_hist > tp2_p else tp2_p + atr_for_levels * 2.0))

        if last_price < PP: confidence += 1.0
        else:               confidence -= 0.5

        if indicators['rsi_signal'] in ['OVERSOLD']:       indicator_score += 1.0
        elif indicators['rsi_signal'] in ['BULLISH_ZONE']: indicator_score += 0.5

        if indicators['macd_signal'] == 'BULLISH_CROSS':   indicator_score += 1.0
        elif indicators['macd_signal'] == 'BULLISH':       indicator_score += 0.5

        if indicators['ema_signal'] in ['ABOVE_STRONG', 'ABOVE']: indicator_score += 0.5

        confidence += max(0.0, indicator_score)
        confidence += 1.0 if high_volume else 0.0

        if confidence >= 3.0:
            if last_price <= PP or abs(last_price - PP) < ATR_TOLERANCE:
                entry_p  = last_price
                decision = "LONG_FUERTE (Activacion Inmediata)" if confidence >= 4.5 else "LONG_MODERADO (Activacion Inmediata)"
            else:
                entry_p  = PP
                decision = "LONG_PENDIENTE (Esperar Retroceso a PP)"
        else:
            decision = f"NO_OPERAR (Gap LONG detectado — confianza baja: {confidence:.1f}/{max_score:.0f})"

    elif gap_signal == "NO_GAP":

        # ── FIX: proximidad a gaps históricos ampliada a 4% (antes 2%) ──
        PROX_GAP = 0.04

        if gaps_above and abs(gaps_above[0]['level'] - last_price) / last_price < PROX_GAP:
            confidence += 1.5
            sl_p  = gaps_above[0]['top'] + atr_for_levels * 0.5
            tp1_p = PP if PP < last_price else last_price - atr_for_levels * 2.0
            tp2_p = S1
            tp3_p = gaps_below[0]['level'] if gaps_below else S2_hist

            if indicators['rsi_signal'] in ['OVERBOUGHT', 'BEARISH_ZONE']: indicator_score += 1.0
            if indicators['macd_signal'] in ['BEARISH_CROSS', 'BEARISH']:   indicator_score += 1.0

            confidence += max(0.0, indicator_score)
            if confidence >= 3.0:
                entry_p  = last_price
                decision = "SHORT_GAP_HISTORICO (Resistencia)"

        elif gaps_below and abs(gaps_below[0]['level'] - last_price) / last_price < PROX_GAP:
            confidence += 1.5
            sl_p  = gaps_below[0]['bottom'] - atr_for_levels * 0.5
            tp1_p = PP if PP > last_price else last_price + atr_for_levels * 2.0
            tp2_p = R1
            tp3_p = gaps_above[0]['level'] if gaps_above else R2_hist

            if indicators['rsi_signal'] in ['OVERSOLD', 'BULLISH_ZONE']:    indicator_score += 1.0
            if indicators['macd_signal'] in ['BULLISH_CROSS', 'BULLISH']:    indicator_score += 1.0

            confidence += max(0.0, indicator_score)
            if confidence >= 3.0:
                entry_p  = last_price
                decision = "LONG_GAP_HISTORICO (Soporte)"

        elif strong_resistance and last_price >= R2_hist:
            confidence += 1.5
            sl_p  = R2_hist + atr_for_levels * 1.0
            tp1_p = PP; tp2_p = S1
            tp3_p = S2_hist if not np.isnan(S2_hist) else S1 - atr_for_levels * 2.0

            if indicators['rsi_signal'] in ['OVERBOUGHT', 'BEARISH_ZONE']: indicator_score += 1.0
            if indicators['macd_signal'] in ['BEARISH_CROSS', 'BEARISH']:   indicator_score += 1.0

            confidence += max(0.0, indicator_score) + (1.0 if high_volume else 0.0)
            if confidence >= 3.5:
                entry_p  = last_price
                decision = "SHORT_RESISTENCIA (Nivel Historico)"

        elif strong_support and last_price <= S2_hist:
            confidence += 1.5
            sl_p  = S2_hist - atr_for_levels * 1.0
            tp1_p = PP; tp2_p = R1
            tp3_p = R2_hist if not np.isnan(R2_hist) else R1 + atr_for_levels * 2.0

            if indicators['rsi_signal'] in ['OVERSOLD', 'BULLISH_ZONE']:    indicator_score += 1.0
            if indicators['macd_signal'] in ['BULLISH_CROSS', 'BULLISH']:    indicator_score += 1.0

            confidence += max(0.0, indicator_score) + (1.0 if high_volume else 0.0)
            if confidence >= 3.5:
                entry_p  = last_price
                decision = "LONG_SOPORTE (Nivel Historico)"

        else:
            # ── NUEVO: Modo indicadores puros — sin gap ni nivel cercano ──
            rsi  = indicators['rsi_4h']
            macd = indicators['macd_signal']
            ema  = indicators['ema_signal']

            if not np.isnan(rsi) and rsi < 35 and macd in ['BULLISH_CROSS', 'BULLISH']:
                confidence  = 3.0 + (0.5 if ema in ['ABOVE_STRONG', 'ABOVE'] else 0.0)
                confidence += 0.5 if rsi < 30 else 0.0
                indicator_score = confidence
                entry_p  = last_price
                sl_p     = last_price - atr_for_levels * 1.5
                tp1_p    = PP if PP > last_price else last_price + atr_for_levels * 1.0
                tp2_p    = R1
                tp3_p    = R2_hist if not np.isnan(R2_hist) else tp2_p + atr_for_levels * 1.5
                decision = "LONG_INDICADORES (RSI Oversold + MACD Alcista)"

            elif not np.isnan(rsi) and rsi > 65 and macd in ['BEARISH_CROSS', 'BEARISH']:
                confidence  = 3.0 + (0.5 if ema in ['BELOW_STRONG', 'BELOW'] else 0.0)
                confidence += 0.5 if rsi > 70 else 0.0
                indicator_score = confidence
                entry_p  = last_price
                sl_p     = last_price + atr_for_levels * 1.5
                tp1_p    = PP if PP < last_price else last_price - atr_for_levels * 1.0
                tp2_p    = S1
                tp3_p    = S2_hist if not np.isnan(S2_hist) else tp2_p - atr_for_levels * 1.5
                decision = "SHORT_INDICADORES (RSI Overbought + MACD Bajista)"

    # ── Validar y ajustar niveles ─────────────────────────────────────
    # Para validación usamos atr_5m (escala granular de la entrada)
    atr_for_validate = atr_5m if not np.isnan(atr_5m) else atr_for_levels * 0.1
    entry_p, sl_p, tp1_p, tp2_p = validate_levels(decision, entry_p, sl_p, tp1_p, tp2_p, atr_for_validate, last_price)

    if "SHORT" in decision and not np.isnan(tp3_p):
        if not np.isnan(tp2_p) and tp3_p >= tp2_p:
            tp3_p = tp2_p - atr_for_levels * 1.0
    elif "LONG" in decision and not np.isnan(tp3_p):
        if not np.isnan(tp2_p) and tp3_p <= tp2_p:
            tp3_p = tp2_p + atr_for_levels * 1.0

    confidence_before_struct = confidence
    confidence *= market_structure['confidence_adjustment']
    confidence_pct = min(100, (confidence / max_score) * 100)

    # ── Formateo de salida ────────────────────────────────────────────
    if "PENDIENTE" in decision and not np.isnan(entry_p):
        entry_display = f"{entry_p:.4f} (Esperar en PP)"
        entry_type    = "Limit Order en PP"
    elif not np.isnan(entry_p):
        entry_display = f"{entry_p:.4f}"
        entry_type    = "Market Order"
    else:
        entry_display = "N/A"
        entry_type    = "Sin Operacion"

    sl_display  = f"{sl_p:.4f}"  if not np.isnan(sl_p)  else "N/A"
    tp1_display = f"{tp1_p:.4f}" if not np.isnan(tp1_p) else "N/A"
    tp2_display = f"{tp2_p:.4f}" if not np.isnan(tp2_p) else "N/A"
    tp3_display = f"{tp3_p:.4f}" if not np.isnan(tp3_p) else "N/A"

    gap_info_display = ""
    if gap_signal != "NO_GAP":
        gap_info_display = f"**{gap_signal}** @ {gap_level:.4f}\n"
        if all_recent_gaps and len(all_recent_gaps) > 1:
            for i, g in enumerate(all_recent_gaps[1:3], 1):
                gap_info_display += f"   {i}. {g['type']} @ {g['level']:.4f} ({g['age_days']}d, {g['size_pct']:.2f}%)\n"
    else:
        gap_info_display = "NO_GAP (Sin gaps recientes sin rellenar)\n"

    rsi_display  = f"{indicators['rsi_4h']:.1f}"      if not np.isnan(indicators['rsi_4h'])      else "N/A"
    macd_display = f"{indicators['macd_histogram']:.4f}" if not np.isnan(indicators['macd_histogram']) else "N/A"
    ema_display  = f"{indicators['ema200_1d']:.2f}"   if not np.isnan(indicators['ema200_1d'])   else "N/A"
    ema_dist     = ""
    if not np.isnan(indicators['ema200_1d']):
        d = ((last_price - indicators['ema200_1d']) / indicators['ema200_1d']) * 100
        ema_dist = f" ({d:+.1f}%)"

    gaps_info = "\n### GAPS HISTÓRICOS DETECTADOS\n"
    if "SHORT" in decision and gaps_below:
        for i, g in enumerate(gaps_below[:3], 1):
            gaps_info += f"  {i}. {g['level']:.4f} ({g['strength']}, {g['age_days']}d, {g['size_pct']:.2f}%) — [{g['bottom']:.4f}–{g['top']:.4f}]\n"
    elif "LONG" in decision and gaps_above:
        for i, g in enumerate(gaps_above[:3], 1):
            gaps_info += f"  {i}. {g['level']:.4f} ({g['strength']}, {g['age_days']}d, {g['size_pct']:.2f}%) — [{g['bottom']:.4f}–{g['top']:.4f}]\n"
    else:
        if gaps_below: gaps_info += f"  Gaps Abajo: {len(gaps_below)} | Más cercano: {gaps_below[0]['level']:.4f}\n"
        if gaps_above: gaps_info += f"  Gaps Arriba: {len(gaps_above)} | Más cercano: {gaps_above[0]['level']:.4f}\n"

    gap_pts = 2.0 if gap_signal != "NO_GAP" else (1.5 if (strong_resistance or strong_support) else 0.0)
    struct_pts = 1.0 if (
        (gap_signal == "SHORT_TO_FILL" and last_price > PP) or
        (gap_signal == "LONG_TO_FILL"  and last_price < PP) or
        (decision.startswith("SHORT")  and last_price > PP) or
        (decision.startswith("LONG")   and last_price < PP)
    ) else 0.0

    struct_info = f"""
### ESTRUCTURA DE MERCADO
* Fase: {market_structure['primary_phase']}
* Recomendacion: {market_structure['recommendation']}
* Ajuste Confianza: {market_structure['confidence_adjustment']:.2f}x  (Base: {confidence_before_struct:.1f} → Ajustada: {confidence:.1f})
"""
    if market_structure['consolidation']['is_consolidating']:
        c = market_structure['consolidation']
        struct_info += f"  [CONSOLIDACION] Rango {c['range_pct']:.2f}% | Res: {c['resistance']:.2f} | Sop: {c['support']:.2f} | Pos: {c['position']}\n"
    if market_structure['accumulation']['detected']:
        a = market_structure['accumulation']
        struct_info += f"  [ACUMULACION] Score: {a['score']:.1f}/5 | Fase: {a['phase']} | {', '.join(a['signals'])}\n"
    if market_structure['distribution']['detected']:
        d = market_structure['distribution']
        struct_info += f"  [DISTRIBUCION] Score: {d['score']:.1f}/5 | Fase: {d['phase']} | {', '.join(d['signals'])}\n"

    atr_display = f"{atr_5m:.4f} (5m) / {atr_1d:.2f} (1d)" if not np.isnan(atr_1d) else f"{atr_5m:.4f} (5m)"

    return f"""
=====================================
ANALISIS DE TRADING | {symbol_yf} ({ccxt_symbol} — Binance)
VERSION 4.0 — CCXT + Optimizaciones
=====================================

### DECISIÓN RÁPIDA
| Confianza: {confidence_pct:.0f}% | Señal: {decision} |
| Próxima Entrada (5m): {entry_time_display} TJ |

---

### NIVELES OPERABLES
| ENTRADA : {entry_display} | Tipo: {entry_type}         |
| SL      : {sl_display}   | Máximo riesgo              |
| TP1     : {tp1_display}  | Cierre del Gap / Nivel 1   |
| TP2     : {tp2_display}  | Pivote R1/S1               |
| TP3     : {tp3_display}  | Gap Histórico / Extensión  |

---

### CONTEXTO CLAVE
* Precio Actual: {last_price:.4f} (Binance | {last_timestamp} TJ)
* ATR: {atr_display}
* Gap Activo:
{gap_info_display}
* Punto Pivote (PP): {PP:.4f}
* Resistencia 1 (R1): {R1:.4f} | Dist: {((R1-last_price)/last_price*100):+.2f}%
* Soporte 1   (S1): {S1:.4f} | Dist: {((S1-last_price)/last_price*100):+.2f}%
{gaps_info}
---
{struct_info}
---

### INDICADORES TÉCNICOS (HTF)
* RSI 1H  : {rsi_display}  → {indicators['rsi_signal']}
* MACD 1H : {macd_display} → {indicators['macd_signal']}
* EMA200 1D: {ema_display}{ema_dist} → {indicators['ema_signal']}

### CONFIRMACIONES
* Puntuación: {confidence:.1f}/{max_score:.1f}
  · Gap/Nivel   : {gap_pts:.1f} pts
  · Estructura  : {struct_pts:.1f} pts
  · Indicadores : {max(0.0, indicator_score):.1f} pts
  · Volumen     : {'[SI]' if high_volume else '[NO]'} (1.0 pt)

[CAMBIOS v4.0]
✓ CCXT/Binance reemplaza yfinance — datos 24/7 sin gaps artificiales
✓ ATR dual: 5m para SL/TP, 1d para comparar niveles pivote
✓ strong_resistance/support: tolerancia ampliada 1%→3%
✓ Penalizaciones negativas eliminadas (indicator_score mínimo = 0)
✓ Consolidación pura: ajuste 0.5x→0.75x
✓ Proximidad gaps históricos: umbral 2%→4%
✓ Modo LONG/SHORT_INDICADORES: señal pura RSI+MACD sin gap
"""


# =======================================================================
# EJECUCIÓN
# =======================================================================

if __name__ == "__main__":
    symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD"]

    exchange = get_exchange()
    print("--- ANALISIS PRE-NY v4.0 (CCXT + Optimizaciones) ---\n")
    print(f"Fuente de datos: Binance via CCXT (sin API key)\n")

    for s in symbols:
        try:
            print(analyze_pre_ny(s, exchange))
        except Exception as e:
            print(f"Error al analizar {s}: {type(e).__name__} — {e}\n")
        time.sleep(0.5)  # respetar rate limit entre símbolos
