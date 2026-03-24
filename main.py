"""
Forex Signal Bot - Main Entry Point
====================================
Orchestrates signal scanning and scheduling
"""

import sys
import time
from datetime import datetime
from typing import List
import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from data.oanda_fetcher import OandaFetcher
from data.deriv_fetcher import DerivFetcher
from signal_engine import SignalEngine, SignalResult, PreSignalResult
from telegram_bot import TelegramBot
from logger import SignalLogger


class SignalBot:
    """Main bot class that coordinates all components"""

    def __init__(self):
        """Initialize all components"""
        print("\n" + "=" * 60)
        print("   FOREX SIGNAL BOT - Initializing")
        print("=" * 60)

        self.oanda = OandaFetcher()
        self.deriv = DerivFetcher()
        self.engine = SignalEngine()
        self.telegram = TelegramBot()
        self.logger = SignalLogger()

        # Track signal cooldowns to avoid duplicates
        self.last_signals = {}

        # Track pre-signals for two-stage alerts
        self.pending_pre_signals = {}

    def test_connections(self) -> bool:
        """
        Test all API connections

        Returns:
            True if all connections successful
        """
        print("\n[STARTUP] Testing connections...")

        results = []

        # Test OANDA
        if config.OANDA_API_KEY:
            results.append(("OANDA", self.oanda.test_connection()))
        else:
            print("[STARTUP] OANDA API key not configured - skipping")

        # Test Deriv
        results.append(("Deriv", self.deriv.test_connection()))

        # Test Telegram
        results.append(("Telegram", self.telegram.test_connection()))

        # Print summary
        print("\nConnection Status:")
        all_ok = True
        for name, status in results:
            status_str = "OK" if status else "FAILED"
            print(f"  {name}: {status_str}")
            if not status:
                all_ok = False

        return all_ok

    def scan_oanda_instruments(self) -> List[SignalResult]:
        """
        Scan all enabled OANDA instruments for signals

        Returns:
            List of SignalResult objects for qualifying signals
        """
        signals = []
        instruments = self.oanda.get_enabled_instruments()

        if not instruments:
            print("[SCAN] No OANDA instruments enabled")
            return signals

        print(f"\n[SCAN] Scanning {len(instruments)} OANDA instruments...")

        for symbol, instrument_config in instruments.items():
            try:
                # Fetch candle data
                df = self.oanda.get_candles(
                    symbol,
                    config.TIMEFRAME,
                    config.CANDLES_TO_FETCH
                )

                if df is None or len(df) < 200:
                    print(f"[SCAN] Insufficient data for {symbol}")
                    continue

                # Analyze for signals
                signal = self.engine.analyze(df, symbol, instrument_config)

                if signal:
                    signals.append(signal)
                    print(f"[SCAN] Signal found: {signal.direction} {symbol} ({signal.grade})")

            except Exception as e:
                print(f"[SCAN] Error scanning {symbol}: {e}")

        return signals

    def get_optimal_timeframe(self, symbol: str) -> str:
        """Get the optimal timeframe for a given symbol based on config or backtest results"""
        # First check if config specifies a timeframe for this instrument
        instrument_config = config.DERIV_INSTRUMENTS.get(symbol, {})
        if "timeframe" in instrument_config:
            return instrument_config["timeframe"]

        # R_75 performs best on H4
        if symbol == "R_75":
            return "H4"
        # 1-second volatility indices perform best on M5
        elif symbol.startswith("1HZ"):
            return "M5"
        else:
            return "H1"

    def scan_deriv_instruments(self) -> List[SignalResult]:
        """
        Scan all enabled Deriv instruments for signals

        Returns:
            List of SignalResult objects for qualifying signals
        """
        signals = []
        instruments = self.deriv.get_enabled_instruments()

        if not instruments:
            print("[SCAN] No Deriv instruments enabled")
            return signals

        print(f"\n[SCAN] Scanning {len(instruments)} Deriv instruments...")

        for symbol, instrument_config in instruments.items():
            try:
                # Get optimal timeframe for this symbol
                timeframe = self.get_optimal_timeframe(symbol)

                # Fetch candle data (need 250 for EMA 200)
                # Forex pairs need more candles requested to get enough data
                candle_count = 500 if symbol.startswith("frx") else 250
                df = self.deriv.get_candles(
                    symbol,
                    timeframe,
                    candle_count
                )

                if df is None or len(df) < 200:
                    print(f"[SCAN] Insufficient data for {symbol}")
                    continue

                # Analyze for signals
                signal = self.engine.analyze(df, symbol, instrument_config)

                if signal:
                    # Check min_grade filter (e.g., R_75 only allows A or A+ grades)
                    min_grade = instrument_config.get("min_grade", "B")  # Default: allow all grades

                    grade_order = {"A+": 3, "A": 2, "B": 1}
                    signal_grade_value = grade_order.get(signal.grade, 0)
                    min_grade_value = grade_order.get(min_grade, 1)

                    if signal_grade_value >= min_grade_value:
                        signals.append(signal)
                        print(f"[SCAN] SIGNAL: {signal.direction} {symbol} ({signal.grade}) on {timeframe}")
                    else:
                        print(f"[SCAN] {symbol}: {signal.grade} signal skipped (min: {min_grade})")
                else:
                    print(f"[SCAN] No signal for {symbol} ({timeframe})")

            except Exception as e:
                print(f"[SCAN] Error scanning {symbol}: {e}")

        return signals

    def pre_scan_deriv_instruments(self) -> List[PreSignalResult]:
        """
        Pre-scan for potential setups (run 15 mins before candle close)
        Returns list of PreSignalResult for instruments showing 65%+ confluence
        """
        pre_signals = []
        instruments = self.deriv.get_enabled_instruments()

        if not instruments:
            return pre_signals

        print(f"\n[PRE-SCAN] Checking {len(instruments)} instruments for forming setups...")

        for symbol, instrument_config in instruments.items():
            try:
                timeframe = self.get_optimal_timeframe(symbol)
                df = self.deriv.get_candles(symbol, timeframe, config.CANDLES_TO_FETCH)

                if df is None or len(df) < 200:
                    continue

                pre_signal = self.engine.pre_analyze(df, symbol, instrument_config)

                if pre_signal:
                    pre_signals.append(pre_signal)
                    print(f"[PRE-SCAN] SETUP FORMING: {pre_signal.direction} {symbol} ({pre_signal.confluence_pct:.0f}%)")

            except Exception as e:
                print(f"[PRE-SCAN] Error checking {symbol}: {e}")

        return pre_signals

    def run_pre_scan(self):
        """Run pre-scan and send alerts for forming setups"""
        utc_now = datetime.now(pytz.UTC)
        print("\n" + "=" * 60)
        print(f"   PRE-SCAN - {utc_now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("   Checking for setups forming (15 mins before candle close)")
        print("=" * 60)

        pre_signals = self.pre_scan_deriv_instruments()

        if pre_signals:
            print(f"\n[PRE-SCAN] Found {len(pre_signals)} potential setup(s)")
            for pre_signal in pre_signals:
                key = f"{pre_signal.pair}_{pre_signal.direction}"

                # Track this pre-signal
                self.pending_pre_signals[key] = pre_signal

                # Send pre-signal alert
                if self.telegram.send_pre_signal(pre_signal):
                    print(f"[PRE-SCAN] Alert sent for {pre_signal.display_name}")
        else:
            print("\n[PRE-SCAN] No setups forming")

    def process_signals(self, signals: List[SignalResult]):
        """
        Process signals: log and send alerts

        Args:
            signals: List of SignalResult objects
        """
        for signal in signals:
            # Check cooldown (avoid duplicate signals within 4 hours)
            key = f"{signal.pair}_{signal.direction}"
            now = datetime.now(pytz.UTC)

            if key in self.last_signals:
                last_time = self.last_signals[key]
                hours_diff = (now - last_time).total_seconds() / 3600
                if hours_diff < 4:
                    print(f"[PROCESS] Skipping {key} - signal sent {hours_diff:.1f}h ago")
                    continue

            # Set cooldown FIRST to prevent duplicates in same batch
            # This prevents logging the same signal multiple times if Telegram fails
            self.last_signals[key] = now

            # Send Telegram alert
            if self.telegram.send_signal(signal):
                # Log only after successful Telegram send
                self.logger.log_signal(signal)
                print(f"[PROCESS] Signal sent and logged: {signal.direction} {signal.pair}")
            else:
                print(f"[PROCESS] Telegram failed for {signal.direction} {signal.pair} - not logged")

    def run_scan(self):
        """Run a complete scan cycle"""
        utc_now = datetime.now(pytz.UTC)
        print("\n" + "=" * 60)
        print(f"   SIGNAL SCAN - {utc_now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("=" * 60)

        all_signals = []

        # Scan OANDA instruments
        if config.OANDA_API_KEY:
            oanda_signals = self.scan_oanda_instruments()
            all_signals.extend(oanda_signals)

        # Scan Deriv instruments
        deriv_signals = self.scan_deriv_instruments()
        all_signals.extend(deriv_signals)

        # Process all signals
        if all_signals:
            print(f"\n[SCAN] Found {len(all_signals)} signal(s)")
            self.process_signals(all_signals)
        else:
            print("\n[SCAN] No signals found this cycle")

        # Heartbeat
        print(f"\n[HEARTBEAT] Scan complete at {utc_now.strftime('%H:%M:%S UTC')}")
        print(f"[HEARTBEAT] Next scan in 4 hours")

    def start_scheduler(self):
        """Start the APScheduler to run scans automatically"""
        scheduler = BlockingScheduler(timezone=pytz.UTC)

        # Build cron hours string: "0,1,2,..." for every hour
        hours = ",".join(str(h) for h in config.SCHEDULE_HOURS)

        # Add main scan job - runs at :00 (top of each hour)
        scheduler.add_job(
            self.run_scan,
            CronTrigger(hour=hours, minute=0),
            id="signal_scan",
            name="Signal Scan",
            misfire_grace_time=300
        )

        # Add pre-scan job - runs at :45 (15 mins before each hour)
        scheduler.add_job(
            self.run_pre_scan,
            CronTrigger(hour=hours, minute=45),
            id="pre_scan",
            name="Pre-Scan (Setup Forming)",
            misfire_grace_time=300
        )

        print(f"\n[SCHEDULER] Two-Stage Alert System Active:")
        print(f"  - Pre-scan: Every hour at :45 (setup forming alerts)")
        print(f"  - Main scan: Every hour at :00 (confirmed signals)")
        print("[SCHEDULER] Press Ctrl+C to stop\n")

        try:
            # Run initial scan immediately
            self.run_scan()

            # Start scheduler
            scheduler.start()

        except KeyboardInterrupt:
            print("\n[SCHEDULER] Shutting down...")
            scheduler.shutdown()

    def run_once(self):
        """Run a single scan (for testing)"""
        print("\n[MODE] Running single scan...")
        self.run_scan()
        print("\n[MODE] Single scan complete")


def print_usage():
    """Print usage instructions"""
    print("""
Usage:
  python main.py                    Run scheduler (scans every 4 hours)
  python main.py --once             Run single scan
  python main.py --scan             Quick scan all enabled pairs
  python main.py --scan R_10        Scan specific pair
  python main.py --backtest PAIR    Backtest a specific instrument
  python main.py --backtest-all     Backtest all enabled instruments

Scan Examples:
  python main.py --scan             Scan all enabled pairs
  python main.py --scan R_10        Scan R_10 only
  python main.py --scan R_75        Scan R_75 only

Backtest Examples:
  python main.py --backtest XAU_USD
  python main.py --backtest R_75
  python main.py --backtest EUR_USD --candles 500

Options:
  --candles N    Number of historical candles for backtest (default: 1000)
""")


def run_backtest(pair: str, candles: int = 1000):
    """Run backtest for a specific pair"""
    from backtester import run_backtest_oanda, run_backtest_deriv

    pair = pair.upper()

    if pair in config.OANDA_INSTRUMENTS:
        return run_backtest_oanda(pair, candles)
    elif pair in config.DERIV_INSTRUMENTS:
        return run_backtest_deriv(pair, candles)
    else:
        print(f"\n[ERROR] Unknown instrument: {pair}")
        print("\nAvailable OANDA instruments:")
        for p in config.OANDA_INSTRUMENTS:
            print(f"  - {p}")
        print("\nAvailable Deriv instruments:")
        for s in config.DERIV_INSTRUMENTS:
            print(f"  - {s}")
        return None


def run_quick_scan(specific_pair: str = None):
    """Run a quick scan for signals"""
    from data.deriv_fetcher import DerivFetcher
    from signal_engine import SignalEngine
    import pandas_ta as ta

    fetcher = DerivFetcher()
    engine = SignalEngine()

    # Determine which pairs to scan
    if specific_pair:
        if specific_pair in config.DERIV_INSTRUMENTS:
            pairs = {specific_pair: config.DERIV_INSTRUMENTS[specific_pair]}
        else:
            print(f"\n[ERROR] Unknown pair: {specific_pair}")
            print("\nAvailable pairs:")
            for p in config.DERIV_INSTRUMENTS:
                print(f"  - {p}")
            return
    else:
        # Scan all enabled pairs
        pairs = {k: v for k, v in config.DERIV_INSTRUMENTS.items() if v.get("enabled")}

    print("\n" + "=" * 50)
    print("   QUICK SCAN - VOLATILITY INDICES")
    print("=" * 50)

    signals_found = []

    for symbol, instrument_config in pairs.items():
        # Get optimal timeframe - check config first
        if "timeframe" in instrument_config:
            timeframe = instrument_config["timeframe"]
        elif symbol == "R_75":
            timeframe = "H4"
        elif symbol.startswith("1HZ"):
            timeframe = "M5"
        else:
            timeframe = "H1"

        print(f"\nScanning {symbol} ({timeframe})...")

        try:
            # Forex pairs need more candles requested
            candle_count = 500 if symbol.startswith("frx") else 250
            df = fetcher.get_candles(symbol, timeframe, candle_count)

            if df is None or len(df) < 200:
                print(f"  -> Insufficient data")
                continue

            signal = engine.analyze(df, symbol, instrument_config)

            if signal:
                # Check min_grade filter (e.g., R_75 only allows A or A+ grades)
                min_grade = instrument_config.get("min_grade", "B")
                grade_order = {"A+": 3, "A": 2, "B": 1}
                signal_grade_value = grade_order.get(signal.grade, 0)
                min_grade_value = grade_order.get(min_grade, 1)

                if signal_grade_value >= min_grade_value:
                    signals_found.append((signal, timeframe))
                    print(f"  -> SIGNAL FOUND: {signal.direction} ({signal.grade})")
                else:
                    print(f"  -> {signal.grade} signal skipped (requires {min_grade}+)")
            else:
                # Show current indicators
                df_calc = df.copy()
                df_calc['rsi'] = ta.rsi(df_calc['close'], length=14)
                adx_result = ta.adx(df_calc['high'], df_calc['low'], df_calc['close'], length=14)
                if adx_result is not None:
                    df_calc['adx'] = adx_result.iloc[:, 0]
                latest = df_calc.iloc[-1]
                rsi = latest['rsi']
                adx = latest.get('adx', 0)
                print(f"  -> No signal (RSI: {rsi:.1f}, ADX: {adx:.1f})")

        except Exception as e:
            print(f"  -> Error: {e}")

    # Print results
    print("\n" + "=" * 50)
    if signals_found:
        print(f"   {len(signals_found)} SIGNAL(S) FOUND!")
        print("=" * 50)

        for signal, timeframe in signals_found:
            print(f"""
----------------------------------------
Pair: {signal.display_name}
Direction: {signal.direction}
Grade: {signal.grade} ({signal.score}/{signal.max_score})
Timeframe: {timeframe}

Entry: {signal.entry:.2f}
Stop Loss: {signal.stop_loss:.2f}
TP1: {signal.tp1:.2f}
TP2: {signal.tp2:.2f}

Indicators: RSI {signal.rsi:.1f} | ADX {signal.adx:.1f}
----------------------------------------""")
    else:
        print("   NO SIGNALS AT THIS TIME")
        print("=" * 50)
        print("\nAll pairs checked. No setups meeting criteria.")
        print("Check back later for new opportunities.")


def run_backtest_all(candles: int = 1000):
    """Run backtest for all enabled instruments"""
    from backtester import run_backtest_oanda, run_backtest_deriv

    results = []

    print("\n" + "=" * 60)
    print("   BACKTESTING ALL ENABLED INSTRUMENTS")
    print("=" * 60)

    # Backtest OANDA instruments
    if config.OANDA_API_KEY:
        for pair, settings in config.OANDA_INSTRUMENTS.items():
            if settings.get("enabled"):
                result = run_backtest_oanda(pair, candles)
                if result:
                    results.append(result)

    # Backtest Deriv instruments
    for symbol, settings in config.DERIV_INSTRUMENTS.items():
        if settings.get("enabled"):
            result = run_backtest_deriv(symbol, candles)
            if result:
                results.append(result)

    # Print summary
    if results:
        print("\n" + "=" * 60)
        print("   BACKTEST SUMMARY - ALL INSTRUMENTS")
        print("=" * 60)
        print(f"\n{'Pair':<20} {'Signals':<10} {'Win Rate':<12} {'PnL (pips)':<12} {'Profit Factor'}")
        print("-" * 70)
        for r in results:
            print(f"{r.pair:<20} {r.total_signals:<10} {r.win_rate:<12.1f}% {r.total_pnl_pips:<12.2f} {r.profit_factor:.2f}")
        print("-" * 70)

    return results


def main():
    """Main entry point"""
    print("\n" + "=" * 60)
    print("   FOREX & SYNTHETICS SIGNAL BOT")
    print("   Confluence-Based Trading Signals")
    print("=" * 60)

    # Parse command line args
    args = sys.argv[1:]

    # Help
    if "--help" in args or "-h" in args:
        print_usage()
        sys.exit(0)

    # Get candles count if specified
    candles = 1000
    if "--candles" in args:
        idx = args.index("--candles")
        if idx + 1 < len(args):
            try:
                candles = int(args[idx + 1])
            except ValueError:
                print("[ERROR] Invalid candles count")
                sys.exit(1)

    # Backtest mode
    if "--backtest" in args:
        idx = args.index("--backtest")
        if idx + 1 < len(args) and not args[idx + 1].startswith("--"):
            pair = args[idx + 1]
            run_backtest(pair, candles)
        else:
            print("[ERROR] Please specify an instrument to backtest")
            print_usage()
        sys.exit(0)

    # Backtest all
    if "--backtest-all" in args:
        run_backtest_all(candles)
        sys.exit(0)

    # Quick scan mode
    if "--scan" in args:
        idx = args.index("--scan")
        specific_pair = None
        if idx + 1 < len(args) and not args[idx + 1].startswith("--"):
            # Keep original case for Deriv instruments (frxXAUUSD)
            specific_pair = args[idx + 1]
            # Try uppercase first for OANDA, then original case for Deriv
            if specific_pair.upper() not in config.DERIV_INSTRUMENTS:
                if specific_pair in config.DERIV_INSTRUMENTS:
                    pass  # Keep original case
                else:
                    specific_pair = specific_pair.upper()

        run_quick_scan(specific_pair)
        sys.exit(0)

    # Check for required config for live mode
    if not config.OANDA_API_KEY and not config.DERIV_API_TOKEN:
        print("\n[ERROR] No API keys configured!")
        print("Please copy .env.example to .env and add your API keys.")
        sys.exit(1)

    # Initialize bot
    bot = SignalBot()

    # Test connections
    if not bot.test_connections():
        print("\n[WARNING] Some connections failed. Check your API keys.")
        print("Continuing anyway...\n")

    # Send startup message
    bot.telegram.send_startup_message()

    # Check command line args
    if "--once" in args:
        # Single scan mode
        bot.run_once()
    else:
        # Scheduler mode
        bot.start_scheduler()


if __name__ == "__main__":
    main()
