import logging
import os
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Dict

from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

NORMAL_PACKS: Dict[str, Decimal] = {
    "86wp": Decimal("137.50"),
    "86wp2": Decimal("213.50"),
    "172wp": Decimal("198.00"),
    "257wp": Decimal("253.50"),
    "wp": Decimal("76.00"),
    "86": Decimal("61.50"),
    "110": Decimal("76.00"),
    "172": Decimal("122.00"),
    "257": Decimal("177.50"),
    "343": Decimal("239.00"),
    "344": Decimal("244.00"),
    "429": Decimal("299.50"),
    "514": Decimal("355.00"),
    "600": Decimal("416.50"),
    "706": Decimal("480.00"),
    "792": Decimal("541.50"),
    "878": Decimal("602.00"),
    "963": Decimal("657.50"),
    "1049": Decimal("719.00"),
    "1135": Decimal("779.50"),
    "1220": Decimal("835.00"),
    "1412": Decimal("960.00"),
    "1584": Decimal("1082.00"),
    "1755": Decimal("1199.00"),
    "2195": Decimal("1453.00"),
    "2901": Decimal("1940.00"),
    "3688": Decimal("2424.00"),
    "4390": Decimal("2906.00"),
    "5532": Decimal("3660.00"),
    "9288": Decimal("6079.00"),
    "11483": Decimal("7532.00"),
}

DOUBLE_PACKS: Dict[str, Decimal] = {
    "50+50": Decimal("39.00"),
    "150+150": Decimal("116.90"),
    "250+250": Decimal("187.50"),
    "500+500": Decimal("385.00"),
}

PASS_PACKS: Dict[str, Decimal] = {
    "Twillight Pass": Decimal("402.50"),
    "web (Weekly Elite Bundle)": Decimal("39.00"),
    "meb (Monthly Epic Bundle)": Decimal("196.50"),
}


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📋 Pack List", callback_data="pack_list"),
                InlineKeyboardButton("💎 Example Price", callback_data="example_price"),
            ],
            [
                InlineKeyboardButton("ℹ️ Help", callback_data="help"),
            ],
        ]
    )


def mmk(value: Decimal) -> str:
    return f"{value.quantize(Decimal('1'), rounding=ROUND_HALF_UP):,} MMK"


def round_50(value: Decimal) -> Decimal:
    return (value / Decimal("50")).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * Decimal("50")


def calculate_price(usdt_price: Decimal, rate: Decimal, profit_percent: Decimal) -> Decimal:
    base_price = usdt_price * rate
    profit_amount = base_price * profit_percent / Decimal("100")
    final_price = base_price + profit_amount
    return round_50(final_price)


def usage_text() -> str:
    return (
        "╔════〔 𝗣𝗨𝗕𝗟𝗜𝗖 𝗗𝗜𝗔𝗠𝗢𝗡𝗗 𝗕𝗢𝗧 〕════╗\n"
        "✅ Welcome\n\n"
        "📌 အသုံးပြုပုံ\n"
        "• 83+2%      → package အကုန်စျေးချမယ်\n"
        "• 83.5+2%    → decimal rate နဲ့တွက်မယ်\n"
        "• 82.3+1.5%  → decimal profit နဲ့တွက်မယ်\n"
        "• /list       → package list ကြည့်မယ်\n"
        "• /help       → help ပြန်ကြည့်မယ်\n\n"
        "📌 Rate Limit\n"
        "• USDT Rate = 60 မှ 85 အတွင်းသာ\n\n"
        "🧾 Round - 50\n"
        "╚════════════════════╝"
    )


def build_pack_section(title: str, packs: Dict[str, Decimal]) -> str:
    rows = [f"• {name} - {price} USDT" for name, price in packs.items()]
    return f"{title}\n" + "\n".join(rows)


def build_price_section(title: str, packs: Dict[str, Decimal], rate: Decimal, profit: Decimal) -> str:
    rows = []
    for name, price in packs.items():
        final_price = calculate_price(price, rate, profit)
        rows.append(f"💎 {name} ➜ {mmk(final_price)}")
    return f"{title}\n" + "\n".join(rows)


async def send_long_message(message_obj, text: str) -> None:
    max_len = 3800
    if len(text) <= max_len:
        await message_obj.reply_text(text)
        return

    current = ""
    for line in text.splitlines(True):
        if len(current) + len(line) > max_len:
            await message_obj.reply_text(current)
            current = line
        else:
            current += line

    if current:
        await message_obj.reply_text(current)


def parse_user_input(text: str):
    compact = text.replace(" ", "")
    if "+" not in compact or not compact.endswith("%"):
        return None, None, "format"

    try:
        rate_text, profit_text = compact.split("+", 1)
        rate = Decimal(rate_text)
        profit = Decimal(profit_text[:-1])
    except (InvalidOperation, ValueError):
        return None, None, "format"

    if rate < Decimal("60") or rate > Decimal("85"):
        return None, None, "rate_range"

    if profit < Decimal("0"):
        return None, None, "profit_range"

    return rate, profit, None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(usage_text(), reply_markup=main_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(usage_text(), reply_markup=main_keyboard())


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    text = (
        "╔════〔 𝗣𝗨𝗕𝗟𝗜𝗖 𝗣𝗔𝗖𝗞 𝗟𝗜𝗦𝗧 〕════╗\n\n"
        f"{build_pack_section('🌟 Normal Pack', NORMAL_PACKS)}\n\n"
        f"{build_pack_section('🔥 Double Pack', DOUBLE_PACKS)}\n\n"
        f"{build_pack_section('🎟 Pass / Bundle', PASS_PACKS)}\n\n"
        "╚════════════════════╝"
    )
    await send_long_message(update.message, text)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()

    if query.data == "help":
        await query.message.reply_text(usage_text(), reply_markup=main_keyboard())
        return

    if query.data == "pack_list":
        text = (
            "╔════〔 𝗣𝗨𝗕𝗟𝗜𝗖 𝗣𝗔𝗖𝗞 𝗟𝗜𝗦𝗧 〕════╗\n\n"
            f"{build_pack_section('🌟 Normal Pack', NORMAL_PACKS)}\n\n"
            f"{build_pack_section('🔥 Double Pack', DOUBLE_PACKS)}\n\n"
            f"{build_pack_section('🎟 Pass / Bundle', PASS_PACKS)}\n\n"
            "╚════════════════════╝"
        )
        await send_long_message(query.message, text)
        return

    if query.data == "example_price":
        rate = Decimal("83.5")
        profit = Decimal("2")
        text = (
            "╔════〔 𝗘𝗫𝗔𝗠𝗣𝗟𝗘 𝗣𝗥𝗜𝗖𝗘 𝗟𝗜𝗦𝗧 〕════╗\n"
            f"💱 USDT Rate - {rate}\n"
            f"📈 Profit - {profit}%\n"
            "🧾 Round - 50\n\n"
            f"{build_price_section('🌟 Normal Pack', NORMAL_PACKS, rate, profit)}\n\n"
            f"{build_price_section('🔥 Double Pack', DOUBLE_PACKS, rate, profit)}\n\n"
            f"{build_price_section('🎟 Pass / Bundle', PASS_PACKS, rate, profit)}\n\n"
            "╚════════════════════╝"
        )
        await send_long_message(query.message, text)
        return


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    rate, profit, error = parse_user_input(user_text)

    if error == "format":
        await update.message.reply_text(
            "╔════〔 𝗗𝗜𝗔𝗠𝗢𝗡𝗗 𝗣𝗥𝗜𝗖𝗘 〕════╗\n"
            "❌ Format မှားနေပါတယ်\n\n"
            "📌 Example\n"
            "83+2%\n"
            "83.5+2%\n"
            "82.3+1.5%\n"
            "/list\n"
            "/help\n"
            "╚════════════════════╝",
            reply_markup=main_keyboard(),
        )
        return

    if error == "rate_range":
        await update.message.reply_text(
            "╔════〔 𝗗𝗜𝗔𝗠𝗢𝗡𝗗 𝗣𝗥𝗜𝗖𝗘 〕════╗\n"
            "❌ USDT Rate သည် 60 မှ 85 အတွင်းသာ ရမယ်\n\n"
            "📌 Example\n"
            "60+2%\n"
            "83.5+2%\n"
            "85+2%\n"
            "╚════════════════════╝",
            reply_markup=main_keyboard(),
        )
        return

    if error == "profit_range":
        await update.message.reply_text(
            "╔════〔 𝗗𝗜𝗔𝗠𝗢𝗡𝗗 𝗣𝗥𝗜𝗖𝗘 〕════╗\n"
            "❌ Profit % သည် 0 ထက်ငယ်လို့မရဘူး\n"
            "╚════════════════════╝",
            reply_markup=main_keyboard(),
        )
        return

    result_text = (
        "╔════〔 𝗣𝗨𝗕𝗟𝗜𝗖 𝗗𝗜𝗔𝗠𝗢𝗡𝗗 𝗣𝗥𝗜𝗖𝗘 𝗟𝗜𝗦𝗧 〕════╗\n"
        f"💱 USDT Rate - {rate}\n"
        f"📈 Profit - {profit}%\n"
        "🧾 Round - 50\n\n"
        f"{build_price_section('🌟 Normal Pack', NORMAL_PACKS, rate, profit)}\n\n"
        f"{build_price_section('🔥 Double Pack', DOUBLE_PACKS, rate, profit)}\n\n"
        f"{build_price_section('🎟 Pass / Bundle', PASS_PACKS, rate, profit)}\n\n"
        "╚════════════════════╝"
    )
    await send_long_message(update.message, result_text)


async def post_init(app: Application) -> None:
    await app.bot.set_my_commands(
        [
            BotCommand("start", "အသုံးပြုပုံ"),
            BotCommand("help", "help ပြရန်"),
            BotCommand("list", "package list ကြည့်ရန်"),
        ]
    )


def main() -> None:
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN env var မထည့်ရသေးပါ")

    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started with polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
