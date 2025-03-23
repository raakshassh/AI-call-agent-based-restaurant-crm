import os
import logging
import json
from datetime import datetime, timedelta
import pytz
from flask import Blueprint, request
from twilio.twiml.voice_response import VoiceResponse, Gather
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google.generativeai import configure, GenerativeModel
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

IST = pytz.timezone('Asia/Kolkata')

# Google Calendar setup
SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
CALENDAR_ID = os.getenv("CID")
logging.info(f"Using Calendar ID: {CALENDAR_ID}")

# Gemini setup
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logging.error("GOOGLE_API_KEY is not set in .env file!")
else:
    try:
        configure(api_key=GOOGLE_API_KEY)
        gemini_model = GenerativeModel('gemini-2.0-flash-001')
        logging.info("✅ Gemini Flash API authenticated successfully!")
    except Exception as e:
        logging.error(f"❌ Gemini Flash API authentication failed: {e}")
        gemini_model = None

# Google Calendar authentication
if not CREDENTIALS_PATH:
    logging.error("GOOGLE_APPLICATION_CREDENTIALS is not set in .env file!")
    service = None
else:
    try:
        creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
        service = build("calendar", "v3", credentials=creds)
        logging.info("✅ Google Calendar API authenticated successfully!")
    except Exception as e:
        logging.error(f"❌ Google Calendar API authentication failed: {e}")
        service = None

routes_bp = Blueprint("routes", __name__)

RESTAURANT_INFO = {
    "hours": {
        "monday": "11:00 AM to 10:00 PM",
        "tuesday": "11:00 AM to 10:00 PM",
        "wednesday": "11:00 AM to 10:00 PM",
        "thursday": "11:00 AM to 10:00 PM",
        "friday": "11:00 AM to 11:00 PM",
        "saturday": "10:00 AM to 11:00 PM",
        "sunday": "10:00 AM to 9:00 PM"
    },
    "menu_highlights": [
        "Our chef's special butter chicken",
        "Paneer tikka masala",
        "Lamb biryani",
        "Vegetable samosas",
        "Garlic naan",
        "Mango lassi"
    ]
}

def process_with_gemini(user_input):
    """Process user input using Gemini Flash to detect intent and generate response"""
    if not gemini_model:
        # Fallback to simple intent detection if Gemini is not available
        return fallback_process(user_input)
    
    try:
        prompt = f"""
        You are an AI assistant for a restaurant. The user has said: "{user_input}"
        
        Context information:
        Restaurant hours: {json.dumps(RESTAURANT_INFO['hours'])}
        Menu highlights: {json.dumps(RESTAURANT_INFO['menu_highlights'])}
        Current time in IST: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')}
        
        Analyze the input and provide:
        1. Intent (hours, menu, reservation, or unknown)
        2. If reservation intent, extract the date, time, and party size
        3. A natural response based on the detected intent
        
        Format your response as a JSON object with these exact keys:
        - intent: string (hours, menu, reservation, or unknown)
        - reservation_details: object (only if intent is reservation) with keys:
          - datetime: string (ISO format date-time in IST timezone)
          - party_size: number (default to 2 if not specified)
        - response_text: string (your natural language response)
        
        Ensure your response is valid JSON.
        """
        
        response = gemini_model.generate_content(prompt)
        response_text = response.text
        
        # Try to extract JSON from the response if it's not already in JSON format
        if not response_text.strip().startswith('{'):
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            else:
                # Try to find any JSON-like structure
                json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
        
        result = json.loads(response_text)
        logging.info(f"Gemini processed intent: {result['intent']}")
        return result
    except Exception as e:
        logging.error(f"❌ Error using Gemini: {str(e)}")
        logging.error(f"Response was: {response.text if 'response' in locals() else 'No response'}")
        return fallback_process(user_input)

def fallback_process(user_input):
    """Fallback processing when Gemini is unavailable"""
    user_input_lower = user_input.lower()
    
    if any(word in user_input_lower for word in ['hour', 'open', 'close', 'timing']):
        intent = "hours"
        response_text = get_hours_info(user_input)
    elif any(word in user_input_lower for word in ['menu', 'food', 'dish', 'specialty', 'serve', 'eat']):
        intent = "menu"
        response_text = get_menu_info(user_input)
    elif any(word in user_input_lower for word in ['book', 'reserve', 'reservation', 'table', 'seat']):
        intent = "reservation"
        reservation_details = parse_reservation_time(user_input)
        if reservation_details:
            reservation_time = datetime.fromisoformat(reservation_details["datetime"])
            formatted_time = reservation_time.strftime('%A, %B %d at %I:%M %p IST')
            response_text = f"I'll book your reservation for {formatted_time} for {reservation_details['party_size']} people."
            return {
                "intent": intent,
                "reservation_details": reservation_details,
                "response_text": response_text
            }
        else:
            response_text = "I couldn't understand when you want to make a reservation. Please specify a day and time."
    else:
        intent = "unknown"
        response_text = "I'm not sure I understood. You can ask about our hours, our menu, or make a reservation."
    
    return {
        "intent": intent,
        "response_text": response_text
    }

# Original functions kept as fallbacks
def parse_reservation_time(user_input):
    logging.info(f"🗣️ User Input: {user_input}")
    
    import dateparser
    import re
    now_ist = datetime.now(IST)
    
    parsed_date = dateparser.parse(user_input, settings={
        'PREFER_DATES_FROM': 'future',
        'TIMEZONE': 'Asia/Kolkata',
        'RETURN_AS_TIMEZONE_AWARE': True
    })
    
    if not parsed_date:
        oclock_match = re.search(r'(\d{1,2})\s*(?:o\'?clock)', user_input, re.IGNORECASE)
        if oclock_match:
            hour = int(oclock_match.group(1))
            
            if 5 <= hour <= 10:
                hour += 12
            
            today = now_ist.replace(tzinfo=None)
            
            if 'tomorrow' in user_input.lower():
                base_date = today + timedelta(days=1)
            else:
                base_date = today
                
            parsed_date = base_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            parsed_date = IST.localize(parsed_date)
        else:
            time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)', user_input, re.IGNORECASE)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                period = time_match.group(3).lower()
                
                if ('pm' in period or 'p.m.' in period) and hour < 12:
                    hour += 12
                elif ('am' in period or 'a.m.' in period) and hour == 12:
                    hour = 0
                
                today = now_ist.replace(tzinfo=None)
                
                if 'tomorrow' in user_input.lower():
                    base_date = today + timedelta(days=1)
                elif 'tonight' in user_input.lower():
                    base_date = today
                else:
                    base_date = today
                    
                parsed_date = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                parsed_date = IST.localize(parsed_date)
    
    if parsed_date and parsed_date < now_ist:
        if parsed_date.date() == now_ist.date():
            parsed_date = parsed_date + timedelta(days=1)
    
    if parsed_date:
        logging.info(f"📅 Parsed Date-Time (IST): {parsed_date.isoformat()}")
        
        party_size = 2
        party_match = re.search(r'(\d+)\s*(people|person|guests?)', user_input, re.IGNORECASE)
        if party_match:
            party_size = int(party_match.group(1))
        
        return {
            "datetime": parsed_date.isoformat(),
            "party_size": party_size
        }
    else:
        logging.warning("⚠️ Could not parse date-time.")
        return None

def get_hours_info(user_input):
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    today = datetime.now(IST).strftime("%A").lower()
    
    for day in days:
        if day in user_input.lower():
            return f"Our hours on {day.capitalize()} are {RESTAURANT_INFO['hours'][day]}."
    
    if "today" in user_input.lower():
        return f"Our hours today ({today.capitalize()}) are {RESTAURANT_INFO['hours'][today]}."
    elif "tomorrow" in user_input.lower():
        tomorrow_idx = (days.index(today) + 1) % 7
        tomorrow = days[tomorrow_idx]
        return f"Our hours tomorrow ({tomorrow.capitalize()}) are {RESTAURANT_INFO['hours'][tomorrow]}."
    else:
        hours_list = ", ".join([f"{day.capitalize()}: {hours}" for day, hours in RESTAURANT_INFO['hours'].items()])
        return f"Our restaurant hours are: {hours_list}"

def get_menu_info(user_input):
    menu_items = ", ".join(RESTAURANT_INFO['menu_highlights'])
    return f"Some of our popular menu items include: {menu_items}. We offer a variety of vegetarian and non-vegetarian dishes."

@routes_bp.route("/voice", methods=["POST"])
def voice_response():
    response = VoiceResponse()
    response.say("Welcome to our restaurant. How can I assist you today? You can ask about our hours, menu, or make a reservation.")
    gather = Gather(input="speech", action="/process-voice", method="POST", timeout=5)
    response.append(gather)
    return str(response)

@routes_bp.route("/process-voice", methods=["POST"])
def process_voice():
    user_input = request.form.get("SpeechResult", "").strip()
    response = VoiceResponse()
    
    if not user_input:
        response.say("I'm sorry, I didn't hear your request. Could you please repeat?")
        gather = Gather(input="speech", action="/process-voice", method="POST", timeout=5)
        response.append(gather)
        return str(response)
    
    # Process with Gemini Flash
    gemini_result = process_with_gemini(user_input)
    intent = gemini_result["intent"]
    ai_response = gemini_result["response_text"]
    
    # Say the AI response
    response.say(ai_response)
    
    # Handle reservation if detected
    if intent == "reservation" and "reservation_details" in gemini_result:
        try:
            details = gemini_result["reservation_details"]
            reservation_time = datetime.fromisoformat(details["datetime"])
            end_time = reservation_time + timedelta(hours=2)
            
            event = {
                "summary": f"Restaurant Reservation ({details['party_size']} people)",
                "description": f"Reservation made via voice system. Original request: '{user_input}'",
                "start": {
                    "dateTime": reservation_time.isoformat(),
                    "timeZone": "Asia/Kolkata"
                },
                "end": {
                    "dateTime": end_time.isoformat(),
                    "timeZone": "Asia/Kolkata"
                }
            }
            
            if service:
                service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
                logging.info(f"✅ Event created successfully")
                
                additional_info = f"Your reservation has been confirmed for {reservation_time.strftime('%A, %B %d at %I:%M %p')}."
                response.say(additional_info)
            else:
                logging.warning("⚠️ Using mock calendar event (service not available)")
        except Exception as e:
            logging.error(f"❌ Reservation Error: {e}")
            response.say("There was an issue with your reservation. Please call the restaurant directly.")
    
    # Continue conversation
    response.say("Is there anything else I can help you with?")
    gather = Gather(input="speech", action="/process-voice", method="POST", timeout=5)
    response.append(gather)
    
    # Log conversation
    with open("restaurant_conversations.log", "a") as file:
        file.write(f"User: {user_input}\nIntent: {intent}\nAI: {ai_response}\n\n")
    
    return str(response)

# Function to configure routes in the main Flask app
def configure_routes(app):
    app.register_blueprint(routes_bp)