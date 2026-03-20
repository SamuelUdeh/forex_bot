"""
Volume Analysis Module
======================
Analyzes volume for trade confirmation
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class VolumeAnalysis:
    """Volume analysis results"""
    has_volume: bool           # Whether volume data is available
    current_volume: float      # Current candle volume
    avg_volume: float          # Average volume (20 period)
    volume_ratio: float        # Current / Average (>1.5 = spike)
    is_volume_spike: bool      # Volume significantly above average
    obv_trend: str             # "UP", "DOWN", or "NEUTRAL"
    volume_trend: str          # "INCREASING", "DECREASING", or "NEUTRAL"
    vwap: float               # Volume Weighted Average Price
    price_vs_vwap: str        # "ABOVE", "BELOW", or "AT"
    confirmation_score: int    # 0-2 points for confluence


class VolumeAnalyzer:
    """Analyzes volume patterns for trade confirmation"""

    def __init__(self, avg_period: int = 20, spike_threshold: float = 1.5):
        """
        Args:
            avg_period: Period for calculating average volume
            spike_threshold: Multiplier for detecting volume spikes
        """
        self.avg_period = avg_period
        self.spike_threshold = spike_threshold

    def calculate_obv(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate On-Balance Volume (OBV)
        OBV increases on up days, decreases on down days
        """
        if 'volume' not in df.columns or df['volume'].sum() == 0:
            return pd.Series([0] * len(df), index=df.index)

        obv = [0]
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i - 1]:
                obv.append(obv[-1] + df['volume'].iloc[i])
            elif df['close'].iloc[i] < df['close'].iloc[i - 1]:
                obv.append(obv[-1] - df['volume'].iloc[i])
            else:
                obv.append(obv[-1])

        return pd.Series(obv, index=df.index)

    def calculate_vwap(self, df: pd.DataFrame, period: int = 20) -> float:
        """
        Calculate Volume Weighted Average Price
        VWAP = Sum(Price * Volume) / Sum(Volume)
        """
        if 'volume' not in df.columns or df['volume'].sum() == 0:
            # If no volume, return simple average
            return df['close'].iloc[-period:].mean()

        recent = df.iloc[-period:]
        typical_price = (recent['high'] + recent['low'] + recent['close']) / 3
        total_volume = recent['volume'].sum()

        if total_volume == 0:
            return typical_price.mean()

        vwap = (typical_price * recent['volume']).sum() / total_volume
        return vwap

    def get_obv_trend(self, obv: pd.Series, lookback: int = 10) -> str:
        """Determine OBV trend direction"""
        if len(obv) < lookback:
            return "NEUTRAL"

        recent_obv = obv.iloc[-lookback:].values

        # Linear regression slope
        x = np.arange(lookback)
        slope = np.polyfit(x, recent_obv, 1)[0]

        # Normalize slope by OBV range
        obv_range = max(recent_obv) - min(recent_obv)
        if obv_range == 0:
            return "NEUTRAL"

        normalized_slope = slope / obv_range * lookback

        if normalized_slope > 0.1:
            return "UP"
        elif normalized_slope < -0.1:
            return "DOWN"
        return "NEUTRAL"

    def get_volume_trend(self, df: pd.DataFrame, lookback: int = 10) -> str:
        """Determine if volume is increasing or decreasing"""
        if 'volume' not in df.columns:
            return "NEUTRAL"

        if len(df) < lookback:
            return "NEUTRAL"

        volumes = df['volume'].iloc[-lookback:].values

        if volumes.sum() == 0:
            return "NEUTRAL"

        # Compare first half to second half
        mid = lookback // 2
        first_half_avg = volumes[:mid].mean()
        second_half_avg = volumes[mid:].mean()

        if first_half_avg == 0:
            return "NEUTRAL"

        change = (second_half_avg - first_half_avg) / first_half_avg

        if change > 0.2:
            return "INCREASING"
        elif change < -0.2:
            return "DECREASING"
        return "NEUTRAL"

    def analyze(self, df: pd.DataFrame) -> VolumeAnalysis:
        """
        Perform complete volume analysis

        Args:
            df: DataFrame with OHLCV data

        Returns:
            VolumeAnalysis with all metrics
        """
        # Check if volume data exists
        has_volume = 'volume' in df.columns and df['volume'].sum() > 0

        if not has_volume:
            # Return neutral analysis for instruments without volume
            current_price = df['close'].iloc[-1]
            return VolumeAnalysis(
                has_volume=False,
                current_volume=0,
                avg_volume=0,
                volume_ratio=1.0,
                is_volume_spike=False,
                obv_trend="NEUTRAL",
                volume_trend="NEUTRAL",
                vwap=current_price,
                price_vs_vwap="AT",
                confirmation_score=0  # No volume = no extra points
            )

        # Current and average volume
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].iloc[-self.avg_period:].mean() if len(df) >= self.avg_period else df['volume'].mean()

        # Volume ratio
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        is_volume_spike = volume_ratio >= self.spike_threshold

        # OBV analysis
        obv = self.calculate_obv(df)
        obv_trend = self.get_obv_trend(obv)

        # Volume trend
        volume_trend = self.get_volume_trend(df)

        # VWAP
        vwap = self.calculate_vwap(df, self.avg_period)
        current_price = df['close'].iloc[-1]

        vwap_diff = (current_price - vwap) / vwap * 100
        if vwap_diff > 0.1:
            price_vs_vwap = "ABOVE"
        elif vwap_diff < -0.1:
            price_vs_vwap = "BELOW"
        else:
            price_vs_vwap = "AT"

        # Calculate confirmation score
        confirmation_score = self._calculate_score(
            is_volume_spike, obv_trend, volume_trend
        )

        return VolumeAnalysis(
            has_volume=True,
            current_volume=current_volume,
            avg_volume=avg_volume,
            volume_ratio=volume_ratio,
            is_volume_spike=is_volume_spike,
            obv_trend=obv_trend,
            volume_trend=volume_trend,
            vwap=vwap,
            price_vs_vwap=price_vs_vwap,
            confirmation_score=confirmation_score
        )

    def _calculate_score(self, is_spike: bool, obv_trend: str, volume_trend: str) -> int:
        """Calculate volume confirmation score (0-2 points)"""
        score = 0

        # Volume spike = +1
        if is_spike:
            score += 1

        # OBV trending = +0.5 (converted to int later)
        # Volume increasing = +0.5
        trend_score = 0
        if obv_trend in ["UP", "DOWN"]:
            trend_score += 0.5
        if volume_trend == "INCREASING":
            trend_score += 0.5

        score += int(trend_score)

        return min(score, 2)  # Cap at 2

    def get_volume_signal(self, volume_analysis: VolumeAnalysis, direction: str) -> Tuple[int, str]:
        """
        Get volume confirmation for a trade direction

        Args:
            volume_analysis: VolumeAnalysis object
            direction: "BUY" or "SELL"

        Returns:
            Tuple of (score, description)
        """
        if not volume_analysis.has_volume:
            return 0, "No volume data"

        score = 0
        details = []

        # Volume spike confirms the move
        if volume_analysis.is_volume_spike:
            score += 1
            details.append(f"Vol spike ({volume_analysis.volume_ratio:.1f}x)")

        # OBV should align with direction
        if direction == "BUY" and volume_analysis.obv_trend == "UP":
            score += 1
            details.append("OBV bullish")
        elif direction == "SELL" and volume_analysis.obv_trend == "DOWN":
            score += 1
            details.append("OBV bearish")

        # VWAP confirmation
        if direction == "BUY" and volume_analysis.price_vs_vwap == "ABOVE":
            details.append("Above VWAP")
        elif direction == "SELL" and volume_analysis.price_vs_vwap == "BELOW":
            details.append("Below VWAP")

        score = min(score, 2)
        description = ", ".join(details) if details else "Neutral volume"

        return score, description
