import yfinance as yf
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, timedelta

# Zonas horarias
NY_TIMEZONE = pytz.timezone('America/New_York')
TIJUANA_TIMEZONE = pytz.timezone('America/Tijuana')

# =======================================================================
# FUNCIONES BASICAS
# =======================================================================

def safe_float(x):
    """Convierte a flotante de forma segura"""
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
    """Evalua si hay alto volumen"""
    if len(df) < period: return False
    try:
        last_volume = safe_float(df['Volume'].iloc[-1])
        avg_volume = df['Volume'].iloc[-period:-1].mean()
        return last_volume > (safe_float(avg_volume) * multiplier)
    except:
        return False

def safe_atr(df, period=14):
    """Calcula ATR"""
    if len(df) < period + 1: return np.nan
    try:
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        result_series = true_range.rolling(period).mean()
        return safe_float(result_series.iloc[-1])
    except:
        return np.nan

def calculate_pivot_points(symbol_str):
    """Calcula Puntos Pivote"""
    try:
        df_1d = yf.download(symbol_str, interval="1d", period="1y", progress=False, auto_adjust=True)
        
        if isinstance(df_1d.columns, pd.MultiIndex):
            df_1d.columns = df_1d.columns.get_level_values(0)
            
    except Exception as e:
        return np.nan, np.nan, np.nan, pd.DataFrame(), f"Error descarga: {e}" 

    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    if df_1d.empty or len(df_1d) < 2 or not all(col in df_1d.columns for col in required_cols):
        return np.nan, np.nan, np.nan, df_1d, "Datos insuficientes"
    
    try:
        H_prev = safe_float(df_1d['High'].iloc[-2])
        L_prev = safe_float(df_1d['Low'].iloc[-2])
        C_prev = safe_float(df_1d['Close'].iloc[-2])
        
        if np.isnan(H_prev) or np.isnan(L_prev) or np.isnan(C_prev): 
            return np.nan, np.nan, np.nan, df_1d, "Valores invalidos"
        
        PP = (H_prev + L_prev + C_prev) / 3
        R1 = (2 * PP) - L_prev
        S1 = (2 * PP) - H_prev
        return PP, R1, S1, df_1d, None
    except Exception as e:
        return np.nan, np.nan, np.nan, df_1d, f"Error: {e}"

def find_historical_level(df_1d, last_price, is_resistance=True, lookback_days=100):
    """Busca niveles historicos"""
    if df_1d.empty or len(df_1d) < 3: return np.nan
    df_history = df_1d.iloc[-lookback_days:-2]
    if df_history.empty: return np.nan
    try:
        if is_resistance:
            relevant_highs = df_history[df_history['High'] > last_price]['High']
            return safe_float(relevant_highs.min()) if not relevant_highs.empty else np.nan
        else:
            relevant_lows = df_history[df_history['Low'] < last_price]['Low']
            return safe_float(relevant_lows.max()) if not relevant_lows.empty else np.nan
    except:
        return np.nan

# =======================================================================
# INDICADORES TECNICOS
# =======================================================================

def calculate_rsi(df, period=14):
    """Calcula RSI"""
    if len(df) < period + 1:
        return np.nan
    
    try:
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return safe_float(rsi.iloc[-1])
    except:
        return np.nan

def calculate_macd(df, fast=12, slow=26, signal=9):
    """Calcula MACD"""
    if len(df) < slow + signal:
        return np.nan, np.nan, np.nan, "NEUTRAL"
    
    try:
        exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
        
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        macd_current = safe_float(macd_line.iloc[-1])
        signal_current = safe_float(signal_line.iloc[-1])
        macd_prev = safe_float(macd_line.iloc[-2])
        signal_prev = safe_float(signal_line.iloc[-2])
        
        if macd_prev <= signal_prev and macd_current > signal_current:
            cross_signal = "BULLISH_CROSS"
        elif macd_prev >= signal_prev and macd_current < signal_current:
            cross_signal = "BEARISH_CROSS"
        elif macd_current > signal_current:
            cross_signal = "BULLISH"
        elif macd_current < signal_current:
            cross_signal = "BEARISH"
        else:
            cross_signal = "NEUTRAL"
        
        hist_current = safe_float(histogram.iloc[-1])
        
        return macd_current, signal_current, hist_current, cross_signal
    except:
        return np.nan, np.nan, np.nan, "NEUTRAL"

def calculate_ema(df, period=200):
    """Calcula EMA"""
    if len(df) < period:
        return np.nan
    
    try:
        ema = df['Close'].ewm(span=period, adjust=False).mean()
        return safe_float(ema.iloc[-1])
    except:
        return np.nan

def analyze_technical_indicators(symbol, last_price):
    """Analiza indicadores tecnicos"""
    indicators = {
        'rsi_4h': np.nan,
        'rsi_signal': 'NEUTRAL',
        'macd_4h': np.nan,
        'macd_signal': 'NEUTRAL',
        'macd_histogram': np.nan,
        'ema200_1d': np.nan,
        'ema_signal': 'NEUTRAL',
        'total_score': 0.0
    }
    
    try:
        df_4h = yf.download(symbol, interval="1h", period="30d", progress=False, auto_adjust=True)
        
        if isinstance(df_4h.columns, pd.MultiIndex):
            df_4h.columns = df_4h.columns.get_level_values(0)
        
        if not df_4h.empty and len(df_4h) > 30:
            rsi_4h = calculate_rsi(df_4h, period=14)
            indicators['rsi_4h'] = rsi_4h
            
            if not np.isnan(rsi_4h):
                if rsi_4h < 30:
                    indicators['rsi_signal'] = 'OVERSOLD'
                    indicators['total_score'] += 1.0
                elif rsi_4h > 70:
                    indicators['rsi_signal'] = 'OVERBOUGHT'
                    indicators['total_score'] += 1.0
                elif 30 <= rsi_4h <= 40:
                    indicators['rsi_signal'] = 'BULLISH_ZONE'
                    indicators['total_score'] += 0.5
                elif 60 <= rsi_4h <= 70:
                    indicators['rsi_signal'] = 'BEARISH_ZONE'
                    indicators['total_score'] += 0.5
            
            macd_line, signal_line, histogram, macd_cross = calculate_macd(df_4h)
            indicators['macd_4h'] = macd_line
            indicators['macd_histogram'] = histogram
            indicators['macd_signal'] = macd_cross
            
            if macd_cross == "BULLISH_CROSS":
                indicators['total_score'] += 1.0
            elif macd_cross == "BEARISH_CROSS":
                indicators['total_score'] += 1.0
            elif macd_cross == "BULLISH":
                indicators['total_score'] += 0.5
            elif macd_cross == "BEARISH":
                indicators['total_score'] += 0.5
        
        df_1d = yf.download(symbol, interval="1d", period="1y", progress=False, auto_adjust=True)
        
        if isinstance(df_1d.columns, pd.MultiIndex):
            df_1d.columns = df_1d.columns.get_level_values(0)
        
        if not df_1d.empty and len(df_1d) > 200:
            ema200 = calculate_ema(df_1d, period=200)
            indicators['ema200_1d'] = ema200
            
            if not np.isnan(ema200):
                distance_pct = ((last_price - ema200) / ema200) * 100
                
                if last_price > ema200:
                    if distance_pct > 2:
                        indicators['ema_signal'] = 'ABOVE_STRONG'
                        indicators['total_score'] += 1.0
                    else:
                        indicators['ema_signal'] = 'ABOVE'
                        indicators['total_score'] += 0.5
                else:
                    if distance_pct < -2:
                        indicators['ema_signal'] = 'BELOW_STRONG'
                        indicators['total_score'] += 1.0
                    else:
                        indicators['ema_signal'] = 'BELOW'
                        indicators['total_score'] += 0.5
    
    except Exception:
        pass
    
    return indicators

# =======================================================================
# ESTRUCTURA DE MERCADO
# =======================================================================

def detect_consolidation(df_1d, lookback=20):
    """Detecta consolidacion"""
    if len(df_1d) < lookback:
        return False, 0.0, np.nan, np.nan
    
    recent = df_1d.iloc[-lookback:]
    
    highest = recent['High'].max()
    lowest = recent['Low'].min()
    
    range_pct = ((highest - lowest) / lowest) * 100
    
    is_consolidating = range_pct < 5.0
    
    resistance_level = highest
    support_level = lowest
    
    return is_consolidating, range_pct, resistance_level, support_level

def detect_accumulation(df_1d, lookback=60):
    """Detecta acumulacion"""
    if len(df_1d) < lookback:
        return False, "NONE", 0.0, [], ""
    
    recent = df_1d.iloc[-lookback:]
    
    price_trend = (recent['Close'].iloc[-1] - recent['Close'].iloc[0]) / recent['Close'].iloc[0]
    
    volume_first_half = recent['Volume'].iloc[:lookback//2].mean()
    volume_second_half = recent['Volume'].iloc[lookback//2:].mean()
    volume_decreasing = volume_second_half < volume_first_half
    
    last_20_days = recent.iloc[-20:]
    range_recent = ((last_20_days['High'].max() - last_20_days['Low'].min()) / 
                    last_20_days['Low'].min()) * 100
    forming_base = range_recent < 8.0
    
    rsi_values = []
    price_values = []
    for i in range(-10, 0, 2):
        rsi = calculate_rsi(df_1d.iloc[:len(df_1d)+i], period=14)
        price = safe_float(df_1d['Close'].iloc[i])
        if not np.isnan(rsi):
            rsi_values.append(rsi)
            price_values.append(price)
    
    bullish_divergence = False
    if len(rsi_values) >= 3 and len(price_values) >= 3:
        if (rsi_values[-1] > rsi_values[0] and price_values[-1] < price_values[0]):
            bullish_divergence = True
    
    accumulation_score = 0
    signals = []
    
    if price_trend < 0 or abs(price_trend) < 0.05:
        accumulation_score += 1
        signals.append("Precio zona baja")
    
    if volume_decreasing:
        accumulation_score += 1
        signals.append("Volumen decreciente")
    
    if forming_base:
        accumulation_score += 1.5
        signals.append("Formando base")
    
    if bullish_divergence:
        accumulation_score += 1.5
        signals.append("Divergencia RSI alcista")
    
    if accumulation_score >= 3.0:
        phase = "STRONG_ACCUMULATION"
        action = "ACUMULACION FUERTE - Preparar LONG"
    elif accumulation_score >= 2.0:
        phase = "POSSIBLE_ACCUMULATION"
        action = "Posible acumulacion - Monitorear"
    else:
        phase = "NONE"
        action = ""
    
    return accumulation_score >= 2.0, phase, accumulation_score, signals, action

def detect_distribution(df_1d, lookback=60):
    """Detecta distribucion"""
    if len(df_1d) < lookback:
        return False, "NONE", 0.0, [], ""
    
    recent = df_1d.iloc[-lookback:]
    
    price_trend = (recent['Close'].iloc[-1] - recent['Close'].iloc[0]) / recent['Close'].iloc[0]
    
    volume_first_half = recent['Volume'].iloc[:lookback//2].mean()
    volume_second_half = recent['Volume'].iloc[lookback//2:].mean()
    volume_decreasing = volume_second_half < volume_first_half
    
    last_20_days = recent.iloc[-20:]
    range_recent = ((last_20_days['High'].max() - last_20_days['Low'].min()) / 
                    last_20_days['Low'].min()) * 100
    forming_top = range_recent < 8.0
    
    rsi_values = []
    price_values = []
    for i in range(-10, 0, 2):
        rsi = calculate_rsi(df_1d.iloc[:len(df_1d)+i], period=14)
        price = safe_float(df_1d['Close'].iloc[i])
        if not np.isnan(rsi):
            rsi_values.append(rsi)
            price_values.append(price)
    
    bearish_divergence = False
    if len(rsi_values) >= 3 and len(price_values) >= 3:
        if (rsi_values[-1] < rsi_values[0] and price_values[-1] > price_values[0]):
            bearish_divergence = True
    
    distribution_score = 0
    signals = []
    
    if price_trend > 0 or abs(price_trend) < 0.05:
        distribution_score += 1
        signals.append("Precio zona alta")
    
    if volume_decreasing:
        distribution_score += 1
        signals.append("Volumen decreciente")
    
    if forming_top:
        distribution_score += 1.5
        signals.append("Formando techo")
    
    if bearish_divergence:
        distribution_score += 1.5
        signals.append("Divergencia RSI bajista")
    
    if distribution_score >= 3.0:
        phase = "STRONG_DISTRIBUTION"
        action = "DISTRIBUCION FUERTE - Preparar SHORT"
    elif distribution_score >= 2.0:
        phase = "POSSIBLE_DISTRIBUTION"
        action = "Posible distribucion - Monitorear"
    else:
        phase = "NONE"
        action = ""
    
    return distribution_score >= 2.0, phase, distribution_score, signals, action

def analyze_market_structure(df_1d, last_price):
    """Analisis de estructura de mercado"""
    is_consolidating, range_pct, resistance, support = detect_consolidation(df_1d)
    
    is_accum, accum_phase, accum_score, accum_signals, accum_action = detect_accumulation(df_1d)
    
    is_distrib, distrib_phase, distrib_score, distrib_signals, distrib_action = detect_distribution(df_1d)
    
    current_price = last_price
    
    if is_consolidating:
        dist_to_resistance = ((resistance - current_price) / current_price) * 100
        dist_to_support = ((current_price - support) / current_price) * 100
        
        if dist_to_resistance < 1.0:
            position = 'NEAR_RESISTANCE'
        elif dist_to_support < 1.0:
            position = 'NEAR_SUPPORT'
        else:
            position = 'MID_RANGE'
        
        if is_accum and accum_score > distrib_score:
            primary_phase = 'ACCUMULATION_IN_RANGE'
            recommendation = 'Consolidacion con acumulacion - ESPERAR breakout'
            confidence_adjustment = 0.8
        elif is_distrib and distrib_score > accum_score:
            primary_phase = 'DISTRIBUTION_IN_RANGE'
            recommendation = 'Consolidacion con distribucion - ESPERAR breakdown'
            confidence_adjustment = 0.8
        else:
            primary_phase = 'PURE_CONSOLIDATION'
            recommendation = 'CONSOLIDACION PURA - NO OPERAR'
            confidence_adjustment = 0.5
    
    elif is_accum and not is_distrib:
        primary_phase = accum_phase
        recommendation = accum_action
        confidence_adjustment = 1.2 if 'STRONG' in accum_phase else 1.1
        position = 'ACCUMULATION_ZONE'
        is_consolidating = False
        range_pct = 0.0
        resistance = np.nan
        support = np.nan
    
    elif is_distrib and not is_accum:
        primary_phase = distrib_phase
        recommendation = distrib_action
        confidence_adjustment = 1.2 if 'STRONG' in distrib_phase else 1.1
        position = 'DISTRIBUTION_ZONE'
        is_consolidating = False
        range_pct = 0.0
        resistance = np.nan
        support = np.nan
    
    else:
        primary_phase = 'TRENDING'
        recommendation = 'Tendencia clara - Operar normal'
        confidence_adjustment = 1.0
        position = 'TRENDING'
        is_consolidating = False
        range_pct = 0.0
        resistance = np.nan
        support = np.nan
    
    return {
        'primary_phase': primary_phase,
        'recommendation': recommendation,
        'confidence_adjustment': confidence_adjustment,
        'consolidation': {
            'is_consolidating': is_consolidating,
            'range_pct': range_pct,
            'resistance': resistance,
            'support': support,
            'position': position if is_consolidating else 'N/A'
        },
        'accumulation': {
            'detected': is_accum,
            'phase': accum_phase,
            'score': accum_score,
            'signals': accum_signals
        },
        'distribution': {
            'detected': is_distrib,
            'phase': distrib_phase,
            'score': distrib_score,
            'signals': distrib_signals
        }
    }

# =======================================================================
# DETECCION DE GAPS - MEJORADA
# =======================================================================

def find_all_gaps_comprehensive(df_1d, current_price, lookback_days=120):
    """
    Encuentra TODOS los gaps sin rellenar de forma mas exhaustiva
    Incluye gaps de 4H para mayor precision
    """
    gaps_above = []
    gaps_below = []
    
    if df_1d.empty or len(df_1d) < 3:
        return gaps_above, gaps_below
    
    # Analizar gaps en datos diarios
    df_recent = df_1d.iloc[-lookback_days:] if len(df_1d) >= lookback_days else df_1d
    
    for i in range(1, len(df_recent)):
        try:
            prev_close = safe_float(df_recent['Close'].iloc[i-1])
            prev_high = safe_float(df_recent['High'].iloc[i-1])
            prev_low = safe_float(df_recent['Low'].iloc[i-1])
            
            curr_open = safe_float(df_recent['Open'].iloc[i])
            curr_high = safe_float(df_recent['High'].iloc[i])
            curr_low = safe_float(df_recent['Low'].iloc[i])
            
            if any(np.isnan([prev_close, curr_open, prev_high, prev_low, curr_high, curr_low])):
                continue
            
            # Gap alcista (precio salta hacia arriba)
            if curr_low > prev_high:
                gap_bottom = prev_high
                gap_top = curr_low
                gap_filled = False
                
                # Verificar si el gap fue rellenado despues
                for j in range(i, len(df_recent)):
                    check_low = safe_float(df_recent['Low'].iloc[j])
                    if not np.isnan(check_low) and check_low <= gap_bottom:
                        gap_filled = True
                        break
                
                if not gap_filled:
                    gap_mid = (gap_bottom + gap_top) / 2
                    gap_size_pct = ((gap_top - gap_bottom) / gap_bottom) * 100
                    
                    gap_info = {
                        'level': gap_mid,
                        'bottom': gap_bottom,
                        'top': gap_top,
                        'type': 'GAP_UP',
                        'age_days': len(df_recent) - i,
                        'size_pct': gap_size_pct,
                        'strength': 'STRONG' if gap_size_pct > 2.0 else 'MEDIUM' if gap_size_pct > 1.0 else 'WEAK'
                    }
                    
                    if gap_mid > current_price:
                        gaps_above.append(gap_info)
                    elif gap_mid < current_price:
                        gaps_below.append(gap_info)
            
            # Gap bajista (precio salta hacia abajo)
            elif curr_high < prev_low:
                gap_top = prev_low
                gap_bottom = curr_high
                gap_filled = False
                
                # Verificar si el gap fue rellenado despues
                for j in range(i, len(df_recent)):
                    check_high = safe_float(df_recent['High'].iloc[j])
                    if not np.isnan(check_high) and check_high >= gap_top:
                        gap_filled = True
                        break
                
                if not gap_filled:
                    gap_mid = (gap_bottom + gap_top) / 2
                    gap_size_pct = ((gap_top - gap_bottom) / gap_bottom) * 100
                    
                    gap_info = {
                        'level': gap_mid,
                        'bottom': gap_bottom,
                        'top': gap_top,
                        'type': 'GAP_DOWN',
                        'age_days': len(df_recent) - i,
                        'size_pct': gap_size_pct,
                        'strength': 'STRONG' if gap_size_pct > 2.0 else 'MEDIUM' if gap_size_pct > 1.0 else 'WEAK'
                    }
                    
                    if gap_mid > current_price:
                        gaps_above.append(gap_info)
                    elif gap_mid < current_price:
                        gaps_below.append(gap_info)
        
        except Exception:
            continue
    
    # Ordenar por cercania al precio actual
    gaps_above = sorted(gaps_above, key=lambda x: x['level'])
    gaps_below = sorted(gaps_below, key=lambda x: x['level'], reverse=True)
    
    return gaps_above, gaps_below

def detect_cme_gap_improved(df_1d, df_4h, last_price):
    """
    Deteccion mejorada de gaps CME con validacion multiple
    Revisa gaps recientes (ultimos 7 dias) y confirma direccion
    """
    if df_1d.empty or len(df_1d) < 5:
        return "NO_GAP", np.nan, []
    
    GAP_THRESHOLD_PCT = 0.3  # Reducido de 0.5% a 0.3% para detectar mas gaps
    recent_gaps = []
    
    # Revisar ultimos 7 dias para gaps
    for i in range(-7, 0):
        try:
            if abs(i) > len(df_1d):
                continue
                
            prev_close = safe_float(df_1d['Close'].iloc[i-1])
            prev_high = safe_float(df_1d['High'].iloc[i-1])
            prev_low = safe_float(df_1d['Low'].iloc[i-1])
            
            curr_open = safe_float(df_1d['Open'].iloc[i])
            curr_low = safe_float(df_1d['Low'].iloc[i])
            curr_high = safe_float(df_1d['High'].iloc[i])
            
            if any(np.isnan([prev_close, curr_open, prev_high, prev_low, curr_high, curr_low])):
                continue
            
            # Gap alcista sin rellenar
            if curr_low > prev_high:
                gap_size_pct = ((curr_low - prev_high) / prev_high) * 100
                if gap_size_pct > GAP_THRESHOLD_PCT:
                    # Verificar que no se haya rellenado
                    gap_filled = False
                    for j in range(i, 0):
                        check_low = safe_float(df_1d['Low'].iloc[j])
                        if not np.isnan(check_low) and check_low <= prev_high:
                            gap_filled = True
                            break
                    
                    if not gap_filled and prev_high < last_price:
                        recent_gaps.append({
                            'level': prev_high,
                            'type': 'GAP_UP',
                            'size_pct': gap_size_pct,
                            'age_days': abs(i),
                            'direction': 'DOWN_TO_FILL'
                        })
            
            # Gap bajista sin rellenar
            elif curr_high < prev_low:
                gap_size_pct = ((prev_low - curr_high) / curr_high) * 100
                if gap_size_pct > GAP_THRESHOLD_PCT:
                    # Verificar que no se haya rellenado
                    gap_filled = False
                    for j in range(i, 0):
                        check_high = safe_float(df_1d['High'].iloc[j])
                        if not np.isnan(check_high) and check_high >= prev_low:
                            gap_filled = True
                            break
                    
                    if not gap_filled and prev_low > last_price:
                        recent_gaps.append({
                            'level': prev_low,
                            'type': 'GAP_DOWN',
                            'size_pct': gap_size_pct,
                            'age_days': abs(i),
                            'direction': 'UP_TO_FILL'
                        })
        
        except Exception:
            continue
    
    if not recent_gaps:
        return "NO_GAP", np.nan, []
    
    # Ordenar por cercania al precio actual
    recent_gaps = sorted(recent_gaps, key=lambda x: abs(x['level'] - last_price))
    
    # Tomar el gap mas cercano
    closest_gap = recent_gaps[0]
    
    if closest_gap['direction'] == 'DOWN_TO_FILL':
        return "SHORT_TO_FILL", closest_gap['level'], recent_gaps
    elif closest_gap['direction'] == 'UP_TO_FILL':
        return "LONG_TO_FILL", closest_gap['level'], recent_gaps
    
    return "NO_GAP", np.nan, []

# =======================================================================
# VALIDACION DE NIVELES
# =======================================================================

def validate_levels(decision, entry_p, sl_p, tp1_p, tp2_p, atr, last_price):
    """Valida niveles TP/SL"""
    if np.isnan(entry_p) or np.isnan(atr):
        return entry_p, sl_p, tp1_p, tp2_p
    
    if "SHORT" in decision:
        if not np.isnan(sl_p) and sl_p <= entry_p:
            sl_p = entry_p + atr * 1.5
        
        if not np.isnan(tp1_p) and tp1_p >= entry_p:
            tp1_p = entry_p - atr * 1.0
        if not np.isnan(tp2_p):
            if tp2_p >= entry_p:
                tp2_p = entry_p - atr * 2.0
            if not np.isnan(tp1_p) and tp2_p >= tp1_p:
                tp2_p = tp1_p - atr * 1.0
    
    elif "LONG" in decision:
        if not np.isnan(sl_p) and sl_p >= entry_p:
            sl_p = entry_p - atr * 1.5
        
        if not np.isnan(tp1_p) and tp1_p <= entry_p:
            tp1_p = entry_p + atr * 1.0
        if not np.isnan(tp2_p):
            if tp2_p <= entry_p:
                tp2_p = entry_p + atr * 2.0
            if not np.isnan(tp1_p) and tp2_p <= tp1_p:
                tp2_p = tp1_p + atr * 1.0
    
    return entry_p, sl_p, tp1_p, tp2_p

# =======================================================================
# ANALISIS PRINCIPAL - MEJORADO
# =======================================================================

def analyze_pre_ny(symbol):
    
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    
    try:
        data_5m = yf.download(symbol, interval="5m", period="7d", progress=False, auto_adjust=True)
        data_4h = yf.download(symbol, interval="1h", period="30d", progress=False, auto_adjust=True)
        
        if isinstance(data_5m.columns, pd.MultiIndex):
            data_5m.columns = data_5m.columns.get_level_values(0)
        if isinstance(data_4h.columns, pd.MultiIndex):
            data_4h.columns = data_4h.columns.get_level_values(0)
        
        if data_5m.empty or not all(col in data_5m.columns for col in required_cols):
             return f"Error de Datos 5m para {symbol}: DataFrame vacio o incompleto."
        data_5m = data_5m.dropna(subset=required_cols)
    except Exception as e:
        return f"Error de Conexion/API (5m) para {symbol}: {e}"

    PP, R1, S1, data_1d, error_1d = calculate_pivot_points(symbol) 
    if error_1d:
        return f"Error de Pivotes (1D) para {symbol}: {error_1d}"
    
    if data_5m.empty or np.isnan(PP) or len(data_5m) < 3: 
        return f"Datos insuficientes para {symbol}."

    try:
        if data_5m.index.tz is not None:
            data_5m_ny = data_5m.tz_convert(NY_TIMEZONE)
        else:
            data_5m_ny = data_5m.tz_localize('UTC').tz_convert(NY_TIMEZONE)
        
        last_candle_time = data_5m_ny.index[-1]
        next_candle_time = last_candle_time + pd.Timedelta(minutes=5)
        
        last_candle_tijuana = last_candle_time.astimezone(TIJUANA_TIMEZONE)
        next_candle_tijuana = next_candle_time.astimezone(TIJUANA_TIMEZONE)
        
        last_timestamp = last_candle_tijuana.strftime('%Y-%m-%d %H:%M:%S')
        entry_time_display = next_candle_tijuana.strftime('%H:%M:%S')
        
        last_price = safe_float(data_5m["Close"].iloc[-1])
        if np.isnan(last_price): raise ValueError("Precio final invalido.")
    except Exception as e:
        return f"Error al extraer precio/tiempo para {symbol}: {e}"
    
    atr = safe_atr(data_5m)
    high_volume = check_high_volume(data_5m) 
    
    # DETECCION MEJORADA DE GAPS
    gap_signal, gap_level, all_recent_gaps = detect_cme_gap_improved(data_1d, data_4h, last_price)
    
    indicators = analyze_technical_indicators(symbol, last_price)
    market_structure = analyze_market_structure(data_1d, last_price)
    
    # BUSQUEDA EXHAUSTIVA DE GAPS
    gaps_above, gaps_below = find_all_gaps_comprehensive(data_1d, last_price, lookback_days=120)
    
    R2_hist = find_historical_level(data_1d, last_price, is_resistance=True)
    S2_hist = find_historical_level(data_1d, last_price, is_resistance=False)
    
    strong_resistance = not np.isnan(R2_hist) and abs(last_price - R2_hist) / last_price < 0.01
    strong_support = not np.isnan(S2_hist) and abs(last_price - S2_hist) / last_price < 0.01

    decision = "NO_OPERAR (Sin Señal Clara)"
    confidence = 0
    entry_p, sl_p, tp1_p, tp2_p, tp3_p = np.nan, np.nan, np.nan, np.nan, np.nan
    indicator_score = 0.0
    max_score = 6  # Aumentado para incluir analisis de gaps multiples
    
    ATR_TOLERANCE = (atr * 0.5 if not np.isnan(atr) and atr > 0 else last_price * 0.001)
    
    # LOGICA DE DECISION MEJORADA CON GAPS MULTIPLES
    if gap_signal == "SHORT_TO_FILL":
        confidence += 2.0  # Mayor peso inicial por gap confirmado
        
        sl_p = R1 if R1 > last_price else (R2_hist if not np.isnan(R2_hist) and R2_hist > last_price else last_price + atr * 1.5)
        tp1_p = gap_level
        tp2_p = S1
        
        # TP3 basado en gaps adicionales debajo
        if gaps_below and len(gaps_below) > 0:
            strong_gaps = [g for g in gaps_below if g['strength'] in ['STRONG', 'MEDIUM'] and g['level'] < tp2_p]
            if strong_gaps:
                tp3_p = strong_gaps[0]['level']
            elif not np.isnan(S2_hist) and S2_hist < tp2_p:
                tp3_p = S2_hist
            else:
                tp3_p = tp2_p - atr * 2.0
        else:
            tp3_p = S2_hist if not np.isnan(S2_hist) and S2_hist < tp2_p else tp2_p - atr * 2.0
        
        # Validar direccion con precio vs PP
        price_above_pp = last_price > PP
        if price_above_pp:
            confidence += 1.0
        else:
            confidence -= 0.5  # Penalizar si el precio no apoya la direccion
        
        # Indicadores tecnicos
        if indicators['rsi_signal'] in ['OVERBOUGHT', 'BEARISH_ZONE']:
            indicator_score += 1.0 if indicators['rsi_signal'] == 'OVERBOUGHT' else 0.5
        else:
            indicator_score -= 0.5  # Penalizar RSI contrario
        
        if indicators['macd_signal'] in ['BEARISH_CROSS', 'BEARISH']:
            indicator_score += 1.0 if indicators['macd_signal'] == 'BEARISH_CROSS' else 0.5
        elif indicators['macd_signal'] in ['BULLISH_CROSS', 'BULLISH']:
            indicator_score -= 0.5  # Penalizar MACD contrario
        
        if indicators['ema_signal'] in ['BELOW_STRONG', 'BELOW']:
            indicator_score += 0.5
        
        confidence += indicator_score
        confidence += 1 if high_volume else 0
        
        # Confianza minima mas estricta
        min_confidence = 3.0
        
        if confidence >= min_confidence and indicator_score >= 0:  # Requiere indicadores positivos
            if last_price >= PP or abs(last_price - PP) < ATR_TOLERANCE:
                entry_p = last_price
                decision = "SHORT_FUERTE (Activacion Inmediata)" if confidence >= 4.5 else "SHORT_MODERADO (Activacion Inmediata)"
            else:
                entry_p = PP 
                decision = "SHORT_PENDIENTE (Esperar Retroceso a PP)"
        else:
            decision = f"NO_OPERAR (Gap SHORT detectado pero confianza baja: {confidence:.1f}/6.0)"

    elif gap_signal == "LONG_TO_FILL":
        confidence += 2.0  # Mayor peso inicial por gap confirmado
        
        sl_p = S1 if S1 < last_price else (S2_hist if not np.isnan(S2_hist) and S2_hist < last_price else last_price - atr * 1.5)
        tp1_p = gap_level
        tp2_p = R1
        
        # TP3 basado en gaps adicionales arriba
        if gaps_above and len(gaps_above) > 0:
            strong_gaps = [g for g in gaps_above if g['strength'] in ['STRONG', 'MEDIUM'] and g['level'] > tp2_p]
            if strong_gaps:
                tp3_p = strong_gaps[0]['level']
            elif not np.isnan(R2_hist) and R2_hist > tp2_p:
                tp3_p = R2_hist
            else:
                tp3_p = tp2_p + atr * 2.0
        else:
            tp3_p = R2_hist if not np.isnan(R2_hist) and R2_hist > tp2_p else tp2_p + atr * 2.0

        # Validar direccion con precio vs PP
        price_below_pp = last_price < PP
        if price_below_pp:
            confidence += 1.0
        else:
            confidence -= 0.5  # Penalizar si el precio no apoya la direccion
        
        # Indicadores tecnicos
        if indicators['rsi_signal'] in ['OVERSOLD', 'BULLISH_ZONE']:
            indicator_score += 1.0 if indicators['rsi_signal'] == 'OVERSOLD' else 0.5
        else:
            indicator_score -= 0.5  # Penalizar RSI contrario
        
        if indicators['macd_signal'] in ['BULLISH_CROSS', 'BULLISH']:
            indicator_score += 1.0 if indicators['macd_signal'] == 'BULLISH_CROSS' else 0.5
        elif indicators['macd_signal'] in ['BEARISH_CROSS', 'BEARISH']:
            indicator_score -= 0.5  # Penalizar MACD contrario
        
        if indicators['ema_signal'] in ['ABOVE_STRONG', 'ABOVE']:
            indicator_score += 0.5
        
        confidence += indicator_score
        confidence += 1 if high_volume else 0
        
        # Confianza minima mas estricta
        min_confidence = 3.0
        
        if confidence >= min_confidence and indicator_score >= 0:  # Requiere indicadores positivos
            if last_price <= PP or abs(last_price - PP) < ATR_TOLERANCE:
                entry_p = last_price
                decision = "LONG_FUERTE (Activacion Inmediata)" if confidence >= 4.5 else "LONG_MODERADO (Activacion Inmediata)"
            else:
                entry_p = PP
                decision = "LONG_PENDIENTE (Esperar Retroceso a PP)"
        else:
            decision = f"NO_OPERAR (Gap LONG detectado pero confianza baja: {confidence:.1f}/6.0)"
    
    elif gap_signal == "NO_GAP":
        # Analizar gaps historicos cercanos como niveles de operacion
        if gaps_above and abs(gaps_above[0]['level'] - last_price) / last_price < 0.02:
            # Precio cerca de gap arriba = posible rechazo SHORT
            confidence += 1.5
            sl_p = gaps_above[0]['top'] + atr * 0.5
            tp1_p = PP if PP < last_price else last_price - atr * 2.0
            tp2_p = S1
            tp3_p = gaps_below[0]['level'] if gaps_below else S2_hist
            
            if indicators['rsi_signal'] in ['OVERBOUGHT', 'BEARISH_ZONE']:
                indicator_score += 1.0
            if indicators['macd_signal'] in ['BEARISH_CROSS', 'BEARISH']:
                indicator_score += 1.0
            
            confidence += indicator_score
            
            if confidence >= 3.0:
                entry_p = last_price
                decision = "SHORT_GAP_HISTORICO (Resistencia)"
        
        elif gaps_below and abs(gaps_below[0]['level'] - last_price) / last_price < 0.02:
            # Precio cerca de gap abajo = posible rebote LONG
            confidence += 1.5
            sl_p = gaps_below[0]['bottom'] - atr * 0.5
            tp1_p = PP if PP > last_price else last_price + atr * 2.0
            tp2_p = R1
            tp3_p = gaps_above[0]['level'] if gaps_above else R2_hist
            
            if indicators['rsi_signal'] in ['OVERSOLD', 'BULLISH_ZONE']:
                indicator_score += 1.0
            if indicators['macd_signal'] in ['BULLISH_CROSS', 'BULLISH']:
                indicator_score += 1.0
            
            confidence += indicator_score
            
            if confidence >= 3.0:
                entry_p = last_price
                decision = "LONG_GAP_HISTORICO (Soporte)"
        
        elif strong_resistance and last_price >= R2_hist:
            confidence += 1.5
            sl_p = R2_hist + atr * 1.0
            tp1_p = PP
            tp2_p = S1
            tp3_p = S2_hist if not np.isnan(S2_hist) else S1 - atr * 2.0
            
            if indicators['rsi_signal'] in ['OVERBOUGHT', 'BEARISH_ZONE']:
                indicator_score += 1.0
            if indicators['macd_signal'] in ['BEARISH_CROSS', 'BEARISH']:
                indicator_score += 1.0
            
            confidence += indicator_score + (1 if high_volume else 0)
            
            if confidence >= 3.5:
                entry_p = last_price
                decision = "SHORT_RESISTENCIA (Nivel Historico)"
        
        elif strong_support and last_price <= S2_hist:
            confidence += 1.5
            sl_p = S2_hist - atr * 1.0
            tp1_p = PP
            tp2_p = R1
            tp3_p = R2_hist if not np.isnan(R2_hist) else R1 + atr * 2.0
            
            if indicators['rsi_signal'] in ['OVERSOLD', 'BULLISH_ZONE']:
                indicator_score += 1.0
            if indicators['macd_signal'] in ['BULLISH_CROSS', 'BULLISH']:
                indicator_score += 1.0

            confidence += indicator_score + (1 if high_volume else 0)
            
            if confidence >= 3.5:
                entry_p = last_price
                decision = "LONG_SOPORTE (Nivel Historico)"
    
    entry_p, sl_p, tp1_p, tp2_p = validate_levels(decision, entry_p, sl_p, tp1_p, tp2_p, atr, last_price)
    
    if "SHORT" in decision and not np.isnan(tp3_p):
        if not np.isnan(tp2_p) and tp3_p >= tp2_p:
            tp3_p = tp2_p - atr * 1.0
    elif "LONG" in decision and not np.isnan(tp3_p):
        if not np.isnan(tp2_p) and tp3_p <= tp2_p:
            tp3_p = tp2_p + atr * 1.0
    
    confidence_before_structure = confidence
    confidence *= market_structure['confidence_adjustment']
    confidence_pct = min(100, (confidence / max_score) * 100)
    
    if "PENDIENTE" in decision and not np.isnan(entry_p):
        entry_display = f"{entry_p:.4f} (Esperar en PP)"
        entry_type = "Limit Order en PP"
    elif decision.endswith("Inmediata)") and not np.isnan(entry_p):
        entry_display = f"{entry_p:.4f}"
        entry_type = "Market Order"
    else:
        entry_display = "N/A"
        entry_type = "Sin Operacion"
    
    sl_display = f"{sl_p:.4f}" if not np.isnan(sl_p) else "N/A"
    tp1_display = f"{tp1_p:.4f}" if not np.isnan(tp1_p) else "N/A"
    tp2_display = f"{tp2_p:.4f}" if not np.isnan(tp2_p) else "N/A"
    tp3_display = f"{tp3_p:.4f}" if not np.isnan(tp3_p) else "N/A"
    
    # Informacion de gaps mejorada
    gap_info_display = ""
    if gap_signal != "NO_GAP":
        gap_info_display = f"**{gap_signal}** @ {gap_level:.4f}\n"
        if all_recent_gaps and len(all_recent_gaps) > 1:
            gap_info_display += f"   └─ Gaps adicionales: {len(all_recent_gaps)-1} detectados\n"
            for i, g in enumerate(all_recent_gaps[1:3], 1):  # Mostrar hasta 2 gaps adicionales
                gap_info_display += f"      {i}. {g['type']} @ {g['level']:.4f} ({g['age_days']}d, {g['size_pct']:.2f}%)\n"
    else:
        gap_info_display = "NO_GAP (Sin gaps recientes sin rellenar)\n"
    
    rsi_display = f"{indicators['rsi_4h']:.1f}" if not np.isnan(indicators['rsi_4h']) else "N/A"
    rsi_status = indicators['rsi_signal']
    
    macd_display = f"{indicators['macd_histogram']:.4f}" if not np.isnan(indicators['macd_histogram']) else "N/A"
    macd_status = indicators['macd_signal']
    
    ema_display = f"{indicators['ema200_1d']:.2f}" if not np.isnan(indicators['ema200_1d']) else "N/A"
    ema_status = indicators['ema_signal']
    ema_distance = ""
    if not np.isnan(indicators['ema200_1d']):
        dist_pct = ((last_price - indicators['ema200_1d']) / indicators['ema200_1d']) * 100
        ema_distance = f" ({dist_pct:+.1f}%)"
    
    # Mostrar gaps relevantes segun direccion
    gaps_info = "\n### GAPS HISTORICOS DETECTADOS\n"
    if "SHORT" in decision and gaps_below:
        gaps_info += f"Soportes (Objetivos Abajo):\n"
        for i, g in enumerate(gaps_below[:3], 1):
            gaps_info += f"  {i}. {g['level']:.4f} ({g['strength']}, {g['age_days']}d, {g['size_pct']:.2f}%) - Rango: [{g['bottom']:.4f} - {g['top']:.4f}]\n"
    elif "LONG" in decision and gaps_above:
        gaps_info += f"Resistencias (Objetivos Arriba):\n"
        for i, g in enumerate(gaps_above[:3], 1):
            gaps_info += f"  {i}. {g['level']:.4f} ({g['strength']}, {g['age_days']}d, {g['size_pct']:.2f}%) - Rango: [{g['bottom']:.4f} - {g['top']:.4f}]\n"
    else:
        if gaps_below:
            gaps_info += f"Gaps Abajo: {len(gaps_below)} | Mas cercano: {gaps_below[0]['level']:.4f} ({abs((gaps_below[0]['level']-last_price)/last_price*100):.2f}% away)\n"
        if gaps_above:
            gaps_info += f"Gaps Arriba: {len(gaps_above)} | Mas cercano: {gaps_above[0]['level']:.4f} ({abs((gaps_above[0]['level']-last_price)/last_price*100):.2f}% away)\n"
    
    gap_level_points = 2.0 if gap_signal != "NO_GAP" else (1.5 if (strong_resistance or strong_support) else 0.0)
    
    structure_points = 0.0
    if (gap_signal == "SHORT_TO_FILL" and last_price > PP) or \
       (gap_signal == "LONG_TO_FILL" and last_price < PP) or \
       (decision.startswith("SHORT") and last_price > PP) or \
       (decision.startswith("LONG") and last_price < PP):
        structure_points = 1.0
    
    structure_info = f"""
### ESTRUCTURA DE MERCADO
* Fase Detectada: {market_structure['primary_phase']}
* Recomendacion: {market_structure['recommendation']}
* Ajuste Confianza: {market_structure['confidence_adjustment']:.1f}x (Base: {confidence_before_structure:.1f} -> Ajustada: {confidence:.1f})
"""
    
    if market_structure['consolidation']['is_consolidating']:
        consol = market_structure['consolidation']
        structure_info += f"""
[CONSOLIDACION] Detectada:
   - Rango: {consol['range_pct']:.2f}%
   - Resistencia: {consol['resistance']:.2f}
   - Soporte: {consol['support']:.2f}
   - Posicion: {consol['position']}
"""
    
    if market_structure['accumulation']['detected']:
        accum = market_structure['accumulation']
        structure_info += f"""
[ACUMULACION] Detectada:
   - Score: {accum['score']:.1f}/5.0
   - Fase: {accum['phase']}
   - Senales: {', '.join(accum['signals']) if accum['signals'] else 'N/A'}
"""
    
    if market_structure['distribution']['detected']:
        distrib = market_structure['distribution']
        structure_info += f"""
[DISTRIBUCION] Detectada:
   - Score: {distrib['score']:.1f}/5.0
   - Fase: {distrib['phase']}
   - Senales: {', '.join(distrib['signals']) if distrib['signals'] else 'N/A'}
"""
    
    return f"""
=====================================
ANALISIS DE TRADING | {symbol}
VERSION 3.0 - DETECCION GAPS MEJORADA
=====================================

### DECISION RAPIDA
| Confianza: {confidence_pct:.0f}% | Senal: {decision} |
| Proxima Entrada (5m): {entry_time_display} TJ |

---

### NIVELES OPERABLES
| **ENTRADA:** {entry_display} | Tipo: {entry_type} |
| SL : {sl_display} | Nivel de maximo riesgo |
| TP1: {tp1_display} | Cierre del Gap / Nivel 1 |
| TP2: {tp2_display} | Nivel de Pivote R1/S1 |
| TP3: {tp3_display} | Gap Historico / Extension |

---

### CONTEXTO CLAVE
* Precio Actual: {last_price:.4f} (Hora: {last_timestamp} TJ)
* Gap Activo: 
{gap_info_display}
* Punto Pivote (PP): {PP:.4f}
* Resistencia 1 (R1): {R1:.4f} | Distancia: {((R1 - last_price) / last_price * 100):+.2f}%
* Soporte 1 (S1): {S1:.4f} | Distancia: {((S1 - last_price) / last_price * 100):+.2f}%
{gaps_info}
---
{structure_info}
---

### INDICADORES TECNICOS (HTF)
* RSI 4H: {rsi_display} -> {rsi_status}
* MACD 4H: {macd_display} -> {macd_status}
* EMA200 1D: {ema_display}{ema_distance} -> {ema_status}

### CONFIRMACIONES
* Puntuacion Total: {confidence:.1f}/{max_score:.1f}
  * Gap/Nivel: {gap_level_points:.1f} pts.
  * Estructura: {structure_points:.1f} pts.
  * Indicadores: {indicator_score:.1f} pts.
  * Volumen: {'[SI]' if high_volume else '[NO]'} (1.0 pt)

[MEJORAS v3.0]
✓ Deteccion de gaps ultimos 7 dias (vs 1 dia anterior)
✓ Umbral reducido: 0.3% (vs 0.5%) para detectar mas gaps
✓ Validacion de direccion con precio vs PP
✓ Penalizacion de indicadores contrarios a la senal
✓ Confianza minima aumentada: 3.0/6.0
✓ Analisis de gaps historicos como niveles de soporte/resistencia
✓ Scoring mas estricto para evitar senales falsas
"""


# =======================================================================
# EJECUCION
# =======================================================================
if __name__ == "__main__":
    symbols_to_analyze = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD"] 

    print("--- ANALISIS PRE-NY v3.0 (Deteccion de Gaps Mejorada) ---\n")
    print("MEJORAS: Revision de gaps ultimos 7 dias + validacion cruzada con indicadores\n")
    for s in symbols_to_analyze:
        try:
            print(analyze_pre_ny(s))
        except Exception as e:
            print(f"Error al analizar {s}: {type(e).__name__} - {e}\n")
