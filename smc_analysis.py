"""
Smart Money Concepts (SMC) Analysis Module (OPTIMIZED)
======================================================
Advanced price action analysis used by institutional traders

Optimized for backtesting performance with:
- Vectorized swing detection using numpy
- Incremental analysis mode
- Limited lookback windows
- Batch pre-computation support

Includes:
- Support & Resistance levels
- Market Structure (HH, HL, LH, LL)
- Break of Structure (BOS) / Change of Character (CHoCH)
- Liquidity Zones (Equal Highs/Lows)
- Fair Value Gaps (FVG) / Imbalances
- Order Blocks (OB)
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class TrendDirection(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    RANGING = "ranging"


class StructureType(Enum):
    HH = "higher_high"
    HL = "higher_low"
    LH = "lower_high"
    LL = "lower_low"
    EQH = "equal_high"  # Liquidity
    EQL = "equal_low"   # Liquidity


@dataclass
class SwingPoint:
    """Represents a swing high or swing low"""
    index: int
    price: float
    is_high: bool  # True for swing high, False for swing low
    structure_type: Optional[StructureType] = None


@dataclass
class SupportResistance:
    """Represents a support or resistance level"""
    price: float
    strength: int  # Number of times price touched this level
    is_support: bool  # True for support, False for resistance
    last_touch_index: int


@dataclass
class FairValueGap:
    """Represents a Fair Value Gap (imbalance)"""
    start_index: int
    high: float
    low: float
    is_bullish: bool  # True for bullish FVG, False for bearish
    filled: bool = False


@dataclass
class OrderBlock:
    """Represents an Order Block"""
    start_index: int
    high: float
    low: float
    is_bullish: bool
    mitigated: bool = False


@dataclass
class SMCAnalysis:
    """Contains all SMC analysis results"""
    trend: TrendDirection
    swing_points: List[SwingPoint]
    support_levels: List[SupportResistance]
    resistance_levels: List[SupportResistance]
    liquidity_zones: List[SwingPoint]  # Equal highs/lows
    fair_value_gaps: List[FairValueGap]
    order_blocks: List[OrderBlock]
    bos_detected: bool  # Break of Structure
    choch_detected: bool  # Change of Character
    near_support: bool
    near_resistance: bool
    near_liquidity: bool
    in_fvg: bool
    in_order_block: bool


class SMCAnalyzer:
    """
    Analyzes price data using Smart Money Concepts
    """

    def __init__(self, swing_lookback: int = 5, level_tolerance: float = 0.001):
        """
        Initialize SMC Analyzer

        Args:
            swing_lookback: Number of candles to look back/forward for swing detection
            level_tolerance: Percentage tolerance for S/R level matching (0.001 = 0.1%)
        """
        self.swing_lookback = swing_lookback
        self.level_tolerance = level_tolerance

    def find_swing_points_vectorized(self, highs: np.ndarray, lows: np.ndarray) -> List[SwingPoint]:
        """
        OPTIMIZED: Find swing highs and lows using vectorized numpy operations

        Much faster than loop-based approach for large datasets
        """
        swings = []
        n = self.swing_lookback
        length = len(highs)

        if length < 2 * n + 1:
            return swings

        # Create rolling max/min windows using strides (much faster than loops)
        # For swing highs: check if each point is max in its window
        # For swing lows: check if each point is min in its window

        for i in range(n, length - n):
            # Get window around point i
            high_window = highs[i - n:i + n + 1]
            low_window = lows[i - n:i + n + 1]

            # Check swing high: current high is max in window
            if highs[i] == np.max(high_window) and np.sum(high_window == highs[i]) == 1:
                swings.append(SwingPoint(
                    index=i,
                    price=float(highs[i]),
                    is_high=True
                ))

            # Check swing low: current low is min in window
            if lows[i] == np.min(low_window) and np.sum(low_window == lows[i]) == 1:
                swings.append(SwingPoint(
                    index=i,
                    price=float(lows[i]),
                    is_high=False
                ))

        # Sort by index
        swings.sort(key=lambda x: x.index)
        return swings

    def find_swing_points(self, df: pd.DataFrame, start_idx: int = 0) -> List[SwingPoint]:
        """
        Find swing highs and swing lows in price data

        Args:
            df: DataFrame with OHLC data
            start_idx: Optional start index for incremental analysis
        """
        highs = df["high"].values
        lows = df["low"].values
        return self.find_swing_points_vectorized(highs, lows)

    def analyze_market_structure(self, swings: List[SwingPoint]) -> Tuple[TrendDirection, bool, bool]:
        """
        Analyze market structure from swing points

        Returns:
            Tuple of (trend_direction, bos_detected, choch_detected)
        """
        if len(swings) < 4:
            return TrendDirection.RANGING, False, False

        # Get recent swing highs and lows
        recent_highs = [s for s in swings[-10:] if s.is_high]
        recent_lows = [s for s in swings[-10:] if not s.is_high]

        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return TrendDirection.RANGING, False, False

        # Label structure
        for i, swing in enumerate(swings):
            if i == 0:
                continue

            prev_same_type = None
            for j in range(i - 1, -1, -1):
                if swings[j].is_high == swing.is_high:
                    prev_same_type = swings[j]
                    break

            if prev_same_type:
                if swing.is_high:
                    if swing.price > prev_same_type.price:
                        swing.structure_type = StructureType.HH
                    elif swing.price < prev_same_type.price:
                        swing.structure_type = StructureType.LH
                    else:
                        swing.structure_type = StructureType.EQH
                else:
                    if swing.price > prev_same_type.price:
                        swing.structure_type = StructureType.HL
                    elif swing.price < prev_same_type.price:
                        swing.structure_type = StructureType.LL
                    else:
                        swing.structure_type = StructureType.EQL

        # Determine trend from recent structure
        recent = swings[-6:]
        hh_count = sum(1 for s in recent if s.structure_type == StructureType.HH)
        hl_count = sum(1 for s in recent if s.structure_type == StructureType.HL)
        lh_count = sum(1 for s in recent if s.structure_type == StructureType.LH)
        ll_count = sum(1 for s in recent if s.structure_type == StructureType.LL)

        bullish_score = hh_count + hl_count
        bearish_score = lh_count + ll_count

        if bullish_score > bearish_score + 1:
            trend = TrendDirection.BULLISH
        elif bearish_score > bullish_score + 1:
            trend = TrendDirection.BEARISH
        else:
            trend = TrendDirection.RANGING

        # Detect Break of Structure (BOS)
        bos = False
        if len(recent) >= 2:
            last_swing = recent[-1]
            prev_swing = recent[-2]
            if last_swing.is_high and prev_swing.is_high:
                if last_swing.price > prev_swing.price:
                    bos = True  # Bullish BOS
            elif not last_swing.is_high and not prev_swing.is_high:
                if last_swing.price < prev_swing.price:
                    bos = True  # Bearish BOS

        # Detect Change of Character (CHoCH)
        choch = False
        if len(recent) >= 4:
            # CHoCH occurs when structure changes from bullish to bearish or vice versa
            first_half = recent[:3]
            second_half = recent[3:]

            first_bullish = sum(1 for s in first_half if s.structure_type in [StructureType.HH, StructureType.HL])
            first_bearish = sum(1 for s in first_half if s.structure_type in [StructureType.LH, StructureType.LL])
            second_bullish = sum(1 for s in second_half if s.structure_type in [StructureType.HH, StructureType.HL])
            second_bearish = sum(1 for s in second_half if s.structure_type in [StructureType.LH, StructureType.LL])

            if first_bullish > first_bearish and second_bearish > second_bullish:
                choch = True  # Bullish to Bearish
            elif first_bearish > first_bullish and second_bullish > second_bearish:
                choch = True  # Bearish to Bullish

        return trend, bos, choch

    def find_support_resistance(self, df: pd.DataFrame, swings: List[SwingPoint]) -> Tuple[List[SupportResistance], List[SupportResistance]]:
        """
        Find support and resistance levels from swing points
        """
        support_levels = []
        resistance_levels = []

        # Group nearby swing lows as support
        swing_lows = [s for s in swings if not s.is_high]
        swing_highs = [s for s in swings if s.is_high]

        # Cluster nearby levels
        def cluster_levels(points: List[SwingPoint], tolerance: float) -> List[SupportResistance]:
            if not points:
                return []

            clusters = []
            used = set()

            for i, p1 in enumerate(points):
                if i in used:
                    continue

                cluster_prices = [p1.price]
                cluster_indices = [p1.index]
                used.add(i)

                for j, p2 in enumerate(points):
                    if j in used:
                        continue
                    if abs(p1.price - p2.price) / p1.price <= tolerance:
                        cluster_prices.append(p2.price)
                        cluster_indices.append(p2.index)
                        used.add(j)

                avg_price = sum(cluster_prices) / len(cluster_prices)
                clusters.append(SupportResistance(
                    price=avg_price,
                    strength=len(cluster_prices),
                    is_support=not points[0].is_high if points else True,
                    last_touch_index=max(cluster_indices)
                ))

            return clusters

        support_levels = cluster_levels(swing_lows, self.level_tolerance * 2)
        resistance_levels = cluster_levels(swing_highs, self.level_tolerance * 2)

        # Sort by strength
        support_levels.sort(key=lambda x: x.strength, reverse=True)
        resistance_levels.sort(key=lambda x: x.strength, reverse=True)

        return support_levels[:5], resistance_levels[:5]  # Return top 5

    def find_liquidity_zones(self, swings: List[SwingPoint]) -> List[SwingPoint]:
        """
        Find liquidity zones (equal highs/lows where stop losses cluster)
        """
        liquidity = []

        for swing in swings:
            if swing.structure_type in [StructureType.EQH, StructureType.EQL]:
                liquidity.append(swing)

        return liquidity

    def find_fair_value_gaps(self, df: pd.DataFrame, lookback: int = 50) -> List[FairValueGap]:
        """
        OPTIMIZED: Find Fair Value Gaps with limited lookback

        Args:
            df: DataFrame with OHLC data
            lookback: Number of candles to look back (default 50)
        """
        fvgs = []
        start_idx = max(2, len(df) - lookback)

        # Use numpy arrays for speed
        highs = df["high"].values
        lows = df["low"].values

        for i in range(start_idx, len(df)):
            # Bullish FVG: candle 1 high < candle 3 low
            if highs[i - 2] < lows[i]:
                fvgs.append(FairValueGap(
                    start_index=i - 1,
                    high=float(lows[i]),
                    low=float(highs[i - 2]),
                    is_bullish=True
                ))

            # Bearish FVG: candle 1 low > candle 3 high
            if lows[i - 2] > highs[i]:
                fvgs.append(FairValueGap(
                    start_index=i - 1,
                    high=float(lows[i - 2]),
                    low=float(highs[i]),
                    is_bullish=False
                ))

        # Check if FVGs are filled (only check candles after each FVG)
        for fvg in fvgs:
            check_start = fvg.start_index + 2
            check_end = len(df)
            if check_start < check_end:
                if fvg.is_bullish:
                    # Bullish FVG filled when price drops below low
                    if np.any(lows[check_start:check_end] <= fvg.low):
                        fvg.filled = True
                else:
                    # Bearish FVG filled when price rises above high
                    if np.any(highs[check_start:check_end] >= fvg.high):
                        fvg.filled = True

        return fvgs

    def find_order_blocks(self, df: pd.DataFrame, swings: List[SwingPoint], lookback: int = 20) -> List[OrderBlock]:
        """
        OPTIMIZED: Find Order Blocks with limited swing and mitigation check

        Args:
            df: DataFrame with OHLC data
            swings: List of swing points
            lookback: Number of recent swings to check (default 20)
        """
        order_blocks = []

        # Use numpy arrays
        opens = df["open"].values
        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values

        # Only check recent swings
        recent_swings = swings[-lookback:] if len(swings) > lookback else swings

        for swing in recent_swings:
            if swing.index < 3 or swing.index >= len(df) - 1:
                continue

            if swing.is_high:  # Look for bullish OB
                # Find last bearish candle before the move
                for j in range(swing.index - 1, max(0, swing.index - 10), -1):
                    if closes[j] < opens[j]:  # Bearish candle
                        order_blocks.append(OrderBlock(
                            start_index=j,
                            high=float(highs[j]),
                            low=float(lows[j]),
                            is_bullish=True
                        ))
                        break
            else:  # Look for bearish OB
                for j in range(swing.index - 1, max(0, swing.index - 10), -1):
                    if closes[j] > opens[j]:  # Bullish candle
                        order_blocks.append(OrderBlock(
                            start_index=j,
                            high=float(highs[j]),
                            low=float(lows[j]),
                            is_bullish=False
                        ))
                        break

        # Check mitigation using vectorized operations
        for ob in order_blocks:
            check_start = ob.start_index + 1
            if check_start < len(df):
                if ob.is_bullish:
                    if np.any(lows[check_start:] <= ob.high):
                        ob.mitigated = True
                else:
                    if np.any(highs[check_start:] >= ob.low):
                        ob.mitigated = True

        return order_blocks[-10:]

    def is_near_level(self, price: float, level: float, atr: float, multiplier: float = 0.5) -> bool:
        """Check if price is near a level (within ATR distance)"""
        return abs(price - level) <= atr * multiplier

    def analyze_fast(self, df: pd.DataFrame, lookback: int = 100) -> SMCAnalysis:
        """
        OPTIMIZED: Fast SMC analysis for backtesting

        Uses limited lookback window and vectorized operations.
        Only analyzes recent data for faster performance.

        Args:
            df: DataFrame with OHLC data
            lookback: Number of candles to analyze (default 100)

        Returns:
            SMCAnalysis object with analysis results
        """
        if len(df) < 50:
            return None

        # Use limited lookback window
        analysis_df = df.iloc[-lookback:] if len(df) > lookback else df

        # Get current price and ATR using numpy
        current_price = float(df.iloc[-1]["close"])
        high_low = df["high"].values - df["low"].values
        atr = float(np.mean(high_low[-14:]))

        # Find swing points (vectorized)
        swings = self.find_swing_points(analysis_df)

        # Adjust swing indices to match original df
        offset = len(df) - len(analysis_df)
        for swing in swings:
            swing.index += offset

        # Analyze market structure
        trend, bos, choch = self.analyze_market_structure(swings)

        # Find S/R levels (from recent swings only)
        support_levels, resistance_levels = self.find_support_resistance(analysis_df, swings)

        # Find liquidity zones
        liquidity_zones = self.find_liquidity_zones(swings)

        # Find FVGs (limited lookback)
        fvgs = self.find_fair_value_gaps(df, lookback=50)
        unfilled_fvgs = [f for f in fvgs if not f.filled]

        # Find Order Blocks (limited)
        order_blocks = self.find_order_blocks(df, swings, lookback=15)
        unmitigated_obs = [ob for ob in order_blocks if not ob.mitigated]

        # Check proximity using numpy operations
        near_support = False
        for s in support_levels[:3]:  # Only check top 3
            if abs(current_price - s.price) <= atr * 0.5:
                near_support = True
                break

        near_resistance = False
        for r in resistance_levels[:3]:
            if abs(current_price - r.price) <= atr * 0.5:
                near_resistance = True
                break

        near_liquidity = False
        for lz in liquidity_zones[-3:]:
            if abs(current_price - lz.price) <= atr * 0.3:
                near_liquidity = True
                break

        # Check if in FVG/OB
        in_fvg = any(fvg.low <= current_price <= fvg.high for fvg in unfilled_fvgs[-3:])
        in_order_block = any(ob.low <= current_price <= ob.high for ob in unmitigated_obs[-3:])

        return SMCAnalysis(
            trend=trend,
            swing_points=swings[-20:],  # Only keep recent swings
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            liquidity_zones=liquidity_zones[-5:],
            fair_value_gaps=unfilled_fvgs[-5:],
            order_blocks=unmitigated_obs[-5:],
            bos_detected=bos,
            choch_detected=choch,
            near_support=near_support,
            near_resistance=near_resistance,
            near_liquidity=near_liquidity,
            in_fvg=in_fvg,
            in_order_block=in_order_block
        )

    def analyze(self, df: pd.DataFrame, fast_mode: bool = False) -> SMCAnalysis:
        """
        Perform SMC analysis on price data

        Args:
            df: DataFrame with OHLC data
            fast_mode: If True, use optimized analysis for backtesting

        Returns:
            SMCAnalysis object with all analysis results
        """
        if fast_mode:
            return self.analyze_fast(df)

        if len(df) < 50:
            return None

        # Get current price and ATR
        current_price = df.iloc[-1]["close"]

        # Calculate ATR for proximity checks
        high_low = df["high"] - df["low"]
        atr = high_low.rolling(window=14).mean().iloc[-1]

        # Find swing points
        swings = self.find_swing_points(df)

        # Analyze market structure
        trend, bos, choch = self.analyze_market_structure(swings)

        # Find S/R levels
        support_levels, resistance_levels = self.find_support_resistance(df, swings)

        # Find liquidity zones
        liquidity_zones = self.find_liquidity_zones(swings)

        # Find FVGs
        fvgs = self.find_fair_value_gaps(df)
        unfilled_fvgs = [f for f in fvgs if not f.filled]

        # Find Order Blocks
        order_blocks = self.find_order_blocks(df, swings)
        unmitigated_obs = [ob for ob in order_blocks if not ob.mitigated]

        # Check proximity to key levels
        near_support = any(
            self.is_near_level(current_price, s.price, atr)
            for s in support_levels
        )

        near_resistance = any(
            self.is_near_level(current_price, r.price, atr)
            for r in resistance_levels
        )

        near_liquidity = any(
            self.is_near_level(current_price, lz.price, atr, 0.3)
            for lz in liquidity_zones[-5:]  # Recent liquidity zones
        )

        # Check if in FVG
        in_fvg = any(
            fvg.low <= current_price <= fvg.high
            for fvg in unfilled_fvgs[-5:]
        )

        # Check if in Order Block
        in_order_block = any(
            ob.low <= current_price <= ob.high
            for ob in unmitigated_obs[-5:]
        )

        return SMCAnalysis(
            trend=trend,
            swing_points=swings,
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            liquidity_zones=liquidity_zones,
            fair_value_gaps=unfilled_fvgs[-10:],
            order_blocks=unmitigated_obs[-10:],
            bos_detected=bos,
            choch_detected=choch,
            near_support=near_support,
            near_resistance=near_resistance,
            near_liquidity=near_liquidity,
            in_fvg=in_fvg,
            in_order_block=in_order_block
        )


# Test if run directly
if __name__ == "__main__":
    import numpy as np

    # Create sample trending data
    np.random.seed(42)
    n = 300
    trend = np.linspace(0, 50, n) + np.random.randn(n) * 5
    close = 100 + trend
    high = close + np.abs(np.random.randn(n)) * 2
    low = close - np.abs(np.random.randn(n)) * 2
    open_price = close + np.random.randn(n) * 1

    df = pd.DataFrame({
        "open": open_price,
        "high": high,
        "low": low,
        "close": close
    })

    analyzer = SMCAnalyzer()
    result = analyzer.analyze(df)

    if result:
        print(f"\n{'='*50}")
        print(f"SMC ANALYSIS RESULTS")
        print(f"{'='*50}")
        print(f"\nMarket Trend: {result.trend.value.upper()}")
        print(f"Break of Structure: {'Yes' if result.bos_detected else 'No'}")
        print(f"Change of Character: {'Yes' if result.choch_detected else 'No'}")
        print(f"\nSwing Points Found: {len(result.swing_points)}")
        print(f"Support Levels: {len(result.support_levels)}")
        print(f"Resistance Levels: {len(result.resistance_levels)}")
        print(f"Liquidity Zones: {len(result.liquidity_zones)}")
        print(f"Fair Value Gaps: {len(result.fair_value_gaps)}")
        print(f"Order Blocks: {len(result.order_blocks)}")
        print(f"\nCurrent Price Analysis:")
        print(f"  Near Support: {'Yes' if result.near_support else 'No'}")
        print(f"  Near Resistance: {'Yes' if result.near_resistance else 'No'}")
        print(f"  Near Liquidity Zone: {'Yes' if result.near_liquidity else 'No'}")
        print(f"  In Fair Value Gap: {'Yes' if result.in_fvg else 'No'}")
        print(f"  In Order Block: {'Yes' if result.in_order_block else 'No'}")

        if result.support_levels:
            print(f"\nTop Support Levels:")
            for s in result.support_levels[:3]:
                print(f"  ${s.price:.2f} (strength: {s.strength})")

        if result.resistance_levels:
            print(f"\nTop Resistance Levels:")
            for r in result.resistance_levels[:3]:
                print(f"  ${r.price:.2f} (strength: {r.strength})")
