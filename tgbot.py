from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot, Update
from dotenv import load_dotenv
from queue import Queue
from typing import Final
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
import asyncio
import os

# .env dosyasından gerekli bilgileri yükle
load_dotenv()

# SharePoint sitesi ve kimlik bilgilerini al
sharepoint_url = os.getenv("SHAREPOINT_URL")
username = os.getenv("SHAREPOINT_USERNAME")
password = os.getenv("SHAREPOINT_PASSWORD")
#token=os.getenv("TELEGRAM_BOT_TOKEN")

async def upload_to_sharepoint(file):
    ctx_auth = AuthenticationContext(url=sharepoint_url)
    if ctx_auth.acquire_token_for_user(username, password):
        ctx = ClientContext(sharepoint_url, ctx_auth)
        library_name = "IRDDmler"  # SharePoint kütüphane adı
        folder_url = f"/sites/{library_name}/Shared%20Documents/Bussiness%20Intelligence/tgbot/"  # Klasör yolunu burada belirtin https://hayratyardim.sharepoint.com/sites/IRDDmler/Shared%20Documents/Bussiness%20Intelligence/tgbot/Book.xlsx?web=1
        target_folder = ctx.web.get_folder_by_server_relative_url(folder_url)
        with open(file, "rb") as file_content:
            target_file = target_folder.upload_file(os.path.basename(file), file_content)
            ctx.execute_query()
            print("Dosya SharePoint'e yüklendi:", target_file.serverRelativeUrl)
            return True
    print("Dosya SharePoint'e yüklenemedi.")
    return False
  
TOKEN: Final = "6640784429:AAFDHRVvLlsdnRimj6s2vx86bdoXYe_Qz7U"

# Program ve ülke listelerini tanımla
programs = ['Acil Yardım', 'Kurban', 'Yetim', 'Su Kuyusu', 'Eğitim', 'Kuran', 'Sağlık', 'Sürdürülebilir Kalkınma', 'Ramazan']
countries = ['Burkina Faso', 'Nijer', 'Suriye', 'Türkiye', 'Filistin', 'Yemen', 'Somali', 'Nijerya', 'Çad']

# Tag seçeneklerini belirle
tag_options = [f"{program}-{country}" for program in programs for country in countries]

# Tagları belirlemek için bir conversation handler oluştur
TAG_SELECTION_PROGRAM, TAG_SELECTION_COUNTRY, FILE_UPLOAD = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    reply_keyboard_programs = [[program] for program in programs]
    await update.message.reply_text(
        'Dosyanı yüklemek için bir program seç:',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard_programs, one_time_keyboard=True))
    return TAG_SELECTION_PROGRAM

async def tag_selection_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_program =  update.message.text 
    context.user_data['selected_program'] = selected_program
    reply_keyboard_countries = [[country] for country in countries]
    await update.message.reply_text(
        f"Seçilen program: {selected_program}. Lütfen bir ülke seç:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard_countries, one_time_keyboard=True))
    return TAG_SELECTION_COUNTRY

async def tag_selection_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_country =  update.message.text
    selected_program = context.user_data['selected_program']
    context.user_data['selected_country'] = selected_country
    tag = f"{selected_program}-{selected_country}"
    await update.message.reply_text(
        f"Seçilen ülke: {selected_country}. Tag: {tag}. Şimdi dosyayı gönder.",
        reply_markup=ReplyKeyboardRemove())
    context.user_data['selected_tag'] = tag
    return FILE_UPLOAD


async def file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Dosya nesnesini al
    file = await update.message.document.get_file()

    # Dosyayı SharePoint'e yükle
    if await upload_to_sharepoint(file):
        # Başarılı bir şekilde yüklendiği durumunda kullanıcıya mesaj gönder
        await update.message.reply_text("Dosya başarıyla yüklendi ve tag ile ilişkilendirildi.")
    else:
        # Yükleme başarısız olduğunda kullanıcıya bilgi ver
        await update.message.reply_text("Dosya yüklenirken bir hata oluştu. Lütfen daha sonra tekrar deneyin.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('İşlem iptal edildi.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
        print(f'Update {update} caused error {context.error}')


if __name__ == '__main__':
   # Telegram botu oluştur
    print('Starting bot...')
    app = Application.builder().token(token=TOKEN).build()

    # Kuyruk oluştur
    #update_queue = Queue()

    # Application'ı başlat
    #application = app(bot=app, update_queue=update_queue)
    
    # Conversation handler'ı oluştur
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TAG_SELECTION_PROGRAM: [MessageHandler(filters.Regex('^(' + '|'.join(programs) + ')$'), tag_selection_program)],
            TAG_SELECTION_COUNTRY: [MessageHandler(filters.Regex('^(' + '|'.join(countries) + ')$'), tag_selection_country)],
            FILE_UPLOAD: [MessageHandler(filters.Document.ALL, file_upload)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Bot komutları ve conversation handler'ı ekle
    app.add_handler(conv_handler)
    
    # Bot'u çalıştır
    # Errors
    app.add_error_handler(error)
    # Polls 
    print('Polling...')
    app.run_polling()
    app.stop_running()
