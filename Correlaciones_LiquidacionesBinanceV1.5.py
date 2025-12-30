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
    """Analiza liquidaciones de Binance Futures usando datos agregados"""
    
    BASE_URL = "https://fapi.binance.com"
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = timedelta(minutes=3)
    
    def get_open_interest(self, symbol):
        """Obtiene Open Interest (posiciones abiertas)"""
        try:
            url = f"{self.BASE_URL}/fapi/v1/openInterest"
            params = {"symbol": symbol}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return float(data['openInterest']) if data else 0.0
        except Exception as e:
            print(f"  ⚠️ Error en Open Interest: {str(e)[:100]}")
            return 0.0
    
    def get_long_short_ratio(self, symbol, period='5m'):
        """Obtiene ratio Long/Short de todos los traders"""
        try:
            url = f"{self.BASE_URL}/futures/data/globalLongShortAccountRatio"
            params = {"symbol": symbol, "period": period, "limit": 30}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return None
            
            df = pd.DataFrame(data)
            df['longShortRatio'] = df['longShortRatio'].astype(float)
            df['longAccount'] = df['longAccount'].astype(float)
            df['shortAccount'] = df['shortAccount'].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
        except Exception as e:
            print(f"  ⚠️ Error en Long/Short Ratio: {str(e)[:100]}")
            return None
    
    def get_taker_volume(self, symbol, period='5m'):
        """Obtiene volumen de takers (agresores del mercado)"""
        try:
            url = f"{self.BASE_URL}/futures/data/takerlongshortRatio"
            params = {"symbol": symbol, "period": period, "limit": 30}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return None
            
            df = pd.DataFrame(data)
            df['buySellRatio'] = df['buySellRatio'].astype(float)
            df['buyVol'] = df['buyVol'].astype(float)
            df['sellVol'] = df['sellVol'].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
        except Exception as e:
            print(f"  ⚠️ Error en Taker Volume: {str(e)[:100]}")
            return None
    
    def get_funding_rate(self, symbol):
        """Obtiene funding rate actual"""
        try:
            url = f"{self.BASE_URL}/fapi/v1/fundingRate"
            params = {"symbol": symbol, "limit": 10}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return 0.0
            
            latest = data[0]
            return float(latest['fundingRate'])
        except Exception as e:
            print(f"  ⚠️ Error en Funding Rate: {str(e)[:100]}")
            return 0.0
    
    
    def find_liquidation_zones(self, symbol, current_price, ranges=None):
        """
        Estima zonas de liquidación basado en Open Interest y ratios
        
        Args:
            symbol: Símbolo de Binance (ej: 'BTCUSDT')
            current_price: Precio actual
            ranges: Lista de rangos personalizados. Por defecto: [0.01, 0.02, 0.03, 0.05, 0.07, 0.10]
                   Representa [±1%, ±2%, ±3%, ±5%, ±7%, ±10%]
        """
        if ranges is None:
            # Rangos por defecto: Muy Cerca, Cerca, Medio, Lejano, Muy Lejano, Extremo
            ranges = [0.01, 0.02, 0.03, 0.05, 0.07, 0.10]
        
        # Obtener datos
        oi = self.get_open_interest(symbol)
        ls_ratio_df = self.get_long_short_ratio(symbol, '5m')
        taker_vol_df = self.get_taker_volume(symbol, '5m')
        funding = self.get_funding_rate(symbol)
        
        if ls_ratio_df is None or ls_ratio_df.empty:
            return []
        
        # Análisis de ratio Long/Short reciente
        recent_ls = ls_ratio_df.tail(6)  # Últimos 30 min
        avg_ls_ratio = recent_ls['longShortRatio'].mean()
        
        # Calcular cambio en el ratio
        if len(recent_ls) >= 2:
            ratio_change = ((recent_ls['longShortRatio'].iloc[-1] - 
                           recent_ls['longShortRatio'].iloc[0]) / 
                          recent_ls['longShortRatio'].iloc[0]) * 100
        else:
            ratio_change = 0
        
        # Etiquetas para cada rango
        range_labels = {
            0.01: "MUY_CERCA",
            0.02: "CERCA", 
            0.03: "MEDIO",
            0.05: "LEJANO",
            0.07: "MUY_LEJANO",
            0.10: "EXTREMO"
        }
        
        zones = []
        
        # Si hay más longs (ratio > 1), zona de liquidación bajista
        if avg_ls_ratio > 1.2:
            # Longs dominan = riesgo de liquidación bajista
            for pct in ranges:
                liq_price = current_price * (1 - pct)
                leverage = int(1 / pct) if pct > 0 else 100
                
                # Calcular intensidad basada en el ratio y la proximidad
                base_intensity = min(1.0, (avg_ls_ratio - 1) / 2)
                # Zonas más cercanas tienen mayor prioridad
                proximity_bonus = 1.0 - (pct / max(ranges))
                final_intensity = base_intensity * (0.7 + 0.3 * proximity_bonus)
                
                zones.append({
                    'price': liq_price,
                    'distance_pct': -pct * 100,
                    'type': 'LONG_LIQ_ZONE',
                    'leverage': leverage,
                    'intensity': final_intensity,
                    'range_label': range_labels.get(pct, f"{pct*100:.0f}%"),
                    'risk_level': self._get_risk_level(pct, avg_ls_ratio)
                })
        
        # Si hay más shorts (ratio < 0.8), zona de liquidación alcista
        if avg_ls_ratio < 0.8:
            # Shorts dominan = riesgo de liquidación alcista
            for pct in ranges:
                liq_price = current_price * (1 + pct)
                leverage = int(1 / pct) if pct > 0 else 100
                
                base_intensity = min(1.0, (1 - avg_ls_ratio) / 2)
                proximity_bonus = 1.0 - (pct / max(ranges))
                final_intensity = base_intensity * (0.7 + 0.3 * proximity_bonus)
                
                zones.append({
                    'price': liq_price,
                    'distance_pct': pct * 100,
                    'type': 'SHORT_LIQ_ZONE',
                    'leverage': leverage,
                    'intensity': final_intensity,
                    'range_label': range_labels.get(pct, f"{pct*100:.0f}%"),
                    'risk_level': self._get_risk_level(pct, 1/avg_ls_ratio)
                })
        
        return zones
    
    def _get_risk_level(self, distance_pct, ratio):
        """Calcula nivel de riesgo de alcanzar la zona"""
        # Combina distancia y desbalance del ratio
        distance_score = 1.0 - min(distance_pct / 0.10, 1.0)  # Normalizar a 0-1
        ratio_score = min(abs(ratio - 1.0) / 1.0, 1.0)  # Desbalance del ratio
        
        combined_score = (distance_score * 0.6) + (ratio_score * 0.4)
        
        if combined_score > 0.7:
            return "🔴 ALTO"
        elif combined_score > 0.4:
            return "🟡 MEDIO"
        else:
            return "🟢 BAJO"
    
    
    def predict_direction(self, symbol, current_price):
        """Predice dirección probable basado en métricas de mercado"""
        
        # Obtener datos
        ls_ratio_df = self.get_long_short_ratio(symbol, '5m')
        taker_vol_df = self.get_taker_volume(symbol, '5m')
        funding = self.get_funding_rate(symbol)
        oi = self.get_open_interest(symbol)
        
        if ls_ratio_df is None or ls_ratio_df.empty:
            return {
                'direccion': 'NEUTRAL',
                'probabilidad': 50.0,
                'razon': 'Sin datos disponibles'
            }
        
        # Análisis de datos
        recent_ls = ls_ratio_df.tail(6)
        avg_ls_ratio = recent_ls['longShortRatio'].mean()
        current_ls_ratio = recent_ls['longShortRatio'].iloc[-1]
        
        # Tendencia del ratio
        if len(recent_ls) >= 2:
            ratio_trend = current_ls_ratio - recent_ls['longShortRatio'].iloc[0]
        else:
            ratio_trend = 0
        
        # Análisis de volumen taker
        buy_sell_ratio = 1.0
        if taker_vol_df is not None and not taker_vol_df.empty:
            recent_taker = taker_vol_df.tail(6)
            buy_sell_ratio = recent_taker['buySellRatio'].mean()
        
        # Sistema de scoring
        score_alcista = 0
        score_bajista = 0
        razones = []
        
        # Factor 1: Ratio Long/Short (peso: 2.5 puntos)
        if avg_ls_ratio > 1.5:
            score_bajista += 2.5
            razones.append(f"Exceso de longs ({avg_ls_ratio:.2f}:1) - Riesgo caída")
        elif avg_ls_ratio < 0.67:
            score_alcista += 2.5
            razones.append(f"Exceso de shorts ({1/avg_ls_ratio:.2f}:1) - Riesgo subida")
        elif avg_ls_ratio > 1.2:
            score_bajista += 1.5
            razones.append(f"Mayoría longs ({avg_ls_ratio:.2f}:1)")
        elif avg_ls_ratio < 0.83:
            score_alcista += 1.5
            razones.append(f"Mayoría shorts ({1/avg_ls_ratio:.2f}:1)")
        
        # Factor 2: Funding Rate (peso: 2.0 puntos)
        if funding > 0.0001:  # >0.01% = longs pagan
            score_bajista += 2.0
            razones.append(f"Funding positivo ({funding*100:.3f}%) - Longs pagan")
        elif funding < -0.0001:  # Negativo = shorts pagan
            score_alcista += 2.0
            razones.append(f"Funding negativo ({funding*100:.3f}%) - Shorts pagan")
        elif funding > 0.00005:
            score_bajista += 1.0
            razones.append("Funding ligeramente positivo")
        elif funding < -0.00005:
            score_alcista += 1.0
            razones.append("Funding ligeramente negativo")
        
        # Factor 3: Volumen Taker (peso: 1.5 puntos)
        if buy_sell_ratio > 1.3:
            score_alcista += 1.5
            razones.append(f"Compras agresivas ({buy_sell_ratio:.2f}:1)")
        elif buy_sell_ratio < 0.77:
            score_bajista += 1.5
            razones.append(f"Ventas agresivas ({1/buy_sell_ratio:.2f}:1)")
        elif buy_sell_ratio > 1.1:
            score_alcista += 0.8
            razones.append("Más compras que ventas")
        elif buy_sell_ratio < 0.91:
            score_bajista += 0.8
            razones.append("Más ventas que compras")
        
        # Factor 4: Tendencia del ratio (peso: 1.0 puntos)
        if ratio_trend > 0.1:
            score_bajista += 1.0
            razones.append("Ratio L/S aumentando")
        elif ratio_trend < -0.1:
            score_alcista += 1.0
            razones.append("Ratio L/S disminuyendo")
        
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
            'ls_ratio': avg_ls_ratio,
            'funding_rate': funding * 100,  # En porcentaje
            'buy_sell_ratio': buy_sell_ratio,
            'open_interest': oi,
            'razones': razones
        }

# =======================================================================
# ORQUESTADOR PRINCIPAL
# =======================================================================

class PreNYAnalyzer:
    """Análisis completo pre-sesión NY"""
    
    def __init__(self, custom_ranges=None):
        """
        Args:
            custom_ranges: Lista de rangos personalizados para zonas de liquidación.
                          Por defecto: [1%, 2%, 3%, 5%, 7%, 10%]
                          Ejemplo: [0.015, 0.025, 0.04, 0.06] = [1.5%, 2.5%, 4%, 6%]
        """
        self.corr_analyzer = CryptoCorrelationAnalyzer(CRYPTOS)
        self.liq_analyzer = BinanceLiquidationAnalyzer()
        self.custom_ranges = custom_ranges
    
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
            
            # Predicción de dirección
            prediccion = self.liq_analyzer.predict_direction(binance_symbol, precio_actual)
            
            if prediccion['direccion'] == 'NEUTRAL' and 'Sin datos' in str(prediccion.get('razon', '')):
                print("❌ Sin datos disponibles de Binance")
                continue
            
            # Zonas de liquidación estimadas
            zones = self.liq_analyzer.find_liquidation_zones(
                binance_symbol, 
                precio_actual,
                ranges=self.custom_ranges
            )
            
            if zones:
                print(f"\n🎯 Zonas de Liquidación Estimadas:")
                print(f"{'#':<3} {'Tipo':<6} {'Precio':<12} {'Distancia':<10} {'Leverage':<9} {'Rango':<12} {'Riesgo':<12} {'Intensidad':<10}")
                print("-" * 85)
                
                for i, zone in enumerate(zones, 1):
                    tipo_icon = "🔴" if zone['type'] == 'LONG_LIQ_ZONE' else "🟢"
                    print(f"{i:<3} {tipo_icon:<6} ${zone['price']:<11,.2f} "
                          f"{zone['distance_pct']:>+6.2f}%   "
                          f"~{zone['leverage']:<7}x "
                          f"{zone['range_label']:<12} "
                          f"{zone['risk_level']:<12} "
                          f"{zone['intensity']:.0%}")
                
                # Resaltar zona de mayor riesgo (más cercana + alta intensidad)
                high_risk_zones = [z for z in zones if "ALTO" in z['risk_level']]
                if high_risk_zones:
                    closest_high_risk = min(high_risk_zones, key=lambda x: abs(x['distance_pct']))
                    print(f"\n⚠️  ZONA CRÍTICA: ${closest_high_risk['price']:,.2f} "
                          f"({closest_high_risk['distance_pct']:+.1f}%) - "
                          f"{closest_high_risk['type'].replace('_ZONE', '')}")
            else:
                print("\n⚪ Sin zonas de liquidación significativas (ratio balanceado)")
            
            # Emoji según dirección
            if prediccion['direccion'] == 'ALCISTA':
                emoji = "🟢📈"
            elif prediccion['direccion'] == 'BAJISTA':
                emoji = "🔴📉"
            else:
                emoji = "⚪➡️"
            
            print(f"\n{emoji} PREDICCION: {prediccion['direccion']}")
            print(f"📊 Probabilidad: {prediccion['probabilidad']:.1f}%")
            print(f"📈 Long/Short Ratio: {prediccion['ls_ratio']:.2f}")
            print(f"💸 Funding Rate: {prediccion['funding_rate']:.4f}%")
            print(f"📊 Buy/Sell Ratio: {prediccion['buy_sell_ratio']:.2f}")
            print(f"💼 Open Interest: ${prediccion['open_interest']:,.0f}")
            
            if prediccion['razones']:
                print(f"🎯 Factores Clave:")
                for razon in prediccion['razones']:
                    print(f"  • {razon}")
            
            # Guardar resultado
            resultados.append({
                'ticker': ticker,
                'nombre': info['nombre'],
                'precio': precio_actual,
                'direccion': prediccion['direccion'],
                'probabilidad': prediccion['probabilidad'],
                'ls_ratio': prediccion['ls_ratio'],
                'funding_rate': prediccion['funding_rate'],
                'zones_count': len(zones),
                'top_zone': zones[0] if zones else None
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
    # Opción 1: Usar rangos por defecto [±1%, ±2%, ±3%, ±5%, ±7%, ±10%]
    analyzer = PreNYAnalyzer()
    
    # Opción 2: Usar rangos personalizados (descomentar para usar)
    # Ejemplo: Enfocarse en rangos más cercanos
    # analyzer = PreNYAnalyzer(custom_ranges=[0.005, 0.01, 0.015, 0.02, 0.03, 0.05])
    #          Esto genera: [±0.5%, ±1%, ±1.5%, ±2%, ±3%, ±5%]
    
    # Ejemplo: Rangos más amplios para swing trading
    # analyzer = PreNYAnalyzer(custom_ranges=[0.02, 0.04, 0.06, 0.08, 0.10, 0.15])
    #          Esto genera: [±2%, ±4%, ±6%, ±8%, ±10%, ±15%]
    
    analyzer.ejecutar_analisis()
