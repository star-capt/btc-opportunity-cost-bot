import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from . import database as db
from . import calculator

logger = logging.getLogger(__name__)

# =============================================================================
# UI HELPERS (per design guide)
# =============================================================================

def back_button():
    """Return the standard ⏮️ Back button keyboard."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("⏮️ Back", callback_data="back:delete")]])

async def delete_command_message(update: Update):
    """Delete the user's command message for cleanliness."""
    try:
        await update.message.delete()
    except BadRequest:
        pass
    except Exception as e:
        logger.debug(f"Could not delete message: {e}")

# =============================================================================
# COMMAND HANDLERS
# =============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start and /menu commands."""
    await delete_command_message(update)
    
    user = update.effective_user
    await db.get_or_create_user(user.id, user.username)
    
    menu_text = """₿ **BTC Opportunity Cost**

What could your money be worth today if you'd bought Bitcoin instead?

**Just tell me what you bought:**
• "iPhone 16 in September 2024"
• "100 shares of GOOG in January 2020"
• "$500 of ETH in March 2021"

/history — _See your past calculations_
/tipjar — _Support the project ❤️_"""
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=menu_text,
        parse_mode='Markdown'
    )

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show last 5 calculations."""
    await delete_command_message(update)
    
    user = update.effective_user
    history = await db.get_user_history(user.id)
    
    if not history:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="📭 You haven't made any calculations yet!\n\nJust send me a message like: `iPhone 16 in Sep 2024`",
            reply_markup=back_button(),
            parse_mode='Markdown'
        )
        return
        
    text = "📜 **Your Recent Calculations**\n\n"
    for row in history:
        # row is a Row object from database.py
        gain = row['btc_value_now'] - row['total_usd']
        text += f"• **{row['item']}** ({row['purchase_date']})\n"
        text += f"  Spent: `${row['total_usd']:,.2f}` → Now: `${row['btc_value_now']:,.2f}`\n"
        text += f"  Difference: `{'+' if gain >= 0 else ''}${gain:,.2f}`\n\n"
        
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=back_button(),
        parse_mode='Markdown'
    )

async def tipjar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Standard tipjar handler."""
    await delete_command_message(update)
    
    message = (
        "🍯 **Support the Bot!**\n\n"
        "If you enjoy seeing how much money you could have had, consider leaving a tip!\n\n"
        "**BTC**\n`bc1qqrqn0n3aff2avwp2dd0zkux84qlq2lvn6qcw8hsw7r69zunswgqq93atac`"
    )
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=back_button(),
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes plain text purchase queries."""
    if not update.message or not update.message.text:
        return
        
    query = update.message.text
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # 1. Show status update (Edit, Don't Spam)
    status_msg = await update.message.reply_text("🔍 Researching pricing...")
    
    # 2. Run calculation
    result = await calculator.run_calculation(query)
    
    if not result:
        await status_msg.edit_text(
            "❌ Sorry, I couldn't find reliable pricing for that. Try being more specific with the date or item name!",
            reply_markup=back_button()
        )
        return
        
    # 3. Save to history
    await db.save_calculation(user_id, result)
    
    # 4. Format and display
    gain_usd = result['btc_value_now'] - result['total_usd']
    gain_pct = (gain_usd / result['total_usd']) * 100
    
    response = f"""₿ **{result['item']}**
📅 {result['purchase_date']}

💰 **Original Purchase:**
• Cost: `${result['total_usd']:,.2f}`
• {result['source']}

🚀 **Bitcoin Alternative:**
• BTC Price then: `${result['btc_price_then']:,.2f}`
• BTC Purchased: `{result['btc_amount']:.6f} BTC`

✨ **Value Today:**
• Current BTC: `${result['btc_price_now']:,.2f}`
• **Total Value: `${result['btc_value_now']:,.2f}`**

📈 **Opportunity Cost:**
• `{'🟢 +' if gain_usd >= 0 else '🔴 -'}${abs(gain_usd):,.2f}` ({gain_pct:.1f}%)
"""
    
    await status_msg.edit_text(
        text=response,
        reply_markup=back_button(),
        parse_mode='Markdown'
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Standard callback handler for back buttons."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "back:delete":
        await query.message.delete()
