import os
from dotenv import load_dotenv
load_dotenv()
from google import genai
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
try:
    print("Testing gemini-1.5-flash...")
    res = client.models.generate_content(model='gemini-1.5-flash', contents="Hello")
    print("Success: " + res.text.strip())
except Exception as e:
    print(f"Error 1.5: {e}")

try:
    print("Testing gemini-3.6-flash...")
    res = client.models.generate_content(model='gemini-3.6-flash', contents="Hello")
    print("Success: " + res.text.strip())
except Exception as e:
    print(f"Error 3.6: {e}")
