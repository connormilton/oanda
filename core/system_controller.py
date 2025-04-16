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

from utils.oanda_connector import execute_trade, close_position, update_stop_loss

logger = logging.getLogger("CollaborativeTrader")

# Core currency pairs to trade
FOREX_PAIRS = [
    "CS.D.EURUSD.TODAY.IP", "CS.D.USDJPY.TODAY.IP", "CS.D.GBPUSD.TODAY.IP", 
    "CS.D.AUDUSD.TODAY.IP", "CS.D.USDCAD.TODAY.IP", "CS.D.GBPJPY.TODAY.IP",
    "CS.D.EURJPY.TODAY.IP", "CS.D.AUDJPY.TODAY.IP", "CS.D.EURGBP.TODAY.IP",
    "CS.D.USDCHF.TODAY.IP", "CS.D.NZDUSD.TODAY.IP", "CS.D.AUDNZD.TODAY.IP"
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
    
    def execute_trading_actions(self, executor_result):
        """Execute the trading actions recommended by the executor agent"""
        logger.info("Executing trading actions")
        
        try:
            # Skip if no executor result
            if not executor_result:
                logger.warning("No executor result to implement")
                return False
            
            # Get current positions
            positions = self.data.get_positions()
            
            # Execute new trades
            trade_actions = executor_result.get("trade_actions", [])
            for trade in trade_actions:
                if trade.get("action_type") == "OPEN":
                    success, trade_result = execute_trade(self.oanda, trade)
                    if success:
                        logger.info(f"Successfully executed trade: {trade.get('epic')} {trade.get('direction')}")
                        # Log the trade in memory
                        self.memory.log_trade(trade_result)
                        
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