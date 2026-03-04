"""
Correlaciones y Sentimiento Crypto
VERSION 3.0 - Sin APIs de pago:
  ✓ CCXT (Binance) para precios, volumen y correlaciones
  ✓ CryptoCompare solo para histoday (gratis, sin key)
  ✓ Fear & Greed Index (alternative.me) — gratis, sin key, sentimiento global
  ✓ Sentimiento por moneda derivado 100% de datos CCXT (momentum, volumen, RSI)
  ✗ Removido: CryptoCompare social stats (requería API key de pago)
"""

import ccxt
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import pytz
import warnings
import logging
import time

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# =======================================================================
# CONFIGURACION
# =======================================================================

TIJUANA_TZ = pytz.timezone('America/Tijuana')
NY_TZ      = pytz.timezone('America/New_York')

CRYPTOS = {
    'BTC/USDT': {'nombre': 'Bitcoin',      'cc_symbol': 'BTC'},
    'ETH/USDT': {'nombre': 'Ethereum',     'cc_symbol': 'ETH'},
    'SOL/USDT': {'nombre': 'Solana',       'cc_symbol': 'SOL'},
    'BNB/USDT': {'nombre': 'Binance Coin', 'cc_symbol': 'BNB'},
    'XRP/USDT': {'nombre': 'Ripple',       'cc_symbol': 'XRP'},
}

# =======================================================================
# MODULO 0: CLIENTE CCXT
# =======================================================================

def get_exchange():
    return ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'spot'}})


def fetch_ohlcv_df(exchange, symbol, timeframe='1h', limit=200):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not ohlcv:
            return pd.DataFrame()
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df.set_index('timestamp', inplace=True)
        return df.astype(float)
    except Exception as e:
        logger.error(f"CCXT [{symbol} {timeframe}]: {e}")
        return pd.DataFrame()


# =======================================================================
# MODULO 1: FEAR & GREED INDEX — alternative.me (100% gratis, sin key)
# =======================================================================

class FearGreedIndex:
    """
    API pública de alternative.me — sin autenticación, sin límites estrictos.
    Retorna el índice Fear & Greed del mercado crypto (0 = Miedo Extremo, 100 = Avaricia Extrema).
    Útil como contexto de sentimiento general del mercado.
    """
    URL = "https://api.alternative.me/fng/?limit=2&format=json"

    def __init__(self):
        self.cache = None

    def get(self):
        """Obtiene Fear & Greed actual y del día anterior"""
        if self.cache:
            return self.cache
        try:
            r = requests.get(self.URL, timeout=10)
            r.raise_for_status()
            data = r.json().get('data', [])
            if not data:
                return None

            hoy   = data[0]
            ayer  = data[1] if len(data) > 1 else data[0]

            result = {
                'value':            int(hoy['value']),
                'classification':   hoy['value_classification'],   # p.ej. "Greed", "Fear"
                'value_yesterday':  int(ayer['value']),
                'change':           int(hoy['value']) - int(ayer['value']),
            }
            self.cache = result
            return result
        except Exception as e:
            logger.warning(f"Fear & Greed API error: {e}")
            return None

    def emoji(self, value):
        if value >= 75: return "🟢🟢"   # Avaricia Extrema
        if value >= 55: return "🟢"      # Avaricia
        if value >= 45: return "⚪"      # Neutral
        if value >= 25: return "🔴"      # Miedo
        return "🔴🔴"                    # Miedo Extremo

    def bias(self, value):
        """Sesgo de mercado derivado del índice"""
        if value >= 65: return 'ALCISTA'
        if value <= 35: return 'BAJISTA'
        return 'NEUTRAL'


# =======================================================================
# MODULO 2: SENTIMIENTO POR MONEDA (derivado de CCXT — sin API externa)
# =======================================================================

class CoinSentimentAnalyzer:
    """
    Calcula sentimiento individual por moneda usando únicamente
    datos de Binance via CCXT: precio, volumen, momentum y RSI.
    Sin dependencia de APIs de terceros — 100% gratuito.
    """

    def __init__(self, exchange):
        self.exchange = exchange
        self.cache = {}

    def _rsi(self, series, period=14):
        if len(series) < period + 1:
            return np.nan
        delta = series.diff()
        gain  = delta.where(delta > 0, 0).rolling(period).mean()
        loss  = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs    = gain / loss
        return float((100 - 100 / (1 + rs)).iloc[-1])

    def get_coin_data(self, symbol):
        """Descarga velas 1h (7 días) y calcula métricas de sentimiento"""
        if symbol in self.cache:
            return self.cache[symbol]

        df = fetch_ohlcv_df(self.exchange, symbol, timeframe='1h', limit=168)
        if df.empty or len(df) < 24:
            self.cache[symbol] = None
            return None

        try:
            precio_actual   = float(df['Close'].iloc[-1])
            precio_ayer     = float(df['Close'].iloc[-24])    # hace 24 velas 1h
            precio_semana   = float(df['Close'].iloc[0])      # inicio del período

            change_24h = (precio_actual - precio_ayer)  / precio_ayer  * 100
            change_7d  = (precio_actual - precio_semana) / precio_semana * 100

            # Volatilidad: desviación estándar de retornos horarios (%)
            returns    = df['Close'].pct_change().dropna()
            volatility = float(returns.std() * 100)

            # Volumen: ratio últimas 4h vs promedio de las 7d
            vol_reciente = float(df['Volume'].iloc[-4:].mean())
            vol_promedio = float(df['Volume'].mean())
            volume_ratio = vol_reciente / vol_promedio if vol_promedio > 0 else 1.0

            # RSI 14 períodos sobre cierres horarios
            rsi = self._rsi(df['Close'], period=14)

            # Posición en rango 7d
            ath_7d = float(df['High'].max())
            atl_7d = float(df['Low'].min())
            rango  = ath_7d - atl_7d
            pos_rango = (precio_actual - atl_7d) / rango if rango > 0 else 0.5

            # Presión compradora: % de velas alcistas en últimas 24h
            ultimas_24 = df.iloc[-24:]
            velas_alcistas = (ultimas_24['Close'] > ultimas_24['Open']).sum()
            buy_pressure = velas_alcistas / len(ultimas_24)

            result = {
                'precio':       precio_actual,
                'change_24h':   change_24h,
                'change_7d':    change_7d,
                'volatility':   volatility,
                'volume_ratio': volume_ratio,
                'rsi':          rsi,
                'ath_7d':       ath_7d,
                'atl_7d':       atl_7d,
                'pos_rango':    pos_rango,
                'buy_pressure': buy_pressure,
                'high_24h':     float(df['High'].iloc[-24:].max()),
                'low_24h':      float(df['Low'].iloc[-24:].min()),
            }
            self.cache[symbol] = result
            return result

        except Exception as e:
            logger.error(f"Error calculando sentimiento {symbol}: {e}")
            self.cache[symbol] = None
            return None

    def predict_direction(self, symbol, fear_greed_value=50):
        """
        Scoring de dirección basado en datos CCXT + contexto Fear & Greed.
        Umbrales optimizados para generar señales en mercados normales.
        """
        resultado = {
            'direccion':    'NEUTRAL',
            'probabilidad': 50.0,
            'change_24h':   0.0,
            'change_7d':    0.0,
            'volatility':   0.0,
            'volume_signal': 'NORMAL',
            'rsi':          np.nan,
            'razones':      [],
        }

        d = self.get_coin_data(symbol)
        if not d:
            resultado['razones'] = ['Datos CCXT no disponibles']
            return resultado

        score_a, score_b, razones = 0, 0, []

        # 1. Momentum 24h
        c24 = d['change_24h']
        if   c24 > 1.5:  score_a += 2; razones.append(f"Momentum alcista 24h: +{c24:.1f}%")
        elif c24 < -1.5: score_b += 2; razones.append(f"Momentum bajista 24h: {c24:.1f}%")
        elif c24 > 0.5:  score_a += 1; razones.append(f"Momentum alcista leve 24h: +{c24:.1f}%")
        elif c24 < -0.5: score_b += 1; razones.append(f"Momentum bajista leve 24h: {c24:.1f}%")

        # 2. Tendencia 7d
        c7 = d['change_7d']
        if   c7 > 5:  score_a += 2; razones.append(f"Tendencia alcista 7d: +{c7:.1f}%")
        elif c7 < -5: score_b += 2; razones.append(f"Tendencia bajista 7d: {c7:.1f}%")
        elif c7 > 2:  score_a += 1; razones.append(f"Tendencia alcista leve 7d: +{c7:.1f}%")
        elif c7 < -2: score_b += 1; razones.append(f"Tendencia bajista leve 7d: {c7:.1f}%")

        # 3. Volumen (ratio últimas 4h vs promedio 7d)
        vr = d['volume_ratio']
        if   vr > 1.2 and c24 > 0: score_a += 1; razones.append(f"Volumen compra elevado ({vr:.1f}x)"); resultado['volume_signal'] = 'ALTO_COMPRA'
        elif vr > 1.2 and c24 < 0: score_b += 1; razones.append(f"Volumen venta elevado ({vr:.1f}x)");  resultado['volume_signal'] = 'ALTO_VENTA'

        # 4. RSI
        rsi = d['rsi']
        if not np.isnan(rsi):
            if   rsi < 30: score_a += 2; razones.append(f"RSI sobrevendido ({rsi:.1f}) — rebote probable")
            elif rsi > 70: score_b += 2; razones.append(f"RSI sobrecomprado ({rsi:.1f}) — corrección probable")
            elif rsi < 40: score_a += 1; razones.append(f"RSI zona alcista ({rsi:.1f})")
            elif rsi > 60: score_b += 1; razones.append(f"RSI zona bajista ({rsi:.1f})")

        # 5. Posición en rango 7d
        pr = d['pos_rango']
        if   pr > 0.85: score_b += 1; razones.append(f"Precio cerca del máximo semanal ({pr:.0%} del rango)")
        elif pr < 0.15: score_a += 1; razones.append(f"Precio cerca del mínimo semanal ({pr:.0%} del rango)")

        # 6. Presión compradora (velas alcistas últimas 24h)
        bp = d['buy_pressure']
        if   bp > 0.60: score_a += 1; razones.append(f"Alta presión compradora ({bp:.0%} velas alcistas)")
        elif bp < 0.40: score_b += 1; razones.append(f"Alta presión vendedora ({bp:.0%} velas alcistas)")

        # 7. Contexto Fear & Greed global
        if fear_greed_value >= 65:   score_a += 1; razones.append(f"Mercado en Avaricia (F&G: {fear_greed_value})")
        elif fear_greed_value <= 35: score_b += 1; razones.append(f"Mercado en Miedo (F&G: {fear_greed_value})")

        # Calcular resultado
        total = score_a + score_b
        prob  = 50 + (max(score_a, score_b) / total * 40) if total > 0 else 50.0

        if   score_a > score_b: direccion = 'ALCISTA'
        elif score_b > score_a: direccion = 'BAJISTA'
        else:                   direccion = 'NEUTRAL'

        resultado.update({
            'direccion':     direccion,
            'probabilidad':  prob,
            'change_24h':    c24,
            'change_7d':     c7,
            'volatility':    d['volatility'],
            'rsi':           rsi,
            'razones':       razones if razones else ['Sin señales claras'],
        })
        return resultado

    def find_support_resistance(self, symbol, current_price):
        """Niveles S/R basados en datos 7d de CCXT + Fibonacci"""
        d = self.cache.get(symbol)
        if not d:
            d = self.get_coin_data(symbol)
        if not d:
            return []

        levels = []
        h24, l24 = d['high_24h'], d['low_24h']
        ath, atl  = d['ath_7d'], d['atl_7d']

        if h24 > current_price:
            dist = (h24 - current_price) / current_price * 100
            levels.append({'price': h24, 'distance_pct': dist, 'type': 'RESISTANCE',
                           'label': 'High 24h', 'strength': '🔴 FUERTE' if dist < 3 else '🟡 MEDIO'})

        if l24 < current_price:
            dist = (l24 - current_price) / current_price * 100
            levels.append({'price': l24, 'distance_pct': dist, 'type': 'SUPPORT',
                           'label': 'Low 24h', 'strength': '🔴 FUERTE' if abs(dist) < 3 else '🟡 MEDIO'})

        if ath > current_price and atl < current_price:
            for fib in [0.236, 0.382, 0.5, 0.618, 0.786]:
                lvl  = atl + (ath - atl) * fib
                dist = (lvl - current_price) / current_price * 100
                if 0.1 < abs(dist) < 15:
                    levels.append({'price': lvl, 'distance_pct': dist,
                                   'type': 'RESISTANCE' if lvl > current_price else 'SUPPORT',
                                   'label': f'Fib {fib:.3f}', 'strength': '🟡 MEDIO'})

        return sorted(levels, key=lambda x: abs(x['distance_pct']))[:5]


# =======================================================================
# MODULO 3: CORRELACIONES (CCXT)
# =======================================================================

class CryptoCorrelationAnalyzer:
    def __init__(self, cryptos_dict, exchange):
        self.cryptos = cryptos_dict
        self.exchange = exchange
        self.datos_cache = {}

    def calcular_correlaciones(self):
        retornos = pd.DataFrame()
        print("📊 Descargando datos históricos desde Binance (CCXT)...")

        for symbol, info in self.cryptos.items():
            df = fetch_ohlcv_df(self.exchange, symbol, timeframe='1h', limit=168)
            if df is not None and not df.empty:
                retornos[info['nombre']] = df['Close'].pct_change()
                self.datos_cache[symbol] = df
                print(f"  ✅ {info['nombre']}: {len(df)} velas 1h")
            else:
                print(f"  ❌ {info['nombre']}: Sin datos")
            time.sleep(0.3)

        if len(retornos.columns) < 2:
            return None, None

        correlaciones = retornos.corr()
        precios = {s: float(d['Close'].iloc[-1]) for s, d in self.datos_cache.items()}
        return correlaciones, precios

    def interpretar_correlaciones(self, corr_matrix):
        if corr_matrix is None:
            return []
        pares = []
        cols = corr_matrix.columns
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                pares.append((cols[i], cols[j], corr_matrix.iloc[i, j]))
        pares.sort(key=lambda x: abs(x[2]), reverse=True)

        insights = []
        for c1, c2, v in pares[:3]:
            if   v > 0.85:      insights.append(f"🔗 {c1} y {c2} se mueven juntas ({v:.3f})")
            elif v > 0.7:       insights.append(f"↗️ {c1} y {c2} alta correlación ({v:.3f})")
            elif v > 0.5:       insights.append(f"➡️ {c1} y {c2} correlación moderada ({v:.3f})")
            elif v < -0.7:      insights.append(f"🔄 {c1} y {c2} inversamente correlacionadas ({v:.3f})")
            elif abs(v) < 0.3:  insights.append(f"🔀 {c1} y {c2} independientes ({v:.3f})")
            else:               insights.append(f"↔️ {c1} y {c2} correlación baja ({v:.3f})")
        return insights


# =======================================================================
# ORQUESTADOR
# =======================================================================

class PreNYAnalyzer:
    def __init__(self):
        self.exchange      = get_exchange()
        self.corr_analyzer = CryptoCorrelationAnalyzer(CRYPTOS, self.exchange)
        self.sentiment     = CoinSentimentAnalyzer(self.exchange)
        self.fear_greed    = FearGreedIndex()

    def ejecutar_analisis(self):
        ahora_ny = datetime.now(NY_TZ)
        print("=" * 80)
        print(f"🚀 ANALISIS PRE-SESION NY | {ahora_ny.strftime('%Y-%m-%d %H:%M:%S')} EST")
        print(f"   Precios: Binance (CCXT) | Sentimiento: CCXT + Fear & Greed Index")
        print("=" * 80)

        # Fear & Greed Index (una sola llamada para todo el análisis)
        fg = self.fear_greed.get()
        if fg:
            emoji   = self.fear_greed.emoji(fg['value'])
            tendencia = "↑" if fg['change'] > 0 else "↓" if fg['change'] < 0 else "→"
            print(f"\n{emoji} FEAR & GREED INDEX: {fg['value']} — {fg['classification']}")
            print(f"   Ayer: {fg['value_yesterday']} | Cambio: {tendencia}{abs(fg['change'])} pts")
            fg_value = fg['value']
        else:
            print("\n⚠️  Fear & Greed Index no disponible")
            fg_value = 50  # neutral como fallback

        # Correlaciones
        correlaciones, precios = self.corr_analyzer.calcular_correlaciones()
        if not precios:
            print("❌ No se pudieron obtener precios.")
            return

        if correlaciones is not None:
            print("\n📈 Matriz de Correlaciones (Retornos 7d — velas 1h Binance):")
            print(correlaciones.to_string(float_format=lambda x: f'{x:.3f}'))
            print("\n   Interpretación:")
            for i in self.corr_analyzer.interpretar_correlaciones(correlaciones):
                print(f"    • {i}")

        # Análisis individual
        print("\n" + "=" * 80)
        print("🔍 ANÁLISIS INDIVIDUAL POR CRIPTOMONEDA")
        print("=" * 80)

        for symbol, info in CRYPTOS.items():
            if symbol not in precios:
                continue

            p = precios[symbol]
            print(f"\n{'─' * 80}")
            print(f"🪙 {info['nombre'].upper()} ({symbol}) | Precio: ${p:,.4f} USDT")
            print(f"{'─' * 80}")

            pred = self.sentiment.predict_direction(symbol, fear_greed_value=fg_value)

            emoji_dir = "🟢" if pred['direccion'] == 'ALCISTA' else "🔴" if pred['direccion'] == 'BAJISTA' else "⚪"
            rsi_str   = f"{pred['rsi']:.1f}" if not np.isnan(pred['rsi']) else "N/A"
            print(f"  {emoji_dir} Sentimiento: {pred['direccion']} ({pred['probabilidad']:.1f}%)")
            print(f"  📊 Volatilidad: {pred['volatility']:.2f}% | Cambio 24h: {pred['change_24h']:+.2f}%")
            print(f"  💰 Cambio 7d: {pred['change_7d']:+.2f}% | Vol: {pred['volume_signal']} | RSI: {rsi_str}")
            print(f"  📝 Señales:")
            for r in pred['razones']:
                print(f"     • {r}")

            levels = self.sentiment.find_support_resistance(symbol, p)
            if levels:
                print(f"\n  🎯 NIVELES CLAVE:")
                for i, lvl in enumerate(levels[:3]):
                    print(f"    {i+1}. ${lvl['price']:,.4f} ({lvl['distance_pct']:+.2f}%) "
                          f"— {lvl['type']} {lvl['label']} {lvl['strength']}")

        print("\n" + "=" * 80)
        print("✅ Análisis completado")
        print("=" * 80)


# =======================================================================
# EJECUCIÓN
# =======================================================================

if __name__ == "__main__":
    analyzer = PreNYAnalyzer()
    analyzer.ejecutar_analisis()
