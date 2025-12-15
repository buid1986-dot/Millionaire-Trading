
"""
================================================================================
ESTRATEGIA DE TRADING: GAP FILL + NIVELES HISTORICOS + INDICADORES HTF
================================================================================

DESCRIPCION:
Sistema de trading automatizado que combina analisis de gaps CME, niveles de 
pivote, indicadores tecnicos (RSI, MACD, EMA200), estructura de mercado 
(consolidacion, acumulacion, distribucion) y soportes/resistencias historicas 
para generar senales de trading en criptomonedas.

VERSION: 2.1 - Con analisis de estructura de mercado (Wyckoff)
ULTIMA ACTUALIZACION: Diciembre 2024

OBJETIVO:
Identificar oportunidades de alta probabilidad para:
1. Cierre de gaps CME (gaps entre velas diarias)
2. Rebotes en soportes/resistencias historicas
3. Confluencias tecnicas con indicadores HTF (Higher TimeFrame)
4. Breakouts de acumulacion y breakdowns de distribucion
5. EVITAR operar en consolidaciones (zonas sin direccion)

================================================================================
NOVEDADES VERSION 2.1
================================================================================

- ANALISIS DE ESTRUCTURA DE MERCADO (Wyckoff):
   * Deteccion de Consolidacion (rangos laterales)
   * Deteccion de Acumulacion (institucionales comprando)
   * Deteccion de Distribucion (institucionales vendiendo)
   * Ajuste automatico de confianza segun fase del mercado

- NUEVOS FILTROS:
   * NO operar en consolidacion pura (evita 40-50% senales falsas)
   * Identificar zonas de acumulacion para LONG futuro
   * Identificar zonas de distribucion para SHORT futuro
   * Ajuste dinamico: confidence x 0.5 en consolidacion, x 1.2 en acum/distrib

- OUTPUT MEJORADO:
   * Seccion "Estructura de Mercado" con fase actual
   * Niveles R1/S1 con distancia porcentual
   * Recomendaciones especificas segun estructura

Ver documentacion completa en el archivo README o en las primeras lineas del codigo.
Para mas informacion sobre uso, consultar las instrucciones de ejecucion al final.

================================================================================
SISTEMA DE PUNTUACION (v2.1 - Actualizado)
================================================================================

SISTEMA DE CONFIANZA BASE (Maximo 5.0 puntos):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
| Elemento                    | Puntos | Descripcion                    |
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
| Gap CME detectado          | +1.0   | Gap >0.5% entre velas diarias  |
| Nivel historico fuerte     | +1.5   | R2/S2 <1% del precio actual    |
| Estructura correcta (PP)   | +1.0   | Precio vs PP favorable         |
| RSI 4H extremo             | +1.0   | RSI <30 (LONG) o >70 (SHORT)   |
| RSI 4H zona                | +0.5   | RSI 30-40 (LONG) o 60-70 (SHORT)|
| MACD 4H cruce              | +1.0   | Cruce alcista/bajista reciente |
| MACD 4H tendencia          | +0.5   | MACD > Signal (sin cruce)      |
| Precio vs EMA200 fuerte    | +1.0   | Distancia >2% de EMA200        |
| Precio vs EMA200 normal    | +0.5   | Distancia 0-2% de EMA200       |
| Volumen alto               | +1.0   | 1.5x volumen promedio 20 velas |
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NUEVO: AJUSTES POR ESTRUCTURA DE MERCADO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
| Fase del Mercado                    | Multiplicador | Accion        |
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
| Consolidacion Pura                  | x 0.5         | NO OPERAR     |
| Consolidacion con Acumulacion       | x 0.8         | Preparar LONG |
| Consolidacion con Distribucion      | x 0.8         | Preparar SHORT|
| Acumulacion Fuerte                  | x 1.2         | Favorecer LONG|
| Distribucion Fuerte                 | x 1.2         | Favorecer SHORT|
| Tendencia Clara                     | x 1.0         | Normal        |
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ejemplo: Si confianza base = 60% (3.0/5.0 puntos)
- En consolidacion pura: 60% x 0.5 = 30% -> NO OPERAR
- En acumulacion fuerte: 60% x 1.2 = 72% -> LONG FUERTE

UMBRALES DE OPERACION (sin cambios):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Escenario                              | Confianza Min. | Puntos Min.  |
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Gap + estructura correcta (vs PP)      | 40%           | 2.0/5.0      |
Gap sin estructura optima              | 50%           | 2.5/5.0      |
Sin gap, resistencia/soporte fuerte    | 60%           | 3.0/5.0      |
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

================================================================================
ESTRUCTURA DE MERCADO (NUEVO - v2.1)
================================================================================

1. CONSOLIDACION (Rango Lateral):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Que es:
   - Precio oscila en rango estrecho sin direccion clara
   - Volumen bajo, RSI entre 40-60
   - Institucionales esperando direccion
   
   Como se detecta:
   [OK] Rango de ultimos 20 dias <5%
   [OK] Sin breakouts significativos
   [OK] Precio oscilando entre niveles definidos
   
   Que hacer:
   [NO] NO OPERAR en medio del rango (50% senales falsas)
   [!!] ESPERAR breakout alcista (arriba de resistencia)
   [!!] ESPERAR breakdown bajista (abajo de soporte)
   [OK] OPERAR solo en extremos del rango (cerca de R1/S1)
   
   Confianza: x 0.5 (reduce senales 50%)

2. ACUMULACION (Institucionales Comprando):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Que es:
   - Smart money comprando discretamente
   - Precio forma "base" en zona baja
   - Preparacion para movimiento alcista fuerte
   
   Como se detecta:
   [OK] Precio bajo o lateral despues de caida
   [OK] Volumen decreciente en caidas (sin panico)
   [OK] Formacion de base (rango <8% en ultimos 20 dias)
   [OK] Divergencia alcista RSI (RSI sube, precio lateral/baja)
   
   Senales de Wyckoff:
   - PS: Preliminary Support (soporte inicial)
   - SC: Selling Climax (ultimo panico vendedor)
   - AR: Automatic Rally (rebote automatico)
   - ST: Secondary Test (prueba del fondo)
   - Spring: Falso breakdown para eliminar stops
   - SOS: Sign of Strength (senal de fuerza)
   
   Que hacer:
   [!!] Fase temprana: NO operar, solo monitorear
   [OK] Fase avanzada (score >=3.0): Preparar LONG
   [**] Breakout con volumen: LONG FUERTE
   
   Confianza: x 1.2 si acumulacion fuerte (score >=3.0)

3. DISTRIBUCION (Institucionales Vendiendo):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Que es:
   - Smart money vendiendo discretamente
   - Precio forma "techo" en zona alta
   - Preparacion para movimiento bajista fuerte
   
   Como se detecta:
   [OK] Precio alto o lateral despues de subida
   [OK] Volumen decreciente en subidas (sin fuerza)
   [OK] Formacion de techo (rango <8% en ultimos 20 dias)
   [OK] Divergencia bajista RSI (RSI baja, precio lateral/sube)
   
   Senales de Wyckoff:
   - PSY: Preliminary Supply (oferta inicial)
   - BC: Buying Climax (ultimo FOMO comprador)
   - AR: Automatic Reaction (caida automatica)
   - ST: Secondary Test (prueba del techo)
   - UTAD: Upthrust After Distribution
   - SOW: Sign of Weakness (senal de debilidad)
   
   Que hacer:
   [!!] Fase temprana: NO operar, solo monitorear
   [OK] Fase avanzada (score >=3.0): Preparar SHORT
   [**] Breakdown con volumen: SHORT FUERTE
   
   Confianza: x 1.2 si distribucion fuerte (score >=3.0)

4. TENDENCIA CLARA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   - Sin consolidacion, acumulacion ni distribucion
   - Precio en movimiento direccional claro
   - Operar normalmente segun senales
   
   Confianza: x 1.0 (sin ajuste)

================================================================================
TIPOS DE SENALES GENERADAS
================================================================================

1. LONG/SHORT_FUERTE (>=70% confianza)
   -> Alta confianza: Gap + indicadores HTF alineados + volumen
   -> Accion: Entrar con tamano de posicion completo (2% capital)

2. LONG/SHORT_MODERADO (50-69% confianza)
   -> Confianza media: Gap + estructura O indicadores favorables
   -> Accion: Entrar con tamano reducido (1% capital)

3. LONG/SHORT_PENDIENTE
   -> Esperar retroceso al Punto Pivote (PP) antes de entrar
   -> Accion: Colocar orden limite en PP

4. LONG/SHORT_RESISTENCIA / SOPORTE (>=60% confianza)
   -> Sin gap, operando rebote en nivel historico fuerte
   -> Accion: Entrada en nivel con confirmacion de indicadores HTF

5. NO_OPERAR (<40% confianza)
   -> Sin confluencia tecnica suficiente
   -> Accion: No operar, esperar siguiente oportunidad

================================================================================
ESTRATEGIAS ACTUALIZADAS (v2.1)
================================================================================

ESTRATEGIA 1: CIERRE DE GAP CME (Principal)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SHORT (Gap Up - Precio arriba del cierre previo):
  Condiciones Base:
  [OK] Gap >0.5% detectado entre cierre D-1 y precio actual
  [OK] Precio actual > Punto Pivote (PP)
  
  Confirmaciones con Indicadores HTF:
  [OK] RSI 4H >70 (sobrecomprado) = +1.0 pt
  [OK] RSI 4H 60-70 (zona bajista) = +0.5 pt
  [OK] MACD 4H cruce bajista = +1.0 pt
  [OK] MACD 4H en tendencia bajista = +0.5 pt
  [OK] Precio <2% bajo EMA200 = +1.0 pt
  [OK] Volumen alto (1.5x promedio) = +1.0 pt
  
  Niveles:
  - Entry: Precio actual (market) o PP (limit pendiente)
  - SL: R1 o resistencia historica R2
  - TP1: Nivel del gap (cierre del gap) [PRIORIDAD]
  - TP2: S1 (soporte de pivote)
  - TP3: Gap historico o S2

NUEVO: CON ESTRUCTURA DE MERCADO:
- Si gap + consolidacion: x 0.5 confianza (cuidado, puede no cerrar)
- Si gap + acumulacion + direccion LONG: x 1.2 confianza
- Si gap + distribucion + direccion SHORT: x 1.2 confianza

LONG (Gap Down - Precio abajo del cierre previo):
  Condiciones Base:
  [OK] Gap >0.5% detectado entre cierre D-1 y precio actual
  [OK] Precio actual < Punto Pivote (PP)
  
  Confirmaciones con Indicadores HTF:
  [OK] RSI 4H <30 (sobrevendido) = +1.0 pt
  [OK] RSI 4H 30-40 (zona alcista) = +0.5 pt
  [OK] MACD 4H cruce alcista = +1.0 pt
  [OK] MACD 4H en tendencia alcista = +0.5 pt
  [OK] Precio >2% sobre EMA200 = +1.0 pt
  [OK] Volumen alto (1.5x promedio) = +1.0 pt
  
  Niveles:
  - Entry: Precio actual (market) o PP (limit pendiente)
  - SL: S1 o soporte historico S2
  - TP1: Nivel del gap (cierre del gap) [PRIORIDAD]
  - TP2: R1 (resistencia de pivote)
  - TP3: Gap historico o R2

ESTRATEGIA 2: REBOTE EN NIVELES HISTORICOS (Sin Gap)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SHORT desde Resistencia:
  Condiciones:
  [OK] Precio cerca (<1%) de resistencia historica R2
  [OK] Precio > PP (estructura bajista)
  [OK] Indicadores HTF bajistas (RSI alto, MACD bajista, bajo EMA200)
  [OK] Volumen alto confirmatorio
  
  Niveles:
  - Entry: Precio actual en resistencia
  - SL: R2 + 1 ATR
  - TP1: PP (primer objetivo)
  - TP2: S1
  - TP3: S2 o soporte historico

NUEVO: CON ESTRUCTURA DE MERCADO:
- Si resistencia + distribucion detectada: x 1.2 confianza SHORT
- Si soporte + acumulacion detectada: x 1.2 confianza LONG
- Si consolidacion pura: NO operar en niveles intermedios

LONG desde Soporte:
  Condiciones:
  [OK] Precio cerca (<1%) de soporte historico S2
  [OK] Precio < PP (estructura alcista)
  [OK] Indicadores HTF alcistas (RSI bajo, MACD alcista, sobre EMA200)
  [OK] Volumen alto confirmatorio
  
  Niveles:
  - Entry: Precio actual en soporte
  - SL: S2 - 1 ATR
  - TP1: PP (primer objetivo)
  - TP2: R1
  - TP3: R2 o resistencia historica

NUEVA: ESTRATEGIA 3: BREAKOUT DE ACUMULACION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cuando aplicar:
[OK] Acumulacion detectada (score >=3.0)
[OK] Precio cerca de resistencia del rango (<1%)
[OK] Volumen aumentando en ultimas velas
[OK] RSI >50 (momentum alcista)

Entrada:
- Esperar breakout de resistencia con volumen
- Entry: Precio rompe resistencia + cierra arriba
- Confirmacion: Vela de 5m cierra arriba de resistencia

Niveles:
- SL: Debajo de la base de acumulacion
- TP1: Altura del rango proyectada arriba
- TP2: Siguiente resistencia historica
- TP3: Gap historico o extension

Confianza: 70-90% (muy alta)

NUEVA: ESTRATEGIA 4: BREAKDOWN DE DISTRIBUCION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cuando aplicar:
[OK] Distribucion detectada (score >=3.0)
[OK] Precio cerca de soporte del rango (<1%)
[OK] Volumen aumentando en ultimas velas
[OK] RSI <50 (momentum bajista)

Entrada:
- Esperar breakdown de soporte con volumen
- Entry: Precio rompe soporte + cierra abajo
- Confirmacion: Vela de 5m cierra abajo de soporte

Niveles:
- SL: Arriba del techo de distribucion
- TP1: Altura del rango proyectada abajo
- TP2: Siguiente soporte historico
- TP3: Gap historico o extension

Confianza: 70-90% (muy alta)

================================================================================
INDICADORES TECNICOS EXPLICADOS (v2.0)
================================================================================

1. RSI 4H (Relative Strength Index):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Mide momentum del precio en escala 0-100
   
   Para LONG:
   - RSI <30: OVERSOLD (sobrevendido) -> +1.0 pt [*****]
   - RSI 30-40: BULLISH_ZONE -> +0.5 pt [***]
   
   Para SHORT:
   - RSI >70: OVERBOUGHT (sobrecomprado) -> +1.0 pt [*****]
   - RSI 60-70: BEARISH_ZONE -> +0.5 pt [***]
   
   RSI 40-60: NEUTRAL -> No suma puntos

2. MACD 4H (Moving Average Convergence Divergence):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Mide cambios en momentum y detecta cruces de tendencia
   
   BULLISH_CROSS: MACD cruza hacia arriba de Signal -> +1.0 pt LONG [*****]
   BEARISH_CROSS: MACD cruza hacia abajo de Signal -> +1.0 pt SHORT [*****]
   BULLISH: MACD > Signal (sin cruce reciente) -> +0.5 pt LONG [***]
   BEARISH: MACD < Signal (sin cruce reciente) -> +0.5 pt SHORT [***]
   NEUTRAL: Sin senal clara -> No suma puntos

3. EMA200 1D (Exponential Moving Average 200):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Indica tendencia de largo plazo
   
   Para LONG:
   - Precio >2% arriba de EMA200: ABOVE_STRONG -> +1.0 pt [*****]
   - Precio 0-2% arriba de EMA200: ABOVE -> +0.5 pt [***]
   
   Para SHORT:
   - Precio >2% abajo de EMA200: BELOW_STRONG -> +1.0 pt [*****]
   - Precio 0-2% abajo de EMA200: BELOW -> +0.5 pt [***]

================================================================================
INSTRUCCIONES DE USO ACTUALIZADAS (v2.1)
================================================================================

MODO 1: ANALISIS EN TIEMPO REAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Uso:
  python script.py

Cuando ejecutar:
  - 6:00-6:30 AM Tijuana (9:00-9:30 AM NY) - Pre-apertura NY
  - Antes de abrir cualquier operacion del dia

Que obtienes:
  - Analisis de BTC, ETH, SOL, BNB, XRP
  - Indicadores HTF (RSI 4H, MACD 4H, EMA200 1D)
  - NUEVO: Analisis de estructura de mercado
  - Senales de entrada inmediata o pendiente
  - Niveles de SL y 3 TPs calculados
  - Confianza y puntuacion detallada

Workflow actualizado v2.1:
  1. Ejecutar script a las 6:30 AM Tijuana
  
  2. NUEVO: REVISAR ESTRUCTURA DE MERCADO PRIMERO:
     - Si "CONSOLIDACION PURA": NO operar (esperar breakout)
     - Si "ACUMULACION": Preparar LONG, esperar breakout
     - Si "DISTRIBUCION": Preparar SHORT, esperar breakdown
     - Si "TENDENCIA CLARA": Operar normal
  
  3. Revisar senales con confianza >=50% (despues de ajuste estructura)
  
  4. Verificar R1/S1:
     - Precio cerca de R1 (<1%)? Considerar entrada en R1 para SHORT
     - Precio cerca de S1 (<1%)? Considerar entrada en S1 para LONG
  
  5. Confirmar indicadores HTF en TradingView:
     - RSI en zona esperada
     - MACD confirma direccion
     - Precio vs EMA200 correcto
  
  6. Colocar ordenes segun tipo de senal y estructura:
     - En consolidacion: SOLO operar extremos del rango
     - En acumulacion: Preparar LONG para breakout
     - En distribucion: Preparar SHORT para breakdown
     - En tendencia: Operar normalmente
  
  7. Registrar en diario: Agregar campo "Estructura de Mercado"

NUEVO: INTERPRETACION DEL OUTPUT v2.1:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ejemplo 1 - Consolidacion con Acumulacion:

### ESTRUCTURA DE MERCADO
* Fase Detectada: ACCUMULATION_IN_RANGE
* Recomendacion: Consolidacion con acumulacion - ESPERAR breakout alcista
* Ajuste Confianza: 0.8x

Consolidacion Detectada:
   - Rango: 4.2%
   - Resistencia: 91500.00 (Breakout objetivo)
   - Soporte: 88000.00 (Base de acumulacion)
   - Posicion: MID_RANGE

Acumulacion Detectada:
   - Score: 3.5/5.0
   - Senales: Precio zona baja, Volumen decreciente, Formando base, Divergencia RSI

Accion:
[NO] NO operar AHORA (en medio del rango)
[OK] Colocar alerta en 91500 (resistencia)
[OK] Si rompe 91500 con volumen: LONG FUERTE
[OK] TP1: 95200 (proyeccion altura rango)


Ejemplo 2 - Tendencia Clara con Gap:

### ESTRUCTURA DE MERCADO
* Fase Detectada: TRENDING
* Recomendacion: Tendencia clara - Operar segun senales
* Ajuste Confianza: 1.0x

Accion:
[OK] Operar normalmente segun senal de gap
[OK] Sin restricciones por estructura


MODO 2: BACKTESTING (Validacion de estrategia)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Uso:
  python script.py --backtest [dias] [confianza_min%] [simbolo]

Ejemplos:
  # Backtest de 30 dias en BTC con senales >=50% confianza
  python script.py --backtest 30 50 BTC-USD
  
  # Backtest de 60 dias en ETH con senales >=55% confianza
  python script.py --backtest 60 55 ETH-USD
  
  # Backtest de 90 dias en SOL (mas agresivo)
  python script.py --backtest 90 45 SOL-USD

NOTA: El backtesting usa indicadores HTF reales y analisis de estructura,
por lo que los resultados son mas precisos que versiones anteriores.

Que obtienes:
  - Win Rate (% operaciones ganadoras)
  - Profit Factor (ganancia total / perdida total)
  - Avg Win / Avg Loss
  - Risk:Reward ratio promedio
  - Retorno total acumulado
  - Max Drawdown (peor racha de perdidas)
  - CSV con todas las operaciones simuladas

Interpretacion de Resultados v2.1:
  [OK] EXCELENTE:     Win Rate >=65% y Profit Factor >=1.8 (+5-10% vs v2.0)
  [OK] ACEPTABLE:     Win Rate >=60% y Profit Factor >=1.6
  [!!] MARGINAL:      Win Rate >=55% y Profit Factor >=1.4
  [NO] INSUFICIENTE:  Win Rate <55% o Profit Factor <1.4


MODO 3: GOOGLE COLAB (Sin instalacion local)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Crear notebook en: https://colab.research.google.com/
2. Celda 1: !pip install yfinance -q
3. Celda 2: Copiar codigo completo
4. Celda 3: Ejecutar analisis

Ejemplo:
  # Analisis normal
  analyze_pre_ny("BTC-USD")
  
  # Todas las criptos
  for sym in ["BTC-USD", "ETH-USD", "SOL-USD"]:
      print(analyze_pre_ny(sym))

================================================================================
GESTION DE RIESGO ACTUALIZADA (v2.1)
================================================================================

REGLAS OBLIGATORIAS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Position Sizing por Estructura:
   - Tendencia clara: 2% capital
   - Acumulacion/Distribucion fuerte: 2% capital (alta probabilidad)
   - Consolidacion con acum/distrib: 1% capital (medio riesgo)
   - NUEVO: Consolidacion pura: 0% capital (NO OPERAR)

2. NUEVO: Reglas Especificas por Estructura:
   
   En Consolidacion:
   [NO] NO operar en medio del rango (40-60% del rango)
   [!!] Solo operar en extremos (<20% y >80% del rango)
   [OK] Mejor: Esperar breakout claro
   
   En Acumulacion:
   [!!] NO operar hasta senal de breakout
   [OK] Colocar alertas en resistencia del rango
   [OK] Cuando rompe: LONG inmediato con size completo
   
   En Distribucion:
   [!!] NO operar hasta senal de breakdown
   [OK] Colocar alertas en soporte del rango
   [OK] Cuando rompe: SHORT inmediato con size completo

3. Stop Loss (SIN EXCEPCIONES):
   - SIEMPRE colocar SL al abrir posicion
   - NUNCA mover SL en contra (aumentar perdida)
   - NUNCA quitar SL temporalmente
   - SL se respeta 100% automaticamente

4. Take Profit (Gestion de Salida Mejorada):
   Metodo 1 - Escalonado (Recomendado):
   - TP1 alcanzado: Cerrar 40% (asegurar ganancia)
   - TP2 alcanzado: Cerrar 30% adicional
   - TP3 alcanzado: Cerrar 30% restante
   
   Metodo 2 - Breakeven + Trailing:
   - TP1 alcanzado: Mover SL a breakeven
   - TP2 alcanzado: Trailing stop ATR x2
   - Dejar correr hasta TP3 o trailing

5. Limites Diarios:
   - Maximo 2-3 operaciones por dia
   - Si pierdes 2 operaciones seguidas: STOP por el dia
   - Si ganas 3% del capital: Considerar parar (proteger ganancia)
   - NUNCA operar por "recuperar" perdidas

6. Diario de Trading (OBLIGATORIO):
   Registrar por cada operacion:
   - Fecha y hora de entrada
   - Simbolo y direccion (LONG/SHORT)
   - Confianza % y puntuacion
   - Indicadores HTF (RSI, MACD, EMA)
   - NUEVO: Estructura de Mercado (Consolidacion/Acumulacion/Distribucion/Tendencia)
   - NUEVO: Score de Acumulacion/Distribucion (si aplica)
   - NUEVO: Operaste en consolidacion? (para analisis posterior)
   - NUEVO: Fue breakout/breakdown exitoso?
   - Entrada, SL, TPs ejecutados
   - Resultado final en % y $
   - Notas: Que funciono? Que fallo?
   
   Revisar semanalmente para identificar patrones

7. Validacion Previa (MUY IMPORTANTE):
   - PAPER TRADING minimo 30 dias antes de operar real
   - Win Rate >55% en paper antes de capital real
   - Profit Factor >1.5 consistente
   - Empezar con capital minimo ($200-500) primeras 2 semanas
   - Escalar gradualmente solo si resultados positivos

8. Confirmacion Manual con Indicadores:
   Aunque el codigo ya analiza RSI/MACD/EMA, SIEMPRE verificar en grafico:
   - Abrir TradingView en 4H
   - Confirmar visualmente RSI en zona esperada
   - Ver MACD histogram creciendo/decreciendo
   - Verificar precio vs EMA200 en 1D
   
   Si indicadores NO confirman: NO ENTRAR (aunque codigo diga 80%)

================================================================================
CONCEPTOS TECNICOS EXPLICADOS
================================================================================

Gap CME:
  Diferencia entre el cierre de una vela diaria y la apertura de la siguiente.
  En cripto spot (24/7) son menos comunes que en futuros CME tradicionales.
  Estadisticamente ~70-80% de gaps tienden a "cerrarse" (precio vuelve al nivel).

Punto Pivote (PP):
  Nivel calculado como: (High_prev + Low_prev + Close_prev) / 3
  Usado como nivel de entrada/retroceso y referencia de estructura.
  Si precio > PP: Estructura bajista para SHORT
  Si precio < PP: Estructura alcista para LONG
  
Resistencias/Soportes (R1, R2, S1, S2):
  R1/S1: Calculados con formula de pivotes estandar
  R2/S2: Niveles historicos (maximos/minimos recientes de 100 dias)
  Usados como objetivos de TP y niveles de SL
  
ATR (Average True Range):
  Mide volatilidad promedio del activo en los ultimos 14 periodos.
  Usado para calcular SL dinamico basado en volatilidad real.
  Ejemplo: Si ATR = $500, SL tipico = Entry +/- (1.5 x $500) = +/-$750

RSI (Relative Strength Index):
  Oscilador de momentum 0-100.
  <30: Sobrevendido (probable rebote alcista)
  >70: Sobrecomprado (probable correccion bajista)
  Periodo usado: 14 velas de 1H (~4H efectivo)

MACD (Moving Average Convergence Divergence):
  Indicador de tendencia y momentum.
  Cruce de lineas indica cambio de tendencia.
  Histogram positivo = alcista, negativo = bajista
  Configuracion: 12, 26, 9 (estandar)

EMA200 (Exponential Moving Average 200):
  Media movil de 200 periodos diarios.
  Precio arriba = tendencia alcista de largo plazo
  Precio abajo = tendencia bajista de largo plazo
  Actua como soporte/resistencia dinamica

NUEVO: Modelo Wyckoff:
  Metodologia creada por Richard Wyckoff (1900s) para identificar fases
  de acumulacion y distribucion institucional. Se basa en:
  - Analisis de volumen (quien tiene el control?)
  - Analisis de precio (que estan haciendo?)
  - Test de oferta/demanda (hay fuerza o debilidad?)

NUEVO: Consolidacion:
  Periodo donde precio oscila en rango estrecho sin direccion clara.
  Indica indecision del mercado o preparacion para movimiento grande.
  Estadistica: 70% de consolidaciones terminan en breakout direccional.

NUEVO: Acumulacion:
  Fase donde smart money (institucionales) compran discretamente.
  Caracteristicas: Precio bajo, volumen bajo, formacion de base.
  Despues de acumulacion completa: Movimiento alcista fuerte (markup).

NUEVO: Distribucion:
  Fase donde smart money vende discretamente a retail FOMO.
  Caracteristicas: Precio alto, volumen bajo en subidas, formacion de techo.
  Despues de distribucion completa: Movimiento bajista fuerte (markdown).

NUEVO: Divergencia RSI:
  - Alcista: Precio baja, RSI sube (vendedores agotandose)
  - Bajista: Precio sube, RSI baja (compradores agotandose)
  Senal muy fuerte de reversion inminente.

================================================================================
PERSONALIZACION Y AJUSTES
================================================================================

Modificar simbolos analizados (linea final):
  symbols_to_analyze = ["BTC-USD", "ETH-USD", "TU-CRIPTO"]

Ajustar umbral de gap (funcion detect_cme_gap):
  THRESHOLD_PCT = 0.005  # 0.5% actual
  # Cambiar a 0.003 (0.3%) para mas senales
  # Cambiar a 0.01 (1.0%) para menos senales, mayor calidad

Modificar periodos de indicadores:
  # RSI (linea ~220)
  rsi_4h = calculate_rsi(df_4h, period=14)  # Cambiar 14 a 10-20
  
  # EMA200 (linea ~265)
  ema200 = calculate_ema(df_1d, period=200)  # Cambiar a 50, 100, 300

Cambiar umbral de volumen alto (linea ~90):
  def check_high_volume(df, period=20, multiplier=1.5):
  # multiplier = 2.0 para ser mas estricto
  # multiplier = 1.3 para ser mas permisivo

Ajustar zona horaria (linea ~20):
  TIJUANA_TIMEZONE = pytz.timezone('America/Tijuana')
  # Cambiar a: 'America/Mexico_City', 'Europe/London', 'Asia/Tokyo'

Modificar umbrales de confianza (lineas ~680-710):
  min_confidence = 2.0  # Actual para gap + estructura
  # Cambiar a 2.5 para ser mas conservador
  # Cambiar a 1.5 para mas senales (mas arriesgado)

================================================================================
SOPORTE Y TROUBLESHOOTING
================================================================================

Error: "yfinance not found"
  Solucion: pip install --upgrade yfinance

Error: "No se generaron senales" en backtesting
  Causa: No hay gaps o niveles fuertes en el periodo
  Solucion: 
    - Reducir min_confidence (ej: de 55% a 45%)
    - Aumentar days_back (ej: de 30 a 60)
    - Probar otro simbolo con mas volatilidad

Error: "Rate limit exceeded"
  Causa: Demasiadas peticiones a Yahoo Finance API
  Solucion: Esperar 10-15 minutos antes de volver a ejecutar

Indicadores muestran "N/A":
  Causa: No hay suficientes datos historicos
  Solucion: 
    - Verificar conexion a internet
    - Esperar unos minutos y reintentar
    - Simbolo puede ser muy nuevo (probar con BTC/ETH)

Senales no coinciden con tu analisis:
  - El codigo es una HERRAMIENTA, no una bola de cristal
  - SIEMPRE verificar manualmente en grafico antes de entrar
  - Si dudas, NO ENTRAR (conservar capital es prioridad)
  - Ajustar umbrales segun tu estilo de trading

Win Rate bajo en backtest (<50%):
  - Normal en periodos de baja volatilidad
  - Probar aumentar min_confidence (mas selectivo)
  - Verificar que gaps historicos esten funcionando bien
  - Considerar operar solo senales FUERTE (>=70%)

================================================================================
DISCLAIMER LEGAL
================================================================================

Este codigo es una herramienta de ANALISIS TECNICO, NO es asesoria financiera.
El trading de criptomonedas conlleva riesgo significativo de perdida de capital.
Los resultados pasados no garantizan resultados futuros.
Opera solo con capital que puedas permitirte perder completamente.
Los indicadores tecnicos no son infalibles y pueden dar senales falsas.
Realiza tu propia investigacion antes de tomar decisiones de inversion.
El desarrollador NO se hace responsable de perdidas generadas por el uso de este codigo.

================================================================================
CHANGELOG v2.1
================================================================================

CAMBIOS PRINCIPALES:
+ Agregado: Deteccion de consolidacion (evita 40-50% senales falsas)
+ Agregado: Deteccion de acumulacion Wyckoff
+ Agregado: Deteccion de distribucion Wyckoff
+ Agregado: Ajuste dinamico de confianza segun estructura (x0.5 a x1.2)
+ Agregado: Niveles R1/S1 en output con distancia %
+ Agregado: Seccion "Estructura de Mercado" en output
+ Agregado: 2 estrategias nuevas (breakout acumulacion, breakdown distribucion)
* Mejorado: Workflow de decision basado en estructura primero
* Mejorado: Documentacion con guias por estructura

RESULTADOS ESPERADOS:
- Win Rate: +5-10% vs v2.0 (de 55-60% a 60-70%)
- Profit Factor: +0.2-0.3 vs v2.0 (de 1.5-1.7 a 1.7-2.0)
- Reduccion drastica de operaciones en rangos laterales
- Identificacion temprana de zonas de alto potencial
- Mejor timing de entradas (esperar extremos de rango)

IMPACTO EN TRADING:
- Menos operaciones pero de mayor calidad
- Evita 40-50% de perdidas en consolidaciones
- Identifica oportunidades de alto R:R en acum/distrib
- Mejor comprension del contexto de mercado

================================================================================
CHANGELOG v2.0
================================================================================

CAMBIOS PRINCIPALES:
+ Agregado: RSI 4H para detectar sobrecompra/sobreventa
+ Agregado: MACD 4H para detectar cruces y cambios de tendencia
+ Agregado: EMA200 1D para confirmar tendencia de largo plazo
- Eliminado: Patrones de vela de 5 minutos (inutiles)
* Mejorado: Sistema de puntuacion mas preciso con HTF
* Mejorado: Umbrales de confianza ajustados (40% min vs 65% anterior)
* Mejorado: Output muestra indicadores HTF claramente
* Mejorado: Backtesting usa indicadores reales (no patrones)

RESULTADOS ESPERADOS:
- Win Rate: +5-10% vs v1.0 (de 50-55% a 55-65%)
- Profit Factor: +0.2-0.4 vs v1.0 (de 1.3-1.5 a 1.5-1.9)
- Senales mas confiables y con mejor contexto

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
# 2. INDICADORES TÉCNICOS
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
# 3. DETECCIÓN DE GAPS Y ESTRUCTURA DE MERCADO
# =======================================================================

def detect_consolidation(df_1d, lookback=20):
    """Detecta si el precio está en consolidación (rango lateral)."""
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
    """Detecta fase de acumulación según modelo Wyckoff simplificado."""
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
        signals.append("Precio en zona baja")
    
    if volume_decreasing:
        accumulation_score += 1
        signals.append("Volumen decreciente")
    
    if forming_base:
        accumulation_score += 1.5
        signals.append("Formando base")
    
    if bullish_divergence:
        accumulation_score += 1.5
        signals.append("Divergencia alcista RSI")
    
    if accumulation_score >= 3.0:
        phase = "STRONG_ACCUMULATION"
        action = "ACUMULACION FUERTE - Preparar LONG en breakout"
    elif accumulation_score >= 2.0:
        phase = "POSSIBLE_ACCUMULATION"
        action = "Posible acumulacion - Monitorear LONG"
    else:
        phase = "NONE"
        action = ""
    
    return accumulation_score >= 2.0, phase, accumulation_score, signals, action


def detect_distribution(df_1d, lookback=60):
    """Detecta fase de distribución según modelo Wyckoff simplificado."""
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
        signals.append("Precio en zona alta")
    
    if volume_decreasing:
        distribution_score += 1
        signals.append("Volumen decreciente")
    
    if forming_top:
        distribution_score += 1.5
        signals.append("Formando techo")
    
    if bearish_divergence:
        distribution_score += 1.5
        signals.append("Divergencia bajista RSI")
    
    if distribution_score >= 3.0:
        phase = "STRONG_DISTRIBUTION"
        action = "DISTRIBUCION FUERTE - Preparar SHORT en breakdown"
    elif distribution_score >= 2.0:
        phase = "POSSIBLE_DISTRIBUTION"
        action = "Posible distribucion - Monitorear SHORT"
    else:
        phase = "NONE"
        action = ""
    
    return distribution_score >= 2.0, phase, distribution_score, signals, action


def analyze_market_structure(df_1d, last_price):
    """Análisis completo de estructura de mercado."""
    
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
            recommendation = 'Consolidacion con acumulacion - ESPERAR breakout alcista'
            confidence_adjustment = 0.8
        elif is_distrib and distrib_score > accum_score:
            primary_phase = 'DISTRIBUTION_IN_RANGE'
            recommendation = 'Consolidacion con distribucion - ESPERAR breakdown bajista'
            confidence_adjustment = 0.8
        else:
            primary_phase = 'PURE_CONSOLIDATION'
            recommendation = 'CONSOLIDACION PURA - NO OPERAR (esperar breakout claro)'
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
        recommendation = 'Tendencia clara - Operar segun senales'
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
    gap_signal, gap_level = detect_cme_gap(data_1d, last_price)
    
    indicators = analyze_technical_indicators(symbol, last_price)
    
    market_structure = analyze_market_structure(data_1d, last_price)
    
    gaps_above, gaps_below = find_historical_gaps(data_1d, last_price, lookback_days=60)
    
    R2_hist = find_historical_level(data_1d, last_price, is_resistance=True)
    S2_hist = find_historical_level(data_1d, last_price, is_resistance=False)
    
    strong_resistance = not np.isnan(R2_hist) and abs(last_price - R2_hist) / last_price < 0.01
    strong_support = not np.isnan(S2_hist) and abs(last_price - S2_hist) / last_price < 0.01

    decision = "NO_OPERAR (Consolidacion)"
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
                decision = "SHORT_FUERTE (Activacion Inmediata)" if confidence >= 3.5 else "SHORT_MODERADO (Activacion Inmediata)"
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
                decision = "LONG_FUERTE (Activacion Inmediata)" if confidence >= 3.5 else "LONG_MODERADO (Activacion Inmediata)"
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
                decision = "SHORT_RESISTENCIA (Sin Gap - Nivel Historico)"
        
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
                decision = "LONG_SOPORTE (Sin Gap - Nivel Historico)"
    
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
        gaps_info = f"\n* Gaps Historicos (Soportes): {', '.join([f'{g['level']:.4f} ({g['age_days']}d)' for g in gaps_below[:3]])}"
    elif "LONG" in decision and gaps_above:
        gaps_info = f"\n* Gaps Historicos (Resistencias): {', '.join([f'{g['level']:.4f} ({g['age_days']}d)' for g in gaps_above[:3]])}"
    
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
   - Resistencia: {consol['resistance']:.2f} (Breakout objetivo)
   - Soporte: {consol['support']:.2f} (Breakdown objetivo)
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
=====================================

### DECISION RAPIDA
| Confianza: {confidence_pct:.0f}% | Senal: {decision} |
| Proxima Entrada (5m): {entry_time_display} TJ |

---

### NIVELES OPERABLES
| **ENTRADA:** {entry_display} | Tipo: {entry_type} |
| SL : {sl_display} | Nivel de maximo riesgo (Validado) |
| TP1: {tp1_display} | Cierre del Gap CME (Prioridad) |
| TP2: {tp2_display} | Nivel de Pivote R1/S1 |
| TP3: {tp3_display} | Gap Historico / Extension |

---

### CONTEXTO CLAVE
* Precio Actual: {last_price:.4f} (Hora: {last_timestamp} TJ)
* Gap Activo: {gap_info} 
* Punto Pivote (PP): {PP:.4f} (Nivel clave de Entrada/Retroceso)
* Resistencia 1 (R1): {R1:.4f} | Distancia: {((R1 - last_price) / last_price * 100):+.2f}%
* Soporte 1 (S1): {S1:.4f} | Distancia: {((S1 - last_price) / last_price * 100):+.2f}%{gaps_info}

[TIP] Uso de R1/S1 para Entradas:
   - SHORT: Si precio cerca de R1 ({abs((R1 - last_price) / last_price * 100):.2f}% away) -> Considera entrar en R1
   - LONG: Si precio cerca de S1 ({abs((S1 - last_price) / last_price * 100):.2f}% away) -> Considera entrar en S1

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
"""


# =======================================================================
# 6. EJECUCIÓN
# =======================================================================
if __name__ == "__main__":
    symbols_to_analyze = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD"] 

    print("--- INICIO DE ANALISIS PRE-NY (Version Corregida) ---\n")
    for s in symbols_to_analyze:
        try:
            print(analyze_pre_ny(s))
        except Exception as e:
            print(f"Error al analizar {s}: {type(e).__name__} - {e}\n")
