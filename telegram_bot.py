"""
Telegram Bot
============
Handles formatting and sending trading signal alerts via Telegram
"""

import asyncio
import requests
from typing import Optional
from datetime import datetime
import pytz

import config
from signal_engine import SignalResult, PreSignalResult


class TelegramBot:
    """Sends formatted trading signals to Telegram"""

    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self):
        """Initialize with Telegram credentials from config"""
        self.token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.dry_run = config.DRY_RUN

    def format_signal(self, signal: SignalResult) -> str:
        """
        Format a signal into the Telegram message format

        Args:
            signal: SignalResult object with all signal data

        Returns:
            Formatted message string
        """
        # Direction emoji and text
        if signal.direction == "BUY":
            direction_emoji = "\U0001F7E2"  # Green circle
            direction_text = "BUY SIGNAL"
        else:
            direction_emoji = "\U0001F534"  # Red circle
            direction_text = "SELL SIGNAL"

        # Grade stars
        if signal.grade == "A+":
            stars = "\u2B50" * 5  # 5 stars
            grade_text = f"A+ SETUP ({signal.score}/{signal.max_score})"
        else:
            stars = "\u2B50" * 4  # 4 stars
            grade_text = f"B SETUP ({signal.score}/{signal.max_score})"

        # Checklist items
        def check(value: bool) -> str:
            return "\u2705" if value else "\u274C"  # Green check or red X

        # Format price based on instrument type
        # Gold and forex have different decimal places
        if "XAU" in signal.pair or "XAG" in signal.pair:
            price_fmt = ".2f"
        elif signal.pair.startswith("R_") or signal.pair.startswith("BOOM") or signal.pair.startswith("CRASH"):
            price_fmt = ".2f"
        else:
            price_fmt = ".5f"  # Forex pairs

        entry_str = f"{signal.entry:{price_fmt}}"
        sl_str = f"{signal.stop_loss:{price_fmt}}"
        tp1_str = f"{signal.tp1:{price_fmt}}"
        tp2_str = f"{signal.tp2:{price_fmt}}"

        # Current UTC time
        utc_now = datetime.now(pytz.UTC)
        datetime_str = utc_now.strftime("%Y-%m-%d %H:%M UTC")

        # Risk-reward ratios (using 1:2 RR system)
        rr1 = "1:2"
        rr2 = "1:3"

        # Determine timeframe based on pair
        if signal.pair == "R_75":
            timeframe = "H4"
        else:
            timeframe = "H1"

        # Candlestick patterns
        patterns_str = ", ".join(signal.candle_patterns) if signal.candle_patterns else "None"

        # Volume info
        vol_info = ""
        if signal.volume_analysis and signal.volume_analysis.has_volume:
            if signal.volume_analysis.is_volume_spike:
                vol_info = f"Spike ({signal.volume_analysis.volume_ratio:.1f}x)"
            else:
                vol_info = f"Normal"
        else:
            vol_info = "N/A"

        message = f"""
{direction_emoji} {direction_text} - {signal.display_name}
{stars} {grade_text}

\u2705 SIGNAL CONFIRMED \u2705

Timeframe: {timeframe}
\u27A1 Entry: {entry_str} (Limit Order)
Stop Loss: {sl_str}
Take Profit 1: {tp1_str} ({rr1} RR)
Take Profit 2: {tp2_str} ({rr2} RR)

Technical Checklist:
- Trend (EMA 200): {check(signal.checklist.get('ema_trend', False))}
- EMA Cross (50/200): {check(signal.checklist.get('ema_cross', False))}
- RSI Neutral Zone: {check(signal.checklist.get('rsi_neutral', False))}
- MACD Favorable: {check(signal.checklist.get('macd_favorable', False))}
- Stochastic: {check(signal.checklist.get('stochastic', False))}
- ADX Strong: {check(signal.checklist.get('adx_strong', False))}
- Bollinger Band: {check(signal.checklist.get('bb_confluence', False))}
- Divergence: {check(signal.checklist.get('divergence', False))}

SMC Checklist:
- Structure Aligned: {check(signal.checklist.get('structure_aligned', False))}
- Near Key Level: {check(signal.checklist.get('near_key_level', False))}
- Order Block: {check(signal.checklist.get('in_order_block', False))}
- Liquidity Safe: {check(signal.checklist.get('liquidity_safe', False))}

Candlestick Patterns: {patterns_str}
Volume: {vol_info}

Indicators: RSI {signal.rsi:.1f} | ADX {signal.adx:.1f}

\U0001F4CC Set {signal.direction} LIMIT order at {entry_str}
\u26A0 Risk 1-2% of your account
{datetime_str}
"""
        return message.strip()

    def send_message(self, message: str) -> bool:
        """
        Send a message to Telegram

        Args:
            message: The message text to send

        Returns:
            True if sent successfully, False otherwise
        """
        if self.dry_run:
            print("\n" + "=" * 60)
            print("[DRY RUN] Would send Telegram message:")
            print("=" * 60)
            # Handle Windows encoding issues with emojis
            try:
                print(message)
            except UnicodeEncodeError:
                # Remove emojis for console display
                import re
                clean_msg = re.sub(r'[^\x00-\x7F]+', '', message)
                print(clean_msg)
            print("=" * 60 + "\n")
            return True

        if not self.token or not self.chat_id:
            print("[TELEGRAM] Missing bot token or chat ID")
            return False

        try:
            url = self.API_URL.format(token=self.token)
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                print("[TELEGRAM] Message sent successfully")
                return True
            else:
                print(f"[TELEGRAM] API error: {result}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"[TELEGRAM] Request error: {e}")
            return False
        except Exception as e:
            print(f"[TELEGRAM] Error sending message: {e}")
            return False

    def send_signal(self, signal: SignalResult) -> bool:
        """
        Format and send a trading signal

        Args:
            signal: SignalResult object

        Returns:
            True if sent successfully, False otherwise
        """
        message = self.format_signal(signal)
        return self.send_message(message)

    def format_pre_signal(self, pre_signal: PreSignalResult) -> str:
        """
        Format a pre-signal (setup forming) into Telegram message
        """
        if pre_signal.direction == "BUY":
            direction_emoji = "\U0001F7E1"  # Yellow circle (pending)
            direction_text = "BUY SETUP FORMING"
        else:
            direction_emoji = "\U0001F7E0"  # Orange circle (pending)
            direction_text = "SELL SETUP FORMING"

        # Format prices
        if "XAU" in pre_signal.pair or "XAG" in pre_signal.pair:
            price_fmt = ".2f"
        elif pre_signal.pair.startswith("R_") or pre_signal.pair.startswith("BOOM") or pre_signal.pair.startswith("CRASH"):
            price_fmt = ".2f"
        else:
            price_fmt = ".5f"

        entry_str = f"{pre_signal.potential_entry:{price_fmt}}"
        sl_str = f"{pre_signal.potential_sl:{price_fmt}}"
        tp1_str = f"{pre_signal.potential_tp1:{price_fmt}}"
        tp2_str = f"{pre_signal.potential_tp2:{price_fmt}}"

        # Conditions met
        conditions_list = "\n".join([f"\u2705 {k}" for k in pre_signal.conditions_met.keys()])

        # Pending conditions
        pending_list = "\n".join([f"\u23F3 {p}" for p in pre_signal.conditions_pending]) if pre_signal.conditions_pending else "None"

        message = f"""
\u23F3 {direction_emoji} {direction_text}
{pre_signal.display_name}

\u26A0 PREPARE PENDING ORDER \u26A0

Confluence: {pre_signal.current_score}/{pre_signal.max_score} ({pre_signal.confluence_pct:.0f}%)

\U0001F4CD Potential Levels:
Entry: {entry_str}
Stop Loss: {sl_str}
TP1: {tp1_str}
TP2: {tp2_str}

\u2705 Conditions Met:
{conditions_list}

\u23F3 Still Needed:
{pending_list}

RSI: {pre_signal.rsi:.1f} | ADX: {pre_signal.adx:.1f}

\U0001F514 Set {pre_signal.direction} LIMIT at {entry_str}
\u23F0 Confirmation alert coming at candle close
"""
        return message.strip()

    def send_pre_signal(self, pre_signal: PreSignalResult) -> bool:
        """
        Send a pre-signal (setup forming) alert
        """
        message = self.format_pre_signal(pre_signal)
        return self.send_message(message)

    def send_heartbeat(self) -> bool:
        """
        Send a heartbeat message to confirm bot is running

        Returns:
            True if sent successfully, False otherwise
        """
        utc_now = datetime.now(pytz.UTC)
        message = f"""
\U0001F49A Signal Bot Heartbeat
\U0001F552 {utc_now.strftime("%Y-%m-%d %H:%M UTC")}

Bot is running and scanning for signals...
Next check in 4 hours.
"""
        return self.send_message(message.strip())

    def send_startup_message(self) -> bool:
        """
        Send a startup notification

        Returns:
            True if sent successfully
        """
        utc_now = datetime.now(pytz.UTC)

        # Count enabled instruments
        oanda_count = len([i for i in config.OANDA_INSTRUMENTS.values() if i.get("enabled")])
        deriv_count = len([i for i in config.DERIV_INSTRUMENTS.values() if i.get("enabled")])

        message = f"""
\U0001F680 Signal Bot Started!
\U0001F552 {utc_now.strftime("%Y-%m-%d %H:%M UTC")}

\U0001F4CA Monitoring:
- OANDA: {oanda_count} instruments
- Deriv: {deriv_count} instruments

\u23F0 Checking every 4 hours
\U0001F4DD Signals logged to CSV

Mode: {"DRY RUN (no alerts)" if self.dry_run else "LIVE"}
"""
        return self.send_message(message.strip())

    def test_connection(self) -> bool:
        """
        Test Telegram bot connection

        Returns:
            True if connection works
        """
        if self.dry_run:
            print("[TELEGRAM] Dry run mode - skipping connection test")
            return True

        try:
            url = f"https://api.telegram.org/bot{self.token}/getMe"
            response = requests.get(url, timeout=10)
            result = response.json()

            if result.get("ok"):
                bot_name = result["result"].get("username", "Unknown")
                print(f"[TELEGRAM] Connected as @{bot_name}")
                return True
            else:
                print(f"[TELEGRAM] Connection failed: {result}")
                return False

        except Exception as e:
            print(f"[TELEGRAM] Connection error: {e}")
            return False


# Test if run directly
if __name__ == "__main__":
    from signal_engine import SignalResult
    from datetime import datetime
    import pytz

    bot = TelegramBot()

    # Test with a sample signal
    sample_signal = SignalResult(
        pair="XAU_USD",
        display_name="XAU/USD (Gold)",
        direction="BUY",
        score=12,
        max_score=15,
        grade="A",
        entry=1950.50,
        stop_loss=1940.25,
        tp1=1960.75,
        tp2=1971.00,
        tp3=1985.00,
        atr=6.83,
        rsi=52.5,
        adx=28.5,
        macd_state="bullish",
        ema_trend=True,
        ema_cross=True,
        rsi_neutral=True,
        macd_favorable=True,
        adx_strong=True,
        structure_aligned=True,
        near_key_level=True,
        in_order_block=False,
        fvg_confluence=True,
        liquidity_safe=True,
        bb_confluence=True,
        candle_pattern_score=2,
        candle_patterns=["Bullish Engulfing", "Hammer"],
        volume_score=1,
        volume_analysis=None,
        session_active=True,
        session_name="London/NY Overlap",
        datetime_utc=datetime.now(pytz.UTC),
        checklist={
            "ema_trend": True,
            "ema_cross": True,
            "rsi_neutral": True,
            "macd_favorable": True,
            "adx_strong": True,
            "bb_confluence": True,
            "structure_aligned": True,
            "near_key_level": True,
            "in_order_block": False,
            "liquidity_safe": True,
            "candle_pattern": True,
            "volume_confirms": True,
            "session_active": True
        }
    )

    print("Testing signal format:\n")
    message = bot.format_signal(sample_signal)
    print(message)

    print("\n\nTesting send (will be dry run):")
    bot.send_signal(sample_signal)
