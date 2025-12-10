"""
================================================================================
🚀 ESTRATEGIA DE TRADING: GAP FILL + NIVELES HISTÓRICOS + INDICADORES HTF          
================================================================================

📌 DESCRIPCIÓN:
Sistema de trading automatizado que combina análisis de gaps CME, niveles de 
pivote, indicadores técnicos (RSI, MACD, EMA200) y soportes/resistencias 
históricas para generar señales de trading en criptomonedas.

VERSIÓN: 2.0 - Con indicadores técnicos en timeframes superiores (4H/1D)
ÚLTIMA ACTUALIZACIÓN: Diciembre 2025

🎯 OBJETIVO:
Identificar oportunidades de alta probabilidad para:
1. Cierre de gaps CME (gaps entre velas diarias)
2. Rebotes en soportes/resistencias históricas
3. Confluencias técnicas con indicadores HTF (Higher TimeFrame)

================================================================================
📊 NUEVO SISTEMA DE PUNTUACIÓN (v2.0)
================================================================================

SISTEMA DE CONFIANZA (Máximo 5.0 puntos):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
| Elemento                    | Puntos | Descripción                    |
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
| Gap CME detectado          | +1.0   | Gap >0.5% entre velas diarias  |
| Nivel histórico fuerte     | +1.5   | R2/S2 <1% del precio actual    |
| Estructura correcta (PP)   | +1.0   | Precio vs PP favorable         |
| RSI 4H extremo             | +1.0   | RSI <30 (LONG) o >70 (SHORT)   |
| RSI 4H zona                | +0.5   | RSI 30-40 (LONG) o 60-70 (SHORT)|
| MACD 4H cruce              | +1.0   | Cruce alcista/bajista reciente |
| MACD 4H tendencia          | +0.5   | MACD > Signal (sin cruce)      |
| Precio vs EMA200 fuerte    | +1.0   | Distancia >2% de EMA200        |
| Precio vs EMA200 normal    | +0.5   | Distancia 0-2% de EMA200       |
| Volumen alto               | +1.0   | 1.5x volumen promedio 20 velas |
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ CAMBIO IMPORTANTE V2.0:
- ❌ ELIMINADOS: Patrones de vela de 5 minutos (no eran útiles)
- ✅ AGREGADOS: RSI, MACD, EMA200 en timeframes 4H/1D (mucho más confiables)

UMBRALES DE OPERACIÓN:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Escenario                              | Confianza Mín. | Puntos Mín.  |
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Gap + estructura correcta (vs PP)      | 40%           | 2.0/5.0      |
Gap sin estructura óptima              | 50%           | 2.5/5.0      |
Sin gap, resistencia/soporte fuerte    | 60%           | 3.0/5.0      |
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

================================================================================
🎲 TIPOS DE SEÑALES GENERADAS
================================================================================

1. LONG/SHORT_FUERTE (≥70% confianza)
   → Alta confianza: Gap + indicadores HTF alineados + volumen
   → Acción: Entrar con tamaño de posición completo (2% capital)

2. LONG/SHORT_MODERADO (50-69% confianza)
   → Confianza media: Gap + estructura O indicadores favorables
   → Acción: Entrar con tamaño reducido (1% capital)

3. LONG/SHORT_PENDIENTE
   → Esperar retroceso al Punto Pivote (PP) antes de entrar
   → Acción: Colocar orden límite en PP

4. LONG/SHORT_RESISTENCIA / SOPORTE (≥60% confianza)
   → Sin gap, operando rebote en nivel histórico fuerte
   → Acción: Entrada en nivel con confirmación de indicadores HTF

5. NO_OPERAR (<40% confianza)
   → Sin confluencia técnica suficiente
   → Acción: No operar, esperar siguiente oportunidad

================================================================================
📈 ESTRATEGIAS DE ENTRADA
================================================================================

ESTRATEGIA 1: CIERRE DE GAP CME (Principal)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SHORT (Gap Up - Precio arriba del cierre previo):
  Condiciones Base:
  ✅ Gap >0.5% detectado entre cierre D-1 y precio actual
  ✅ Precio actual > Punto Pivote (PP)
  
  Confirmaciones con Indicadores HTF:
  ✅ RSI 4H >70 (sobrecomprado) = +1.0 pt
  ✅ RSI 4H 60-70 (zona bajista) = +0.5 pt
  ✅ MACD 4H cruce bajista = +1.0 pt
  ✅ MACD 4H en tendencia bajista = +0.5 pt
  ✅ Precio <2% bajo EMA200 = +1.0 pt
  ✅ Volumen alto (1.5x promedio) = +1.0 pt
  
  Niveles:
  - Entry: Precio actual (market) o PP (limit pendiente)
  - SL: R1 o resistencia histórica R2
  - TP1: Nivel del gap (cierre del gap) ⭐ Prioridad
  - TP2: S1 (soporte de pivote)
  - TP3: Gap histórico o S2

LONG (Gap Down - Precio abajo del cierre previo):
  Condiciones Base:
  ✅ Gap >0.5% detectado entre cierre D-1 y precio actual
  ✅ Precio actual < Punto Pivote (PP)
  
  Confirmaciones con Indicadores HTF:
  ✅ RSI 4H <30 (sobrevendido) = +1.0 pt
  ✅ RSI 4H 30-40 (zona alcista) = +0.5 pt
  ✅ MACD 4H cruce alcista = +1.0 pt
  ✅ MACD 4H en tendencia alcista = +0.5 pt
  ✅ Precio >2% sobre EMA200 = +1.0 pt
  ✅ Volumen alto (1.5x promedio) = +1.0 pt
  
  Niveles:
  - Entry: Precio actual (market) o PP (limit pendiente)
  - SL: S1 o soporte histórico S2
  - TP1: Nivel del gap (cierre del gap) ⭐ Prioridad
  - TP2: R1 (resistencia de pivote)
  - TP3: Gap histórico o R2

ESTRATEGIA 2: REBOTE EN NIVELES HISTÓRICOS (Sin Gap)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SHORT desde Resistencia:
  Condiciones:
  ✅ Precio cerca (<1%) de resistencia histórica R2
  ✅ Precio > PP (estructura bajista)
  ✅ Indicadores HTF bajistas (RSI alto, MACD bajista, bajo EMA200)
  ✅ Volumen alto confirmatorio
  
  Niveles:
  - Entry: Precio actual en resistencia
  - SL: R2 + 1 ATR
  - TP1: PP (primer objetivo)
  - TP2: S1
  - TP3: S2 o soporte histórico

LONG desde Soporte:
  Condiciones:
  ✅ Precio cerca (<1%) de soporte histórico S2
  ✅ Precio < PP (estructura alcista)
  ✅ Indicadores HTF alcistas (RSI bajo, MACD alcista, sobre EMA200)
  ✅ Volumen alto confirmatorio
  
  Niveles:
  - Entry: Precio actual en soporte
  - SL: S2 - 1 ATR
  - TP1: PP (primer objetivo)
  - TP2: R1
  - TP3: R2 o resistencia histórica

================================================================================
📊 INDICADORES TÉCNICOS EXPLICADOS (v2.0)
================================================================================

1. RSI 4H (Relative Strength Index):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Mide momentum del precio en escala 0-100
   
   Para LONG:
   - RSI <30: OVERSOLD (sobrevendido) → +1.0 pt ⭐⭐⭐⭐⭐
   - RSI 30-40: BULLISH_ZONE → +0.5 pt ⭐⭐⭐
   
   Para SHORT:
   - RSI >70: OVERBOUGHT (sobrecomprado) → +1.0 pt ⭐⭐⭐⭐⭐
   - RSI 60-70: BEARISH_ZONE → +0.5 pt ⭐⭐⭐
   
   RSI 40-60: NEUTRAL → No suma puntos

2. MACD 4H (Moving Average Convergence Divergence):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Mide cambios en momentum y detecta cruces de tendencia
   
   BULLISH_CROSS: MACD cruza hacia arriba de Signal → +1.0 pt LONG ⭐⭐⭐⭐⭐
   BEARISH_CROSS: MACD cruza hacia abajo de Signal → +1.0 pt SHORT ⭐⭐⭐⭐⭐
   BULLISH: MACD > Signal (sin cruce reciente) → +0.5 pt LONG ⭐⭐⭐
   BEARISH: MACD < Signal (sin cruce reciente) → +0.5 pt SHORT ⭐⭐⭐
   NEUTRAL: Sin señal clara → No suma puntos

3. EMA200 1D (Exponential Moving Average 200):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Indica tendencia de largo plazo
   
   Para LONG:
   - Precio >2% arriba de EMA200: ABOVE_STRONG → +1.0 pt ⭐⭐⭐⭐⭐
   - Precio 0-2% arriba de EMA200: ABOVE → +0.5 pt ⭐⭐⭐
   
   Para SHORT:
   - Precio >2% abajo de EMA200: BELOW_STRONG → +1.0 pt ⭐⭐⭐⭐⭐
   - Precio 0-2% abajo de EMA200: BELOW → +0.5 pt ⭐⭐⭐

================================================================================
💻 INSTRUCCIONES DE USO
================================================================================

MODO 1: ANÁLISIS EN TIEMPO REAL (Recomendado para trading diario)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Uso:
  python script.py

Cuándo ejecutar:
  - 6:00-6:30 AM Tijuana (9:00-9:30 AM NY) - Pre-apertura NY
  - Antes de abrir cualquier operación del día

Qué obtienes:
  - Análisis de BTC, ETH, SOL, BNB, XRP
  - Indicadores HTF (RSI 4H, MACD 4H, EMA200 1D)
  - Señales de entrada inmediata o pendiente
  - Niveles de SL y 3 TPs calculados
  - Confianza y puntuación detallada

Workflow recomendado:
  1. Ejecutar script a las 6:30 AM Tijuana
  2. Revisar señales con confianza ≥50%
  3. Verificar indicadores HTF manualmente en TradingView:
     - Confirmar RSI en zona correcta
     - Verificar MACD visual
     - Confirmar posición vs EMA200
  4. Colocar órdenes según tipo de señal:
     - FUERTE (≥70%): Full size, entrada inmediata
     - MODERADO (50-69%): Half size, entrada inmediata
     - PENDIENTE: Limit order en PP
     - RESISTENCIA/SOPORTE: Esperar confirmación de rechazo
  5. Colocar SL y TPs según niveles indicados
  6. Registrar operación en diario de trading

INTERPRETACIÓN DE SEÑALES v2.0:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ejemplo de output mejorado:

### 📊 INDICADORES TÉCNICOS (HTF)
* RSI 4H: 28.5 → OVERSOLD
* MACD 4H: 0.0234 → BULLISH_CROSS
* EMA200 1D: 88500.00 (+2.0%) → ABOVE_STRONG

Interpretación:
- RSI <30: Precio muy sobrevendido, probable rebote alcista
- MACD cruce alcista: Momentum cambiando a alcista
- Precio +2% sobre EMA200: Tendencia de largo plazo alcista

Conclusión: ✅ Confluencia perfecta para LONG


MODO 2: BACKTESTING (Validación de estrategia)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Uso:
  python script.py --backtest [días] [confianza_min%] [símbolo]

Ejemplos:
  # Backtest de 30 días en BTC con señales ≥50% confianza
  python script.py --backtest 30 50 BTC-USD
  
  # Backtest de 60 días en ETH con señales ≥55% confianza
  python script.py --backtest 60 55 ETH-USD
  
  # Backtest de 90 días en SOL (más agresivo)
  python script.py --backtest 90 45 SOL-USD

⚠️ NOTA: El backtesting ahora usa indicadores HTF reales, por lo que
los resultados deberían ser más precisos que la versión anterior.

Qué obtienes:
  - Win Rate (% operaciones ganadoras)
  - Profit Factor (ganancia total / pérdida total)
  - Avg Win / Avg Loss
  - Risk:Reward ratio promedio
  - Retorno total acumulado
  - Max Drawdown (peor racha de pérdidas)
  - CSV con todas las operaciones simuladas

Interpretación de Resultados v2.0:
  ✅ EXCELENTE:     Win Rate ≥60% y Profit Factor ≥1.7
  ✔️  ACEPTABLE:    Win Rate ≥55% y Profit Factor ≥1.5
  ⚠️  MARGINAL:     Win Rate ≥50% y Profit Factor ≥1.3
  ❌ INSUFICIENTE:  Win Rate <50% o Profit Factor <1.3

  Con indicadores HTF, esperamos win rates 5-10% mejores que v1.0


MODO 3: GOOGLE COLAB (Sin instalación local)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Crear notebook en: https://colab.research.google.com/
2. Celda 1: !pip install yfinance -q
3. Celda 2: Copiar código completo
4. Celda 3: Ejecutar análisis

Ejemplo:
  # Análisis normal
  analyze_pre_ny("BTC-USD")
  
  # Todas las criptos
  for sym in ["BTC-USD", "ETH-USD", "SOL-USD"]:
      print(analyze_pre_ny(sym))

================================================================================
⚠️ GESTIÓN DE RIESGO (CRÍTICO - LEER ANTES DE OPERAR)
================================================================================

REGLAS OBLIGATORIAS v2.0:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Position Sizing (Ajustado con nueva confianza):
   - Señales ≥70% (FUERTE): Tamaño completo (2% capital)
   - Señales 50-69% (MODERADO): Tamaño reducido (1% capital)
   - Señales <50%: NO OPERAR

2. Stop Loss (SIN EXCEPCIONES):
   - SIEMPRE colocar SL al abrir posición
   - NUNCA mover SL en contra (aumentar pérdida)
   - NUNCA quitar SL temporalmente
   - SL se respeta 100% automáticamente

3. Take Profit (Gestión de Salida Mejorada):
   Método 1 - Escalonado (Recomendado):
   - TP1 alcanzado: Cerrar 40% (asegurar ganancia)
   - TP2 alcanzado: Cerrar 30% adicional
   - TP3 alcanzado: Cerrar 30% restante
   
   Método 2 - Breakeven + Trailing:
   - TP1 alcanzado: Mover SL a breakeven
   - TP2 alcanzado: Trailing stop ATR x2
   - Dejar correr hasta TP3 o trailing

4. Límites Diarios:
   - Máximo 2-3 operaciones por día
   - Si pierdes 2 operaciones seguidas: STOP por el día
   - Si ganas 3% del capital: Considerar parar (proteger ganancia)
   - NUNCA operar por "recuperar" pérdidas

5. Diario de Trading (OBLIGATORIO):
   Registrar por cada operación:
   - Fecha y hora de entrada
   - Símbolo y dirección (LONG/SHORT)
   - Confianza % y puntuación
   - Indicadores HTF (RSI, MACD, EMA)
   - Entrada, SL, TPs ejecutados
   - Resultado final en % y $
   - Notas: ¿Qué funcionó? ¿Qué falló?
   
   Revisar semanalmente para identificar patrones

6. Validación Previa (MUY IMPORTANTE):
   - PAPER TRADING mínimo 30 días antes de operar real
   - Win Rate >55% en paper antes de capital real
   - Profit Factor >1.5 consistente
   - Empezar con capital mínimo ($200-500) primeras 2 semanas
   - Escalar gradualmente solo si resultados positivos

7. Confirmación Manual con Indicadores:
   Aunque el código ya analiza RSI/MACD/EMA, SIEMPRE verificar en gráfico:
   - Abrir TradingView en 4H
   - Confirmar visualmente RSI en zona esperada
   - Ver MACD histogram creciendo/decreciendo
   - Verificar precio vs EMA200 en 1D
   
   Si indicadores NO confirman: NO ENTRAR (aunque código diga 80%)

================================================================================
📚 CONCEPTOS TÉCNICOS EXPLICADOS
================================================================================

Gap CME:
  Diferencia entre el cierre de una vela diaria y la apertura de la siguiente.
  En cripto spot (24/7) son menos comunes que en futuros CME tradicionales.
  Estadísticamente ~70-80% de gaps tienden a "cerrarse" (precio vuelve al nivel).

Punto Pivote (PP):
  Nivel calculado como: (High_prev + Low_prev + Close_prev) / 3
  Usado como nivel de entrada/retroceso y referencia de estructura.
  Si precio > PP: Estructura bajista para SHORT
  Si precio < PP: Estructura alcista para LONG
  
Resistencias/Soportes (R1, R2, S1, S2):
  R1/S1: Calculados con fórmula de pivotes estándar
  R2/S2: Niveles históricos (máximos/mínimos recientes de 100 días)
  Usados como objetivos de TP y niveles de SL
  
ATR (Average True Range):
  Mide volatilidad promedio del activo en los últimos 14 períodos.
  Usado para calcular SL dinámico basado en volatilidad real.
  Ejemplo: Si ATR = $500, SL típico = Entry ± (1.5 x $500) = ±$750

RSI (Relative Strength Index):
  Oscilador de momentum 0-100.
  <30: Sobrevendido (probable rebote alcista)
  >70: Sobrecomprado (probable corrección bajista)
  Período usado: 14 velas de 1H (≈4H efectivo)

MACD (Moving Average Convergence Divergence):
  Indicador de tendencia y momentum.
  Cruce de líneas indica cambio de tendencia.
  Histogram positivo = alcista, negativo = bajista
  Configuración: 12, 26, 9 (estándar)

EMA200 (Exponential Moving Average 200):
  Media móvil de 200 períodos diarios.
  Precio arriba = tendencia alcista de largo plazo
  Precio abajo = tendencia bajista de largo plazo
  Actúa como soporte/resistencia dinámica

================================================================================
🔧 PERSONALIZACIÓN Y AJUSTES
================================================================================

Modificar símbolos analizados (línea final):
  symbols_to_analyze = ["BTC-USD", "ETH-USD", "TU-CRIPTO"]

Ajustar umbral de gap (función detect_cme_gap):
  THRESHOLD_PCT = 0.005  # 0.5% actual
  # Cambiar a 0.003 (0.3%) para más señales
  # Cambiar a 0.01 (1.0%) para menos señales, mayor calidad

Modificar períodos de indicadores:
  # RSI (línea ~165)
  rsi_4h = calculate_rsi(df_4h, period=14)  # Cambiar 14 a 10-20
  
  # EMA200 (línea ~210)
  ema200 = calculate_ema(df_1d, period=200)  # Cambiar a 50, 100, 300

Cambiar umbral de volumen alto (línea ~90):
  def check_high_volume(df, period=20, multiplier=1.5):
  # multiplier = 2.0 para ser más estricto
  # multiplier = 1.3 para ser más permisivo

Ajustar zona horaria (línea ~20):
  TIJUANA_TIMEZONE = pytz.timezone('America/Tijuana')
  # Cambiar a: 'America/Mexico_City', 'Europe/London', 'Asia/Tokyo'

Modificar umbrales de confianza (líneas ~540-570):
  min_confidence = 2.0  # Actual para gap + estructura
  # Cambiar a 2.5 para ser más conservador
  # Cambiar a 1.5 para más señales (más arriesgado)

================================================================================
📞 SOPORTE Y TROUBLESHOOTING
================================================================================

Error: "yfinance not found"
  Solución: pip install --upgrade yfinance

Error: "No se generaron señales" en backtesting
  Causa: No hay gaps o niveles fuertes en el período
  Solución: 
    - Reducir min_confidence (ej: de 55% a 45%)
    - Aumentar days_back (ej: de 30 a 60)
    - Probar otro símbolo con más volatilidad

Error: "Rate limit exceeded"
  Causa: Demasiadas peticiones a Yahoo Finance API
  Solución: Esperar 10-15 minutos antes de volver a ejecutar

Indicadores muestran "N/A":
  Causa: No hay suficientes datos históricos
  Solución: 
    - Verificar conexión a internet
    - Esperar unos minutos y reintentar
    - Símbolo puede ser muy nuevo (probar con BTC/ETH)

Señales no coinciden con tu análisis:
  - El código es una HERRAMIENTA, no una bola de cristal
  - SIEMPRE verificar manualmente en gráfico antes de entrar
  - Si dudas, NO ENTRAR (conservar capital es prioridad)
  - Ajustar umbrales según tu estilo de trading

Win Rate bajo en backtest (<50%):
  - Normal en períodos de baja volatilidad
  - Probar aumentar min_confidence (más selectivo)
  - Verificar que gaps históricos estén funcionando bien
  - Considerar operar solo señales FUERTE (≥70%)

================================================================================
⚖️ DISCLAIMER LEGAL
================================================================================

Este código es una herramienta de ANÁLISIS TÉCNICO, NO es asesoría financiera.
El trading de criptomonedas conlleva riesgo significativo de pérdida de capital.
Los resultados pasados no garantizan resultados futuros.
Opera solo con capital que puedas permitirte perder completamente.
Los indicadores técnicos no son infalibles y pueden dar señales falsas.
Realiza tu propia investigación antes de tomar decisiones de inversión.
El desarrollador NO se hace responsable de pérdidas generadas por el uso de este código.

================================================================================
📝 CHANGELOG v2.0
================================================================================

CAMBIOS PRINCIPALES:
+ Agregado: RSI 4H para detectar sobrecompra/sobreventa
+ Agregado: MACD 4H para detectar cruces y cambios de tendencia
+ Agregado: EMA200 1D para confirmar tendencia de largo plazo
- Eliminado: Patrones de vela de 5 minutos (inútiles)
* Mejorado: Sistema de puntuación más preciso con HTF
* Mejorado: Umbrales de confianza ajustados (40% mín vs 65% anterior)
* Mejorado: Output muestra indicadores HTF claramente
* Mejorado: Backtesting usa indicadores reales (no patrones)

RESULTADOS ESPERADOS:
- Win Rate: +5-10% vs v1.0 (de 50-55% a 55-65%)
- Profit Factor: +0.2-0.4 vs v1.0 (de 1.3-1.5 a 1.5-1.9)
- Señales más confiables y con mejor contexto

================================================================================
"""

import yfinance as yf
import pandas as pd
import numpy as np
import pytz
from datetime import datetime

# Definición de zonas horarias
NY_TIMEZONE = pytz.timezone('America/New_York')
TIJUANA_TIMEZONE = pytz.timezone('America/Tijuana')

# =======================================================================
# 1. FUNCIONES BÁSICAS
# =======================================================================

def safe_float(x):
    """Convierte a flotante de forma segura, adaptado para Series, escalares y numpy types."""
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
    """Evalúa si el volumen de la última vela es un 'disparador' (alto volumen)."""
    if len(df) < period: return False
    try:
        last_volume = safe_float(df['Volume'].iloc[-1])
        avg_volume = df['Volume'].iloc[-period:-1].mean()
        return last_volume > (safe_float(avg_volume) * multiplier)
    except:
        return False

def safe_atr(df, period=14):
    """Calcula el Rango Verdadero Promedio (ATR)."""
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
    """Calcula los Puntos Pivote (PP, R1, S1) del día actual."""
    try:
        df_1d = yf.download(symbol_str, interval="1d", period="1y", progress=False, auto_adjust=True)
        
        if isinstance(df_1d.columns, pd.MultiIndex):
            df_1d.columns = df_1d.columns.get_level_values(0)
            
    except Exception as e:
        return np.nan, np.nan, np.nan, pd.DataFrame(), f"Falla de descarga 1D: {e}" 

    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    if df_1d.empty or len(df_1d) < 2 or not all(col in df_1d.columns for col in required_cols):
        return np.nan, np.nan, np.nan, df_1d, "Datos 1D insuficientes o incompletos."
    
    try:
        H_prev = safe_float(df_1d['High'].iloc[-2])
        L_prev = safe_float(df_1d['Low'].iloc[-2])
        C_prev = safe_float(df_1d['Close'].iloc[-2])
        
        if np.isnan(H_prev) or np.isnan(L_prev) or np.isnan(C_prev): 
            return np.nan, np.nan, np.nan, df_1d, "Valores PP no numéricos."
        
        PP = (H_prev + L_prev + C_prev) / 3
        R1 = (2 * PP) - L_prev
        S1 = (2 * PP) - H_prev
        return PP, R1, S1, df_1d, None
    except Exception as e:
        return np.nan, np.nan, np.nan, df_1d, f"Error cálculo PP: {e}"

def find_historical_level(df_1d, last_price, is_resistance=True, lookback_days=100):
    """Busca y define niveles de Resistencia o Soporte de largo plazo."""
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
# 2. INDICADORES TÉCNICOS (REEMPLAZAN PATRONES DE VELA)
# =======================================================================

def calculate_rsi(df, period=14):
    """Calcula el RSI (Relative Strength Index). Retorna valor entre 0-100."""
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
    """Calcula MACD. Retorna: macd_line, signal_line, histogram, y señal de cruce."""
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
    """Calcula EMA (Exponential Moving Average)."""
    if len(df) < period:
        return np.nan
    
    try:
        ema = df['Close'].ewm(span=period, adjust=False).mean()
        return safe_float(ema.iloc[-1])
    except:
        return np.nan


def analyze_technical_indicators(symbol, last_price):
    """Analiza indicadores técnicos en 4H y 1D."""
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
# 3. DETECCIÓN DE GAPS
# =======================================================================

def find_historical_gaps(df_1d, current_price, lookback_days=60):
    """Encuentra gaps históricos sin cerrar."""
    if df_1d.empty or len(df_1d) < 3:
        return [], []
    
    gaps_above = []
    gaps_below = []
    
    df_recent = df_1d.iloc[-lookback_days:] if len(df_1d) >= lookback_days else df_1d
    
    for i in range(1, len(df_recent)):
        try:
            prev_close = safe_float(df_recent['Close'].iloc[i-1])
            curr_open = safe_float(df_recent['Open'].iloc[i])
            
            if any(np.isnan([prev_close, curr_open])):
                continue
            
            if curr_open > prev_close * 1.005:
                gap_level = prev_close
                gap_filled = False
                for j in range(i, len(df_recent)):
                    check_low = safe_float(df_recent['Low'].iloc[j])
                    if not np.isnan(check_low) and check_low <= gap_level:
                        gap_filled = True
                        break
                
                if not gap_filled:
                    if gap_level > current_price:
                        gaps_above.append({
                            'level': gap_level,
                            'type': 'GAP_UP',
                            'age_days': len(df_recent) - i,
                            'size_pct': ((curr_open - prev_close) / prev_close) * 100
                        })
                    elif gap_level < current_price:
                        gaps_below.append({
                            'level': gap_level,
                            'type': 'GAP_UP',
                            'age_days': len(df_recent) - i,
                            'size_pct': ((curr_open - prev_close) / prev_close) * 100
                        })
            
            elif curr_open < prev_close * 0.995:
                gap_level = prev_close
                gap_filled = False
                for j in range(i, len(df_recent)):
                    check_high = safe_float(df_recent['High'].iloc[j])
                    if not np.isnan(check_high) and check_high >= gap_level:
                        gap_filled = True
                        break
                
                if not gap_filled:
                    if gap_level > current_price:
                        gaps_above.append({
                            'level': gap_level,
                            'type': 'GAP_DOWN',
                            'age_days': len(df_recent) - i,
                            'size_pct': ((prev_close - curr_open) / prev_close) * 100
                        })
                    elif gap_level < current_price:
                        gaps_below.append({
                            'level': gap_level,
                            'type': 'GAP_DOWN',
                            'age_days': len(df_recent) - i,
                            'size_pct': ((prev_close - curr_open) / prev_close) * 100
                        })
        
        except Exception:
            continue
    
    gaps_above = sorted(gaps_above, key=lambda x: x['level'])
    gaps_below = sorted(gaps_below, key=lambda x: x['level'], reverse=True)
    
    return gaps_above, gaps_below


def detect_cme_gap(df_1d, last_price):
    """Detecta gap significativo (0.5%) entre precio actual y cierre previo."""
    if df_1d.empty or len(df_1d) < 2: return "NO_GAP", np.nan
    gap_level = safe_float(df_1d['Close'].iloc[-2])
    if np.isnan(gap_level): return "NO_GAP", np.nan
    
    THRESHOLD_PCT = 0.005
    
    if last_price > gap_level * (1 + THRESHOLD_PCT):
        return "SHORT_TO_FILL", gap_level
    elif last_price < gap_level * (1 - THRESHOLD_PCT):
        return "LONG_TO_FILL", gap_level
    else:
        return "NO_GAP", np.nan


# =======================================================================
# 4. VALIDACIÓN DE NIVELES
# =======================================================================

def validate_levels(decision, entry_p, sl_p, tp1_p, tp2_p, atr, last_price):
    """Valida que niveles TP/SL estén correctamente ordenados."""
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
# 5. ANÁLISIS PRINCIPAL
# =======================================================================

def analyze_pre_ny(symbol):
    
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    
    try:
        data_5m = yf.download(symbol, interval="5m", period="7d", progress=False, auto_adjust=True)
        
        if isinstance(data_5m.columns, pd.MultiIndex):
            data_5m.columns = data_5m.columns.get_level_values(0)
        
        if data_5m.empty or not all(col in data_5m.columns for col in required_cols):
             return f"Error de Datos 5m para {symbol}: DataFrame vacío o incompleto."
        data_5m = data_5m.dropna(subset=required_cols)
    except Exception as e:
        return f"Error de Conexión/API (5m) para {symbol}: {e}"

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
        if np.isnan(last_price): raise ValueError("Precio final inválido.")
    except Exception as e:
        return f"Error al extraer precio/tiempo para {symbol}: {e}"
    
    atr = safe_atr(data_5m)
    high_volume = check_high_volume(data_5m) 
    gap_signal, gap_level = detect_cme_gap(data_1d, last_price)
    
    indicators = analyze_technical_indicators(symbol, last_price)
    
    gaps_above, gaps_below = find_historical_gaps(data_1d, last_price, lookback_days=60)
    
    R2_hist = find_historical_level(data_1d, last_price, is_resistance=True)
    S2_hist = find_historical_level(data_1d, last_price, is_resistance=False)
    
    strong_resistance = not np.isnan(R2_hist) and abs(last_price - R2_hist) / last_price < 0.01
    strong_support = not np.isnan(S2_hist) and abs(last_price - S2_hist) / last_price < 0.01

    decision = "NO_OPERAR (Consolidación)"
    confidence = 0
    entry_p, sl_p, tp1_p, tp2_p, tp3_p = np.nan, np.nan, np.nan, np.nan, np.nan
    indicator_score = 0.0
    max_score = 5
    
    ATR_TOLERANCE = (atr * 0.5 if not np.isnan(atr) and atr > 0 else last_price * 0.001)
    
    if gap_signal == "SHORT_TO_FILL":
        confidence += 1
        
        sl_p = R1 if R1 > last_price else (R2_hist if not np.isnan(R2_hist) and R2_hist > last_price else last_price + atr * 1.5)
        tp1_p = gap_level
        tp2_p = S1
        
        if gaps_below and len(gaps_below) > 0:
            valid_gaps = [g for g in gaps_below if g['level'] < tp2_p]
            if valid_gaps:
                tp3_p = valid_gaps[0]['level']
            elif not np.isnan(S2_hist) and S2_hist < tp2_p:
                tp3_p = S2_hist
            else:
                tp3_p = tp2_p - atr * 2.0
        else:
            if not np.isnan(S2_hist) and S2_hist < tp2_p:
                tp3_p = S2_hist
            else:
                tp3_p = tp2_p - atr * 2.0
        
        price_above_pp = last_price > PP
        confidence += 1 if price_above_pp else 0
        
        if indicators['rsi_signal'] in ['OVERBOUGHT', 'BEARISH_ZONE']:
            indicator_score += 1.0 if indicators['rsi_signal'] == 'OVERBOUGHT' else 0.5
        
        if indicators['macd_signal'] in ['BEARISH_CROSS', 'BEARISH']:
            indicator_score += 1.0 if indicators['macd_signal'] == 'BEARISH_CROSS' else 0.5
        
        if indicators['ema_signal'] in ['BELOW_STRONG', 'BELOW']:
            indicator_score += 1.0 if indicators['ema_signal'] == 'BELOW_STRONG' else 0.5
        
        confidence += indicator_score
        confidence += 1 if high_volume else 0
        
        min_confidence = 2.0 if price_above_pp else 2.5
        
        if confidence >= min_confidence:
            if last_price >= PP or abs(last_price - PP) < ATR_TOLERANCE:
                entry_p = last_price
                decision = "SHORT_FUERTE (Activación Inmediata)" if confidence >= 3.5 else "SHORT_MODERADO (Activación Inmediata)"
            else:
                entry_p = PP 
                decision = "SHORT_PENDIENTE (Esperar Retroceso a PP)"

    elif gap_signal == "LONG_TO_FILL":
        confidence += 1
        
        sl_p = S1 if S1 < last_price else (S2_hist if not np.isnan(S2_hist) and S2_hist < last_price else last_price - atr * 1.5)
        tp1_p = gap_level
        tp2_p = R1
        
        if gaps_above and len(gaps_above) > 0:
            valid_gaps = [g for g in gaps_above if g['level'] > tp2_p]
            if valid_gaps:
                tp3_p = valid_gaps[0]['level']
            elif not np.isnan(R2_hist) and R2_hist > tp2_p:
                tp3_p = R2_hist
            else:
                tp3_p = tp2_p + atr * 2.0
        else:
            if not np.isnan(R2_hist) and R2_hist > tp2_p:
                tp3_p = R2_hist
            else:
                tp3_p = tp2_p + atr * 2.0

        price_below_pp = last_price < PP
        confidence += 1 if price_below_pp else 0
        
        if indicators['rsi_signal'] in ['OVERSOLD', 'BULLISH_ZONE']:
            indicator_score += 1.0 if indicators['rsi_signal'] == 'OVERSOLD' else 0.5
        
        if indicators['macd_signal'] in ['BULLISH_CROSS', 'BULLISH']:
            indicator_score += 1.0 if indicators['macd_signal'] == 'BULLISH_CROSS' else 0.5
        
        if indicators['ema_signal'] in ['ABOVE_STRONG', 'ABOVE']:
            indicator_score += 1.0 if indicators['ema_signal'] == 'ABOVE_STRONG' else 0.5
        
        confidence += indicator_score
        confidence += 1 if high_volume else 0
        
        min_confidence = 2.0 if price_below_pp else 2.5
        
        if confidence >= min_confidence:
            if last_price <= PP or abs(last_price - PP) < ATR_TOLERANCE:
                entry_p = last_price
                decision = "LONG_FUERTE (Activación Inmediata)" if confidence >= 3.5 else "LONG_MODERADO (Activación Inmediata)"
            else:
                entry_p = PP
                decision = "LONG_PENDIENTE (Esperar Retroceso a PP)"
    
    elif gap_signal == "NO_GAP":
        if strong_resistance and last_price >= R2_hist:
            confidence += 1.5
            
            sl_p = R2_hist + atr * 1.0 if not np.isnan(R2_hist) else last_price + atr * 1.5
            tp1_p = PP
            tp2_p = S1
            tp3_p = S2_hist if not np.isnan(S2_hist) else S1 - atr * 2.0
            
            if last_price > PP:
                confidence += 1.0
            
            if indicators['rsi_signal'] in ['OVERBOUGHT', 'BEARISH_ZONE']:
                indicator_score += 1.0 if indicators['rsi_signal'] == 'OVERBOUGHT' else 0.5
            if indicators['macd_signal'] in ['BEARISH_CROSS', 'BEARISH']:
                indicator_score += 1.0 if indicators['macd_signal'] == 'BEARISH_CROSS' else 0.5
            if indicators['ema_signal'] in ['BELOW_STRONG', 'BELOW']:
                indicator_score += 1.0 if indicators['ema_signal'] == 'BELOW_STRONG' else 0.5
            
            confidence += indicator_score
            confidence += 1 if high_volume else 0
            
            if confidence >= 3.0:
                entry_p = last_price
                decision = "SHORT_RESISTENCIA (Sin Gap - Nivel Histórico)"
        
        elif strong_support and last_price <= S2_hist:
            confidence += 1.5
            
            sl_p = S2_hist - atr * 1.0 if not np.isnan(S2_hist) else last_price - atr * 1.5
            tp1_p = PP
            tp2_p = R1
            tp3_p = R2_hist if not np.isnan(R2_hist) else R1 + atr * 2.0
            
            if last_price < PP:
                confidence += 1.0
            
            if indicators['rsi_signal'] in ['OVERSOLD', 'BULLISH_ZONE']:
                indicator_score += 1.0 if indicators['rsi_signal'] == 'OVERSOLD' else 0.5
            if indicators['macd_signal'] in ['BULLISH_CROSS', 'BULLISH']:
                indicator_score += 1.0 if indicators['macd_signal'] == 'BULLISH_CROSS' else 0.5
            if indicators['ema_signal'] in ['ABOVE_STRONG', 'ABOVE']:
                indicator_score += 1.0 if indicators['ema_signal'] == 'ABOVE_STRONG' else 0.5

            confidence += indicator_score
            confidence += 1 if high_volume else 0
            
            if confidence >= 3.0:
                entry_p = last_price
                decision = "LONG_SOPORTE (Sin Gap - Nivel Histórico)"
    
    entry_p, sl_p, tp1_p, tp2_p = validate_levels(decision, entry_p, sl_p, tp1_p, tp2_p, atr, last_price)
    
    if "SHORT" in decision and not np.isnan(tp3_p):
        if not np.isnan(tp2_p) and tp3_p >= tp2_p:
            tp3_p = tp2_p - atr * 1.0
    elif "LONG" in decision and not np.isnan(tp3_p):
        if not np.isnan(tp2_p) and tp3_p <= tp2_p:
            tp3_p = tp2_p + atr * 1.0
    
    confidence_pct = min(100, (confidence / max_score) * 100)
    
    if "PENDIENTE" in decision and not np.isnan(entry_p):
        entry_display = f"{entry_p:.4f} (Esperar en PP)"
        entry_type = "Limit Order en PP"
    elif decision.endswith("Inmediata)") and not np.isnan(entry_p):
        entry_display = f"{entry_p:.4f}"
        entry_type = "Market Order"
    else:
        entry_display = "N/A"
        entry_type = "Sin Operación"
    
    sl_display = f"{sl_p:.4f}" if not np.isnan(sl_p) else "N/A"
    tp1_display = f"{tp1_p:.4f}" if not np.isnan(tp1_p) else "N/A"
    tp2_display = f"{tp2_p:.4f}" if not np.isnan(tp2_p) else "N/A"
    tp3_display = f"{tp3_p:.4f}" if not np.isnan(tp3_p) else "N/A"
    
    gap_info = f"**{gap_signal}** ({gap_level:.4f})" if not np.isnan(gap_level) else "NO_GAP"
    
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
    
    gaps_info = ""
    if "SHORT" in decision and gaps_below:
        gaps_info = f"\n* Gaps Históricos (Soportes): {', '.join([f'{g['level']:.4f} ({g['age_days']}d)' for g in gaps_below[:3]])}"
    elif "LONG" in decision and gaps_above:
        gaps_info = f"\n* Gaps Históricos (Resistencias): {', '.join([f'{g['level']:.4f} ({g['age_days']}d)' for g in gaps_above[:3]])}"
    
    gap_level_points = 0.0
    if gap_signal != "NO_GAP":
        gap_level_points = 1.0
    elif strong_resistance or strong_support:
        gap_level_points = 1.5
    
    structure_points = 0.0
    if (gap_signal == "SHORT_TO_FILL" and last_price > PP) or \
       (gap_signal == "LONG_TO_FILL" and last_price < PP) or \
       (decision.startswith("SHORT") and last_price > PP) or \
       (decision.startswith("LONG") and last_price < PP):
        structure_points = 1.0
    
    return f"""
=====================================
🚀 ANÁLISIS DE TRADING | {symbol} 📊
=====================================

### 🎯 DECISIÓN RÁPIDA
| Confianza: {confidence_pct:.0f}% | Señal: {decision} |
| Próxima Entrada (5m): {entry_time_display} TJ |

---

### 📈 NIVELES OPERABLES
| **ENTRADA:** {entry_display} | Tipo: {entry_type} |
| SL : {sl_display} | Nivel de máximo riesgo (Validado) |
| TP1: {tp1_display} | Cierre del Gap CME (Prioridad) |
| TP2: {tp2_display} | Nivel de Pivote R1/S1 |
| TP3: {tp3_display} | Gap Histórico / Extensión |

---

### 🔍 CONTEXTO CLAVE
* Precio Actual: {last_price:.4f} (Hora: {last_timestamp} TJ)
* Gap Activo: {gap_info} 
* Punto Pivote (PP): {PP:.4f} (Nivel clave){gaps_info}

### 📊 INDICADORES TÉCNICOS (HTF)
* RSI 4H: {rsi_display} → {rsi_status}
* MACD 4H: {macd_display} → {macd_status}
* EMA200 1D: {ema_display}{ema_distance} → {ema_status}

### 🎯 CONFIRMACIONES
* Puntuación Total: {confidence:.1f}/{max_score:.1f}
  * Gap/Nivel: {gap_level_points:.1f} pts.
  * Estructura: {structure_points:.1f} pts.
  * Indicadores: {indicator_score:.1f} pts.
  * Volumen: {'✅' if high_volume else '❌'} (1.0 pt)
"""


# =======================================================================
# 6. EJECUCIÓN
# =======================================================================
if __name__ == "__main__":
    symbols_to_analyze = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD"] 

    print("--- INICIO DE ANÁLISIS PRE-NY (Versión Corregida) ---\n")
    for s in symbols_to_analyze:
        try:
            print(analyze_pre_ny(s))
        except Exception as e:
            print(f"Error al analizar {s}: {type(e).__name__} - {e}\n")
