"""
LLM Budget Management Module
Tracks and controls API usage costs
"""

import os
import json
from datetime import datetime, timezone


class LLMBudgetManager:
    """Lightweight manager for LLM API budget"""
    
    def __init__(self):
        self.daily_budget = float(os.getenv("DAILY_LLM_BUDGET", 20.0))
        self.usage_file = "data/usage_log.jsonl"
        self.today = datetime.now(timezone.utc).date().isoformat()
        self.refresh_usage()
        
    def refresh_usage(self):
        """Load or initialize today's usage data"""
        os.makedirs(os.path.dirname(self.usage_file), exist_ok=True)
        
        self.usage = {"date": self.today, "total_cost": 0.0, "calls": []}
        
        if os.path.exists(self.usage_file):
            try:
                with open(self.usage_file, "r") as f:
                    for line in f:
                        entry = json.loads(line)
                        if entry.get("date") == self.today:
                            self.usage = entry
                            break
            except:
                pass

    def log_usage(self, tier, tokens_in, tokens_out, cost):
        """Log LLM API usage"""
        self.usage["total_cost"] += cost
        self.usage["calls"].append({
            "tier": tier,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost": cost,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Save to file
        entries = []
        if os.path.exists(self.usage_file):
            with open(self.usage_file, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("date") != self.today:
                            entries.append(entry)
                    except:
                        continue
        
        entries.append(self.usage)
        
        with open(self.usage_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
                
        return cost
    
    def can_spend(self, estimated_cost):
        """Check if we have enough budget remaining"""
        return self.usage["total_cost"] + estimated_cost <= self.daily_budget
    
    def get_status(self):
        """Get current budget status"""
        return {
            "total_budget": self.daily_budget,
            "spent": self.usage["total_cost"],
            "remaining": self.daily_budget - self.usage["total_cost"],
            "percent_used": (self.usage["total_cost"] / self.daily_budget) * 100
        }