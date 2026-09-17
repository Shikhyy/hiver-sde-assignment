import os
import json
import logging
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure production-grade logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("HiverPipeline")


class ClassificationResult(BaseModel):
    intent: str
    action: str = Field(description="auto or escalate")
    reason: str = Field(description="Reason for escalation or auto-handling")


class DrafterResult(BaseModel):
    reply: str


class HiverPipeline:
    def __init__(self):
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.brand = "AppleSupport"
        self.model_name = "gemini-3.6-flash"

    # Exponential backoff retry logic to handle API rate limits and network flakes
    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def classify_and_route(self, customer_text: str) -> ClassificationResult:
        logger.info(f"Classifying inbound tweet: '{customer_text[:50]}...'")

        prompt = f"""
        You are an AI router for {self.brand}.
        Analyze this customer tweet: "{customer_text}"
        
        1. Classify the intent into a category like: technical_issue, account_access, general_inquiry, complaint.
        2. Decide if we should 'auto' handle it or 'escalate' to a human.
        
        ESCALATION RULES:
        - Auto: Standard technical questions, battery issues, forgotten passwords, general questions.
        - Escalate: Extreme anger, profanity, threats of legal action, or requests requiring backend account access.
        
        Examples:
        - "My screen is cracked, how much is repair?" -> intent: repair_and_service, action: auto
        - "You guys are the worst company ever, I'm suing you for losing my data!" -> intent: complaint, action: escalate
        """

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ClassificationResult,
                temperature=0.0,  # Strict zero temp for routing logic
            ),
        )
        return ClassificationResult.model_validate_json(response.text)

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def draft_reply(self, customer_text: str, intent: str) -> str:
        logger.info(f"Drafting automated reply for intent: {intent}")

        prompt = f"""
        You are an official support agent for {self.brand} on Twitter.
        
        Guidelines:
        - Keep it under 280 characters.
        - Tone: Empathetic, professional, direct, and helpful.
        - Never use hashtags unless absolutely necessary.
        - If troubleshooting requires details, ask them to DM (Direct Message).
        
        Example 1 (Technical Issue):
        Customer: "My iPhone battery drains completely in 2 hours since the update."
        Draft: "We want to help with your iPhone battery life. DM us which iOS version you are currently running and we can look into this together."
        
        Example 2 (Account Access):
        Customer: "I forgot my apple ID password and am locked out."
        Draft: "We know how important it is to access your account. Check out this link for steps to reset your password securely: http://apple.co/password"
        
        Now, draft a reply for:
        Customer Tweet: "{customer_text}"
        Intent: {intent}
        """

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3  # Low temp for consistency
            ),
        )
        return response.text.strip()

    def process(self, customer_text: str) -> dict[str, str]:
        # 1. Classify & Route
        routing = self.classify_and_route(customer_text)

        # 2. Draft if auto
        reply = ""
        if routing.action == "auto":
            reply = self.draft_reply(customer_text, routing.intent)
            logger.info("Successfully drafted automated response.")
        else:
            reply = "[ESCALATED TO HUMAN AGENT]"
            logger.warning(f"Tweet escalated. Reason: {routing.reason}")

        return {
            "intent": routing.intent,
            "action": routing.action,
            "reason": routing.reason,
            "draft": reply,
        }


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    pipeline = HiverPipeline()
    test_tweet = "My iPhone screen just went completely black and won't turn on! Help!"
    print(json.dumps(pipeline.process(test_tweet), indent=2))
