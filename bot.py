import os
import sqlite3
import datetime
import time
import nextcord
from nextcord.ext import commands, tasks
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

# Constants
DATABASE_FILE = "scheduled_notifications.db"
MAX_RETRY_DELAY = 300  # 5 minutes in seconds
UTC = datetime.timezone.utc

# Initialize database
def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS notifications
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  channel_id INTEGER NOT NULL,
                  scheduled_time TEXT NOT NULL,
                  message TEXT NOT NULL,
                  user_id INTEGER NOT NULL)''')
    conn.commit()
    conn.close()

# Helper function for timestamped console output
def log(message: str):
    timestamp = datetime.datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

# Bot class
class NotificationBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connected = False
        self.last_connect_time = None
        self.retry_count = 0
        init_db()  # Initialize database on startup

    async def on_ready(self):
        if not self.connected:
            self.connected = True
            self.retry_count = 0
            self.last_connect_time = datetime.datetime.now(UTC)
            log(f"Successfully reconnected to Discord as {self.user} (ID: {self.user.id})")
        else:
            log(f"Logged in as {self.user} (ID: {self.user.id})")
            self.check_scheduled_notifications.start()
            self.print_invite_url()

    async def on_disconnect(self):
        if self.connected:
            self.connected = False
            log("Disconnected from Discord. Attempting to reconnect...")

    def print_invite_url(self):
        permissions = nextcord.Permissions()
        permissions.send_messages = True
        permissions.read_messages = True
        permissions.manage_messages = True  # Needed for slash commands
        permissions.mention_everyone = True  # Needed for @everyone/@here mentions

        client_id = os.getenv("CLIENT_ID", self.user.id)
        invite_url = nextcord.utils.oauth_url(
            client_id,
            permissions=permissions
        )
        log(f"Invite URL: {invite_url}")

    @tasks.loop(seconds=60)
    async def check_scheduled_notifications(self):
        now = datetime.datetime.now(UTC)
        notifications = get_notifications()
        
        for notification in notifications:
            notification_id, channel_id, scheduled_time_str, message = notification
            scheduled_time = datetime.datetime.fromisoformat(scheduled_time_str)
            
            if scheduled_time <= now:
                channel = self.get_channel(channel_id)
                if channel:
                    try:
                        await channel.send(message)
                        log(f"Sent notification ID {notification_id} in channel {channel_id}")
                    except Exception as e:
                        log(f"Failed to send notification ID {notification_id} in channel {channel_id}: {str(e)}")
                else:
                    log(f"Failed to send notification ID {notification_id} - channel {channel_id} not found")
                
                delete_notification(notification_id)

# Create bot instance
intents = nextcord.Intents.default()
bot = NotificationBot(intents=intents)

# Database operations
def add_notification(channel_id: int, scheduled_time: datetime.datetime, message: str, user_id: int) -> int:
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO notifications (channel_id, scheduled_time, message, user_id) VALUES (?, ?, ?, ?)",
              (channel_id, scheduled_time.isoformat(), message, user_id))
    notification_id = c.lastrowid
    conn.commit()
    conn.close()
    return notification_id

def get_notifications() -> list:
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("SELECT id, channel_id, scheduled_time, message FROM notifications ORDER BY scheduled_time")
    notifications = c.fetchall()
    conn.close()
    return notifications

def get_notification_by_id(notification_id: int) -> Optional[tuple]:
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("SELECT id, channel_id, scheduled_time, message, user_id FROM notifications WHERE id = ?", (notification_id,))
    notification = c.fetchone()
    conn.close()
    return notification

def delete_notification(notification_id: int) -> bool:
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
    rows_affected = c.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0

# Slash commands
@bot.slash_command(name="schedule", description="Schedule a notification to be sent at a specific time")
async def schedule(
    interaction: nextcord.Interaction,
    channel: nextcord.TextChannel = nextcord.SlashOption(
        name="channel",
        description="The channel to send the notification to",
        required=True
    ),
    time_str: str = nextcord.SlashOption(
        name="time",
        description="The time to send the notification (YYYY-mm-dd HH:MM in UTC)",
        required=True
    ),
    message: str = nextcord.SlashOption(
        name="message",
        description="The message to send (can include mentions)",
        required=True
    )
):
    try:
        scheduled_time = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
    except ValueError:
        await interaction.response.send_message("Invalid time format. Please use YYYY-mm-dd HH:MM (UTC).", ephemeral=True)
        log(f"User {interaction.user} provided invalid time format: {time_str}")
        return

    now = datetime.datetime.now(UTC)
    if scheduled_time <= now:
        await interaction.response.send_message("Scheduled time must be in the future.", ephemeral=True)
        log(f"User {interaction.user} tried to schedule a notification in the past")
        return

    notification_id = add_notification(channel.id, scheduled_time, message, interaction.user.id)
    await interaction.response.send_message(
        f"Notification scheduled for {scheduled_time.strftime('%Y-%m-%d %H:%M')} UTC in {channel.mention} (ID: {notification_id}).",
        ephemeral=True
    )
    log(f"User {interaction.user} scheduled notification ID {notification_id} for {scheduled_time} in channel {channel.id}")

@bot.slash_command(name="scheduled", description="List all scheduled notifications")
async def scheduled(interaction: nextcord.Interaction):
    notifications = get_notifications()
    if not notifications:
        await interaction.response.send_message("No notifications are currently scheduled.", ephemeral=True)
        log(f"User {interaction.user} checked scheduled notifications - none found")
        return

    embed = nextcord.Embed(title="Scheduled Notifications", color=nextcord.Color.blue())
    for n in notifications:
        notification_id, channel_id, scheduled_time_str, message = n
        scheduled_time = datetime.datetime.fromisoformat(scheduled_time_str)
        channel = bot.get_channel(channel_id)
        channel_name = channel.mention if channel else f"Unknown Channel ({channel_id})"

        # Truncate message if too long
        display_message = message if len(message) <= 100 else message[:97] + "..."

        embed.add_field(
            name=f"ID: {notification_id} - {scheduled_time.strftime('%Y-%m-%d %H:%M')} UTC",
            value=f"Channel: {channel_name}\nMessage: {display_message}",
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)
    log(f"User {interaction.user} viewed {len(notifications)} scheduled notifications")

@bot.slash_command(name="unschedule", description="Remove a scheduled notification")
async def unschedule(
    interaction: nextcord.Interaction,
    notification_id: int = nextcord.SlashOption(
        name="id",
        description="The ID of the notification to remove",
        required=True
    )
):
    notification = get_notification_by_id(notification_id)
    if not notification:
        await interaction.response.send_message(f"No notification found with ID {notification_id}.", ephemeral=True)
        log(f"User {interaction.user} tried to unschedule non-existent notification ID {notification_id}")
        return

    # Check if the user is the one who created the notification or has admin permissions
    _, channel_id, scheduled_time_str, message, user_id = notification
    if interaction.user.id != user_id and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You can only unschedule your own notifications unless you're an admin.", ephemeral=True)
        log(f"User {interaction.user} tried to unschedule notification ID {notification_id} belonging to user {user_id}")
        return

    if delete_notification(notification_id):
        scheduled_time = datetime.datetime.fromisoformat(scheduled_time_str)
        await interaction.response.send_message(
            f"Notification ID {notification_id} scheduled for {scheduled_time.strftime('%Y-%m-%d %H:%M')} UTC has been canceled.",
            ephemeral=True
        )
        log(f"User {interaction.user} unscheduled notification ID {notification_id}")
    else:
        await interaction.response.send_message(f"Failed to cancel notification ID {notification_id}.", ephemeral=True)
        log(f"User {interaction.user} failed to unschedule notification ID {notification_id}")

@bot.slash_command(name="schedule_help", description="Get help with the schedule commands")
async def schedule_help(
    interaction: nextcord.Interaction,
    command: Optional[str] = nextcord.SlashOption(
        name="command",
        description="The specific command to get help with",
        required=False,
        choices=["schedule", "scheduled", "unschedule"]
    )
):
    if not command:
        # General help
        embed = nextcord.Embed(title="Schedule Bot Help", color=nextcord.Color.green())
        embed.add_field(
            name="/schedule <channel> <YYYY-mm-dd HH:MM> <message>",
            value="Schedule a notification to be sent at a specific time",
            inline=False
        )
        embed.add_field(
            name="/scheduled",
            value="List all scheduled notifications",
            inline=False
        )
        embed.add_field(
            name="/unschedule <ID>",
            value="Remove a scheduled notification",
            inline=False
        )
        embed.add_field(
            name="/schedule_help [command]",
            value="Get detailed help about a specific command",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        log(f"User {interaction.user} viewed general help")
    else:
        # Specific command help
        embed = nextcord.Embed(title=f"Help for /{command}", color=nextcord.Color.green())
        if command == "schedule":
            embed.description = "Schedule a notification to be sent at a specific time in a specific channel."
            embed.add_field(
                name="Usage",
                value="/schedule <#channel> <YYYY-mm-dd HH:MM> <message>",
                inline=False
            )
            embed.add_field(
                name="Example",
                value='`/schedule #general 2023-12-25 00:00 "Merry Christmas! @everyone"`',
                inline=False
            )
            embed.add_field(
                name="Notes",
                value="- Time must be in UTC\n- You can mention users, roles, @everyone, or @here in the message",
                inline=False
            )
        elif command == "scheduled":
            embed.description = "List all currently scheduled notifications."
            embed.add_field(
                name="Usage",
                value="/scheduled",
                inline=False
            )
            embed.add_field(
                name="Output",
                value="Returns an embed showing all scheduled notifications with their IDs, scheduled times, channels, and message previews.",
                inline=False
            )
        elif command == "unschedule":
            embed.description = "Remove a scheduled notification."
            embed.add_field(
                name="Usage",
                value="/unschedule <ID>",
                inline=False
            )
            embed.add_field(
                name="Example",
                value="`/unschedule 42`",
                inline=False
            )
            embed.add_field(
                name="Notes",
                value="- You can only unschedule your own notifications unless you're an admin\n- Get notification IDs from /scheduled",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        log(f"User {interaction.user} viewed help for command: {command}")

# Run the bot
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        log("Error: DISCORD_TOKEN not found in .env file")
        exit(1)

    while True:
        try:
            bot.run(token)
        except nextcord.errors.HTTPException as e:
            if e.status == 429:
                # Rate limited
                retry_after = e.retry_after
                log(f"Rate limited. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
                continue
            else:
                log(f"HTTP error: {e}")
                raise
        except Exception as e:
            log(f"Error: {e}")

            # Exponential backoff for reconnection
            if not bot.connected:
                delay = min(2 ** bot.retry_count, MAX_RETRY_DELAY)
                bot.retry_count += 1
                log(f"Attempting to reconnect in {delay} seconds...")
                time.sleep(delay)
            else:
                # If we were connected but got an error, exit
                raise
