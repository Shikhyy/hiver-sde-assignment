import os
import json
import time
import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()

class Label(BaseModel):
    tweet_id: str = Field(description="The customer tweet ID")
    intent: str = Field(description="One of: technical_issue, account_access, repair_and_service, complaint, general_inquiry")
    action: str = Field(description="One of: auto, escalate. Escalate if the user is extremely angry, threatening legal action, or requires sensitive account info. Otherwise auto.")

class BatchLabels(BaseModel):
    labels: list[Label]

def auto_label():
    # Make sure we use the API key from the environment
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    df = pd.read_csv('data/apple_support_golden_set.csv')
    df['intent_label'] = df['intent_label'].astype('object')
    df['action_label'] = df['action_label'].astype('object')
    
    # Process in chunks of 20 to avoid rate limits and context overload
    chunk_size = 20
    
    for i in range(0, len(df), chunk_size):
        chunk = df.iloc[i:i+chunk_size]
        
        prompt = "Analyze the following customer support tweets directed at Apple Support.\n\n"
        for _, row in chunk.iterrows():
            prompt += f"Tweet ID: {row['customer_tweet_id']}\nText: {row['customer_text']}\n---\n"
            
        print(f"Processing chunk {i} to {i+len(chunk)} (out of {len(df)})...", flush=True)
        
        try:
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=BatchLabels,
                    temperature=0.1
                ),
            )
            
            batch_result = json.loads(response.text)
            for lbl in batch_result.get('labels', []):
                # Update the dataframe
                idx = df.index[df['customer_tweet_id'].astype(str) == lbl['tweet_id']].tolist()
                if idx:
                    df.at[idx[0], 'intent_label'] = lbl['intent']
                    df.at[idx[0], 'action_label'] = lbl['action']
                    
            print(f"Successfully processed chunk.", flush=True)
            time.sleep(2) # Small delay to respect free tier RPM limits
        except Exception as e:
            print(f"Error on chunk {i}: {e}")
            # Try to print the raw response text if json failed
            if hasattr(e, 'response') and e.response:
                print(e.response.text)
            
    out_path = 'data/apple_support_golden_set_labeled.csv'
    df.to_csv(out_path, index=False)
    print(f"\nSuccessfully labeled dataset saved to {out_path}")
    
    # Print a quick summary of the labels
    print("\nIntent Distribution:")
    print(df['intent_label'].value_counts())
    print("\nAction Distribution:")
    print(df['action_label'].value_counts())

if __name__ == "__main__":
    auto_label()
