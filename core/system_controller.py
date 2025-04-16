"""
System Controller Module
Orchestrates the trading system components and workflow
"""

import logging
import time
from datetime import datetime, timezone
import openai
import os

from core.budget_manager import LLMBudgetManager
from core.trading_memory import TradingMemory
from core.data_collector import DataCollector

from agents.scout_agent import ScoutAgent
from agents.strategist_agent import StrategistAgent
from agents.executor_agent import ExecutorAgent
from agents.team_reviewer import TeamReviewer

from utils.oanda_connector import (
    execute_trade, 
    close_position, 
    update_stop_loss
)

logger = logging.getLogger("CollaborativeTrader")

# Core currency pairs to trade
FOREX_PAIRS = [
    "EUR_USD", "USD_JPY", "GBP_USD", 
    "AUD_USD", "USD_CAD", "GBP_JPY", 
    "EUR_JPY", "AUD_JPY", "EUR_GBP",
    "USD_CHF", "NZD_USD", "AUD_NZD"
]

class SystemController:
    """Controls the collaborative trading system workflow"""
    
    def __init__(self, oanda_client):
        # Set up OpenAI API
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        # Initialize components
        self.budget = LLMBudgetManager()
        self.memory = TradingMemory()
        self.data = DataCollector(oanda_client)
        
        # Initialize agents
        self.scout = ScoutAgent(self.budget)
        self.strategist = StrategistAgent(self.budget)
        self.executor = ExecutorAgent(self.budget)
        self.team_reviewer = TeamReviewer(self.budget)
        
        # Trading services
        self.oanda = oanda_client
        
        # Initialize agent responses
        self.agent_responses = {
            "scout": None,
            "strategist": None,
            "executor": None,
            "team_review": None
        }
    
    def validate_trade(self, trade, account_data, positions):
        """Validate trade parameters and ensure they meet risk management criteria
        
        Args:
            trade (dict): Trade details
            account_data (dict): Account information
            positions (DataFrame): Current open positions
            
        Returns:
            dict: Validated and possibly modified trade
        """
        try:
            # Ensure we have the basic required fields
            required_fields = ["epic", "direction", "risk_percent"]
            for field in required_fields:
                if field not in trade:
                    logger.warning(f"Trade missing required field: {field}. Cannot execute.")
                    return None
            
            # Get account balance
            account_balance = float(account_data.get('balance', 1000))
            
            # Validate risk percentage (1-5%)
            risk_percent = float(trade.get("risk_percent", 2.0))
            if risk_percent < 1.0:
                logger.warning(f"Risk percentage {risk_percent}% below minimum 1%. Adjusting to 1%.")
                trade["risk_percent"] = 1.0
            elif risk_percent > 5.0:
                logger.warning(f"Risk percentage {risk_percent}% exceeds maximum 5%. Capping at 5%.")
                trade["risk_percent"] = 5.0
            
            # Calculate current total risk exposure
            total_risk = self.calculate_portfolio_risk(positions)
            new_total_risk = total_risk + float(trade.get("risk_percent", 2.0))
            
            # Check 30% total risk limit
            if new_total_risk > 30.0:
                logger.warning(f"New trade would put total risk at {new_total_risk:.2f}%, exceeding 30% limit. Canceling trade.")
                return None
            
            # Check currency exposure limit (10%)
            currency_risk = self.calculate_currency_risk(positions, trade.get("epic"))
            new_currency_risk = currency_risk + float(trade.get("risk_percent", 2.0))
            
            # Extract currency from the epic
            currency = trade.get("epic").split("_")[0] if "_" in trade.get("epic") else trade.get("epic")[5:8]
            
            if new_currency_risk > 10.0:
                logger.warning(f"New trade would put {currency} exposure at {new_currency_risk:.2f}%, exceeding 10% limit. Canceling trade.")
                return None
            
            # Validate entry price and stop loss
            if "entry_price" not in trade or not trade["entry_price"]:
                logger.warning("Trade missing entry price. Cannot properly validate.")
                return None
                
            if "initial_stop_loss" not in trade or not trade["initial_stop_loss"]:
                logger.warning("Trade missing stop loss. Cannot properly validate risk.")
                return None
            
            return trade
            
        except Exception as e:
            logger.error(f"Error validating trade: {e}")
            return None
    
    def calculate_portfolio_risk(self, positions):
        """Calculate current portfolio risk based on open positions
        
        Args:
            positions (DataFrame): Current open positions
            
        Returns:
            float: Total risk percentage
        """
        if positions is None or len(positions) == 0:
            return 0.0
        
        # In a real system, this would be calculated based on 
        # actual stop loss distances and position sizes
        # For this simplified version, we'll assume each position
        # has a risk of 2% (conservative estimate)
        return len(positions) * 2.0

    def calculate_currency_risk(self, positions, epic):
        """Calculate risk exposure for a specific currency
        
        Args:
            positions (DataFrame): Current open positions
            epic (str): Instrument epic or name
            
        Returns:
            float: Risk percentage for the currency
        """
        if positions is None or len(positions) == 0:
            return 0.0
        
        # Extract the currency from the epic
        currency = epic.split("_")[0] if "_" in epic else epic[5:8]
        
        # Calculate risk for positions with the same currency
        currency_risk = 0.0
        for _, position in positions.iterrows():
            position_epic = position.get("epic", "")
            position_currency = position_epic.split("_")[0] if "_" in position_epic else position_epic[5:8]
            
            if position_currency == currency:
                # Assume 2% risk per position with the same currency
                currency_risk += 2.0
        
        return currency_risk
    
    def execute_trading_actions(self, executor_result):
        """Execute the trading actions recommended by the executor agent
        with added risk management validation
        """
        logger.info("Executing trading actions")
        
        try:
            # Skip if no executor result
            if not executor_result:
                logger.warning("No executor result to implement")
                return False
            
            # Get current positions
            positions = self.data.get_positions()
            
            # Get account data
            account_data = self.data.get_account_data()
            
            # Execute new trades
            trade_actions = executor_result.get("trade_actions", [])
            for trade in trade_actions:
                # Validate trade against risk management rules
                validated_trade = self.validate_trade(trade, account_data, positions)
                
                if validated_trade is None:
                    logger.warning(f"Trade for {trade.get('epic')} failed validation. Skipping.")
                    continue
                    
                if trade.get("action_type") == "OPEN":
                    success, trade_result = execute_trade(self.oanda, validated_trade, positions)
                    if success:
                        logger.info(f"Successfully executed trade: {trade.get('epic')} {trade.get('direction')}")
                        # Log the trade in memory
                        self.memory.log_trade(trade_result)
                        
                        # Update positions after trade execution
                        positions = self.data.get_positions()
                        
                        # Save analysis for this pair
                        if "epic" in trade:
                            self.memory.update_analysis_history(trade["epic"], {
                                "direction": trade.get("direction"),
                                "entry_price": trade.get("entry_price"),
                                "stop_loss": trade.get("initial_stop_loss"),
                                "take_profit": trade.get("take_profit_levels"),
                                "risk_reward": trade.get("risk_reward"),
                                "pattern": trade.get("pattern"),
                                "reasoning": trade.get("reasoning")
                            })
                    else:
                        logger.error(f"Failed to execute trade: {trade_result}")
            
            # Execute position actions
            position_actions = executor_result.get("position_actions", [])
            for action in position_actions:
                action_type = action.get("action_type", "").upper()
                
                if action_type == "CLOSE":
                    success, result = close_position(self.oanda, action, positions)
                    if success:
                        logger.info(f"Successfully closed position: {action.get('epic')} {action.get('dealId')}")
                        # Log the close
                        self.memory.log_trade(result)
                        
                        # Update positions after closing
                        positions = self.data.get_positions()
                    else:
                        logger.error(f"Failed to close position: {result}")
                        
                elif action_type == "UPDATE_STOP":
                    success, result = update_stop_loss(self.oanda, action)
                    if success:
                        logger.info(f"Successfully updated stop: {action.get('epic')} {action.get('dealId')} to {action.get('new_level')}")
                        # Log the update
                        self.memory.log_trade(result)
                    else:
                        logger.error(f"Failed to update stop: {result}")
            
            # Update daily return tracking (placeholder - would use actual P&L in production)
            # This is just a simple counter for demonstration purposes
            current_return = self.memory.memory.get("daily_return", 0)
            trade_count = len(trade_actions) + len(position_actions)
            if trade_count > 0:
                # Simulate some progress toward 10% goal
                self.memory.update_memory("daily_return", min(10.0, current_return + (0.5 * trade_count)))
            
            return True
        except Exception as e:
            logger.error(f"Error executing trading actions: {e}")
            return False
    
    def run_trading_cycle(self):
        """Run a complete trading cycle with all three agents"""
        logger.info("Starting collaborative trading cycle")
        
        try:
            # Reset agent responses for this cycle
            self.agent_responses = {
                "scout": None,
                "strategist": None,
                "executor": None,
                "team_review": None
            }
            
            # Collect common data for agents
            account_data = self.data.get_account_data()
            positions = self.data.get_positions()
            
            # Collect market data for all pairs
            market_data = {}
            for epic in FOREX_PAIRS:
                data = self.data.get_market_data(epic)
                if data:
                    market_data[epic] = data
            
            # 1. Run Market Scout Agent
            scout_result = self.scout.run(
                market_data, 
                account_data, 
                positions, 
                self.memory
            )
            
            if scout_result:
                self.agent_responses["scout"] = scout_result
                
                # 2. Run Strategist Agent if scout found opportunities
                opportunities = scout_result.get("opportunities", [])
                if opportunities:
                    # Collect market data for selected pairs only
                    opportunity_market_data = {}
                    for opp in opportunities:
                        epic = opp.get("epic")
                        if epic in market_data:
                            opportunity_market_data[epic] = market_data[epic]
                        else:
                            # Try to standardize the epic format if needed
                            standardized_epic = self._standardize_epic_format(epic)
                            if standardized_epic in market_data:
                                opportunity_market_data[standardized_epic] = market_data[standardized_epic]
                                # Update the epic in the opportunity to the standardized format
                                opp["epic"] = standardized_epic
                    
                    strategist_result = self.strategist.run(
                        opportunities,
                        opportunity_market_data,
                        account_data,
                        positions,
                        self.memory
                    )
                    
                    if strategist_result:
                        self.agent_responses["strategist"] = strategist_result
                        
                        # 3. Run Executor Agent if strategist produced analysis
                        analysis_results = strategist_result.get("analysis_results", [])
                        if analysis_results:
                            executor_result = self.executor.run(
                                analysis_results,
                                market_data,
                                account_data,
                                positions,
                                self.memory
                            )
                            
                            if executor_result:
                                self.agent_responses["executor"] = executor_result
                                
                                # 4. Execute trading actions
                                self.execute_trading_actions(executor_result)
                
                # 5. Run team review if all agents produced results
                if all(self.agent_responses.values()):
                    team_result = self.team_reviewer.run(
                        self.agent_responses,
                        market_data, 
                        account_data, 
                        positions, 
                        self.memory
                    )
                    
                    if team_result:
                        self.agent_responses["team_review"] = team_result
            
            # Log budget status
            budget_status = self.budget.get_status()
            logger.info(f"Budget status: ${budget_status['remaining']:.2f} remaining ({100-budget_status['percent_used']:.1f}%)")
            
            return True
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            return False
    
    def _standardize_epic_format(self, epic):
        """Standardize epic format to OANDA format (e.g. EUR/USD to EUR_USD)"""
        if "/" in epic:
            return epic.replace("/", "_")
        if "-" in epic:
            return epic.replace("-", "_")
        
        # Handle full IG format if any left
        if "CS.D." in epic and ".TODAY.IP" in epic:
            pair = epic.replace("CS.D.", "").replace(".TODAY.IP", "")
            if len(pair) == 6:
                return f"{pair[:3]}_{pair[3:]}"
        
        return epic
    
    def run(self):
        """Main trading loop"""
        logger.info("Starting Collaborative LLM Forex Trading System")
        print("\nSTARTING COLLABORATIVE LLM FOREX TRADING SYSTEM")
        
        # Display initial budget
        budget_status = self.budget.get_status()
        print(f"Daily budget: ${budget_status['total_budget']:.2f}")
        print(f"Available: ${budget_status['remaining']:.2f}")
        
        # Trading loop
        while True:
            try:
                # Run a full trading cycle
                self.run_trading_cycle()
                
                # Sleep between cycles - adjust based on market activity
                # Market hours could influence the sleep duration
                current_hour = datetime.now(timezone.utc).hour
                
                # More frequent during active market hours
                if 8 <= current_hour <= 16:  # Major market hours (approx)
                    sleep_time = 5 * 60  # 5 minutes
                else:
                    sleep_time = 15 * 60  # 15 minutes
                
                logger.info(f"Cycle complete. Sleeping for {sleep_time/60:.1f} minutes until next cycle.")
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait 1 minute on error