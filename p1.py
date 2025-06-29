import os
from tkinter import Image
from fuzzywuzzy import fuzz
import geocoder
import requests
import sys
import time
import datetime
from datetime import timezone, timedelta
import random
import subprocess
import threading
import queue
import json
import re
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
import webbrowser
import socket
import shutil
import winsound
import ctypes
import platform
import psutil
import pyautogui
import pyjokes

import wikipedia
import feedparser
import pytz
from PIL import ImageGrab
import pytesseract
import speech_recognition as sr
import pyttsx3
import pywhatkit
import cv2
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from bs4 import BeautifulSoup
from email.header import decode_header
from geopy.geocoders import Nominatim
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tkinter as tk
from tkinter import scrolledtext, ttk
from pydub import AudioSegment

# Constants (configurable via config.json)
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CONFIG_FILE = "config.json"
LOG_FILE = "assistant_log.json"
COMMAND_HISTORY_FILE = "command_history.json"
LEARNING_DATA_FILE = "learning_data.json"

class VoiceAssistant:
    def __init__(self, web_mode=False):
        self.web_mode = web_mode
        self.load_config()
        self.engine = pyttsx3.init()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.command_queue = queue.Queue()
        self.is_listening = False
        self.last_command = ""
        self.command_history = []
        self.learning_data = self.load_learning_data()
        self.volume_controller = self.setup_volume_controller()
        self.setup_voice_engine()
         
        
    def load_config(self):
        """Load configuration from JSON file"""
        
        
        try:
            with open(CONFIG_FILE, "r") as f:
                self.config = json.load(f)
            # Merge with default config for any missing keys
            """for key, value in default_config.items():
                if key not in self.config:
                    self.config[key] = value"""
        except (FileNotFoundError, json.JSONDecodeError):
            """self.config = default_config
            with open(CONFIG_FILE, "w") as f:
                json.dump(default_config, f, indent=4)"""
    
    def load_learning_data(self):
        """Load learning data from file"""
        try:
            with open(LEARNING_DATA_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"frequent_commands": {}, "preferences": {}}
    
    def save_learning_data(self):
        """Save learning data to file"""
        with open(LEARNING_DATA_FILE, "w") as f:
            json.dump(self.learning_data, f, indent=4)
    
    def load_command_history(self):
        """Load command history from file"""
        try:
            with open(COMMAND_HISTORY_FILE, "r") as f:
                self.command_history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.command_history = []
    
    def save_command_history(self):
        """Save command history to file"""
        with open(COMMAND_HISTORY_FILE, "w") as f:
            json.dump(self.command_history, f, indent=4)
    
    def log_interaction(self, command, response):
        """Log user interactions"""
        timestamp = datetime.datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "command": command,
            "response": response
        }
        
        try:
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Error logging interaction: {e}")
    
    def setup_voice_engine(self):
        """Configure the text-to-speech engine"""
        voices = self.engine.getProperty('voices')
        if voices and len(voices) > self.config["voice"]["voice_id"]:
            self.engine.setProperty('voice', voices[self.config["voice"]["voice_id"]].id)
        self.engine.setProperty('rate', self.config["voice"]["rate"])
        self.engine.setProperty('volume', self.config["voice"]["volume"])
    
    def setup_volume_controller(self):
        """Initialize system volume controller"""
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
    
    def speak(self, text):
        """Convert text to speech"""
        self.engine.say(text)
        self.engine.runAndWait()
    
    def listen(self):
        """Listen for voice commands using microphone"""
        with self.microphone as source:
            print("Listening...")
            self.recognizer.adjust_for_ambient_noise(source)
            audio = self.recognizer.listen(source)
        
        try:
            command = self.recognizer.recognize_google(audio).lower()
            print(f"User said: {command}")
            return command
        except sr.UnknownValueError:
            print("Could not understand audio")
            return ""
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            return ""
    
    def process_command(self, command):
        """Process and execute voice commands"""
        if not command:
            return
        
        self.last_command = command
        self.command_history.append(command)
        self.update_learning_data(command)
        
        # Check for wake word
        if self.config["wake_word"] in command:
            command = command.replace(self.config["wake_word"], "").strip()
        
        response = ""
        
        # Remove web_mode restriction: allow all commands in both modes
        # Optionally, warn if system/desktop function is used in web mode

        # 🎤 Voice Interaction
        if "repeat" in command and "last command" in command:
            response = self.repeat_last_command()
        elif "confirm" in command:
            response = self.confirm_action(command)
        
        # 📆 Productivity & Reminders
        elif "remind me to" in command:
            response = self.set_reminder(command)
            if self.web_mode:
                response =  response
        elif "set an alarm" in command:
            response = self.set_alarm(command)
            if self.web_mode:
                response =  response
        elif "add to my to do list" in command:
            response = self.add_todo_item(command)
        elif "what's on my calendar today" in command:
            response = self.read_calendar_events()
            if self.web_mode:
                response =  response
        elif "set a timer" in command:
            response = self.set_timer(command)
            if self.web_mode:
                response =  response
        elif "take a note" in command:
            response = self.take_note(command)
        elif "send email" in command:
            response = self.send_email(command)
        elif "summarise my email" in command:
            response = self.summarize_emails()
        elif "translate" in command:
            response = self.translate_text(command)
        elif "add to shopping list" in command:
            response = self.add_shopping_item(command)
        
        # 🌐 Web & Search
        elif "search Google for" in command:
            response = self.search_google(command)
        elif "wikipedia" in command:
            response = self.search_wikipedia(command)
        elif "what is" in command or "who is" in command:
            response = self.answer_factual_question(command)
        elif "search youtube for" in command:
            response = self.search_youtube(command)
        elif "search YouTube" in command:
            response = self.search_youtube(command)
        elif "news headlines" in command:
            response = self.get_news_headlines()
        elif "open"  in command and "website" in command :

            response = self.open_website(command)
        
        # 🧮 Utilities & System Control
        elif "what time is it" in command:
            response = self.get_current_time()
        elif "what's today's date" in command:
            response = self.get_current_date()
        elif "open"   in command and "application" in command:
            response = self.open_application(command)
            if self.web_mode:
                response =  response
        elif "open downloads" in command or "open documents" in command:
            response = self.open_system_folder(command)
            if self.web_mode:
                response = response
        elif "increase volume" in command:
            response = self.adjust_volume("increase")
            if self.web_mode:
                response =  response
        elif "decrease volume" in command:
            response = self.adjust_volume("decrease")
            if self.web_mode:
                response =   response
        elif "mute" in command:
            response = self.adjust_volume("mute")
            if self.web_mode:
                response =  response
        elif "take a screenshot" in command:
            response = self.take_screenshot()
            if self.web_mode:
                response =  response
        elif "lock my computer" in command:
            response = self.lock_system()
            if self.web_mode:
                response =  response
        elif "shutdown" in command:
            response = self.shutdown_system()
            if self.web_mode:
                response =   response
        elif "restart" in command:
            response = self.restart_system()
            if self.web_mode:
                response =  response
        elif "battery percentage" in command:
            response = self.check_battery()
            if self.web_mode:
                response =  response
        elif "ip address" in command:
            response = self.get_ip_address()
        
        # 📱 Messaging & Communication
        elif "send whatsapp message" in command:
            response = self.send_whatsapp_message(command)
            if self.web_mode:
                response =  response
        
        
        
        
        # 🌦️ Weather & Location
        elif "weather in" in command:
            response = self.get_weather(command)
        elif "weekly forecast" in command:
            response = self.get_weekly_forecast(command)
        elif "my location" in command:
            response = self.get_current_location()
        elif "nearby" in command:
            response = self.find_nearby_places(command)
        elif "distance between" in command:
            response = self.get_distance(command)
        
        # 🎵 Entertainment
        elif "play song" in command:
            response = self.play_youtube_song(command)
        elif "play music" in command:
            response = self.play_local_music()
            if self.web_mode:
                response = response
        elif "tell me a joke" in command:
            response = self.tell_joke()
        elif "recommend a movie" in command:
            response = self.recommend_movie()
        elif "tell me a story" in command:
            response = self.tell_story() 
        elif "short story" in command:
            response = self.short_story(command)
        elif "roll a dice" in command:
            response = self.roll_dice()
        elif "flip a coin" in command:
            response = self.flip_coin()
        # --- Web-safe extra features ---
        
        elif "define" in command:
            response = self.get_dictionary_definition(command)
       
        
        else:
            response = "I didn't understand that command. Can you please repeat?"
        
        self.log_interaction(command, response)
        return response
    
    def update_learning_data(self, command):
        """Update learning data with the new command"""
        if command in self.learning_data["frequent_commands"]:
            self.learning_data["frequent_commands"][command] += 1
        else:
            self.learning_data["frequent_commands"][command] = 1
        self.save_learning_data()
    
    # 🎤 Voice Interaction Functions
    def repeat_last_command(self):
        """Repeat the last command"""
        if self.last_command:
            return f"You said: {self.last_command}"
        return "I don't have a last command to repeat."
    
    def confirm_action(self, command):
        """Confirm an action with the user"""
        action = command.replace("confirm", "").strip()
        return f"Please confirm, you want me to {action}. Is that correct?"
    
    # 📆 Productivity & Reminders Functions
    def set_reminder(self,command):
        try:
        # Ensure command has the correct structure
            if "remind me to" not in command.lower() or "at" not in command.lower():
                return "Please say: Remind me to <task> at <time>"

        # Normalize and extract parts
            command = command.lower().strip()
            task = command.split("remind me to")[1].split("at")[0].strip()
            time_part = command.split("at")[-1].strip()

        # Clean up time format
            time_part = time_part.replace(".", "").replace("am", "AM").replace("pm", "PM").upper()

        # If only hour is given (e.g., "7 PM"), add ":00"
            if re.match(r"^\d{1,2}\s?(AM|PM)$", time_part):
                time_part = time_part.replace(" ", "")
                time_part = time_part[:-2] + ":00 " + time_part[-2:]

            parsed_time = None

        # Try 12-hour format
            try:
                parsed_time = datetime.datetime.strptime(time_part, "%I:%M %p")
            except ValueError:
            # Try 24-hour format
                try:
                    parsed_time = datetime.datetime.strptime(time_part, "%H:%M")
                except ValueError:
                    return f"❌ I couldn't understand the time '{time_part}'."

        # Set reminder time
            now = datetime.datetime.now()
            reminder_time = parsed_time.replace(year=now.year, month=now.month, day=now.day)

            if reminder_time < now:
                reminder_time += datetime.timedelta(days=1)

            delta = (reminder_time - now).total_seconds()

        # Set the reminder (you can replace the print with your own function or chatbot callback)
            threading.Timer(delta, self.speak, [f"🔔 Reminder: {task}"]).start()

            

            return f"✅ I’ll remind you to {task} at {reminder_time.strftime('%I:%M %p')}."

        except Exception as e:
            return f"❌ Error: {str(e)}"
    def set_alarm(self,command):
        """Set an alarm for a specific time"""

        try:
            if "alarm for" not in command.lower():
                return "Please say: Set alarm for <time> (e.g., 7:30 AM or 19:30)"

        # Extract time part
            time_part = command.lower().split("alarm for")[1].strip()

        # Normalize
            time_part = time_part.replace(".", "").replace("am", "AM").replace("pm", "PM").upper()

        # If user says "7 PM", make it "7:00 PM"
            if re.match(r"^\d{1,2}\s?(AM|PM)$", time_part):
                time_part = time_part.replace(" ", "")
                time_part = time_part[:-2] + ":00 " + time_part[-2:]

        # Parse the time
            try:
                alarm_time = datetime.datetime.strptime(time_part, "%I:%M %p")
            except ValueError:
                try:
                    alarm_time = datetime.datetime.strptime(time_part, "%H:%M")
                except ValueError:
                    return f"❌ I couldn’t understand the time '{time_part}'."

        # Set to today or tomorrow
            now = datetime.datetime.now()
            alarm_time = alarm_time.replace(year=now.year, month=now.month, day=now.day)
            if alarm_time < now:
                alarm_time += datetime.timedelta(days=1)

            delta = (alarm_time - now).total_seconds()

            def play_alarm():
                for _ in range(5):
                    winsound.Beep(1000, 1000)
                    time.sleep(1)

            threading.Timer(delta, play_alarm).start()
            return f"✅ Alarm set for {alarm_time.strftime('%I:%M %p')}."

        except Exception as e:
            return f"❌ Error: {str(e)}"
            
    
    def add_todo_item(self, command):
        """Add an item to the to-do list"""
        item = command.split("add to my to do list")[1].strip()
        with open("todo_list.txt", "a") as f:
            f.write(f"- {item}\n")
        return f"Added '{item}' to your to-do list."
    
    def read_calendar_events(self):
        """Fetch and display only today's calendar events in local time, handling all-day and timed events."""
        import datetime
        import pytz
        creds = None
        # Load token or request OAuth access
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        try:
            service = build("calendar", "v3", credentials=creds)
            # Get local timezone
            local_tz = datetime.datetime.now().astimezone().tzinfo
            today = datetime.datetime.now(local_tz).date()
            # RFC3339 UTC format for start/end of today in local time
            start_of_day = datetime.datetime.combine(today, datetime.time.min).astimezone(local_tz)
            end_of_day = datetime.datetime.combine(today, datetime.time.max).astimezone(local_tz)
            time_min = start_of_day.astimezone(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
            time_max = end_of_day.astimezone(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=20,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            if not events:
                return " You have no events scheduled for today."
            response = " Today's calendar events:\n"
            for i, event in enumerate(events, 1):
                # Handle all-day and timed events
                start = event['start'].get('dateTime', event['start'].get('date'))
                summary = event.get('summary', 'Untitled Event')
                if 'dateTime' in event['start']:
                    # Timed event
                    dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                    local_dt = dt.astimezone(local_tz)
                    start_time = local_dt.strftime("%I:%M %p")
                    response += f"{i}. {summary} at {start_time}\n"
                else:
                    # All-day event
                    response += f"{i}. {summary} (All day)\n"
            return response.strip()
        except Exception as e:
            return f"❌ Could not fetch events: {str(e)}"

    
    def set_timer(self, command):
        """Set a countdown timer"""
        duration = 0
        if "minute" in command:
            duration = int(re.search(r'(\d+) minute', command).group(1)) * 60
        elif "second" in command:
            duration = int(re.search(r'(\d+) second', command).group(1))
        
        if duration > 0:
            threading.Timer(duration, self.speak, ["Your timer has ended"]).start()
            return f"Timer set for {duration} seconds."
        return "I couldn't understand the timer duration. Please try again."
    
    def take_note(self, command):
        """Take a note via voice"""
        note = command.split("take a note")[1].strip()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("notes.txt", "a") as f:
            f.write(f"[{timestamp}] {note}\n")
        return "Note saved successfully."
    
    

    
    def send_email(self,command):
   
        try:
        # Load configs
            with open("config.json", "r") as f:
                config = json.load(f)
            with open("email.json", "r") as f:
                contacts = json.load(f)

            email_cfg = config["email"]

        # Normalize and parse command
            command = command.lower()

            if "to" in command and "subject" in command and "body" in command:
                recipient_key = command.split("to")[1].split("with subject")[0].strip()
                subject = command.split("with subject")[1].split("and body")[0].strip()
                body = command.split("and body")[1].strip()

            # Lookup email from contact name
                recipient_email = contacts.get(recipient_key)
                if not recipient_email:
                    return f"❌ Contact '{recipient_key}' not found in contacts.json."

            # Compose email
                msg = MIMEText(body)
                msg["From"] = email_cfg["email_address"]
                msg["To"] = recipient_email
                msg["Subject"] = subject

            # Send via SMTP
                with smtplib.SMTP(email_cfg["smtp_server"], email_cfg["smtp_port"]) as server:
                    server.starttls()
                    server.login(email_cfg["email_address"], email_cfg["password"])
                    server.send_message(msg)

                return f"✅ Email sent to {recipient_key} with subject '{subject}'."
        
            return "❌ Please say: Send email to <name> with subject <subject> and body <message>"

        except Exception as e:
            return f"❌ Failed to send email: {str(e)}"

    
    def summarize_emails(self):
        """Summarize emails using IMAP (no c key needed)"""
        try:
            if not all([
            self.config["email"]["imap_server"], 
            self.config["email"]["email_address"], 
            self.config["email"]["password"]
            ]):
                return "Email credentials not configured."
        
            mail = imaplib.IMAP4_SSL(self.config["email"]["imap_server"])
            mail.login(self.config["email"]["email_address"], self.config["email"]["password"])
            mail.select("inbox")
        
            status, messages = mail.search(None, "UNSEEN")
            msg_nums = messages[0].split()
            unread_count = len(msg_nums)

            if unread_count == 0:
                return "✅ You have no unread emails."

            senders = []
            for num in msg_nums[-5:]:  # Get last 5 unread emails
                typ, msg_data = mail.fetch(num, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                sender = msg.get("From", "Unknown sender")

            # Decode sender name if encoded
                decoded_sender, encoding = decode_header(sender)[0]
                if isinstance(decoded_sender, bytes):
                    sender = decoded_sender.decode(encoding or "utf-8", errors="ignore")
                else:
                    sender = decoded_sender

            # Remove special characters and emojis
                sender = re.sub(r"[^\w\s@.<>\[\]\(\)\-]", "", sender)
                senders.append(sender.strip())

            mail.logout()

        # Prepare summary
            senders_list = ", ".join(senders[:3])
            more = f" and {len(senders) - 3} others" if len(senders) > 3 else ""
            return f"📧 You have {unread_count} unread emails. Recent senders: {senders_list}{more}."
    
        except Exception as e:
            return f"❌ Could not check emails: {str(e)}"
    
    def translate_text(self, command):
    
        try:
            try:
                from googletrans import Translator
            except ImportError:
                import subprocess
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'googletrans==4.0.0rc1'])
                from googletrans import Translator
            match = re.search(r'translate (.+) to (.+)', command, re.IGNORECASE)
            if not match:
                return "Please say: Translate <text> to <language>"
            text, dest_lang = match.group(1).strip(), match.group(2).strip().lower()
            translator = Translator()
            result = translator.translate(text, dest=dest_lang)
            if self.web_mode:
                # Return a JSON-like string for the web frontend
                return f'{{"translated": "{result.text}", "lang": "{result.dest}"}}'
            else:
                return f'Translation: {result.text}'
        except Exception as e:
            return f"❌ Could not translate: {str(e)}"
        
    def add_shopping_item(self, command):
        """Add an item to the shopping list"""
        item = command.split("add to shopping list")[1].strip()
        with open("shopping_list.txt", "a") as f:
            f.write(f"- {item}\n")
        return f"Added '{item}' to your shopping list."
    
    # 🌐 Web & Search Functions
    def search_google(self, command):
        """Search Google using command: 'hey buddy search google for <query>'"""
        # Normalize input
        command = command.lower().strip()
        wake_word = self.config["wake_word"].lower()

        # Remove wake word if present
        if wake_word in command:
            command = command.replace(wake_word, "").strip()

        # Accept both "search google for" and "search google"
        if "search google for" in command:
            query = command.split("search google for", 1)[1].strip()
        elif "search google" in command:
            query = command.split("search google", 1)[1].strip()
        else:
            query = ""

        if query:
            pywhatkit.search(query)
            return f"Searching Google for {query}"
        else:
            return "Please specify what you want to search on Google."
    
    def search_wikipedia(self, command):
        """Get a Wikipedia summary"""
        query = command.split("wikipedia")[0].strip()
        try:
            summary = wikipedia.summary(query, sentences=2)
            return summary
        except wikipedia.exceptions.DisambiguationError as e:
            return f"Multiple results found. Please be more specific: {', '.join(e.options[:3])}"
        except wikipedia.exceptions.PageError:
            return "No information found on Wikipedia."
    
    def answer_factual_question(self, command):
        """Answer factual questions using Wikipedia and web scraping"""
        question = command.strip()
        
        # First try Wikipedia
        try:
            summary = wikipedia.summary(question, sentences=2)
            return summary
        except:
            pass
        
        # Fallback to web scraping
        try:
            search_url = f"https://www.google.com/search?q={question.replace(' ', '+')}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(search_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to get featured snippet
            snippet = soup.find('div', class_='BNeawe s3v9rd AP7Wnd')
            if snippet:
                return snippet.get_text()
            
            # Try to get first result
            result = soup.find('div', class_='BNeawe vvjwJb AP7Wnd')
            if result:
                return result.get_text()
            
            return "I couldn't find an answer to that question."
        except Exception as e:
            return f"Search failed: {str(e)}"
    
    def search_youtube(self, command):
        """Search and play a YouTube video"""
        # Accept both 'search youtube for' and 'search youtube'
        if "search YouTube for" in command:
            query = command.split("search YouTube for", 1)[1].strip()
        elif "search YouTube" in command:
            query = command.split("search YouTube", 1)[1].strip()
        else:
            query = ""
        if not query:
            return "Please specify what you want to search on YouTube."
        pywhatkit.playonyt(query)
        return f"Playing YouTube video for {query}"
    def get_news_headlines(self):
        try:
            feed_urls = {
            "BBC": "http://feeds.bbci.co.uk/news/rss.xml",
            "CNN": "http://rss.cnn.com/rss/edition.rss",
            "Times Of India": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
            "NDTV": "https://feeds.feedburner.com/ndtvnews-top-stories",
            "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml"
            }

            headers = {'User-Agent': 'Mozilla/5.0'}
            headlines_output = "📰 Top News Headlines:\n"

            for source, url in feed_urls.items():
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    feed = feedparser.parse(response.content)

                    if not feed.entries:
                        headlines_output += f"\n❌ {source}: No headlines fetched.\n"
                        continue

                    headlines_output += f"\n {source}:\n"
                    for i, entry in enumerate(feed.entries[:3]):
                        headlines_output += f"  {i+1}. {entry.title}\n"

                except Exception as inner_e:
                    headlines_output += f"\n⚠️ {source}: Error - {str(inner_e)}\n"

            return headlines_output.strip()

        except Exception as e:
            return f"❌ Could not fetch news: {str(e)}"
    
    def open_website(self, command):
    
        command = command.lower()

        # Remove known filler words including wake words and command keywords
        keywords_to_remove = ["hey buddy", "open", "website", "the", "a"]
        for word in keywords_to_remove:
            command = command.replace(word, "")
    
        # Remove extra spaces
        site = command.strip().replace(" ", "")

    # Ensure URL starts correctly
        if not site.startswith("http"):
            site = f"https://www.{site}.com"

        webbrowser.open(site)
        return f"Opening {site}"
    
    # --- Web-safe extra features ---
    

    

    def get_dictionary_definition(self, command):
        try:
            word = command.split("define", 1)[1].strip()
            r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=5)
            if r.status_code == 200:
                data = r.json()
                meaning = data[0]['meanings'][0]['definitions'][0]['definition']
                return f"{word}: {meaning}"
            return f"No definition found for {word}."
        except Exception:
            return "Couldn't fetch definition."

    
    # 🧮 Utilities & System Control Functions
    def get_current_time(self):
        """Get the current time"""
        now = datetime.datetime.now().strftime("%I:%M %p")
        return f"The current time is {now}"
    
    def get_current_date(self):
        """Get today's date"""
        today = datetime.date.today().strftime("%B %d, %Y")
        return f"Today is {today}"
    
    def open_application(self, command):
        """Open a system application"""
        app = command.split("open application")[1].strip().lower()

    # Map spoken app names to the actual names typed in the Start menu
        app_map = {
        "notepad": "notepad",
        "calculator": "calculator",
        "paint": "paint",
        "word": "word",
        "excel": "excel",
        "chrome": "chrome",
        "vs code": "visual studio code",
        "youtube":"youtube"
        }

        if app in app_map:
            try:
                # Press Windows key to open Start menu
                pyautogui.press('win')
                time.sleep(0.5)  # slight delay to allow Start to open

                # Type the app name
                pyautogui.typewrite(app_map[app], interval=0.1)
                time.sleep(0.5)

                # Press Enter to open the app
                pyautogui.press('enter')
                return f"Opening {app}"
            except Exception as e:
                return f"Failed to open {app}: {e}"
        else:
            return f"I don't know how to open {app}"
    
    def open_system_folder(self, command):
        """Open a system folder"""
        folder = command.replace("open", "").strip().lower()
        folder_path = ""
        
        if "download" in folder:
            folder_path = self.config["paths"]["downloads"]
        elif "document" in folder:
            folder_path = self.config["paths"]["documents"]
        elif "music" in folder:
            folder_path = self.config["paths"]["music"]
        
        if folder_path and os.path.exists(folder_path):
            os.startfile(folder_path)
            return f"Opening {folder} folder"
        return f"Could not find the {folder} folder"
    
    def adjust_volume(self, action):
        """Adjust system volume"""
        current_volume = self.volume_controller.GetMasterVolumeLevelScalar()
        
        if action == "increase":
            new_volume = min(1.0, current_volume + 0.2)
            self.volume_controller.SetMasterVolumeLevelScalar(new_volume, None)
            return "Volume increased"
        elif action == "decrease":
            new_volume = max(0.0, current_volume - 0.2)
            self.volume_controller.SetMasterVolumeLevelScalar(new_volume, None)
            return "Volume decreased"
        elif action == "mute":
            self.volume_controller.SetMute(1, None)
            return "Volume muted"
    
    def take_screenshot(self):
        """Take a screenshot"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        pyautogui.screenshot(filename)
        return f"Screenshot saved as {filename}"
    
    def lock_system(self):
        """Lock the computer"""
        ctypes.windll.user32.LockWorkStation()
        return "Locking your computer"
    
    def shutdown_system(self):
        """Shutdown the computer"""
        os.system("shutdown /s /t 1")
        return "Shutting down the system"
    
    def restart_system(self):
        """Restart the computer"""
        os.system("shutdown /r /t 1")
        return "Restarting the system"
    
    def check_battery(self):
        """Check battery percentage"""
        battery = psutil.sensors_battery()
        if battery:
            return f"Battery is at {battery.percent}%"
        return "Could not check battery status"
    
    def get_ip_address(self):
        """Get system IP address"""
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            return f"Your IP address is {ip_address}"
        except Exception:
            return "Could not determine IP address"
    
    # 📱 Messaging & Communication Functions
  
    
    
    def send_whatsapp_message(self, command):
    # Load contacts
        with open("contacts.json", "r") as f:
            raw_contacts = json.load(f)
            contacts = {name.lower(): number for name, number in raw_contacts.items()}

    # Alias map (spoken → actual contact key)
        alias_map = {
        "amma": "amma",
        "ama": "amma",
        "am ma": "amma",
        "mommy": "mom",
        "mummy": "mom",
        "mum": "mom",
        "daddy": "dad"
    }

        try:
            command = command.lower()

            if "send whatsapp message" not in command:
                return "Say: send WhatsApp message <message> to <name>"

        # Split into message and recipient
            split_index = command.rfind(" to ")
            if split_index == -1:
                return "Please include 'to <name>' in your message."

            message = command.replace("send whatsapp message", "").strip()[:split_index].strip()
            recipient = command[split_index + 4:].strip().lower()

        # Normalize using alias
            true_name = alias_map.get(recipient, recipient)

            phone = contacts.get(true_name)
            if not phone:
                return f"❌ Contact '{recipient}' not found."

        # Send WhatsApp message instantly
            pywhatkit.sendwhatmsg_instantly(phone, message, wait_time=15, tab_close=False)
            return f"✅ Message sent to {true_name} ({phone})"

        except Exception as e:
            return f"❌ Error: {str(e)}"

    def read_whatsapp_messages(self):
        """Read WhatsApp messages (simulated)"""
        #pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"  # Change if needed
        pass
    def get_weather(self, command):
        """Get weather using OpenWeatherMap API (without API key by scraping)"""
        try:
        # Extract city name from command like "weather in Delhi"
            if "weather in" not in command.lower():
                return "❌ Please say something like 'What's the weather in Mumbai?'"
        
            city = command.lower().split("weather in")[1].strip()

        # Geocoding the city name
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}"
            geo_resp = requests.get(geo_url).json()
        
            if "results" not in geo_resp or not geo_resp['results']:
                return "❌ Couldn't find the city."

            lat = geo_resp['results'][0]['latitude']
            lon = geo_resp['results'][0]['longitude']
            city_name = geo_resp['results'][0]['name']

        # Get weather using latitude and longitude
            weather_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}&current_weather=true"
            )
            weather_resp = requests.get(weather_url).json()
            weather = weather_resp.get('current_weather', {})

            if not weather:
                return "❌ Couldn't fetch weather data."

            temperature = weather['temperature']
            windspeed = weather['windspeed']
            return f"🌤️ Weather in {city_name}: {temperature}°C, Wind speed: {windspeed} km/h"

        except Exception as e:
            return f"❌ Error getting weather: {str(e)}"
    def get_weekly_forecast(self, command):
        """Get weekly forecast by scraping"""
        command = command.lower()

    # Use fuzzy match to check for intent
        if fuzz.partial_ratio(command, "weekly forecast for") < 70:
            return "Sorry, I didn't understand that. Please use something like 'weekly forecast for Delhi'."

        try:
        # Extract city
            if "for" not in command:
                return "Please mention a city after 'for'."
        
            city_raw = command.split("for")[-1].strip().replace(" ", "+")
            url = f"https://wttr.in/{city_raw}?format=j1"  # JSON format
        
            response = requests.get(url)
            if response.status_code != 200:
                return f"Could not fetch weather for {city_raw}."

            data = response.json()
            forecast_days = data["weather"][:3]  # 3-day forecast

            forecast = ""
            for day in forecast_days:
                date = day["date"]
                maxtempC = day["maxtempC"]
                mintempC = day["mintempC"]
                description = day["hourly"][4]["weatherDesc"][0]["value"]  # midday description
                forecast += f"{date}: High {maxtempC}°C / Low {mintempC}°C, {description}\n"

            return f"3-day forecast for {city_raw.replace('+', ' ').title()}:\n{forecast.strip()}"

        except Exception as e:
            return f"Could not get forecast: {str(e)}"
    def get_current_location(self):
        """Get approximate location using geocoder (no API key needed)"""
        try:
            g = geocoder.ip('me')
            if g.city and g.country:
                return f"Your approximate location is {g.city}, {g.country}"
            return "Could not determine exact location, but you're near {g.latlng}"
        except Exception as e:
            return f"Location detection failed: {str(e)}"
    
    def find_nearby_places(self, command):
        """Find nearby places using OpenStreetMap"""
        try:
            place_type = command.split("nearby")[1].strip()
            g = geocoder.ip('me')
            
            if not g.latlng:
                return "Could not determine your location"
            
            # Use Nominatim (no API key needed)
            
            geolocator = Nominatim(user_agent="voice_assistant")
            location = geolocator.reverse(f"{g.latlng[0]}, {g.latlng[1]}")
            
            # Construct search query
            search_query = f"{place_type} near {location.address.split(',')[0]}"
            places = geolocator.geocode(search_query, exactly_one=False, limit=3)
            
            if not places:
                return f"No {place_type} found nearby"
            
            results = "\n".join(
                f"{i+1}. {place.address}" 
                for i, place in enumerate(places[:3])
            )
            return f"Nearby {place_type}:\n{results}"
        except Exception as e:
            return f"Place search failed: {str(e)}"
    
    def get_distance(self, command):
        """Get distance between two places (simulated)"""
        places = command.split("distance between")[1].strip().split("and")
        place1 = places[0].strip()
        place2 = places[1].strip()
        return f"Distance between {place1} and {place2} would appear here. This is a simulated response."
    
    # 🎵 Entertainment Functions
    def play_youtube_song(self, command):
        """Play a song on YouTube"""
        song = command.split("play song")[1].strip()
        pywhatkit.playonyt(song)
        return f"Playing {song} on YouTube"
    
    def play_local_music(self):
        """Play local music from folder"""
        music_folder = self.config["paths"]["music"]
        if os.path.exists(music_folder):
            os.startfile(music_folder)
            return "Opening your music folder"
        return "Could not find your music folder"
    
    def tell_joke(self):
        """Tell a random joke"""
        return pyjokes.get_joke()
    
    def recommend_movie(self,):
        """Recommend a movie by scraping IMDb"""
    
        api_key = "63208924ea0cb74bc778c873553eb687"  # 🔁 Replace this with your actual API key
        url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={api_key}"

        try:
            response = requests.get(url)
            data = response.json()

            if "results" in data:
                movie = random.choice(data["results"][:10])  # pick from top 10 trending
                title = movie.get("title", "Unknown")
                overview = movie.get("overview", "No description.")
                year = movie.get("release_date", "")[:4]

                return f" I recommend watching *{title}* ({year})\n Plot: {overview}"

            return "Couldn't fetch movie list."

        except Exception as e:
            return f"Error: {e}"
    def tell_story(self):
        try:
            url = "https://northccs.com/misc/short-story-examples-for-kids.html"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return "❌ Couldn't fetch stories right now."

            soup = BeautifulSoup(resp.text, "html.parser")

            # Stories start with <h4> and followed by <p> tags
            stories = []
            current_title = None
            current_content = []

            for tag in soup.find_all(['h4', 'p']):
                if tag.name == 'h4':
                    # Save previous story
                    if current_title and current_content:
                        stories.append((current_title, '\n'.join(current_content)))
                    current_title = tag.get_text(strip=True)
                    current_content = []
                elif tag.name == 'p':
                    text = tag.get_text(strip=True)
                    if text:
                        current_content.append(text)

            # Save the last story
            if current_title and current_content:
                stories.append((current_title, '\n'.join(current_content)))

            if not stories:
                return "⚠️ No stories found."

            # Pick a random story
            title, story = random.choice(stories)
            return f"{title}\n\n{story}"

        except Exception as e:
            return f"❌ Error fetching story: {e}" 
    
    def roll_dice(self):
        """Roll a dice"""
        return f"You rolled a {random.randint(1, 6)}"
    
    def flip_coin(self):
        """Flip a coin"""
        return "Heads" if random.random() > 0.5 else "Tails"
    
    # 🚀 Advanced Features
    def show_command_log(self):
        """Show recent command log"""
        try:
            with open(LOG_FILE, "r") as f:
                logs = [json.loads(line) for line in f.readlines()[-5:]]  # Last 5 entries
            response = "Recent commands:\n"
            for log in logs:
                response += f"{log['timestamp']}: {log['command']}\n"
            return response
        except Exception:
            return "No command log available."
    
    def show_frequent_commands(self):
        """Show frequently used commands"""
        if not self.learning_data["frequent_commands"]:
            return "No frequent commands recorded yet."
        
        sorted_commands = sorted(
            self.learning_data["frequent_commands"].items(),
            key=lambda x: x[1], reverse=True
        )[:5]  # Top 5
        
        response = "You frequently ask me to:\n"
        for cmd, count in sorted_commands:
            response += f"- {cmd} ({count} times)\n"
        return response
    
    def personalized_greeting(self):
        """Give a personalized greeting"""
        # In a real implementation, this would use face/voice recognition
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Good morning"
        elif 12 <= hour < 18:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"
        
        return f"{greeting}! How can I help you today?"
    
    def read_text_from_image(self):
        """Read text from image using pytesseract"""
        try:
            # Get the most recent image in Downloads folder
            downloads_path = self.config["paths"]["downloads"]
            image_files = [
                f for f in os.listdir(downloads_path) 
                if f.lower().endswith(('.png', '.jpg', '.jpeg'))
            ]
            
            if not image_files:
                return "No images found in your Downloads folder"
            
            # Sort by modification time and get the newest
            image_files.sort(key=lambda x: os.path.getmtime(os.path.join(downloads_path, x)))
            latest_image = os.path.join(downloads_path, image_files[-1])
            
            # Extract text
            text = pytesseract.image_to_string(Image.open(latest_image))
            if not text.strip():
                return "No readable text found in the image"
            
            return f"Text from image: {text[:200]}..."  # Limit to first 200 chars
        except Exception as e:
            return f"Could not read text from image: {str(e)}"
    
    
    
    # --- Extra Realistic Web Features ---
    def get_time_in_city(self, command):
        try:
            import pytz
            city = command.split("time in", 1)[1].strip()
            r = requests.get(f"https://worldtimeapi.org/api/timezone", timeout=5)
            if r.status_code == 200:
                zones = r.json()
                match = [z for z in zones if city.replace(' ', '_').title() in z or city.lower() in z.lower()]
                if match:
                    time_r = requests.get(f"https://worldtimeapi.org/api/timezone/{match[0]}", timeout=5)
                    if time_r.status_code == 200:
                        dt = time_r.json()['datetime']
                        return f"Current time in {city.title()}: {dt[11:16]}"
            return f"Couldn't find time for {city}."
        except Exception:
            return f"Couldn't get time for {city}."

    def get_advice(self, _):
        try:
            r = requests.get("https://api.adviceslip.com/advice", timeout=5)
            if r.status_code == 200:
                return r.json()['slip']['advice']
            return "Couldn't fetch advice."
        except Exception:
            return "Couldn't fetch advice."

    def motivate_me(self, _):
        try:
            r = requests.get("https://type.fit/api/quotes", timeout=5)
            if r.status_code == 200:
                quotes = r.json()
                import random
                q = random.choice(quotes)
                return f'"{q["text"]}" — {q.get("author", "Unknown")}'

            return "Couldn't fetch a motivational quote."
        except Exception:
            return "Couldn't fetch a motivational quote."

    def word_of_the_day(self, _):
        try:
            r = requests.get("https://api.wordnik.com/v4/words.json/wordOfTheDay?api_key=YOUR_WORDNIK_API_KEY", timeout=5)
            if r.status_code == 200:
                data = r.json()
                return f'{data["word"]}: {data["definitions"][0]["text"]}'
            return "Couldn't fetch word of the day."
        except Exception:
            return "Couldn't fetch word of the day."

    def tell_poem(self, _):
        try:
            r = requests.get("https://poetrydb.org/random", timeout=5)
            if r.status_code == 200:
                data = r.json()[0]
                return f'{data["title"]} by {data["author"]}:\n' + '\n'.join(data['lines'][:6])
            return "Couldn't fetch a poem."
        except Exception:
            return "Couldn't fetch a poem."

    def dad_joke(self, _):
        try:
            r = requests.get("https://icanhazdadjoke.com/", headers={"Accept": "application/json"}, timeout=5)
            if r.status_code == 200:
                return r.json()['joke']
            return "Couldn't fetch a dad joke."
        except Exception:
            return "Couldn't fetch a dad joke."

    def short_story(self, _):
        stories = [
            "Once upon a time, a little bird wanted to fly. She tried and tried, and one day, she soared above the clouds.",
            "A wise old turtle told the young fish: 'Patience is the key to every journey.' The fish listened, and found happiness.",
            "A child planted a seed. With care and love, it grew into a beautiful tree, giving shade to all."
        ]
        import random
        return random.choice(stories)

    def weather_suggestion(self, command):
        try:
            city = command.split("what should i wear in", 1)[1].strip().replace('?', '')
            r = requests.get(f"https://wttr.in/{city}?format=j1", timeout=5)
            if r.status_code == 200:
                data = r.json()
                temp = int(float(data['current_condition'][0]['temp_C']))
                if temp < 10:
                    return f"It's cold in {city.title()} ({temp}°C). Wear a jacket!"
                elif temp < 20:
                    return f"It's cool in {city.title()} ({temp}°C). A sweater should be fine."
                else:
                    return f"It's warm in {city.title()} ({temp}°C). Light clothes are good!"
            return "Couldn't fetch weather suggestion."
        except Exception:
            return "Couldn't fetch weather suggestion."

    def random_number(self, command):
        try:
            import random
            parts = command.lower().split()
            idx = parts.index("between")
            low = int(parts[idx+1])
            high = int(parts[idx+3]) if 'and' in parts else int(parts[idx+2])
            return f"Random number between {low} and {high}: {random.randint(low, high)}"
        except Exception:
            return "Couldn't generate a random number."

    def horoscope(self, command):
        try:
            sign = command.split("horoscope for", 1)[1].strip().capitalize()
            r = requests.get(f"https://ohmanda.com/api/horoscope/{sign.lower()}/", timeout=5)
            if r.status_code == 200:
                return r.json()['horoscope']
            return f"Couldn't fetch horoscope for {sign}."
        except Exception:
            return "Couldn't fetch horoscope."
    
    def run(self):
        """Main run loop for the voice assistant"""
        print("Voice Assistant is ready!")
        self.speak("Voice Assistant is ready!")
        
        
        
        while True:
            try:
                command = self.listen()
                if command and self.config["wake_word"] in command.lower():
                    response = self.process_command(command)
                    if response:
                        print(f"Assistant: {response}")
                        self.speak(response)
            except KeyboardInterrupt:
                print("\nGoodbye!")
                self.save_command_history()
                self.save_learning_data()
                sys.exit(0)
            except Exception as e:
                print(f"Error: {e}")
                continue

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        from flask import Flask, render_template, request, jsonify
        import speech_recognition as sr
        from pydub import AudioSegment
        app = Flask(__name__)
        assistant = VoiceAssistant(web_mode=True)

        @app.route("/")
        def index():
            return render_template("index.html")

        @app.route("/process_audio", methods=["POST"])
        def process_audio():
            if 'audio' not in request.files:
                return jsonify({"error": "No audio received."}), 400
            audio_file = request.files['audio']
            audio_path = "input_upload.webm"  # Save as webm to match frontend
            audio_file.save(audio_path)
            try:
                # Always use webm as input format
                sound = AudioSegment.from_file(audio_path, format="webm")
                sound.export("input.wav", format="wav")
            except Exception as e:
                return jsonify({"error": f"Audio conversion failed: {str(e)}"}), 500
            recognizer = sr.Recognizer()
            with sr.AudioFile("input.wav") as source:
                audio = recognizer.record(source)
                try:
                    command = recognizer.recognize_google(audio)
                    print(f"Recognized command: {command}")
                    response = assistant.process_command(command)
                    return jsonify({"response": response})
                except Exception as e:
                    return jsonify({"error": str(e)}), 500

        if __name__ == '__main__':
            print("🚀 Starting Flask server...")
            app.run(debug=True)
    else:
        assistant = VoiceAssistant()
        assistant.run() # type: ignore
