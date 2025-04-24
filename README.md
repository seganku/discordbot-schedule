# Discord Schedule Notifications Bot - Installation & Usage

## Prerequisites
- Python 3.9 or higher
- [Discord bot token](https://discord.com/developers/applications)

## Installation

### 1. Clone the repository (if applicable)
```bash
git clone https://github.com/seganku/schedule-notifications.git
```

### 2. Set up virtual environment (recommended)
```bash
python -m venv schedule-notifications
cd schedule-notifications

# Activate on Linux/Mac:
source bin/activate

# Activate on Windows:
.\Scripts\activate
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

## First Run Setup
The bot will:
* Create scheduled_notifications.db automatically
* Print an invite URL with required permissions
You can use the printed invite URL to add the bot to your server

### Command Reference
| Command |	Description |	Example |
|:--------|:------------|:--------|
| /schedule #channel YYYY-MM-DD HH:MM message | Schedule a notification	| /schedule #general 2024-12-25 00:00 "Merry Christmas!" |
| /scheduled | List all scheduled notifications |  |
| /unschedule ID | Remove a scheduled notification | /unschedule 5 |
| /schedule_help | Show command help |  |



