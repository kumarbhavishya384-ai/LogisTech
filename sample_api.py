import json
from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    data = await request.json()
    print(f"[Sample API] Received chat completion request for model: {data.get('model')}")
    
    # Return a mocked action that logistech OpenEnv understands
    mock_action = {
        "action_type": "NOTIFY",
        "params": {"message": "Mock Local Action without credentials"}
    }
    
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": 1712470000,
        "model": data.get("model", "mock-model"),
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(mock_action)
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
    }

if __name__ == "__main__":
    print("Starting Mock LiteLLM Proxy API on http://localhost:8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
