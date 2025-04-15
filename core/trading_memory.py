"""
Trading Memory Module
Manages persistence of trading history, analysis and system state
"""

import os
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("CollaborativeTrader")

class TradingMemory:
    """Enhanced memory system for collaborative trading"""
    
    def __init__(self):
        self.memory_file = "data/system_memory.json"
        self.feedback_file = "data/agent_feedback.json"
        self.trade_log_file = "data/trade_log.jsonl"
        self.analysis_file = "data/analysis_history.json"
        
        # Initialize all memory systems
        self.load_memory()
        self.load_feedback()
        self.load_analysis_history()
    
    def load_memory(self):
        """Load or initialize system memory"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r") as f:
                    self.memory = json.load(f)
            except:
                self.initialize_memory()
        else:
            self.initialize_memory()
    
    def load_feedback(self):
        """Load or initialize agent feedback"""
        if os.path.exists(self.feedback_file):
            try:
                with open(self.feedback_file, "r") as f:
                    self.feedback = json.load(f)
            except:
                self.initialize_feedback()
        else:
            self.initialize_feedback()
    
    def load_analysis_history(self):
        """Load or initialize analysis history"""
        if os.path.exists(self.analysis_file):
            try:
                with open(self.analysis_file, "r") as f:
                    self.analysis_history = json.load(f)
            except:
                self.initialize_analysis_history()
        else:
            self.initialize_analysis_history()
    
    def initialize_memory(self):
        """Create initial memory structure"""
        self.memory = {
            "created": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "trade_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "risk_multiplier": 1.0,
            "base_risk": 1.0,
            "daily_return": 0.0,
            "daily_return_target": 10.0,
            "context": {}
        }
        self.save_memory()
    
    def initialize_feedback(self):
        """Create initial feedback structure"""
        self.feedback = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "scout": {},
            "strategist": {},
            "executor": {}
        }
        self.save_feedback()
    
    def initialize_analysis_history(self):
        """Create initial analysis history structure"""
        self.analysis_history = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "pairs": {}
        }
        self.save_analysis_history()
    
    def save_memory(self):
        """Save memory to disk"""
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        with open(self.memory_file, "w") as f:
            json.dump(self.memory, f, indent=2)
    
    def save_feedback(self):
        """Save feedback to disk"""
        os.makedirs(os.path.dirname(self.feedback_file), exist_ok=True)
        with open(self.feedback_file, "w") as f:
            json.dump(self.feedback, f, indent=2)
    
    def save_analysis_history(self):
        """Save analysis history to disk"""
        os.makedirs(os.path.dirname(self.analysis_file), exist_ok=True)
        with open(self.analysis_file, "w") as f:
            json.dump(self.analysis_history, f, indent=2)
    
    def update_memory(self, key, value):
        """Update a specific memory item"""
        self.memory[key] = value
        self.memory["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.save_memory()
    
    def update_feedback(self, agent, feedback):
        """Update feedback for a specific agent"""
        self.feedback[agent] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content": feedback
        }
        self.feedback["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.save_feedback()
    
    def update_analysis_history(self, pair, analysis):
        """Update analysis history for a specific pair"""
        if pair not in self.analysis_history["pairs"]:
            self.analysis_history["pairs"][pair] = []
        
        # Add new analysis with timestamp
        analysis_entry = analysis.copy()
        analysis_entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Add to history (keep last 10)
        self.analysis_history["pairs"][pair].append(analysis_entry)
        if len(self.analysis_history["pairs"][pair]) > 10:
            self.analysis_history["pairs"][pair] = self.analysis_history["pairs"][pair][-10:]
        
        self.analysis_history["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.save_analysis_history()
    
    def log_trade(self, trade_data):
        """Log a trade and update statistics"""
        # Update basic stats
        self.memory["trade_count"] += 1
        
        outcome = trade_data.get("outcome", "").upper()
        if "WIN" in outcome or "PROFIT" in outcome:
            self.memory["win_count"] += 1
        elif "LOSS" in outcome or "STOPPED" in outcome:
            self.memory["loss_count"] += 1
            
        # Update analysis outcome if this is a close
        if trade_data.get("direction") == "CLOSE" and "epic" in trade_data:
            epic = trade_data.get("epic")
            if epic in self.analysis_history["pairs"] and self.analysis_history["pairs"][epic]:
                # Update the most recent analysis with the outcome
                latest = self.analysis_history["pairs"][epic][-1]
                latest["outcome"] = outcome
                self.save_analysis_history()
        
        # Save trade to log
        with open(self.trade_log_file, "a") as f:
            f.write(json.dumps(trade_data) + "\n")
            
        # Update memory
        self.memory["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.save_memory()
    
    def get_recent_trades(self, limit=5):
        """Get recent trades from log"""
        trades = []
        try:
            if os.path.exists(self.trade_log_file):
                with open(self.trade_log_file, "r") as f:
                    for line in f:
                        trades.append(json.loads(line))
                
                # Sort by timestamp (newest first) and limit
                trades.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                return trades[:limit]
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
        
        return trades
    
    def get_all_trades(self):
        """Get all trades from log"""
        trades = []
        try:
            if os.path.exists(self.trade_log_file):
                with open(self.trade_log_file, "r") as f:
                    for line in f:
                        trades.append(json.loads(line))
                
                # Sort by timestamp (newest first)
                trades.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        except Exception as e:
            logger.error(f"Error getting all trades: {e}")
        
        return trades
    
    def get_agent_feedback(self, agent=None):
        """Get feedback for specific agent or all agents"""
        if agent:
            return self.feedback.get(agent, {})
        else:
            return {
                "scout": self.feedback.get("scout", {}).get("content", "No feedback available"),
                "strategist": self.feedback.get("strategist", {}).get("content", "No feedback available"),
                "executor": self.feedback.get("executor", {}).get("content", "No feedback available")
            }
    
    def get_pair_analysis_history(self, pair=None):
        """Get analysis history for specific pair or all pairs"""
        if pair:
            return self.analysis_history["pairs"].get(pair, [])
        else:
            return self.analysis_history["pairs"]
    
    def calculate_performance_metrics(self):
        """Calculate various performance metrics from trade history"""
        trades = self.get_all_trades()
        
        if not trades:
            return {
                "avg_return_per_trade": 0,
                "avg_risk_per_trade": 0,
                "avg_risk_reward": 0,
                "largest_win": 0,
                "largest_loss": 0
            }
        
        # Extract metrics
        returns = []
        risks = []
        risk_rewards = []
        wins = []
        losses = []
        
        for trade in trades:
            # Skip non-completed trades
            outcome = trade.get("outcome", "").upper()
            if "WIN" not in outcome and "LOSS" not in outcome and "PROFIT" not in outcome and "STOPPED" not in outcome:
                continue
                
            # Extract metrics where available
            if "return_percent" in trade:
                returns.append(float(trade["return_percent"]))
                
                if "WIN" in outcome or "PROFIT" in outcome:
                    wins.append(float(trade["return_percent"]))
                elif "LOSS" in outcome or "STOPPED" in outcome:
                    losses.append(float(trade["return_percent"]))
            
            if "risk_percent" in trade:
                risks.append(float(trade["risk_percent"]))
                
            if "risk_reward" in trade:
                risk_rewards.append(float(trade["risk_reward"]))
        
        # Calculate metrics
        avg_return = sum(returns) / len(returns) if returns else 0
        avg_risk = sum(risks) / len(risks) if risks else 0
        avg_rr = sum(risk_rewards) / len(risk_rewards) if risk_rewards else 0
        largest_win = max(wins) if wins else 0
        largest_loss = min(losses) if losses else 0
        
        return {
            "avg_return_per_trade": avg_return,
            "avg_risk_per_trade": avg_risk,
            "avg_risk_reward": avg_rr,
            "largest_win": largest_win,
            "largest_loss": largest_loss
        }