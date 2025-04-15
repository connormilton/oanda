"""
Data Collection Module
Handles market and account data collection from OANDA API
"""

import logging
import pandas as pd
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("CollaborativeTrader")

class DataCollector:
    """Collects market and account data"""
    
    def __init__(self, oanda_client):
        self.oanda = oanda_client
    
    def get_account_data(self):
        """Get account information"""
        try:
            account = self.oanda.get_account()
            
            # Format account data similar to previous format
            return {
                'accountId': account.get('id', ''),
                'accountName': account.get('alias', 'Trading Account'),
                'accountType': 'OANDA',
                'balance': float(account.get('balance', 0)),
                'available': float(account.get('marginAvailable', 0)),
                'currency': account.get('currency', 'USD'),
                'profitLoss': float(account.get('unrealizedPL', 0)),
                'marginUsed': float(account.get('marginUsed', 0))
            }
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return {}
    
    def get_positions(self):
        """Get open positions"""
        try:
            return self.oanda.get_open_positions()
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return pd.DataFrame()
    
    def get_market_data(self, epic, timeframes=None):
        """Collect market data for an instrument"""
        if timeframes is None:
            timeframes = {
                "m15": {"granularity": "M15", "count": 96},  # 24 hours (4 candles per hour)
                "h1": {"granularity": "H1", "count": 48},    # 2 days (24 hours per day)
                "h4": {"granularity": "H4", "count": 30}     # 5 days (6 candles per day)
            }
        
        # Convert IG epic to OANDA instrument
        from utils.oanda_connector import convert_ig_epic_to_oanda
        instrument = convert_ig_epic_to_oanda(epic)
        
        results = {}
        
        try:
            for key, config in timeframes.items():
                granularity = config["granularity"]
                count = config["count"]
                
                # Get candle data from OANDA
                candles = self.oanda.get_candles(
                    instrument=instrument,
                    granularity=granularity,
                    count=count
                )
                
                if not candles:
                    continue
                
                # Convert to standardized format
                data = []
                for candle in candles:
                    if candle.get("complete", False):  # Only include complete candles
                        mid = candle.get("mid", {})
                        data.append({
                            "timestamp": candle.get("time"),
                            "open": float(mid.get("o", 0)),
                            "high": float(mid.get("h", 0)),
                            "low": float(mid.get("l", 0)),
                            "close": float(mid.get("c", 0)),
                            "volume": int(candle.get("volume", 0))
                        })
                
                results[key] = data
            
            # Add current price snapshot
            snapshot = self.get_price_snapshot(epic)
            if snapshot:
                results["current"] = snapshot
                
            return results
        except Exception as e:
            logger.error(f"Error collecting market data for {epic}: {e}")
            return {}
    
    def get_price_snapshot(self, epic):
        """Get current market price snapshot"""
        try:
            # Convert IG epic to OANDA instrument
            from utils.oanda_connector import convert_ig_epic_to_oanda
            instrument = convert_ig_epic_to_oanda(epic)
            
            # Get price data
            price_data = self.oanda.get_price(instrument)
            
            if price_data:
                # Extract bid/ask prices
                bid = float(price_data.get("bids", [{}])[0].get("price", 0)) if price_data.get("bids") else None
                ask = float(price_data.get("asks", [{}])[0].get("price", 0)) if price_data.get("asks") else None
                
                return {
                    "bid": bid,
                    "offer": ask,  # OANDA uses "ask", IG uses "offer"
                    "epic": epic,
                    "instrument": instrument,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            return None
        except Exception as e:
            logger.error(f"Error getting snapshot for {epic}: {e}")
            return None
    
    def get_available_instruments(self):
        """Get all available instruments"""
        try:
            instruments = self.oanda.get_account_instruments()
            return instruments
        except Exception as e:
            logger.error(f"Error getting instruments: {e}")
            return []
            
    def convert_oanda_instrument_to_ig_epic(self, instrument):
        """Convert OANDA instrument to IG epic format
        
        Args:
            instrument (str): OANDA instrument name (e.g. EUR_USD)
            
        Returns:
            str: IG epic format
        """
        # Check if instrument has OANDA format (XXX_YYY)
        if "_" in instrument:
            base, quote = instrument.split("_")
            return f"CS.D.{base}{quote}.TODAY.IP"
        
        # Return original if not in standard format
        return instrument