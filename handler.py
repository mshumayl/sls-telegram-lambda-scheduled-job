import json
import os
import requests
from supabase import create_client, Client

def handle_request(event, context):
    data = None
    
    try:
        data = query_data()
        response = {
            "statusCode": 200,
            "body": json.dumps(data)
        }
        send_to_bot(json.dumps(data))
        
    except Exception as e:
        response = {
            "statusCode": 400,
            "body": e
        }
        send_to_bot(json.dumps(e))
        
    return response

def send_to_bot(message):
    bot_token = os.environ.get("telegram_token")
    chat_id = os.environ.get("chat_id")
    api_message = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={message}"
    requests.get(api_message)

def query_data():
    supabase_url = os.environ.get("supabase_url")
    supabase_key = os.environ.get("supabase_key")
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    rsvp_responses = supabase.table("RsvpResponse").select("*").limit(10).execute()
    
    return rsvp_responses