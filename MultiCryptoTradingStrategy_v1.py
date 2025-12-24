import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class MultiCryptoTradingStrategy:
    """
    Estrategia de Trading Activo en Múltiples Criptomonedas
    Analiza: BTC, ETH, SOL, BNB, XRP
    Gestión de riesgo inspirada en Dalio
    Trading activo con selección de mejor oportunidad
    """
    
    def __init__(self, capital_inicial=10000):
        self.capital = capital_inicial
        self.max_riesgo_por_trade = 0.02  # 2% por operación
        self.max_posiciones_simultaneas = 2  # Máximo 2 cryptos al mismo tiempo
        
        # Cryptocurrencias a analizar
        self.cryptos = {
            'BTC-USD': {'nombre': 'Bitcoin', 'peso_min': 0.3},
            'ETH-USD': {'nombre': 'Ethereum', 'peso_min': 0.25},
            'SOL-USD': {'nombre': 'Solana', 'peso_min': 0.15},
            'BNB-USD': {'nombre': 'Binance Coin', 'peso_min': 0.15},
            'XRP-USD': {'nombre': 'Ripple', 'peso_min': 0.15}
        }
        
        self.posiciones_actuales = {}
        self.score_minimo = 50  # Score mínimo para considerar operación
        
    def es_dia_operativo(self):
        """Verifica si es día operativo (L-V)"""
        return datetime.now().weekday() < 5
    
    def descargar_datos_crypto(self, ticker, periodo='3mo', intervalo='1h'):
        """Descarga datos de una crypto"""
        try:
            datos = yf.download(ticker, period=periodo, interval=intervalo, progress=False)
            if datos.empty:
                return None
            
            # Si tiene multi-índice, aplanarlo
            if isinstance(datos.columns, pd.MultiIndex):
                datos.columns = datos.columns.get_level_values(0)
            
            return datos
        except Exception as e:
            print(f"Error descargando {ticker}: {e}")
            return None
    
    def calcular_indicadores(self, df):
        """Calcula todos los indicadores técnicos"""
        ind = df.copy()
        
        # RSI
        delta = ind['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        ind['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = ind['Close'].ewm(span=12, adjust=False).mean()
        exp2 = ind['Close'].ewm(span=26, adjust=False).mean()
        ind['MACD'] = exp1 - exp2
        ind['MACD_Signal'] = ind['MACD'].ewm(span=9, adjust=False).mean()
        
        # EMAs
        ind['EMA_9'] = ind['Close'].ewm(span=9, adjust=False).mean()
        ind['EMA_21'] = ind['Close'].ewm(span=21, adjust=False).mean()
        ind['EMA_50'] = ind['Close'].ewm(span=50, adjust=False).mean()
        ind['EMA_200'] = ind['Close'].ewm(span=200, adjust=False).mean()
        
        # Bandas de Bollinger
        bb_middle = ind['Close'].rolling(window=20).mean()
        bb_std = ind['Close'].rolling(window=20).std()
        ind['BB_Middle'] = bb_middle
        ind['BB_Upper'] = bb_middle + (bb_std * 2)
        ind['BB_Lower'] = bb_middle - (bb_std * 2)
        
        # Volatilidad
        ind['Volatilidad'] = ind['Close'].pct_change().rolling(window=24).std()
        
        # Volumen
        vol_sma = ind['Volume'].rolling(window=20).mean()
        ind['Vol_SMA'] = vol_sma
        ind['Vol_Ratio'] = ind['Volume'] / vol_sma
        
        return ind
    
    def analizar_crypto(self, ticker, indicadores):
        """Analiza una crypto y genera score"""
        if len(indicadores) < 200:
            return None
        
        ultima = indicadores.iloc[-1]
        
        # Extraer valores escalares usando .item() o indexación
        try:
            # Método más seguro: convertir a dict primero
            ultima_dict = ultima.to_dict()
            
            precio = float(ultima_dict['Close'])
            rsi_val = float(ultima_dict['RSI']) if not np.isnan(ultima_dict['RSI']) else 50
            macd_val = float(ultima_dict['MACD']) if not np.isnan(ultima_dict['MACD']) else 0
            macd_signal = float(ultima_dict['MACD_Signal']) if not np.isnan(ultima_dict['MACD_Signal']) else 0
            ema_9 = float(ultima_dict['EMA_9']) if not np.isnan(ultima_dict['EMA_9']) else precio
            ema_21 = float(ultima_dict['EMA_21']) if not np.isnan(ultima_dict['EMA_21']) else precio
            ema_50 = float(ultima_dict['EMA_50']) if not np.isnan(ultima_dict['EMA_50']) else precio
            ema_200 = float(ultima_dict['EMA_200']) if not np.isnan(ultima_dict['EMA_200']) else precio
            bb_lower = float(ultima_dict['BB_Lower']) if not np.isnan(ultima_dict['BB_Lower']) else precio * 0.95
            bb_upper = float(ultima_dict['BB_Upper']) if not np.isnan(ultima_dict['BB_Upper']) else precio * 1.05
            volatilidad = float(ultima_dict['Volatilidad']) if not np.isnan(ultima_dict['Volatilidad']) else 0.05
            vol_ratio = float(ultima_dict['Vol_Ratio']) if not np.isnan(ultima_dict['Vol_Ratio']) else 1.0
        except Exception as e:
            print(f"Error extrayendo valores de {ticker}: {e}")
            return None
        
        scores = []
        razones = []
        
        # 1. RSI
        if rsi_val < 30:
            scores.append(25)
            razones.append(f"RSI sobreventa ({rsi_val:.1f})")
        elif rsi_val > 70:
            scores.append(-25)
            razones.append(f"RSI sobrecompra ({rsi_val:.1f})")
        else:
            scores.append((50 - rsi_val) / 5)
        
        # 2. MACD
        if macd_val > macd_signal:
            scores.append(20)
            razones.append("MACD alcista")
        else:
            scores.append(-20)
            razones.append("MACD bajista")
        
        # 3. Tendencia EMAs
        ema_score = 0
        if ema_9 > ema_21:
            ema_score += 15
            razones.append("Tendencia corto plazo alcista")
        else:
            ema_score -= 15
        
        if precio > ema_50:
            ema_score += 10
        else:
            ema_score -= 10
        
        scores.append(ema_score)
        
        # 4. Bandas de Bollinger
        if precio < bb_lower:
            scores.append(20)
            razones.append("Precio en banda inferior")
        elif precio > bb_upper:
            scores.append(-20)
            razones.append("Precio en banda superior")
        else:
            scores.append(0)
        
        # 5. Momentum
        mom_24h = 0
        mom_7d = 0
        if len(indicadores) >= 168:
            try:
                close_series = indicadores['Close'].values  # Convertir a numpy array
                precio_actual = float(close_series[-1])
                precio_24h = float(close_series[-24])
                precio_7d = float(close_series[-168])
                mom_24h = (precio_actual / precio_24h - 1) * 100
                mom_7d = (precio_actual / precio_7d - 1) * 100
                momentum = (mom_24h * 0.6 + mom_7d * 0.4)
                scores.append(np.clip(momentum, -20, 20))
                
                if abs(momentum) > 5:
                    razones.append(f"Momentum {momentum:+.1f}%")
            except:
                pass
        
        # 6. Volumen
        if vol_ratio > 1.5:
            scores.append(10)
            razones.append("Volumen alto")
        elif vol_ratio < 0.6:
            scores.append(-5)
        else:
            scores.append(0)
        
        # 7. Filtro de tendencia macro
        if precio > ema_200:
            scores.append(10)
            razones.append("Por encima de EMA 200")
        else:
            scores.append(-10)
        
        # 8. Ajuste por volatilidad
        if volatilidad > 0.06:
            scores = [s * 0.8 for s in scores]
            razones.append("Alta volatilidad - señal reducida")
        
        score_final = sum(scores)
        
        return {
            'ticker': ticker,
            'precio': precio,
            'score': score_final,
            'razones': razones,
            'volatilidad': volatilidad,
            'rsi': rsi_val,
            'momentum_24h': mom_24h,
            'momentum_7d': mom_7d,
            'volumen_ratio': vol_ratio,
            'ema_200': ema_200,
            'bb_lower': bb_lower,
            'bb_upper': bb_upper
        }
    
    def calcular_correlaciones(self, datos_multiple):
        """Calcula correlaciones entre cryptos"""
        retornos = pd.DataFrame()
        
        for ticker, datos in datos_multiple.items():
            if datos is not None and len(datos) > 0:
                retornos[ticker] = datos['Close'].pct_change()
        
        if len(retornos.columns) < 2:
            return None
        
        return retornos.corr()
    
    def seleccionar_mejor_oportunidad(self, analisis_cryptos):
        """Selecciona la mejor crypto para operar según score y diversificación"""
        # Filtrar solo señales válidas
        validas = [a for a in analisis_cryptos if a['score'] > self.score_minimo or a['score'] < -self.score_minimo]
        
        if not validas:
            return None, "No hay señales suficientemente fuertes"
        
        # Ordenar por score absoluto (fuerza de la señal)
        validas_ordenadas = sorted(validas, key=lambda x: abs(x['score']), reverse=True)
        
        # Verificar si ya tenemos posiciones
        if len(self.posiciones_actuales) >= self.max_posiciones_simultaneas:
            return None, f"Ya tienes {self.max_posiciones_simultaneas} posiciones abiertas"
        
        # Seleccionar mejor oportunidad
        mejor = validas_ordenadas[0]
        
        return mejor, "OK"
    
    def calcular_tamaño_posicion(self, precio, volatilidad, score):
        """Calcula tamaño de posición con gestión de riesgo"""
        # Riesgo base
        riesgo_dolares = self.capital * self.max_riesgo_por_trade
        
        # Ajustar por volatilidad
        factor_vol = min(0.04 / volatilidad, 2.0) if volatilidad > 0 else 1.0
        
        # Ajustar por confianza
        factor_confianza = abs(score) / 100
        
        # Calcular cantidad
        cantidad = (riesgo_dolares * factor_vol * factor_confianza) / precio
        
        # Límite máximo: 30% del capital por crypto
        cantidad_max = (self.capital * 0.30) / precio
        cantidad = min(cantidad, cantidad_max)
        
        return cantidad, factor_confianza
    
    def calcular_apalancamiento(self, volatilidad, confianza):
        """Calcula apalancamiento recomendado"""
        if volatilidad < 0.03:
            apal_base = 3
        elif volatilidad < 0.05:
            apal_base = 2
        else:
            apal_base = 1
        
        if confianza > 0.7:
            mult = 1.0
        elif confianza > 0.55:
            mult = 0.75
        else:
            mult = 0.5
        
        apal = int(apal_base * mult)
        return max(1, min(apal, 3))
    
    def ejecutar_estrategia(self):
        """Función principal de trading"""
        print("="*80)
        print(f"ESTRATEGIA MULTI-CRYPTO TRADING - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Verificar día operativo
        if not self.es_dia_operativo():
            print("\n❌ Fin de semana - No operar")
            return None
        
        print(f"\n✅ Día operativo: {datetime.now().strftime('%A')}")
        print(f"Capital disponible: ${self.capital:,.2f}")
        print(f"Posiciones actuales: {len(self.posiciones_actuales)}/{self.max_posiciones_simultaneas}")
        
        # Descargar datos de todas las cryptos
        print("\n" + "="*80)
        print("DESCARGANDO DATOS")
        print("="*80)
        
        datos_cryptos = {}
        for ticker, info in self.cryptos.items():
            print(f"Descargando {info['nombre']} ({ticker})...", end=" ")
            datos = self.descargar_datos_crypto(ticker)
            if datos is not None and len(datos) > 200:
                datos_cryptos[ticker] = datos
                print(f"✅ {len(datos)} registros")
            else:
                print("❌ Error")
        
        if len(datos_cryptos) == 0:
            print("\n❌ No se pudieron descargar datos")
            return None
        
        # Calcular correlaciones
        print("\n" + "="*80)
        print("ANALISIS DE CORRELACIONES")
        print("="*80)
        
        correlaciones = self.calcular_correlaciones(datos_cryptos)
        if correlaciones is not None:
            print("\nCorrelaciones entre cryptos:")
            print(correlaciones.round(3))
        
        # Analizar cada crypto
        print("\n" + "="*80)
        print("ANALISIS INDIVIDUAL DE CADA CRYPTO")
        print("="*80)
        
        analisis_todas = []
        
        for ticker in datos_cryptos.keys():
            print(f"\n--- {self.cryptos[ticker]['nombre']} ({ticker}) ---")
            
            indicadores = self.calcular_indicadores(datos_cryptos[ticker])
            analisis = self.analizar_crypto(ticker, indicadores)
            
            if analisis:
                analisis_todas.append(analisis)
                
                print(f"Precio: ${analisis['precio']:,.4f}")
                print(f"Score: {analisis['score']:.1f}/100")
                print(f"RSI: {analisis['rsi']:.1f}")
                print(f"Momentum 24h: {analisis['momentum_24h']:+.2f}%")
                print(f"Momentum 7d: {analisis['momentum_7d']:+.2f}%")
                print(f"Volatilidad: {analisis['volatilidad']*100:.2f}%")
                print(f"Volumen: {analisis['volumen_ratio']:.2f}x promedio")
                print(f"\nRazones principales:")
                for razon in analisis['razones'][:3]:
                    print(f"  • {razon}")
        
        # Ranking de oportunidades
        print("\n" + "="*80)
        print("RANKING DE OPORTUNIDADES")
        print("="*80)
        
        # Separar señales alcistas y bajistas
        señales_long = [a for a in analisis_todas if a['score'] > self.score_minimo]
        señales_short = [a for a in analisis_todas if a['score'] < -self.score_minimo]
        
        if señales_long:
            print("\n🟢 SEÑALES DE COMPRA (LONG):")
            señales_long_ord = sorted(señales_long, key=lambda x: x['score'], reverse=True)
            for i, s in enumerate(señales_long_ord, 1):
                print(f"  {i}. {s['ticker']}: Score {s['score']:.1f} - ${s['precio']:,.4f}")
        
        if señales_short:
            print("\n🔴 SEÑALES DE VENTA (SHORT):")
            señales_short_ord = sorted(señales_short, key=lambda x: x['score'])
            for i, s in enumerate(señales_short_ord, 1):
                print(f"  {i}. {s['ticker']}: Score {s['score']:.1f} - ${s['precio']:,.4f}")
        
        if not señales_long and not señales_short:
            print("\n🟡 NO HAY SEÑALES FUERTES HOY")
            print(f"Score mínimo requerido: ±{self.score_minimo}")
            return None
        
        # Seleccionar mejor oportunidad
        mejor_op, mensaje = self.seleccionar_mejor_oportunidad(analisis_todas)
        
        if mejor_op is None:
            print(f"\n❌ {mensaje}")
            return None
        
        # Presentar mejor oportunidad
        print("\n" + "="*80)
        print("MEJOR OPORTUNIDAD DETECTADA")
        print("="*80)
        
        ticker = mejor_op['ticker']
        nombre = self.cryptos[ticker]['nombre']
        precio = mejor_op['precio']
        score = mejor_op['score']
        
        print(f"\n{'🟢 COMPRAR' if score > 0 else '🔴 VENDER'} {nombre} ({ticker})")
        print(f"Precio actual: ${precio:,.4f}")
        print(f"Score: {score:.1f}/100")
        
        # Calcular posición
        cantidad, confianza = self.calcular_tamaño_posicion(precio, mejor_op['volatilidad'], score)
        valor_posicion = cantidad * precio
        apalancamiento = self.calcular_apalancamiento(mejor_op['volatilidad'], confianza)
        
        print(f"\n📊 TAMAÑO DE POSICION:")
        print(f"  Cantidad: {cantidad:.6f} {ticker.replace('-USD', '')}")
        print(f"  Valor: ${valor_posicion:,.2f}")
        print(f"  % del capital: {(valor_posicion/self.capital)*100:.1f}%")
        print(f"  Confianza: {confianza*100:.1f}%")
        
        print(f"\n⚙️ APALANCAMIENTO: {apalancamiento}x")
        print(f"  Exposición total: ${valor_posicion * apalancamiento:,.2f}")
        print(f"  Distancia liquidación: ~{(100/apalancamiento):.1f}%")
        
        # Precio de entrada
        print(f"\n💰 PRECIOS DE ENTRADA:")
        if score > 0:  # LONG
            entrada_ideal = mejor_op['bb_lower'] if precio > mejor_op['bb_lower'] * 1.02 else precio
            print(f"  Entrada inmediata: ${precio:,.4f}")
            print(f"  Entrada ideal: ${entrada_ideal:,.4f}")
            
            stop_loss = precio * 0.97
            take_profit = precio * 1.05
        else:  # SHORT
            entrada_ideal = mejor_op['bb_upper'] if precio < mejor_op['bb_upper'] * 0.98 else precio
            print(f"  Entrada inmediata: ${precio:,.4f}")
            print(f"  Entrada ideal: ${entrada_ideal:,.4f}")
            
            stop_loss = precio * 1.03
            take_profit = precio * 0.95
        
        print(f"\n⚠️ GESTION DE RIESGO:")
        print(f"  Stop Loss: ${stop_loss:,.4f} ({'−' if score > 0 else '+'}3%)")
        print(f"  Take Profit: ${take_profit:,.4f} ({'+' if score > 0 else '−'}5%)")
        
        perdida_max = abs(precio - stop_loss) * cantidad * apalancamiento
        ganancia_obj = abs(precio - take_profit) * cantidad * apalancamiento
        
        print(f"  Pérdida máxima: ${perdida_max:,.2f}")
        print(f"  Ganancia objetivo: ${ganancia_obj:,.2f}")
        print(f"  Ratio R/R: 1:{(ganancia_obj/perdida_max):.2f}")
        
        # Plan de ejecución
        print(f"\n📝 PLAN DE EJECUCION:")
        print(f"  1. {'Comprar' if score > 0 else 'Vender en corto'} {cantidad:.6f} {ticker.replace('-USD', '')}")
        print(f"  2. Precio objetivo: ${entrada_ideal:,.4f}")
        print(f"  3. Apalancamiento: {apalancamiento}x")
        print(f"  4. Stop Loss: ${stop_loss:,.4f}")
        print(f"  5. Take Profit: ${take_profit:,.4f}")
        
        print(f"\n💡 RAZONES DE LA SEÑAL:")
        for i, razon in enumerate(mejor_op['razones'][:5], 1):
            print(f"  {i}. {razon}")
        
        print("\n" + "="*80)
        print("⚠️ RECUERDA:")
        print("  - Esto es trading activo, requiere seguimiento constante")
        print("  - Usa stop loss SIEMPRE")
        print("  - Nunca arriesgues más del 2% por operación")
        print("  - Considera fees del exchange (0.1-0.5%)")
        print("="*80)
        
        return {
            'timestamp': datetime.now(),
            'crypto': ticker,
            'nombre': nombre,
            'accion': 'LONG' if score > 0 else 'SHORT',
            'precio': precio,
            'cantidad': cantidad,
            'score': score,
            'apalancamiento': apalancamiento,
            'stop_loss': stop_loss,
            'take_profit': take_profit
        }


# EJECUCIÓN PRINCIPAL
if __name__ == "__main__":
    print("\n" + "="*80)
    print("ESTRATEGIA DE TRADING ACTIVO EN CRIPTOMONEDAS")
    print("="*80)
    print("\nCRYPTOS ANALIZADAS:")
    print("  • Bitcoin (BTC)")
    print("  • Ethereum (ETH)")
    print("  • Solana (SOL)")
    print("  • Binance Coin (BNB)")
    print("  • Ripple (XRP)")
    print("\nCARACTERISTICAS:")
    print("  • Análisis técnico multi-indicador")
    print("  • Selección automática de mejor oportunidad")
    print("  • Gestión de riesgo por operación")
    print("  • Máximo 2 posiciones simultáneas")
    print("  • Apalancamiento dinámico (1-3x)")
    print("="*80 + "\n")
    
    estrategia = MultiCryptoTradingStrategy(capital_inicial=10000)
    resultado = estrategia.ejecutar_estrategia()
    
    if resultado:
        print(f"\n✅ SEÑAL GENERADA: {resultado['accion']} {resultado['nombre']}")
        print(f"Score: {resultado['score']:.1f}/100")
        print(f"Precio: ${resultado['precio']:,.4f}")
    else:
        print("\n🟡 No hay oportunidades de trading hoy")
        print("Mantener posiciones actuales o esperar mejores señales")
