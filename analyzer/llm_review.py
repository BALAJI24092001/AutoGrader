"""Readability analyzer: ask an LLM (on Groq) to rate how readable the code is.

We send the student's code with a fixed prompt to Groq's OpenAI-compatible
chat API (https://api.groq.com/openai/v1/chat/completions) and ask for JSON like
    {"score": 7, "reasons": ["clear names", "no comments"]}
score = that number / 10.

The API key is read from the GROQ_API_KEY environment variable. It is never
stored in a file in the repo, so it cannot be committed by mistake.

Reproducible grades:
  - temperature 0 and a fixed seed (both from the rules) make the model
    give the same answer to the same question as far as Groq allows;
  - every answer is also saved in cache/llm/<hash>.json, where the hash is
    made from the code, the prompt, the model, the temperature and the seed.
    On a rerun we read the saved answer instead of asking again, so the
    score cannot change even if the model would answer slightly differently.
    cache/llm/ is committed, so anyone who clones the repo gets the same
    readability scores for the sample submissions without needing a key.

If an answer is not in the cache and there is no key, or Groq refuses the
request, we stop the whole grading run with a message that says how to fix it.
Carrying on would give readability 0 and a grade that is wrong without anyone
noticing.
"""

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
CACHE_DIR = os.path.join("cache", "llm")
TIMEOUT_S = 60

PROMPT = """You are grading the readability of a student's C program.
Judge only readability: clear names, helpful comments, consistent indentation
and spacing, short focused functions. Do not judge correctness or speed.
Give a score from 0 (unreadable) to 10 (very clear).
Answer with JSON only, in exactly this form, with at most 3 short reasons:
{"score": <integer 0-10>, "reasons": ["<reason>", "<reason>"]}

Program:
```c
CODE
```
"""


def ask_groq(model, prompt, temperature, seed):
    """Send one prompt to Groq and return the text of its answer."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        sys.exit("GROQ_API_KEY is not set, and this answer is not in cache/llm/.\n"
                 "Get a key at https://console.groq.com/keys and run: "
                 "export GROQ_API_KEY=<your key>")

    request_body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "seed": seed,
        "response_format": {"type": "json_object"},  # the answer must be valid JSON
    }
    request = urllib.request.Request(
        GROQ_URL, data=json.dumps(request_body).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}",
                 # Groq's firewall rejects Python's default User-Agent.
                 "User-Agent": "autograder/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return json.loads(response.read())["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as error:
        # 401 = wrong key, 404 = unknown model, 429 = too many requests.
        details = error.read().decode(errors="replace")
        sys.exit(f"Groq error {error.code} for model {model!r}: {details}")
    except urllib.error.URLError as error:
        sys.exit(f"Could not reach Groq at {GROQ_URL}: {error.reason}")
    except OSError as error:
        # e.g. TimeoutError when Groq connects but does not answer within TIMEOUT_S.
        sys.exit(f"Groq did not answer in time ({TIMEOUT_S} s): {error}")


def analyze(source_path, first_pass, params, rules):
    model = params["model"]
    temperature = params.get("temperature", 0)
    seed = params.get("seed", 42)

    with open(source_path, errors="replace") as f:
        code = f.read()
    # replace() rather than format(): the JSON example in PROMPT has { } in it.
    prompt = PROMPT.replace("CODE", code)

    key = json.dumps([code, PROMPT, model, temperature, seed])
    cache_path = os.path.join(CACHE_DIR, hashlib.sha256(key.encode()).hexdigest() + ".json")

    if os.path.exists(cache_path):
        with open(cache_path) as f:
            raw = f.read()
    else:
        raw = ask_groq(model, prompt, temperature, seed)

    # Check the answer before saving it, so a bad answer is never cached.
    answer = json.loads(raw)
    value = answer["score"]
    if not isinstance(value, (int, float)) or not 0 <= value <= 10:
        raise ValueError(f"model gave score {value!r}, expected a number from 0 to 10")
    # The model sometimes packs all reasons into one string, joined by '","'.
    reasons = []
    for reason in answer.get("reasons", []):
        reasons += str(reason).split('","')
    reasons = reasons[:3]

    if not os.path.exists(cache_path):
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_path, "w") as f:
            f.write(raw)

    return {
        "score": value / 10,
        "evidence": {"model": model, "temperature": temperature, "seed": seed,
                     "raw_response": raw, "cache_file": cache_path},
        "feedback": f"{value}/10 from {model}: " + ("; ".join(reasons) or "no reasons given"),
    }
