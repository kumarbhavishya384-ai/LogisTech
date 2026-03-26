import os
import requests
import json
import time

# Host of the environment
BASE_URL = os.getenv("ENV_URL", "http://localhost:8000")

def run_task(task_id: str):
    print(f"--- Running Task: {task_id} ---")
    
    # Reset environment
    response = requests.post(f"{BASE_URL}/reset", params={"task_id": task_id})
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
        # Simple Logic-based Agent for Baseline Reproducibility
        # (Could be replaced with an LLM call using openai library)
        
        action = {"action_type": "NOTIFY", "params": {"message": "monitoring"}}
        
        if task_id == "easy" and steps == 0:
            # Transfer stock from DE to UK
            action = {"action_type": "TRANSFER", "params": {"sku": "SKU_IPHONE", "origin": "WH_DE", "destination": "WH_UK", "quantity": 100}}
        elif task_id == "medium" and steps == 0:
            # Reroute S1 to AIR
            action = {"action_type": "REROUTE", "params": {"id": "S1", "mode": "AIR"}}
        elif task_id == "hard":
            # Reorder all items that are low in stock
            for wh in observation["warehouses"]:
                if wh["id"] == "WH_SH": continue
                for sku, qty in wh["inventory"].items():
                    if qty < 50:
                        action = {"action_type": "TRANSFER", "params": {"sku": sku, "origin": "WH_SH", "destination": wh["id"], "quantity": 50}}
                        break
        
        # Take step
        step_response = requests.post(
            f"{BASE_URL}/step", 
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
        
    # Get Final Grade
    grader_response = requests.get(f"{BASE_URL}/grader", params={"session_id": session_id})
    score = grader_response.json()["score"]
    print(f"Task {task_id} Finished. Score: {score}")
    return score

if __name__ == "__main__":
    results = {}
    for task_id in ["easy", "medium", "hard"]:
        results[task_id] = run_task(task_id)
        
    print("\n--- FINAL BASELINE SCORES ---")
    print(json.dumps(results, indent=2))
