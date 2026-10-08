"""Check that the OpenAI key in .env works. Free: only lists available models, no text generation."""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
key = os.environ.get("OPENAI_API_KEY", "")
if not key:
    raise SystemExit("No key found. Paste it after OPENAI_API_KEY= in the .env file and save.")
print(f"Key loaded (starts with {key[:7]}..., {len(key)} characters)")
models = sorted(m.id for m in OpenAI().models.list())
print(f"Key works. {len(models)} models available.")
print("Small models:", [m for m in models if "luna" in m or "mini" in m or "nano" in m][:15])
