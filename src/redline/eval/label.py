"""A local page for labelling my own sentences: select text, press a number key, Enter to save.

Blind: redline's own flags are never shown, so the labels can't be nudged toward what it already finds.
"""

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from redline.eval.data import PERSONAL
from redline.eval.personal import load_jsonl

GOLD = PERSONAL / "style_gold.jsonl"
CANDIDATES = PERSONAL / "candidates.jsonl"
LABELS = {"1": "filler", "2": "ai-tell", "3": "em-dash", "4": "other"}


def pending(candidates: list[dict], labelled: list[dict]) -> list[str]:
    done = {r["text"] for r in labelled}
    return [c["text"] for c in candidates if c["text"] not in done]


def save_label(path: Path, text: str, spans: list) -> None:
    clean = [[int(s), int(e), str(lab)] for s, e, lab in spans if 0 <= int(s) < int(e) <= len(text)]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"text": text, "spans": clean}, ensure_ascii=False) + "\n")


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>redline labels</title>
<style>
:root{--bg:#f7f6f2;--fg:#1d1d1b;--mut:#6b6a66;--hl:#ffd8a8;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ecebe6;--mut:#9a9893;--hl:#7a4a12;--card:#22221f}}
body{background:var(--bg);color:var(--fg);font:18px/1.6 system-ui,sans-serif;max-width:760px;margin:40px auto;padding:0 16px}
#s{background:var(--card);padding:24px;border-radius:10px;font-size:22px;white-space:pre-wrap}
mark{background:var(--hl);color:inherit}
.k{color:var(--mut);font-size:15px}
</style></head><body>
<p class="k" id="left"></p>
<div id="s"></div>
<p id="spans" class="k"></p>
<p class="k">Select words you would want flagged, then press <b>1</b> filler, <b>2</b> AI-sounding,
<b>3</b> em-dash, <b>4</b> other. <b>Backspace</b> clears. <b>Enter</b> saves (nothing marked = clean sentence).</p>
<script>
let text="", spans=[];
const LABELS=%LABELS%;
function esc(t){return t.replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]))}
function render(){
  let out="",pos=0;
  [...spans].sort((a,b)=>a[0]-b[0]).forEach(([s,e])=>{out+=esc(text.slice(pos,s))+"<mark>"+esc(text.slice(s,e))+"</mark>";pos=e});
  document.getElementById("s").innerHTML=out+esc(text.slice(pos));
  document.getElementById("spans").textContent=spans.map(([s,e,l])=>l+": "+text.slice(s,e)).join("  |  ");
}
function offsetIn(node,off){
  const root=document.getElementById("s");let n=0;
  const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  while(w.nextNode()){if(w.currentNode===node)return n+off;n+=w.currentNode.length}
  return -1;
}
async function next(){
  const r=await (await fetch("/next")).json();
  document.getElementById("left").textContent=r.left+" left";
  text=r.text||"All done. You can close this tab.";spans=[];render();
}
document.addEventListener("keydown",async ev=>{
  if(LABELS[ev.key]){
    const sel=getSelection();if(!sel.rangeCount)return;
    const rg=sel.getRangeAt(0);
    let a=offsetIn(rg.startContainer,rg.startOffset),b=offsetIn(rg.endContainer,rg.endOffset);
    if(a<0||b<=a)return;
    spans.push([a,b,LABELS[ev.key]]);sel.removeAllRanges();render();
  }else if(ev.key==="Backspace"){spans=[];render();ev.preventDefault()}
  else if(ev.key==="Enter"&&text){
    await fetch("/label",{method:"POST",body:JSON.stringify({text,spans})});next();
  }
});
next();
</script></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, ctype: str):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/next":
            left = pending(load_jsonl(CANDIDATES), load_jsonl(GOLD))
            self._send(json.dumps({"text": left[0] if left else None, "left": len(left)}).encode(), "application/json")
        else:
            self._send(PAGE.replace("%LABELS%", json.dumps(LABELS)).encode(), "text/html; charset=utf-8")

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        save_label(GOLD, data["text"], data["spans"])
        self._send(b"{}", "application/json")

    def log_message(self, *args):
        pass


def serve(port: int = 8765) -> None:
    if not CANDIDATES.exists():
        print("No candidates yet. Run `redline build-sets` first.")
        return
    srv = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"Labelling at {url}  (Ctrl+C to stop; progress is saved after every sentence)")
    webbrowser.open(url)
    srv.serve_forever()
