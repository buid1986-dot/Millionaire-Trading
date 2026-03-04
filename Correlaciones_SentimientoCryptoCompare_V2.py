"""
Correlaciones y Sentimiento Crypto
VERSION 2.0 - Optimizaciones aplicadas:
  ✓ CCXT (Binance) en lugar de yfinance — datos más confiables y en tiempo real
  ✓ Umbrales reducidos: change_24h 3%→1.5%, change_7d 10%→5%
  ✓ Scoring de momentum leve agregado (0.5% y 2%)
  ✓ Señal de posición en rango 7d (cerca de ATH/ATL semanal)
  ✓ get_social_stats() integrado en predict_direction()
"""

import ccxt
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
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
NY_TZ = pytz.timezone('America/New_York')

# Criptomonedas a analizar
# 'ccxt_symbol': símbolo para Binance via CCXT (USDT pair)
# 'cc_symbol': símbolo para CryptoCompare API
CRYPTOS = {
    'BTC/USDT': {'nombre': 'Bitcoin',      'cc_symbol': 'BTC'},
    'ETH/USDT': {'nombre': 'Ethereum',     'cc_symbol': 'ETH'},
    'SOL/USDT': {'nombre': 'Solana',       'cc_symbol': 'SOL'},
    'BNB/USDT': {'nombre': 'Binance Coin', 'cc_symbol': 'BNB'},
    'XRP/USDT': {'nombre': 'Ripple',       'cc_symbol': 'XRP'},
}

# =======================================================================
# MODULO 0: CLIENTE CCXT (BINANCE — SIN API KEY)
# =======================================================================

def get_exchange():
    """Crea instancia de Binance via CCXT (solo datos públicos, sin API key)"""
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    return exchange


def fetch_ohlcv_df(exchange, symbol, timeframe='1h', limit=200):
    """
    Descarga velas OHLCV de Binance y retorna DataFrame.
    symbol   : 'BTC/USDT'
    timeframe: '1m','5m','15m','1h','4h','1d'
    limit    : número de velas (máx 1000 en Binance)
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
        logger.error(f"CCXT error [{symbol} {timeframe}]: {e}")
        return pd.DataFrame()


# =======================================================================
# MODULO 1: CORRELACIONES (ahora con CCXT)
# =======================================================================

class CryptoCorrelationAnalyzer:
    def __init__(self, cryptos_dict, exchange):
        self.cryptos = cryptos_dict
        self.exchange = exchange
        self.datos_cache = {}

    def descargar_datos(self, symbol, timeframe='1h', limit=168):
        """
        Descarga ~7 días de velas 1h (168 velas) desde Binance.
        Más confiable que yfinance para crypto 24/7.
        """
        df = fetch_ohlcv_df(self.exchange, symbol, timeframe=timeframe, limit=limit)
        if df.empty:
            logger.warning(f"Sin datos CCXT para {symbol}")
        return df if not df.empty else None

    def calcular_correlaciones(self):
        """Calcula matriz de correlaciones entre criptomonedas"""
        retornos = pd.DataFrame()
        print("📊 Descargando datos históricos desde Binance (CCXT)...")

        for symbol, info in self.cryptos.items():
            datos = self.descargar_datos(symbol)
            if datos is not None and len(datos) > 0:
                retornos[info['nombre']] = datos['Close'].pct_change()
                self.datos_cache[symbol] = datos
                print(f"  ✅ {info['nombre']}: {len(datos)} velas 1h")
            else:
                print(f"  ❌ {info['nombre']}: Sin datos disponibles")
            time.sleep(0.3)  # respeto rate limit Binance

        if len(retornos.columns) < 2:
            logger.warning("No hay suficientes datos para calcular correlaciones")
            return None, None

        correlaciones = retornos.corr()
        precios = {
            symbol: float(datos['Close'].iloc[-1])
            for symbol, datos in self.datos_cache.items()
        }
        return correlaciones, precios

    def interpretar_correlaciones(self, corr_matrix):
        """Interpreta la matriz de correlaciones y genera insights"""
        if corr_matrix is None:
            return []

        insights = []
        all_correlations = []

        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_val = corr_matrix.iloc[i, j]
                c1, c2 = corr_matrix.columns[i], corr_matrix.columns[j]
                all_correlations.append((c1, c2, corr_val))

        all_correlations.sort(key=lambda x: abs(x[2]), reverse=True)

        for c1, c2, corr_val in all_correlations[:3]:
            if corr_val > 0.85:
                insights.append({'interpretacion': f"🔗 {c1} y {c2} se mueven juntas ({corr_val:.3f})"})
            elif corr_val > 0.7:
                insights.append({'interpretacion': f"↗️ {c1} y {c2} alta correlación ({corr_val:.3f})"})
            elif corr_val > 0.5:
                insights.append({'interpretacion': f"➡️ {c1} y {c2} correlación moderada ({corr_val:.3f})"})
            elif corr_val < -0.7:
                insights.append({'interpretacion': f"🔄 {c1} y {c2} inversamente correlacionadas ({corr_val:.3f})"})
            elif abs(corr_val) < 0.3:
                insights.append({'interpretacion': f"🔀 {c1} y {c2} independientes ({corr_val:.3f})"})
            else:
                insights.append({'interpretacion': f"↔️ {c1} y {c2} correlación baja ({corr_val:.3f})"})

        return insights


# =======================================================================
# MODULO 2: CRYPTOCOMPARE API
# =======================================================================

class CryptoCompareAnalyzer:
    """
    ✅ Sin API Key necesaria para endpoints básicos
    ✅ Rate limit: 100,000 llamadas/mes (gratis)
    ✅ Datos de sentimiento y volumen más completos que exchange
    """

    BASE_URL = "https://min-api.cryptocompare.com/data"

    def __init__(self):
        self.timeout = 15
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/json'
        })
        self.cache = {}

    def _get(self, endpoint, params=None):
        try:
            url = f"{self.BASE_URL}{endpoint}"
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            if data.get('Response') == 'Error':
                logger.warning(f"CryptoCompare error: {data.get('Message')}")
                return None
            return data
        except requests.RequestException as e:
            logger.debug(f"Error en CryptoCompare {endpoint}: {e}")
            return None

    def test_connection(self):
        data = self._get("/price", {"fsym": "BTC", "tsyms": "USD"})
        return data is not None

    def get_historical_data(self, symbol, limit=7):
        data = self._get("/v2/histoday", {
            "fsym": symbol,
            "tsym": "USD",
            "limit": limit
        })
        if data and 'Data' in data and 'Data' in data['Data']:
            return data['Data']['Data']
        return []

    def _get_coin_id(self, symbol):
        coin_ids = {
            'BTC': '1182', 'ETH': '7605', 'SOL': '935284',
            'BNB': '4614', 'XRP': '5031'
        }
        return coin_ids.get(symbol, symbol)

    def get_social_stats(self, symbol):
        """Obtiene estadísticas sociales y sentiment"""
        data = self._get("/social/coin/latest", {"coinId": self._get_coin_id(symbol)})
        if data and 'Data' in data:
            return data['Data']
        return None

    def get_coin_data(self, symbol):
        """Obtiene datos completos con CACHE"""
        if symbol in self.cache:
            return self.cache[symbol]

        hist_data = self.get_historical_data(symbol, limit=7)
        if not hist_data or len(hist_data) < 2:
            self.cache[symbol] = None
            return None

        try:
            latest    = hist_data[-1]
            yesterday = hist_data[-2] if len(hist_data) > 1 else hist_data[-1]
            week_ago  = hist_data[0]

            price_current   = latest['close']
            price_yesterday = yesterday['close']
            price_week_ago  = week_ago['close']

            change_24h = ((price_current - price_yesterday) / price_yesterday * 100) if price_yesterday > 0 else 0
            change_7d  = ((price_current - price_week_ago)  / price_week_ago  * 100) if price_week_ago  > 0 else 0

            closes    = [d['close']    for d in hist_data]
            returns   = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
            volatility = np.std(returns) * 100 if returns else 0

            avg_volume    = np.mean([d['volumeto'] for d in hist_data])
            latest_volume = latest['volumeto']
            volume_ratio  = (latest_volume / avg_volume) if avg_volume > 0 else 1.0

            ath = max([d['high'] for d in hist_data])
            atl = min([d['low']  for d in hist_data])

            result = {
                'price':          price_current,
                'price_change_24h': change_24h,
                'price_change_7d':  change_7d,
                'volatility':       volatility,
                'volume_24h':       latest_volume,
                'volume_ratio':     volume_ratio,
                'ath_7d':           ath,
                'atl_7d':           atl,
                'high_24h':         latest['high'],
                'low_24h':          latest['low'],
            }

            # ── Enriquecer con datos sociales si están disponibles ──────
            social = self.get_social_stats(symbol)
            if social:
                result['social_score']   = social.get('CryptoCompare', {}).get('Points', 0)
                result['reddit_posts']   = social.get('Reddit', {}).get('posts_per_day', 0)
                result['twitter_volume'] = social.get('Twitter', {}).get('statuses', 0)

            self.cache[symbol] = result
            return result

        except Exception as e:
            logger.error(f"Error procesando datos de {symbol}: {e}")
            self.cache[symbol] = None
            return None

    # ------------------------------------------------------------------
    # PREDICCION DE DIRECCIÓN — UMBRALES OPTIMIZADOS
    # ------------------------------------------------------------------
    def predict_direction(self, symbol, current_price):
        """
        Predice dirección con umbrales ajustados para generar más señales:
          • Momentum 24h:  ±1.5% fuerte (antes ±3%),  ±0.5% leve (nuevo)
          • Tendencia 7d:  ±5%  fuerte (antes ±10%), ±2%  leve (nuevo)
          • Volumen:       1.2x  (antes 1.5x)
          • Posición rango 7d: NUEVO — cerca de ATH/ATL semanal
          • Social score:  NUEVO — integrado desde get_social_stats()
        """
        resultado = {
            'direccion':        'NEUTRAL',
            'probabilidad':     50.0,
            'price_change_24h': 0.0,
            'price_change_7d':  0.0,
            'volatility':       0.0,
            'volume_signal':    'NORMAL',
            'razones':          [],
        }

        coin_data = self.get_coin_data(symbol)
        if not coin_data:
            resultado['razones'] = ['Datos no disponibles']
            return resultado

        score_alcista = 0
        score_bajista = 0
        razones = []

        # 1. Momentum 24h — umbrales reducidos + nivel leve
        change_24h = coin_data['price_change_24h']
        if change_24h > 1.5:
            score_alcista += 2
            razones.append(f"Momentum alcista 24h: +{change_24h:.1f}%")
        elif change_24h < -1.5:
            score_bajista += 2
            razones.append(f"Momentum bajista 24h: {change_24h:.1f}%")
        elif change_24h > 0.5:
            score_alcista += 1
            razones.append(f"Momentum alcista leve 24h: +{change_24h:.1f}%")
        elif change_24h < -0.5:
            score_bajista += 1
            razones.append(f"Momentum bajista leve 24h: {change_24h:.1f}%")

        # 2. Tendencia 7d — umbrales reducidos + nivel leve
        change_7d = coin_data['price_change_7d']
        if change_7d > 5:
            score_alcista += 2
            razones.append(f"Tendencia alcista 7d: +{change_7d:.1f}%")
        elif change_7d < -5:
            score_bajista += 2
            razones.append(f"Tendencia bajista 7d: {change_7d:.1f}%")
        elif change_7d > 2:
            score_alcista += 1
            razones.append(f"Tendencia alcista leve 7d: +{change_7d:.1f}%")
        elif change_7d < -2:
            score_bajista += 1
            razones.append(f"Tendencia bajista leve 7d: {change_7d:.1f}%")

        # 3. Volumen — umbral reducido a 1.2x
        volume_ratio = coin_data['volume_ratio']
        if volume_ratio > 1.2 and change_24h > 0:
            score_alcista += 1
            razones.append(f"Volumen de compra elevado ({volume_ratio:.1f}x)")
            resultado['volume_signal'] = 'ALTO_COMPRA'
        elif volume_ratio > 1.2 and change_24h < 0:
            score_bajista += 1
            razones.append(f"Volumen de venta elevado ({volume_ratio:.1f}x)")
            resultado['volume_signal'] = 'ALTO_VENTA'

        # 4. NUEVO: Posición en rango 7d
        ath = coin_data['ath_7d']
        atl = coin_data['atl_7d']
        rango = ath - atl
        if rango > 0:
            pos_rel = (current_price - atl) / rango
            if pos_rel > 0.85:
                score_bajista += 1
                razones.append(f"Precio cerca del máximo semanal ({pos_rel:.0%} del rango)")
            elif pos_rel < 0.15:
                score_alcista += 1
                razones.append(f"Precio cerca del mínimo semanal ({pos_rel:.0%} del rango)")

        # 5. NUEVO: Social score (si disponible)
        if 'social_score' in coin_data and coin_data['social_score'] > 0:
            social = coin_data['social_score']
            if social > 5000:
                score_alcista += 1
                razones.append(f"Alto interés social (score: {social:,})")

        # 6. Volatilidad informativa
        volatility = coin_data['volatility']
        if volatility > 5:
            razones.append(f"Alta volatilidad ({volatility:.1f}%)")

        # Calcular probabilidad
        total_score = score_alcista + score_bajista
        if total_score > 0:
            prob = 50 + (max(score_alcista, score_bajista) / total_score) * 40
        else:
            prob = 50.0

        # Dirección
        if score_alcista > score_bajista:
            direccion = 'ALCISTA'
        elif score_bajista > score_alcista:
            direccion = 'BAJISTA'
        else:
            direccion = 'NEUTRAL'

        resultado.update({
            'direccion':        direccion,
            'probabilidad':     prob,
            'price_change_24h': change_24h,
            'price_change_7d':  change_7d,
            'volatility':       volatility,
            'razones':          razones if razones else ['Sin señales claras'],
        })
        return resultado

    def find_support_resistance(self, symbol, current_price):
        """Niveles de soporte/resistencia basados en datos 7d + Fibonacci"""
        coin_data = self.cache.get(symbol)
        if not coin_data:
            coin_data = self.get_coin_data(symbol)
            if not coin_data:
                return []

        ath      = coin_data['ath_7d']
        atl      = coin_data['atl_7d']
        high_24h = coin_data['high_24h']
        low_24h  = coin_data['low_24h']

        levels = []

        if high_24h > current_price:
            dist = ((high_24h - current_price) / current_price) * 100
            levels.append({'price': high_24h, 'distance_pct': dist,
                           'type': 'RESISTANCE', 'label': 'High 24h',
                           'strength': '🔴 FUERTE' if dist < 3 else '🟡 MEDIO'})

        if low_24h < current_price:
            dist = ((low_24h - current_price) / current_price) * 100
            levels.append({'price': low_24h, 'distance_pct': dist,
                           'type': 'SUPPORT', 'label': 'Low 24h',
                           'strength': '🔴 FUERTE' if abs(dist) < 3 else '🟡 MEDIO'})

        if ath > current_price and atl < current_price:
            for fib in [0.236, 0.382, 0.5, 0.618, 0.786]:
                lvl = atl + ((ath - atl) * fib)
                dist = ((lvl - current_price) / current_price) * 100
                if abs(dist) < 15 and abs(dist) > 0.1:
                    levels.append({'price': lvl, 'distance_pct': dist,
                                   'type': 'RESISTANCE' if lvl > current_price else 'SUPPORT',
                                   'label': f'Fib {fib:.3f}', 'strength': '🟡 MEDIO'})

        return sorted(levels, key=lambda x: abs(x['distance_pct']))[:5]


# =======================================================================
# ORQUESTADOR
# =======================================================================

class PreNYAnalyzer:
    def __init__(self):
        self.exchange = get_exchange()
        self.corr_analyzer = CryptoCorrelationAnalyzer(CRYPTOS, self.exchange)
        self.cc_analyzer   = CryptoCompareAnalyzer()

    def ejecutar_analisis(self):
        ahora_ny = datetime.now(NY_TZ)
        print("=" * 80)
        print(f"🚀 ANALISIS PRE-SESION NY | {ahora_ny.strftime('%Y-%m-%d %H:%M:%S')} EST")
        print(f"   Fuente de precios: Binance (CCXT) | Sentimiento: CryptoCompare")
        print("=" * 80)

        cc_disponible = self.cc_analyzer.test_connection()
        if not cc_disponible:
            print("⚠️  No se pudo conectar a CryptoCompare API")

        # Pre-cargar datos CryptoCompare
        if cc_disponible:
            print("\n🔄 Precargando datos de mercado (CryptoCompare)...")
            for i, (symbol, info) in enumerate(CRYPTOS.items()):
                print(f"   [{i+1}/{len(CRYPTOS)}] {info['nombre']}...", end='', flush=True)
                result = self.cc_analyzer.get_coin_data(info['cc_symbol'])
                print(" ✅" if result else " ❌")
                if i < len(CRYPTOS) - 1:
                    time.sleep(1.5)

        # Correlaciones (datos de Binance via CCXT)
        correlaciones, precios = self.corr_analyzer.calcular_correlaciones()
        if not precios:
            print("❌ No se pudo obtener datos de precios.")
            return

        if correlaciones is not None:
            print("\n📈 Matriz de Correlaciones (Retornos 7d — velas 1h Binance):")
            print(correlaciones.to_string(float_format=lambda x: f'{x:.3f}'))
            print("\n   Interpretación:")
            for insight in self.corr_analyzer.interpretar_correlaciones(correlaciones)[:3]:
                print(f"    • {insight['interpretacion']}")

        # Análisis individual
        print("\n" + "=" * 80)
        print("🔍 ANÁLISIS INDIVIDUAL POR CRIPTOMONEDA")
        print("=" * 80)

        for symbol, info in CRYPTOS.items():
            if symbol not in precios:
                continue

            p_actual = precios[symbol]
            print(f"\n{'─' * 80}")
            print(f"🪙 {info['nombre'].upper()} ({symbol}) | Precio: ${p_actual:,.4f} USDT")
            print(f"{'─' * 80}")

            if cc_disponible:
                pred = self.cc_analyzer.predict_direction(info['cc_symbol'], p_actual)

                emoji = "🟢" if pred['direccion'] == 'ALCISTA' else "🔴" if pred['direccion'] == 'BAJISTA' else "⚪"
                print(f"  {emoji} Sentiment: {pred['direccion']} ({pred['probabilidad']:.1f}%)")
                print(f"  📊 Volatilidad: {pred['volatility']:.2f}% | Cambio 24h: {pred['price_change_24h']:+.2f}%")
                print(f"  💰 Cambio 7d: {pred['price_change_7d']:+.2f}% | Vol: {pred['volume_signal']}")

                if pred['razones']:
                    for r in pred['razones']:
                        print(f"    • {r}")

                levels = self.cc_analyzer.find_support_resistance(info['cc_symbol'], p_actual)
                if levels:
                    print(f"\n  🎯 NIVELES CLAVE:")
                    for i, lvl in enumerate(levels[:3]):
                        print(f"    {i+1}. ${lvl['price']:,.4f} ({lvl['distance_pct']:+.2f}%) "
                              f"- {lvl['type']} {lvl['label']} - {lvl['strength']}")
                else:
                    print(f"  ℹ️  No hay niveles significativos detectados")
            else:
                print(f"  ⚪ CryptoCompare no disponible — solo precio Binance: ${p_actual:,.4f}")

        print("\n" + "=" * 80)
        print("✅ Análisis completado")
        print("=" * 80)


# =======================================================================
# EJECUCION
# =======================================================================

if __name__ == "__main__":
    analyzer = PreNYAnalyzer()
    analyzer.ejecutar_analisis()
