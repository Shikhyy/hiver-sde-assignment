# 🤖 Hiver AI Customer Support Pipeline

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

> **Hiver SDE Intern Assignment**  
> An autonomous LLM pipeline that classifies, safely routes, and drafts empathetic responses to `@AppleSupport` customer tweets using Google's `gemini-3.6-flash`.

---

## 🚀 Quickstart (Reproduce in < 5 mins)

**Prerequisites:** Python 3.10+ and a Google Gemini API Key.

```bash
# 1. Clone the repository
git clone https://github.com/Shikhyy/hiver-sde-assignment.git
cd hiver-sde-assignment

# 2. Add your API key
echo "GEMINI_API_KEY=your_key_here" > .env

# 3. Execute the automated Makefile
make setup   # Creates environment and installs dependencies
make test    # Runs the pytest suite (with mocked API calls)
make run     # Executes the end-to-end pipeline demonstration
```

*(Note: To re-run the full 200-row LLM-as-a-judge evaluation harness, simply run `python evaluator.py`. It is omitted from the default `make run` due to free-tier API rate limits, which cause the 200 rows to take >15 minutes to evaluate).*

---

## 🧠 1. Problem Framing & Pipeline Architecture

**The Problem:** Customer support teams are overwhelmed by high-volume, low-complexity queries (e.g., password resets) while critical issues (angry customers, hardware failures) get buried in the queue. 

**The Solution:** I built a two-stage LLM pipeline to act as a triage agent for `@AppleSupport`:
1. **The Router:** Classifies the intent (e.g., `technical_issue`, `complaint`) and strictly decides whether to `auto` draft a reply or `escalate` to a human based on severity.
2. **The Drafter:** For `auto` queries, drafts a helpful, empathetic, sub-280-character reply mirroring historical brand tone.

---

## 📊 2. Results vs Baselines

Our headline metrics from the evaluation harness (run on a sampled 200-item Golden Set):
* **Helpfulness Score:** 4.21 / 5.0
* **Brand Tone Score:** 4.65 / 5.0
* **Escalation Rate:** 12.5%

**Baselines Comparison:**
1. **Trivial Baseline (Static Link):** "Thanks for reaching out! Check out https://support.apple.com for help."
   * *Comparison:* Our AI system drastically outperforms this by addressing the specific user problem (e.g., forcing a restart for a black screen) rather than blindly redirecting.
2. **Simple Baseline (Zero-shot unprompted LLM):** Passing the tweet to an LLM without brand context or escalation rules.
   * *Comparison:* A zero-shot baseline often writes paragraphs that are too long for Twitter and attempts to solve dangerous issues (like hacked accounts) instead of safely escalating them. Our pipeline routes securely.

---

## ⚖️ 3. Evaluation Harness & Human-Judge Agreement

We use an LLM-as-a-judge (`evaluator.py`) to grade the drafted replies against the human ground truth on Helpfulness and Brand Tone (1-5 scale).

**Evidence of Human Agreement:** 
To validate the judge, I randomly sampled 10 AI-drafted replies and blindly graded them myself (Human Score). I then compared my scores to the LLM Judge scores. 
* **Exact Match Rate:** 70%
* **Within 1-Point Margin:** 100%

*Conclusion:* The LLM judge is highly correlated with human QA standards and can be trusted for automated evaluation.

---

## ⚠️ 4. Failure Analysis (Top 5 Modes)

Through manual review of the `evaluator.py` outputs, I identified 5 distinct failure modes where the pipeline underperforms the human baseline:

1. **Context Hallucination (Dead Links):** The Drafter occasionally confidently fabricates URL slugs (e.g., `http://apple.co/black-screen-fix`) instead of routing to the general support portal.
2. **Sarcasm / Tone Deafness:** When a user makes a sarcastic joke ("My iPhone is a brilliant $1000 paperweight"), the classifier misses the anger, flags it as a standard technical issue, and drafts a cheerful response, exacerbating the customer's frustration.
3. **Over-promising Resolutions:** For hardware issues (like a shattered screen), the AI sometimes says "We can fix that right away!"—setting incorrect expectations for what is actually a paid, mail-in repair process.
4. **Redundant Verification Requests:** If a customer includes their software version in the initial tweet ("iOS 17.2 battery drain"), the AI drafter sometimes still rigidly asks "What iOS version are you running?", appearing robotic.
5. **Dropped Secondary Intents:** For multi-intent tweets ("My screen is cracked and your store manager was rude"), the classifier picks the primary technical intent (`repair_and_service`) and auto-handles it, completely dropping the complaint escalation regarding the employee.

---

## 📉 5. What is misleading about my headline number? (Mandatory)

While the Helpfulness score is high (4.21/5.0), **it is highly misleading because the judge is the same foundational model family as the drafter.** LLMs suffer from "self-preference bias," where they grade their own generated styles much higher than human styles. 

Additionally, our Golden Set was randomly sampled, meaning it is heavily skewed toward simple, common questions (like password resets) where the LLM excels, effectively masking its higher failure rate on complex edge cases.

---

## 🔮 6. What I'd do next with one more week

1. **Implement RAG:** Index official Apple Support articles so the drafting agent can retrieve and cite specific, up-to-date documentation links, solving the Context Hallucination failure mode.
2. **Train a smaller classifier:** Replace the expensive LLM API for intent classification with a fine-tuned lightweight model (like DistilBERT) to drastically reduce latency and cost.
3. **Human-in-the-loop Evaluation:** Conduct a blind A/B test with real humans grading the AI vs. the actual Apple Support agent to calculate a true Elo rating, bypassing LLM judge bias.

---

## 📝 7. Decision Log (10 Non-Obvious Decisions)

1. **Brand Choice (`@AppleSupport`):** Picked because they have the highest volume in the Kaggle dataset and deal with clear, objective technical intents.
2. **Golden Set Size (200):** 200 provides statistical significance without hitting free-tier API rate limits too aggressively during the LLM-as-a-judge evaluation.
3. **Pipeline Modularity:** Separated Classification/Routing from Drafting. This allows us to escalate *before* wasting tokens and latency drafting a reply we won't use.
4. **Structured JSON Output:** Used Pydantic schemas in `pipeline.py` to force the Gemini API to output perfectly formatted JSON, preventing downstream parsing errors.
5. **Few-Shot Prompting:** Upgraded from zero-shot to few-shot prompting for the drafter to explicitly train the model on Apple's historical response tone (which is short and directs to DMs).
6. **Exponential Backoff:** Implemented the `tenacity` library to automatically retry API calls if they hit a `429 RESOURCE_EXHAUSTED` rate limit, mirroring production SWE practices.
7. **Strict Temperature Controls:** Set `temperature=0.0` for the Router (requiring deterministic, logical routing) but `temperature=0.3` for the Drafter (allowing slightly more natural language generation).
8. **Automated Testing:** Added a `pytest` suite that uses `unittest.mock` to mock the Gemini API, ensuring the pipeline's structure can be tested instantly in CI/CD without burning API credits.
9. **Industry Standard Tooling:** Included a `Makefile`, formatted the codebase with `black`, and added strict type checking with `mypy` to ensure enterprise-grade code quality.
10. **Evaluating Tone vs Helpfulness:** Separated the LLM judge's rubric into two distinct scores. An AI reply can be technically helpful but overly robotic in tone, so measuring both is essential for brand safety.
