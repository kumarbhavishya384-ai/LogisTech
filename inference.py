import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Mandatory env vars ────────────────────────────────────────────────────────
# API_BASE_URL : injected by the evaluation platform (LiteLLM proxy endpoint)
# API_KEY      : injected by the evaluation platform (LiteLLM proxy key)
# MODEL_NAME   : model identifier for inference
# HF_TOKEN     : Hugging Face / platform token (used for Space auth if needed)
# ENV_URL      : base URL of the OpenEnv FastAPI server
# ─────────────────────────────────────────────────────────────────────────────
API_BASE_URL = os.environ["API_BASE_URL"]          # must come from environment
API_KEY      = os.environ["API_KEY"]               # must come from environment
MODEL_NAME   = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN     = os.getenv("HF_TOKEN", "")
ENV_URL      = os.getenv("ENV_URL", "http://localhost:7860")

# Always initialise with the injected LiteLLM proxy credentials
client = OpenAI(
    api_key=API_KEY,
    base_url=API_BASE_URL,
)


def get_llm_action(observation: dict, task_id: str) -> dict:
    """Call the LLM via the injected API_BASE_URL proxy to choose an action."""
    prompt = (
        "You are a logistics AI agent managing a global supply chain.\n"
        f"Task: {task_id}\n"
        f"Current Observation:\n{json.dumps(observation, indent=2)}\n\n"
        "Choose ONE action from: TRANSFER, REORDER, REROUTE, NOTIFY, PRIORITIZE.\n"
        "Respond ONLY with valid JSON, for example:\n"
        '{"action_type": "TRANSFER", "params": {"sku": "SKU_IPHONE", '
        '"origin": "WH_DE", "destination": "WH_UK", "quantity": 100}}'
    )
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
        )
        content = response.choices[0].message.content.strip()
        start = content.find("{")
        end   = content.rfind("}") + 1
        return json.loads(content[start:end])
    except Exception as exc:
        print(f"[WARN] LLM call failed: {exc}. Using fallback NOTIFY action.")
        return {"action_type": "NOTIFY", "params": {"message": "monitoring"}}


def run_task(task_id: str) -> float:
    # ── [START] ───────────────────────────────────────────────────────────────
    print(json.dumps({
        "event":   "[START]",
        "task_id": task_id,
        "model":   MODEL_NAME,
        "env_url": ENV_URL,
    }))

    # Reset the environment for this task
    reset_resp = requests.post(f"{ENV_URL}/reset", params={"task_id": task_id})
    if reset_resp.status_code != 200:
        print(f"[ERROR] Failed to reset task '{task_id}': {reset_resp.text}")
        return 0.0

    data       = reset_resp.json()
    session_id = data["session_id"]
    observation = data["observation"]

    done      = False
    step_num  = 0
    max_steps = 30

    while not done and step_num < max_steps:
        action = get_llm_action(observation, task_id)

        step_resp = requests.post(
            f"{ENV_URL}/step",
            params={"session_id": session_id},
            json=action,
        )

        if step_resp.status_code != 200:
            print(f"[ERROR] Step {step_num} failed: {step_resp.text}")
            break

        step_data   = step_resp.json()
        reward_val  = step_data.get("reward", {})
        observation = step_data["observation"]
        done        = step_data["done"]

        # ── [STEP] ────────────────────────────────────────────────────────────
        print(json.dumps({
            "event":      "[STEP]",
            "task_id":    task_id,
            "step":       step_num,
            "action":     action,
            "reward":     reward_val,
            "done":       done,
        }))

        step_num += 1

    # Final grade
    grader_resp = requests.get(f"{ENV_URL}/grader", params={"session_id": session_id})
    score = grader_resp.json().get("score", 0.0)

    # ── [END] ─────────────────────────────────────────────────────────────────
    print(json.dumps({
        "event":      "[END]",
        "task_id":    task_id,
        "steps_used": step_num,
        "score":      score,
    }))

    return score


if __name__ == "__main__":
    results = {}
    for task_id in ["easy", "medium", "hard"]:
        results[task_id] = run_task(task_id)

    print("\n--- FINAL BASELINE SCORES ---")
    print(json.dumps(results, indent=2))
