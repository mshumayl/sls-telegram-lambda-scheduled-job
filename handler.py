from collections import defaultdict
import json
import os
import requests
from supabase import create_client, Client
from datetime import datetime, timedelta

session_dict_short = {
    "firstSlot": "S1",
    "secondSlot": "S2",
    "thirdSlot": "S3"
}

session_dict_long = {
    "first_session": "(11.30am-1.00pm)",
    "second_session": "(1.00pm-2.30pm)",
    "third_session": "(2.30pm-4.00pm)"
}

def handle_request(event, context):
    data = None
    response = None
    
    try:
        data, count = query_data()
        message = prepare_message(data, count)
        response = {
            "statusCode": 200,
            "body": "data"
        }
        send_to_bot(message)
    except Exception as e:
        raise e
        
    return response

def send_to_bot(message):
    bot_token = os.environ.get("telegram_token")
    chat_id = os.environ.get("chat_id")
    api_message = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={message}"
    print(api_message)
    requests.get(api_message)

def query_data():
    supabase_url = os.environ.get("supabase_url")
    supabase_key = os.environ.get("supabase_key")

    supabase = create_client(supabase_url, supabase_key)
    data, count = supabase.table('RsvpResponse').select("name", "attendanceCt", "timeSlot", "createdAt", count="exact").order("createdAt", desc=True).execute()
    
    return data, count

def prepare_message(data, count):
    message = ""
    
    total_attendees = 0
    submissions = count[1]
    last_5_submissions = []
    attendees_by_session = {
        "first_session": 0,
        "second_session": 0,
        "third_session": 0,
    }
    remaining_slots = {
        "first_session": "",
        "second_session": "",
        "third_session": "",
    }
    new_attendees_by_day = defaultdict(int)
    today_new_attendees_by_hour = defaultdict(int)
    
    internal_counter = 0
    
    # Calculate total attendees
    for d in data[1]:
        
        if not d["attendanceCt"]:
            continue
        
        if internal_counter < 5:
            last_5_submissions.append(d)
        
        internal_counter += 1
        
        total_attendees += d["attendanceCt"]
        
        if d["timeSlot"] == "firstSlot":
            attendees_by_session["first_session"] += d["attendanceCt"]
        elif d["timeSlot"] == "secondSlot":
            attendees_by_session["second_session"] += d["attendanceCt"]
        else:
            attendees_by_session["third_session"] += d["attendanceCt"]
        
        date = d["createdAt"].split("T")[0]
        
        new_attendees_by_day[date] += d["attendanceCt"]
        
        current_utc_date = datetime.utcnow().date()
        date_object = datetime.strptime(date, "%Y-%m-%d").date()
        
        if date_object == current_utc_date:
            hour = int(d["createdAt"].split("T")[1].split(":")[0]) + 8
            today_new_attendees_by_hour[hour] += d["attendanceCt"]
            
    remaining_slots["first_session"] = f"{350 - attendees_by_session['first_session']}/350"
    remaining_slots["second_session"] = f"{350 - attendees_by_session['second_session']}/350"
    remaining_slots["third_session"] = f"{350 - attendees_by_session['third_session']}/350"
    
    # Convert for better rendering
    new_attendees_by_day = dict(new_attendees_by_day) 
    today_new_attendees_by_hour = dict(today_new_attendees_by_hour)
    
    current_time = datetime.utcnow() + timedelta(hours=8)
    
    message = f"RSVP Response Update\n{current_time}\n————————————————\nTotal Attendees: {total_attendees} ({submissions} submissions)\n\nAttendees by Session:\n"
    for k in attendees_by_session.keys():
        message += f"{session_dict_long[k]} — {attendees_by_session[k]}\n"
        
    message += "\nRemaining Slots by Session:\n"
    for rk in remaining_slots.keys():
        message += f"{session_dict_long[rk]} — {remaining_slots[rk]}\n"
        
    message += "\nNew Attendees Registered by Day:\n"
    for nbd in new_attendees_by_day.keys():
        message += f"{nbd} — {new_attendees_by_day[nbd]}\n"
        
    message += "\nNew Attendees Registered by Hour (Today):\n"
    for nbhtoday in today_new_attendees_by_hour.keys():
        message += f"{nbhtoday}00hrs — {today_new_attendees_by_hour[nbhtoday]}\n"
            
    message += "\nLast 5 Responses:\n"
    for response in last_5_submissions:
        message += f"{response['createdAt'].split('.')[0].replace('T', ' ').split('0', 1)[1]} — {response['name']}, {response['attendanceCt']}pax ({session_dict_short[response['timeSlot']]})\n"
    
    return message