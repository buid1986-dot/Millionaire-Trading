"""
================================================================================
ESTRATEGIA DE TRADING ACTIVO EN CRIPTOMONEDAS
================================================================================

Autor: Inspirado en principios de Ray Dalio
Versión: 2.0
Última actualización: Diciembre 2024
Zona Horaria: America/Tijuana (PST/PDT)

DESCRIPCIÓN:
-----------
Sistema automatizado de trading para múltiples criptomonedas que combina
análisis técnico multi-indicador con gestión de riesgo profesional.

CRIPTOMONEDAS ANALIZADAS:
-------------------------
• Bitcoin (BTC-USD)      - Rey del mercado, más estable
• Ethereum (ETH-USD)     - Smart contracts, líder DeFi
• Solana (SOL-USD)       - Alta velocidad, alto potencial
• Binance Coin (BNB-USD) - Token de exchange
• Ripple (XRP-USD)       - Pagos internacionales

CARACTERÍSTICAS PRINCIPALES:
---------------------------
✓ Análisis técnico multi-indicador (RSI, MACD, EMAs, Bollinger, Momentum)
✓ Selección automática de mejor oportunidad
✓ Gestión de riesgo: máximo 2% por operación
✓ Máximo 2 posiciones simultáneas
✓ Apalancamiento dinámico (1-3x) según volatilidad
✓ Control de correlaciones entre activos

INDICADORES TÉCNICOS UTILIZADOS:
--------------------------------
1. RSI (14 períodos) - Sobreventa/Sobrecompra
2. MACD (12,26,9) - Momentum y cambios de tendencia
3. EMAs (9,21,50,200) - Dirección de tendencia
4. Bandas de Bollinger (20,2) - Volatilidad y extremos
5. Momentum (24h y 7d) - Fuerza del movimiento
6. Volumen relativo - Validación de movimientos
7. ATR - Medida de volatilidad real

SISTEMA DE SCORING:
------------------
Score de -100 a +100:
• > +50: Señal de COMPRA (LONG)
• < -50: Señal de VENTA (SHORT)
• -50 a +50: NO OPERAR (señal débil)

GESTIÓN DE RIESGO:
-----------------
• Riesgo máximo: 2% del capital por operación
• Stop Loss: -3% del precio de entrada
• Take Profit: +5% del precio de entrada
• Apalancamiento máximo: 3x
• Máximo 2 posiciones simultáneas

HORARIOS RECOMENDADOS (TIJUANA):
--------------------------------
• 06:00-08:00 AM - Pre-apertura NYSE
• 09:00-11:00 AM - Apertura NYSE (alta volatilidad)
• 11:00 AM-01:00 PM - Media sesión (buen volumen)
• 01:00-03:00 PM - Cierre NYSE

EVITAR:
• 05:00-06:00 PM - Bajo volumen
• Fines de semana - Movimientos erráticos

CONFIGURACIÓN GITHUB ACTIONS:
----------------------------
Ejecutar 2-3 veces al día en horarios óptimos:

```yaml
on:
  schedule:
    - cron: '30 16 * * 1-5'  # 08:30 AM Tijuana
    - cron: '0 19 * * 1-5'   # 11:00 AM Tijuana
```

USO:
----
```python
# Ejecución básica
estrategia = MultiCryptoTradingStrategy(capital_inicial=10000)
resultado = estrategia.ejecutar_estrategia()

# Configuración conservadora
estrategia.max_posiciones_simultaneas = 1
estrategia.score_minimo = 60

# Configuración agresiva
estrategia.max_posiciones_simultaneas = 3
estrategia.score_minimo = 45
```

DEPENDENCIAS:
------------
pip install yfinance pandas numpy

ADVERTENCIAS:
------------
⚠️  Este es un sistema de trading activo - requiere seguimiento constante
⚠️  Siempre usa Stop Loss
⚠️  Empieza con capital pequeño ($500-1000)
⚠️  Considera fees del exchange (0.1-0.5%)
⚠️  No hagas overtrading - calidad sobre cantidad

LIMITACIONES:
------------
• No considera noticias fundamentales
• Basado solo en análisis técnico
• Sensible a manipulación de mercado (whales)
• Requiere liquidez adecuada en exchange

PRÓXIMAS MEJORAS:
----------------
□ Backtesting automático con datos históricos
□ Machine Learning para optimizar scores
□ Análisis de sentimiento de redes sociales
□ Integración con exchanges (Binance API)
□ Dashboard web con historial de trades

================================================================================
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from pytz import timezone
import warnings
warnings.filterwarnings('ignore')

# Configurar zona horaria de Tijuana
TZ_TIJUANA = timezone('America/Tijuana')

class MultiCryptoTradingStrategy:
    """
    Estrategia de Trading Activo en Múltiples Criptomonedas
    
    Esta clase implementa un sistema completo de trading que:
    1. Descarga datos de 5 criptomonedas principales
    2. Calcula indicadores técnicos avanzados
    3. Genera scores de trading
    4. Selecciona la mejor oportunidad
    5. Calcula tamaño de posición con gestión de riesgo
    6. Determina apalancamiento óptimo
    
    Attributes:
        capital (float): Capital inicial disponible
        max_riesgo_por_trade (float): Porcentaje máximo a arriesgar (default: 0.02 = 2%)
        max_posiciones_simultaneas (int): Máximo de cryptos simultáneas (default: 2)
        score_minimo (int): Score mínimo para operar (default: 50)
        
    Example:
        >>> estrategia = MultiCryptoTradingStrategy(capital_inicial=10000)
        >>> resultado = estrategia.ejecutar_estrategia()
        >>> if resultado:
        ...     print(f"Acción: {resultado['accion']}")
    """
    
    def __init__(self, capital_inicial=10000):
        """
        Inicializa la estrategia de trading.
        
        Args:
            capital_inicial (float): Capital disponible en USD (default: 10000)
        """
        self.capital = capital_inicial
        self.max_riesgo_por_trade = 0.02  # 2% máximo por operación
        self.max_posiciones_simultaneas = 2  # Máximo 2 cryptos al mismo tiempo
        self.tz = TZ_TIJUANA  # Zona horaria de Tijuana
        
        # Cryptocurrencias a analizar con pesos mínimos recomendados
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
        """
        Verifica si hoy es día operativo (Lunes-Viernes).
        
        Aunque crypto opera 24/7, seguimos el calendario tradicional
        porque el volumen es mucho mayor en días laborables.
        
        Returns:
            bool: True si es L-V, False si es fin de semana
        """
        ahora_tijuana = datetime.now(self.tz)
        return ahora_tijuana.weekday() < 5
    
    def descargar_datos_crypto(self, ticker, periodo='3mo', intervalo='1h'):
        """
        Descarga datos históricos de una criptomoneda desde Yahoo Finance.
        
        Args:
            ticker (str): Símbolo de la crypto (ej: 'BTC-USD')
            periodo (str): Período de datos ('1mo', '3mo', '6mo', '1y')
            intervalo (str): Intervalo de velas ('1h', '1d', '1wk')
            
        Returns:
            DataFrame: Datos OHLCV o None si hay error
            
        Note:
            - yfinance puede devolver columnas con multi-índice
            - Se aplana automáticamente para simplificar
        """
        try:
            datos = yf.download(ticker, period=periodo, interval=intervalo, progress=False)
            if datos.empty:
                return None
            
            # Si tiene multi-índice, aplanarlo
            # Esto ocurre cuando yfinance devuelve ('Close', 'BTC-USD')
            if isinstance(datos.columns, pd.MultiIndex):
                datos.columns = datos.columns.get_level_values(0)
            
            return datos
        except Exception as e:
            print(f"Error descargando {ticker}: {e}")
            return None
    
    def calcular_indicadores(self, df):
        """
        Calcula todos los indicadores técnicos necesarios para el análisis.
        
        Indicadores incluidos:
        - RSI (14): Relative Strength Index
        - MACD (12,26,9): Moving Average Convergence Divergence
        - EMAs (9,21,50,200): Exponential Moving Averages
        - Bandas de Bollinger (20,2): Volatilidad
        - Volatilidad (24h): Desviación estándar de retornos
        - Volumen relativo: Ratio vs promedio 20 períodos
        
        Args:
            df (DataFrame): DataFrame con columnas OHLCV
            
        Returns:
            DataFrame: DataFrame original + columnas de indicadores
        """
        ind = df.copy()
        
        # === RSI (Relative Strength Index) ===
        # Mide momentum: <30 sobreventa, >70 sobrecompra
        delta = ind['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        ind['RSI'] = 100 - (100 / (1 + rs))
        
        # === MACD (Moving Average Convergence Divergence) ===
        # Detecta cambios de momentum y tendencia
        exp1 = ind['Close'].ewm(span=12, adjust=False).mean()
        exp2 = ind['Close'].ewm(span=26, adjust=False).mean()
        ind['MACD'] = exp1 - exp2
        ind['MACD_Signal'] = ind['MACD'].ewm(span=9, adjust=False).mean()
        
        # === EMAs (Exponential Moving Averages) ===
        # Definen tendencia en diferentes timeframes
        ind['EMA_9'] = ind['Close'].ewm(span=9, adjust=False).mean()      # Muy corto plazo
        ind['EMA_21'] = ind['Close'].ewm(span=21, adjust=False).mean()    # Corto plazo
        ind['EMA_50'] = ind['Close'].ewm(span=50, adjust=False).mean()    # Medio plazo
        ind['EMA_200'] = ind['Close'].ewm(span=200, adjust=False).mean()  # Largo plazo (tendencia macro)
        
        # === Bandas de Bollinger ===
        # Miden volatilidad y extremos de precio
        bb_middle = ind['Close'].rolling(window=20).mean()
        bb_std = ind['Close'].rolling(window=20).std()
        ind['BB_Middle'] = bb_middle
        ind['BB_Upper'] = bb_middle + (bb_std * 2)  # +2 desviaciones estándar
        ind['BB_Lower'] = bb_middle - (bb_std * 2)  # -2 desviaciones estándar
        
        # === Volatilidad ===
        # Desviación estándar de retornos horarios
        ind['Volatilidad'] = ind['Close'].pct_change().rolling(window=24).std()
        
        # === Volumen Relativo ===
        # Ratio del volumen actual vs promedio 20 períodos
        vol_sma = ind['Volume'].rolling(window=20).mean()
        ind['Vol_SMA'] = vol_sma
        ind['Vol_Ratio'] = ind['Volume'] / vol_sma
        
        return ind
    
    def analizar_crypto(self, ticker, indicadores):
        """
        Analiza una criptomoneda y genera un score de trading.
        
        Sistema de Scoring (suma de todos los factores):
        1. RSI: ±25 puntos (sobreventa/sobrecompra)
        2. MACD: ±20 puntos (momentum)
        3. EMAs: ±25 puntos (tendencia)
        4. Bollinger: ±20 puntos (extremos)
        5. Momentum: ±20 puntos (24h + 7d)
        6. Volumen: ±10 puntos (confirmación)
        7. EMA 200: ±10 puntos (tendencia macro)
        8. Ajuste volatilidad: ×0.8 si muy alta
        
        Args:
            ticker (str): Símbolo de la crypto
            indicadores (DataFrame): DataFrame con indicadores calculados
            
        Returns:
            dict: Diccionario con análisis completo o None si error
            {
                'ticker': str,
                'precio': float,
                'score': float,
                'razones': list,
                'volatilidad': float,
                'rsi': float,
                'momentum_24h': float,
                'momentum_7d': float,
                ...
            }
        """
        if len(indicadores) < 200:
            return None
        
        ultima = indicadores.iloc[-1]
        
        # Extraer valores escalares usando to_dict() para evitar problemas con Series
        try:
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
        
        # === 1. RSI (Relative Strength Index) ===
        # <30 = sobreventa (oportunidad compra), >70 = sobrecompra (posible venta)
        if rsi_val < 30:
            scores.append(25)
            razones.append(f"RSI sobreventa ({rsi_val:.1f})")
        elif rsi_val > 70:
            scores.append(-25)
            razones.append(f"RSI sobrecompra ({rsi_val:.1f})")
        else:
            scores.append((50 - rsi_val) / 5)
        
        # === 2. MACD (Momentum) ===
        # MACD > Signal = momentum alcista
        if macd_val > macd_signal:
            scores.append(20)
            razones.append("MACD alcista")
        else:
            scores.append(-20)
            razones.append("MACD bajista")
        
        # === 3. Tendencia EMAs ===
        # EMA corta > EMA larga = tendencia alcista
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
        
        # === 4. Bandas de Bollinger ===
        # Precio en banda inferior = oversold, posible rebote
        if precio < bb_lower:
            scores.append(20)
            razones.append("Precio en banda inferior")
        elif precio > bb_upper:
            scores.append(-20)
            razones.append("Precio en banda superior")
        else:
            scores.append(0)
        
        # === 5. Momentum Multi-Timeframe ===
        # Combina momentum de 24h (60%) y 7d (40%)
        mom_24h = 0
        mom_7d = 0
        if len(indicadores) >= 168:
            try:
                close_series = indicadores['Close'].values
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
        
        # === 6. Volumen ===
        # Volumen alto confirma el movimiento
        if vol_ratio > 1.5:
            scores.append(10)
            razones.append("Volumen alto")
        elif vol_ratio < 0.6:
            scores.append(-5)
        else:
            scores.append(0)
        
        # === 7. Filtro de Tendencia Macro (EMA 200) ===
        # Precio > EMA200 = bull market
        if precio > ema_200:
            scores.append(10)
            razones.append("Por encima de EMA 200")
        else:
            scores.append(-10)
        
        # === 8. Ajuste por Volatilidad Extrema ===
        # Si volatilidad >6%, reducir agresividad
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
        """
        Calcula matriz de correlaciones entre criptomonedas.
        
        Alta correlación (>0.8) indica que se mueven juntas.
        Baja correlación (<0.5) indica movimientos independientes.
        
        Args:
            datos_multiple (dict): Diccionario {ticker: DataFrame}
            
        Returns:
            DataFrame: Matriz de correlaciones o None
        """
        retornos = pd.DataFrame()
        
        for ticker, datos in datos_multiple.items():
            if datos is not None and len(datos) > 0:
                retornos[ticker] = datos['Close'].pct_change()
        
        if len(retornos.columns) < 2:
            return None
        
        return retornos.corr()
    
    def seleccionar_mejor_oportunidad(self, analisis_cryptos):
        """
        Selecciona la mejor crypto para operar según score y diversificación.
        
        Criterios:
        1. Score debe superar score_minimo (±50)
        2. Ordenar por score absoluto (fuerza de señal)
        3. Verificar límite de posiciones simultáneas
        
        Args:
            analisis_cryptos (list): Lista de análisis de cada crypto
            
        Returns:
            tuple: (mejor_analisis, mensaje) o (None, razon)
        """
        # Filtrar solo señales válidas (score > umbral)
        validas = [a for a in analisis_cryptos if a['score'] > self.score_minimo or a['score'] < -self.score_minimo]
        
        if not validas:
            return None, "No hay señales suficientemente fuertes"
        
        # Ordenar por score absoluto (fuerza de la señal)
        validas_ordenadas = sorted(validas, key=lambda x: abs(x['score']), reverse=True)
        
        # Verificar si ya tenemos el máximo de posiciones
        if len(self.posiciones_actuales) >= self.max_posiciones_simultaneas:
            return None, f"Ya tienes {self.max_posiciones_simultaneas} posiciones abiertas"
        
        # Seleccionar la mejor
        mejor = validas_ordenadas[0]
        
        return mejor, "OK"
    
    def calcular_tamaño_posicion(self, precio, volatilidad, score):
        """
        Calcula el tamaño de posición óptimo usando gestión de riesgo.
        
        Fórmula inspirada en Kelly Criterion y Paridad de Riesgo:
        Tamaño = (Riesgo_Base * Factor_Volatilidad * Factor_Confianza) / Precio
        
        Factores:
        - Riesgo base: 2% del capital
        - Factor volatilidad: Reduce si vol > 4%
        - Factor confianza: Score/100 (mayor score = mayor posición)
        - Límite máximo: 30% del capital
        
        Args:
            precio (float): Precio actual de la crypto
            volatilidad (float): Volatilidad horaria
            score (float): Score de la señal
            
        Returns:
            tuple: (cantidad, confianza)
        """
        # Riesgo base: 2% del capital total
        riesgo_dolares = self.capital * self.max_riesgo_por_trade
        
        # Ajustar por volatilidad
        # Si vol = 4%, factor = 1.0
        # Si vol = 8%, factor = 0.5 (reducir posición)
        factor_vol = min(0.04 / volatilidad, 2.0) if volatilidad > 0 else 1.0
        
        # Ajustar por confianza en la señal
        factor_confianza = abs(score) / 100
        
        # Calcular cantidad en crypto
        cantidad = (riesgo_dolares * factor_vol * factor_confianza) / precio
        
        # Límite máximo: 30% del capital por crypto
        cantidad_max = (self.capital * 0.30) / precio
        cantidad = min(cantidad, cantidad_max)
        
        return cantidad, factor_confianza
    
    def calcular_apalancamiento(self, volatilidad, confianza):
        """
        Calcula apalancamiento recomendado basado en volatilidad y confianza.
        
        Reglas conservadoras:
        - Volatilidad <3%: máximo 3x
        - Volatilidad 3-5%: máximo 2x
        - Volatilidad >5%: solo 1x (sin apalancamiento)
        
        Ajuste por confianza:
        - Confianza >70%: 100% del apalancamiento base
        - Confianza 55-70%: 75% del apalancamiento base
        - Confianza <55%: 50% del apalancamiento base
        
        Args:
            volatilidad (float): Volatilidad de la crypto
            confianza (float): Nivel de confianza (0-1)
            
        Returns:
            int: Apalancamiento recomendado (1-3x)
        """
        # Determinar apalancamiento base por volatilidad
        if volatilidad < 0.03:
            apal_base = 3
        elif volatilidad < 0.05:
            apal_base = 2
        else:
            apal_base = 1
        
        # Ajustar por confianza
        if confianza > 0.7:
            mult = 1.0
        elif confianza > 0.55:
            mult = 0.75
        else:
            mult = 0.5
        
        apal = int(apal_base * mult)
        return max(1, min(apal, 3))  # Entre 1x y 3x
    
    def ejecutar_estrategia(self):
        """
        Función principal que ejecuta toda la estrategia de trading.
        
        Flujo de ejecución:
        1. Verificar día operativo
        2. Descargar datos de las 5 cryptos
        3. Calcular correlaciones
        4. Analizar cada crypto individualmente
        5. Ranking de oportunidades
        6. Seleccionar mejor oportunidad
        7. Calcular tamaño de posición y apalancamiento
        8. Mostrar plan de ejecución completo
        
        Returns:
            dict: Resultado del análisis con detalles de la operación
            {
                'timestamp': datetime,
                'crypto': str,
                'nombre': str,
                'accion': 'LONG' o 'SHORT',
                'precio': float,
                'cantidad': float,
                'score': float,
                'apalancamiento': int,
                'stop_loss': float,
                'take_profit': float
            }
            
        Returns None si:
        - No es día operativo
        - No se pueden descargar datos
        - No hay señales fuertes
        - Ya se alcanzó el máximo de posiciones
        """
        print("="*80)
        ahora_tijuana = datetime.now(self.tz)
        print(f"ESTRATEGIA MULTI-CRYPTO TRADING - {ahora_tijuana.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print("="*80)
        
        # === PASO 1: Verificar día operativo ===
        if not self.es_dia_operativo():
            print("\nFin de semana - No operar")
            print("Crypto opera 24/7 pero volumen es bajo en weekends")
            return None
        
        print(f"\nDia operativo: {ahora_tijuana.strftime('%A, %d de %B')}")
        print(f"Hora Tijuana: {ahora_tijuana.strftime('%I:%M %p')}")
        print(f"Capital disponible: ${self.capital:,.2f}")
        print(f"Posiciones actuales: {len(self.posiciones_actuales)}/{self.max_posiciones_simultaneas}")
        
        # === PASO 2: Descargar datos ===
        print("\n" + "="*80)
        print("DESCARGANDO DATOS")
        print("="*80)
        
        datos_cryptos = {}
        for ticker, info in self.cryptos.items():
            print(f"Descargando {info['nombre']} ({ticker})...", end=" ")
            datos = self.descargar_datos_crypto(ticker)
            if datos is not None and len(datos) > 200:
                datos_cryptos[ticker] = datos
                print(f"OK {len(datos)} registros")
            else:
                print("ERROR")
        
        if len(datos_cryptos) == 0:
            print("\nNo se pudieron descargar datos")
            return None
        
        # === PASO 3: Calcular correlaciones ===
        print("\n" + "="*80)
        print("ANALISIS DE CORRELACIONES")
        print("="*80)
        
        correlaciones = self.calcular_correlaciones(datos_cryptos)
        if correlaciones is not None:
            print("\nCorrelaciones entre cryptos:")
            print(correlaciones.round(3))
            print("\nInterpretacion:")
            print("  >0.8: Muy correlacionadas (se mueven juntas)")
            print("  0.5-0.8: Correlacion moderada")
            print("  <0.5: Movimientos independientes")
        
        # === PASO 4: Analizar cada crypto ===
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
                    print(f"  - {razon}")
        
        # === PASO 5: Ranking de oportunidades ===
        print("\n" + "="*80)
        print("RANKING DE OPORTUNIDADES")
        print("="*80)
        
        # Separar señales alcistas y bajistas
        señales_long = [a for a in analisis_todas if a['score'] > self.score_minimo]
        señales_short = [a for a in analisis_todas if a['score'] < -self.score_minimo]
        
        if señales_long:
            print("\nSEÑALES DE COMPRA (LONG):")
            señales_long_ord = sorted(señales_long, key=lambda x: x['score'], reverse=True)
            for i, s in enumerate(señales_long_ord, 1):
                print(f"  {i}. {s['ticker']}: Score {s['score']:.1f} - ${s['precio']:,.4f}")
        
        if señales_short:
            print("\nSEÑALES DE VENTA (SHORT):")
            señales_short_ord = sorted(señales_short, key=lambda x: x['score'])
            for i, s in enumerate(señales_short_ord, 1):
                print(f"  {i}. {s['ticker']}: Score {s['score']:.1f} - ${s['precio']:,.4f}")
        
        if not señales_long and not señales_short:
            print("\nNO HAY SEÑALES FUERTES HOY")
            print(f"Score minimo requerido: ±{self.score_minimo}")
            print("\nEsto es BUENO - significa:")
            print("  - El sistema es selectivo (calidad > cantidad)")
            print("  - No hay oportunidades claras")
            print("  - Mejor esperar que forzar operaciones")
            return None
        
        # === PASO 6: Seleccionar mejor oportunidad ===
        mejor_op, mensaje = self.seleccionar_mejor_oportunidad(analisis_todas)
        
        if mejor_op is None:
            print(f"\n{mensaje}")
            return None
        
        # === PASO 7: Presentar mejor oportunidad ===
        print("\n" + "="*80)
        print("MEJOR OPORTUNIDAD DETECTADA")
        print("="*80)
        
        ticker = mejor_op['ticker']
        nombre = self.cryptos[ticker]['nombre']
        precio = mejor_op['precio']
        score = mejor_op['score']
        
        print(f"\n{'COMPRAR' if score > 0 else 'VENDER'} {nombre} ({ticker})")
        print(f"Precio actual: ${precio:,.4f}")
        print(f"Score: {score:.1f}/100")
        print(f"Confianza: {abs(score)/100*100:.1f}%")
        
        # === PASO 8: Calcular tamaño de posición ===
        cantidad, confianza = self.calcular_tamaño_posicion(precio, mejor_op['volatilidad'], score)
        valor_posicion = cantidad * precio
        apalancamiento = self.calcular_apalancamiento(mejor_op['volatilidad'], confianza)
        
        print(f"\nTAMAÑO DE POSICION:")
        print(f"  Cantidad: {cantidad:.6f} {ticker.replace('-USD', '')}")
        print(f"  Valor: ${valor_posicion:,.2f}")
        print(f"  % del capital: {(valor_posicion/self.capital)*100:.1f}%")
        print(f"  Confianza: {confianza*100:.1f}%")
        
        print(f"\nAPALANCAMIENTO: {apalancamiento}x")
        print(f"  Exposicion total: ${valor_posicion * apalancamiento:,.2f}")
        print(f"  Distancia liquidacion: ~{(100/apalancamiento):.1f}%")
        
        if apalancamiento >= 3:
            print(f"  ADVERTENCIA: Apalancamiento {apalancamiento}x es alto")
            print(f"  - Solo {100/apalancamiento:.0f}% de movimiento en contra = liquidacion")
            print(f"  - Requiere monitoreo constante")
        
        # === PASO 9: Calcular precios de entrada y salida ===
        print(f"\nPRECIOS DE ENTRADA:")
        if score > 0:  # LONG
            entrada_ideal = mejor_op['bb_lower'] if precio > mejor_op['bb_lower'] * 1.02 else precio
            print(f"  Entrada inmediata: ${precio:,.4f}")
            print(f"  Entrada ideal: ${entrada_ideal:,.4f}")
            if precio > entrada_ideal * 1.02:
                print(f"  Recomendacion: Esperar pullback a ${entrada_ideal:,.4f}")
            
            stop_loss = precio * 0.97
            take_profit = precio * 1.05
        else:  # SHORT
            entrada_ideal = mejor_op['bb_upper'] if precio < mejor_op['bb_upper'] * 0.98 else precio
            print(f"  Entrada inmediata: ${precio:,.4f}")
            print(f"  Entrada ideal: ${entrada_ideal:,.4f}")
            if precio < entrada_ideal * 0.98:
                print(f"  Recomendacion: Esperar rebote a ${entrada_ideal:,.4f}")
            
            stop_loss = precio * 1.03
            take_profit = precio * 0.95
        
        # === PASO 10: Calcular riesgo/beneficio ===
        perdida_max = abs(precio - stop_loss) * cantidad * apalancamiento
        ganancia_obj = abs(precio - take_profit) * cantidad * apalancamiento
        
        print(f"\nGESTION DE RIESGO:")
        print(f"  Stop Loss: ${stop_loss:,.4f} ({'−' if score > 0 else '+'}3%)")
        print(f"  Take Profit: ${take_profit:,.4f} ({'+' if score > 0 else '−'}5%)")
        print(f"  Perdida maxima: ${perdida_max:,.2f} ({(perdida_max/self.capital)*100:.2f}% del capital)")
        print(f"  Ganancia objetivo: ${ganancia_obj:,.2f} ({(ganancia_obj/self.capital)*100:.2f}% del capital)")
        print(f"  Ratio Riesgo/Beneficio: 1:{(ganancia_obj/perdida_max):.2f}")
        
        if perdida_max > self.capital * 0.02:
            print(f"  ALERTA: Riesgo ({perdida_max/self.capital*100:.1f}%) supera limite (2%)")
            print(f"  Considerar reducir apalancamiento o tamaño")
        
        # === PASO 11: Plan de ejecución ===
        print(f"\nPLAN DE EJECUCION:")
        print(f"  1. {'Comprar' if score > 0 else 'Vender en corto'} {cantidad:.6f} {ticker.replace('-USD', '')}")
        print(f"  2. Precio objetivo: ${entrada_ideal:,.4f}")
        print(f"  3. Usar apalancamiento: {apalancamiento}x")
        print(f"  4. Colocar Stop Loss: ${stop_loss:,.4f}")
        print(f"  5. Colocar Take Profit: ${take_profit:,.4f}")
        print(f"  6. Monitorear continuamente (especialmente con apalancamiento)")
        
        print(f"\nRAZONES DE LA SEÑAL:")
        for i, razon in enumerate(mejor_op['razones'][:5], 1):
            print(f"  {i}. {razon}")
        
        # === PASO 12: Consideraciones finales ===
        print("\n" + "="*80)
        print("CONSIDERACIONES IMPORTANTES")
        print("="*80)
        print("\nANTES DE EJECUTAR:")
        print("  - Verifica liquidez en tu exchange")
        print("  - Considera fees (0.1-0.5% por operacion)")
        print(f"  - Con {apalancamiento}x, fees de apertura/cierre: ~${valor_posicion * apalancamiento * 0.002:,.2f}")
        print("  - Configura alertas de precio para Stop Loss")
        print("  - Ten plan B si el mercado se mueve rapido")
        
        print("\nRECUERDOS:")
        print("  - Esto es trading ACTIVO - requiere seguimiento")
        print("  - SIEMPRE usa Stop Loss (no negociable)")
        print("  - No hagas revenge trading si pierdes")
        print("  - Calidad > Cantidad de operaciones")
        print("  - Si dudas, NO operes")
        
        print("\n" + "="*80)
        
        return {
            'timestamp': datetime.now(self.tz),
            'crypto': ticker,
            'nombre': nombre,
            'accion': 'LONG' if score > 0 else 'SHORT',
            'precio': precio,
            'cantidad': cantidad,
            'score': score,
            'apalancamiento': apalancamiento,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'perdida_maxima': perdida_max,
            'ganancia_objetivo': ganancia_obj,
            'ratio_riesgo_beneficio': ganancia_obj/perdida_max,
            'volatilidad': mejor_op['volatilidad'],
            'rsi': mejor_op['rsi'],
            'momentum_24h': mejor_op['momentum_24h']
        }


# ================================================================================
# EJECUCIÓN PRINCIPAL
# ================================================================================
if __name__ == "__main__":
    print("\n" + "="*80)
    print("ESTRATEGIA DE TRADING ACTIVO EN CRIPTOMONEDAS")
    print("="*80)
    print("\nCRYPTOS ANALIZADAS:")
    print("  - Bitcoin (BTC) - Rey del mercado, mas estable")
    print("  - Ethereum (ETH) - Smart contracts, lider DeFi")
    print("  - Solana (SOL) - Alta velocidad, alto potencial")
    print("  - Binance Coin (BNB) - Token de exchange")
    print("  - Ripple (XRP) - Pagos internacionales")
    
    #print("\nCARACTERISTICAS:")
    #print("  - Analisis tecnico multi-indicador")
    #print("  - Seleccion automatica de mejor oportunidad")
    #print("  - Gestion de riesgo: max 2% por operacion")
    #print("  - Maximo 2 posiciones simultaneas")
    #print("  - Apalancamiento dinamico (1-3x)")
    #print("  - Score minimo: ±50 (selectivo)")
    
    #print("\nHORARIOS RECOMENDADOS (TIJUANA):")
    #print("  - 06:00-08:00 AM: Pre-apertura NYSE")
    #print("  - 09:00-11:00 AM: Apertura NYSE (alta volatilidad)")
    #print("  - 11:00 AM-01:00 PM: Media sesion")
    
    ahora_tijuana = datetime.now(TZ_TIJUANA)
    print(f"\nHORA ACTUAL: {ahora_tijuana.strftime('%I:%M %p %Z')}")
    print(f"FECHA: {ahora_tijuana.strftime('%A, %d de %B de %Y')}")
    
    print("\nCONFIGURACION ACTUAL:")
    estrategia = MultiCryptoTradingStrategy(capital_inicial=10000)
    print(f"  - Capital: ${estrategia.capital:,.2f}")
    print(f"  - Riesgo maximo: {estrategia.max_riesgo_por_trade*100}% por trade")
    print(f"  - Posiciones simultaneas: {estrategia.max_posiciones_simultaneas}")
    print(f"  - Score minimo: ±{estrategia.score_minimo}")
    
    print("\n" + "="*80)
    print("INICIANDO ANALISIS...")
    print("="*80 + "\n")
    
    # Ejecutar estrategia
    resultado = estrategia.ejecutar_estrategia()
    
    # Resumen final
    if resultado:
        print("\n" + "="*80)
        print("RESUMEN EJECUTIVO")
        print("="*80)
        print(f"\nTIMESTAMP: {resultado['timestamp'].strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"CRYPTO: {resultado['nombre']} ({resultado['crypto']})")
        print(f"ACCION: {resultado['accion']}")
        print(f"PRECIO: ${resultado['precio']:,.4f}")
        print(f"CANTIDAD: {resultado['cantidad']:.6f} {resultado['crypto'].replace('-USD', '')}")
        print(f"SCORE: {resultado['score']:.1f}/100")
        print(f"APALANCAMIENTO: {resultado['apalancamiento']}x")
        print(f"STOP LOSS: ${resultado['stop_loss']:,.4f}")
        print(f"TAKE PROFIT: ${resultado['take_profit']:,.4f}")
        print(f"RATIO R/R: 1:{resultado['ratio_riesgo_beneficio']:.2f}")
        
        print("\n¡SEÑAL DE TRADING GENERADA!")
        print("Revisa los detalles arriba antes de ejecutar.")
        
    else:
        print("\n" + "="*80)
        print("RESUMEN EJECUTIVO")
        print("="*80)
        print("\nNO HAY OPORTUNIDADES DE TRADING HOY")
        print("\nPosibles razones:")
        print("  - Todas las cryptos con scores debiles")
        print("  - Mercado lateral (sin tendencia clara)")
        print("  - Ya tienes el maximo de posiciones abiertas")
        print("  - Es fin de semana (bajo volumen)")
        
        print("\nRECOMENDACION:")
        print("  - Mantener posiciones actuales")
        print("  - Esperar mejores señales")
        print("  - Revisar nuevamente en el proximo horario")
        print("  - Paciencia es clave en trading")
    
    print("\n" + "="*80)
    print("ANALISIS COMPLETADO")
    print("="*80)
    
    # Información para GitHub Actions
    #print("\nPARA GITHUB ACTIONS:")
    #print("  - Este output se guardara en 'output.txt'")
    #print("  - Se enviara por email automaticamente")
    #print("  - Revisa tu bandeja de entrada")
    #print("  - Si hay señal fuerte, actua rapido")
    
    # Exit code para GitHub Actions
    # 0 = Señal encontrada, 1 = Sin señal
    # import sys
    # if resultado and abs(resultado['score']) > estrategia.score_minimo:
    #    sys.exit(0)  # Señal fuerte
    # else:
    #    sys.exit(1)  # Sin señal fuerte
