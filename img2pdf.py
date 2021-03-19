import array
from PIL import Image
from datetime import datetime
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import File, Bot, InputFile
from collections import deque
from io import BytesIO
import sys
import os
import signal
import json
from google.cloud import vision
import six
from google.cloud import translate_v2 as translate


logToConsole = lambda string: print(f'[{datetime.now().strftime("%H:%M:%S")}] {string}') 
 
# with open("TOKEN", 'r') as file:
BOT_TOKEN = "1642345795:AAGxcTISCcjfVr0qY1awD2ryPuVRY5Vyy0c"
updater = Updater(token=BOT_TOKEN, use_context=True)
bot = Bot(token=BOT_TOKEN)
logToConsole("Bot started.")  
dispatcher = updater.dispatcher
client = vision.ImageAnnotatorClient.from_service_account_json('vision-key.json')
translate_client = translate.Client.from_service_account_json('vision-key.json')
users = {}
def translate_text(target, text):
    

    if isinstance(text, six.binary_type):
        text = text.decode("utf-8")

    # Text can also be a sequence of strings, in which case this method
    # will return a sequence of results for each text.
    result = translate_client.translate(text, target_language=target)

    logToConsole(u"Text: {}".format(result["input"]))
    logToConsole(u"Translation: {}".format(result["translatedText"]))
    logToConsole(u"Detected source language: {}".format(result["detectedSourceLanguage"]))
    return result["translatedText"]

def combineArgsIntoSentence(args):
    """Combines all the args into a string with spaces as divider. Returns that string."""
    filename = ""
    for word in args:
        filename+=" "+word
    filename.strip()
    return filename

def start(update, context):
    """Sends the welcome message to the user."""
    context.bot.send_message(chat_id=update.effective_chat.id, text=getLocalized("start", update.effective_user.language_code))
    logToConsole("User @{username}(chat_id:{chat_id}) initalized the bot.".format(username = update.message.from_user.username, chat_id = update.effective_chat.id))
    

unknown = lambda update, context: context.bot.send_message(chat_id=update.effective_chat.id, text=getLocalized("unknown", update.effective_user.language_code))

def getPhoto(update, context):
    """Downloads a photo and adds it to the photos queue."""
    user = update.message.from_user
    chat = update.effective_chat.id
    if chat not in users:
       users[chat] = Image(chat, user.username, user.language_code)
    currUser = users[update.effective_chat.id]
    currUser.append(update.message.photo[-1].file_id)
    users[chat].displayLabels()
    users[chat].displayText()
    users[chat].deleteImage()

def getFile(update, context):
    """Downloads a document and adds it to the photos queue."""
    user = update.message.from_user
    chat = update.effective_chat.id
    if chat not in users:
        users[chat] = Image(chat, user.username, user.language_code)
    currUser = users[update.effective_chat.id]
    currUser.append(update.message.document.file_id)
    users[chat].displayLabels()
    users[chat].displayText()

def create(update, context):
    """combines the photos into a pdf file and sends that to the user."""
    chat = update.effective_chat.id
    if chat in users:
        currUser = users[chat]
        if context.args: pdf.setFilename(combineArgsIntoSentence(context.args))
        currUser.createPFD()
        currUser.uploadPDF()
        users.pop(chat)   
    else:
        context.bot.send_message(chat_id=chat, text=getLocalized("pdfEmptyError", update.message.from_user.language_code))

dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(MessageHandler(Filters.command, unknown))
dispatcher.add_handler(MessageHandler(Filters.photo & (~Filters.command), getPhoto))
dispatcher.add_handler(MessageHandler(Filters.document.category("image") & (~Filters.command), getFile))

updater.start_polling()

class Image:
    def __init__(self, chat_id, user_id, lc):
        self.chat_id = chat_id
        self.user_id = user_id
        self.lc = lc
        self.images = deque()
        self.document = BytesIO()
        logToConsole(f"User @{user_id}(chat_id:{chat_id}) sent a file.")

    def append(self, image):
        bot.send_message(chat_id=self.chat_id, text=getLocalized("success", self.lc))
        self.images.append(image)

    def displayLabels(self):
        for image in self.images:          
            bytearray = bot.getFile(image).download_as_bytearray()
            self.document = BytesIO(bytearray)
            img = vision.Image(content=self.document.read())

            response = client.label_detection(image=img)
            labels = response.label_annotations

            bot.send_message(chat_id=self.chat_id,text = getLocalized("labels", self.lc))
            labelsString = ", ".join(map(lambda label: label.description, labels))
            bot.send_message(chat_id=self.chat_id,text = translate_text("ru", labelsString))

    def displayText(self):
        for image in self.images:          
            bytearray = bot.getFile(image).download_as_bytearray()
            self.document = BytesIO(bytearray)
            img = vision.Image(content=self.document.read())
            response = client.text_detection(image=img)
            texts = response.text_annotations
            
            if len(texts)!=0:
                bot.send_message(chat_id=self.chat_id,text = getLocalized("text", self.lc))
                bot.send_message(chat_id=self.chat_id,text = translate_text("ru", texts[0].description))
    def deleteImage(self):
        self.images.popleft()

          

with open('localization.json', encoding="utf8") as localizatationFile:
    localizedStrings = json.load(localizatationFile)

def getLocalized(string, lc):
    if lc=="uk": lc = "ru"
    if lc not in localizedStrings:
        dictionary = localizedStrings.get("en")
    else:
        dictionary = localizedStrings.get(lc)
    return dictionary.get(string)