"""
Signal Logger
=============
Logs all trading signals to CSV for review and analysis
"""

import csv
import os
from datetime import datetime
from typing import Optional
import pytz

import config
from signal_engine import SignalResult


class SignalLogger:
    """Logs signals to CSV file"""

    def __init__(self):
        """Initialize logger with file path from config"""
        self.log_file = config.LOG_FILE
        self.columns = config.LOG_COLUMNS
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create log file with headers if it doesn't exist"""
        # Create logs directory if needed
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Create file with headers if it doesn't exist
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.columns)
            print(f"[LOGGER] Created log file: {self.log_file}")

    def log_signal(self, signal: SignalResult) -> bool:
        """
        Log a signal to the CSV file

        Args:
            signal: SignalResult object to log

        Returns:
            True if logged successfully
        """
        try:
            row = [
                signal.datetime_utc.strftime("%Y-%m-%d %H:%M:%S"),
                signal.pair,
                signal.direction,
                signal.score,
                signal.grade,
                f"{signal.entry:.5f}",
                f"{signal.stop_loss:.5f}",
                f"{signal.tp1:.5f}",
                f"{signal.tp2:.5f}",
                signal.session_name,
                f"{signal.rsi:.2f}",
                signal.macd_state,
                "above" if signal.ema_trend else "below",
                "bullish" if signal.ema_cross else "bearish"
            ]

            with open(self.log_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(row)

            print(f"[LOGGER] Logged signal: {signal.direction} {signal.pair}")
            return True

        except Exception as e:
            print(f"[LOGGER] Error logging signal: {e}")
            return False

    def get_recent_signals(self, count: int = 10) -> list:
        """
        Get most recent signals from log

        Args:
            count: Number of recent signals to retrieve

        Returns:
            List of dictionaries with signal data
        """
        try:
            signals = []
            with open(self.log_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    signals.append(row)

            return signals[-count:] if signals else []

        except Exception as e:
            print(f"[LOGGER] Error reading signals: {e}")
            return []

    def get_stats(self) -> dict:
        """
        Get statistics from logged signals

        Returns:
            Dictionary with signal statistics
        """
        try:
            signals = []
            with open(self.log_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                signals = list(reader)

            if not signals:
                return {"total": 0}

            total = len(signals)
            buys = len([s for s in signals if s.get("direction") == "BUY"])
            sells = len([s for s in signals if s.get("direction") == "SELL"])
            a_plus = len([s for s in signals if s.get("grade") == "A+"])
            b_grade = len([s for s in signals if s.get("grade") == "B"])

            # Count by pair
            pairs = {}
            for s in signals:
                pair = s.get("pair", "Unknown")
                pairs[pair] = pairs.get(pair, 0) + 1

            return {
                "total": total,
                "buys": buys,
                "sells": sells,
                "a_plus_setups": a_plus,
                "b_setups": b_grade,
                "by_pair": pairs
            }

        except Exception as e:
            print(f"[LOGGER] Error calculating stats: {e}")
            return {"total": 0, "error": str(e)}


# Test if run directly
if __name__ == "__main__":
    from signal_engine import SignalResult
    import pytz

    logger = SignalLogger()

    # Create a sample signal
    sample = SignalResult(
        pair="XAU_USD",
        display_name="XAU/USD (Gold)",
        direction="BUY",
        score=5,
        max_score=5,
        grade="A+",
        entry=1950.50,
        stop_loss=1940.25,
        tp1=1960.75,
        tp2=1971.00,
        atr=6.83,
        rsi=52.5,
        macd_state="bullish",
        ema_trend=True,
        ema_cross=True,
        rsi_neutral=True,
        macd_favorable=True,
        session_active=True,
        session_name="London",
        datetime_utc=datetime.now(pytz.UTC),
        checklist={
            "ema_trend": True,
            "ema_cross": True,
            "rsi_neutral": True,
            "macd_favorable": True,
            "session_active": True
        }
    )

    # Log it
    logger.log_signal(sample)

    # Get stats
    print("\nSignal Stats:")
    stats = logger.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
