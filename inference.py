import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=API_BASE_URL if "openai" not in API_BASE_URL else None
)

ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")


def get_llm_action(observation: dict, task_id: str) -> dict:
    """Use OpenAI client to decide the next action based on observation."""
    prompt = f"""You are a logistics AI agent managing a supply chain.
Task: {task_id}
Current Observation: {json.dumps(observation, indent=2)}

Choose ONE action from: TRANSFER, REORDER, REROUTE, NOTIFY, PRIORITIZE.
Respond ONLY with valid JSON like:
{{"action_type": "TRANSFER", "params": {{"sku": "SKU_IPHONE", "origin": "WH_DE", "destination": "WH_UK", "quantity": 100}}}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200
        )
        content = response.choices[0].message.content.strip()
        # Extract JSON from response
        start = content.find("{")
        end = content.rfind("}") + 1
        return json.loads(content[start:end])
    except Exception as e:
        print(f"LLM call failed: {e}, using fallback NOTIFY action")
        return {"action_type": "NOTIFY", "params": {"message": "monitoring"}}


def run_task(task_id: str) -> float:
    print(f"--- Running Task: {task_id} ---")

    response = requests.post(f"{ENV_URL}/reset", params={"task_id": task_id})
    if response.status_code != 200:
        print(f"Failed to reset: {response.text}")
        return 0.0

    data = response.json()
    session_id = data["session_id"]
    observation = data["observation"]

    done = False
    steps = 0
    max_steps = 30

    while not done and steps < max_steps:
        action = get_llm_action(observation, task_id)

        step_response = requests.post(
            f"{ENV_URL}/step",
            params={"session_id": session_id},
            json=action
        )

        if step_response.status_code != 200:
            print(f"Step failed: {step_response.text}")
            break

        step_data = step_response.json()
        observation = step_data["observation"]
        done = step_data["done"]
        steps += 1

    grader_response = requests.get(f"{ENV_URL}/grader", params={"session_id": session_id})
    score = grader_response.json()["score"]
    print(f"Task {task_id} Finished. Score: {score}")
    return score


if __name__ == "__main__":
    results = {}
    for task_id in ["easy", "medium", "hard"]:
        results[task_id] = run_task(task_id)

    print("\n--- FINAL BASELINE SCORES ---")
    print(json.dumps(results, indent=2))
