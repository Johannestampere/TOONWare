<h1 align="center">TOONWare</h1>

<p align="center">A lightweight middleware that converts JSON to TOON to reduce LLM token usage</p>

## What is TOON?

**TOON (Token-Oriented Object Notation)** is a compact data format designed to express JSON structures with significantly fewer tokens when processed by LLMs.
Compared to raw JSON, TOON:
- Removes redundant characters such as braces, quotes, and commas
- Uses concise structural patterns to represent objects and arrays
- Produces fewer tokens for the same semantic information
- Is friendly for LLM parsing and reversible back into JSON

TOON is particularly effective for large, deeply-nested objects or repeated structures where JSON's syntax overhead becomes costly.

<p align="center">
  <img src="https://miro.medium.com/v2/da:true/resize:fit:1200/0*h-jO934tgAO-k5xs" width="600" />
</p>

## Why TOONWare?

Large JSON blocks can inflate LLM prompts by thousands of tokens due to quotes, braces, and formatting overhead. TOONWare automatically compresses those blocks into the TOON format, reducing token usage without requiring any code changes to your application.

## How it works

TOONWare sits between your app and your LLM provider (currently only OpenAI) as a drop-in middleware. You keep calling `/v1/chat/completions` the same way - TOONWare just optimizes the request before it leaves your system.
1. Your app sends a normal OpenAI-style request to TOONWare.
2. TOONWare scans the message content for large JSON blocks.
3. When it finds one, it converts the block to TOON.
4. The optimized request is forwarded to your real LLM provider.
5. TOONWare returns the standard completion response back to you.
6. Prometheus metrics show how much you saved.

**The result**: smaller prompts, faster responses, and lower token usage, with zero changes to your application code.

## Where TOONWare fits in your stack

Use TOONWare as a drop-in replacement for OpenAI’s API endpoint.
Instead of sending requests to:

`https://api.openai.com/v1/chat/completions`

You send them to your local or hosted TOONWare container, for example:

`http://localhost:8000/v1/chat/completions`

TOONWare forwards the request to OpenAI, compressing any JSON along the way. No code changes are needed, just update the API base URL.

## Getting started

### Requirements
- Docker installed
- An OpenAI API key

### 1. Pull the container
```bash
docker pull ghcr.io/johannestampere/toonware:latest
```

### 2. Run the middleware locally

Expose it on port 8000 (or any port you choose):

```bash
docker run -p 8000:8000 \
  -e TOONWARE_API_KEY="YOUR_OPENAI_KEY" \
  -e TOONWARE_TARGET="https://api.openai.com" \
  -e TOONWARE_MIN_BYTES=256 \
  ghcr.io/johannestampere/toonware:latest
```

Environment variables:
- **TOONWARE_API_KEY** - The API key used for OpenAI calls.
- **TOONWARE_TARGET** - The upstream provider URL (defaults to https://api.openai.com).
- **TOONWARE_MIN_BYTES** - Minimum JSON size before TOON compression is attempted.

### 3. Call TOONWare just like the OpenAI API

Bash example:
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
        "model": "gpt-4o",
        "messages": [
          { "role": "user", "content": "Summarize this: {\"id\": 5, \"name\": \"Bob\"}" }
        ]
      }'
```

Python example:
```python
import requests

response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    json={
        "model": "gpt-4o",
        "messages": [
            {"role": "user", "content": "Summarize this: {\"id\":5,\"name\":\"Bob\"}"}
        ]
    }
)

print(response.json())
```

### 4. Check Prometheus metrics

```bash
curl http://localhost:8000/metrics
```

## Example

Let's test TOONWare on this large JSON example:

```json
{
  "id": 1248,
  "user": {
    "first_name": "Michael",
    "last_name": "Roberts",
    "email": "michael.roberts@example.com",
    "is_active": true,
    "roles": ["editor", "reviewer", "admin"]
  },
  "profile": {
    "age": 34,
    "location": {
      "city": "Seattle",
      "state": "WA",
      "country": "USA"
    },
    "preferences": {
      "theme": "dark",
      "language": "en",
      "notifications": {
        "email": true,
        "sms": false,
        "push": true
      }
    }
  },
  "security": {
    "mfa_enabled": true,
    "last_login": "2025-01-15T09:42:18Z",
    "backup_codes": [
      "XF29-AH12",
      "GH77-KL90",
      "PQ45-ZT22"
    ]
  },
  "projects": [
    {
      "id": 501,
      "name": "Market Trends Dashboard",
      "status": "active",
      "team": [
        {"id": 1, "name": "Michael Roberts", "hours": 120},
        {"id": 2, "name": "Sarah Bennett", "hours": 96},
        {"id": 3, "name": "Tom Mitchell", "hours": 87}
      ]
    },
    {
      "id": 502,
      "name": "Customer Insights API",
      "status": "maintenance",
      "settings": {
        "rate_limit_per_min": 1200,
        "cache_enabled": true,
        "region": "us-west-2"
      }
    }
  ],
  "billing": {
    "plan": "Business",
    "usage": {
      "requests_this_month": 98214,
      "requests_last_month": 77340,
      "cost_this_month": 148.92,
      "cost_last_month": 119.44
    },
    "payment_methods": [
      {"type": "credit_card", "last4": "8812", "brand": "Visa"},
      {"type": "bank_transfer", "bank": "Chase"}
    ]
  }
}
```

Results:

<img width="784" height="304" alt="Screenshot 2025-11-13 at 12 19 18" src="https://github.com/user-attachments/assets/dd27605c-ba76-48b5-8b0e-18e30b3b6216" />

## License

MIT License. Feel free to use, modify, and contribute.



