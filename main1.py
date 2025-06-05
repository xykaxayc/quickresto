from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)
from datetime import datetime
import os
import json
import sys

# Этапы
FIO, POSITION, ADDRESS, WORK_TYPE, STEP_STATUS, STEP_TIME, STEP_COMMENT = range(7)

# Данные
addresses = ["Кемерово, ул. Промышленная, 2А", "Новосибирск, Сибирская 23"]
work_types = {
    "Лестница": ["Замер", "Фрезеровка", "Изготовление", "Шлифовка", "Покраска", "Монтаж"],
    "Шпонка": ["Шлифовка", "Покраска"],
    "Потолок": ["Футляры", "Подшивка 1", "Подшивка 2", "Подшивка 3"]
}
status_options = ["Выполнено", "В процессе", "Не выполнено"]

# Хранилище текущего этапа
step_index = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Введи своё ФИО:")
    return FIO

async def get_fio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ФИО'] = update.message.text
    await update.message.reply_text("Твоя должность:")
    return POSITION

async def get_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['Должность'] = update.message.text
    keyboard = [[KeyboardButton(addr)] for addr in addresses]
    await update.message.reply_text("Выбери объект:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['Объект'] = update.message.text
    keyboard = [[InlineKeyboardButton(name, callback_data=name)] for name in work_types.keys()]
    await update.message.reply_text("Выбери вид работ:", reply_markup=InlineKeyboardMarkup(keyboard))
    return WORK_TYPE

async def get_work_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    work_type = query.data
    context.user_data['Вид работ'] = work_type
    context.user_data['Этапы'] = []
    step_index[query.message.chat_id] = 0
    step = work_types[work_type][0]
    buttons = [[InlineKeyboardButton(text=s, callback_data=s)] for s in status_options]
    await query.message.reply_text(f"Этап: {step}\nВыберите статус:", reply_markup=InlineKeyboardMarkup(buttons))
    return STEP_STATUS

async def get_step_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    i = step_index[chat_id]
    steps = work_types[context.user_data['Вид работ']]
    step_name = steps[i]
    context.user_data['Этапы'].append({"Название": step_name, "Статус": query.data})
    await query.message.reply_text("Затраченное время (например, 2ч 30м):")
    return STEP_TIME

async def get_step_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    i = step_index[chat_id]
    context.user_data['Этапы'][i]['Время'] = update.message.text
    await update.message.reply_text("Комментарий (если есть):")
    return STEP_COMMENT

async def get_step_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    i = step_index[chat_id]
    context.user_data['Этапы'][i]['Комментарий'] = update.message.text

    step_index[chat_id] += 1
    steps = work_types[context.user_data['Вид работ']]
    if step_index[chat_id] < len(steps):
        next_step = steps[step_index[chat_id]]
        buttons = [[InlineKeyboardButton(text=s, callback_data=s)] for s in status_options]
        await update.message.reply_text(f"Этап: {next_step}\nВыберите статус:", reply_markup=InlineKeyboardMarkup(buttons))
        return STEP_STATUS
    else:
        return await finish_report(update, context)

async def finish_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    today = datetime.now().strftime('%Y-%m-%d')
    filename = f"reports/{today}_{data['ФИО'].replace(' ', '_')}.json"
    os.makedirs("reports", exist_ok=True)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    await update.message.reply_text("Спасибо! Отчет сохранён в формате JSON ✅")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Заполнение отменено.")
    return ConversationHandler.END

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Environment variable TELEGRAM_BOT_TOKEN is not set. Exiting.")
        sys.exit(1)

    app = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fio)],
            POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_position)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            WORK_TYPE: [CallbackQueryHandler(get_work_type)],
            STEP_STATUS: [CallbackQueryHandler(get_step_status)],
            STEP_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_step_time)],
            STEP_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_step_comment)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
