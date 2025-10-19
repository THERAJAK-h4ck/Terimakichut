import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import requests
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 🔑 BOT TOKEN - यहाँ अपना token डालें
BOT_TOKEN = os.getenv('8455342768:AAH3URoRvQJY5ySG8YEH8LO6txwMLvLk6Lw')
if not BOT_TOKEN:
    # अगर environment variable नहीं मिला तो directly डालें
    BOT_TOKEN = "8455342768:AAH3URoRvQJY5ySG8YEH8LO6txwMLvLk6Lw"  # 🔥 यहाँ अपना token डालें

if BOT_TOKEN == "YOUR_ACTUAL_BOT_TOKEN_HERE":
    logging.error("❌ PLEASE UPDATE BOT_TOKEN IN THE CODE!")
    exit(1)

# 📢 TELEGRAM CHANNELS - Force Join के लिए
CHANNELS = [
    {
        'id': '@rajakkhan4x',  # Channel username
        'name': 'Rajak Khan 4X',
        'url': 'https://t.me/rajakkhan4x'
    },
    {
        'id': '@PromotionsOffers', 
        'name': 'Promotions & Offers',
        'url': 'https://t.me/+eqtzUeGK774yMzQ1'
    },
    {
        'id': '@WorldMainSMMPanel',
        'name': 'WorldMain SMM Panel', 
        'url': 'https://t.me/+rL16oopNfU5iYzk9'
    },
    {
        'id': '@SMMUpdatesChannel',
        'name': 'SMM Updates',
        'url': 'https://t.me/+XUbztPQKGScwNGNl'
    }
]

# 🔗 NUMBER INFO API
NUMBER_API_URL = "https://happy-api-app.vercel.app/?num="

# User data storage (production में database use करें)
user_data = {}

class UserState:
    def __init__(self, user_id):
        self.user_id = user_id
        self.joined_channels = set()
        self.last_activity = datetime.now()
    
    def has_joined_all_channels(self):
        return len(self.joined_channels) == len(CHANNELS)

def get_user_state(user_id):
    if user_id not in user_data:
        user_data[user_id] = UserState(user_id)
    return user_data[user_id]

async def check_channel_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user has joined all required channels"""
    try:
        user_state = get_user_state(user_id)
        
        for i, channel in enumerate(CHANNELS):
            try:
                # Check if user is member of channel
                chat_member = await context.bot.get_chat_member(
                    chat_id=channel['id'], 
                    user_id=user_id
                )
                
                if chat_member.status in ['member', 'administrator', 'creator']:
                    user_state.joined_channels.add(i)
                else:
                    if i in user_state.joined_channels:
                        user_state.joined_channels.remove(i)
                        
            except Exception as e:
                logging.warning(f"Could not check channel {channel['id']}: {e}")
                continue
                
        return user_state.has_joined_all_channels()
        
    except Exception as e:
        logging.error(f"Error checking channel membership: {e}")
        return False

async def get_number_info(phone_number: str) -> dict:
    """Get number information from API"""
    try:
        response = requests.get(f'{NUMBER_API_URL}{phone_number}', timeout=10)
        if response.status_code == 200:
            return response.json()
        return {'error': 'API not responding'}
    except Exception as e:
        logging.error(f"Error fetching number info: {e}")
        return {'error': str(e)}

def format_number_info(info: dict) -> str:
    """Format number information for display"""
    if not info or info.get('error'):
        return '❌ इस नंबर की जानकारी उपलब्ध नहीं है। कृपया सही नंबर डालें।'

    message = "📱 *नंबर जानकारी*\n\n"
    
    # Basic info
    if info.get('number'):
        message += f"🔢 *नंबर:* `{info['number']}`\n"
    
    if info.get('carrier'):
        message += f"🏢 *ऑपरेटर:* {info['carrier']}\n"
    
    if info.get('country'):
        message += f"🌍 *देश:* {info['country']}\n"
    
    if info.get('location'):
        message += f"📍 *लोकेशन:* {info['location']}\n"
    
    if info.get('timezone'):
        message += f"⏰ *टाइमजोन:* {info['timezone']}\n"
    
    # Validity
    if 'valid' in info:
        status = "✅ *वैलिड नंबर*" if info['valid'] else "❌ *इनवैलिड नंबर*"
        message += f"📊 *स्टेटस:* {status}\n"
    
    return message

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_state = get_user_state(user.id)
    
    welcome_text = (
        f"👋 नमस्ते *{user.first_name}*!\\n\\n"
        f"🤖 *Number Information Bot* में आपका स्वागत है!\\n\\n"
        f"📞 किसी भी नंबर की पूरी जानकारी प्राप्त करें\\.\\n\\n"
        f"⚠️ बॉट का उपयोग करने से पहले नीचे दिए गए सभी चैनल्स को ज्वाइन करें:"
    )
    
    # Create channel buttons
    keyboard = []
    for channel in CHANNELS:
        keyboard.append([InlineKeyboardButton(
            f"📢 {channel['name']}", 
            url=channel['url']
        )])
    
    keyboard.append([InlineKeyboardButton(
        "✅ मैंने सभी चैनल ज्वाइन कर लिए", 
        callback_data='check_join_status'
    )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )

async def check_join_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle check join status callback"""
    query = update.callback_query
    user = query.from_user
    user_state = get_user_state(user.id)
    
    await query.answer()
    
    try:
        has_joined_all = await check_channel_membership(user.id, context)
        
        if has_joined_all:
            # User has joined all channels
            main_keyboard = [
                [KeyboardButton("📞 नंबर सर्च करें")],
                [KeyboardButton("ℹ️ बॉट के बारे में")],
                [KeyboardButton("🔄 चैनल्स फिर से चेक करें")]
            ]
            reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
            
            success_text = (
                f"🎉 बहुत बढ़िया *{user.first_name}*\\!\\n\\n"
                f"✅ आपने सभी चैनल्स सफलतापूर्वक ज्वाइन कर लिए हैं\\.\\n\\n"
                f"📞 अब आप नंबर सर्च कर सकते हैं:\\n\\n"
                f"*उदाहरण:*\\n"
                f"• 91XXXXXXXXXX\\n"
                f"• \\+91XXXXXXXXXX\\n"
                f"• XXXXXXXXXX\\n\\n"
                f"🔍 नीचे दिए बटन से सर्च शुरू करें:"
            )
            
            await query.edit_message_text(
                success_text,
                reply_markup=reply_markup,
                parse_mode='MarkdownV2'
            )
            
        else:
            # User hasn't joined all channels
            await query.answer("❌ आपने अभी तक सभी चैनल्स ज्वाइन नहीं किए हैं!", show_alert=True)
            
            # Show channels again with updated status
            keyboard = []
            for i, channel in enumerate(CHANNELS):
                status = " ✅" if i in user_state.joined_channels else ""
                keyboard.append([InlineKeyboardButton(
                    f"📢 {channel['name']}{status}", 
                    url=channel['url']
                )])
            
            keyboard.append([InlineKeyboardButton(
                "🔁 फिर से चेक करें", 
                callback_data='check_join_status'
            )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            error_text = (
                f"❌ *{user.first_name}*, आपने अभी तक सभी चैनल्स ज्वाइन नहीं किए हैं\\!\\n\\n"
                f"⚠️ कृपया नीचे दिए गए सभी चैनल्स को ज्वाइन करें और फिर \"मैंने सभी चैनल ज्वाइन कर लिए\" बटन पर क्लिक करें:"
            )
            
            await query.edit_message_text(
                error_text,
                reply_markup=reply_markup,
                parse_mode='MarkdownV2'
            )
            
    except Exception as e:
        logging.error(f"Error in check_join_status: {e}")
        await query.answer("❌ चेक करने में error आया! बाद में कोशिश करें।", show_alert=True)

async def handle_search_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle search number button"""
    user = update.effective_user
    
    # Check if user has joined all channels
    has_joined_all = await check_channel_membership(user.id, context)
    if not has_joined_all:
        await show_channel_join_required(update, context)
        return
    
    search_text = (
        "🔍 *नंबर सर्च*\\n\\n"
        "कृपया नंबर डालें:\\n\\n"
        "*फॉर्मेट:*\\n"
        "• 91XXXXXXXXXX\\n"
        "• \\+91XXXXXXXXXX\\n"
        "• XXXXXXXXXX\\n\\n"
        "उदाहरण: 919876543210"
    )
    
    await update.message.reply_text(
        search_text,
        parse_mode='MarkdownV2'
    )

async def handle_about_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle about button"""
    about_text = (
        "🤖 *Number Information Bot*\\n\\n"
        "📞 किसी भी नंबर की पूरी जानकारी प्राप्त करें\\n\\n"
        "✨ *फीचर्स:*\\n"
        "• नंबर वैलिडेशन\\n"
        "• ऑपरेटर जानकारी\\n"
        "• लोकेशन डिटेल्स\\n"
        "• देश और टाइमजोन\\n\\n"
        "👨‍💻 डेवलपर: @rajakkhan4x\\n"
        "📢 अपडेट्स: @WorldMainSMMPanel"
    )
    
    keyboard = [
        [InlineKeyboardButton("📢 अपडेट चैनल", url="https://t.me/+rL16oopNfU5iYzk9")],
        [InlineKeyboardButton("👨‍💻 डेवलपर", url="https://t.me/rajakkhan4x")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        about_text,
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )

async def handle_recheck_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle recheck channels button"""
    user = update.effective_user
    has_joined_all = await check_channel_membership(user.id, context)
    
    if has_joined_all:
        await update.message.reply_text("✅ आप सभी चैनल्स के मेंबर हैं! अब नंबर सर्च कर सकते हैं।")
    else:
        await show_channel_join_required(update, context)

async def show_channel_join_required(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show channel join required message"""
    user = update.effective_user
    user_state = get_user_state(user.id)
    
    keyboard = []
    for i, channel in enumerate(CHANNELS):
        status = " ✅" if i in user_state.joined_channels else ""
        keyboard.append([InlineKeyboardButton(
            f"📢 {channel['name']}{status}", 
            url=channel['url']
        )])
    
    keyboard.append([InlineKeyboardButton(
        "✅ मैंने सभी चैनल ज्वाइन कर लिए", 
        callback_data='check_join_status'
    )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    error_text = (
        f"❌ *{user.first_name}*, आपने अभी तक सभी चैनल्स ज्वाइन नहीं किए हैं\\!\\n\\n"
        f"⚠️ कृपया नीचे दिए गए सभी चैनल्स को ज्वाइन करें:"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            error_text,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            error_text,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )

async def handle_number_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle number input from user"""
    user = update.effective_user
    message_text = update.message.text
    
    # Check if user has joined all channels
    has_joined_all = await check_channel_membership(user.id, context)
    if not has_joined_all:
        await show_channel_join_required(update, context)
        return
    
    # Skip button texts
    if message_text in ['📞 नंबर सर्च करें', 'ℹ️ बॉट के बारे में', '🔄 चैनल्स फिर से चेक करें']:
        return
    
    # Process number
    phone_number = message_text.strip()
    
    # Validate number format
    if not phone_number.replace('+', '').replace(' ', '').isdigit():
        await update.message.reply_text("❌ कृपया सही नंबर फॉर्मेट में डालें।")
        return
    
    # Show loading message
    loading_msg = await update.message.reply_text("🔄 जानकारी प्राप्त की जा रही है...")
    
    try:
        # Get number information
        number_info = await get_number_info(phone_number)
        
        # Format and send response
        formatted_info = format_number_info(number_info)
        
        await context.bot.edit_message_text(
            chat_id=loading_msg.chat_id,
            message_id=loading_msg.message_id,
            text=formatted_info,
            parse_mode='MarkdownV2'
        )
        
    except Exception as e:
        logging.error(f"Error processing number: {e}")
        await context.bot.edit_message_text(
            chat_id=loading_msg.chat_id,
            message_id=loading_msg.message_id,
            text="❌ सर्च करने में error आया! कृपया बाद में कोशिश करें।"
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logging.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("search", handle_search_button))
    application.add_handler(CommandHandler("about", handle_about_button))
    
    application.add_handler(CallbackQueryHandler(check_join_status_callback, pattern='check_join_status'))
    
    application.add_handler(MessageHandler(filters.Text("📞 नंबर सर्च करें"), handle_search_button))
    application.add_handler(MessageHandler(filters.Text("ℹ️ बॉट के बारे में"), handle_about_button))
    application.add_handler(MessageHandler(filters.Text("🔄 चैनल्स फिर से चेक करें"), handle_recheck_button))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number_input))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    print("🤖 Bot is starting...")
    print(f"✅ Bot Token: {BOT_TOKEN[:10]}...")  # First 10 chars only for security
    
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    main()