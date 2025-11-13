from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import httpx, os, json
from toon import encode
import tiktoken
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="TOONWare", version="0.1.0")

TARGET = os.getenv("TOONWARE_TARGET", "https://api.openai.com")
API_KEY = os.getenv("TOONWARE_API_KEY", "")
TIMEOUT = float(os.getenv("TOONWARE_TIMEOUT", "60"))
MIN_BYTES = int(os.getenv("TOONWARE_MIN_BYTES", "512"))

REQS = Counter("toonware_requests_total", "Total requests proxied")
OPTIMIZED = Counter("toonware_optimized_total", "Requests where TOON compression applied")
LAST_SAVING = Gauge("toonware_last_saving_percent", "Token savings on last request")

ENC = tiktoken.encoding_for_model("gpt-4o")

def count_tokens(data: str):
    return len(ENC.encode(data))

def find_json_blocks(text: str):
    out = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]
        if ch in "{[":
            for j in range(i + 1, n + 1):
                snippet = text[i:j]
                try:
                    obj = json.loads(snippet)
                    toon_str = encode(obj)
                    out.append(toon_str)
                    i = j
                    break
                except json.JSONDecodeError:
                    continue
            else:
                out.append(ch)
                i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)

def compress_json_blocks(body: dict):
    changed = False

    if not isinstance(body, dict):
        return body, changed

    if "messages" in body:
        # iterate thru the messages in the request body
        for msg in body["messages"]:
            content = msg.get("content")

            # if the content is a string and longer than the minimum bytes, compress it
            if isinstance(content, str) and len(content) > MIN_BYTES:
                new_text = find_json_blocks(content)
                if new_text != content:
                    msg["content"] = new_text
                    changed = True
            # if the content is a dictionary or list, compress it
            elif isinstance(content, (dict, list)):
                toon_str = encode(content)
                msg["content"] = toon_str
                changed = True
    return body, changed

@app.post("/{path:path}")
async def proxy(path: str, req: Request):
    REQS.inc() # increment the request counter 

    try:
        body = await req.json()
    except Exception:
        return Response("Invalid JSON", status_code=400)

    before = count_tokens(json.dumps(body)) # count the tokens in the request body
    new_body, changed = compress_json_blocks(body) # compress the JSON blocks in the request body
    after = count_tokens(json.dumps(new_body)) # count the tokens in the new request body
    savings = round(100 * (1 - after / before), 2) if before > 0 else 0 # calculate the savings

    if changed:
        OPTIMIZED.inc() # increment the optimized counter
        LAST_SAVING.set(savings) # set the last saving percentage

    headers = {k: v for k, v in req.headers.items() if k.lower() not in ("host", "content-length")} # remove the host and content-length headers
    
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{TARGET}/{path}", headers=headers, json=new_body)

    try:
        data = r.json()
        data["_toonware"] = {
            "optimized": changed,
            "tokens_before": before,
            "tokens_after": after,
            "saving_percent": savings,
        }
        return JSONResponse(
            content=data,
            status_code=r.status_code,
            headers={
                "X-TOON-Optimized": str(int(changed)),
                "X-TOON-Saving-Percent": str(savings),
            },
        )
    except Exception:
        return Response(content=r.content, status_code=r.status_code)

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
