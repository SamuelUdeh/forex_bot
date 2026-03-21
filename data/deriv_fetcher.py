"""
Deriv Data Fetcher
==================
Fetches historical candle data from Deriv WebSocket API for Synthetics
"""

import pandas as pd
import asyncio
import json
import websockets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import config


class DerivFetcher:
    """Fetches price data from Deriv WebSocket API"""

    WEBSOCKET_URL = "wss://ws.binaryws.com/websockets/v3?app_id={app_id}"

    # Granularity mapping for Deriv API
    GRANULARITY_MAP = {
        "M1": 60,
        "M5": 300,
        "M15": 900,
        "M30": 1800,
        "H1": 3600,
        "H4": 14400,
        "D": 86400
    }

    def __init__(self):
        """Initialize Deriv API settings"""
        self.api_token = config.DERIV_API_TOKEN
        self.app_id = config.DERIV_APP_ID
        self.ws_url = self.WEBSOCKET_URL.format(app_id=self.app_id)

    async def _fetch_candles_async(
        self,
        symbol: str,
        granularity: str = "H4",
        count: int = 200
    ) -> Optional[pd.DataFrame]:
        """
        Async method to fetch candles via WebSocket

        Args:
            symbol: Deriv symbol (e.g., 'R_75', 'BOOM300N')
            granularity: Timeframe
            count: Number of candles

        Returns:
            DataFrame with OHLC data or None
        """
        try:
            granularity_seconds = self.GRANULARITY_MAP.get(granularity, 14400)

            # Calculate start time
            end_time = int(datetime.utcnow().timestamp())
            start_time = end_time - (count * granularity_seconds)

            async with websockets.connect(self.ws_url) as ws:
                # Skip auth for public data (volatility indices are public)
                # Auth only needed for account-specific operations

                # Request candle history
                candles_request = {
                    "ticks_history": symbol,
                    "adjust_start_time": 1,
                    "count": count,
                    "end": "latest",
                    "granularity": granularity_seconds,
                    "style": "candles"
                }

                await ws.send(json.dumps(candles_request))
                response = await ws.recv()
                data = json.loads(response)

                if "error" in data:
                    print(f"[DERIV] Error for {symbol}: {data['error']['message']}")
                    return None

                candles = data.get("candles", [])

                if not candles:
                    print(f"[DERIV] No candles returned for {symbol}")
                    return None

                # Parse candles into DataFrame
                df_data = []
                for candle in candles:
                    df_data.append({
                        "datetime": pd.to_datetime(candle["epoch"], unit="s", utc=True),
                        "open": float(candle["open"]),
                        "high": float(candle["high"]),
                        "low": float(candle["low"]),
                        "close": float(candle["close"])
                    })

                df = pd.DataFrame(df_data)
                df.set_index("datetime", inplace=True)
                df = df.sort_index()

                # Remove the last candle if it's incomplete
                if len(df) > 1:
                    df = df.iloc[:-1]

                print(f"[DERIV] Fetched {len(df)} candles for {symbol}")
                return df

        except Exception as e:
            print(f"[DERIV] Error fetching {symbol}: {e}")
            return None

    def get_candles(
        self,
        symbol: str,
        granularity: str = "H4",
        count: int = 200
    ) -> Optional[pd.DataFrame]:
        """
        Synchronous wrapper to fetch candles

        Args:
            symbol: Deriv symbol (e.g., 'R_75', 'BOOM300N')
            granularity: Timeframe
            count: Number of candles

        Returns:
            DataFrame with OHLC data or None
        """
        try:
            # Run async function in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self._fetch_candles_async(symbol, granularity, count)
                )
                return result
            finally:
                loop.close()
        except Exception as e:
            print(f"[DERIV] Error in get_candles: {e}")
            return None

    async def _get_current_price_async(self, symbol: str) -> Optional[float]:
        """
        Async method to get current price

        Args:
            symbol: Deriv symbol

        Returns:
            Current price or None
        """
        try:
            async with websockets.connect(self.ws_url) as ws:
                # Request tick
                tick_request = {
                    "ticks": symbol,
                    "subscribe": 0  # Don't subscribe, just get one tick
                }

                await ws.send(json.dumps(tick_request))
                response = await ws.recv()
                data = json.loads(response)

                if "error" in data:
                    print(f"[DERIV] Error getting price for {symbol}: {data['error']['message']}")
                    return None

                tick = data.get("tick", {})
                return float(tick.get("quote", 0))

        except Exception as e:
            print(f"[DERIV] Error getting price for {symbol}: {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Synchronous wrapper to get current price

        Args:
            symbol: Deriv symbol

        Returns:
            Current price or None
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self._get_current_price_async(symbol)
                )
                return result
            finally:
                loop.close()
        except Exception as e:
            print(f"[DERIV] Error in get_current_price: {e}")
            return None

    def get_enabled_instruments(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all enabled Deriv instruments from config

        Returns:
            Dictionary of enabled instruments with their settings
        """
        return {
            symbol: settings
            for symbol, settings in config.DERIV_INSTRUMENTS.items()
            if settings.get("enabled", False)
        }

    def test_connection(self) -> bool:
        """
        Test API connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            async def _test():
                async with websockets.connect(self.ws_url, close_timeout=10) as ws:
                    # Simple ping with timeout
                    await ws.send(json.dumps({"ping": 1}))
                    response = await asyncio.wait_for(ws.recv(), timeout=15)
                    data = json.loads(response)
                    return "pong" in data

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(asyncio.wait_for(_test(), timeout=20))
                if result:
                    print("[DERIV] Connection successful")
                return result
            finally:
                loop.close()

        except asyncio.TimeoutError:
            print("[DERIV] Connection timeout - will retry during scan")
            return False
        except Exception as e:
            print(f"[DERIV] Connection test failed: {e}")
            return False


# Test the fetcher if run directly
if __name__ == "__main__":
    fetcher = DerivFetcher()

    if fetcher.test_connection():
        # Test fetching V75 data
        df = fetcher.get_candles("R_75", "H4", 50)
        if df is not None:
            print("\nSample data:")
            print(df.tail())

        # Test current price
        price = fetcher.get_current_price("R_75")
        if price:
            print(f"\nCurrent R_75 price: {price}")
