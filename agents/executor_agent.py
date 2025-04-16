"""
Decision Executor Agent
Makes final trading decisions and manages portfolio risk
"""

import logging
import json
from datetime import datetime, timezone
import openai
from prompts.collaborative_trading_prompts import CollaborativeTradingPrompts

logger = logging.getLogger("CollaborativeTrader")

class ExecutorAgent:
    """Executor Agent that makes final trading decisions"""
    
    def __init__(self, budget_manager):
        self.model = "gpt-4-turbo-preview"
        self.cost_estimate = 0.60
        self.budget_manager = budget_manager
    
    def run(self, analysis_results, market_data, account_data, positions, memory):
        """Run the executor agent to make trading decisions"""
        logger.info("Running Executor Agent")
        
        try:
            # Exit if no analysis results
            if not analysis_results:
                logger.warning("No analysis results for execution")
                return None
            
            # Pre-process analysis results to handle any string ratio formats
            self._preprocess_analysis_results(analysis_results)
            
            # Get recent trades and trade history
            recent_trades = memory.get_recent_trades(5)
            all_trades = memory.get_all_trades()
            
            # Build prompt using template
            executor_prompt = CollaborativeTradingPrompts.decision_maker(
                analysis_results,
                account_data,
                positions,
                memory.memory,
                market_data,
                recent_trades,
                all_trades
            )
            
            # Check budget
            if not self.budget_manager.can_spend(self.cost_estimate):
                logger.warning("Insufficient budget for Executor agent")
                return None
            
            # Call LLM API
            result = self._call_llm(executor_prompt)
            
            if result:
                logger.info(f"Executor generated {len(result.get('trade_actions', []))} trades and {len(result.get('position_actions', []))} position actions")
                
                # Process results to ensure all values are proper types and conform to risk management
                self._postprocess_results(result, account_data)
                
                # Save self-improvement suggestions
                if "self_improvement" in result:
                    memory.update_feedback("executor", result["self_improvement"])
                
                # Save response for logging
                self._save_response(result)
                
                return result
            else:
                logger.warning("Executor agent produced no result")
                return None
                
        except Exception as e:
            logger.error(f"Error in executor agent: {e}")
            return None
    
    def _preprocess_analysis_results(self, analysis_results):
        """Pre-process analysis results to handle string ratio formats"""
        for result in analysis_results:
            # Convert risk_reward if it's a string ratio like "1:2"
            if "risk_reward" in result and isinstance(result["risk_reward"], str):
                try:
                    if ":" in result["risk_reward"]:
                        parts = result["risk_reward"].split(":")
                        if len(parts) == 2:
                            risk = float(parts[0].strip())
                            reward = float(parts[1].strip())
                            result["risk_reward"] = reward / risk
                            logger.info(f"Converted risk_reward ratio '{result['risk_reward']}' to {reward/risk}")
                except Exception as e:
                    logger.warning(f"Could not convert risk_reward ratio: {e}")
                    # Set a default value
                    result["risk_reward"] = 2.0
    
    def _postprocess_results(self, result, account_data):
        """Post-process results to ensure proper data types and risk management compliance"""
        account_balance = float(account_data.get('balance', 1000))
        
        if "trade_actions" in result:
            for trade in result["trade_actions"]:
                # Handle risk_reward conversions
                if "risk_reward" in trade and isinstance(trade["risk_reward"], str):
                    try:
                        if ":" in trade["risk_reward"]:
                            parts = trade["risk_reward"].split(":")
                            if len(parts) == 2:
                                risk = float(parts[0].strip())
                                reward = float(parts[1].strip())
                                trade["risk_reward"] = reward / risk
                        else:
                            trade["risk_reward"] = float(trade["risk_reward"])
                    except Exception as e:
                        logger.warning(f"Could not convert trade risk_reward: {e}")
                        trade["risk_reward"] = 2.0
                
                # Ensure risk_percent is a float and within limits (1-5%)
                if "risk_percent" in trade:
                    try:
                        trade["risk_percent"] = float(trade["risk_percent"])
                        # Enforce risk limits
                        if trade["risk_percent"] < 1.0:
                            logger.warning(f"Risk percentage {trade['risk_percent']}% below minimum 1%. Adjusting to 1%.")
                            trade["risk_percent"] = 1.0
                        elif trade["risk_percent"] > 5.0:
                            logger.warning(f"Risk percentage {trade['risk_percent']}% exceeds maximum 5%. Capping at 5%.")
                            trade["risk_percent"] = 5.0
                    except Exception as e:
                        logger.warning(f"Could not convert risk_percent to float: {trade.get('risk_percent')}. Setting to default 1%.")
                        trade["risk_percent"] = 1.0
                else:
                    # If risk_percent not provided, assign based on analysis quality
                    analysis_quality = 0
                    for analysis in result.get("analysis_results", []):
                        if analysis.get("epic") == trade.get("epic"):
                            analysis_quality = analysis.get("analysis_quality", 0)
                            break
                    
                    # Set risk based on quality
                    if analysis_quality >= 8:
                        trade["risk_percent"] = 3.0  # High quality = higher risk
                    elif analysis_quality >= 6:
                        trade["risk_percent"] = 2.0  # Medium quality = medium risk
                    else:
                        trade["risk_percent"] = 1.0  # Low quality = low risk
                
                # Set size based on risk_percent if not provided
                # This helps maintain backward compatibility
                if "size" not in trade or not isinstance(trade["size"], (int, float)):
                    # Calculate size as a function of risk_percent
                    # This is a simple approximation - the actual calculation happens in the connector
                    risk_amount = account_balance * (trade["risk_percent"] / 100)
                    trade["size"] = risk_amount / 10  # Simplified conversion
                    logger.info(f"Set size to {trade['size']} based on risk_percent {trade['risk_percent']}%")
                
                # Ensure all required fields are present
                required_fields = ["action_type", "epic", "direction", "risk_percent"]
                missing_fields = [field for field in required_fields if field not in trade]
                if missing_fields:
                    logger.warning(f"Trade missing required fields: {missing_fields}")
    
    def _call_llm(self, prompt):
        """Call LLM API with appropriate model"""
        try:
            # Build parameters
            params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a forex trading executor that works in a collaborative team of trading agents."},
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
            self.budget_manager.log_usage("executor", tokens_in, tokens_out, cost)
            
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
        # GPT-4 pricing
        return (tokens_in * 0.03 + tokens_out * 0.06) / 1000
    
    def _save_response(self, result):
        """Save response to log file"""
        try:
            with open(f"data/executor_results.jsonl", "a") as f:
                f.write(json.dumps({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "result": result
                }) + "\n")
        except Exception as e:
            logger.error(f"Error saving executor result: {e}")