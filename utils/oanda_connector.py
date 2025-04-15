"""
OANDA API Connection Utilities
Handles connections to OANDA platform for trading and data retrieval
"""

import os
import logging
import requests
import json
from datetime import datetime, timezone
import pandas as pd

logger = logging.getLogger("CollaborativeTrader")

class OandaAPI:
    """OANDA API connector for forex trading"""
    
    def __init__(self, practice=True):
        """Initialize OANDA API connector
        
        Args:
            practice (bool): If True, use practice account, else use live account
        """
        self.practice = practice
        
        # Set base URL based on account type
        if practice:
            self.base_url = "https://api-fxpractice.oanda.com"
        else:
            self.base_url = "https://api-fxtrade.oanda.com"
            
        # Set API token from environment variables
        self.api_token = os.getenv("OANDA_API_TOKEN")
        if not self.api_token:
            raise ValueError("OANDA_API_TOKEN environment variable not set")
            
        # Set account ID from environment variables
        self.account_id = os.getenv("OANDA_ACCOUNT_ID")
        if not self.account_id:
            raise ValueError("OANDA_ACCOUNT_ID environment variable not set")
            
        # Set default headers for all requests
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        # Test connection
        self.test_connection()
        
    def test_connection(self):
        """Test connection to OANDA API"""
        try:
            # Try to get account details to test connection
            accounts = self.get_accounts()
            logger.info(f"OANDA API connected successfully. Found {len(accounts)} accounts.")
            
            # Get active account details
            if self.account_id in [acc["id"] for acc in accounts]:
                logger.info(f"Using OANDA account ID: {self.account_id}")
                
                # Get account details
                account = self.get_account()
                currency = account.get("currency", "Unknown")
                balance = account.get("balance", "Unknown")
                logger.info(f"Account balance: {balance} {currency}")
            else:
                available_accounts = [acc["id"] for acc in accounts]
                logger.warning(f"Specified account ID {self.account_id} not found in available accounts: {available_accounts}")
        except Exception as e:
            logger.error(f"OANDA connection error: {e}")
            raise
    
    def _make_request(self, method, endpoint, params=None, data=None):
        """Make request to OANDA API
        
        Args:
            method (str): HTTP method (GET, POST, PUT, etc.)
            endpoint (str): API endpoint to call
            params (dict, optional): Query parameters
            data (dict, optional): Request body data
            
        Returns:
            dict: Response data
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data
            )
            
            # Raise exception for HTTP errors
            response.raise_for_status()
            
            # Return response data
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Log error details from response
            error_details = {}
            try:
                error_details = response.json()
            except:
                error_details = {"text": response.text}
                
            logger.error(f"OANDA API HTTP error: {e}")
            logger.error(f"Error details: {error_details}")
            raise
        except Exception as e:
            logger.error(f"OANDA API request error: {e}")
            raise
    
    def get_accounts(self):
        """Get all accounts for the current token
        
        Returns:
            list: List of account objects
        """
        response = self._make_request("GET", "/v3/accounts")
        return response.get("accounts", [])
    
    def get_account(self):
        """Get account details
        
        Returns:
            dict: Account details
        """
        response = self._make_request("GET", f"/v3/accounts/{self.account_id}/summary")
        return response.get("account", {})
    
    def get_account_instruments(self):
        """Get available instruments for the account
        
        Returns:
            list: List of available instruments
        """
        response = self._make_request("GET", f"/v3/accounts/{self.account_id}/instruments")
        return response.get("instruments", [])
    
    def get_candles(self, instrument, granularity="H1", count=100):
        """Get candle data for an instrument
        
        Args:
            instrument (str): Instrument name (e.g., "EUR_USD")
            granularity (str): Candle granularity (e.g., "M5", "H1", "D")
            count (int): Number of candles to retrieve
            
        Returns:
            list: List of candle data
        """
        params = {
            "granularity": granularity,
            "count": count,
            "price": "M"  # Midpoint candles
        }
        
        response = self._make_request(
            "GET",
            f"/v3/instruments/{instrument}/candles",
            params=params
        )
        
        return response.get("candles", [])
    
    def get_price(self, instrument):
        """Get current price for an instrument
        
        Args:
            instrument (str): Instrument name (e.g., "EUR_USD")
            
        Returns:
            dict: Price data
        """
        params = {
            "instruments": instrument
        }
        
        response = self._make_request(
            "GET", 
            f"/v3/accounts/{self.account_id}/pricing",
            params=params
        )
        
        prices = response.get("prices", [])
        return prices[0] if prices else {}
    
    def get_open_positions(self):
        """Get all open positions
        
        Returns:
            DataFrame: DataFrame of open positions
        """
        try:
            response = self._make_request("GET", f"/v3/accounts/{self.account_id}/openPositions")
            positions = response.get("positions", [])
            
            # Convert to pandas DataFrame similar to IG API format
            if positions:
                data = []
                for position in positions:
                    try:
                        instrument = position["instrument"]
                        
                        # Get long and short units
                        long_units = int(position.get("long", {}).get("units", 0)) if position.get("long") else 0
                        short_units = int(position.get("short", {}).get("units", 0)) if position.get("short") else 0
                        
                        direction = "BUY" if long_units > 0 else "SELL"
                        units = long_units if long_units > 0 else abs(short_units)
                        
                        # Get position details based on direction
                        pos_details = position.get("long", {}) if direction == "BUY" else position.get("short", {})
                        
                        # Use position ID or generate a unique ID if not present
                        deal_id = position.get("id", f"position_{instrument}_{direction}")
                        
                        data.append({
                            "dealId": deal_id,
                            "epic": instrument,
                            "direction": direction,
                            "size": units,
                            "level": float(pos_details.get("averagePrice", 0)),
                            "profit": float(pos_details.get("unrealizedPL", 0)),
                            "currency": position.get("pl", "").split(" ")[1] if " " in position.get("pl", "") else "USD"
                        })
                    except Exception as position_error:
                        logger.error(f"Error processing position: {position_error}")
                        continue
                
                return pd.DataFrame(data)
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return pd.DataFrame()
    
    def create_order(self, instrument, units, price=None, stop_loss=None, take_profit=None):
        """Create a new order
        
        Args:
            instrument (str): Instrument name (e.g., "EUR_USD")
            units (int): Number of units (positive for buy, negative for sell)
            price (float, optional): Limit price (if None, market order)
            stop_loss (float, optional): Stop loss price
            take_profit (float, optional): Take profit price
            
        Returns:
            dict: Order details
        """
        # IMPORTANT: OANDA requires whole number of units, so convert to standard lots (100,000 units)
        # Convert size (in lots) to units
        # For example: 0.01 lots = 1,000 units, 0.1 lots = 10,000 units, 1 lot = 100,000 units
        # Minimum is 1 unit
        
        # First check if units is already an integer (proper format)
        if not isinstance(units, int):
            # Convert from lot size to actual units
            try:
                # Convert to float first to handle strings
                float_units = float(units)
                
                # Convert to whole units (1 lot = 100,000 units)
                units_as_int = int(float_units * 100000)
                
                # Ensure we have at least 1 unit
                if abs(units_as_int) < 1:
                    units_as_int = 1 if units_as_int >= 0 else -1
                    
                units = units_as_int
                logger.info(f"Converted lot size {float_units} to {units} units")
            except (ValueError, TypeError) as e:
                logger.error(f"Could not convert units to integer: {e}")
                units = 1 if units > 0 else -1  # Default to minimum
        
        # Build order request
        order_data = {
            "order": {
                "instrument": instrument,
                "units": str(units),
                "timeInForce": "FOK",  # Fill or Kill
                "positionFill": "DEFAULT"
            }
        }
        
        # Determine order type
        if price is None:
            order_data["order"]["type"] = "MARKET"
        else:
            order_data["order"]["type"] = "LIMIT"
            order_data["order"]["price"] = str(price)
        
        # Add stop loss if provided
        if stop_loss is not None:
            order_data["order"]["stopLossOnFill"] = {
                "price": str(stop_loss),
                "timeInForce": "GTC"  # Good Till Cancelled
            }
        
        # Add take profit if provided
        if take_profit is not None:
            order_data["order"]["takeProfitOnFill"] = {
                "price": str(take_profit),
                "timeInForce": "GTC"  # Good Till Cancelled
            }
        
        # Submit order
        response = self._make_request(
            "POST",
            f"/v3/accounts/{self.account_id}/orders",
            data=order_data
        )
        
        return response
    
    def close_position(self, instrument):
        """Close a position for an instrument
        
        Args:
            instrument (str): Instrument name (e.g., "EUR_USD")
            
        Returns:
            dict: Close position response
        """
        data = {
            "longUnits": "ALL",
            "shortUnits": "ALL"
        }
        
        response = self._make_request(
            "PUT",
            f"/v3/accounts/{self.account_id}/positions/{instrument}/close",
            data=data
        )
        
        return response
    
    def update_position(self, instrument, stop_loss=None, take_profit=None):
        """Update stop loss or take profit for a position
        
        Args:
            instrument (str): Instrument name (e.g., "EUR_USD")
            stop_loss (float, optional): New stop loss price
            take_profit (float, optional): New take profit price
            
        Returns:
            dict: Update position response
        """
        # Get open trades for the instrument
        response = self._make_request(
            "GET",
            f"/v3/accounts/{self.account_id}/trades?instrument={instrument}&state=OPEN"
        )
        
        trades = response.get("trades", [])
        if not trades:
            logger.warning(f"No open trades found for {instrument}")
            return {"error": "No open trades found"}
        
        # Update each trade
        results = []
        for trade in trades:
            trade_id = trade["id"]
            
            # Build update data
            update_data = {}
            if stop_loss is not None:
                update_data["stopLoss"] = {
                    "price": str(stop_loss),
                    "timeInForce": "GTC"
                }
            if take_profit is not None:
                update_data["takeProfit"] = {
                    "price": str(take_profit),
                    "timeInForce": "GTC"
                }
            
            # Skip if no updates
            if not update_data:
                continue
                
            # Execute update
            update_response = self._make_request(
                "PUT",
                f"/v3/accounts/{self.account_id}/trades/{trade_id}/orders",
                data=update_data
            )
            
            results.append(update_response)
        
        return results


def get_oanda_client():
    """Get OANDA API client
    
    Returns:
        OandaAPI: OANDA API client
    """
    try:
        practice_mode = os.getenv("OANDA_PRACTICE", "True").lower() in ["true", "1", "yes"]
        client = OandaAPI(practice=practice_mode)
        return client
    except Exception as e:
        logger.error(f"Failed to create OANDA client: {e}")
        return None


def execute_trade(oanda_client, trade):
    """Execute a new trade on OANDA platform
    
    Args:
        oanda_client (OandaAPI): OANDA API client
        trade (dict): Trade details
        
    Returns:
        tuple: (success, trade_data)
    """
    try:
        epic = trade.get("epic")
        direction = trade.get("direction")
        size = float(trade.get("size", 1.0))
        
        # Convert IG epic to OANDA instrument
        instrument = convert_ig_epic_to_oanda(epic)
        
        # Determine units based on direction
        # Convert size from lots to units (1 lot = 100,000 units)
        # Minimum is 1 unit
        units_raw = size * 100000
        units = int(units_raw)
        if abs(units) < 1:
            units = 1 if direction == "BUY" else -1
            
        # Apply direction
        if direction == "SELL" and units > 0:
            units = -units
        elif direction == "BUY" and units < 0:
            units = abs(units)
            
        logger.info(f"Executing {direction} {instrument} | Units: {units} (from size {size})")
        
        # Get stop loss and take profit
        stop_loss = trade.get("initial_stop_loss")
        take_profit = None
        if trade.get("take_profit_levels") and len(trade.get("take_profit_levels")) > 0:
            take_profit = trade.get("take_profit_levels")[0]
        
        # Create order
        response = oanda_client.create_order(
            instrument=instrument,
            units=units,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        # Check if order was created successfully
        order_created = "orderCreateTransaction" in response
        order_filled = "orderFillTransaction" in response
        
        if order_created and order_filled:
            # Get trade details
            fill_details = response.get("orderFillTransaction", {})
            trade_id = fill_details.get("id")
            
            # Prepare trade log data
            trade_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "epic": epic,
                "instrument": instrument,
                "direction": direction,
                "size": size,
                "units": units,
                "entry_price": float(fill_details.get("price", 0)),
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk_percent": trade.get("risk_percent"),
                "risk_reward": trade.get("risk_reward"),
                "pattern": trade.get("pattern"),
                "stop_management": trade.get("stop_management", []),
                "outcome": "EXECUTED",
                "deal_id": trade_id
            }
            
            return True, trade_data
        else:
            # Order rejected
            rejection_reason = ""
            if "orderRejectTransaction" in response:
                rejection_reason = response["orderRejectTransaction"].get("reason", "Unknown reason")
                
            logger.error(f"Trade execution failed: {rejection_reason}")
            return False, {"outcome": "FAILED", "reason": rejection_reason}
            
    except Exception as e:
        logger.error(f"Trade execution error: {e}")
        return False, {"outcome": "ERROR", "reason": str(e)}


def close_position(oanda_client, position_action, positions):
    """Close an existing position
    
    Args:
        oanda_client (OandaAPI): OANDA API client
        position_action (dict): Position action details
        positions (DataFrame): Current positions
        
    Returns:
        tuple: (success, close_data)
    """
    try:
        deal_id = position_action.get("dealId")
        epic = position_action.get("epic")
        
        # Convert IG epic to OANDA instrument
        instrument = convert_ig_epic_to_oanda(epic)
        
        logger.info(f"Closing position {deal_id} | {instrument}")
        
        # Close position
        response = oanda_client.close_position(instrument)
        
        # Check if position was closed successfully
        long_closed = "longOrderCreateTransaction" in response and "longOrderFillTransaction" in response
        short_closed = "shortOrderCreateTransaction" in response and "shortOrderFillTransaction" in response
        
        if long_closed or short_closed:
            # Get close details
            close_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "epic": epic,
                "instrument": instrument,
                "direction": "CLOSE",
                "outcome": "CLOSED",
                "deal_id": deal_id,
                "reason": position_action.get("reason", "")
            }
            
            return True, close_data
        else:
            # No position to close or close failed
            error_message = "No position found to close"
            if "errorMessage" in response:
                error_message = response["errorMessage"]
                
            logger.error(f"Position close failed: {error_message}")
            return False, {"outcome": "FAILED", "reason": error_message}
            
    except Exception as e:
        logger.error(f"Close position error: {e}")
        return False, {"outcome": "ERROR", "reason": str(e)}


def update_stop_loss(oanda_client, position_action):
    """Update stop loss for an existing position
    
    Args:
        oanda_client (OandaAPI): OANDA API client
        position_action (dict): Position action details
        
    Returns:
        tuple: (success, update_data)
    """
    try:
        epic = position_action.get("epic")
        new_level = position_action.get("new_level")
        
        # Convert IG epic to OANDA instrument
        instrument = convert_ig_epic_to_oanda(epic)
        
        logger.info(f"Updating stop for {instrument} to {new_level}")
        
        # Update position
        response = oanda_client.update_position(
            instrument=instrument,
            stop_loss=new_level
        )
        
        # Check if update was successful
        if not isinstance(response, dict) or "error" not in response:
            # Log the update
            update_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "epic": epic,
                "instrument": instrument,
                "action_type": "UPDATE_STOP",
                "new_level": new_level,
                "outcome": "UPDATED",
                "reason": position_action.get("reason", "")
            }
            
            return True, update_data
        else:
            logger.error(f"Update stop loss failed: {response.get('error')}")
            return False, {"outcome": "FAILED", "reason": response.get("error")}
            
    except Exception as e:
        logger.error(f"Update stop loss error: {e}")
        return False, {"outcome": "ERROR", "reason": str(e)}


def convert_ig_epic_to_oanda(epic):
    """Convert IG epic to OANDA instrument format
    
    Args:
        epic (str): IG epic
        
    Returns:
        str: OANDA instrument
    """
    # Map IG epics to OANDA instruments
    epic_map = {
        "CS.D.EURUSD.TODAY.IP": "EUR_USD",
        "CS.D.USDJPY.TODAY.IP": "USD_JPY",
        "CS.D.GBPUSD.TODAY.IP": "GBP_USD",
        "CS.D.AUDUSD.TODAY.IP": "AUD_USD",
        "CS.D.USDCAD.TODAY.IP": "USD_CAD",
        "CS.D.USDCHF.TODAY.IP": "USD_CHF",
        "CS.D.NZDUSD.TODAY.IP": "NZD_USD",
        "CS.D.EURJPY.TODAY.IP": "EUR_JPY",
        "CS.D.EURGBP.TODAY.IP": "EUR_GBP",
        "CS.D.GBPJPY.TODAY.IP": "GBP_JPY",
        "CS.D.AUDJPY.TODAY.IP": "AUD_JPY",
        "CS.D.AUDNZD.TODAY.IP": "AUD_NZD"
    }
    
    # Return mapped instrument or original if not found
    if epic in epic_map:
        return epic_map[epic]
    
    # Try to extract the currency pair from the epic
    import re
    match = re.search(r'\.D\.([A-Z]{3})([A-Z]{3})\.', epic)
    if match:
        return f"{match.group(1)}_{match.group(2)}"
    
    # Return original if not matched
    return epic