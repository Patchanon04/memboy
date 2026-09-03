import asyncio, httpx, os, time, base64, sys
from pathlib import Path
KEY=os.environ['GEMINI_API_KEY']; img=Path(sys.argv[1]); b64=base64.b64encode(img.read_bytes()).decode()
body={"contents":[{"parts":[{"inline_data":{"mime_type":"image/png","data":b64}},{"text":"one line: what is this?"}]}]}
async def main():
    for m in ["gemma-4-26b-a4b-it"]:
        for label, kw in (("async default", {}), ("async http1 no-env", {"trust_env": False})):
            t=time.time()
            try:
                async with httpx.AsyncClient(timeout=70, **kw) as c:
                    r=await c.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",params={"key":KEY},json=body)
                print(label, m, r.status_code, f"{time.time()-t:.1f}s")
            except Exception as e:
                print(label, m, "ERR", type(e).__name__, repr(e)[:150])
    t=time.time(); r=httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemma-4-26b-a4b-it:generateContent",params={"key":KEY},json=body,timeout=70); print("sync", r.status_code, f"{time.time()-t:.1f}s")
asyncio.run(main())
