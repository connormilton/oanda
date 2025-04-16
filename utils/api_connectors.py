"""
API Connection Utilities
Handles connections to trading platforms and data providers
"""

import os
import logging
from datetime import datetime, timezone
from utils.oanda_connector import (
    execute_trade as oanda_execute_trade,
    close_position as oanda_close_position,
    update_stop_loss as oanda_update_stop_loss
)

logger = logging.getLogger("CollaborativeTrader")

def get_polygon_client():
    """Get Polygon API client"""
    try:
        from polygon import RESTClient
        return RESTClient(os.getenv("POLYGON_API_KEY"))
    except ImportError:
        logger.warning("Polygon SDK not installed. Market data features will be limited.")
        return None
    except Exception as e:
        logger.error(f"Error connecting to Polygon API: {e}")
        return None

def execute_trade(oanda_client, trade, positions=None):
    """Execute a new trade with the appropriate platform
    
    Args:
        oanda_client: The OANDA client
        trade (dict): Trade details
        positions (DataFrame): Current open positions
    
    Returns:
        tuple: (success, trade_data)
    """
    return oanda_execute_trade(oanda_client, trade, positions)

def close_position(oanda_client, position_action, positions):
    """Close an existing position
    
    Args:
        oanda_client: The OANDA client
        position_action (dict): Position action details
        positions (DataFrame): Current positions
    
    Returns:
        tuple: (success, close_data)
    """
    return oanda_close_position(oanda_client, position_action, positions)

def update_stop_loss(oanda_client, position_action):
    """Update stop loss for an existing position
    
    Args:
        oanda_client: The OANDA client
        position_action (dict): Position action details
    
    Returns:
        tuple: (success, update_data)
    """
    return oanda_update_stop_loss(oanda_client, position_action)