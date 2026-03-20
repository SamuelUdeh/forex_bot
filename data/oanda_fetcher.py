"""
OANDA Data Fetcher
==================
Fetches historical candle data from OANDA API for Forex and Metals
"""

import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any
import oandapyV20
import oandapyV20.endpoints.instruments as instruments
from oandapyV20.exceptions import V20Error

import config


class OandaFetcher:
    """Fetches price data from OANDA API"""

    def __init__(self):
        """Initialize OANDA API client"""
        self.api_key = config.OANDA_API_KEY
        self.account_id = config.OANDA_ACCOUNT_ID
        self.environment = config.OANDA_ENVIRONMENT

        # Set API URL based on environment
        if self.environment == "live":
            self.api_url = "https://api-fxtrade.oanda.com"
        else:
            self.api_url = "https://api-fxpractice.oanda.com"

        # Initialize client
        self.client = oandapyV20.API(
            access_token=self.api_key,
            environment=self.environment
        )

    def get_candles(
        self,
        instrument: str,
        granularity: str = "H4",
        count: int = 200
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical candles for an instrument

        Args:
            instrument: OANDA instrument name (e.g., 'XAU_USD', 'EUR_USD')
            granularity: Timeframe (M1, M5, M15, M30, H1, H4, D, W, M)
            count: Number of candles to fetch (max 5000)

        Returns:
            DataFrame with columns: datetime, open, high, low, close, volume
            Returns None if fetch fails
        """
        try:
            params = {
                "granularity": granularity,
                "count": count,
                "price": "M"  # Midpoint prices
            }

            request = instruments.InstrumentsCandles(
                instrument=instrument,
                params=params
            )

            response = self.client.request(request)
            candles = response.get("candles", [])

            if not candles:
                print(f"[OANDA] No candles returned for {instrument}")
                return None

            # Parse candles into DataFrame
            data = []
            for candle in candles:
                if candle.get("complete", False):  # Only use complete candles
                    mid = candle.get("mid", {})
                    data.append({
                        "datetime": pd.to_datetime(candle["time"]),
                        "open": float(mid.get("o", 0)),
                        "high": float(mid.get("h", 0)),
                        "low": float(mid.get("l", 0)),
                        "close": float(mid.get("c", 0)),
                        "volume": int(candle.get("volume", 0))
                    })

            if not data:
                print(f"[OANDA] No complete candles for {instrument}")
                return None

            df = pd.DataFrame(data)
            df.set_index("datetime", inplace=True)
            df = df.sort_index()

            print(f"[OANDA] Fetched {len(df)} candles for {instrument}")
            return df

        except V20Error as e:
            print(f"[OANDA] API Error for {instrument}: {e}")
            return None
        except Exception as e:
            print(f"[OANDA] Error fetching {instrument}: {e}")
            return None

    def get_current_price(self, instrument: str) -> Optional[float]:
        """
        Get current mid price for an instrument

        Args:
            instrument: OANDA instrument name

        Returns:
            Current price or None if fetch fails
        """
        try:
            params = {
                "granularity": "M1",
                "count": 1,
                "price": "M"
            }

            request = instruments.InstrumentsCandles(
                instrument=instrument,
                params=params
            )

            response = self.client.request(request)
            candles = response.get("candles", [])

            if candles:
                mid = candles[-1].get("mid", {})
                return float(mid.get("c", 0))

            return None

        except Exception as e:
            print(f"[OANDA] Error getting price for {instrument}: {e}")
            return None

    def get_enabled_instruments(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all enabled OANDA instruments from config

        Returns:
            Dictionary of enabled instruments with their settings
        """
        return {
            symbol: settings
            for symbol, settings in config.OANDA_INSTRUMENTS.items()
            if settings.get("enabled", False)
        }

    def test_connection(self) -> bool:
        """
        Test API connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to fetch 1 candle from EUR_USD
            params = {"granularity": "H1", "count": 1, "price": "M"}
            request = instruments.InstrumentsCandles(
                instrument="EUR_USD",
                params=params
            )
            self.client.request(request)
            print("[OANDA] Connection successful")
            return True
        except Exception as e:
            print(f"[OANDA] Connection failed: {e}")
            return False


# Test the fetcher if run directly
if __name__ == "__main__":
    fetcher = OandaFetcher()

    if fetcher.test_connection():
        # Test fetching Gold data
        df = fetcher.get_candles("XAU_USD", "H4", 50)
        if df is not None:
            print("\nSample data:")
            print(df.tail())
