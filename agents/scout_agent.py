"""
Market Scout Agent
Identifies trading opportunities and maintains market awareness
"""

import logging
import json
from datetime import datetime, timezone
import openai
from prompts.collaborative_trading_prompts import CollaborativeTradingPrompts

logger = logging.getLogger("CollaborativeTrader")

class ScoutAgent:
    """Market Scout Agent that identifies opportunities"""
    
    def __init__(self, budget_manager):
        self.model = "gpt-3.5-turbo"
        self.cost_estimate = 0.15
        self.budget_manager = budget_manager
    
    def run(self, market_data, account_data, positions, memory):
        """Run the scout agent to identify opportunities"""
        logger.info("Running Scout Agent")
        
        try:
            # Get data needed for the prompt
            recent_trades = memory.get_recent_trades(5)
            all_trades = memory.get_all_trades()
            agent_feedback = memory.get_agent_feedback()
            
            # Build prompt using template
            scout_prompt = CollaborativeTradingPrompts.market_scanner(
                market_data, 
                account_data, 
                positions, 
                recent_trades, 
                all_trades, 
                agent_feedback
            )
            
            # Check budget
            if not self.budget_manager.can_spend(self.cost_estimate):
                logger.warning("Insufficient budget for Scout agent")
                return None
            
            # Call LLM API
            result = self._call_llm(scout_prompt)
            
            if result:
                logger.info(f"Scout found {len(result.get('opportunities', []))} opportunities")
                
                # Save self-improvement suggestions
                if "self_improvement" in result:
                    memory.update_feedback("scout", result["self_improvement"])
                
                # Save response for logging
                self._save_response(result)
                
                return result
            else:
                logger.warning("Scout agent produced no result")
                return None
                
        except Exception as e:
            logger.error(f"Error in scout agent: {e}")
            return None
    
    def _call_llm(self, prompt):
        """Call LLM API with appropriate model"""
        try:
            # Build parameters
            params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a forex trading scout that works in a collaborative team of trading agents."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"}
            }
            
            # Set a timeout to avoid hanging
            import os
            timeout = int(os.getenv("OPENAI_API_REQUEST_TIMEOUT", "60"))
            
            # Call API with error handling for platform detection issues
            try:
                # Call API
                response = openai.chat.completions.create(**params, timeout=timeout)
            except Exception as platform_error:
                # Handle platform detection errors by temporarily modifying environment
                import platform as py_platform
                original_platform = py_platform.platform
                
                # Create a wrapper that catches errors
                def safe_platform(*args, **kwargs):
                    try:
                        return original_platform(*args, **kwargs)
                    except:
                        return "Windows-10"  # Safe fallback
                
                # Apply the patch
                py_platform.platform = safe_platform
                
                # Try again with patched platform detection
                logger.warning(f"Retrying API call after platform error: {platform_error}")
                response = openai.chat.completions.create(**params, timeout=timeout)
                
                # Restore original function
                py_platform.platform = original_platform
            
            # Log usage
            usage = response.usage
            tokens_in = usage.prompt_tokens
            tokens_out = usage.completion_tokens
            cost = self._calculate_cost(tokens_in, tokens_out)
            self.budget_manager.log_usage("scout", tokens_in, tokens_out, cost)
            
            # Parse response
            result = response.choices[0].message.content
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                # Try to extract JSON if wrapped in code blocks
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', result)
                if json_match:
                    try:
                        return json.loads(json_match.group(1))
                    except:
                        logger.error("Failed to parse JSON from response")
                        return None
                else:
                    logger.error("Failed to extract JSON from response")
                    return None
                    
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            return None
    
    def _calculate_cost(self, tokens_in, tokens_out):
        """Calculate cost of API call"""
        # GPT-3.5 pricing
        return (tokens_in * 0.0015 + tokens_out * 0.002) / 1000
    
    def _save_response(self, result):
        """Save response to log file"""
        try:
            with open(f"data/scout_results.jsonl", "a") as f:
                f.write(json.dumps({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "result": result
                }) + "\n")
        except Exception as e:
            logger.error(f"Error saving scout result: {e}")