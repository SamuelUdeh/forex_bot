"""
Backtester (ENHANCED - Uses Full Signal Engine)
================================================
Tests the SMC-enhanced signal strategy on historical data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
import pytz
import csv
import os

import config
from signal_engine import SignalEngine, SignalResult


@dataclass
class BacktestTrade:
    """Represents a single backtested trade"""
    entry_time: datetime
    pair: str
    direction: str
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: float
    score: int
    max_score: int
    grade: str

    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl_pips: Optional[float] = None


@dataclass
class BacktestResult:
    """Contains all backtest results and statistics"""
    pair: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    total_candles: int

    total_signals: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    tp1_hits: int = 0
    tp2_hits: int = 0
    sl_hits: int = 0

    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_pnl_pips: float = 0.0
    avg_win_pips: float = 0.0
    avg_loss_pips: float = 0.0
    max_drawdown_pips: float = 0.0

    a_plus_signals: int = 0
    a_plus_wins: int = 0
    a_signals: int = 0
    a_wins: int = 0
    b_signals: int = 0
    b_wins: int = 0

    trades: List[BacktestTrade] = field(default_factory=list)


class Backtester:
    """
    Backtests the SMC-enhanced confluence strategy on historical data
    """

    def __init__(self):
        """Initialize backtester with signal engine"""
        self.engine = SignalEngine()
        self.results_dir = "logs/backtest"

        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)

    def _check_trade_exit(self, trade: BacktestTrade, candle: pd.Series) -> bool:
        """Check if a trade hits TP or SL on a given candle"""
        high = candle['high']
        low = candle['low']

        if trade.direction == 'BUY':
            if low <= trade.stop_loss:
                trade.exit_time = candle.name
                trade.exit_price = trade.stop_loss
                trade.exit_reason = 'SL'
                trade.pnl_pips = trade.stop_loss - trade.entry_price
                return True

            if high >= trade.tp2:
                trade.exit_time = candle.name
                trade.exit_price = trade.tp2
                trade.exit_reason = 'TP2'
                trade.pnl_pips = trade.tp2 - trade.entry_price
                return True

            if high >= trade.tp1:
                trade.exit_time = candle.name
                trade.exit_price = trade.tp1
                trade.exit_reason = 'TP1'
                trade.pnl_pips = trade.tp1 - trade.entry_price
                return True

        else:  # SELL
            if high >= trade.stop_loss:
                trade.exit_time = candle.name
                trade.exit_price = trade.stop_loss
                trade.exit_reason = 'SL'
                trade.pnl_pips = trade.entry_price - trade.stop_loss
                return True

            if low <= trade.tp2:
                trade.exit_time = candle.name
                trade.exit_price = trade.tp2
                trade.exit_reason = 'TP2'
                trade.pnl_pips = trade.entry_price - trade.tp2
                return True

            if low <= trade.tp1:
                trade.exit_time = candle.name
                trade.exit_price = trade.tp1
                trade.exit_reason = 'TP1'
                trade.pnl_pips = trade.entry_price - trade.tp1
                return True

        return False

    def _analyze_historical(
        self,
        df: pd.DataFrame,
        idx: int,
        pair: str,
        instrument_config: Dict[str, Any]
    ) -> Optional[BacktestTrade]:
        """
        Analyze a specific point in historical data using the full signal engine

        Uses the SMC-enhanced SignalEngine for proper analysis
        """
        # Get data up to current candle (simulating real-time)
        historical_df = df.iloc[:idx+1].copy()

        if len(historical_df) < 200:
            return None

        # Use the full signal engine analysis (includes SMC) with fast_mode for backtesting
        signal = self.engine.analyze(historical_df, pair, instrument_config, fast_mode=True)

        if signal is None:
            return None

        return BacktestTrade(
            entry_time=historical_df.index[-1],
            pair=pair,
            direction=signal.direction,
            entry_price=signal.entry,
            stop_loss=signal.stop_loss,
            tp1=signal.tp1,
            tp2=signal.tp2,
            score=signal.score,
            max_score=signal.max_score,
            grade=signal.grade
        )

    def run_backtest(
        self,
        df: pd.DataFrame,
        pair: str,
        instrument_config: Dict[str, Any],
        max_open_trades: int = 1,
        show_progress: bool = True
    ) -> BacktestResult:
        """Run backtest on historical data using full SMC analysis (optimized)"""
        import time

        print(f"\n[BACKTEST] Running backtest for {pair}...")
        print(f"[BACKTEST] Data range: {df.index[0]} to {df.index[-1]}")
        print(f"[BACKTEST] Total candles: {len(df)}")
        print(f"[BACKTEST] Using optimized SMC analysis (fast_mode)")

        start_time = time.time()

        result = BacktestResult(
            pair=pair,
            timeframe=config.TIMEFRAME,
            start_date=df.index[0],
            end_date=df.index[-1],
            total_candles=len(df)
        )

        open_trades: List[BacktestTrade] = []
        closed_trades: List[BacktestTrade] = []
        last_signal_idx = None

        # Iterate through each candle (starting after warmup period)
        total_iterations = len(df) - 200
        progress_interval = max(1, total_iterations // 10)  # Report every 10%

        for idx in range(200, len(df)):
            current_candle = df.iloc[idx]

            # Progress reporting
            if show_progress and (idx - 200) % progress_interval == 0:
                progress = ((idx - 200) / total_iterations) * 100
                elapsed = time.time() - start_time
                print(f"[BACKTEST] Progress: {progress:.0f}% ({idx - 200}/{total_iterations} candles, {elapsed:.1f}s)")

            # Check and close any open trades
            for trade in open_trades[:]:
                if self._check_trade_exit(trade, current_candle):
                    closed_trades.append(trade)
                    open_trades.remove(trade)

            # Check for new signals (with cooldown)
            if len(open_trades) < max_open_trades:
                # Cooldown: no new signal within 4 candles of last signal
                if last_signal_idx is None or idx - last_signal_idx >= 4:
                    trade = self._analyze_historical(df, idx, pair, instrument_config)

                    if trade:
                        # Check min_grade filter (e.g., R_75 only allows A or A+ grades)
                        min_grade = instrument_config.get("min_grade", "B")
                        grade_order = {"A+": 3, "A": 2, "B": 1}
                        trade_grade_value = grade_order.get(trade.grade, 0)
                        min_grade_value = grade_order.get(min_grade, 1)

                        if trade_grade_value >= min_grade_value:
                            result.total_signals += 1
                            open_trades.append(trade)
                            last_signal_idx = idx

                            if trade.grade == "A+":
                                result.a_plus_signals += 1
                            elif trade.grade == "A":
                                result.a_signals += 1
                            else:
                                result.b_signals += 1

        # Close any remaining open trades at last price
        for trade in open_trades:
            trade.exit_time = df.index[-1]
            trade.exit_price = df.iloc[-1]['close']
            trade.exit_reason = 'OPEN'
            if trade.direction == 'BUY':
                trade.pnl_pips = trade.exit_price - trade.entry_price
            else:
                trade.pnl_pips = trade.entry_price - trade.exit_price
            closed_trades.append(trade)

        # Calculate statistics
        result.trades = closed_trades
        result.total_trades = len(closed_trades)

        wins = []
        losses = []

        for trade in closed_trades:
            if trade.exit_reason in ['TP1', 'TP2']:
                result.winning_trades += 1
                wins.append(trade.pnl_pips)

                if trade.exit_reason == 'TP1':
                    result.tp1_hits += 1
                else:
                    result.tp2_hits += 1

                if trade.grade == "A+":
                    result.a_plus_wins += 1
                elif trade.grade == "A":
                    result.a_wins += 1
                else:
                    result.b_wins += 1

            elif trade.exit_reason == 'SL':
                result.losing_trades += 1
                result.sl_hits += 1
                losses.append(abs(trade.pnl_pips))

        # Win rate
        if result.total_trades > 0:
            result.win_rate = (result.winning_trades / result.total_trades) * 100

        # Average win/loss
        if wins:
            result.avg_win_pips = sum(wins) / len(wins)
        if losses:
            result.avg_loss_pips = sum(losses) / len(losses)

        # Total PnL
        result.total_pnl_pips = sum(t.pnl_pips for t in closed_trades if t.pnl_pips)

        # Profit factor
        total_wins = sum(wins) if wins else 0
        total_losses = sum(losses) if losses else 0
        if total_losses > 0:
            result.profit_factor = total_wins / total_losses

        # Max drawdown
        running_pnl = 0
        peak = 0
        max_dd = 0
        for trade in closed_trades:
            if trade.pnl_pips:
                running_pnl += trade.pnl_pips
                if running_pnl > peak:
                    peak = running_pnl
                dd = peak - running_pnl
                if dd > max_dd:
                    max_dd = dd
        result.max_drawdown_pips = max_dd

        # Report completion time
        elapsed = time.time() - start_time
        print(f"[BACKTEST] Completed in {elapsed:.1f} seconds")

        return result

    def print_results(self, result: BacktestResult):
        """Print formatted backtest results"""
        print("\n" + "=" * 60)
        print(f"   BACKTEST RESULTS - {result.pair}")
        print("=" * 60)

        print(f"\nPeriod: {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}")
        print(f"Timeframe: {result.timeframe}")
        print(f"Total Candles: {result.total_candles}")

        print("\n--- SIGNALS ---")
        print(f"Total Signals: {result.total_signals}")
        print(f"  A+ Setups: {result.a_plus_signals}")
        print(f"  A Setups: {result.a_signals}")
        print(f"  B Setups: {result.b_signals}")

        print("\n--- TRADES ---")
        print(f"Total Trades: {result.total_trades}")
        print(f"Winning Trades: {result.winning_trades}")
        print(f"Losing Trades: {result.losing_trades}")
        print(f"  TP1 Hits: {result.tp1_hits}")
        print(f"  TP2 Hits: {result.tp2_hits}")
        print(f"  SL Hits: {result.sl_hits}")

        print("\n--- PERFORMANCE ---")
        print(f"Win Rate: {result.win_rate:.1f}%")
        print(f"Profit Factor: {result.profit_factor:.2f}")
        print(f"Total PnL (pips): {result.total_pnl_pips:.2f}")
        print(f"Avg Win (pips): {result.avg_win_pips:.2f}")
        print(f"Avg Loss (pips): {result.avg_loss_pips:.2f}")
        print(f"Max Drawdown (pips): {result.max_drawdown_pips:.2f}")

        print("\n--- BY GRADE ---")
        if result.a_plus_signals > 0:
            a_plus_wr = (result.a_plus_wins / result.a_plus_signals) * 100
            print(f"A+ Win Rate: {a_plus_wr:.1f}% ({result.a_plus_wins}/{result.a_plus_signals})")
        if result.a_signals > 0:
            a_wr = (result.a_wins / result.a_signals) * 100
            print(f"A Win Rate: {a_wr:.1f}% ({result.a_wins}/{result.a_signals})")
        if result.b_signals > 0:
            b_wr = (result.b_wins / result.b_signals) * 100
            print(f"B Win Rate: {b_wr:.1f}% ({result.b_wins}/{result.b_signals})")

        print("=" * 60)

    def save_results(self, result: BacktestResult) -> str:
        """Save backtest results to CSV"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.results_dir}/backtest_{result.pair}_{timestamp}.csv"

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            writer.writerow(["BACKTEST SUMMARY"])
            writer.writerow(["Pair", result.pair])
            writer.writerow(["Period", f"{result.start_date} to {result.end_date}"])
            writer.writerow(["Total Signals", result.total_signals])
            writer.writerow(["Win Rate", f"{result.win_rate:.1f}%"])
            writer.writerow(["Profit Factor", f"{result.profit_factor:.2f}"])
            writer.writerow(["Total PnL (pips)", f"{result.total_pnl_pips:.2f}"])
            writer.writerow([])

            writer.writerow(["TRADES"])
            writer.writerow([
                "Entry Time", "Direction", "Grade", "Score", "Entry", "SL", "TP1", "TP2",
                "Exit Time", "Exit Price", "Exit Reason", "PnL (pips)"
            ])

            for trade in result.trades:
                writer.writerow([
                    trade.entry_time,
                    trade.direction,
                    trade.grade,
                    f"{trade.score}/{trade.max_score}",
                    f"{trade.entry_price:.5f}",
                    f"{trade.stop_loss:.5f}",
                    f"{trade.tp1:.5f}",
                    f"{trade.tp2:.5f}",
                    trade.exit_time,
                    f"{trade.exit_price:.5f}" if trade.exit_price else "",
                    trade.exit_reason,
                    f"{trade.pnl_pips:.2f}" if trade.pnl_pips else ""
                ])

        print(f"\n[BACKTEST] Results saved to: {filename}")
        return filename


def run_backtest_oanda(pair: str, candles: int = 1000):
    """Run backtest on an OANDA instrument"""
    from data.oanda_fetcher import OandaFetcher

    fetcher = OandaFetcher()
    backtester = Backtester()

    instrument_config = config.OANDA_INSTRUMENTS.get(pair)
    if not instrument_config:
        print(f"[ERROR] Unknown instrument: {pair}")
        return None

    print(f"\n[BACKTEST] Fetching {candles} candles for {pair}...")
    df = fetcher.get_candles(pair, config.TIMEFRAME, candles)

    if df is None or len(df) < 250:
        print("[ERROR] Insufficient data for backtest")
        return None

    result = backtester.run_backtest(df, pair, instrument_config)
    backtester.print_results(result)
    backtester.save_results(result)

    return result


def get_optimal_timeframe(symbol: str) -> str:
    """Get the optimal timeframe for a given symbol based on backtest results"""
    # R_75 works best on H4
    if symbol == "R_75":
        return "H4"
    # 1-second pairs need M5 (but we disabled them)
    elif symbol.startswith("1HZ"):
        return "M5"
    # Boom/Crash work better on H4
    elif symbol.startswith("BOOM") or symbol.startswith("CRASH"):
        return "H4"
    # All other synthetics work on H1
    else:
        return "H1"


def run_backtest_deriv(symbol: str, candles: int = 1000):
    """Run backtest on a Deriv instrument"""
    from data.deriv_fetcher import DerivFetcher

    fetcher = DerivFetcher()
    backtester = Backtester()

    instrument_config = config.DERIV_INSTRUMENTS.get(symbol)
    if not instrument_config:
        print(f"[ERROR] Unknown instrument: {symbol}")
        return None

    # Use optimal timeframe for this symbol
    timeframe = get_optimal_timeframe(symbol)

    print(f"\n[BACKTEST] Fetching {candles} candles for {symbol} ({timeframe})...")
    df = fetcher.get_candles(symbol, timeframe, candles)

    if df is None or len(df) < 250:
        print("[ERROR] Insufficient data for backtest")
        return None

    result = backtester.run_backtest(df, symbol, instrument_config)
    backtester.print_results(result)
    backtester.save_results(result)

    return result


if __name__ == "__main__":
    import sys

    print("\n" + "=" * 60)
    print("   BACKTEST MODULE (SMC-Enhanced)")
    print("=" * 60)

    if len(sys.argv) > 1:
        pair = sys.argv[1].upper()
        candles = int(sys.argv[2]) if len(sys.argv) > 2 else 1000

        if pair in config.OANDA_INSTRUMENTS:
            run_backtest_oanda(pair, candles)
        elif pair in config.DERIV_INSTRUMENTS:
            run_backtest_deriv(pair, candles)
        else:
            print(f"[ERROR] Unknown instrument: {pair}")
    else:
        print("\nUsage:")
        print("  python backtester.py XAU_USD 1000")
        print("  python backtester.py R_75 500")
