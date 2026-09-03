import httpx, os, time, base64, sys
from pathlib import Path
KEY=os.environ['GEMINI_API_KEY']
img=Path(sys.argv[1]); b64=base64.b64encode(img.read_bytes()).decode()
body={"contents":[{"parts":[{"inline_data":{"mime_type":"image/png","data":b64}},{"text":"what is this? one line"}]}]}
for m in ["gemma-4-26b-a4b-it","gemma-4-31b-it"]:
    t=time.time()
    try:
        r=httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",params={"key":KEY},json=body,timeout=60)
        print(m, r.status_code, f"{time.time()-t:.1f}s", f"payload={len(b64)//1024}KB")
    except Exception as e:
        print(m, "ERR", type(e).__name__, repr(e)[:200], "cause:", repr(getattr(e,'__cause__',None))[:200])
