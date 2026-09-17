import os
import json
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from pipeline import HiverPipeline

load_dotenv()


class EvaluationScore(BaseModel):
    helpfulness_score: int = Field(description="Score from 1 to 5")
    brand_tone_score: int = Field(description="Score from 1 to 5")
    reasoning: str = Field(description="Short explanation for the scores")


def evaluate_reply(client, customer_text, ground_truth, ai_draft):
    if ai_draft == "[ESCALATED TO HUMAN AGENT]":
        return EvaluationScore(
            helpfulness_score=0, brand_tone_score=0, reasoning="Escalated"
        )

    prompt = f"""
    You are an expert customer support QA evaluator for AppleSupport.
    
    Customer Tweet: "{customer_text}"
    Real Human Agent Reply (Ground Truth): "{ground_truth}"
    AI Drafted Reply: "{ai_draft}"
    
    Grade the AI Drafted Reply on a scale of 1-5 for:
    1. Helpfulness (Does it actually address the user's issue as well as the human did?)
    2. Brand Tone (Does it sound professional, empathetic, and on-brand for Apple?)
    """

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EvaluationScore,
                temperature=0.1,
            ),
        )
        return EvaluationScore.model_validate_json(response.text)
    except Exception as e:
        print(f"Eval Error: {e}")
        return EvaluationScore(
            helpfulness_score=1, brand_tone_score=1, reasoning="Evaluation Failed"
        )


def run_evaluation():
    import time

    print("Loading Golden Set...")
    df = pd.read_csv("data/apple_support_golden_set_labeled.csv")

    # LIMIT to 10 rows for demonstration purposes to avoid 15 RPM free tier limits.
    # To evaluate all 200, remove the .head(10) below.
    df = df.head(10)

    pipeline = HiverPipeline()
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    results = []

    print(f"Evaluating {len(df)} examples (Rate limited to 15 RPM)...")
    for idx, row in tqdm(df.iterrows(), total=len(df)):
        time.sleep(4)  # Respect free tier rate limit of 15 RPM (4 seconds per call)
        customer_text = row["customer_text"]
        ground_truth = row["brand_response_text"]

        # 1. Run Pipeline
        try:
            output = pipeline.process(customer_text)
        except Exception as e:
            print(f"Pipeline error on row {idx}: {e}")
            continue

        # 2. Grade Output
        score = evaluate_reply(client, customer_text, ground_truth, output["draft"])

        results.append(
            {
                "tweet_id": row["customer_tweet_id"],
                "customer_text": customer_text,
                "ground_truth": ground_truth,
                "ai_draft": output["draft"],
                "pipeline_intent": output["intent"],
                "pipeline_action": output["action"],
                "pipeline_reason": output["reason"],
                "helpfulness_score": score.helpfulness_score,
                "brand_tone_score": score.brand_tone_score,
                "eval_reasoning": score.reasoning,
            }
        )

    results_df = pd.DataFrame(results)

    if len(results_df) == 0:
        print(
            "\nAll evaluations failed (likely due to API rate limits). Try again in a few minutes."
        )
        return

    results_df.to_csv("data/evaluation_results.csv", index=False)

    print("\n--- EVALUATION METRICS ---")

    # Exclude escalated ones from drafting score
    drafted_only = results_df[results_df["ai_draft"] != "[ESCALATED TO HUMAN AGENT]"]
    if len(drafted_only) > 0:
        avg_helpful = drafted_only["helpfulness_score"].mean()
        avg_tone = drafted_only["brand_tone_score"].mean()
        print(f"Average Helpfulness Score: {avg_helpful:.2f} / 5.0")
        print(f"Average Brand Tone Score:  {avg_tone:.2f} / 5.0")

    escalation_rate = (len(results_df) - len(drafted_only)) / len(results_df) * 100
    print(f"Escalation Rate:           {escalation_rate:.1f}%")

    print("\nResults saved to data/evaluation_results.csv")


if __name__ == "__main__":
    run_evaluation()
