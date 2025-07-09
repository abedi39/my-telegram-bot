import asyncio
import json
import random
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler,
    ConversationHandler, filters, CallbackQueryHandler
)

# فایل کاربران
USERS_FILE = 'users.json'
INITIAL_BALANCE = 20000

# کانال اجباری برای عضویت (بدون @)
REQUIRED_CHANNEL = "tasssssssjs"  # یوزرنیم کانالت رو اینجا بزار

# مراحل کانورسیشن
ASK_BET, CHOOSE_TYPE, CHOOSE_NUMBER, CONFIRM, ROLL_DICE = range(5)
DEPOSIT_WITHDRAW, WITHDRAW_NAME, WITHDRAW_CARD = range(ROLL_DICE + 1, ROLL_DICE + 4)
CHECK_SUB = ROLL_DICE + 4

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(f"@{REQUIRED_CHANNEL}", user_id)
        return member.status in ["member", "creator", "administrator"]
    except:
        return False

# --- تابع start فقط پیام عضویت میده و دکمه انجام دادم ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("عضو شید 📢", url=f"https://t.me/{REQUIRED_CHANNEL}")],
        [InlineKeyboardButton("انجام دادم ✅", callback_data="check_sub")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"📢 سلام {update.effective_user.first_name}!\n\n"
        f"برای استفاده از ربات ابتدا باید در کانال زیر عضو شوید:\n👉 https://t.me/{REQUIRED_CHANNEL}\n\n"
        "پس از عضویت روی دکمه «انجام دادم ✅» بزنید.",
        reply_markup=reply_markup
    )
    return CHECK_SUB

# --- تابعی که بعد از تایید عضویت پیام اصلی ربات رو میفرسته ---
async def start_after_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = load_users()

    if context.args:
        referrer_code = context.args[0]
    else:
        referrer_code = None

    if user_id not in users:
        users[user_id] = {
            'username': update.effective_user.username or "",
            'balance': INITIAL_BALANCE,
            'code': str(random.randint(100000, 999999)),
            'referrer_code': referrer_code
        }
    else:
        if referrer_code and ('referrer_code' not in users[user_id] or users[user_id]['referrer_code'] is None):
            users[user_id]['referrer_code'] = referrer_code
            for uid, info in users.items():
                if info['code'] == referrer_code:
                    info['balance'] += 20000
                    try:
                        await context.bot.send_message(
                            chat_id=int(uid),
                            text="🎉 تبریک! یک زیرمجموعه جدید اضافه شد و ۲۰ هزار تومان به موجودی شما افزوده شد!"
                        )
                    except Exception as e:
                        print(f"Error sending bonus message: {e}")

    save_users(users)

    user_data = users[user_id]
    balance = user_data['balance']
    user_code = user_data['code']

    message_text = (
        f"🎉 سلام {update.effective_user.first_name}!\n\n"
        f"💰 موجودی اولیه: {balance}\n"
        f"🔑 کد اختصاصی شما: {user_code}\n\n"
        "حالا می‌تونی تاس بندازی و شرط ببندی!"
    )
    
    keyboard = ReplyKeyboardMarkup(
        [["🎲 تاس بیندازید", "💼 حساب من"], ["💳 واریز و برداشت", "👥 زیرمجموعه"]],
        resize_keyboard=True
    )

    # انتخاب پیام مناسب از callback_query یا message
    if update.callback_query:
        await update.callback_query.message.reply_text(message_text, reply_markup=keyboard)
    else:
        await update.message.reply_text(message_text, reply_markup=keyboard)

    return ASK_BET



# --- هندلر دکمه انجام دادم ✅ که چک عضویت و ادامه میده ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "check_sub":
        is_member = await check_membership(update, context)
        if is_member:
            await query.message.delete()
            await start_after_check(update, context)
            return ASK_BET
        else:
            keyboard = [
                [InlineKeyboardButton("عضو شید 📢", url=f"https://t.me/{REQUIRED_CHANNEL}")],
                [InlineKeyboardButton("انجام دادم ✅", callback_data="check_sub")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(
                f"❌ هنوز عضو نشدید!\n\nحتماً در https://t.me/{REQUIRED_CHANNEL} عضو شوید و دوباره «انجام دادم ✅» را بزنید.",
                reply_markup=reply_markup
            )
            return CHECK_SUB

# --- بقیه توابع بدون تغییر هستند ---
async def show_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = load_users()

    if user_id not in users:
        await update.message.reply_text("شما هنوز ثبت نام نکردید! لطفاً /start را بزنید.")
        return

    user_data = users[user_id]
    user_code = user_data['code']
    balance = user_data['balance']
    telegram_id = user_id

    referrals = [u for u in users.values() if u.get('referrer_code') == user_code]
    referral_count = len(referrals)

    text = (
        f"💼 اطلاعات حساب شما:\n\n"
        f"🔑 کد اختصاصی: {user_code}\n"
        f"💰 موجودی: {balance} تومان\n"
        f"🆔 آیدی تلگرام: {telegram_id}\n"
        f"👥 تعداد زیرمجموعه‌ها: {referral_count}"
    )
    await update.message.reply_text(text)

async def ask_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "لطفاً مبلغ شرط را فقط به صورت عدد انگلیسی وارد کنید (مثلاً: 2000)."
    keyboard = ReplyKeyboardMarkup([["بازگشت"]], resize_keyboard=True)
    await update.message.reply_text(text, reply_markup=keyboard)
    return CHOOSE_TYPE

async def get_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = str(update.effective_user.id)
    users = load_users()
    balance = users[user_id]['balance'] if user_id in users else INITIAL_BALANCE

    if text == "بازگشت":
        keyboard = ReplyKeyboardMarkup(
            [["🎲 تاس بیندازید", "💼 حساب من"], ["💳 واریز و برداشت", "👥 زیرمجموعه"]],
            resize_keyboard=True
        )
        await update.message.reply_text("به منوی اصلی برگشتید.", reply_markup=keyboard)
        return ASK_BET

    if not text.isdigit():
        await update.message.reply_text("خطا: لطفاً فقط عدد انگلیسی وارد کنید.")
        return CHOOSE_TYPE

    bet = int(text)
    if bet > balance:
        await update.message.reply_text(f"خطا: موجودی شما {balance} تومان است. مبلغ شرط نمی‌تواند بیشتر از موجودی باشد.")
        return CHOOSE_TYPE

    context.user_data['bet'] = bet
    keyboard = ReplyKeyboardMarkup([["زوج", "فرد", "اعدادی"], ["بازگشت"]], resize_keyboard=True)
    await update.message.reply_text("نوع شرط خود را انتخاب کنید:", reply_markup=keyboard)
    return CHOOSE_NUMBER

async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "بازگشت":
        return await ask_bet(update, context)

    if text not in ['زوج', 'فرد', 'اعدادی']:
        await update.message.reply_text("لطفا یکی از گزینه‌های زوج، فرد یا اعدادی را انتخاب کنید.")
        return CHOOSE_NUMBER

    context.user_data['bet_type'] = text

    bet = context.user_data['bet']

    if text == 'اعدادی':
        buttons = [[str(i) for i in range(1, 7)], ["بازگشت"]]
        keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        await update.message.reply_text("یک عدد بین ۱ تا ۶ انتخاب کنید:", reply_markup=keyboard)
        return CONFIRM
    else:
        win_amount = int(bet * 1.3)
        context.user_data['win_amount'] = win_amount
        text_message = (
            f"مبلغ شرط: {bet} تومان\n"
            f"مبلغ برد احتمالی: {win_amount} تومان"
        )
        keyboard = ReplyKeyboardMarkup([["✅ شروع", "↩️ بازگشت"]], resize_keyboard=True)
        await update.message.reply_text(text_message, reply_markup=keyboard)
        return ROLL_DICE

async def choose_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "بازگشت":
        return await choose_type(update, context)

    if text not in [str(i) for i in range(1, 7)]:
        await update.message.reply_text("لطفا عددی بین 1 تا 6 انتخاب کنید.")
        return CONFIRM

    context.user_data['chosen_number'] = int(text)
    bet = context.user_data['bet']
    win_amount = int(bet * 1.6)
    context.user_data['win_amount'] = win_amount

    text_message = (
        f"عدد انتخابی شما: {text}\n"
        f"مبلغ شرط: {bet} تومان\n"
        f"مبلغ برد احتمالی: {win_amount} تومان"
    )
    keyboard = ReplyKeyboardMarkup([["✅ شروع", "↩️ بازگشت"]], resize_keyboard=True)
    await update.message.reply_text(text_message, reply_markup=keyboard)
    return ROLL_DICE

async def roll_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "↩️ بازگشت":
        return await choose_type(update, context)

    if text != "✅ شروع":
        await update.message.reply_text("لطفا یکی از گزینه‌های '✅ شروع' یا '↩️ بازگشت' را انتخاب کنید.")
        return ROLL_DICE

    message = await update.message.reply_dice(emoji="🎲")
    dice_value = message.dice.value

    await asyncio.sleep(4)

    bet = context.user_data['bet']
    bet_type = context.user_data['bet_type']
    user_id = str(update.effective_user.id)
    users = load_users()
    balance = users[user_id]['balance'] if user_id in users else INITIAL_BALANCE
    chosen_number = context.user_data.get('chosen_number', None)

    win = False
    if bet_type == 'زوج' and dice_value % 2 == 0:
        win = True
    elif bet_type == 'فرد' and dice_value % 2 == 1:
        win = True
    elif bet_type == 'اعدادی' and dice_value == chosen_number:
        win = True

    if win:
        balance += context.user_data['win_amount']
        result_text = (
            f"🎲 عدد تاس: {dice_value}\n"
            f"✅ شما برنده شدید!\n"
            f"💰 مبلغ برد: {context.user_data['win_amount']} تومان\n"
            f"💳 موجودی جدید: {balance} تومان"
        )
    else:
        balance -= bet
        result_text = (
            f"🎲 عدد تاس: {dice_value}\n"
            f"❌ متاسفم! شما باختید.\n"
            f"💳 موجودی جدید: {balance} تومان"
        )

    users[user_id]['balance'] = balance
    save_users(users)
    await update.message.reply_text(result_text)


    keyboard = ReplyKeyboardMarkup([["🎲 تاس بیندازید", "💼 حساب من"], ["💳 واریز و برداشت", "👥 زیرمجموعه"]], resize_keyboard=True)
    await update.message.reply_text(result_text, reply_markup=keyboard)
    return ASK_BET

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('بازی لغو شد. برای شروع دوباره /start را بزنید.')
    return ConversationHandler.END


# ----- بخش جدید: واریز و برداشت -----

async def deposit_withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(
        [["➕ واریز", "➖ برداشت"], ["↩️ بازگشت"]],
        resize_keyboard=True
    )
    await update.message.reply_text("یکی از گزینه‌ها را انتخاب کنید:", reply_markup=keyboard)
    return DEPOSIT_WITHDRAW

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "↩️ بازگشت":
        return await deposit_withdraw_back(update, context)

    keyboard = ReplyKeyboardMarkup([["↩️ بازگشت"]], resize_keyboard=True)
    await update.message.reply_text(
        "برای واریز لطفاً با آیدی پشتیبانی در ارتباط باشید:\n\n@YourAdminID",
        reply_markup=keyboard
    )
    return DEPOSIT_WITHDRAW

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "↩️ بازگشت":
        return await deposit_withdraw_back(update, context)

    await update.message.reply_text(
        "⚠️ حداقل مبلغ برداشت ۱۰۰ هزار تومان است.\n\n"
        "لطفاً نام و نام خانوادگی خود را وارد کنید:"
    )
    return WITHDRAW_NAME

async def withdraw_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "↩️ بازگشت":
        return await deposit_withdraw_back(update, context)

    context.user_data['withdraw_name'] = update.message.text
    await update.message.reply_text("✅ حالا شماره کارت ۱۶ رقمی خود را وارد کنید:")
    return WITHDRAW_CARD

async def withdraw_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "↩️ بازگشت":
        return await deposit_withdraw_back(update, context)

    card = update.message.text.strip().replace(" ", "")
    if not (card.isdigit() and len(card) == 16):
        await update.message.reply_text("❌ شماره کارت معتبر نیست! باید ۱۶ رقم باشد. دوباره وارد کنید:")
        return WITHDRAW_CARD

    user_id = str(update.effective_user.id)
    users = load_users()
    balance = users[user_id]['balance'] if user_id in users else INITIAL_BALANCE

    if balance < 100000:
        await update.message.reply_text("❌ موجودی شما کمتر از حداقل برداشت (۱۰۰ هزار تومان) است!")
        return DEPOSIT_WITHDRAW

    await update.message.reply_text(
        f"✅ درخواست برداشت شما ثبت شد!\n"
        f"💳 شماره کارت: {card}\n"
        f"🕒 درخواست شما در صف انتظار پرداخت است."
    )
    return DEPOSIT_WITHDRAW

async def deposit_withdraw_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(
        [["🎲 تاس بیندازید", "💼 حساب من"], ["💳 واریز و برداشت", "👥 زیرمجموعه"]],
        resize_keyboard=True
    )
    await update.message.reply_text("به منوی اصلی برگشتید.", reply_markup=keyboard)
    return ASK_BET


# ----- بخش جدید: زیرمجموعه -----

async def show_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = load_users()
    if user_id not in users:
        await update.message.reply_text("لطفاً اول /start را بزنید.")
        return

    user_code = users[user_id]['code']
    bot_username = "Taschi_GameBot"  # یوزرنیم ربات خودت را بزار

    referral_link = f"https://t.me/{bot_username}?start={user_code}"
    referrals = [u for u in users.values() if u.get('referrer_code') == user_code]
    referral_count = len(referrals)

    text = (
    f"👥 تعداد زیرمجموعه‌های شما: {referral_count}\n"
    f"🎉 اگر دوستان خود را با لینک دعوت خودتان دعوت کنید، به ازای هر نفر ۲۰ هزار تومان بونوس دریافت می‌کنید!\n\n"
    f"🔗 لینک دعوت شما:\n{referral_link}"
)

    keyboard = ReplyKeyboardMarkup(
        [["🎲 تاس بیندازید", "💼 حساب من"], ["💳 واریز و برداشت", "👥 زیرمجموعه"]],
        resize_keyboard=True
    )
    await update.message.reply_text(text, reply_markup=keyboard)

# ---------------------------------------------

if __name__ == '__main__':
    app = ApplicationBuilder().token("7926126400:AAGMCq3iGErd8hx9nJ77jMQZhJVSPe4zN24").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHECK_SUB: [CallbackQueryHandler(button_callback, pattern="check_sub")],

            ASK_BET: [
                MessageHandler(filters.Regex("^🎲 تاس بیندازید$"), ask_bet),
                MessageHandler(filters.Regex("^💼 حساب من$"), show_account),
                MessageHandler(filters.Regex("^💳 واریز و برداشت$"), deposit_withdraw_menu),
                MessageHandler(filters.Regex("^👥 زیرمجموعه$"), show_referral),
            ],
            CHOOSE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bet)],
            CHOOSE_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_type)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_number)],
            ROLL_DICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, roll_dice)],

            DEPOSIT_WITHDRAW: [
                MessageHandler(filters.Regex("^➕ واریز$"), deposit),
                MessageHandler(filters.Regex("^➖ برداشت$"), withdraw),
                MessageHandler(filters.Regex("^↩️ بازگشت$"), deposit_withdraw_back),
            ],
            WITHDRAW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_name)],
            WITHDRAW_CARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_card)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    print("Bot started...")
    app.run_polling()
