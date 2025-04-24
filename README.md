# Discord Notification Scheduler Bot - Installation & Usage

## Prerequisites
- Python 3.9 or higher
- Discord bot token ([create one here](https://discord.com/developers/applications))

## Installation

### 1. Clone the repository (if applicable)
```bash
git clone https://github.com/your-repo/discord-scheduler-bot.git
cd discord-scheduler-bot
```
### 2. Set up virtual environment (recommended)
```bash
python -m venv venv

# Activate on Linux/Mac:
source venv/bin/activate

# Activate on Windows:
.\venv\Scripts\activate
```
### 3. Install dependencies
```bash
pip install -r requirements.txt
```
### 4. Configure Environment
Create a `.env` file with:
```bash
echo "DISCORD_TOKEN=your_bot_token_here" > .env
echo "CLIENT_ID=your_bot_client_id_here" >> .env
```

## Usage
### Starting the bot
```bash
python bot.py
```
