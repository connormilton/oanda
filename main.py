"""
Collaborative LLM Forex Trading System
Main entry point (OANDA version)
"""

import os
import logging
from dotenv import load_dotenv
from utils.oanda_connector import get_oanda_client
from core.system_controller import SystemController

# Setup
load_dotenv()
os.makedirs("data", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/trading_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CollaborativeTrader")

def main():
    logger.info("Initializing Collaborative LLM Forex Trading System (OANDA)")
    
    # Connect to OANDA API
    oanda_client = get_oanda_client()
    
    if not oanda_client:
        logger.error("Failed to connect to OANDA API. Exiting.")
        return
    
    # Display connected account info
    try:
        account = oanda_client.get_account()
        logger.info(f"Connected to OANDA account: {account.get('id', 'Unknown')}")
        logger.info(f"Account balance: {account.get('balance', 'Unknown')} {account.get('currency', 'Unknown')}")
        
        # Display available forex pairs
        try:
            instruments = oanda_client.get_account_instruments()
            forex_count = sum(1 for instr in instruments if instr.get('type') == 'CURRENCY')
            logger.info(f"Available forex pairs: {forex_count}")
        except Exception as e:
            logger.error(f"Error getting instruments: {e}")
        
        # Display open positions
        try:
            positions = oanda_client.get_open_positions()
            open_count = len(positions) if not isinstance(positions, str) and not positions.empty else 0
            logger.info(f"Open positions: {open_count}")
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
    except Exception as e:
        logger.error(f"Error getting OANDA account info: {e}")
    
    # Initialize and run the system
    system = SystemController(oanda_client)
    system.run()

if __name__ == "__main__":
    import pandas as pd  # Added for positions check
    main()