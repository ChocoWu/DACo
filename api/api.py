from openai import OpenAI
import os
import base64
import json  
import time  
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff



generation_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")    # e.g. http://127.0.0.1:8000/v1

if generation_key is not None:
    client = OpenAI(
        api_key=generation_key,
    )
elif base_url is not None:      # call local model
    client = OpenAI(
        api_key="xxx",
        base_url=base_url
    )
else:
    raise ValueError("Neither API key not base url is found. Please set the API_KEY or BASE_URL environment variable.")

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def completion_with_backoff(**kwargs):
    return client.chat.completions.create(**kwargs)


def call_2D_llm(system, prompt, image_dict, model="gpt-4o-2024-11-20", max_tokens=1000, out_dir=None, instr_id=None):
    user_content = []

    # prepare user messages
    for idx, image in image_dict.items():
        if image is not None:
            user_content.append(
                {
                    "type": "text",
                    "text": f"Image: {idx}:"
                },
            )
            with open(image, "rb") as image_file:
                image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

            image_message = {
                     "type": "image_url",
                     "image_url": {
                         "url": f"data:image/jpeg;base64,{image_base64}",
                         "detail": "low"
                     }
                 }
            user_content.append(image_message)

    user_content.append(
        {
            "type": "text",
            "text": prompt
        }
    )

    messages = [
        {"role": "system",
         "content": system
        },
        {"role": "user",
         "content": user_content
        }
    ]

    start_time = time.time()
    
    chat_message = completion_with_backoff(model=model, messages=messages, temperature=0, max_tokens=max_tokens, seed=42)
    answer = chat_message.choices[0].message.content
    
    end_time = time.time()
    latency = end_time - start_time 

    # ------------------ calculate token usage ------------------
    if chat_message.usage:
        usage_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": model,
            "prompt_tokens": chat_message.usage.prompt_tokens,
            "completion_tokens": chat_message.usage.completion_tokens,
            "total_tokens": chat_message.usage.total_tokens,
            "latency_seconds": round(latency, 3),   
        }

        if out_dir and instr_id:
            try:
                os.makedirs(out_dir, exist_ok=True)
                log_file = os.path.join(out_dir, f"logs/api_usage_log_{instr_id}.jsonl")
                
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(usage_data, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"Error logging API usage: {e}")

    return answer