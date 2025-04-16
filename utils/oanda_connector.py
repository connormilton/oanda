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
        # Ensure units is an integer - OANDA requires whole numbers
        try:
            units = int(units)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert units '{units}' to integer, using minimum value")
            units = 1  # Default to minimum
        
        # Build order request
        order_data = {
            "order": {
                "instrument": instrument,
                "units": str(units),  # OANDA API expects string
                "timeInForce": "FOK",  # Fill or Kill
                "positionFill": "DEFAULT",
                "type": "MARKET"  # Default to market order
            }
        }
        
        # For limit orders, add price
        if price is not None:
            order_data["order"]["type"] = "LIMIT"
            order_data["order"]["price"] = str(price)
        
        # Add stop loss if provided
        if stop_loss is not None:
            order_data["order"]["stopLossOnFill"] = {
                "price": str(stop_loss),
                "timeInForce": "GTC",  # Good Till Cancelled
                "triggerMode": "TOP_OF_BOOK"  # Standard trigger mode
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


def calculate_pip_value(instrument, account_currency, price=1.0, units=1):
    """Calculate the value of a pip for a given instrument and units
    
    Args:
        instrument (str): OANDA instrument name (e.g., "EUR_USD")
        account_currency (str): Account currency (e.g., "USD")
        price (float): Current price of the instrument
        units (int): Number of units in the position
        
    Returns:
        float: Value of 1 pip in account currency
    """
    # Set pip size based on JPY or standard pairs
    pip_size = 0.01 if "_JPY" in instrument else 0.0001
    
    # Extract quote currency
    quote_currency = instrument.split('_')[1]
    
    # Calculate pip value in quote currency
    pip_value_quote = pip_size * units
    
    # If quote currency is the same as account currency, return directly
    if quote_currency == account_currency:
        return pip_value_quote
    
    # Otherwise, convert to account currency (simplified)
    # In a real system, you would use current exchange rates
    # This is a simplified approximation
    pip_value_account = pip_value_quote
    
    return pip_value_account


def calculate_position_size(account_balance, risk_percent, entry_price, stop_loss, instrument, account_currency):
    """Calculate position size based on risk percentage and stop distance
    
    Args:
        account_balance (float): Account balance
        risk_percent (float): Risk percentage (1-5%)
        entry_price (float): Entry price
        stop_loss (float): Stop loss price
        instrument (str): OANDA instrument name
        account_currency (str): Account currency
        
    Returns:
        int: Position size in units
    """
    # Calculate risk amount in account currency
    risk_amount = account_balance * (risk_percent / 100)
    
    # Calculate stop distance in price
    stop_distance = abs(entry_price - stop_loss)
    
    # Ensure stop distance is not zero
    if stop_distance <= 0:
        logger.warning(f"Stop distance is zero or negative for {instrument}. Using minimum value.")
        stop_distance = 0.0001  # Minimum stop distance
    
    # Convert stop distance to pips
    pip_multiplier = 100 if "_JPY" in instrument else 10000
    stop_distance_pips = stop_distance * pip_multiplier
    
    # Calculate pip value for 1 unit
    pip_value_per_unit = calculate_pip_value(instrument, account_currency, entry_price, 1)
    
    # Calculate required units for the risk amount
    try:
        required_units = risk_amount / (stop_distance_pips * pip_value_per_unit)
        
        # Round down to whole units
        units = int(required_units)
        
        # Ensure minimum units
        if units < 1:
            units = 1
            
        return units
    except Exception as e:
        logger.error(f"Error calculating position size: {e}")
        return 10  # Default minimum position size


def execute_trade(oanda_client, trade, positions=None):
    """Execute a new trade on OANDA platform with proper risk management
    
    Args:
        oanda_client (OandaAPI): OANDA API client
        trade (dict): Trade details
        positions (DataFrame, optional): Current open positions
        
    Returns:
        tuple: (success, trade_data)
    """
    try:
        epic = trade.get("epic")
        direction = trade.get("direction")
        size = trade.get("size")
        risk_percent = trade.get("risk_percent", 2.0)
        
        # Convert IG epic to OANDA instrument
        instrument = convert_ig_epic_to_oanda(epic)
        
        # Get account information
        account = oanda_client.get_account()
        account_balance = float(account.get("balance", 1000))
        account_currency = account.get("currency", "USD")
        
        # Get entry and stop loss prices
        entry_price = float(trade.get("entry_price", 0))
        stop_loss = float(trade.get("initial_stop_loss", 0))
        
        # If no positions provided, get them
        if positions is None:
            positions = oanda_client.get_open_positions()
        
        # Check for 30% total risk limit
        total_risk_percent = calculate_total_risk_percentage(positions, risk_percent, account_balance)
        if total_risk_percent > 30.0:
            logger.warning(f"Total risk percentage {total_risk_percent:.2f}% exceeds 30% limit. Canceling trade.")
            return False, {"outcome": "CANCELED", "reason": "Total risk percentage exceeds 30% limit"}
        
        # Check for 10% same currency limit
        currency_risk = calculate_currency_risk_percentage(positions, instrument, risk_percent, account_balance)
        if currency_risk > 10.0:
            logger.warning(f"Risk for {instrument.split('_')[0]} ({currency_risk:.2f}%) exceeds 10% limit. Canceling trade.")
            return False, {"outcome": "CANCELED", "reason": f"Risk for {instrument.split('_')[0]} exceeds 10% limit"}
        
        # Calculate position size based on risk
        if entry_price > 0 and stop_loss > 0:
            # Use proper risk-based position sizing
            units = calculate_position_size(
                account_balance, 
                risk_percent, 
                entry_price, 
                stop_loss, 
                instrument, 
                account_currency
            )
            
            # Log risk calculation
            stop_distance = abs(entry_price - stop_loss)
            pip_multiplier = 100 if "_JPY" in instrument else 10000
            stop_distance_pips = stop_distance * pip_multiplier
            
            logger.info(f"Risk calculation for {instrument}:")
            logger.info(f"  Account balance: ${account_balance:.2f}")
            logger.info(f"  Risk: {risk_percent:.2f}% (${account_balance * risk_percent / 100:.2f})")
            logger.info(f"  Entry: {entry_price:.5f}, Stop: {stop_loss:.5f}")
            logger.info(f"  Stop distance: {stop_distance_pips:.1f} pips")
            logger.info(f"  Position size: {units} units")
        else:
            # Fallback to size-based calculation if prices not provided
            # First ensure size is a float
            try:
                size = float(size) if size is not None else 0.01
            except (ValueError, TypeError):
                logger.warning(f"Could not convert size '{size}' to float, using default")
                size = 0.01
            
            # Convert size to units with a conservative multiplier
            units = int(size * 100)  # Small multiplier for small account
            logger.info(f"Using size-based position: {size} → {units} units")
        
        # Ensure minimum unit size (1) and apply direction
        if abs(units) < 1:
            units = 1
            
        # Apply direction to units
        if direction == "SELL":
            units = -abs(units)
        else:  # BUY
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
                "risk_percent": risk_percent,
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
        error_message = str(e)
        if "UNITS_LIMIT_EXCEEDED" in error_message:
            error_message = f"Position size too large for account. Tried {units} units, reduce 'risk_percent' parameter."
        elif "INSUFFICIENT_FUNDS" in error_message:
            error_message = f"Insufficient funds for trade size {size} (units: {units})."
        
        logger.error(f"Trade execution error: {error_message}")
        return False, {"outcome": "ERROR", "reason": error_message}


def calculate_total_risk_percentage(positions, new_trade_risk, account_balance):
    """Calculate total risk percentage including existing positions
    
    Args:
        positions (DataFrame): Current positions
        new_trade_risk (float): Risk percentage for new trade
        account_balance (float): Account balance
        
    Returns:
        float: Total risk percentage
    """
    # Default to new trade risk if no positions
    if positions is None or len(positions) == 0:
        return float(new_trade_risk)
        
    # Estimate risk for existing positions (simplified)
    # In a real system, you would calculate this based on stop loss distances
    existing_risk = sum([2.0 for _ in range(len(positions))])  # Assume 2% risk per position
    
    # Add new trade risk
    total_risk = existing_risk + float(new_trade_risk)
    
    return total_risk


def calculate_currency_risk_percentage(positions, new_instrument, new_trade_risk, account_balance):
    """Calculate risk percentage for a specific currency
    
    Args:
        positions (DataFrame): Current positions
        new_instrument (str): New instrument (e.g., "EUR_USD")
        new_trade_risk (float): Risk percentage for new trade
        account_balance (float): Account balance
        
    Returns:
        float: Risk percentage for the currency
    """
    # Extract base currency from the instrument
    base_currency = new_instrument.split('_')[0]
    
    # Default to new trade risk if no positions
    if positions is None or len(positions) == 0:
        return float(new_trade_risk)
        
    # Calculate risk for positions with the same base currency
    existing_risk = 0.0
    for _, position in positions.iterrows():
        position_instrument = position.get("epic", "")
        if isinstance(position_instrument, str) and base_currency in position_instrument.split('_')[0]:
            # Assume 2% risk per position with same currency
            existing_risk += 2.0
    
    # Add new trade risk
    total_currency_risk = existing_risk + float(new_trade_risk)
    
    return total_currency_risk


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