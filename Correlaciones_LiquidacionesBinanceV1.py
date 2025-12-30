import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import pytz
import warnings
warnings.filterwarnings('ignore')

# =======================================================================
# CONFIGURACION
# =======================================================================

TIJUANA_TZ = pytz.timezone('America/Tijuana')
NY_TZ = pytz.timezone('America/New_York')

# Criptomonedas a analizar
CRYPTOS = {
    'BTC-USD': {'nombre': 'Bitcoin', 'binance': 'BTCUSDT'},
    'ETH-USD': {'nombre': 'Ethereum', 'binance': 'ETHUSDT'},
    'SOL-USD': {'nombre': 'Solana', 'binance': 'SOLUSDT'},
    'BNB-USD': {'nombre': 'Binance Coin', 'binance': 'BNBUSDT'},
    'XRP-USD': {'nombre': 'Ripple', 'binance': 'XRPUSDT'}
}

# =======================================================================
# MODULO 1: DESCARGA DE DATOS Y CORRELACIONES
# =======================================================================

class CryptoCorrelationAnalyzer:
    """Analiza correlaciones entre criptomonedas"""
    
    def __init__(self, cryptos_dict):
        self.cryptos = cryptos_dict
        self.datos_cache = {}
    
    def descargar_datos(self, ticker, periodo='7d', intervalo='1h'):
        """Descarga datos históricos de yfinance"""
        try:
            datos = yf.download(ticker, period=periodo, interval=intervalo, 
                              progress=False, auto_adjust=True)
            
            if datos.empty:
                return None
            
            # Aplanar multi-índice si existe
            if isinstance(datos.columns, pd.MultiIndex):
                datos.columns = datos.columns.get_level_values(0)
            
            return datos
        except Exception as e:
            print(f"❌ Error descargando {ticker}: {e}")
            return None
    
    def calcular_correlaciones(self):
        """Calcula matriz de correlaciones de retornos"""
        retornos = pd.DataFrame()
        
        print("📊 Descargando datos históricos...")
        for ticker, info in self.cryptos.items():
            datos = self.descargar_datos(ticker)
            if datos is not None and len(datos) > 0:
                retornos[info['nombre']] = datos['Close'].pct_change()
                self.datos_cache[ticker] = datos
                print(f"  ✅ {info['nombre']}: {len(datos)} velas")
            else:
                print(f"  ❌ {info['nombre']}: Sin datos")
        
        if len(retornos.columns) < 2:
            return None, None
        
        # Matriz de correlaciones
        correlaciones = retornos.corr()
        
        # Precios actuales
        precios = {}
        for ticker, datos in self.datos_cache.items():
            precios[ticker] = float(datos['Close'].iloc[-1])
        
        return correlaciones, precios
    
    def interpretar_correlaciones(self, corr_matrix):
        """Genera interpretación de correlaciones"""
        if corr_matrix is None:
            return []
        
        insights = []
        
        # Encontrar pares con correlación alta (>0.85)
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_val = corr_matrix.iloc[i, j]
                crypto1 = corr_matrix.columns[i]
                crypto2 = corr_matrix.columns[j]
                
                if corr_val > 0.85:
                    insights.append({
                        'tipo': 'ALTA_CORRELACION',
                        'par': f"{crypto1} - {crypto2}",
                        'valor': corr_val,
                        'interpretacion': f"🔗 Se mueven juntas ({corr_val:.3f})"
                    })
                elif corr_val < 0.3:
                    insights.append({
                        'tipo': 'BAJA_CORRELACION',
                        'par': f"{crypto1} - {crypto2}",
                        'valor': corr_val,
                        'interpretacion': f"🔀 Movimientos independientes ({corr_val:.3f})"
                    })
        
        return insights

# =======================================================================
# MODULO 2: LIQUIDACIONES BINANCE
# =======================================================================

class BinanceLiquidationAnalyzer:
    """Analiza liquidaciones de Binance Futures"""
    
    BASE_URL = "https://fapi.binance.com/fapi/v1"
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = timedelta(minutes=3)
    
    def get_liquidations(self, symbol, limit=1000):
        """Obtiene liquidaciones recientes"""
        cache_key = f"{symbol}_{limit}"
        
        # Verificar cache
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_duration:
                return cached_data
        
        url = f"{self.BASE_URL}/allForceOrders"
        params = {"symbol": symbol, "limit": limit}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return None
            
            # Procesar datos
            df = pd.DataFrame(data)
            df['price'] = df['price'].astype(float)
            df['origQty'] = df['origQty'].astype(float)
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            df['usd_volume'] = df['price'] * df['origQty']
            
            df['liq_type'] = df['side'].map({
                'SELL': 'LONG_LIQ',  # Liquidación de longs (bajista)
                'BUY': 'SHORT_LIQ'   # Liquidación de shorts (alcista)
            })
            
            df = df[['time', 'side', 'liq_type', 'price', 'origQty', 'usd_volume']]
            df = df.sort_values('time', ascending=False)
            
            # Guardar en cache
            self.cache[cache_key] = (datetime.now(), df)
            return df
            
        except Exception as e:
            print(f"❌ Error obteniendo liquidaciones {symbol}: {e}")
            return None
    
    def find_liquidation_clusters(self, liq_df, current_price, tolerance_pct=0.5):
        """Encuentra clusters de liquidaciones cerca del precio actual"""
        if liq_df is None or liq_df.empty:
            return []
        
        # Agrupar por precio (tolerancia de 0.5%)
        liq_df = liq_df.copy()
        price_step = current_price * (tolerance_pct / 100)
        liq_df['price_group'] = (liq_df['price'] / price_step).round() * price_step
        
        # Agrupar y sumar volúmenes
        grouped = liq_df.groupby('price_group').agg({
            'usd_volume': 'sum',
            'price': 'mean',
            'liq_type': lambda x: x.mode()[0] if not x.empty else 'NEUTRAL',
            'time': 'max'
        }).reset_index(drop=True)
        
        # Filtrar clusters significativos (>$50k)
        significant = grouped[grouped['usd_volume'] > 50000].copy()
        
        if significant.empty:
            return []
        
        # Calcular distancia al precio actual
        significant['distance_pct'] = ((significant['price'] - current_price) / current_price) * 100
        significant['age_hours'] = (datetime.now() - significant['time']).dt.total_seconds() / 3600
        
        # Intensidad relativa
        max_vol = significant['usd_volume'].max()
        significant['intensity'] = significant['usd_volume'] / max_vol
        
        # Ordenar por proximidad al precio actual
        significant = significant.sort_values('distance_pct', key=abs)
        
        clusters = []
        for _, row in significant.head(10).iterrows():
            clusters.append({
                'price': row['price'],
                'distance_pct': row['distance_pct'],
                'volume_usd': row['usd_volume'],
                'type': row['liq_type'],
                'intensity': row['intensity'],
                'age_hours': row['age_hours']
            })
        
        return clusters
    
    def predict_direction(self, liq_df, current_price):
        """Predice dirección probable del movimiento basado en liquidaciones"""
        if liq_df is None or liq_df.empty:
            return {
                'direccion': 'NEUTRAL',
                'probabilidad': 50.0,
                'razon': 'Sin datos de liquidaciones'
            }
        
        # Separar liquidaciones por tipo
        long_liq = liq_df[liq_df['liq_type'] == 'LONG_LIQ']
        short_liq = liq_df[liq_df['liq_type'] == 'SHORT_LIQ']
        
        long_vol = long_liq['usd_volume'].sum()
        short_vol = short_liq['usd_volume'].sum()
        total_vol = long_vol + short_vol
        
        if total_vol == 0:
            return {
                'direccion': 'NEUTRAL',
                'probabilidad': 50.0,
                'razon': 'Sin volumen significativo'
            }
        
        # Calcular ratio
        long_pct = (long_vol / total_vol) * 100
        short_pct = (short_vol / total_vol) * 100
        
        # Analizar liquidaciones recientes (últimas 24h)
        recent_24h = liq_df[liq_df['time'] > (datetime.now() - timedelta(hours=24))]
        recent_long_vol = recent_24h[recent_24h['liq_type'] == 'LONG_LIQ']['usd_volume'].sum()
        recent_short_vol = recent_24h[recent_24h['liq_type'] == 'SHORT_LIQ']['usd_volume'].sum()
        
        # Buscar clusters cercanos (±2%)
        margin = current_price * 0.02
        near_clusters = liq_df[
            (liq_df['price'] >= current_price - margin) & 
            (liq_df['price'] <= current_price + margin)
        ]
        
        near_long_vol = near_clusters[near_clusters['liq_type'] == 'LONG_LIQ']['usd_volume'].sum()
        near_short_vol = near_clusters[near_clusters['liq_type'] == 'SHORT_LIQ']['usd_volume'].sum()
        
        # Sistema de scoring
        score_alcista = 0
        score_bajista = 0
        razones = []
        
        # Factor 1: Volumen total de liquidaciones
        if long_vol > short_vol * 1.5:
            score_bajista += 2
            razones.append(f"Longs liquidados masivamente (${long_vol:,.0f})")
        elif short_vol > long_vol * 1.5:
            score_alcista += 2
            razones.append(f"Shorts liquidados masivamente (${short_vol:,.0f})")
        
        # Factor 2: Liquidaciones recientes (24h)
        if recent_long_vol > recent_short_vol * 1.3:
            score_bajista += 1.5
            razones.append("Momentum bajista (24h)")
        elif recent_short_vol > recent_long_vol * 1.3:
            score_alcista += 1.5
            razones.append("Momentum alcista (24h)")
        
        # Factor 3: Clusters cercanos al precio
        if near_long_vol > near_short_vol * 1.2 and near_long_vol > 100000:
            score_bajista += 1
            razones.append(f"Zona caliente bajista (${near_long_vol:,.0f})")
        elif near_short_vol > near_long_vol * 1.2 and near_short_vol > 100000:
            score_alcista += 1
            razones.append(f"Zona caliente alcista (${near_short_vol:,.0f})")
        
        # Determinar dirección y probabilidad
        total_score = score_alcista + score_bajista
        
        if total_score == 0:
            direccion = 'NEUTRAL'
            probabilidad = 50.0
        elif score_alcista > score_bajista:
            direccion = 'ALCISTA'
            probabilidad = 50 + (score_alcista / total_score) * 30
        else:
            direccion = 'BAJISTA'
            probabilidad = 50 + (score_bajista / total_score) * 30
        
        return {
            'direccion': direccion,
            'probabilidad': round(probabilidad, 1),
            'score_alcista': score_alcista,
            'score_bajista': score_bajista,
            'long_liq_pct': long_pct,
            'short_liq_pct': short_pct,
            'total_volume': total_vol,
            'razones': razones
        }

# =======================================================================
# ORQUESTADOR PRINCIPAL
# =======================================================================

class PreNYAnalyzer:
    """Análisis completo pre-sesión NY"""
    
    def __init__(self):
        self.corr_analyzer = CryptoCorrelationAnalyzer(CRYPTOS)
        self.liq_analyzer = BinanceLiquidationAnalyzer()
    
    def ejecutar_analisis(self):
        """Ejecuta análisis completo"""
        
        # Timestamp
        ahora_tj = datetime.now(TIJUANA_TZ)
        ahora_ny = datetime.now(NY_TZ)
        
        print("="*80)
        print("🚀 ANALISIS PRE-SESION NY | CORRELACIONES + LIQUIDACIONES")
        print("="*80)
        print(f"📅 Fecha: {ahora_tj.strftime('%Y-%m-%d')}")
        print(f"🕐 Hora Tijuana: {ahora_tj.strftime('%H:%M:%S %Z')}")
        print(f"🕐 Hora NY: {ahora_ny.strftime('%H:%M:%S %Z')}")
        print(f"⏰ Apertura NY en: {self._tiempo_hasta_ny(ahora_ny)}")
        print("="*80)
        print()
        
        # PASO 1: Correlaciones
        print("📊 PASO 1: ANALISIS DE CORRELACIONES")
        print("-"*80)
        correlaciones, precios = self.corr_analyzer.calcular_correlaciones()
        
        if correlaciones is not None:
            print("\n🔗 Matriz de Correlaciones (Retornos 7d):")
            print(correlaciones.round(3).to_string())
            
            insights = self.corr_analyzer.interpretar_correlaciones(correlaciones)
            if insights:
                print("\n💡 Interpretación:")
                for insight in insights:
                    print(f"  {insight['interpretacion']}")
        else:
            print("❌ No se pudieron calcular correlaciones")
            return
        
        print("\n" + "="*80)
        print("🔥 PASO 2: ANALISIS DE LIQUIDACIONES BINANCE")
        print("="*80)
        
        resultados = []
        
        for ticker, info in CRYPTOS.items():
            if ticker not in precios:
                continue
            
            precio_actual = precios[ticker]
            binance_symbol = info['binance']
            
            print(f"\n--- {info['nombre']} ({ticker}) ---")
            print(f"💰 Precio: ${precio_actual:,.4f}")
            
            # Obtener liquidaciones
            liq_df = self.liq_analyzer.get_liquidations(binance_symbol)
            
            if liq_df is None or liq_df.empty:
                print("❌ Sin datos de liquidaciones")
                continue
            
            # Clusters cercanos
            clusters = self.liq_analyzer.find_liquidation_clusters(liq_df, precio_actual)
            
            if clusters:
                print(f"\n📍 Top 5 Clusters Cercanos:")
                for i, cluster in enumerate(clusters[:5], 1):
                    tipo_icon = "🔴" if cluster['type'] == 'LONG_LIQ' else "🟢"
                    print(f"  {i}. {tipo_icon} ${cluster['price']:,.2f} "
                          f"({cluster['distance_pct']:+.2f}%) | "
                          f"${cluster['volume_usd']:,.0f} | "
                          f"Intensidad: {cluster['intensity']:.0%} | "
                          f"Edad: {cluster['age_hours']:.1f}h")
            
            # Predicción de dirección
            prediccion = self.liq_analyzer.predict_direction(liq_df, precio_actual)
            
            # Emoji según dirección
            if prediccion['direccion'] == 'ALCISTA':
                emoji = "🟢📈"
            elif prediccion['direccion'] == 'BAJISTA':
                emoji = "🔴📉"
            else:
                emoji = "⚪➡️"
            
            print(f"\n{emoji} PREDICCION: {prediccion['direccion']}")
            print(f"📊 Probabilidad: {prediccion['probabilidad']:.1f}%")
            print(f"💼 Volumen Total: ${prediccion['total_volume']:,.0f}")
            print(f"📉 Long Liq: {prediccion['long_liq_pct']:.1f}% | "
                  f"📈 Short Liq: {prediccion['short_liq_pct']:.1f}%")
            
            if prediccion['razones']:
                print(f"🎯 Razones:")
                for razon in prediccion['razones']:
                    print(f"  • {razon}")
            
            # Guardar resultado
            resultados.append({
                'ticker': ticker,
                'nombre': info['nombre'],
                'precio': precio_actual,
                'direccion': prediccion['direccion'],
                'probabilidad': prediccion['probabilidad'],
                'clusters_count': len(clusters),
                'top_cluster': clusters[0] if clusters else None
            })
        
        # RESUMEN FINAL
        print("\n" + "="*80)
        print("📋 RESUMEN EJECUTIVO")
        print("="*80)
        
        if resultados:
            # Ordenar por probabilidad
            resultados_ord = sorted(resultados, key=lambda x: x['probabilidad'], reverse=True)
            
            print("\n🎯 Señales Más Fuertes:")
            for i, r in enumerate(resultados_ord, 1):
                emoji = "🟢" if r['direccion'] == 'ALCISTA' else "🔴" if r['direccion'] == 'BAJISTA' else "⚪"
                print(f"  {i}. {emoji} {r['nombre']:15} | "
                      f"{r['direccion']:8} ({r['probabilidad']:.1f}%) | "
                      f"${r['precio']:,.4f}")
            
            # Señales alcistas vs bajistas
            alcistas = [r for r in resultados if r['direccion'] == 'ALCISTA']
            bajistas = [r for r in resultados if r['direccion'] == 'BAJISTA']
            
            print(f"\n📊 Balance del Mercado:")
            print(f"  🟢 Señales Alcistas: {len(alcistas)}")
            print(f"  🔴 Señales Bajistas: {len(bajistas)}")
            
            if len(alcistas) > len(bajistas) * 1.5:
                print(f"  ➡️  SENTIMENT GENERAL: ALCISTA 📈")
            elif len(bajistas) > len(alcistas) * 1.5:
                print(f"  ➡️  SENTIMENT GENERAL: BAJISTA 📉")
            else:
                print(f"  ➡️  SENTIMENT GENERAL: NEUTRAL ⚖️")
        
        print("\n" + "="*80)
        print("✅ Análisis completado")
        print("="*80)
    
    def _tiempo_hasta_ny(self, ahora_ny):
        """Calcula tiempo hasta apertura NY (9:30 AM)"""
        apertura = ahora_ny.replace(hour=9, minute=30, second=0, microsecond=0)
        
        if ahora_ny.time() >= apertura.time():
            # Ya pasó, calcular para mañana
            apertura += timedelta(days=1)
        
        delta = apertura - ahora_ny
        horas = int(delta.total_seconds() // 3600)
        minutos = int((delta.total_seconds() % 3600) // 60)
        
        return f"{horas}h {minutos}m"

# =======================================================================
# EJECUCION
# =======================================================================

if __name__ == "__main__":
    analyzer = PreNYAnalyzer()
    analyzer.ejecutar_analisis()
