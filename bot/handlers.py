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

def back_button(text: str = "⏮️ Back"):
    """Return a back button with optional custom text."""
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data="back:delete")]])

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

What could your money be worth today if you'd bought Bitcoin instead? No regrets, though!—As they say, "everyone gets Bitcoin at the price they deserve."

**Just tell me what you bought:**
• "iPhone 11 in September 2019"
• "100 shares of GOOG in January 2020"
• "$500 of ETH in March 2021"

/history — _See your past calculations_
/tipjar — _Show some love!🧡_"""
    
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
            text="📭 You haven't made any calculations yet!\n\nJust send me a message like: `iPhone 11 in Sep 2019`",
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
        "🍯 **Show some love!🧡**\n\n"
        "If you enjoy seeing how much money you could have had, consider leaving a tip!\n\n"
        "**BTC**\n`bc1qa2tgxpuswjnprc7k82296z2ryvshth3c8t53ya0gutkyvvuzdv6sw5y8j4`"
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
        
    await delete_command_message(update)
    
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
    
    # 4. Calculate gains
    gain_usd = result['btc_value_now'] - result['total_usd']
    gain_pct = (gain_usd / result['total_usd']) * 100
    
    # Current value comparison (if item still has value)
    current_value = result.get('current_total_value', 0)
    current_gain = current_value - result['total_usd'] if current_value else 0
    current_gain_pct = (current_gain / result['total_usd']) * 100 if result['total_usd'] > 0 else 0
    btc_vs_current = result['btc_value_now'] - current_value
    
    # 5. Build response with commentary
    commentary = result.get('commentary', '')
    commentary_section = f"💬 _{commentary}_\n\n" if commentary else ""
    
    # Current value section (only show if item has residual value)
    if current_value > 0:
        current_section = f"""
📊 **Current Value (If Held):**
• Unit Price Now: `${result.get('current_unit_value', 0):,.2f}`
• Total Value Now: `${current_value:,.2f}`
• Change: `{'🟢 +' if current_gain >= 0 else '🔴 '}${abs(current_gain):,.2f}` ({current_gain_pct:+.1f}%)
• _{result.get('value_explanation', '')}_
"""
    else:
        current_section = f"""
📊 **Current Value:**
• `$0.00` — _{result.get('value_explanation', 'Consumed/no resale value')}_
"""
    
    response = f"""{commentary_section}₿ **{result['item']}**
📅 {result['purchase_date']}

💰 **Original Purchase:**
• Quantity: `{result.get('quantity', 1):,.2f}` @ `${result.get('unit_price', result['total_usd']):,.2f}` each
• Total Cost: `${result['total_usd']:,.2f}`
• _{result['source']}_
{current_section}
🚀 **Bitcoin Alternative:**
• BTC Price then: `${result['btc_price_then']:,.2f}`
• BTC Purchased: `{result['btc_amount']:.6f} BTC`

✨ **If You'd Bought BTC:**
• Current BTC: `${result['btc_price_now']:,.2f}`
• **Total Value: `${result['btc_value_now']:,.2f}`**

📈 **Opportunity Cost:**
• {'🟢' if gain_usd >= 0 else '🔴'} `{'+' if gain_usd >= 0 else '-'}${abs(gain_usd):,.2f}` vs original purchase ({gain_pct:,.1f}%)"""
    
    # Add comparison to current holding if item still has value
    if current_value > 0:
        response += f"\n• 🟡 `+${btc_vs_current:,.2f}` vs holding {result['item']}"
    
    # 6. Use dynamic AI-generated back button text
    back_text = result.get('button_text', "⏮️ Back")

    await status_msg.edit_text(
        text=response,
        reply_markup=back_button(back_text),
        parse_mode='Markdown'
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Standard callback handler for back buttons."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "back:delete":
        await query.message.delete()
