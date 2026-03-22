"""
Forex Signal Bot - Configuration
================================
All settings and instrument configurations
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ===========================================
# API CREDENTIALS
# ===========================================

# OANDA (Forex & Metals)
OANDA_API_KEY = os.getenv("OANDA_API_KEY", "")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "")
OANDA_ENVIRONMENT = os.getenv("OANDA_ENVIRONMENT", "practice")  # 'practice' or 'live'

# DERIV (Synthetics)
DERIV_API_TOKEN = os.getenv("DERIV_API_TOKEN", "")
DERIV_APP_ID = os.getenv("DERIV_APP_ID", "1089")

# TELEGRAM
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ===========================================
# BOT SETTINGS
# ===========================================

DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
TIMEFRAME = "H1"  # H1 for R_10, R_25, R_100
CANDLES_TO_FETCH = 200  # Number of candles to fetch for indicator calculation
MIN_SCORE_TO_ALERT = 4  # Minimum confluence score to send alert (4 or 5)

# ===========================================
# TRADING SESSIONS (UTC)
# ===========================================

SESSIONS = {
    "london": {"start": 7, "end": 16},    # 07:00 - 16:00 UTC
    "new_york": {"start": 13, "end": 22}  # 13:00 - 22:00 UTC
}

# ===========================================
# INDICATOR SETTINGS (ENHANCED)
# ===========================================

INDICATORS = {
    # EMAs
    "ema_fast": 50,
    "ema_slow": 200,
    "ema_slope_period": 5,  # NEW: Check EMA slope over 5 candles

    # RSI - BALANCED: Good win rate + enough signals
    "rsi_period": 14,
    "rsi_neutral_low": 45,  # Balanced setting
    "rsi_neutral_high": 55,  # Balanced setting
    "rsi_oversold": 30,
    "rsi_overbought": 70,

    # MACD
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,

    # ATR
    "atr_period": 14,

    # ADX - Trend Strength
    "adx_period": 14,
    "adx_threshold": 20,  # Standard threshold for trending market

    # Bollinger Bands
    "bb_period": 20,
    "bb_std": 2.0,

    # Stochastic Oscillator
    "stoch_k": 14,
    "stoch_d": 3,
    "stoch_smooth": 3,
    "stoch_oversold": 20,
    "stoch_overbought": 80,

    # Candle Confirmation
    "min_candle_body_percent": 40,  # Candle body must be 40% of total range

    # Divergence Detection
    "divergence_lookback": 20,  # Number of candles to look back for divergence
}

# ===========================================
# INSTRUMENTS CONFIGURATION
# ===========================================

# OANDA Forex & Metals
# Set 'enabled' to True/False to include/exclude
OANDA_INSTRUMENTS = {
    # Metals
    "XAU_USD": {
        "display_name": "XAU/USD (Gold)",
        "enabled": True,
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": True,
        "reversal_mode": True
    },
    "XAG_USD": {
        "display_name": "XAG/USD (Silver)",
        "enabled": True,
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": True,
        "reversal_mode": True
    },
    # Major Pairs
    "EUR_USD": {
        "display_name": "EUR/USD",
        "enabled": True,
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": True,
        "reversal_mode": True
    },
    "GBP_USD": {
        "display_name": "GBP/USD",
        "enabled": True,
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": True,
        "reversal_mode": True
    },
    "USD_JPY": {
        "display_name": "USD/JPY",
        "enabled": True,
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": True,
        "reversal_mode": True
    },
    "USD_CHF": {
        "display_name": "USD/CHF",
        "enabled": False,
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": True
    },
    "AUD_USD": {
        "display_name": "AUD/USD",
        "enabled": False,
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": True
    },
    "USD_CAD": {
        "display_name": "USD/CAD",
        "enabled": False,
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": True
    },
    "NZD_USD": {
        "display_name": "NZD/USD",
        "enabled": False,
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": True
    },
    # Cross Pairs
    "EUR_GBP": {
        "display_name": "EUR/GBP",
        "enabled": False,
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": True
    },
    "EUR_JPY": {
        "display_name": "EUR/JPY",
        "enabled": False,
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": True
    },
    "GBP_JPY": {
        "display_name": "GBP/JPY",
        "enabled": True,
        "atr_multiplier_sl": 2.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 4.0,
        "use_session_filter": True,
        "reversal_mode": True
    },
}

# DERIV Synthetics
# Set 'enabled' to True/False to include/exclude
DERIV_INSTRUMENTS = {
    # ===== FOREX ON DERIV =====
    "frxXAUUSD": {
        "display_name": "XAU/USD (Gold)",
        "enabled": True,  # H4: 100% WR with BOS + 65% confluence
        "atr_multiplier_sl": 1.0,
        "atr_multiplier_tp1": 3.0,  # 1:3 RR for Gold - optimal
        "atr_multiplier_tp2": 4.0,
        "use_session_filter": True,
        "min_confluence": 0.65,  # 65% confluence on H4
        "timeframe": "H4",  # H4 for clearer SMC structure
        "require_bos": True,  # Require Break of Structure - 100% WR filter
        "reversal_mode": True
    },
    "frxXAGUSD": {
        "display_name": "XAG/USD (Silver)",
        "enabled": False,  # Disabled - poor WR (30-33%) with current strategy
        "atr_multiplier_sl": 1.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": True,
        "timeframe": "H1",
        "reversal_mode": True
    },
    # ===== CRYPTOCURRENCY =====
    "cryBTCUSD": {
        "display_name": "BTC/USD (Bitcoin)",
        "enabled": True,  # H4: 70% WR, PF 2.33 with Daily MTF alignment
        "atr_multiplier_sl": 1.0,
        "atr_multiplier_tp1": 2.0,  # 1:2 RR optimal
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": False,  # 24/7 market
        "min_confluence": 0.70,  # 70% confluence - sweet spot
        "timeframe": "H4",  # H4 timeframe
        "require_bos": False,
        "reversal_mode": False,
        "use_daily_mtf_confirmation": True  # Daily EMA50/200 alignment required
    },
    # ===== PROFITABLE VOLATILITY INDICES =====
    "R_10": {
        "display_name": "Volatility 10 Index",
        "enabled": True,
        "atr_multiplier_sl": 1.0,
        "atr_multiplier_tp1": 2.0,  # 1:2 RR
        "atr_multiplier_tp2": 3.0,  # 1:3 RR
        "use_session_filter": False,
        "min_confluence": 0.75,  # 75% confluence - 100% WR on SELL
        "require_bos": False,
        "reversal_mode": False,
        "allowed_directions": "SELL_ONLY"  # BUY fails even with 10/12 + BOS
    },
    "R_50": {
        "display_name": "Volatility 50 Index",
        "enabled": True,  # 56.1% WR, PF 1.41 - PROFITABLE
        "atr_multiplier_sl": 1.0,   # Tighter SL
        "atr_multiplier_tp1": 2.0,  # 1:2 RR
        "atr_multiplier_tp2": 3.0,  # 1:3 RR
        "use_session_filter": False,
        "min_confluence": 0.85,  # R_50 needs stricter filtering (85%)
        "reversal_mode": False,  # Disabled - 23.5% WR on reversals
        "use_mtf_confirmation": True  # H4 trend must align with H1 signal
    },
    "R_100": {
        "display_name": "Volatility 100 Index",
        "enabled": True,
        "atr_multiplier_sl": 1.0,
        "atr_multiplier_tp1": 2.0,  # 1:2 RR
        "atr_multiplier_tp2": 3.0,  # 1:3 RR
        "use_session_filter": False,
        "min_confluence": 0.85,  # 85% confluence - 66.7% WR, PF 4.62
        "require_bos": True,  # Require BOS - prevents ranging market losses
        "reversal_mode": True
    },
    # ===== UNPROFITABLE - DISABLED =====
    "R_15": {
        "display_name": "Volatility 15 Index",
        "enabled": False,  # Testing
        "atr_multiplier_sl": 1.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": False,
        "min_confluence": 0.70
    },
    "R_25": {
        "display_name": "Volatility 25 Index",
        "enabled": False,  # 33.3% WR - NOT PROFITABLE
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 2.5,
        "use_session_filter": False
    },
    "R_30": {
        "display_name": "Volatility 30 Index",
        "enabled": False,  # Testing
        "atr_multiplier_sl": 1.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": False,
        "min_confluence": 0.70
    },
    "R_75": {
        "display_name": "Volatility 75 Index",
        "enabled": False,  # 0 signals at 80% confluence - DISABLED
        "min_grade": "A",
        "atr_multiplier_sl": 2.0,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 2.5,
        "use_session_filter": False
    },
    "R_90": {
        "display_name": "Volatility 90 Index",
        "enabled": False,  # Testing
        "atr_multiplier_sl": 1.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": False,
        "min_confluence": 0.70
    },
    # ===== BOOM INDICES - MOSTLY UNPROFITABLE =====
    "BOOM300N": {
        "display_name": "Boom 300 Index",
        "enabled": False,  # 0 signals in backtest
        "atr_multiplier_sl": 2.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 4.0,
        "use_session_filter": False
    },
    "BOOM500": {
        "display_name": "Boom 500 Index",
        "enabled": False,  # 52.4% WR, PF 1.05 - marginal
        "atr_multiplier_sl": 2.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 4.0,
        "use_session_filter": False
    },
    "BOOM1000": {
        "display_name": "Boom 1000 Index",
        "enabled": False,  # 41.7% WR - NOT PROFITABLE
        "atr_multiplier_sl": 2.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 4.0,
        "use_session_filter": False
    },
    # ===== CRASH INDICES =====
    "CRASH300N": {
        "display_name": "Crash 300 Index",
        "enabled": False,  # 50% WR - marginal
        "atr_multiplier_sl": 2.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 4.0,
        "use_session_filter": False
    },
    "CRASH500": {
        "display_name": "Crash 500 Index",
        "enabled": False,  # 43.5% WR - NOT PROFITABLE
        "atr_multiplier_sl": 2.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 4.0,
        "use_session_filter": False
    },
    "CRASH1000": {
        "display_name": "Crash 1000 Index",
        "enabled": False,  # 0 signals at 80% confluence - DISABLED
        "atr_multiplier_sl": 2.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 4.0,
        "use_session_filter": False
    },
    # Step Index
    "STPINDEX": {
        "display_name": "Step Index",
        "enabled": False,
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": False
    },
    # ===== 1-SECOND VOLATILITY INDICES =====
    # DISABLED: Backtested on M5 - NOT PROFITABLE (30-46% win rate)
    # Our strategy is optimized for H1/H4 timeframes only
    "1HZ10V": {
        "display_name": "Volatility 10 (1s)",
        "enabled": False,  # 30% win rate on M5 - DO NOT USE
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 2.5,
        "use_session_filter": False
    },
    "1HZ25V": {
        "display_name": "Volatility 25 (1s)",
        "enabled": False,  # 46% win rate on M5 - DO NOT USE
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 2.5,
        "use_session_filter": False
    },
    "1HZ50V": {
        "display_name": "Volatility 50 (1s)",
        "enabled": False,  # NOT TESTED - likely unprofitable
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 2.5,
        "use_session_filter": False
    },
    "1HZ75V": {
        "display_name": "Volatility 75 (1s)",
        "enabled": False,  # 41% win rate on M5 - DO NOT USE
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 2.5,
        "use_session_filter": False
    },
    "1HZ100V": {
        "display_name": "Volatility 100 (1s)",
        "enabled": False,  # NOT TESTED - likely unprofitable
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 1.5,
        "atr_multiplier_tp2": 2.5,
        "use_session_filter": False
    },
    # ===== DERIV FOREX PAIRS =====
    "frxEURUSD": {
        "display_name": "EUR/USD (Deriv)",
        "enabled": False,  # Testing
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": True,
        "min_confluence": 0.70
    },
    "frxGBPUSD": {
        "display_name": "GBP/USD (Deriv)",
        "enabled": False,  # Testing
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": True,
        "min_confluence": 0.70
    },
    "frxGBPJPY": {
        "display_name": "GBP/JPY (Deriv)",
        "enabled": False,  # Testing
        "atr_multiplier_sl": 2.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 4.0,
        "use_session_filter": True,
        "min_confluence": 0.70
    },
    "frxUSDJPY": {
        "display_name": "USD/JPY (Deriv)",
        "enabled": False,  # Testing
        "atr_multiplier_sl": 1.5,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": True,
        "min_confluence": 0.70
    },
    # ===== JUMP INDICES =====
    "JD10": {
        "display_name": "Jump 10 Index",
        "enabled": False,  # Testing
        "atr_multiplier_sl": 1.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": False,
        "min_confluence": 0.70
    },
    "JD25": {
        "display_name": "Jump 25 Index",
        "enabled": False,  # Testing
        "atr_multiplier_sl": 1.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": False,
        "min_confluence": 0.70
    },
    "JD50": {
        "display_name": "Jump 50 Index",
        "enabled": False,  # Testing
        "atr_multiplier_sl": 1.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": False,
        "min_confluence": 0.70
    },
    "JD75": {
        "display_name": "Jump 75 Index",
        "enabled": False,  # Testing
        "atr_multiplier_sl": 1.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": False,
        "min_confluence": 0.70
    },
    "JD100": {
        "display_name": "Jump 100 Index",
        "enabled": False,  # Testing
        "atr_multiplier_sl": 1.0,
        "atr_multiplier_tp1": 2.0,
        "atr_multiplier_tp2": 3.0,
        "use_session_filter": False,
        "min_confluence": 0.70
    },
}

# ===========================================
# SCHEDULER SETTINGS
# ===========================================

# Times to run signal check (UTC hours)
# Check every hour for H1 candle closes
SCHEDULE_HOURS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]

# ===========================================
# LOGGING
# ===========================================

LOG_FILE = "logs/signals.csv"
LOG_COLUMNS = [
    "datetime",
    "pair",
    "direction",
    "score",
    "grade",
    "entry",
    "stop_loss",
    "tp1",
    "tp2",
    "session",
    "rsi",
    "macd_state",
    "ema_trend",
    "ema_cross"
]
