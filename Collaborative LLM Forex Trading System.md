# Collaborative LLM Forex Trading System (OANDA)

A multi-agent LLM system for forex trading using OANDA's API. This system employs a team of specialized agents that collaborate to identify trading opportunities, analyze market data, and execute trades.

## System Architecture

The system consists of four specialized LLM agents:

1. **Scout Agent**: Identifies potential trading opportunities across forex pairs
2. **Strategist Agent**: Performs in-depth technical analysis on the opportunities
3. **Executor Agent**: Makes final trading decisions and manages risk
4. **Team Reviewer**: Coordinates between agents and improves system performance

## Requirements

- Python 3.8+
- OANDA API account (practice or live)
- OpenAI API key

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/collaborative-llm-forex-trading.git
   cd collaborative-llm-forex-trading
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   ```
   cp .env.template .env
   ```
   
   Edit the `.env` file with your OANDA API token, account ID, and OpenAI API key.

## OANDA API Setup

1. Create an OANDA account at [OANDA.com](https://www.oanda.com/)
2. Generate an API token in your OANDA account dashboard
3. Note your account ID

## Configuration

Key environment variables:

- `OANDA_API_TOKEN`: Your OANDA API token
- `OANDA_ACCOUNT_ID`: Your OANDA account ID
- `OANDA_PRACTICE`: Set to "True" for practice account, "False" for live account
- `OPENAI_API_KEY`: Your OpenAI API key
- `DAILY_LLM_BUDGET`: Maximum daily budget for LLM API calls in USD

## Usage

Run the system:

```
python main.py
```

The system will:
1. Connect to your OANDA account
2. Start the trading loop with the collaborative agents
3. Analyze market data and execute trades based on agent decisions
4. Log all activities and trades

## Directory Structure

- `agents/` - LLM agent implementations
  - `scout_agent.py` - Market opportunity identification
  - `strategist_agent.py` - Technical analysis
  - `executor_agent.py` - Trade decision and execution
  - `team_reviewer.py` - Team coordination
  
- `core/` - Core system components
  - `budget_manager.py` - LLM API usage tracking
  - `data_collector.py` - Market data collection
  - `system_controller.py` - Main workflow orchestration
  - `trading_memory.py` - Trading history and system state
  
- `prompts/` - LLM prompt templates
  - `collaborative_trading_prompts.py` - Specialized prompts for each agent
  
- `utils/` - Utility functions
  - `oanda_connector.py` - OANDA API interaction

## Trading Pairs

The system trades major forex pairs:
- EUR/USD
- USD/JPY
- GBP/USD
- AUD/USD
- USD/CAD
- GBP/JPY
- EUR/JPY
- AUD/JPY
- EUR/GBP
- USD/CHF
- NZD/USD
- AUD/NZD

## Risk Management

The system implements risk management through:
- Position sizing based on account balance
- Stop loss placement
- Take profit targets
- Correlation management
- Daily return targets

## Data Storage

Trading data is stored in the `data/` directory:
- Trading history
- Agent outputs
- System memory
- Budget usage logs

## Warning

This is an experimental system. Use at your own risk. It is recommended to:
1. Start with a practice account
2. Use small position sizes
3. Monitor the system's performance before scaling up

## License

[MIT License](LICENSE)