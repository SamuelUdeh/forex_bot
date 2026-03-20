"""
Candlestick Pattern Detection Module
=====================================
Detects key reversal and continuation patterns
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum


class PatternType(Enum):
    """Types of candlestick patterns"""
    # Bullish Reversal
    BULLISH_ENGULFING = "bullish_engulfing"
    HAMMER = "hammer"
    INVERTED_HAMMER = "inverted_hammer"
    MORNING_STAR = "morning_star"
    BULLISH_DOJI = "bullish_doji"
    THREE_WHITE_SOLDIERS = "three_white_soldiers"
    PIERCING_LINE = "piercing_line"
    TWEEZER_BOTTOM = "tweezer_bottom"
    TOWER_BOTTOM = "tower_bottom"
    BULLISH_HARAMI = "bullish_harami"
    DRAGONFLY_DOJI = "dragonfly_doji"

    # Bearish Reversal
    BEARISH_ENGULFING = "bearish_engulfing"
    SHOOTING_STAR = "shooting_star"
    HANGING_MAN = "hanging_man"
    EVENING_STAR = "evening_star"
    BEARISH_DOJI = "bearish_doji"
    THREE_BLACK_CROWS = "three_black_crows"
    DARK_CLOUD_COVER = "dark_cloud_cover"
    TWEEZER_TOP = "tweezer_top"
    TOWER_TOP = "tower_top"
    UPSIDE_GAP_TWO_CROWS = "upside_gap_two_crows"
    BEARISH_HARAMI = "bearish_harami"
    GRAVESTONE_DOJI = "gravestone_doji"

    # Continuation
    RISING_THREE = "rising_three"
    FALLING_THREE = "falling_three"


@dataclass
class CandlePattern:
    """Represents a detected candlestick pattern"""
    pattern_type: PatternType
    index: int
    direction: str  # "BUY" or "SELL"
    strength: int   # 1-3 (1=weak, 2=moderate, 3=strong)
    name: str


class CandlestickAnalyzer:
    """Analyzes candlestick patterns for trading signals"""

    def __init__(self, body_threshold: float = 0.1, doji_threshold: float = 0.05):
        """
        Args:
            body_threshold: Min body size as % of range for regular candles
            doji_threshold: Max body size as % of range for doji detection
        """
        self.body_threshold = body_threshold
        self.doji_threshold = doji_threshold

    def _get_candle_properties(self, row: pd.Series) -> dict:
        """Calculate candle properties"""
        open_price = row['open']
        high = row['high']
        low = row['low']
        close = row['close']

        body = abs(close - open_price)
        range_size = high - low

        if range_size == 0:
            range_size = 0.0001  # Prevent division by zero

        body_percent = body / range_size

        is_bullish = close > open_price
        is_bearish = close < open_price

        upper_wick = high - max(open_price, close)
        lower_wick = min(open_price, close) - low

        return {
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'body': body,
            'range': range_size,
            'body_percent': body_percent,
            'is_bullish': is_bullish,
            'is_bearish': is_bearish,
            'upper_wick': upper_wick,
            'lower_wick': lower_wick,
            'upper_wick_percent': upper_wick / range_size,
            'lower_wick_percent': lower_wick / range_size,
        }

    def _is_doji(self, props: dict) -> bool:
        """Check if candle is a doji (very small body)"""
        return props['body_percent'] < self.doji_threshold

    def _is_hammer(self, props: dict) -> bool:
        """
        Hammer: Small body at top, long lower wick (2x body), small upper wick
        Bullish reversal at bottom of downtrend
        """
        if props['body_percent'] < 0.1:
            return False

        return (
            props['lower_wick'] >= 2 * props['body'] and
            props['upper_wick'] <= props['body'] * 0.5 and
            props['body_percent'] < 0.4
        )

    def _is_inverted_hammer(self, props: dict) -> bool:
        """
        Inverted Hammer: Small body at bottom, long upper wick, small lower wick
        Bullish reversal at bottom of downtrend
        """
        if props['body_percent'] < 0.1:
            return False

        return (
            props['upper_wick'] >= 2 * props['body'] and
            props['lower_wick'] <= props['body'] * 0.5 and
            props['body_percent'] < 0.4
        )

    def _is_shooting_star(self, props: dict) -> bool:
        """
        Shooting Star: Small body at bottom, long upper wick, small lower wick
        Bearish reversal at top of uptrend (same shape as inverted hammer)
        """
        return self._is_inverted_hammer(props)

    def _is_hanging_man(self, props: dict) -> bool:
        """
        Hanging Man: Same shape as hammer but at top of uptrend
        Bearish reversal
        """
        return self._is_hammer(props)

    def detect_engulfing(self, df: pd.DataFrame, idx: int) -> Optional[CandlePattern]:
        """Detect bullish or bearish engulfing pattern"""
        if idx < 1:
            return None

        prev = self._get_candle_properties(df.iloc[idx - 1])
        curr = self._get_candle_properties(df.iloc[idx])

        # Bullish Engulfing: Previous bearish, current bullish body engulfs previous
        if (prev['is_bearish'] and curr['is_bullish'] and
            curr['open'] <= prev['close'] and curr['close'] >= prev['open'] and
            curr['body'] > prev['body']):

            strength = 3 if curr['body'] > prev['body'] * 1.5 else 2
            return CandlePattern(
                pattern_type=PatternType.BULLISH_ENGULFING,
                index=idx,
                direction="BUY",
                strength=strength,
                name="Bullish Engulfing"
            )

        # Bearish Engulfing: Previous bullish, current bearish body engulfs previous
        if (prev['is_bullish'] and curr['is_bearish'] and
            curr['open'] >= prev['close'] and curr['close'] <= prev['open'] and
            curr['body'] > prev['body']):

            strength = 3 if curr['body'] > prev['body'] * 1.5 else 2
            return CandlePattern(
                pattern_type=PatternType.BEARISH_ENGULFING,
                index=idx,
                direction="SELL",
                strength=strength,
                name="Bearish Engulfing"
            )

        return None

    def detect_hammer_patterns(self, df: pd.DataFrame, idx: int, trend: str) -> Optional[CandlePattern]:
        """Detect hammer, inverted hammer, shooting star, hanging man"""
        if idx < 1:
            return None

        curr = self._get_candle_properties(df.iloc[idx])

        # Hammer at bottom of downtrend = Bullish
        if trend == "DOWN" and self._is_hammer(curr):
            return CandlePattern(
                pattern_type=PatternType.HAMMER,
                index=idx,
                direction="BUY",
                strength=2,
                name="Hammer"
            )

        # Inverted Hammer at bottom of downtrend = Bullish
        if trend == "DOWN" and self._is_inverted_hammer(curr):
            return CandlePattern(
                pattern_type=PatternType.INVERTED_HAMMER,
                index=idx,
                direction="BUY",
                strength=2,
                name="Inverted Hammer"
            )

        # Shooting Star at top of uptrend = Bearish
        if trend == "UP" and self._is_shooting_star(curr):
            return CandlePattern(
                pattern_type=PatternType.SHOOTING_STAR,
                index=idx,
                direction="SELL",
                strength=2,
                name="Shooting Star"
            )

        # Hanging Man at top of uptrend = Bearish
        if trend == "UP" and self._is_hanging_man(curr):
            return CandlePattern(
                pattern_type=PatternType.HANGING_MAN,
                index=idx,
                direction="SELL",
                strength=2,
                name="Hanging Man"
            )

        return None

    def detect_doji(self, df: pd.DataFrame, idx: int, trend: str) -> Optional[CandlePattern]:
        """Detect doji patterns (indecision, potential reversal)"""
        if idx < 1:
            return None

        curr = self._get_candle_properties(df.iloc[idx])

        if not self._is_doji(curr):
            return None

        # Doji at top of uptrend = potential bearish reversal
        if trend == "UP":
            return CandlePattern(
                pattern_type=PatternType.BEARISH_DOJI,
                index=idx,
                direction="SELL",
                strength=1,
                name="Doji (Bearish)"
            )

        # Doji at bottom of downtrend = potential bullish reversal
        if trend == "DOWN":
            return CandlePattern(
                pattern_type=PatternType.BULLISH_DOJI,
                index=idx,
                direction="BUY",
                strength=1,
                name="Doji (Bullish)"
            )

        return None

    def detect_morning_star(self, df: pd.DataFrame, idx: int) -> Optional[CandlePattern]:
        """
        Morning Star: 3-candle bullish reversal
        1. Large bearish candle
        2. Small body (doji or small candle) - gaps down
        3. Large bullish candle closing above midpoint of first
        """
        if idx < 2:
            return None

        first = self._get_candle_properties(df.iloc[idx - 2])
        second = self._get_candle_properties(df.iloc[idx - 1])
        third = self._get_candle_properties(df.iloc[idx])

        # First candle: large bearish
        if not (first['is_bearish'] and first['body_percent'] > 0.5):
            return None

        # Second candle: small body (star)
        if second['body_percent'] > 0.3:
            return None

        # Third candle: large bullish, closes above midpoint of first
        first_midpoint = (first['open'] + first['close']) / 2
        if not (third['is_bullish'] and third['body_percent'] > 0.5 and
                third['close'] > first_midpoint):
            return None

        strength = 3 if third['close'] > first['open'] else 2
        return CandlePattern(
            pattern_type=PatternType.MORNING_STAR,
            index=idx,
            direction="BUY",
            strength=strength,
            name="Morning Star"
        )

    def detect_evening_star(self, df: pd.DataFrame, idx: int) -> Optional[CandlePattern]:
        """
        Evening Star: 3-candle bearish reversal
        1. Large bullish candle
        2. Small body (doji or small candle) - gaps up
        3. Large bearish candle closing below midpoint of first
        """
        if idx < 2:
            return None

        first = self._get_candle_properties(df.iloc[idx - 2])
        second = self._get_candle_properties(df.iloc[idx - 1])
        third = self._get_candle_properties(df.iloc[idx])

        # First candle: large bullish
        if not (first['is_bullish'] and first['body_percent'] > 0.5):
            return None

        # Second candle: small body (star)
        if second['body_percent'] > 0.3:
            return None

        # Third candle: large bearish, closes below midpoint of first
        first_midpoint = (first['open'] + first['close']) / 2
        if not (third['is_bearish'] and third['body_percent'] > 0.5 and
                third['close'] < first_midpoint):
            return None

        strength = 3 if third['close'] < first['open'] else 2
        return CandlePattern(
            pattern_type=PatternType.EVENING_STAR,
            index=idx,
            direction="SELL",
            strength=strength,
            name="Evening Star"
        )

    def detect_three_white_soldiers(self, df: pd.DataFrame, idx: int) -> Optional[CandlePattern]:
        """
        Three White Soldiers: 3 consecutive bullish candles
        Each opens within previous body and closes higher
        """
        if idx < 2:
            return None

        candles = [self._get_candle_properties(df.iloc[idx - i]) for i in range(2, -1, -1)]

        # All three must be bullish with decent body
        for c in candles:
            if not (c['is_bullish'] and c['body_percent'] > 0.5):
                return None

        # Each opens within previous body and closes higher
        for i in range(1, 3):
            prev = candles[i - 1]
            curr = candles[i]

            # Opens within previous body
            if not (curr['open'] >= prev['open'] and curr['open'] <= prev['close']):
                return None

            # Closes higher
            if curr['close'] <= prev['close']:
                return None

        return CandlePattern(
            pattern_type=PatternType.THREE_WHITE_SOLDIERS,
            index=idx,
            direction="BUY",
            strength=3,
            name="Three White Soldiers"
        )

    def detect_three_black_crows(self, df: pd.DataFrame, idx: int) -> Optional[CandlePattern]:
        """
        Three Black Crows: 3 consecutive bearish candles
        Each opens within previous body and closes lower
        """
        if idx < 2:
            return None

        candles = [self._get_candle_properties(df.iloc[idx - i]) for i in range(2, -1, -1)]

        # All three must be bearish with decent body
        for c in candles:
            if not (c['is_bearish'] and c['body_percent'] > 0.5):
                return None

        # Each opens within previous body and closes lower
        for i in range(1, 3):
            prev = candles[i - 1]
            curr = candles[i]

            # Opens within previous body
            if not (curr['open'] <= prev['open'] and curr['open'] >= prev['close']):
                return None

            # Closes lower
            if curr['close'] >= prev['close']:
                return None

        return CandlePattern(
            pattern_type=PatternType.THREE_BLACK_CROWS,
            index=idx,
            direction="SELL",
            strength=3,
            name="Three Black Crows"
        )

    def detect_piercing_line(self, df: pd.DataFrame, idx: int) -> Optional[CandlePattern]:
        """
        Piercing Line: 2-candle bullish reversal
        1. Large bearish candle
        2. Bullish candle opening below low, closing above midpoint
        """
        if idx < 1:
            return None

        prev = self._get_candle_properties(df.iloc[idx - 1])
        curr = self._get_candle_properties(df.iloc[idx])

        if not (prev['is_bearish'] and prev['body_percent'] > 0.5):
            return None

        if not curr['is_bullish']:
            return None

        prev_midpoint = (prev['open'] + prev['close']) / 2

        if (curr['open'] < prev['low'] and
            curr['close'] > prev_midpoint and
            curr['close'] < prev['open']):
            return CandlePattern(
                pattern_type=PatternType.PIERCING_LINE,
                index=idx,
                direction="BUY",
                strength=2,
                name="Piercing Line"
            )

        return None

    def detect_dark_cloud_cover(self, df: pd.DataFrame, idx: int) -> Optional[CandlePattern]:
        """
        Dark Cloud Cover: 2-candle bearish reversal
        1. Large bullish candle
        2. Bearish candle opening above high, closing below midpoint
        """
        if idx < 1:
            return None

        prev = self._get_candle_properties(df.iloc[idx - 1])
        curr = self._get_candle_properties(df.iloc[idx])

        if not (prev['is_bullish'] and prev['body_percent'] > 0.5):
            return None

        if not curr['is_bearish']:
            return None

        prev_midpoint = (prev['open'] + prev['close']) / 2

        if (curr['open'] > prev['high'] and
            curr['close'] < prev_midpoint and
            curr['close'] > prev['open']):
            return CandlePattern(
                pattern_type=PatternType.DARK_CLOUD_COVER,
                index=idx,
                direction="SELL",
                strength=2,
                name="Dark Cloud Cover"
            )

        return None

    def detect_tweezer_top(self, df: pd.DataFrame, idx: int) -> Optional[CandlePattern]:
        """
        Tweezer Top: 2 candles with matching highs at resistance
        1. Bullish candle followed by bearish candle
        2. Both have same/similar high
        """
        if idx < 1:
            return None

        prev = self._get_candle_properties(df.iloc[idx - 1])
        curr = self._get_candle_properties(df.iloc[idx])

        # First bullish, second bearish
        if not (prev['is_bullish'] and curr['is_bearish']):
            return None

        # Highs within 0.1% of each other
        high_diff = abs(prev['high'] - curr['high']) / prev['high']
        if high_diff < 0.001:
            return CandlePattern(
                pattern_type=PatternType.TWEEZER_TOP,
                index=idx,
                direction="SELL",
                strength=2,
                name="Tweezer Top"
            )
        return None

    def detect_tweezer_bottom(self, df: pd.DataFrame, idx: int) -> Optional[CandlePattern]:
        """
        Tweezer Bottom: 2 candles with matching lows at support
        1. Bearish candle followed by bullish candle
        2. Both have same/similar low
        """
        if idx < 1:
            return None

        prev = self._get_candle_properties(df.iloc[idx - 1])
        curr = self._get_candle_properties(df.iloc[idx])

        # First bearish, second bullish
        if not (prev['is_bearish'] and curr['is_bullish']):
            return None

        # Lows within 0.1% of each other
        low_diff = abs(prev['low'] - curr['low']) / prev['low']
        if low_diff < 0.001:
            return CandlePattern(
                pattern_type=PatternType.TWEEZER_BOTTOM,
                index=idx,
                direction="BUY",
                strength=2,
                name="Tweezer Bottom"
            )
        return None

    def detect_tower_top(self, df: pd.DataFrame, idx: int) -> Optional[CandlePattern]:
        """
        Tower Top: Multiple bullish candles followed by multiple bearish
        Shows strong reversal from uptrend
        """
        if idx < 4:
            return None

        candles = [self._get_candle_properties(df.iloc[idx - i]) for i in range(4, -1, -1)]

        # First 2-3 bullish, last 2 bearish
        bullish_count = sum(1 for c in candles[:3] if c['is_bullish'])
        bearish_count = sum(1 for c in candles[3:] if c['is_bearish'])

        if bullish_count >= 2 and bearish_count == 2:
            # Last bearish candles should have decent body
            if candles[3]['body_percent'] > 0.4 and candles[4]['body_percent'] > 0.4:
                return CandlePattern(
                    pattern_type=PatternType.TOWER_TOP,
                    index=idx,
                    direction="SELL",
                    strength=3,
                    name="Tower Top"
                )
        return None

    def detect_tower_bottom(self, df: pd.DataFrame, idx: int) -> Optional[CandlePattern]:
        """
        Tower Bottom: Multiple bearish candles followed by multiple bullish
        Shows strong reversal from downtrend
        """
        if idx < 4:
            return None

        candles = [self._get_candle_properties(df.iloc[idx - i]) for i in range(4, -1, -1)]

        # First 2-3 bearish, last 2 bullish
        bearish_count = sum(1 for c in candles[:3] if c['is_bearish'])
        bullish_count = sum(1 for c in candles[3:] if c['is_bullish'])

        if bearish_count >= 2 and bullish_count == 2:
            # Last bullish candles should have decent body
            if candles[3]['body_percent'] > 0.4 and candles[4]['body_percent'] > 0.4:
                return CandlePattern(
                    pattern_type=PatternType.TOWER_BOTTOM,
                    index=idx,
                    direction="BUY",
                    strength=3,
                    name="Tower Bottom"
                )
        return None

    def detect_upside_gap_two_crows(self, df: pd.DataFrame, idx: int) -> Optional[CandlePattern]:
        """
        Upside Gap Two Crows: 3-candle bearish pattern
        1. Large bullish candle
        2. Small bearish candle gaps up
        3. Larger bearish candle engulfs #2 but stays above #1
        """
        if idx < 2:
            return None

        first = self._get_candle_properties(df.iloc[idx - 2])
        second = self._get_candle_properties(df.iloc[idx - 1])
        third = self._get_candle_properties(df.iloc[idx])

        # First large bullish
        if not (first['is_bullish'] and first['body_percent'] > 0.5):
            return None

        # Second small bearish, gaps up from first
        if not second['is_bearish']:
            return None
        if second['open'] <= first['close']:  # Should gap up
            return None

        # Third bearish, engulfs second but closes above first's close
        if not third['is_bearish']:
            return None
        if not (third['open'] > second['close'] and third['close'] < second['open']):
            return None
        if third['close'] <= first['close']:  # Should stay above first
            return None

        return CandlePattern(
            pattern_type=PatternType.UPSIDE_GAP_TWO_CROWS,
            index=idx,
            direction="SELL",
            strength=2,
            name="Upside Gap Two Crows"
        )

    def detect_harami(self, df: pd.DataFrame, idx: int) -> Optional[CandlePattern]:
        """
        Harami: Small candle contained within previous large candle
        Bullish Harami: Large bearish followed by small bullish inside
        Bearish Harami: Large bullish followed by small bearish inside
        """
        if idx < 1:
            return None

        prev = self._get_candle_properties(df.iloc[idx - 1])
        curr = self._get_candle_properties(df.iloc[idx])

        # Previous should be large
        if prev['body_percent'] < 0.5:
            return None

        # Current should be small and contained within previous
        if curr['body_percent'] > 0.4:
            return None

        # Bullish Harami
        if prev['is_bearish'] and curr['is_bullish']:
            if curr['close'] < prev['open'] and curr['open'] > prev['close']:
                return CandlePattern(
                    pattern_type=PatternType.BULLISH_HARAMI,
                    index=idx,
                    direction="BUY",
                    strength=1,
                    name="Bullish Harami"
                )

        # Bearish Harami
        if prev['is_bullish'] and curr['is_bearish']:
            if curr['open'] < prev['close'] and curr['close'] > prev['open']:
                return CandlePattern(
                    pattern_type=PatternType.BEARISH_HARAMI,
                    index=idx,
                    direction="SELL",
                    strength=1,
                    name="Bearish Harami"
                )

        return None

    def detect_dragonfly_doji(self, df: pd.DataFrame, idx: int, trend: str) -> Optional[CandlePattern]:
        """
        Dragonfly Doji: Doji with long lower wick, no upper wick
        Bullish reversal at bottom of downtrend
        """
        curr = self._get_candle_properties(df.iloc[idx])

        if not self._is_doji(curr):
            return None

        # Long lower wick, tiny upper wick
        if (curr['lower_wick_percent'] > 0.6 and
            curr['upper_wick_percent'] < 0.1):
            if trend == "DOWN":
                return CandlePattern(
                    pattern_type=PatternType.DRAGONFLY_DOJI,
                    index=idx,
                    direction="BUY",
                    strength=2,
                    name="Dragonfly Doji"
                )
        return None

    def detect_gravestone_doji(self, df: pd.DataFrame, idx: int, trend: str) -> Optional[CandlePattern]:
        """
        Gravestone Doji: Doji with long upper wick, no lower wick
        Bearish reversal at top of uptrend
        """
        curr = self._get_candle_properties(df.iloc[idx])

        if not self._is_doji(curr):
            return None

        # Long upper wick, tiny lower wick
        if (curr['upper_wick_percent'] > 0.6 and
            curr['lower_wick_percent'] < 0.1):
            if trend == "UP":
                return CandlePattern(
                    pattern_type=PatternType.GRAVESTONE_DOJI,
                    index=idx,
                    direction="SELL",
                    strength=2,
                    name="Gravestone Doji"
                )
        return None

    def detect_rising_three(self, df: pd.DataFrame, idx: int) -> Optional[CandlePattern]:
        """
        Rising Three Methods: Bullish continuation
        1. Large bullish
        2-4. Three small bearish candles staying within first candle
        5. Large bullish closing above first
        """
        if idx < 4:
            return None

        candles = [self._get_candle_properties(df.iloc[idx - i]) for i in range(4, -1, -1)]

        # First and last bullish
        if not (candles[0]['is_bullish'] and candles[4]['is_bullish']):
            return None

        # First should be large
        if candles[0]['body_percent'] < 0.5:
            return None

        # Middle three should be small and bearish (or mixed small)
        for i in range(1, 4):
            if candles[i]['body_percent'] > 0.4:
                return None
            # Should stay within first candle's range
            if candles[i]['high'] > candles[0]['high']:
                return None
            if candles[i]['low'] < candles[0]['low']:
                return None

        # Last should close above first's close
        if candles[4]['close'] > candles[0]['close']:
            return CandlePattern(
                pattern_type=PatternType.RISING_THREE,
                index=idx,
                direction="BUY",
                strength=2,
                name="Rising Three Methods"
            )
        return None

    def detect_falling_three(self, df: pd.DataFrame, idx: int) -> Optional[CandlePattern]:
        """
        Falling Three Methods: Bearish continuation
        1. Large bearish
        2-4. Three small bullish candles staying within first candle
        5. Large bearish closing below first
        """
        if idx < 4:
            return None

        candles = [self._get_candle_properties(df.iloc[idx - i]) for i in range(4, -1, -1)]

        # First and last bearish
        if not (candles[0]['is_bearish'] and candles[4]['is_bearish']):
            return None

        # First should be large
        if candles[0]['body_percent'] < 0.5:
            return None

        # Middle three should be small
        for i in range(1, 4):
            if candles[i]['body_percent'] > 0.4:
                return None
            # Should stay within first candle's range
            if candles[i]['high'] > candles[0]['high']:
                return None
            if candles[i]['low'] < candles[0]['low']:
                return None

        # Last should close below first's close
        if candles[4]['close'] < candles[0]['close']:
            return CandlePattern(
                pattern_type=PatternType.FALLING_THREE,
                index=idx,
                direction="SELL",
                strength=2,
                name="Falling Three Methods"
            )
        return None

    def get_short_term_trend(self, df: pd.DataFrame, idx: int, lookback: int = 5) -> str:
        """Determine short-term trend for context"""
        if idx < lookback:
            return "NEUTRAL"

        closes = df['close'].iloc[idx - lookback:idx].values

        # Simple trend: compare first half avg to second half avg
        mid = lookback // 2
        first_half = np.mean(closes[:mid])
        second_half = np.mean(closes[mid:])

        diff_percent = (second_half - first_half) / first_half * 100

        if diff_percent > 0.5:
            return "UP"
        elif diff_percent < -0.5:
            return "DOWN"
        return "NEUTRAL"

    def analyze(self, df: pd.DataFrame, idx: int = -1) -> List[CandlePattern]:
        """
        Analyze candlestick patterns at the given index

        Args:
            df: DataFrame with OHLC data
            idx: Index to analyze (default: last candle)

        Returns:
            List of detected patterns
        """
        if idx == -1:
            idx = len(df) - 1

        if idx < 2:
            return []

        patterns = []
        trend = self.get_short_term_trend(df, idx)

        # Check all pattern types
        pattern_checks = [
            # Basic patterns
            self.detect_engulfing(df, idx),
            self.detect_hammer_patterns(df, idx, trend),
            self.detect_doji(df, idx, trend),
            # 3-candle patterns
            self.detect_morning_star(df, idx),
            self.detect_evening_star(df, idx),
            self.detect_three_white_soldiers(df, idx),
            self.detect_three_black_crows(df, idx),
            # 2-candle patterns
            self.detect_piercing_line(df, idx),
            self.detect_dark_cloud_cover(df, idx),
            self.detect_tweezer_top(df, idx),
            self.detect_tweezer_bottom(df, idx),
            self.detect_harami(df, idx),
            # Multi-candle patterns
            self.detect_tower_top(df, idx),
            self.detect_tower_bottom(df, idx),
            self.detect_upside_gap_two_crows(df, idx),
            # Doji variations
            self.detect_dragonfly_doji(df, idx, trend),
            self.detect_gravestone_doji(df, idx, trend),
            # Continuation patterns
            self.detect_rising_three(df, idx),
            self.detect_falling_three(df, idx),
        ]

        for pattern in pattern_checks:
            if pattern is not None:
                patterns.append(pattern)

        return patterns

    def get_pattern_score(self, patterns: List[CandlePattern], direction: str) -> Tuple[int, List[str]]:
        """
        Calculate pattern score for confluence system

        Args:
            patterns: List of detected patterns
            direction: "BUY" or "SELL"

        Returns:
            Tuple of (score, list of pattern names)
        """
        score = 0
        pattern_names = []

        for pattern in patterns:
            if pattern.direction == direction:
                # Strong patterns (3-candle or strong engulfing) = +2
                # Moderate patterns = +1
                if pattern.strength >= 3:
                    score += 2
                else:
                    score += 1
                pattern_names.append(pattern.name)

        # Cap at 2 points max for candlestick patterns
        score = min(score, 2)

        return score, pattern_names
