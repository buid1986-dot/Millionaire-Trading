import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import pytz
import warnings
import logging

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# =======================================================================
# CONFIGURACION
# =======================================================================

TIJUANA_TZ = pytz.timezone('America/Tijuana')
NY_TZ = pytz.timezone('America/New_York')

# Criptomonedas a analizar (símbolos para CryptoCompare)
CRYPTOS = {
    'BTC-USD': {'nombre': 'Bitcoin', 'symbol': 'BTC'},
    'ETH-USD': {'nombre': 'Ethereum', 'symbol': 'ETH'},
    'SOL-USD': {'nombre': 'Solana', 'symbol': 'SOL'},
    'BNB-USD': {'nombre': 'Binance Coin', 'symbol': 'BNB'},
    'XRP-USD': {'nombre': 'Ripple', 'symbol': 'XRP'}
}

# =======================================================================
# MODULO 1: DESCARGA DE DATOS Y CORRELACIONES
# =======================================================================

class CryptoCorrelationAnalyzer:
    def __init__(self, cryptos_dict):
        self.cryptos = cryptos_dict
        self.datos_cache = {}
    
    def descargar_datos(self, ticker, periodo='7d', intervalo='1h'):
        """Descarga datos históricos de Yahoo Finance con fallback"""
        try:
            datos = yf.download(ticker, period=periodo, interval=intervalo, 
                                progress=False, auto_adjust=True)
            
            if datos.empty:
                alt_ticker = ticker.replace("-", "") + "=X"
                datos = yf.download(alt_ticker, period=periodo, interval=intervalo, 
                                    progress=False, auto_adjust=True)
            
            if datos.empty:
                logger.warning(f"No se obtuvieron datos para {ticker}")
                return None
            
            if isinstance(datos.columns, pd.MultiIndex):
                datos = datos.droplevel(1, axis=1)
            
            return datos
        except Exception as e:
            logger.error(f"Error descargando {ticker}: {e}")
            return None
    
    def calcular_correlaciones(self):
        """Calcula matriz de correlaciones entre criptomonedas"""
        retornos = pd.DataFrame()
        print("📊 Descargando datos históricos de Yahoo Finance...")
        
        for ticker, info in self.cryptos.items():
            datos = self.descargar_datos(ticker)
            if datos is not None and len(datos) > 0:
                retornos[info['nombre']] = datos['Close'].pct_change()
                self.datos_cache[ticker] = datos
                print(f"  ✅ {info['nombre']}: {len(datos)} velas")
            else:
                print(f"  ❌ {info['nombre']}: Sin datos disponibles")
        
        if len(retornos.columns) < 2:
            logger.warning("No hay suficientes datos para calcular correlaciones")
            return None, None
        
        correlaciones = retornos.corr()
        precios = {
            ticker: float(datos['Close'].iloc[-1]) 
            for ticker, datos in self.datos_cache.items()
        }
        return correlaciones, precios

    def interpretar_correlaciones(self, corr_matrix):
        """Interpreta la matriz de correlaciones y genera insights"""
        if corr_matrix is None: 
            return []
        
        insights = []
        all_correlations = []
        
        # Recopilar todas las correlaciones (sin diagonal)
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_val = corr_matrix.iloc[i, j]
                crypto1, crypto2 = corr_matrix.columns[i], corr_matrix.columns[j]
                all_correlations.append((crypto1, crypto2, corr_val))
        
        # Ordenar por valor absoluto de correlación (más fuerte primero)
        all_correlations.sort(key=lambda x: abs(x[2]), reverse=True)
        
        # Generar insights para las 3 correlaciones más significativas
        for crypto1, crypto2, corr_val in all_correlations[:3]:
            if corr_val > 0.85:
                insights.append({
                    'interpretacion': f"🔗 {crypto1} y {crypto2} se mueven juntas ({corr_val:.3f})"
                })
            elif corr_val > 0.7:
                insights.append({
                    'interpretacion': f"↗️ {crypto1} y {crypto2} alta correlación ({corr_val:.3f})"
                })
            elif corr_val > 0.5:
                insights.append({
                    'interpretacion': f"➡️ {crypto1} y {crypto2} correlación moderada ({corr_val:.3f})"
                })
            elif corr_val < -0.7:
                insights.append({
                    'interpretacion': f"🔄 {crypto1} y {crypto2} inversamente correlacionadas ({corr_val:.3f})"
                })
            elif abs(corr_val) < 0.3:
                insights.append({
                    'interpretacion': f"🔀 {crypto1} y {crypto2} independientes ({corr_val:.3f})"
                })
            else:
                insights.append({
                    'interpretacion': f"↔️ {crypto1} y {crypto2} correlación baja ({corr_val:.3f})"
                })
        
        return insights

# =======================================================================
# MODULO 2: CRYPTOCOMPARE API (MAS CONFIABLE QUE COINGECKO)
# =======================================================================

class CryptoCompareAnalyzer:
    """
    Analizador usando CryptoCompare API
    ✅ Sin API Key necesaria para endpoints básicos
    ✅ Rate limit: 100,000 llamadas/mes (gratis)
    ✅ No bloqueado en Google Colab/GitHub
    ✅ Datos más confiables que CoinGecko
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
        """Helper para peticiones GET"""
        try:
            url = f"{self.BASE_URL}{endpoint}"
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # CryptoCompare retorna errores en el JSON
            if data.get('Response') == 'Error':
                logger.warning(f"CryptoCompare error: {data.get('Message')}")
                return None
            
            return data
        except requests.RequestException as e:
            logger.debug(f"Error en CryptoCompare {endpoint}: {e}")
            return None
    
    def test_connection(self):
        """Prueba conexión a CryptoCompare"""
        data = self._get("/price", {"fsym": "BTC", "tsyms": "USD"})
        return data is not None
    
    def get_price(self, symbol):
        """Obtiene precio actual de una crypto"""
        data = self._get("/price", {"fsym": symbol, "tsyms": "USD"})
        if data and 'USD' in data:
            return data['USD']
        return 0
    
    def get_historical_data(self, symbol, limit=7):
        """Obtiene datos históricos diarios"""
        data = self._get("/v2/histoday", {
            "fsym": symbol,
            "tsym": "USD",
            "limit": limit
        })
        
        if data and 'Data' in data and 'Data' in data['Data']:
            return data['Data']['Data']
        return []
    
    def get_social_stats(self, symbol):
        """Obtiene estadísticas sociales y sentiment"""
        data = self._get("/social/coin/latest", {"coinId": self._get_coin_id(symbol)})
        if data and 'Data' in data:
            return data['Data']
        return None
    
    def _get_coin_id(self, symbol):
        """Mapeo de símbolos a IDs de CryptoCompare"""
        coin_ids = {
            'BTC': '1182',
            'ETH': '7605',
            'SOL': '935284',
            'BNB': '4614',
            'XRP': '5031'
        }
        return coin_ids.get(symbol, symbol)
    
    def get_coin_data(self, symbol):
        """
        Obtiene datos completos de una criptomoneda CON CACHE
        """
        if symbol in self.cache:
            return self.cache[symbol]
        
        # Obtener datos históricos
        hist_data = self.get_historical_data(symbol, limit=7)
        if not hist_data or len(hist_data) < 2:
            self.cache[symbol] = None
            return None
        
        try:
            # Calcular cambios de precio
            latest = hist_data[-1]
            yesterday = hist_data[-2] if len(hist_data) > 1 else hist_data[-1]
            week_ago = hist_data[0]
            
            price_current = latest['close']
            price_yesterday = yesterday['close']
            price_week_ago = week_ago['close']
            
            change_24h = ((price_current - price_yesterday) / price_yesterday * 100) if price_yesterday > 0 else 0
            change_7d = ((price_current - price_week_ago) / price_week_ago * 100) if price_week_ago > 0 else 0
            
            # Calcular volatilidad (desviación estándar de retornos)
            closes = [d['close'] for d in hist_data]
            returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
            volatility = np.std(returns) * 100 if returns else 0
            
            # Calcular volumen promedio
            avg_volume = np.mean([d['volumeto'] for d in hist_data])
            latest_volume = latest['volumeto']
            volume_ratio = (latest_volume / avg_volume) if avg_volume > 0 else 1.0
            
            # Calcular ATH y ATL de los últimos 7 días
            ath = max([d['high'] for d in hist_data])
            atl = min([d['low'] for d in hist_data])
            
            result = {
                'price': price_current,
                'price_change_24h': change_24h,
                'price_change_7d': change_7d,
                'volatility': volatility,
                'volume_24h': latest_volume,
                'volume_ratio': volume_ratio,
                'ath_7d': ath,
                'atl_7d': atl,
                'high_24h': latest['high'],
                'low_24h': latest['low']
            }
            
            self.cache[symbol] = result
            return result
            
        except Exception as e:
            logger.error(f"Error procesando datos de {symbol}: {e}")
            self.cache[symbol] = None
            return None
    
    def predict_direction(self, symbol, current_price):
        """
        Predice dirección basándose en métricas de CryptoCompare
        """
        resultado = {
            'direccion': 'NEUTRAL',
            'probabilidad': 50.0,
            'price_change_24h': 0.0,
            'price_change_7d': 0.0,
            'volatility': 0.0,
            'volume_signal': 'NORMAL',
            'razones': []
        }
        
        coin_data = self.get_coin_data(symbol)
        if not coin_data:
            resultado['razones'] = ['Datos no disponibles']
            return resultado
        
        # Sistema de scoring
        score_alcista = 0
        score_bajista = 0
        razones = []
        
        # 1. Análisis de momentum (cambio 24h)
        change_24h = coin_data['price_change_24h']
        if change_24h > 3:
            score_alcista += 2
            razones.append(f"Momentum alcista 24h: +{change_24h:.1f}%")
        elif change_24h < -3:
            score_bajista += 2
            razones.append(f"Momentum bajista 24h: {change_24h:.1f}%")
        
        # 2. Análisis de tendencia (cambio 7d)
        change_7d = coin_data['price_change_7d']
        if change_7d > 10:
            score_alcista += 2
            razones.append(f"Tendencia alcista 7d: +{change_7d:.1f}%")
        elif change_7d < -10:
            score_bajista += 2
            razones.append(f"Tendencia bajista 7d: {change_7d:.1f}%")
        
        # 3. Análisis de volumen
        volume_ratio = coin_data['volume_ratio']
        if volume_ratio > 1.5 and change_24h > 0:
            score_alcista += 1
            razones.append(f"Alto volumen de compra ({volume_ratio:.1f}x)")
            resultado['volume_signal'] = 'ALTO_COMPRA'
        elif volume_ratio > 1.5 and change_24h < 0:
            score_bajista += 1
            razones.append(f"Alto volumen de venta ({volume_ratio:.1f}x)")
            resultado['volume_signal'] = 'ALTO_VENTA'
        
        # 4. Análisis de volatilidad
        volatility = coin_data['volatility']
        if volatility > 5:
            razones.append(f"Alta volatilidad ({volatility:.1f}%)")
        
        # Calcular probabilidad
        total_score = score_alcista + score_bajista
        if total_score > 0:
            prob = 50 + (max(score_alcista, score_bajista) / total_score) * 40
        else:
            prob = 50.0
        
        # Determinar dirección
        if score_alcista > score_bajista:
            direccion = 'ALCISTA'
        elif score_bajista > score_alcista:
            direccion = 'BAJISTA'
        else:
            direccion = 'NEUTRAL'
        
        resultado.update({
            'direccion': direccion,
            'probabilidad': prob,
            'price_change_24h': change_24h,
            'price_change_7d': change_7d,
            'volatility': volatility,
            'razones': razones if razones else ['Sin señales claras']
        })
        
        return resultado
    
    def find_support_resistance(self, symbol, current_price):
        """
        Calcula niveles de soporte/resistencia
        """
        coin_data = self.cache.get(symbol)
        if not coin_data:
            coin_data = self.get_coin_data(symbol)
            if not coin_data:
                return []
        
        ath = coin_data['ath_7d']
        atl = coin_data['atl_7d']
        high_24h = coin_data['high_24h']
        low_24h = coin_data['low_24h']
        
        levels = []
        
        # Niveles basados en máximos y mínimos recientes
        if high_24h > current_price:
            distance = ((high_24h - current_price) / current_price) * 100
            levels.append({
                'price': high_24h,
                'distance_pct': distance,
                'type': 'RESISTANCE',
                'label': 'High 24h',
                'strength': '🔴 FUERTE' if distance < 3 else '🟡 MEDIO'
            })
        
        if low_24h < current_price:
            distance = ((low_24h - current_price) / current_price) * 100
            levels.append({
                'price': low_24h,
                'distance_pct': distance,
                'type': 'SUPPORT',
                'label': 'Low 24h',
                'strength': '🔴 FUERTE' if abs(distance) < 3 else '🟡 MEDIO'
            })
        
        # Fibonacci levels de los últimos 7 días
        if ath > current_price and atl < current_price:
            fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
            for fib in fib_levels:
                level_price = atl + ((ath - atl) * fib)
                distance = ((level_price - current_price) / current_price) * 100
                
                if abs(distance) < 15 and abs(distance) > 0.1:
                    levels.append({
                        'price': level_price,
                        'distance_pct': distance,
                        'type': 'RESISTANCE' if level_price > current_price else 'SUPPORT',
                        'label': f'Fib {fib:.3f}',
                        'strength': '🟡 MEDIO'
                    })
        
        return sorted(levels, key=lambda x: abs(x['distance_pct']))[:5]

# =======================================================================
# ORQUESTADOR
# =======================================================================

class PreNYAnalyzer:
    def __init__(self, custom_ranges=None):
        self.corr_analyzer = CryptoCorrelationAnalyzer(CRYPTOS)
        self.cc_analyzer = CryptoCompareAnalyzer()
        self.custom_ranges = custom_ranges
    
    def ejecutar_analisis(self):
        """Ejecuta el análisis completo de criptomonedas"""
        ahora_ny = datetime.now(NY_TZ)
        print("=" * 80)
        print(f"🚀 ANALISIS PRE-SESION NY | {ahora_ny.strftime('%Y-%m-%d %H:%M:%S')} EST")
        print("=" * 80)
        
        # Probar conexión a CryptoCompare
        cc_disponible = self.cc_analyzer.test_connection()
        
        if not cc_disponible:
            print("⚠️  No se pudo conectar a CryptoCompare API")
        
        # PRE-CARGAR datos con delay para evitar rate limit
        if cc_disponible:
            print("\n🔄 Precargando datos de mercado...")
            import time
            for i, (ticker, info) in enumerate(CRYPTOS.items()):
                print(f"   [{i+1}/5] {info['nombre']}...", end='', flush=True)
                result = self.cc_analyzer.get_coin_data(info['symbol'])
                if result:
                    print(f" ✅")
                else:
                    print(f" ❌")
                
                # Delay de 2 segundos entre llamadas
                if i < len(CRYPTOS) - 1:
                    time.sleep(2.0)
        
        # Análisis de correlaciones
        correlaciones, precios = self.corr_analyzer.calcular_correlaciones()
        if not precios:
            print("❌ No se pudo obtener datos de precios.")
            return
        
        # Mostrar correlaciones
        if correlaciones is not None:
            print("\n📈 Matriz de Correlaciones (Retornos 7d):")
            print(correlaciones.to_string(float_format=lambda x: f'{x:.3f}'))
            
            print("\n   Interpretación:")
            insights = self.corr_analyzer.interpretar_correlaciones(correlaciones)
            for insight in insights[:3]:
                print(f"    • {insight['interpretacion']}")
        
        # Análisis individual
        print("\n" + "=" * 80)
        print("🔍 ANÁLISIS INDIVIDUAL POR CRIPTOMONEDA")
        print("=" * 80)
        
        for ticker, info in CRYPTOS.items():
            if ticker not in precios:
                continue
            
            p_actual = precios[ticker]
            print(f"\n{'─' * 80}")
            print(f"🪙 {info['nombre'].upper()} | Precio: ${p_actual:,.2f}")
            print(f"{'─' * 80}")
            
            if cc_disponible:
                pred = self.cc_analyzer.predict_direction(info['symbol'], p_actual)
                
                emoji = "🟢" if pred['direccion'] == 'ALCISTA' else "🔴" if pred['direccion'] == 'BAJISTA' else "⚪"
                print(f"  {emoji} Sentiment: {pred['direccion']} ({pred['probabilidad']:.1f}%)")
                print(f"  📊 Volatilidad: {pred['volatility']:.2f}% | Cambio 24h: {pred['price_change_24h']:+.2f}%")
                print(f"  💰 Cambio 7d: {pred['price_change_7d']:+.2f}% | Vol: {pred['volume_signal']}")
                
                if pred['razones']:
                    print(f"  📝 Razones: {', '.join(pred['razones'])}")
                
                levels = self.cc_analyzer.find_support_resistance(info['symbol'], p_actual)
                if levels:
                    print(f"\n  🎯 NIVELES CLAVE:")
                    for i, level in enumerate(levels[:3]):
                        print(f"    {i+1}. ${level['price']:,.2f} ({level['distance_pct']:+.2f}%) "
                              f"- {level['type']} {level['label']} - {level['strength']}")
                else:
                    print(f"  ℹ️  No hay niveles significativos detectados")
            else:
                print(f"  ⚪ Sentiment: NEUTRAL (50.0%)")
                print(f"  📊 Volatilidad: 0.00% | Cambio 24h: +0.00%")
                print(f"  💰 Cambio 7d: 0.00%")
                print(f"  📝 Razones: API CryptoCompare no disponible")
                print(f"  ℹ️  No hay niveles significativos detectados")
        
        print("\n" + "=" * 80)
        print("✅ Análisis completado")
        print("=" * 80)

# =======================================================================
# EJECUCION
# =======================================================================

if __name__ == "__main__":
    analyzer = PreNYAnalyzer()
    analyzer.ejecutar_analisis()
