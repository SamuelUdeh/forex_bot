"""
Signal Engine (ENHANCED v5 - TRADING MACHINE)
=============================================
Complete trading signal generator combining:
- Technical Indicators (EMA, RSI, MACD, ADX, ATR, BB, Stochastic)
- Smart Money Concepts (Structure, S/R, FVG, Order Blocks, Liquidity)
- Candlestick Patterns (20+ reversal & continuation patterns)
- Volume Analysis (OBV, VWAP, Volume Spikes)
- Divergence Detection (RSI & MACD divergence for reversal signals)

Maximum Confluence Score: 14 points (Forex) / 13 points (Synthetics)
"""

import pandas as pd
import pandas_ta as ta
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass, field
import pytz

import config
from smc_analysis import SMCAnalyzer, SMCAnalysis, TrendDirection
from candlestick_patterns import CandlestickAnalyzer, CandlePattern
from volume_analysis import VolumeAnalyzer, VolumeAnalysis


@dataclass
class SignalResult:
    """Data class to hold signal analysis results"""
    pair: str
    display_name: str
    direction: str  # 'BUY' or 'SELL'
    score: int
    max_score: int
    grade: str  # 'A+', 'A', or 'B'
    entry: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float  # Third take profit
    atr: float
    rsi: float
    adx: float
    macd_state: str
    # Technical checklist
    ema_trend: bool
    ema_cross: bool
    rsi_neutral: bool
    macd_favorable: bool
    adx_strong: bool
    # SMC checklist
    structure_aligned: bool
    near_key_level: bool  # S/R
    in_order_block: bool
    fvg_confluence: bool
    liquidity_safe: bool
    # Bollinger Bands
    bb_confluence: bool  # Price at BB extreme
    # Candlestick Patterns
    candle_pattern_score: int  # 0-2 points
    # Volume Analysis
    volume_score: int  # 0-2 points
    # Session
    session_active: bool
    session_name: str
    datetime_utc: datetime
    checklist: Dict[str, bool]
    # Optional fields with defaults at the end
    candle_patterns: List[str] = field(default_factory=list)  # Pattern names
    volume_analysis: Optional[VolumeAnalysis] = None
    smc_analysis: Optional[SMCAnalysis] = None


class SignalEngine:
    """
    Complete Trading Machine - Technical + SMC + Candlestick + Volume confluence
    """

    def __init__(self):
        """Initialize with indicator settings from config"""
        self.settings = config.INDICATORS
        self.smc = SMCAnalyzer(swing_lookback=5)
        self.candle_analyzer = CandlestickAnalyzer()
        self.volume_analyzer = VolumeAnalyzer()

    def detect_divergence(self, df: pd.DataFrame, lookback: int = 20) -> Dict[str, Any]:
        """
        Detect RSI and MACD divergence

        Bullish Divergence: Price makes LOWER LOW but RSI/MACD makes HIGHER LOW
        Bearish Divergence: Price makes HIGHER HIGH but RSI/MACD makes LOWER HIGH

        Returns dict with divergence info
        """
        result = {
            "rsi_bullish_div": False,
            "rsi_bearish_div": False,
            "macd_bullish_div": False,
            "macd_bearish_div": False,
            "any_bullish_div": False,
            "any_bearish_div": False
        }

        if len(df) < lookback + 5:
            return result

        # Get recent data for divergence check
        recent = df.iloc[-lookback:].copy()

        # Find swing highs and lows in price
        def find_swings(series, window=3):
            """Find local swing highs and lows"""
            highs = []
            lows = []
            for i in range(window, len(series) - window):
                # Swing high: higher than neighbors
                if all(series.iloc[i] >= series.iloc[i-j] for j in range(1, window+1)) and \
                   all(series.iloc[i] >= series.iloc[i+j] for j in range(1, window+1)):
                    highs.append((i, series.iloc[i]))
                # Swing low: lower than neighbors
                if all(series.iloc[i] <= series.iloc[i-j] for j in range(1, window+1)) and \
                   all(series.iloc[i] <= series.iloc[i+j] for j in range(1, window+1)):
                    lows.append((i, series.iloc[i]))
            return highs, lows

        price_highs, price_lows = find_swings(recent["close"])

        # Check RSI divergence
        if "rsi" in recent.columns and not recent["rsi"].isna().all():
            rsi_highs, rsi_lows = find_swings(recent["rsi"])

            # Bullish divergence: price lower low, RSI higher low
            if len(price_lows) >= 2 and len(rsi_lows) >= 2:
                # Compare last two lows
                if price_lows[-1][1] < price_lows[-2][1]:  # Price made lower low
                    if rsi_lows[-1][1] > rsi_lows[-2][1]:  # RSI made higher low
                        result["rsi_bullish_div"] = True

            # Bearish divergence: price higher high, RSI lower high
            if len(price_highs) >= 2 and len(rsi_highs) >= 2:
                if price_highs[-1][1] > price_highs[-2][1]:  # Price made higher high
                    if rsi_highs[-1][1] < rsi_highs[-2][1]:  # RSI made lower high
                        result["rsi_bearish_div"] = True

        # Check MACD histogram divergence
        if "macd_hist" in recent.columns and not recent["macd_hist"].isna().all():
            macd_highs, macd_lows = find_swings(recent["macd_hist"])

            # Bullish divergence
            if len(price_lows) >= 2 and len(macd_lows) >= 2:
                if price_lows[-1][1] < price_lows[-2][1]:  # Price made lower low
                    if macd_lows[-1][1] > macd_lows[-2][1]:  # MACD made higher low
                        result["macd_bullish_div"] = True

            # Bearish divergence
            if len(price_highs) >= 2 and len(macd_highs) >= 2:
                if price_highs[-1][1] > price_highs[-2][1]:  # Price made higher high
                    if macd_highs[-1][1] < macd_highs[-2][1]:  # MACD made lower high
                        result["macd_bearish_div"] = True

        # Combine results
        result["any_bullish_div"] = result["rsi_bullish_div"] or result["macd_bullish_div"]
        result["any_bearish_div"] = result["rsi_bearish_div"] or result["macd_bearish_div"]

        return result

    def _check_reversal_setup(
        self,
        df: pd.DataFrame,
        rsi: float,
        smc_result,
        divergence: Dict[str, Any],
        near_support: bool,
        near_resistance: bool,
        adx: float,
        is_boom: bool,
        is_crash: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Check for reversal setup at extreme levels

        Reversal BUY requires:
        - RSI oversold (<30) OR bullish divergence
        - Near support level
        - BOS or CHoCH detected (structure shift)

        Reversal SELL requires:
        - RSI overbought (>70) OR bearish divergence
        - Near resistance level
        - BOS or CHoCH detected (structure shift)

        Returns dict with direction and score if valid, None otherwise
        """
        if smc_result is None:
            return None

        rsi_oversold = self.settings.get("rsi_oversold", 30)
        rsi_overbought = self.settings.get("rsi_overbought", 70)

        # Check for structure shift (BOS or CHoCH)
        structure_shift = smc_result.bos_detected or smc_result.choch_detected

        # ===== BULLISH REVERSAL =====
        bullish_reversal_score = 0

        # RSI oversold
        if rsi <= rsi_oversold:
            bullish_reversal_score += 2

        # Bullish divergence
        if divergence.get("any_bullish_div", False):
            bullish_reversal_score += 2

        # Near support
        if near_support:
            bullish_reversal_score += 1

        # Structure shift (BOS/CHoCH)
        if structure_shift:
            bullish_reversal_score += 2

        # In order block or FVG
        if smc_result.in_order_block or smc_result.in_fvg:
            bullish_reversal_score += 1

        # COMBO BONUS: RSI extreme + structure shift together = stronger signal
        if (rsi <= rsi_oversold) and structure_shift:
            bullish_reversal_score += 1

        # ===== BEARISH REVERSAL =====
        bearish_reversal_score = 0

        # RSI overbought
        if rsi >= rsi_overbought:
            bearish_reversal_score += 2

        # Bearish divergence
        if divergence.get("any_bearish_div", False):
            bearish_reversal_score += 2

        # Near resistance
        if near_resistance:
            bearish_reversal_score += 1

        # Structure shift (BOS/CHoCH)
        if structure_shift:
            bearish_reversal_score += 2

        # In order block or FVG
        if smc_result.in_order_block or smc_result.in_fvg:
            bearish_reversal_score += 1

        # COMBO BONUS: RSI extreme + structure shift together = stronger signal
        if (rsi >= rsi_overbought) and structure_shift:
            bearish_reversal_score += 1

        # ===== DETERMINE REVERSAL SIGNAL =====
        # Require minimum 5 points for reversal (stricter than trend-following)
        min_reversal_score = 5

        # Also require at least RSI extreme OR divergence (not just structure)
        has_momentum_signal_buy = (rsi <= rsi_oversold) or divergence.get("any_bullish_div", False)
        has_momentum_signal_sell = (rsi >= rsi_overbought) or divergence.get("any_bearish_div", False)

        if bullish_reversal_score >= min_reversal_score and has_momentum_signal_buy:
            if not is_crash:  # Don't buy on Crash indices
                return {
                    "direction": "BUY",
                    "score": bullish_reversal_score,
                    "type": "reversal"
                }

        if bearish_reversal_score >= min_reversal_score and has_momentum_signal_sell:
            if not is_boom:  # Don't sell on Boom indices
                return {
                    "direction": "SELL",
                    "score": bearish_reversal_score,
                    "type": "reversal"
                }

        return None

    def get_htf_trend(self, df: pd.DataFrame) -> str:
        """
        Get Higher Timeframe (H4) trend from H1 data by resampling.

        Returns:
            'bullish' - H4 EMA50 > EMA200 and price above EMA50
            'bearish' - H4 EMA50 < EMA200 and price below EMA50
            'neutral' - Mixed signals
        """
        try:
            # Resample H1 to H4
            df_h4 = df.resample('4h').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last'
            }).dropna()

            if len(df_h4) < 50:
                return 'neutral'

            # Calculate EMAs on H4
            ema50_h4 = ta.ema(df_h4['close'], length=50)
            ema200_h4 = ta.ema(df_h4['close'], length=50)  # Use 50 for H4 (equivalent to 200 on H1)

            if ema50_h4 is None or len(ema50_h4) < 1:
                return 'neutral'

            current_close = df_h4['close'].iloc[-1]
            current_ema50 = ema50_h4.iloc[-1]

            # Simple trend determination
            if current_close > current_ema50:
                return 'bullish'
            elif current_close < current_ema50:
                return 'bearish'
            else:
                return 'neutral'

        except Exception as e:
            return 'neutral'

    def get_daily_trend(self, df: pd.DataFrame) -> str:
        """
        Get Daily trend from H4 data by resampling.
        Used for BTC/USD MTF confirmation.

        Returns:
            'bullish' - Daily EMA50 > EMA200
            'bearish' - Daily EMA50 < EMA200
            'neutral' - Mixed signals or insufficient data
        """
        try:
            # Resample H4 to Daily
            df_daily = df.resample('1D').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last'
            }).dropna()

            if len(df_daily) < 50:
                return 'neutral'

            # Calculate EMAs on Daily
            ema50_daily = ta.ema(df_daily['close'], length=50)
            ema200_daily = ta.ema(df_daily['close'], length=200)

            if ema50_daily is None or ema200_daily is None:
                return 'neutral'
            if len(ema50_daily) < 1 or len(ema200_daily) < 1:
                return 'neutral'

            current_ema50 = ema50_daily.iloc[-1]
            current_ema200 = ema200_daily.iloc[-1]

            # Trend based on EMA crossover
            if current_ema50 > current_ema200:
                return 'bullish'
            elif current_ema50 < current_ema200:
                return 'bearish'
            else:
                return 'neutral'

        except Exception as e:
            return 'neutral'

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators on price data"""
        if df is None or len(df) < self.settings["ema_slow"]:
            return None

        df = df.copy()

        # ===== TREND INDICATORS =====
        df["ema_fast"] = ta.ema(df["close"], length=self.settings["ema_fast"])
        df["ema_slow"] = ta.ema(df["close"], length=self.settings["ema_slow"])

        slope_period = self.settings.get("ema_slope_period", 5)
        df["ema_fast_slope"] = df["ema_fast"].diff(slope_period)

        # ===== MOMENTUM INDICATORS =====
        df["rsi"] = ta.rsi(df["close"], length=self.settings["rsi_period"])

        macd = ta.macd(
            df["close"],
            fast=self.settings["macd_fast"],
            slow=self.settings["macd_slow"],
            signal=self.settings["macd_signal"]
        )
        if macd is not None:
            df["macd"] = macd.iloc[:, 0]
            df["macd_signal"] = macd.iloc[:, 1]
            df["macd_hist"] = macd.iloc[:, 2]

        # ===== TREND STRENGTH =====
        adx_period = self.settings.get("adx_period", 14)
        adx_result = ta.adx(df["high"], df["low"], df["close"], length=adx_period)
        if adx_result is not None:
            df["adx"] = adx_result.iloc[:, 0]

        # ===== VOLATILITY =====
        df["atr"] = ta.atr(
            df["high"], df["low"], df["close"],
            length=self.settings["atr_period"]
        )

        # ===== STOCHASTIC OSCILLATOR =====
        stoch_k = self.settings.get("stoch_k", 14)
        stoch_d = self.settings.get("stoch_d", 3)
        stoch_smooth = self.settings.get("stoch_smooth", 3)
        stoch = ta.stoch(df["high"], df["low"], df["close"], k=stoch_k, d=stoch_d, smooth_k=stoch_smooth)
        if stoch is not None:
            df["stoch_k"] = stoch.iloc[:, 0]  # %K line
            df["stoch_d"] = stoch.iloc[:, 1]  # %D line (signal)

        # ===== BOLLINGER BANDS =====
        bb_period = self.settings.get("bb_period", 20)
        bb_std = self.settings.get("bb_std", 2.0)
        bb = ta.bbands(df["close"], length=bb_period, std=bb_std)
        if bb is not None:
            df["bb_upper"] = bb.iloc[:, 2]  # Upper band
            df["bb_middle"] = bb.iloc[:, 1]  # Middle band (SMA)
            df["bb_lower"] = bb.iloc[:, 0]  # Lower band

        # ===== CANDLE ANALYSIS =====
        df["candle_body"] = abs(df["close"] - df["open"])
        df["candle_range"] = df["high"] - df["low"]
        df["body_percent"] = (df["candle_body"] / df["candle_range"]) * 100
        df["is_bullish"] = df["close"] > df["open"]
        df["is_bearish"] = df["close"] < df["open"]

        return df

    def is_session_active(self) -> Tuple[bool, str]:
        """Check if current time is within London or New York session"""
        utc_now = datetime.now(pytz.UTC)
        current_hour = utc_now.hour

        london = config.SESSIONS["london"]
        new_york = config.SESSIONS["new_york"]

        in_london = london["start"] <= current_hour < london["end"]
        in_new_york = new_york["start"] <= current_hour < new_york["end"]

        if in_london and in_new_york:
            return True, "London/NY Overlap"
        elif in_london:
            return True, "London"
        elif in_new_york:
            return True, "New York"
        else:
            return False, "Off-Session"

    def analyze(
        self,
        df: pd.DataFrame,
        pair: str,
        instrument_config: Dict[str, Any],
        fast_mode: bool = False
    ) -> Optional[SignalResult]:
        """
        TRADING MACHINE - Complete Analysis System

        SCORING SYSTEM (Max 15 for Forex, 14 for Synthetics):

        Technical Indicators (6 points):
        - +1 Price above/below EMA 200
        - +1 EMA 50/200 cross aligned
        - +1 RSI in neutral zone (45-55)
        - +1 MACD favorable
        - +1 ADX > 20 (trending market)
        - +1 Bollinger Band confluence

        Smart Money Concepts (4 points):
        - +1 Market structure aligned
        - +1 Near key S/R level
        - +1 In/near Order Block
        - +1 Not near liquidity zone

        Candlestick Patterns (2 points):
        - +1-2 Reversal/continuation patterns aligned with direction

        Volume Analysis (2 points):
        - +1 Volume spike confirmation
        - +1 OBV trend aligned

        Session (1 point - Forex only):
        - +1 London or New York session active

        MINIMUM TO TRADE: 9/15 (60% confluence)
        """
        # Calculate technical indicators
        df = self.calculate_indicators(df)

        if df is None or len(df) < 50:
            print(f"[ENGINE] Insufficient data for {pair}")
            return None

        # ===== GET CURRENT VALUES =====
        latest = df.iloc[-1]
        close = latest["close"]
        ema_fast = latest["ema_fast"]
        ema_slow = latest["ema_slow"]
        ema_slope = latest.get("ema_fast_slope", 0)
        rsi = latest["rsi"]
        macd = latest["macd"]
        macd_signal_line = latest["macd_signal"]
        atr = latest["atr"]
        adx = latest.get("adx", 25)
        is_bullish_candle = latest.get("is_bullish", False)
        is_bearish_candle = latest.get("is_bearish", False)

        # Check for NaN
        if pd.isna(ema_slow) or pd.isna(rsi) or pd.isna(macd) or pd.isna(atr):
            print(f"[ENGINE] NaN values in indicators for {pair}")
            return None

        if pd.isna(adx):
            adx = 25

        # ===== SMC ANALYSIS =====
        smc_result = self.smc.analyze(df, fast_mode=fast_mode)

        if smc_result is None:
            print(f"[ENGINE] SMC analysis failed for {pair}")
            return None

        # ===== CANDLESTICK PATTERN ANALYSIS =====
        candle_patterns = self.candle_analyzer.analyze(df)

        # ===== VOLUME ANALYSIS =====
        vol_analysis = self.volume_analyzer.analyze(df)

        # ===== DIVERGENCE DETECTION =====
        divergence_lookback = self.settings.get("divergence_lookback", 20)
        divergence = self.detect_divergence(df, lookback=divergence_lookback)

        # ===== SESSION CHECK =====
        use_session = instrument_config.get("use_session_filter", True)
        session_active, session_name = self.is_session_active()

        # ===== TECHNICAL CONFLUENCE =====

        # 1. Price vs EMA 200
        price_above_ema200 = close > ema_slow
        price_below_ema200 = close < ema_slow

        # 2. EMA Cross
        ema_bullish = ema_fast > ema_slow
        ema_bearish = ema_fast < ema_slow

        # 3. RSI Neutral Zone
        rsi_low = self.settings["rsi_neutral_low"]
        rsi_high = self.settings["rsi_neutral_high"]
        rsi_neutral = rsi_low <= rsi <= rsi_high

        # 4. MACD
        macd_bullish = macd > macd_signal_line
        macd_bearish = macd < macd_signal_line

        # 5. ADX Strong Trend
        adx_threshold = self.settings.get("adx_threshold", 20)
        adx_strong = adx > adx_threshold

        # 6. Stochastic Oscillator
        stoch_k = latest.get("stoch_k", 50)
        stoch_d = latest.get("stoch_d", 50)
        stoch_oversold = self.settings.get("stoch_oversold", 20)
        stoch_overbought = self.settings.get("stoch_overbought", 80)

        # Stochastic signals:
        # BUY: %K crosses above %D in oversold zone (<20) or %K < 30
        # SELL: %K crosses below %D in overbought zone (>80) or %K > 70
        stoch_bullish = stoch_k < 30 or (stoch_k > stoch_d and stoch_k < 50)
        stoch_bearish = stoch_k > 70 or (stoch_k < stoch_d and stoch_k > 50)

        # 7. Bollinger Bands (Mean Reversion Signal)
        bb_upper = latest.get("bb_upper", close + 1000)
        bb_lower = latest.get("bb_lower", close - 1000)
        bb_middle = latest.get("bb_middle", close)

        # Price at/near upper BB = good for SELL (mean reversion)
        # Price at/near lower BB = good for BUY (mean reversion)
        at_upper_bb = close >= bb_upper * 0.998  # Within 0.2% of upper band
        at_lower_bb = close <= bb_lower * 1.002  # Within 0.2% of lower band

        # ===== SMC CONFLUENCE =====

        # 6. Market Structure Aligned
        structure_bullish = smc_result.trend == TrendDirection.BULLISH
        structure_bearish = smc_result.trend == TrendDirection.BEARISH

        # 7. Near Key Level (S/R)
        near_support = smc_result.near_support
        near_resistance = smc_result.near_resistance

        # 8. In Order Block
        in_order_block = smc_result.in_order_block

        # 9. Liquidity Safety (NOT near liquidity = safer)
        liquidity_safe = not smc_result.near_liquidity

        # 10. FVG Confluence (price in Fair Value Gap)
        in_fvg = smc_result.in_fvg

        # ===== CALCULATE SCORES =====

        buy_score = 0
        sell_score = 0

        # Technical (5 points)
        if price_above_ema200:
            buy_score += 1
        if price_below_ema200:
            sell_score += 1

        if ema_bullish:
            buy_score += 1
        if ema_bearish:
            sell_score += 1

        if rsi_neutral:
            buy_score += 1
            sell_score += 1

        if macd_bullish:
            buy_score += 1
        if macd_bearish:
            sell_score += 1

        if adx_strong:
            buy_score += 1
            sell_score += 1

        # Stochastic (1 point)
        if stoch_bullish:
            buy_score += 1
        if stoch_bearish:
            sell_score += 1

        # SMC (4 points)
        if structure_bullish:
            buy_score += 1
        if structure_bearish:
            sell_score += 1

        # Near support is good for BUY, near resistance is good for SELL
        if near_support:
            buy_score += 1
        if near_resistance:
            sell_score += 1

        # Order block adds confluence
        if in_order_block:
            buy_score += 1
            sell_score += 1

        # Liquidity safety
        if liquidity_safe:
            buy_score += 1
            sell_score += 1

        # Bollinger Bands (+1 for mean reversion signal)
        if at_lower_bb:
            buy_score += 1  # Price at lower BB = good BUY opportunity
        if at_upper_bb:
            sell_score += 1  # Price at upper BB = good SELL opportunity

        # ===== CANDLESTICK PATTERNS (2 points max) =====
        buy_pattern_score, buy_patterns = self.candle_analyzer.get_pattern_score(candle_patterns, "BUY")
        sell_pattern_score, sell_patterns = self.candle_analyzer.get_pattern_score(candle_patterns, "SELL")

        buy_score += buy_pattern_score
        sell_score += sell_pattern_score

        # ===== VOLUME ANALYSIS (2 points max) =====
        # Volume spike confirms the move
        if vol_analysis.has_volume:
            if vol_analysis.is_volume_spike:
                buy_score += 1
                sell_score += 1
            # OBV trend alignment
            if vol_analysis.obv_trend == "UP":
                buy_score += 1
            elif vol_analysis.obv_trend == "DOWN":
                sell_score += 1

        # ===== DIVERGENCE (BONUS - not part of min score calculation) =====
        # Divergence is a powerful reversal signal but should be a BONUS
        # It adds points when present but doesn't increase the minimum required score
        divergence_bonus_buy = 0
        divergence_bonus_sell = 0
        if divergence["any_bullish_div"]:
            divergence_bonus_buy = 1
        if divergence["any_bearish_div"]:
            divergence_bonus_sell = 1

        # Calculate actual max score based on available data
        # Technical: 6 (EMA trend, EMA cross, RSI, MACD, ADX, BB)
        # SMC: 4 (structure, S/R, order block, liquidity)
        # Candlestick: 2
        # Volume: 2 (if available), Session: 1 (if applicable)
        # NOTE: Stochastic and Divergence are BONUSES - they add points but don't increase min threshold
        base_max = 12  # Technical (6) + SMC (4) + Candlestick (2)

        if vol_analysis.has_volume:
            base_max += 2  # Volume adds 2 points

        if use_session:
            base_max += 1  # Session adds 1 point

        max_score = base_max

        if use_session and session_active:
            buy_score += 1
            sell_score += 1

        # ===== SIGNAL DECISION =====

        # TRADING MACHINE: Minimum confluence required
        # Higher threshold = fewer signals but higher win rate
        # Allow per-pair confluence override in config
        confluence_pct = instrument_config.get("min_confluence", 0.80)
        min_score = int(max_score * confluence_pct)

        direction = None
        score = 0

        # ===== BOOM/CRASH DIRECTIONAL FILTER =====
        # Boom indices: ONLY BUY (spikes are upward)
        # Crash indices: ONLY SELL (spikes are downward)
        is_boom = "BOOM" in pair.upper()
        is_crash = "CRASH" in pair.upper()

        # ===== DIRECTION FILTER (from config) =====
        # allowed_directions: "ALL", "BUY_ONLY", "SELL_ONLY"
        allowed_directions = instrument_config.get("allowed_directions", "ALL").upper()

        # REFINED: Require structure alignment (no ranging market trades)
        # This filters out low-conviction setups
        if buy_score >= min_score and buy_score > sell_score:
            if structure_bullish:
                # Block SELL direction on Boom indices
                # Also block if SELL_ONLY is configured
                if not is_crash and allowed_directions != "SELL_ONLY":
                    direction = "BUY"
                    score = buy_score + divergence_bonus_buy  # Add divergence bonus
        elif sell_score >= min_score and sell_score > buy_score:
            if structure_bearish:
                # Block BUY direction on Crash indices
                # Also block if BUY_ONLY is configured
                if not is_boom and allowed_directions != "BUY_ONLY":
                    direction = "SELL"
                    score = sell_score + divergence_bonus_sell  # Add divergence bonus

        if direction is None:
            # ===== REVERSAL MODE =====
            # If no trend-following signal, check for reversal setup
            reversal_mode = instrument_config.get("reversal_mode", False)

            if reversal_mode:
                reversal_signal = self._check_reversal_setup(
                    df, rsi, smc_result, divergence,
                    near_support, near_resistance, adx,
                    is_boom, is_crash
                )
                if reversal_signal:
                    reversal_dir = reversal_signal["direction"]
                    # Apply direction filter to reversals too
                    if allowed_directions == "SELL_ONLY" and reversal_dir == "BUY":
                        return None
                    if allowed_directions == "BUY_ONLY" and reversal_dir == "SELL":
                        return None
                    direction = reversal_dir
                    score = reversal_signal["score"]
                    max_score = 8  # Reversal max score
                    is_reversal = True
                else:
                    return None
            else:
                return None
        else:
            is_reversal = False

        # REFINED: Additional ADX filter - require stronger trend
        # Skip signals in weak trending conditions (ADX < 20)
        # Skip ADX filter for reversals (reversals happen at trend exhaustion)
        if not is_reversal and adx < adx_threshold:
            return None

        # BOS (Break of Structure) requirement filter
        # Instruments with require_bos need BOS confirmation for ALL signals
        # This prevents trading in ranging markets
        require_bos = instrument_config.get("require_bos", False)
        if require_bos and not smc_result.bos_detected:
            return None  # No BOS = No trade (applies to trend AND reversal signals)

        # ===== MULTI-TIMEFRAME CONFIRMATION =====
        # Check H4 trend alignment with H1 signal
        use_mtf = instrument_config.get("use_mtf_confirmation", False)
        if use_mtf:
            htf_trend = self.get_htf_trend(df)
            # BUY signals need bullish H4 trend
            if direction == "BUY" and htf_trend == "bearish":
                return None  # H4 bearish, skip H1 BUY
            # SELL signals need bearish H4 trend
            if direction == "SELL" and htf_trend == "bullish":
                return None  # H4 bullish, skip H1 SELL

        # ===== DAILY MTF CONFIRMATION (for H4 signals like BTC) =====
        # Check Daily trend alignment with H4 signal
        use_daily_mtf = instrument_config.get("use_daily_mtf_confirmation", False)
        if use_daily_mtf:
            daily_trend = self.get_daily_trend(df)
            # BUY signals need bullish Daily trend
            if direction == "BUY" and daily_trend == "bearish":
                return None  # Daily bearish, skip H4 BUY
            # SELL signals need bearish Daily trend
            if direction == "SELL" and daily_trend == "bullish":
                return None  # Daily bullish, skip H4 SELL

        # Update max_score to include divergence bonus if present
        divergence_bonus = divergence_bonus_buy if direction == "BUY" else divergence_bonus_sell
        if divergence_bonus > 0:
            max_score += 1  # Add divergence to max for display

        # ===== CALCULATE ENTRY, SL, TP =====

        entry = close
        atr_sl = instrument_config.get("atr_multiplier_sl", 1.5)
        atr_tp1 = instrument_config.get("atr_multiplier_tp1", 1.5)
        atr_tp2 = instrument_config.get("atr_multiplier_tp2", 2.5)
        atr_tp3 = atr_tp2 * 1.5  # TP3 at 1.5x TP2 distance

        if direction == "BUY":
            stop_loss = entry - (atr * atr_sl)
            tp1 = entry + (atr * atr_tp1)
            tp2 = entry + (atr * atr_tp2)
            tp3 = entry + (atr * atr_tp3)
        else:
            stop_loss = entry + (atr * atr_sl)
            tp1 = entry - (atr * atr_tp1)
            tp2 = entry - (atr * atr_tp2)
            tp3 = entry - (atr * atr_tp3)

        # ===== DETERMINE GRADE =====
        # A+ = 95%+ confluence (12/12) - PERFECT setup
        # A  = 90%+ confluence (11/12) - Excellent setup
        # B  = 80%+ confluence (10/12) - Good setup (minimum)

        confluence_pct = (score / max_score) * 100
        if confluence_pct >= 95:  # 12/12
            grade = "A+"
        elif confluence_pct >= 90:  # 11/12
            grade = "A"
        else:  # 10/12
            grade = "B"

        # ===== BUILD CHECKLIST =====

        # Bollinger Band confluence for this direction
        bb_confluence = at_lower_bb if direction == "BUY" else at_upper_bb

        # Get pattern info for this direction
        pattern_score = buy_pattern_score if direction == "BUY" else sell_pattern_score
        pattern_names = buy_patterns if direction == "BUY" else sell_patterns

        # Get volume score for this direction
        vol_score, vol_desc = self.volume_analyzer.get_volume_signal(vol_analysis, direction)

        # Check divergence for this direction
        has_divergence = divergence["any_bullish_div"] if direction == "BUY" else divergence["any_bearish_div"]

        # Check stochastic for this direction
        stoch_favorable = stoch_bullish if direction == "BUY" else stoch_bearish

        checklist = {
            # Technical (7 points)
            "ema_trend": price_above_ema200 if direction == "BUY" else price_below_ema200,
            "ema_cross": ema_bullish if direction == "BUY" else ema_bearish,
            "rsi_neutral": rsi_neutral,
            "macd_favorable": macd_bullish if direction == "BUY" else macd_bearish,
            "stochastic": stoch_favorable,
            "adx_strong": adx_strong,
            "bb_confluence": bb_confluence,
            # SMC (4 points)
            "structure_aligned": structure_bullish if direction == "BUY" else structure_bearish,
            "near_key_level": near_support if direction == "BUY" else near_resistance,
            "in_order_block": in_order_block,
            "liquidity_safe": liquidity_safe,
            # Candlestick (2 points)
            "candle_pattern": pattern_score > 0,
            # Divergence (1 point)
            "divergence": has_divergence,
            # Volume (2 points)
            "volume_confirms": vol_score > 0,
            # Session (1 point)
            "session_active": session_active if use_session else True
        }

        return SignalResult(
            pair=pair,
            display_name=instrument_config.get("display_name", pair),
            direction=direction,
            score=score,
            max_score=max_score,
            grade=grade,
            entry=entry,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            atr=atr,
            rsi=rsi,
            adx=adx,
            macd_state="bullish" if macd_bullish else "bearish",
            ema_trend=checklist["ema_trend"],
            ema_cross=checklist["ema_cross"],
            rsi_neutral=rsi_neutral,
            macd_favorable=checklist["macd_favorable"],
            adx_strong=adx_strong,
            structure_aligned=checklist["structure_aligned"],
            near_key_level=checklist["near_key_level"],
            in_order_block=in_order_block,
            fvg_confluence=in_fvg,
            liquidity_safe=liquidity_safe,
            bb_confluence=bb_confluence,
            candle_pattern_score=pattern_score,
            candle_patterns=pattern_names,
            volume_score=vol_score,
            volume_analysis=vol_analysis,
            session_active=session_active,
            session_name=session_name,
            datetime_utc=datetime.now(pytz.UTC),
            checklist=checklist,
            smc_analysis=smc_result
        )


@dataclass
class PreSignalResult:
    """Data class for pre-signal (setup forming) alerts"""
    pair: str
    display_name: str
    direction: str  # 'BUY' or 'SELL'
    current_score: int
    max_score: int
    confluence_pct: float
    potential_entry: float
    potential_sl: float
    potential_tp1: float
    potential_tp2: float
    rsi: float
    adx: float
    conditions_met: Dict[str, bool]
    conditions_pending: list  # What's still needed


def pre_analyze(
    self,
    df: pd.DataFrame,
    pair: str,
    instrument_config: Dict[str, Any]
) -> Optional[PreSignalResult]:
    """
    Pre-scan for potential setups (run 15 mins before candle close)
    Returns PreSignalResult if 65%+ conditions are met
    """
    # Calculate indicators
    df = self.calculate_indicators(df)

    if df is None or len(df) < 50:
        return None

    latest = df.iloc[-1]
    close = latest["close"]
    ema_fast = latest["ema_fast"]
    ema_slow = latest["ema_slow"]
    rsi = latest["rsi"]
    macd = latest["macd"]
    macd_signal_line = latest["macd_signal"]
    atr = latest["atr"]
    adx = latest.get("adx", 25)

    if pd.isna(ema_slow) or pd.isna(rsi) or pd.isna(macd) or pd.isna(atr):
        return None

    if pd.isna(adx):
        adx = 25

    # SMC Analysis
    smc_result = self.smc.analyze(df, fast_mode=True)
    if smc_result is None:
        return None

    # Check conditions
    conditions = {
        "ema_trend_buy": close > ema_slow,
        "ema_trend_sell": close < ema_slow,
        "ema_cross_buy": ema_fast > ema_slow,
        "ema_cross_sell": ema_fast < ema_slow,
        "rsi_neutral": 45 <= rsi <= 55,
        "macd_buy": macd > macd_signal_line,
        "macd_sell": macd < macd_signal_line,
        "adx_strong": adx > 20,
        "structure_buy": smc_result.trend.value == "bullish",
        "structure_sell": smc_result.trend.value == "bearish",
        "near_support": smc_result.near_support,
        "near_resistance": smc_result.near_resistance,
        "liquidity_safe": not smc_result.near_liquidity,
    }

    # Calculate BUY score
    buy_score = 0
    buy_conditions_met = {}
    buy_pending = []

    if conditions["ema_trend_buy"]:
        buy_score += 1
        buy_conditions_met["EMA Trend"] = True
    else:
        buy_pending.append("Price above EMA200")

    if conditions["ema_cross_buy"]:
        buy_score += 1
        buy_conditions_met["EMA Cross"] = True
    else:
        buy_pending.append("EMA50 > EMA200")

    if conditions["rsi_neutral"]:
        buy_score += 1
        buy_conditions_met["RSI Neutral"] = True
    else:
        buy_pending.append("RSI 45-55")

    if conditions["macd_buy"]:
        buy_score += 1
        buy_conditions_met["MACD"] = True
    else:
        buy_pending.append("MACD bullish")

    if conditions["adx_strong"]:
        buy_score += 1
        buy_conditions_met["ADX Strong"] = True
    else:
        buy_pending.append("ADX > 20")

    if conditions["structure_buy"]:
        buy_score += 1
        buy_conditions_met["Structure"] = True
    else:
        buy_pending.append("Bullish structure")

    if conditions["near_support"]:
        buy_score += 1
        buy_conditions_met["Near Support"] = True

    if conditions["liquidity_safe"]:
        buy_score += 1
        buy_conditions_met["Liquidity Safe"] = True

    # Calculate SELL score
    sell_score = 0
    sell_conditions_met = {}
    sell_pending = []

    if conditions["ema_trend_sell"]:
        sell_score += 1
        sell_conditions_met["EMA Trend"] = True
    else:
        sell_pending.append("Price below EMA200")

    if conditions["ema_cross_sell"]:
        sell_score += 1
        sell_conditions_met["EMA Cross"] = True
    else:
        sell_pending.append("EMA50 < EMA200")

    if conditions["rsi_neutral"]:
        sell_score += 1
        sell_conditions_met["RSI Neutral"] = True
    else:
        sell_pending.append("RSI 45-55")

    if conditions["macd_sell"]:
        sell_score += 1
        sell_conditions_met["MACD"] = True
    else:
        sell_pending.append("MACD bearish")

    if conditions["adx_strong"]:
        sell_score += 1
        sell_conditions_met["ADX Strong"] = True
    else:
        sell_pending.append("ADX > 20")

    if conditions["structure_sell"]:
        sell_score += 1
        sell_conditions_met["Structure"] = True
    else:
        sell_pending.append("Bearish structure")

    if conditions["near_resistance"]:
        sell_score += 1
        sell_conditions_met["Near Resistance"] = True

    if conditions["liquidity_safe"]:
        sell_score += 1
        sell_conditions_met["Liquidity Safe"] = True

    # Determine direction and check threshold
    max_score = 8
    min_pre_signal_pct = 0.65  # 65% for pre-signal

    # Check for Boom/Crash restrictions
    is_boom = "BOOM" in pair.upper()
    is_crash = "CRASH" in pair.upper()

    direction = None
    score = 0
    conditions_met = {}
    pending = []

    if buy_score >= sell_score and buy_score >= int(max_score * min_pre_signal_pct):
        if not is_crash:
            direction = "BUY"
            score = buy_score
            conditions_met = buy_conditions_met
            pending = buy_pending[:3]  # Top 3 pending conditions
    elif sell_score > buy_score and sell_score >= int(max_score * min_pre_signal_pct):
        if not is_boom:
            direction = "SELL"
            score = sell_score
            conditions_met = sell_conditions_met
            pending = sell_pending[:3]

    if direction is None:
        return None

    # Calculate potential levels
    atr_sl = instrument_config.get("atr_multiplier_sl", 1.5)
    atr_tp1 = instrument_config.get("atr_multiplier_tp1", 1.5)
    atr_tp2 = instrument_config.get("atr_multiplier_tp2", 2.5)

    if direction == "BUY":
        potential_sl = close - (atr * atr_sl)
        potential_tp1 = close + (atr * atr_tp1)
        potential_tp2 = close + (atr * atr_tp2)
    else:
        potential_sl = close + (atr * atr_sl)
        potential_tp1 = close - (atr * atr_tp1)
        potential_tp2 = close - (atr * atr_tp2)

    confluence_pct = (score / max_score) * 100

    return PreSignalResult(
        pair=pair,
        display_name=instrument_config.get("display_name", pair),
        direction=direction,
        current_score=score,
        max_score=max_score,
        confluence_pct=confluence_pct,
        potential_entry=close,
        potential_sl=potential_sl,
        potential_tp1=potential_tp1,
        potential_tp2=potential_tp2,
        rsi=rsi,
        adx=adx,
        conditions_met=conditions_met,
        conditions_pending=pending
    )


# Add pre_analyze as a method to SignalEngine
SignalEngine.pre_analyze = pre_analyze


# Test if run directly
if __name__ == "__main__":
    import numpy as np

    # Create sample trending data
    np.random.seed(42)
    n = 300
    trend = np.linspace(0, 30, n) + np.cumsum(np.random.randn(n) * 0.5)
    close = 100 + trend
    high = close + np.abs(np.random.randn(n)) * 2
    low = close - np.abs(np.random.randn(n)) * 2
    open_price = close + np.random.randn(n)

    df = pd.DataFrame({
        "open": open_price,
        "high": high,
        "low": low,
        "close": close
    })

    engine = SignalEngine()

    test_config = {
        "display_name": "TEST/USD",
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 2.5,
        "use_session_filter": False
    }

    result = engine.analyze(df, "TEST_USD", test_config)

    if result:
        print(f"\n{'='*60}")
        print(f"SIGNAL ANALYSIS RESULT")
        print(f"{'='*60}")
        print(f"\nSignal: {result.direction} {result.display_name}")
        print(f"Score: {result.score}/{result.max_score} ({result.grade})")
        print(f"\nEntry: {result.entry:.2f}")
        print(f"Stop Loss: {result.stop_loss:.2f}")
        print(f"TP1: {result.tp1:.2f} (1:1 RR)")
        print(f"TP2: {result.tp2:.2f} (1:1.7 RR)")
        print(f"TP3: {result.tp3:.2f} (1:2.5 RR)")
        print(f"\nIndicators:")
        print(f"  RSI: {result.rsi:.2f}")
        print(f"  ADX: {result.adx:.2f}")
        print(f"  MACD: {result.macd_state}")
        print(f"\nSMC Analysis:")
        if result.smc_analysis:
            print(f"  Market Structure: {result.smc_analysis.trend.value.upper()}")
            print(f"  Break of Structure: {'Yes' if result.smc_analysis.bos_detected else 'No'}")
            print(f"  Change of Character: {'Yes' if result.smc_analysis.choch_detected else 'No'}")
        print(f"\nConfluence Checklist:")
        for key, value in result.checklist.items():
            status = "Yes" if value else "No"
            print(f"  {key}: {status}")
    else:
        print("No signal generated (conditions not met)")
