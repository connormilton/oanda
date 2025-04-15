"""
Team Review Agent
Coordinates agent communication and improves system performance
"""

import logging
import json
from datetime import datetime, timezone
import openai
from prompts.collaborative_trading_prompts import CollaborativeTradingPrompts

logger = logging.getLogger("CollaborativeTrader")

class TeamReviewer:
    """Team Review Agent that coordinates the trading team"""
    
    def __init__(self, budget_manager):
        self.model = "gpt-4-turbo-preview"
        self.cost_estimate = 0.40
        self.budget_manager = budget_manager
    
    def run(self, agent_responses, market_data, account_data, positions, memory):
        """Run team review to coordinate and improve the agents"""
        logger.info("Running Team Review")
        
        try:
            # Skip if not all agents have run
            if not all(agent_responses.values()):
                logger.warning("Cannot run team review - missing agent responses")
                return None
            
            # Calculate daily performance
            # In a production system, this would come from actual P&L tracking
            daily_perf = {
                "profit_loss": 0,  # Placeholder
                "return_percent": memory.memory.get("daily_return", 0),
                "winning_trades": 0,  # Placeholder
                "losing_trades": 0    # Placeholder
            }
            
            # Build prompt using template
            team_review_prompt = CollaborativeTradingPrompts.team_review(
                agent_responses,
                memory.memory,
                market_data,
                positions,
                account_data,
                daily_perf
            )
            
            # Check budget
            if not self.budget_manager.can_spend(self.cost_estimate):
                logger.warning("Insufficient budget for Team Review agent")
                return None
            
            # Call LLM API
            result = self._call_llm(team_review_prompt)
            
            if result:
                logger.info("Team review completed")
                
                # Update agent feedback from team review
                if "agent_feedback" in result:
                    for agent, feedback in result["agent_feedback"].items():
                        memory.update_feedback(agent, feedback)
                
                # Log any requests for the human operator
                if "requests_for_human" in result:
                    requests = result["requests_for_human"]
                    logger.info(f"Requests for human operator: {requests}")
                    
                    # Save to a dedicated file for the human to review
                    with open("data/human_requests.jsonl", "a") as f:
                        f.write(json.dumps({
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "requests": requests
                        }) + "\n")
                
                # Save response for logging
                self._save_response(result)
                
                return result
            else:
                logger.warning("Team review produced no result")
                return None
                
        except Exception as e:
            logger.error(f"Error in team review: {e}")
            return None
    
    def _call_llm(self, prompt):
        """Call LLM API with appropriate model"""
        try:
            # Build parameters
            params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a forex trading team coordinator that works to improve collaboration between trading agents."},
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
            self.budget_manager.log_usage("team_review", tokens_in, tokens_out, cost)
            
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
            with open(f"data/team_review_results.jsonl", "a") as f:
                f.write(json.dumps({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "result": result
                }) + "\n")
        except Exception as e:
            logger.error(f"Error saving team review result: {e}")