# NBA Encyclopedia

A Streamlit-powered NBA analytics app with live stats, player/team cards, standings, comparisons, and an AI analyst agent.

## Features
- Live player and team stats via NBA API
- Player comparison with career accolades and shot zones
- Team standings with tiebreakers and playoff markers
- AI analyst powered by Groq (LLaMA 3.3) + Tavily web search
- Legends database (MJ, Kobe, Shaq, Kareem, etc.)

## Setup

- bash
# Clone the repo
- git clone https://github.com/YOUR_USERNAME/nba-encyclopedia.git
- cd nba-encyclopedia

# Create virtual environment
- python3 -m venv venv
- source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
- pip install -r requirements.txt

# Add your API keys
- cp .env.example .env
# Edit .env with your keys

# Run
- streamlit run app.py
```

# Environment Variables
- Create a `.env` file with: