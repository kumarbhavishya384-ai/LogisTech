"""
LogisTech-OpenEnv — Inference Script
======================================
Follows the mandatory format defined in the OpenEnv Sample Inference Script.

STDOUT FORMAT (exact):
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...,rn>

ENV VARS (injected by evaluation platform):
    API_BASE_URL   — LiteLLM proxy endpoint
    API_KEY        — LiteLLM proxy key  (fallback: HF_TOKEN)
    HF_TOKEN       — Hugging Face token (also accepted as API key)
    MODEL_NAME     — Model identifier for inference
    ENV_URL        — Base URL of the LogisTech OpenEnv server
"""

import json
import os
import textwrap
from typing import List, Optional

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Make sure os.environ has the keys so it doesn't crash locally
if not os.environ.get("API_BASE_URL"):
    os.environ["API_BASE_URL"] = "http://localhost:8000/v1"
if not os.environ.get("API_KEY"):
    os.environ["API_KEY"] = "dummy-key"

# EXACT SYNTAX REQUIRED BY VALIDATOR
client = OpenAI(
    base_url=os.environ["API_BASE_URL"],
    api_key=os.environ["API_KEY"],
)

MODEL_NAME   = os.getenv("MODEL_NAME", "").strip() or "Qwen/Qwen2.5-72B-Instruct"
ENV_URL      = os.getenv("ENV_URL", "http://localhost:7860").strip()

BENCHMARK    = "logistech-openenv"
MAX_STEPS    = 30
SUCCESS_THRESHOLD = 0.5   # score >= this → success=true



# ── Mandatory stdout helpers ───────────────────────────────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val  = str(done).lower()
    # action_str must be a single token (no spaces/newlines)
    action_safe = action.replace("\n", " ").replace("\r", "")
    print(
        f"[STEP] step={step} action={action_safe!r} "
        f"reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ── LLM action selection ───────────────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert logistics AI agent managing a global supply chain.
    You will receive the current environment observation in JSON and must
    choose exactly ONE action from: TRANSFER, REORDER, REROUTE, NOTIFY, PRIORITIZE.
    Respond ONLY with a single valid JSON object — no explanation, no markdown:
    {"action_type": "<TYPE>", "params": {<key>: <value>, ...}}

    Action schemas:
    - TRANSFER:   {"sku": str, "origin": str, "destination": str, "quantity": int}
    - REORDER:    {"sku": str, "warehouse_id": str, "quantity": int}
    - REROUTE:    {"id": str, "mode": "AIR"|"SEA"|"RAIL"|"TRUCK"}
    - NOTIFY:     {"message": str}
    - PRIORITIZE: {"order_id": str}
""")


def get_llm_action(observation: dict, task_id: str, step: int) -> dict:
    """Ask the LLM (via the injected proxy) for the next action."""
    user_prompt = (
        f"Task: {task_id}\n"
        f"Step: {step}\n"
        f"Observation:\n{json.dumps(observation, indent=2)}\n\n"
        "Choose the best single action as JSON."
    )
    try:
        global client
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=200,
        )
        content = resp.choices[0].message.content.strip()
        start = content.find("{")
        end   = content.rfind("}") + 1
        return json.loads(content[start:end])
    except Exception as exc:
        return {"action_type": "NOTIFY", "params": {"message": f"fallback: {exc}"}}


# ── Episode runner ─────────────────────────────────────────────────────────────

def run_task(task_id: str) -> float:
    """Run one full episode and return score in [0.0, 1.0]."""
    rewards: List[float] = []
    steps_taken = 0
    score  = 0.0
    success = False

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        # ── Reset ────────────────────────────────────────────────────────────
        reset_resp = requests.post(f"{ENV_URL}/reset", params={"task_id": task_id}, timeout=30)
        if reset_resp.status_code != 200:
            print(f"[DEBUG] /reset failed ({reset_resp.status_code}): {reset_resp.text}", flush=True)
            return 0.0

        data        = reset_resp.json()
        session_id  = data["session_id"]
        observation = data["observation"]

        done = False

        # ── Agentic loop ──────────────────────────────────────────────────────
        for step_num in range(1, MAX_STEPS + 1):
            if done:
                break

            action = get_llm_action(observation, task_id, step_num)

            step_resp = requests.post(
                f"{ENV_URL}/step",
                params={"session_id": session_id},
                json=action,
                timeout=30,
            )

            error: Optional[str] = None
            if step_resp.status_code != 200:
                error = step_resp.text[:120]
                step_raw_reward = 0.0
                done = False
            else:
                step_data   = step_resp.json()
                observation = step_data["observation"]
                done        = step_data["done"]
                # Reward model: {"total": float, "components": {...}}
                reward_obj  = step_data.get("reward", {})
                if isinstance(reward_obj, dict):
                    step_raw_reward = float(reward_obj.get("total", 0.0))
                else:
                    step_raw_reward = 0.0

            rewards.append(step_raw_reward)
            steps_taken = step_num

            action_str = f"{action.get('action_type')}({json.dumps(action.get('params', {}))})"
            log_step(step=step_num, action=action_str,
                     reward=step_raw_reward, done=done, error=error)

        # ── Grade ─────────────────────────────────────────────────────────────
        grader_resp = requests.get(
            f"{ENV_URL}/grader", params={"session_id": session_id}, timeout=30
        )
        raw_score = grader_resp.json().get("score", 0.0)
        score   = float(min(max(raw_score, 0.01), 0.99))   # clamp strictly to (0, 1)
        success = score >= SUCCESS_THRESHOLD

    except Exception as exc:
        print(f"[DEBUG] Episode error for task '{task_id}': {exc}", flush=True)
        score   = 0.01
        success = False

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = {}
    for task_id in ["easy", "medium", "hard"]:
        results[task_id] = run_task(task_id)

    print("\n--- FINAL BASELINE SCORES ---")
    print(json.dumps(results, indent=2))
