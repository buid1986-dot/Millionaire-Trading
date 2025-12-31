import yfinance as yf
import pandas as pd
import numpy as np
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
    'BTC-USD': {'nombre': 'Bitcoin'},
    'ETH-USD': {'nombre': 'Ethereum'},
    'SOL-USD': {'nombre': 'Solana'},
    'BNB-USD': {'nombre': 'Binance Coin'},
    'XRP-USD': {'nombre': 'Ripple'}
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
        
        correlaciones = retornos.corr()
        
        precios = {}
        for ticker, datos in self.datos_cache.items():
            precios[ticker] = float(datos['Close'].iloc[-1])
        
        return correlaciones, precios
    
    def interpretar_correlaciones(self, corr_matrix):
        """Genera interpretación de correlaciones"""
        if corr_matrix is None:
            return []
        
        insights = []
        
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
# MODULO 2: ANALISIS TECNICO AVANZADO (SIN APIs EXTERNAS)
# =======================================================================

class TechnicalAnalyzer:
    """Analiza tendencias y estima sentiment usando solo price action"""
    
    def __init__(self):
        pass
    
    def calculate_rsi(self, prices, period=14):
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    
    def calculate_momentum(self, prices):
        """Calcula momentum multi-timeframe"""
        mom_24h = ((prices.iloc[-1] - prices.iloc[-24]) / prices.iloc[-24]) * 100 if len(prices) >= 24 else 0
        mom_7d = ((prices.iloc[-1] - prices.iloc[-168]) / prices.iloc[-168]) * 100 if len(prices) >= 168 else 0
        return mom_24h, mom_7d
    
    def calculate_volatility(self, prices, window=24):
        """Calcula volatilidad"""
        returns = prices.pct_change()
        return returns.rolling(window=window).std().iloc[-1]
    
    def estimate_long_short_bias(self, datos):
        """
        Estima sesgo Long/Short basado en price action
        
        Lógica:
        - Precio subiendo + Volumen alto = Longs entrando
        - Precio cayendo + Volumen alto = Shorts entrando o Longs saliendo
        - RSI + Momentum dan sentiment general
        """
        prices = datos['Close']
        volume = datos['Volume']
        
        # RSI
        rsi = self.calculate_rsi(prices)
        
        # Momentum
        mom_24h, mom_7d = self.calculate_momentum(prices)
        
        # Volatilidad
        volatility = self.calculate_volatility(prices)
        
        # Tendencia reciente (últimas 24h)
        recent_trend = mom_24h
        
        # Volumen relativo
        avg_volume = volume.rolling(20).mean().iloc[-1]
        current_volume = volume.iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Estimación de sesgo
        # RSI alto + momentum positivo = Exceso de longs
        # RSI bajo + momentum negativo = Exceso de shorts
        
        if rsi > 65 and recent_trend > 0:
            ls_ratio = 1.5 + (rsi - 65) / 35 * 0.5  # 1.5 a 2.0
            bias_text = "Exceso de LONGS"
        elif rsi < 35 and recent_trend < 0:
            ls_ratio = 0.5 + (35 - rsi) / 35 * 0.17  # 0.5 a 0.67
            bias_text = "Exceso de SHORTS"
        else:
            ls_ratio = 0.8 + (rsi / 100) * 0.4  # 0.8 a 1.2
            bias_text = "BALANCEADO"
        
        # Estimación de funding (basado en momentum sostenido)
        if mom_24h > 3 and mom_7d > 5:
            funding_rate = 0.015  # Funding positivo (longs pagan)
        elif mom_24h < -3 and mom_7d < -5:
            funding_rate = -0.015  # Funding negativo (shorts pagan)
        else:
            funding_rate = mom_24h / 1000  # Pequeño sesgo
        
        # Buy/Sell ratio estimado
        if volume_ratio > 1.5 and recent_trend > 0:
            buy_sell_ratio = 1.4  # Compras agresivas
        elif volume_ratio > 1.5 and recent_trend < 0:
            buy_sell_ratio = 0.7  # Ventas agresivas
        else:
            buy_sell_ratio = 1.0  # Neutral
        
        return {
            'ls_ratio': ls_ratio,
            'bias_text': bias_text,
            'funding_rate': funding_rate,
            'buy_sell_ratio': buy_sell_ratio,
            'rsi': rsi,
            'momentum_24h': mom_24h,
            'momentum_7d': mom_7d,
            'volatility': volatility,
            'volume_ratio': volume_ratio
        }
    
    def estimate_liquidation_zones(self, current_price, ls_ratio, ranges=None):
        """Estima zonas de liquidación basado en el ratio L/S"""
        if ranges is None:
            ranges = [0.01, 0.02, 0.03, 0.05, 0.07, 0.10]
        
        range_labels = {
            0.01: "MUY_CERCA",
            0.02: "CERCA",
            0.03: "MEDIO",
            0.05: "LEJANO",
            0.07: "MUY_LEJANO",
            0.10: "EXTREMO"
        }
        
        zones = []
        
        # Si ratio > 1.2 = Exceso de longs → Zonas bajistas
        if ls_ratio > 1.2:
            for pct in ranges:
                liq_price = current_price * (1 - pct)
                leverage = int(1 / pct) if pct > 0 else 100
                
                base_intensity = min(1.0, (ls_ratio - 1) / 2)
                proximity_bonus = 1.0 - (pct / max(ranges))
                final_intensity = base_intensity * (0.7 + 0.3 * proximity_bonus)
                
                distance_score = 1.0 - min(pct / 0.10, 1.0)
                ratio_score = min(abs(ls_ratio - 1.0) / 1.0, 1.0)
                combined_score = (distance_score * 0.6) + (ratio_score * 0.4)
                
                if combined_score > 0.7:
                    risk_level = "🔴 ALTO"
                elif combined_score > 0.4:
                    risk_level = "🟡 MEDIO"
                else:
                    risk_level = "🟢 BAJO"
                
                zones.append({
                    'price': liq_price,
                    'distance_pct': -pct * 100,
                    'type': 'LONG_LIQ_ZONE',
                    'leverage': leverage,
                    'intensity': final_intensity,
                    'range_label': range_labels.get(pct, f"{pct*100:.0f}%"),
                    'risk_level': risk_level
                })
        
        # Si ratio < 0.8 = Exceso de shorts → Zonas alcistas
        if ls_ratio < 0.8:
            for pct in ranges:
                liq_price = current_price * (1 + pct)
                leverage = int(1 / pct) if pct > 0 else 100
                
                base_intensity = min(1.0, (1 - ls_ratio) / 2)
                proximity_bonus = 1.0 - (pct / max(ranges))
                final_intensity = base_intensity * (0.7 + 0.3 * proximity_bonus)
                
                distance_score = 1.0 - min(pct / 0.10, 1.0)
                ratio_score = min(abs(ls_ratio - 1.0) / 1.0, 1.0)
                combined_score = (distance_score * 0.6) + (ratio_score * 0.4)
                
                if combined_score > 0.7:
                    risk_level = "🔴 ALTO"
                elif combined_score > 0.4:
                    risk_level = "🟡 MEDIO"
                else:
                    risk_level = "🟢 BAJO"
                
                zones.append({
                    'price': liq_price,
                    'distance_pct': pct * 100,
                    'type': 'SHORT_LIQ_ZONE',
                    'leverage': leverage,
                    'intensity': final_intensity,
                    'range_label': range_labels.get(pct, f"{pct*100:.0f}%"),
                    'risk_level': risk_level
                })
        
        return zones
    
    def predict_direction(self, metrics):
        """Predice dirección basado en métricas técnicas"""
        
        ls_ratio = metrics['ls_ratio']
        funding = metrics['funding_rate']
        buy_sell = metrics['buy_sell_ratio']
        rsi = metrics['rsi']
        mom_24h = metrics['momentum_24h']
        
        score_alcista = 0
        score_bajista = 0
        razones = []
        
        # Factor 1: L/S Ratio (2.5 pts)
        if ls_ratio > 1.5:
            score_bajista += 2.5
            razones.append(f"Exceso de longs ({ls_ratio:.2f}:1)")
        elif ls_ratio < 0.67:
            score_alcista += 2.5
            razones.append(f"Exceso de shorts ({1/ls_ratio:.2f}:1)")
        elif ls_ratio > 1.2:
            score_bajista += 1.5
            razones.append(f"Mayoría longs ({ls_ratio:.2f}:1)")
        elif ls_ratio < 0.83:
            score_alcista += 1.5
            razones.append(f"Mayoría shorts ({1/ls_ratio:.2f}:1)")
        
        # Factor 2: Funding Rate estimado (2.0 pts)
        if funding > 0.01:
            score_bajista += 2.0
            razones.append(f"Funding positivo ({funding*100:.3f}%)")
        elif funding < -0.01:
            score_alcista += 2.0
            razones.append(f"Funding negativo ({funding*100:.3f}%)")
        elif funding > 0.005:
            score_bajista += 1.0
            razones.append("Funding ligeramente positivo")
        elif funding < -0.005:
            score_alcista += 1.0
            razones.append("Funding ligeramente negativo")
        
        # Factor 3: Buy/Sell ratio (1.5 pts)
        if buy_sell > 1.3:
            score_alcista += 1.5
            razones.append(f"Compras agresivas ({buy_sell:.2f}:1)")
        elif buy_sell < 0.77:
            score_bajista += 1.5
            razones.append(f"Ventas agresivas ({1/buy_sell:.2f}:1)")
        
        # Factor 4: RSI extremo (1.0 pt)
        if rsi > 70:
            score_bajista += 1.0
            razones.append(f"RSI sobrecompra ({rsi:.1f})")
        elif rsi < 30:
            score_alcista += 1.0
            razones.append(f"RSI sobreventa ({rsi:.1f})")
        
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
            'razones': razones
        }

# =======================================================================
# ORQUESTADOR PRINCIPAL
# =======================================================================

class PreNYAnalyzer:
    """Análisis completo pre-sesión NY usando solo yfinance"""
    
    def __init__(self, custom_ranges=None):
        self.corr_analyzer = CryptoCorrelationAnalyzer(CRYPTOS)
        self.tech_analyzer = TechnicalAnalyzer()
        self.custom_ranges = custom_ranges
    
    def ejecutar_analisis(self):
        """Ejecuta análisis completo"""
        
        ahora_tj = datetime.now(TIJUANA_TZ)
        ahora_ny = datetime.now(NY_TZ)
        
        print("="*80)
        print("🚀 ANALISIS PRE-SESION NY | CORRELACIONES + ANALISIS TECNICO")
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
        print("📈 PASO 2: ANALISIS TECNICO Y PREDICCIONES")
        print("="*80)
        
        resultados = []
        
        for ticker, info in CRYPTOS.items():
            if ticker not in self.corr_analyzer.datos_cache:
                continue
            
            datos = self.corr_analyzer.datos_cache[ticker]
            precio_actual = precios[ticker]
            
            print(f"\n--- {info['nombre']} ({ticker}) ---")
            print(f"💰 Precio: ${precio_actual:,.4f}")
            
            # Análisis técnico
            metrics = self.tech_analyzer.estimate_long_short_bias(datos)
            
            # Zonas de liquidación
            zones = self.tech_analyzer.estimate_liquidation_zones(
                precio_actual,
                metrics['ls_ratio'],
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
                
                high_risk_zones = [z for z in zones if "ALTO" in z['risk_level']]
                if high_risk_zones:
                    closest_high_risk = min(high_risk_zones, key=lambda x: abs(x['distance_pct']))
                    print(f"\n⚠️  ZONA CRÍTICA: ${closest_high_risk['price']:,.2f} "
                          f"({closest_high_risk['distance_pct']:+.1f}%) - "
                          f"{closest_high_risk['type'].replace('_ZONE', '')}")
            else:
                print("\n⚪ Sin zonas de liquidación significativas (ratio balanceado)")
            
            # Predicción
            prediccion = self.tech_analyzer.predict_direction(metrics)
            
            emoji = "🟢📈" if prediccion['direccion'] == 'ALCISTA' else "🔴📉" if prediccion['direccion'] == 'BAJISTA' else "⚪➡️"
            
            print(f"\n{emoji} PREDICCION: {prediccion['direccion']}")
            print(f"📊 Probabilidad: {prediccion['probabilidad']:.1f}%")
            print(f"📈 Long/Short Ratio (Estimado): {metrics['ls_ratio']:.2f} - {metrics['bias_text']}")
            print(f"💸 Funding Rate (Estimado): {metrics['funding_rate']*100:.4f}%")
            print(f"📊 Buy/Sell Ratio (Estimado): {metrics['buy_sell_ratio']:.2f}")
            print(f"📊 RSI: {metrics['rsi']:.1f}")
            print(f"📊 Momentum 24h: {metrics['momentum_24h']:+.2f}%")
            print(f"📊 Volatilidad: {metrics['volatility']*100:.2f}%")
            
            if prediccion['razones']:
                print(f"🎯 Factores Clave:")
                for razon in prediccion['razones']:
                    print(f"  • {razon}")
            
            resultados.append({
                'ticker': ticker,
                'nombre': info['nombre'],
                'precio': precio_actual,
                'direccion': prediccion['direccion'],
                'probabilidad': prediccion['probabilidad'],
                'ls_ratio': metrics['ls_ratio'],
                'funding_rate': metrics['funding_rate'],
                'zones_count': len(zones),
                'top_zone': zones[0] if zones else None
            })
        
        # RESUMEN FINAL
        print("\n" + "="*80)
        print("📋 RESUMEN EJECUTIVO")
        print("="*80)
        
        if resultados:
            resultados_ord = sorted(resultados, key=lambda x: x['probabilidad'], reverse=True)
            
            print("\n🎯 Señales Más Fuertes:")
            for i, r in enumerate(resultados_ord, 1):
                emoji = "🟢" if r['direccion'] == 'ALCISTA' else "🔴" if r['direccion'] == 'BAJISTA' else "⚪"
                print(f"  {i}. {emoji} {r['nombre']:15} | "
                      f"{r['direccion']:8} ({r['probabilidad']:.1f}%) | "
                      f"${r['precio']:,.4f}")
            
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
        
        print("\n💡 NOTA: Este análisis usa estimaciones basadas en price action")
        print("   ya que las APIs de exchange están bloqueadas en GitHub Actions.")
        print("   Los ratios L/S y funding son calculados usando RSI, momentum y volumen.")
        
        print("\n" + "="*80)
        print("✅ Análisis completado")
        print("="*80)
    
    def _tiempo_hasta_ny(self, ahora_ny):
        """Calcula tiempo hasta apertura NY (9:30 AM)"""
        apertura = ahora_ny.replace(hour=9, minute=30, second=0, microsecond=0)
        
        if ahora_ny.time() >= apertura.time():
            apertura += timedelta(days=1)
        
        delta = apertura - ahora_ny
        horas = int(delta.total_seconds() // 3600)
        minutos = int((delta.total_seconds() % 3600) // 60)
        
        return f"{horas}h {minutos}m"

# =======================================================================
# EJECUCION
# =======================================================================

if __name__ == "__main__":
    print("\n💡 Este código funciona 100% en GitHub Actions")
    print("   Usa solo yfinance (sin APIs de exchanges bloqueadas)\n")
    
    analyzer = PreNYAnalyzer()
    analyzer.ejecutar_analisis()
