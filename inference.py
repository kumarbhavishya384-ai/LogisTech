from scripts.baseline_inference import run_task
import json

if __name__ == "__main__":
    results = {}
    for task_id in ["easy", "medium", "hard"]:
        results[task_id] = run_task(task_id)

    print("\n--- FINAL BASELINE SCORES ---")
    print(json.dumps(results, indent=2))
