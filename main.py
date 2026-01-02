import os
import json
import asyncio
import random
from pathlib import Path
from typing import List, Union, Optional
from dotenv import load_dotenv

from pyrogram import Client, filters, enums
from pyrogram.types import Message
from pyrogram.errors import (
    FloodWait, PeerIdInvalid, UsernameInvalid,
    UsernameNotOccupied, ChatWriteForbidden,
    UserNotParticipant, ChannelPrivate, ChatAdminRequired
)

# Load environment variables
load_dotenv()

# Configuration from environment
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

# Bot developer info
BOT_DEVELOPER_ID = 5265190519  # JishuEdits User ID
BOT_DEVELOPER_USERNAME = "JishuEdits"  # JishuEdits username

# Configuration file
CONFIG_FILE = "config.json"

class BotConfig:
    """Handles configuration loading and saving"""
    
    DEFAULT_CONFIG = {
        "authorized_users": [],
        "authorized_chats": [],  # For groups/channels where any authorized user can use the bot
        "spam_command": "/s",
        "spam_messages": ["Hello {mention}! Welcome to the group!"],
        "owner_id": OWNER_ID
    }
    
    def __init__(self):
        self.config = self.load_config()
        
    def load_config(self) -> dict:
        """Load configuration from file or create default"""
        if Path(CONFIG_FILE).exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """Save configuration to file"""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=4)
    
    @property
    def authorized_users(self) -> List[int]:
        return self.config.get("authorized_users", [])
    
    @authorized_users.setter
    def authorized_users(self, users: List[int]):
        self.config["authorized_users"] = users
        self.save_config()
    
    @property
    def authorized_chats(self) -> List[int]:
        return self.config.get("authorized_chats", [])
    
    @authorized_chats.setter
    def authorized_chats(self, chats: List[int]):
        self.config["authorized_chats"] = chats
        self.save_config()
    
    @property
    def spam_command(self) -> str:
        return self.config.get("spam_command", "/s")
    
    @spam_command.setter
    def spam_command(self, command: str):
        # Ensure command starts with /
        if not command.startswith('/'):
            command = f'/{command}'
        self.config["spam_command"] = command
        self.save_config()
    
    @property
    def spam_messages(self) -> List[str]:
        return self.config.get("spam_messages", ["Hello {mention}! Welcome to the group!"])
    
    @spam_messages.setter
    def spam_messages(self, messages: List[str]):
        self.config["spam_messages"] = messages
        self.save_config()
    
    def add_spam_message(self, message: str):
        """Add a new spam message to the list"""
        messages = self.spam_messages
        if message not in messages:  # Avoid duplicates
            messages.append(message)
            self.spam_messages = messages
    
    def remove_spam_message(self, index: int):
        """Remove a spam message by index"""
        messages = self.spam_messages
        if 0 <= index < len(messages):
            messages.pop(index)
            self.spam_messages = messages
    
    def add_authorized_chat(self, chat_id: int):
        """Add chat to authorized chats list"""
        chats = self.authorized_chats
        if chat_id not in chats:
            chats.append(chat_id)
            self.authorized_chats = chats
    
    def remove_authorized_chat(self, chat_id: int):
        """Remove chat from authorized chats list"""
        chats = self.authorized_chats
        if chat_id in chats:
            chats.remove(chat_id)
            self.authorized_chats = chats
    
    @property
    def owner_id(self) -> int:
        return self.config.get("owner_id", OWNER_ID)

# Initialize configuration
config = BotConfig()

# Initialize Pyrogram client
app = Client(
    "spam_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    parse_mode=enums.ParseMode.HTML
)

# Utility functions
async def resolve_user_id(user_input: str) -> Optional[int]:
    """
    Resolve username or user_id to user ID
    Returns None if user not found
    """
    try:
        # Check if input is numeric
        if user_input.isdigit() or (user_input.startswith('-') and user_input[1:].isdigit()):
            return int(user_input)
        
        # Check if it's a username
        if user_input.startswith('@'):
            user_input = user_input[1:]
        
        # Try to get user by username
        try:
            user = await app.get_users(user_input)
            return user.id
        except (UsernameInvalid, UsernameNotOccupied, PeerIdInvalid):
            return None
            
    except Exception:
        return None

async def resolve_chat_id(chat_input: str) -> Optional[int]:
    """
    Resolve channel username or chat_id to chat ID
    Returns None if chat not found
    """
    try:
        # Check if input is numeric
        if chat_input.isdigit() or (chat_input.startswith('-') and chat_input[1:].isdigit()):
            return int(chat_input)
        
        # Check if it's a username
        if chat_input.startswith('@'):
            chat_input = chat_input[1:]
        
        # Try to get chat by username
        try:
            chat = await app.get_chat(chat_input)
            return chat.id
        except (UsernameInvalid, UsernameNotOccupied, PeerIdInvalid):
            return None
            
    except Exception:
        return None

def is_authorized(user_id: int) -> bool:
    """Check if user is authorized"""
    return user_id in config.authorized_users or user_id == config.owner_id

def is_owner(user_id: int) -> bool:
    """Check if user is the owner"""
    return user_id == config.owner_id

def is_chat_authorized(chat_id: int) -> bool:
    """Check if chat is authorized"""
    return chat_id in config.authorized_chats

# Function to get different welcome messages based on user role
def get_welcome_message(user_id: int) -> str:
    """Get appropriate welcome message based on user role"""
    
    # Get formatted list of spam messages (limited to 5 for display)
    spam_msgs_list = ""
    for idx, msg in enumerate(config.spam_messages[:5], 1):
        spam_msgs_list += f"{idx}. `{msg}`\n"
    if len(config.spam_messages) > 5:
        spam_msgs_list += f"and {len(config.spam_messages) - 5} more...\n"
    
    # Bot by footer
    bot_by_footer = f'\n\n<b>Bot by:</b> <a href="tg://user?id={BOT_DEVELOPER_ID}">{BOT_DEVELOPER_USERNAME}</a> ❤️‍🔥'
    
    if is_owner(user_id):
        # Owner gets full access
        return f"""
<b>✨ Welcome to Spam Bot ✨</b>

<b>Owner:</b> <code>{config.owner_id}</code>
<b>Your ID:</b> <code>{user_id}</code>

<b>📋 Available Commands:</b>
• <code>{config.spam_command} &lt;target&gt; &lt;quantity&gt;</code> - Send spam messages

<b>⚙️ Current Configuration:</b>
• Spam Command: <code>{config.spam_command}</code>
• Spam Messages: <code>{len(config.spam_messages)}</code> messages available
• Authorized Users: <code>{len(config.authorized_users)}</code>
• Authorized Chats: <code>{len(config.authorized_chats)}</code>

<b>📝 Spam Messages:</b>
{spam_msgs_list}

<b>🔧 Owner Commands (PM only):</b>
• <code>/a &lt;user_id/username&gt;</code> - Authorize user
• <code>/r &lt;user_id/username&gt;</code> - Remove user
• <code>/listauth</code> - List authorized users
• <code>/addchat &lt;chat_id_or_username&gt;</code> - Authorize chat (group/channel)
• <code>/removechat &lt;chat_id_or_username&gt;</code> - Remove authorized chat
• <code>/listchats</code> - List authorized chats
• <code>/setcmd &lt;new_command&gt;</code> - Set spam command
• <code>/addmsg &lt;message&gt;</code> - Add spam message
• <code>/delmsg &lt;index&gt;</code> - Delete spam message
• <code>/listmsg</code> - List all spam messages
• <code>/clrmsg</code> - Clear all spam messages

<b>📝 Usage:</b>
Send <code>{config.spam_command} @username 5</code> in authorized chats.
{bot_by_footer}
        """
    elif is_authorized(user_id):
        # Authorized users get limited access
        return f"""
<b>✨ Welcome to Spam Bot ✨</b>

<b>Your ID:</b> <code>{user_id}</code>

<b>📋 Available Commands:</b>
• <code>{config.spam_command} &lt;target&gt; &lt;quantity&gt;</code> - Send spam messages in authorized chats

<b>⚙️ Current Configuration:</b>
• Spam Command: <code>{config.spam_command}</code>
• Spam Messages: <code>{len(config.spam_messages)}</code> messages available
• Your Status: <b>✅ Authorized User</b>

<b>📝 Usage:</b>
1. Add me to a group/channel as admin
2. Ask owner to authorize that chat using <code>/addchat</code>
3. Use: <code>{config.spam_command} @username 5</code>

<i>Note: You can only use spam command in authorized chats where you are a member.</i>
{bot_by_footer}
        """
    else:
        # Unauthorized users
        return f"""
<b>✨ Welcome to Spam Bot ✨</b>

<b>Your ID:</b> <code>{user_id}</code>

⛔ <b>Access Denied</b>

You are not authorized to use this bot.
Contact the owner (<code>{config.owner_id}</code>) for access.

<i>Owner can authorize you using: <code>/a {user_id}</code></i>
{bot_by_footer}
        """

# Command handlers - DIFFERENT ACCESS BASED ON USER ROLE
@app.on_message(filters.command(["start", "help"]) & filters.private)
async def start_command(client: Client, message: Message):
    """Handle /start command with different access levels"""
    user_id = message.from_user.id
    welcome_message = get_welcome_message(user_id)
    await message.reply_text(welcome_message, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)

# ===== OWNER ONLY COMMANDS =====
# These commands only work for owner in PM

@app.on_message(filters.command(["a", "add"]) & filters.private)
async def add_user_command(client: Client, message: Message):
    """Add user to authorized list (Owner only)"""
    if not is_owner(message.from_user.id):
        await message.reply_text("⛔ This command is for owner only!")
        return
    
    if len(message.command) < 2:
        await message.reply_text("Usage: <code>/a &lt;user_id_or_username&gt;</code>", parse_mode=enums.ParseMode.HTML)
        return
    
    user_input = message.command[1]
    user_id = await resolve_user_id(user_input)
    
    if not user_id:
        await message.reply_text("❌ Invalid user ID or username!")
        return
    
    if user_id in config.authorized_users:
        await message.reply_text("⚠️ User is already authorized!")
        return
    
    if user_id == config.owner_id:
        await message.reply_text("⚠️ Owner is already authorized by default!")
        return
    
    # Add user to authorized list
    authorized = config.authorized_users
    authorized.append(user_id)
    config.authorized_users = authorized
    
    await message.reply_text(f"✅ User <code>{user_id}</code> has been authorized!", parse_mode=enums.ParseMode.HTML)

@app.on_message(filters.command(["r", "remove"]) & filters.private)
async def remove_user_command(client: Client, message: Message):
    """Remove user from authorized list (Owner only)"""
    if not is_owner(message.from_user.id):
        await message.reply_text("⛔ This command is for owner only!")
        return
    
    if len(message.command) < 2:
        await message.reply_text("Usage: <code>/r &lt;user_id_or_username&gt;</code>", parse_mode=enums.ParseMode.HTML)
        return
    
    user_input = message.command[1]
    user_id = await resolve_user_id(user_input)
    
    if not user_id:
        await message.reply_text("❌ Invalid user ID or username!")
        return
    
    if user_id == config.owner_id:
        await message.reply_text("❌ Cannot remove owner!")
        return
    
    if user_id not in config.authorized_users:
        await message.reply_text("⚠️ User is not in authorized list!")
        return
    
    # Remove user from authorized list
    authorized = config.authorized_users
    authorized.remove(user_id)
    config.authorized_users = authorized
    
    await message.reply_text(f"✅ User <code>{user_id}</code> has been removed!", parse_mode=enums.ParseMode.HTML)

@app.on_message(filters.command(["listauth"]) & filters.private)
async def list_auth_command(client: Client, message: Message):
    """List all authorized users (Owner only)"""
    if not is_owner(message.from_user.id):
        await message.reply_text("⛔ This command is for owner only!")
        return
    
    authorized_users = config.authorized_users
    owner_id = config.owner_id
    
    if not authorized_users:
        auth_list = "No authorized users (only owner)"
    else:
        auth_list = "\n".join([f"• <code>{uid}</code>" for uid in authorized_users])
    
    response = f"""
<b>👥 Authorized Users:</b>

<b>Owner:</b> <code>{owner_id}</code>

<b>Authorized Users ({len(authorized_users)}):</b>
{auth_list}
    """
    
    await message.reply_text(response, parse_mode=enums.ParseMode.HTML)

# Chat authorization management - OWNER ONLY
@app.on_message(filters.command(["addchat"]) & filters.private)
async def add_chat_command(client: Client, message: Message):
    """Add chat to authorized list (Owner only)"""
    if not is_owner(message.from_user.id):
        await message.reply_text("⛔ This command is for owner only!")
        return
    
    if len(message.command) < 2:
        await message.reply_text("Usage: <code>/addchat &lt;chat_id_or_username&gt;</code>", parse_mode=enums.ParseMode.HTML)
        return
    
    chat_input = message.command[1]
    chat_id = await resolve_chat_id(chat_input)
    
    if not chat_id:
        await message.reply_text("❌ Invalid chat ID or username!")
        return
    
    if chat_id in config.authorized_chats:
        await message.reply_text("⚠️ Chat is already authorized!")
        return
    
    # Add chat to authorized list
    config.add_authorized_chat(chat_id)
    
    await message.reply_text(f"✅ Chat <code>{chat_id}</code> has been authorized!", parse_mode=enums.ParseMode.HTML)

@app.on_message(filters.command(["removechat"]) & filters.private)
async def remove_chat_command(client: Client, message: Message):
    """Remove chat from authorized list (Owner only)"""
    if not is_owner(message.from_user.id):
        await message.reply_text("⛔ This command is for owner only!")
        return
    
    if len(message.command) < 2:
        await message.reply_text("Usage: <code>/removechat &lt;chat_id_or_username&gt;</code>", parse_mode=enums.ParseMode.HTML)
        return
    
    chat_input = message.command[1]
    chat_id = await resolve_chat_id(chat_input)
    
    if not chat_id:
        await message.reply_text("❌ Invalid chat ID or username!")
        return
    
    if chat_id not in config.authorized_chats:
        await message.reply_text("⚠️ Chat is not in authorized list!")
        return
    
    # Remove chat from authorized list
    config.remove_authorized_chat(chat_id)
    
    await message.reply_text(f"✅ Chat <code>{chat_id}</code> has been removed!", parse_mode=enums.ParseMode.HTML)

@app.on_message(filters.command(["listchats"]) & filters.private)
async def list_chats_command(client: Client, message: Message):
    """List all authorized chats (Owner only)"""
    if not is_owner(message.from_user.id):
        await message.reply_text("⛔ This command is for owner only!")
        return
    
    authorized_chats = config.authorized_chats
    
    if not authorized_chats:
        await message.reply_text("❌ No authorized chats!")
        return
    
    # Get chat info for each authorized chat
    chats_list = ""
    for chat_id in authorized_chats:
        try:
            chat = await client.get_chat(chat_id)
            chat_title = chat.title if chat.title else "Unknown"
            chat_type = "Channel" if chat.type == enums.ChatType.CHANNEL else "Group" if chat.type == enums.ChatType.GROUP or chat.type == enums.ChatType.SUPERGROUP else "Private"
            chats_list += f"• <code>{chat_id}</code> - {chat_title} ({chat_type})\n"
        except Exception:
            chats_list += f"• <code>{chat_id}</code> - Unknown (Cannot fetch info)\n"
    
    response = f"""
<b>💬 Authorized Chats ({len(authorized_chats)}):</b>

{chats_list}
    """
    
    await message.reply_text(response, parse_mode=enums.ParseMode.HTML)

# Spam command configuration - OWNER ONLY
@app.on_message(filters.command(["setcmd"]) & filters.private)
async def set_command_command(client: Client, message: Message):
    """Set spam command (Owner only)"""
    if not is_owner(message.from_user.id):
        await message.reply_text("⛔ This command is for owner only!")
        return
    
    if len(message.command) < 2:
        await message.reply_text("Usage: <code>/setcmd &lt;new_command&gt;</code>\nExample: <code>/setcmd spam</code>", parse_mode=enums.ParseMode.HTML)
        return
    
    new_command = message.command[1]
    old_command = config.spam_command
    
    config.spam_command = new_command
    
    await message.reply_text(
        f"✅ Spam command updated!\n\n"
        f"Old: <code>{old_command}</code>\n"
        f"New: <code>{config.spam_command}</code>",
        parse_mode=enums.ParseMode.HTML
    )

# Spam message management - OWNER ONLY
@app.on_message(filters.command(["addmsg"]) & filters.private)
async def add_message_command(client: Client, message: Message):
    """Add a new spam message (Owner only)"""
    if not is_owner(message.from_user.id):
        await message.reply_text("⛔ This command is for owner only!")
        return
    
    if len(message.command) < 2:
        await message.reply_text(
            "Usage: <code>/addmsg &lt;message_text&gt;</code>\n\n"
            "Use <code>{{mention}}</code> as placeholder for user mention.\n"
            "Example: <code>/addmsg Hello {{mention}}! Check this out!</code>",
            parse_mode=enums.ParseMode.HTML
        )
        return
    
    # Get the full message text (including spaces)
    new_message = ' '.join(message.command[1:])
    
    # Check if message already exists
    if new_message in config.spam_messages:
        await message.reply_text("⚠️ This message already exists in the list!")
        return
    
    config.add_spam_message(new_message)
    
    await message.reply_text(
        f"✅ Spam message added!\n"
        f"Total messages: <code>{len(config.spam_messages)}</code>\n\n"
        f"<b>Message:</b> <code>{new_message}</code>",
        parse_mode=enums.ParseMode.HTML
    )

@app.on_message(filters.command(["delmsg"]) & filters.private)
async def delete_message_command(client: Client, message: Message):
    """Delete a spam message by index (Owner only)"""
    if not is_owner(message.from_user.id):
        await message.reply_text("⛔ This command is for owner only!")
        return
    
    if len(message.command) < 2:
        # Show list of messages with indices
        messages = config.spam_messages
        if not messages:
            await message.reply_text("❌ No spam messages configured!")
            return
        
        msg_list = ""
        for idx, msg in enumerate(messages, 1):
            msg_list += f"{idx}. `{msg}`\n"
        
        await message.reply_text(
            f"📝 Current spam messages:\n\n{msg_list}\n"
            f"Usage: <code>/delmsg &lt;index&gt;</code>\n"
            f"Example: <code>/delmsg 1</code> to delete first message",
            parse_mode=enums.ParseMode.HTML
        )
        return
    
    try:
        index = int(message.command[1]) - 1  # Convert to 0-based index
        
        if index < 0 or index >= len(config.spam_messages):
            await message.reply_text(f"❌ Invalid index! Please use 1-{len(config.spam_messages)}")
            return
        
        deleted_message = config.spam_messages[index]
        config.remove_spam_message(index)
        
        await message.reply_text(
            f"✅ Message deleted!\n"
            f"Remaining messages: <code>{len(config.spam_messages)}</code>\n\n"
            f"<b>Deleted:</b> <code>{deleted_message}</code>",
            parse_mode=enums.ParseMode.HTML
        )
    except ValueError:
        await message.reply_text("❌ Invalid index! Please provide a number.")

@app.on_message(filters.command(["listmsg"]) & filters.private)
async def list_messages_command(client: Client, message: Message):
    """List all spam messages (Owner only)"""
    if not is_owner(message.from_user.id):
        await message.reply_text("⛔ This command is for owner only!")
        return
    
    messages = config.spam_messages
    
    if not messages:
        await message.reply_text("❌ No spam messages configured!")
        return
    
    msg_list = ""
    for idx, msg in enumerate(messages, 1):
        msg_list += f"{idx}. `{msg}`\n"
    
    await message.reply_text(
        f"📝 Spam Messages ({len(messages)}):\n\n{msg_list}",
        parse_mode=enums.ParseMode.HTML
    )

@app.on_message(filters.command(["clrmsg"]) & filters.private)
async def clear_messages_command(client: Client, message: Message):
    """Clear all spam messages (Owner only)"""
    if not is_owner(message.from_user.id):
        await message.reply_text("⛔ This command is for owner only!")
        return
    
    if not config.spam_messages:
        await message.reply_text("❌ No spam messages to clear!")
        return
    
    # Add a default message before clearing
    config.spam_messages = ["Hello {mention}! Welcome to the group!"]
    
    await message.reply_text(
        "✅ All spam messages cleared!\n"
        "Default message has been added.",
        parse_mode=enums.ParseMode.HTML
    )

# ===== SPAM COMMAND HANDLER =====
# Works in authorized chats only for authorized users
@app.on_message(filters.command([config.spam_command.strip('/')]))
async def spam_command_handler(client: Client, message: Message):
    """Handle spam command - STRICT USER AUTHORIZATION"""
    
    # Skip if it's a private chat (1-on-1 with bot)
    if message.chat.type == enums.ChatType.PRIVATE:
        return
    
    # Check if chat is authorized
    if not is_chat_authorized(message.chat.id):
        return  # Silent - chat not authorized
    
    # Check if user is authorized
    user_authorized = False
    if message.from_user:
        user_authorized = is_authorized(message.from_user.id)
    
    # If no user info or user not authorized, return silently
    if not user_authorized:
        return
    
    # Check command format
    if len(message.command) < 3:
        return  # Silent - no response
    
    target_input = message.command[1]
    quantity_input = message.command[2]
    
    # Validate quantity
    try:
        quantity = int(quantity_input)
        if quantity < 1 or quantity > 100:  # Increased limit
            return  # Silent - no response
    except ValueError:
        return  # Silent - no response
    
    # Resolve target user
    target_id = await resolve_user_id(target_input)
    if not target_id:
        return  # Silent - no response
    
    # Get target user info
    try:
        target_user = await client.get_users(target_id)
        mention = f'<a href="tg://user?id={target_user.id}">{target_user.first_name}</a>'
    except (PeerIdInvalid, UsernameInvalid, UsernameNotOccupied):
        return  # Silent - no response
    
    # Check if bot is admin in the chat
    try:
        chat_member = await client.get_chat_member(message.chat.id, "me")
        if chat_member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return  # Silent - no response
    except ChatAdminRequired:
        return  # Silent - bot is not admin
    except Exception:
        return  # Silent - other errors
    
    # Get available messages
    messages = config.spam_messages
    if not messages:
        return  # Silent - no response
    
    # Prepare shuffled messages
    # If quantity is more than available messages, shuffle and repeat
    message_pool = []
    for i in range(quantity):
        if i % len(messages) == 0:
            # Shuffle when we've used all messages once
            shuffled = random.sample(messages, len(messages))
            message_pool.extend(shuffled)
    
    # Trim to required quantity
    message_pool = message_pool[:quantity]
    
    # Send messages SILENTLY - no status, no replies
    for msg_text in message_pool:
        try:
            # Prepare message with mention
            formatted_msg = msg_text.format(mention=mention)
            
            # Send message
            await client.send_message(
                chat_id=message.chat.id,
                text=formatted_msg,
                parse_mode=enums.ParseMode.HTML
            )
            
            # Small random delay to avoid flood (0.3 to 1.5 seconds)
            await asyncio.sleep(random.uniform(0.3, 1.5))
            
        except FloodWait as e:
            # Handle flood wait silently
            await asyncio.sleep(e.value)
            continue
        except ChatWriteForbidden:
            break  # Stop if bot can't send messages
        except Exception:
            continue  # Continue trying with next message
    
    # COMPLETELY SILENT - NO STATUS MESSAGE AT ALL
    return

# ===== BLOCK UNAUTHORIZED COMMANDS =====
# Block all owner commands in groups/channels
owner_commands = ["a", "add", "r", "remove", "listauth", "setcmd", 
                  "addmsg", "delmsg", "listmsg", "clrmsg",
                  "addchat", "removechat", "listchats"]

@app.on_message(filters.command(owner_commands) & (filters.group | filters.channel))
async def block_owner_commands_in_chats(client: Client, message: Message):
    """Block owner commands in groups/channels - SILENT"""
    # Simply ignore these commands in groups/channels
    return

# Block owner commands in PM for non-owners
@app.on_message(filters.command(owner_commands) & filters.private)
async def block_owner_commands_for_non_owners(client: Client, message: Message):
    """Block owner commands in PM for non-owners"""
    if not is_owner(message.from_user.id):
        await message.reply_text("⛔ This command is for owner only!")
        return

# Catch-all handler for unknown commands in groups/channels
@app.on_message(filters.group | filters.channel)
async def handle_unknown_commands(client: Client, message: Message):
    """Handle unknown commands in groups/channels - SILENT"""
    # Completely silent - ignore all unknown commands
    return

# ===== MAIN FUNCTION =====
def main():
    """Start the bot"""
    print("=" * 50)
    print("🤖 Spam Bot - SECURE VERSION")
    print("=" * 50)
    print(f"👑 Owner ID: {config.owner_id}")
    print(f"👥 Authorized users: {len(config.authorized_users)}")
    print(f"💬 Authorized chats: {len(config.authorized_chats)}")
    print(f"🔧 Spam command: {config.spam_command}")
    print(f"📝 Spam messages: {len(config.spam_messages)}")
    print("=" * 50)
    print("✅ SECURITY FEATURES:")
    print("• Owner commands → ONLY owner in PM")
    print("• Authorized users → ONLY spam command in authorized chats")
    print("• Public/Private channels → Only authorized users can spam")
    print("• Silent mode → No status messages")
    print("• Bot by footer → With clickable link to JishuEdits")
    print("=" * 50)
    print("Bot is running...")
    print("=" * 50)
    
    app.run()

if __name__ == "__main__":
    # Validate required environment variables
    if not all([API_ID, API_HASH, BOT_TOKEN, OWNER_ID]):
        print("❌ Error: Missing environment variables!")
        print("Please set: API_ID, API_HASH, BOT_TOKEN, OWNER_ID")
        print("Create a .env file or set environment variables")
        exit(1)
    
    main()