# collaborative_trading_prompts.py - Advanced prompts for collaborative LLM forex trading agents

class CollaborativeTradingPrompts:
    """Advanced prompt templates for a team of 3 collaborative trading agents"""
    
    @staticmethod
    def market_scanner(market_data, account_data, positions, recent_trades, trade_logs=None, agent_feedback=None):
        """
        Build prompt for market scanner agent (Scout)
        The scout identifies opportunities and maintains market awareness
        """
        # Format market data summary
        market_summary = ""
        for epic, data in market_data.items():
            if "current" in data:
                current = data["current"]
                market_summary += f"\n{epic}: Bid/Ask: {current.get('bid')}/{current.get('offer')}"
        
        # Format positions
        positions_info = "No open positions"
        open_position_count = 0
        if not positions.empty:
            positions_info = positions.to_string()
            open_position_count = len(positions)
        
        # Format recent trades
        recent_trades_text = "No recent trades"
        if recent_trades:
            recent_trades_text = "\n".join([
                f"- {t.get('timestamp', '')[:10]} {t.get('epic')} {t.get('direction')}: {t.get('outcome')} " +
                f"(Reason: {t.get('pattern', 'Unknown pattern')})"
                for t in recent_trades
            ])
        
        # Get feedback from other agents
        feedback_section = ""
        if agent_feedback:
            feedback_section = "\n## Recent Agent Feedback\n"
            for agent, feedback in agent_feedback.items():
                feedback_section += f"### {agent}\n{feedback}\n"
        
        # Trade log insights
        trade_log_insights = ""
        if trade_logs:
            # Extract patterns that worked well
            successful_patterns = {}
            failed_patterns = {}
            for trade in trade_logs:
                pattern = trade.get("pattern", "Unknown")
                outcome = trade.get("outcome", "").upper()
                
                if "WIN" in outcome or "PROFIT" in outcome:
                    successful_patterns[pattern] = successful_patterns.get(pattern, 0) + 1
                elif "LOSS" in outcome or "STOPPED" in outcome:
                    failed_patterns[pattern] = failed_patterns.get(pattern, 0) + 1
            
            # Format insights
            trade_log_insights = "\n## Trade Log Insights\n"
            
            # Successful patterns
            trade_log_insights += "### Successful Patterns\n"
            for pattern, count in sorted(successful_patterns.items(), key=lambda x: x[1], reverse=True)[:3]:
                trade_log_insights += f"- {pattern}: {count} successful trades\n"
            
            # Failed patterns
            trade_log_insights += "\n### Challenging Patterns\n"
            for pattern, count in sorted(failed_patterns.items(), key=lambda x: x[1], reverse=True)[:3]:
                trade_log_insights += f"- {pattern}: {count} failed trades\n"
        
        # Create the main part of the prompt with variables
        main_prompt = f"""
# Forex Market Scout Agent

## Your Role and Goals
You are the Market Scout in a team of three collaborative trading agents targeting 10% daily returns.
Your specific responsibilities are:
1. Identify promising trading opportunities across forex pairs
2. Maintain broad market awareness and detect correlations
3. Recommend at least 5-7 high-potential opportunities

## Current Trading Status
- Account Balance: {account_data.get('balance')}
- Available Funds: {account_data.get('available')}
- Open Positions: {open_position_count} (Target minimum: 3)
- Daily Return Target: 10% of account

## Open Positions
{positions_info}

## Recent Trading History
{recent_trades_text}
{trade_log_insights}
{feedback_section}

## Current Market Prices
{market_summary}

## Your Task
1. Analyze all forex pairs to identify 5-7 high-potential trading opportunities
2. Consider correlation between currencies and overall market conditions
3. Prioritize finding setups with clear price action patterns
4. Evaluate how your suggestions complement existing positions
5. If we have fewer than 3 open positions, prioritize finding new opportunities

## Self-Improvement
Reflect on past trade performance from the logs. How can you improve your opportunity identification? What patterns have been working? What information would help you make better recommendations?
"""
        
        # Use raw string for response format to avoid f-string formatting issues
        response_format = r"""
## Response Format
Respond with a JSON object containing:
1. "market_assessment" with:
   - "overall_condition": "trending/ranging/volatile/uncertain"
   - "overall_bias": "bullish/bearish/neutral"
   - "correlations": [key currency correlations you've identified]
   - "summary": "Brief 1-2 sentence market summary"

2. "opportunities" array with the best trading setups:
   - "epic": Currency pair code
   - "pattern": Specific pattern identified
   - "direction": "BUY" or "SELL"
   - "conviction": Rating from 1-10
   - "timeframe": "short-term/medium-term/long-term"
   - "reasoning": Detailed explanation of the opportunity
   - "key_levels": Important price levels to watch

3. "self_improvement":
   - "pattern_effectiveness": Assessment of which patterns have worked best
   - "questions_for_team": Questions for other agents about what information would help you
   - "suggestions": Ideas to improve the overall trading system
"""

        # Combine main prompt with response format
        return main_prompt + response_format

    @staticmethod
    def analysis_engine(opportunities, market_data, account_data, positions, system_memory, previous_analyses=None):
        """
        Build prompt for analysis agent (Strategist)
        The strategist performs deep technical analysis and develops trading plans
        """
        # Format selected opportunities
        opps_section = ""
        for opp in opportunities:
            epic = opp.get("epic")
            if epic in market_data:
                data = market_data[epic]
                
                # Format price data
                price_info = ""
                if "h1" in data and data["h1"]:
                    candles = data["h1"][-5:]  # Last 5 candles
                    for candle in reversed(candles):
                        from datetime import datetime
                        dt = datetime.fromisoformat(candle.get('timestamp', ''))
                        time_str = dt.strftime("%H:%M")
                        price_info += f"\n- {time_str}: O={candle.get('open'):.5f} H={candle.get('high'):.5f} L={candle.get('low'):.5f} C={candle.get('close'):.5f}"
                
                opps_section += f"""
## {epic}
- Pattern: {opp.get('pattern')}
- Direction: {opp.get('direction')}
- Conviction: {opp.get('conviction')}/10
- Reasoning: {opp.get('reasoning')}
- Key Levels: {opp.get('key_levels', 'None specified')}

### Recent Price Data:
{price_info}
"""
        
        # Format positions
        positions_info = "No open positions"
        open_position_count = 0
        if not positions.empty:
            positions_info = positions.to_string()
            open_position_count = len(positions)
        
        # Previous analyses insights
        previous_analyses_section = ""
        if previous_analyses:
            previous_analyses_section = "\n## Previous Analysis Insights\n"
            for pair, analyses in previous_analyses.items():
                if analyses:
                    latest = analyses[-1]
                    previous_analyses_section += f"### {pair}\n"
                    previous_analyses_section += f"- Last Analysis: {latest.get('timestamp', 'Unknown')}\n"
                    previous_analyses_section += f"- Direction: {latest.get('direction', 'Unknown')}\n"
                    previous_analyses_section += f"- Outcome: {latest.get('outcome', 'Pending')}\n"
                    previous_analyses_section += f"- Key Insight: {latest.get('key_insight', 'None')}\n"
        
        # Create the main part of the prompt with variables
        main_prompt = f"""
# Forex Strategist Agent

## Your Role and Goals
You are the Strategic Analyst in a team of three collaborative trading agents targeting 10% daily returns.
Your specific responsibilities are:
1. Perform detailed technical analysis on promising opportunities
2. Determine precise entry/exit points and stop loss levels
3. Create specific trading plans with clear risk management
4. Calculate risk-reward ratios and evaluate trade quality

## Current Trading Status
- Account Balance: {account_data.get('balance')}
- Available Funds: {account_data.get('available')}
- Open Positions: {open_position_count} (Target minimum: 3)
- Daily Return Target: 10% of account
- Win Rate: {system_memory.get('win_count', 0)}/{system_memory.get('trade_count', 0)} trades

## Open Positions
{positions_info}

{previous_analyses_section}

## Selected Opportunities
{opps_section}

## Your Task
1. Analyze each opportunity and determine if it meets your quality criteria
2. For each valid opportunity, develop a complete trading plan with:
   - Precise entry zone with ideal price and acceptable range
   - Multiple take profit targets based on key levels
   - Stop loss level with clear reasoning
   - Position sizing recommendation based on risk
3. Calculate and evaluate risk-reward ratios (aim for 1:2 minimum)
4. If we have fewer than 3 open positions, prioritize finding executable trades

## Self-Improvement
Reflect on your analysis techniques. What additional information or tools would help you create better trade plans? What patterns have had the highest success rate? How can you improve your stop placement?
"""
        
        # Use raw string for response format to avoid f-string formatting issues
        response_format = r"""
## Response Format
Respond with a JSON object containing:
1. "analysis_results" array with detailed analysis for each pair:
   - "epic": Currency pair code
   - "direction": "BUY" or "SELL"
   - "analysis_quality": Rating from 1-10
   - "entry_zone": {"ideal": price, "range_low": price, "range_high": price}
   - "stop_loss": {"price": level, "pips": distance, "reasoning": explanation}
   - "take_profit": [{"level": price, "pips": distance, "probability": confidence}]
   - "risk_reward": Calculated R:R ratio
   - "position_size_recommendation": Percentage of account or lot size
   - "trading_plan": Detailed explanation of the setup and execution
   - "key_indicators": Important technical indicators supporting the trade

2. "market_insights": Overall insights from your analysis

3. "self_improvement":
   - "analysis_effectiveness": Assessment of your previous analyses
   - "questions_for_team": Questions for other agents that would help you
   - "suggestions": Ideas to improve your analysis approach
"""

        # Combine main prompt with response format
        return main_prompt + response_format

    @staticmethod
    def decision_maker(analysis_results, account_data, positions, system_memory, market_data, 
                       recent_trades=None, execution_history=None):
        """
        Build prompt for decision agent (Executor)
        The executor makes final decisions and manages overall portfolio risk
        """
        # Format analysis results
        analysis_section = ""
        for result in analysis_results:
            epic = result.get("epic")
            
            # Format take profit levels
            take_profit_text = ""
            for idx, tp in enumerate(result.get("take_profit", [])):
                take_profit_text += f"TP{idx+1}: {tp.get('level')} ({tp.get('pips')} pips, {tp.get('probability')}% prob)\n      "
            
            analysis_section += f"""
## {epic}
- Direction: {result.get('direction')}
- Analysis Quality: {result.get('analysis_quality')}/10
- Entry Zone: {result.get('entry_zone', {}).get('ideal')} (Range: {result.get('entry_zone', {}).get('range_low')} - {result.get('entry_zone', {}).get('range_high')})
- Stop Loss: {result.get('stop_loss', {}).get('price')} ({result.get('stop_loss', {}).get('pips')} pips)
- Take Profit: {take_profit_text}
- Risk-Reward: {result.get('risk_reward')}
- Size Recommendation: {result.get('position_size_recommendation')}
- Trading Plan: {result.get('trading_plan')}
"""
        
        # Format positions
        positions_info = "No open positions"
        open_position_count = 0
        if not positions.empty:
            positions_info = positions.to_string()
            open_position_count = len(positions)
        
        # Format recent trades
        recent_trades_text = "No recent trades"
        if recent_trades:
            recent_trades_text = "\n".join([
                f"- {t.get('timestamp', '')[:10]} {t.get('epic')} {t.get('direction')}: {t.get('outcome')} " +
                f"(Risk: {t.get('risk_percent', 'Unknown')}%, R:R: {t.get('risk_reward', 'Unknown')})"
                for t in recent_trades
            ])
        
        # Get system performance metrics
        win_rate = 0
        if system_memory.get('trade_count', 0) > 0:
            win_rate = (system_memory.get('win_count', 0) / system_memory.get('trade_count', 0)) * 100
        
        # Execution history insights
        execution_insights = ""
        if execution_history:
            # Extract patterns that worked well
            position_sizes = []
            risk_percents = []
            risk_rewards = []
            
            for trade in execution_history:
                if "size" in trade:
                    position_sizes.append(float(trade["size"]))
                if "risk_percent" in trade:
                    risk_percents.append(float(trade["risk_percent"]))
                if "risk_reward" in trade:
                    risk_rewards.append(float(trade["risk_reward"]))
            
            # Calculate averages
            avg_size = sum(position_sizes) / len(position_sizes) if position_sizes else 0
            avg_risk = sum(risk_percents) / len(risk_percents) if risk_percents else 0
            avg_rr = sum(risk_rewards) / len(risk_rewards) if risk_rewards else 0
            
            execution_insights = f"""
## Execution History Insights
- Average Position Size: {avg_size:.2f}
- Average Risk per Trade: {avg_risk:.2f}%
- Average Risk-Reward: {avg_rr:.2f}
"""
        
        # Calculate daily progress toward 10% goal
        daily_return = system_memory.get("daily_return", 0)
        daily_goal = 10.0  # 10% daily target
        
        # Current market conditions (brief)
        market_conditions = ""
        for epic, data in list(market_data.items())[:5]:  # Just show first 5 pairs
            if "current" in data:
                current = data["current"]
                market_conditions += f"\n- {epic}: {current.get('bid')}/{current.get('offer')}"
        
        # Create the main part of the prompt with variables
        main_prompt = f"""
# Forex Executor Agent

## Your Role and Goals
You are the Decision Executor in a team of three collaborative trading agents targeting 10% daily returns.
Your specific responsibilities are:
1. Make final trading decisions based on analysis
2. Manage overall portfolio risk and exposure
3. Ensure we maintain at least 3 open positions at all times
4. Balance risk across currency pairs and correlations
5. Implement sophisticated stop management strategies

## Current Trading Status
- Account Balance: {account_data.get('balance')}
- Available Funds: {account_data.get('available')}
- Open Positions: {open_position_count} (Target minimum: 3)
- Daily Return Target: 10% of account (Current progress: {daily_return:.2f}%)
- Win Rate: {win_rate:.1f}% ({system_memory.get('win_count', 0)}/{system_memory.get('trade_count', 0)} trades)
- Risk Multiplier: {system_memory.get('risk_multiplier', 1.0)}x

## Current Market Snapshot
{market_conditions}

## Open Positions
{positions_info}

## Recent Trading History
{recent_trades_text}
{execution_insights}

## Analysis Results
{analysis_section}

## Your Task
1. Decide which trade opportunities to execute based on quality and portfolio balance
2. Determine final position sizes and risk levels (aim for consistent risk per trade)
3. If we have fewer than 3 open positions, prioritize opening new positions
4. For existing positions, decide if any need to be closed or have stops adjusted
5. Implement risk management strategies for each new position

## Stop Management Strategies
1. FIXED STOP - Traditional fixed stop loss placement
2. TRAILING STOP - Stop follows price at a fixed distance as it moves in your favor
3. BREAKEVEN STOP - Move stop to entry once trade has moved a certain distance
4. PARTIAL PROFIT - Take profits on part of position at first target

## Self-Improvement
Reflect on execution performance. What position sizing has worked best? Which stop strategies have been most effective? How can you better balance the portfolio to achieve the 10% daily target?
"""
        
        # Use raw string for response format to avoid f-string formatting issues
        response_format = r"""
## Response Format
Respond with a JSON object containing:
1. "trade_actions" array with specific trades to execute:
   - "action_type": "OPEN"
   - "epic": Currency pair code
   - "direction": "BUY" or "SELL"
   - "size": Position size
   - "entry_price": Ideal entry price
   - "entry_range": [lower, upper] range for entry
   - "initial_stop_loss": Initial stop loss level
   - "take_profit_levels": [level1, level2, ...]
   - "risk_percent": Percentage of account risked
   - "risk_reward": Expected R:R ratio
   - "pattern": Pattern being traded
   - "stop_management": [{"type": "strategy", "settings": {"specific": "settings"}}]
   - "reasoning": Detailed reasoning for this execution decision

2. "position_actions" array with actions for existing positions:
   - "action_type": "CLOSE", "UPDATE_STOP", "TAKE_PARTIAL"
   - "epic": Currency pair code
   - "dealId": Deal identifier
   - "new_level": New level for stop or take profit
   - "percentage": Percentage to close (for partial)
   - "reason": Explanation for the action

3. "portfolio_assessment":
   - "current_exposure": Overall market exposure assessment
   - "risk_distribution": How risk is spread across positions
   - "correlation_management": How you're managing correlations
   - "progress_to_daily_goal": Assessment of progress toward 10% target

4. "self_improvement":
   - "execution_effectiveness": Assessment of your decision making
   - "questions_for_team": Questions for other agents that would help you
   - "suggestions": Ideas to improve execution approach
   - "needs_from_user": What you need from the human trader to improve
"""

        # Combine main prompt with response format
        return main_prompt + response_format

    @staticmethod
    def team_review(agent_responses, system_memory, market_data, positions, account_data, daily_perf=None):
        """
        Build prompt for team review and coordination
        This allows the agents to review each other's work and coordinate strategy
        """
        # Format agent responses
        agent_summaries = ""
        for agent, response in agent_responses.items():
            if agent == "scout":
                opportunities = response.get("opportunities", [])
                opps_summary = f"Found {len(opportunities)} opportunities.\n"
                for opp in opportunities[:3]:  # Top 3
                    opps_summary += f"- {opp.get('epic')}: {opp.get('direction')} ({opp.get('conviction')}/10) - {opp.get('pattern')}\n"
                
                agent_summaries += f"""
## Scout's Findings
- Market Assessment: {response.get('market_assessment', {}).get('overall_condition', 'Unknown')} / {response.get('market_assessment', {}).get('overall_bias', 'Unknown')}
- Top Opportunities:
{opps_summary}
- Self-improvement notes: {response.get('self_improvement', {}).get('suggestions', 'None provided')}
"""
            
            elif agent == "strategist":
                analyses = response.get("analysis_results", [])
                analyses_summary = f"Analyzed {len(analyses)} opportunities.\n"
                for analysis in analyses[:3]:  # Top 3
                    analyses_summary += f"- {analysis.get('epic')}: {analysis.get('direction')} (Quality: {analysis.get('analysis_quality')}/10) - R:R {analysis.get('risk_reward')}\n"
                
                agent_summaries += f"""
## Strategist's Analyses
- Key insights: {response.get('market_insights', 'None provided')}
- Top Analyses:
{analyses_summary}
- Self-improvement notes: {response.get('self_improvement', {}).get('suggestions', 'None provided')}
"""
            
            elif agent == "executor":
                trades = response.get("trade_actions", [])
                positions_actions = response.get("position_actions", [])
                trades_summary = f"Executed {len(trades)} trades, modified {len(positions_actions)} positions.\n"
                for trade in trades[:3]:  # Top 3
                    trades_summary += f"- {trade.get('epic')}: {trade.get('direction')} (Risk: {trade.get('risk_percent')}%, R:R: {trade.get('risk_reward')})\n"
                
                agent_summaries += f"""
## Executor's Decisions
- Portfolio assessment: {response.get('portfolio_assessment', {}).get('progress_to_daily_goal', 'Not provided')}
- Actions:
{trades_summary}
- Self-improvement notes: {response.get('self_improvement', {}).get('suggestions', 'None provided')}
"""
        
        # Format daily performance if available
        performance_section = ""
        if daily_perf:
            profit_loss = daily_perf.get('profit_loss', 0)
            return_pct = daily_perf.get('return_percent', 0)
            win_trades = daily_perf.get('winning_trades', 0)
            loss_trades = daily_perf.get('losing_trades', 0)
            
            performance_section = f"""
## Daily Performance Review
- Profit/Loss: {profit_loss}
- Return: {return_pct:.2f}% (Target: 10%)
- Winning Trades: {win_trades}
- Losing Trades: {loss_trades}
- Win Rate: {(win_trades / (win_trades + loss_trades) * 100) if (win_trades + loss_trades) > 0 else 0:.1f}%
"""
        
        # Create the main part of the prompt with variables
        main_prompt = f"""
# Trading Team Review Session

## Current Status
- Account Balance: {account_data.get('balance')}
- Open Positions: {len(positions) if not positions.empty else 0} (Target minimum: 3)
- Win Rate: {(system_memory.get('win_count', 0) / system_memory.get('trade_count', 1)) * 100:.1f}% 
- Risk Multiplier: {system_memory.get('risk_multiplier', 1.0)}x

{performance_section}

## Agent Summaries
{agent_summaries}

## Team Review Questions
1. How are the agents coordinating effectively? What gaps exist in communication?
2. Are we maintaining the minimum of 3 open positions at all times?
3. What strategies are working best toward our 10% daily target?
4. How can each agent better support the others?
5. What information or tools do we need from our human operator?
"""
        
        # Use raw string for response format to avoid f-string formatting issues
        response_format = r"""
## Response Format
Respond with a JSON object containing:
1. "team_assessment":
   - "coordination_quality": Rating from 1-10
   - "progress_to_goal": Assessment of progress toward 10% daily target
   - "key_strengths": What's working well
   - "key_weaknesses": Areas needing improvement

2. "agent_feedback":
   - "scout": Specific feedback and advice for the scout
   - "strategist": Specific feedback and advice for the strategist
   - "executor": Specific feedback and advice for the executor

3. "strategy_adjustments":
   - "risk_management": Suggested changes to risk approach
   - "pair_selection": Suggested changes to market focus
   - "technical_approach": Suggested changes to analysis methods

4. "requests_for_human":
   - Specific questions or requests for the human operator
"""

        # Combine main prompt with response format
        return main_prompt + response_format

    @staticmethod
    def position_manager(positions, market_data, system_memory, execution_history=None):
        """
        Build prompt for position management
        Focuses on managing existing positions rather than opening new ones
        """
        # Format positions
        positions_info = "No open positions"
        if not positions.empty:
            positions_info = positions.to_string()
        
        # Format current market data for relevant pairs
        market_info = ""
        for _, position in positions.iterrows():
            epic = position.get("epic")
            if epic in market_data and "current" in market_data[epic]:
                current = market_data[epic]["current"]
                direction = position.get("direction")
                opening_level = position.get("level")
                current_level = current.get("bid") if direction == "SELL" else current.get("offer")
                
                # Calculate pip movement and profit/loss
                multiplier = 0.01 if "JPY" in epic else 0.0001
                pips_moved = (current_level - opening_level) / multiplier
                if direction == "SELL":
                    pips_moved = -pips_moved
                
                market_info += f"\n## {epic}\n"
                market_info += f"- Current Price: {current.get('bid')}/{current.get('offer')}\n"
                market_info += f"- Opening Level: {opening_level}\n"
                market_info += f"- Movement: {pips_moved:.1f} pips\n"
                
                # Add recent price action
                if "h1" in market_data[epic] and market_data[epic]["h1"]:
                    last_candle = market_data[epic]["h1"][-1]
                    market_info += f"- Latest H1: O={last_candle.get('open'):.5f} H={last_candle.get('high'):.5f} L={last_candle.get('low'):.5f} C={last_candle.get('close'):.5f}\n"
        
        # Position management history
        management_history = ""
        if execution_history:
            updates = [t for t in execution_history if t.get("action_type") in ["UPDATE_STOP", "TAKE_PARTIAL", "CLOSE"]]
            if updates:
                management_history = "\n## Recent Position Management Actions\n"
                for update in updates[:5]:
                    management_history += f"- {update.get('timestamp', '')[:10]} {update.get('epic')} {update.get('action_type')}: {update.get('reason')}\n"
        
        # Create the main part of the prompt with variables
        main_prompt = f"""
# Position Management Agent

## Your Role and Goals
You specialize in managing existing trading positions to:
1. Protect capital by moving stops to breakeven when appropriate
2. Maximize profit by implementing trailing stops
3. Take partial profits at key levels
4. Close positions when technical conditions change

## Current Trading Status
- Account Balance: {system_memory.get('balance')}
- Open Positions: {len(positions) if not positions.empty else 0}
- Win Rate: {(system_memory.get('win_count', 0) / system_memory.get('trade_count', 1)) * 100:.1f}%
- Daily Return Target: 10% of account

## Open Positions
{positions_info}

## Current Market Data
{market_info}

{management_history}

## Your Task
Analyze each open position and determine:
1. If stop loss needs to be adjusted (breakeven, tightened, or trailed)
2. If partial profits should be taken at current levels
3. If any position should be completely closed due to changing conditions
4. The optimal balance between securing profit and allowing room for further movement

## Position Management Strategies
1. BREAKEVEN STOP - Move stop to entry once trade has moved a certain distance in your favor
2. TRAILING STOP - Stop follows price at a fixed distance as it moves in your favor
3. PARTIAL PROFIT - Take profits on part of position at current level
4. FULL CLOSE - Close entire position
5. NO CHANGE - Leave position as is
"""
        
        # Use raw string for response format to avoid f-string formatting issues
        response_format = r"""
## Response Format
Respond with a JSON object containing:
1. "position_actions" array with actions for each position:
   - "action_type": "CLOSE", "UPDATE_STOP", "TAKE_PARTIAL", "NO_CHANGE"
   - "epic": Currency pair code
   - "dealId": Deal identifier
   - "new_level": New level for stop (if applicable)
   - "percentage": Percentage to close (if applicable)
   - "reason": Detailed reasoning for this action

2. "risk_assessment":
   - "overall_portfolio_risk": Assessment of current risk level
   - "primary_threats": Main risks to current positions
   - "recommended_adjustments": General portfolio adjustment recommendations
"""

        # Combine main prompt with response format
        return main_prompt + response_format

    @staticmethod
    def system_optimizer(all_logs, system_memory, budget_status, performance_metrics):
        """
        Build prompt for system optimization agent
        Focuses on overall system improvement based on all available data
        """
        # Format log statistics
        trade_count = len(all_logs.get("trades", []))
        scanner_count = len(all_logs.get("scanner", []))
        analyzer_count = len(all_logs.get("analyzer", []))
        decision_count = len(all_logs.get("decision", []))
        
        win_count = sum(1 for t in all_logs.get("trades", []) if "WIN" in t.get("outcome", "").upper() or "PROFIT" in t.get("outcome", "").upper())
        loss_count = sum(1 for t in all_logs.get("trades", []) if "LOSS" in t.get("outcome", "").upper() or "STOPPED" in t.get("outcome", "").upper())
        win_rate = (win_count / trade_count) * 100 if trade_count > 0 else 0
        
        # Calculate average cost per tier
        avg_scanner_cost = sum(log.get("cost", 0) for log in all_logs.get("budget", []) if log.get("tier") == "scout") / max(1, scanner_count)
        avg_analyzer_cost = sum(log.get("cost", 0) for log in all_logs.get("budget", []) if log.get("tier") == "strategist") / max(1, analyzer_count)
        avg_decision_cost = sum(log.get("cost", 0) for log in all_logs.get("budget", []) if log.get("tier") == "executor") / max(1, decision_count)
        
        # Current budget status
        budget_section = f"""
## Budget Status
- Daily Budget: ${budget_status.get('total_budget', 0):.2f}
- Spent: ${budget_status.get('spent', 0):.2f} ({budget_status.get('percent_used', 0):.1f}%)
- Remaining: ${budget_status.get('remaining', 0):.2f}
- Average Cost per Tier:
  - Scout: ${avg_scanner_cost:.4f}
  - Strategist: ${avg_analyzer_cost:.4f}
  - Executor: ${avg_decision_cost:.4f}
"""
        
        # Performance metrics
        perf_section = f"""
## Performance Metrics
- Trade Count: {trade_count} ({win_count} wins, {loss_count} losses)
- Win Rate: {win_rate:.1f}%
- Average Return per Trade: {performance_metrics.get('avg_return_per_trade', 0):.2f}%
- Average Risk per Trade: {performance_metrics.get('avg_risk_per_trade', 0):.2f}%
- Average Risk:Reward: {performance_metrics.get('avg_risk_reward', 0):.2f}
- Largest Win: {performance_metrics.get('largest_win', 0):.2f}%
- Largest Loss: {performance_metrics.get('largest_loss', 0):.2f}%
"""
        
        # Pattern performance
        pattern_performance = {}
        for trade in all_logs.get("trades", []):
            pattern = trade.get("pattern", "Unknown")
            outcome = trade.get("outcome", "").upper()
            
            if pattern not in pattern_performance:
                pattern_performance[pattern] = {"wins": 0, "losses": 0}
            
            if "WIN" in outcome or "PROFIT" in outcome:
                pattern_performance[pattern]["wins"] += 1
            elif "LOSS" in outcome or "STOPPED" in outcome:
                pattern_performance[pattern]["losses"] += 1
        
        pattern_section = "## Pattern Performance\n"
        for pattern, stats in pattern_performance.items():
            total = stats["wins"] + stats["losses"]
            win_rate = (stats["wins"] / total) * 100 if total > 0 else 0
            if total >= 3:  # Only show patterns with at least 3 trades
                pattern_section += f"- {pattern}: {win_rate:.1f}% win rate ({stats['wins']}/{total} trades)\n"
        
        # Create the main part of the prompt with variables
        main_prompt = f"""
# System Optimization Agent

## Your Role and Goals
You analyze the entire trading system to identify improvements and optimize:
1. Budget allocation between the three agent tiers
2. Trading patterns and strategies that are most effective
3. Risk management and position sizing approaches
4. Overall system efficiency and performance
5. Progress toward the 10% daily return target

{budget_section}

{perf_section}

{pattern_section}

## System Memory
- Trade Count: {system_memory.get('trade_count', 0)}
- Win Count: {system_memory.get('win_count', 0)}
- Loss Count: {system_memory.get('loss_count', 0)}
- Risk Multiplier: {system_memory.get('risk_multiplier', 1.0)}
- Base Risk: {system_memory.get('base_risk', 1.0)}%

## Your Task
Analyze all available data to:
1. Identify the most effective trading patterns and approaches
2. Recommend optimal budget allocation across agent tiers
3. Suggest improvements to risk management parameters
4. Determine if system parameters need adjustment
5. Provide actionable insights to improve performance
"""
        
        # Use raw string for response format to avoid f-string formatting issues
        response_format = r"""
## Response Format
Respond with a JSON object containing:
1. "system_assessment":
   - "overall_performance": Rating from 1-10
   - "progress_to_goal": Assessment of progress toward 10% daily target
   - "key_strengths": What's working well
   - "key_weaknesses": Areas needing improvement

2. "optimization_recommendations":
   - "budget_allocation": {"scout": percentage, "strategist": percentage, "executor": percentage}
   - "risk_parameters": {"base_risk": percentage, "risk_multiplier": factor}
   - "pattern_focus": Array of most effective patterns to prioritize
   - "timeframe_focus": Most effective timeframes to focus on

3. "process_improvements":
   - "scout_recommendations": Specific improvements for the scout agent
   - "strategist_recommendations": Specific improvements for the strategist agent
   - "executor_recommendations": Specific improvements for the executor agent

4. "technical_improvements":
   - Specific technical enhancements to the system
   - Data sources that would improve decision making
   - Algorithmic improvements to consider
"""

        # Combine main prompt with response format
        return main_prompt + response_format