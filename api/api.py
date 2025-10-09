from openai import OpenAI
import os
import base64
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff


generation_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")

if generation_key is not None:
    client = OpenAI(
        api_key=generation_key,
    )
elif base_url is not None:      # call local model
    client = OpenAI(
        api_key="xxx",
        base_url=base_url     # call qwen2.5-vl
    )
else:
    raise ValueError("Neither API key not base url is found. Please set the API_KEY or BASE_URL environment variable.")

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def completion_with_backoff(**kwargs):
    return client.chat.completions.create(**kwargs)


def call_2D_llm(system, prompt, image_dict, model="gpt-4o-2024-11-20", max_tokens=1000):
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

    chat_message = completion_with_backoff(model=model, messages=messages, temperature=0, max_tokens=max_tokens, seed=42)

    answer = chat_message.choices[0].message.content

    return answer