"""Systems compared in the grammar eval. Each returns, per input text, a list of flagged char spans."""

import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
JDK_DIR = Path.home() / ".cache" / "redline" / "jdk"


class RedlineGrammar:
    name = "redline"

    def __init__(self, model_id: str = "Unbabel/gec-t5_small"):
        from redline.grammar import GrammarChecker

        self.checker = GrammarChecker(model_id)
        if model_id != "Unbabel/gec-t5_small":
            self.name = f"redline[{model_id.split('/')[-1]}]"

    def spans(self, texts: list[str]) -> list[list[tuple[int, int]]]:
        # Eval texts are single sentences, so batch them straight through the model.
        fixed = self.checker.correct_batch(texts)
        from redline.grammar import diff_flags

        return [[(f.start, f.end) for f in diff_flags(t, c)] for t, c in zip(texts, fixed)]

    def close(self):
        pass


class Harper:
    name = "harper"

    def __init__(self):
        script = REPO / "src" / "redline" / "eval" / "harper_lint.mjs"
        if not (REPO / "node_modules" / "harper.js").exists():
            subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=REPO, check=True, shell=os.name == "nt")
        self.proc = subprocess.Popen(["node", str(script)], cwd=REPO, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, text=True, encoding="utf-8")

    def spans(self, texts):
        out = []
        for t in texts:
            self.proc.stdin.write(json.dumps(t) + "\n")
            self.proc.stdin.flush()
            out.append([tuple(s) for s in json.loads(self.proc.stdout.readline())])
        return out

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=30)


def _ensure_java() -> None:
    """Use system Java if present, else a JRE downloaded once into ~/.cache/redline/jdk."""
    from shutil import which

    if which("java"):
        return
    homes = sorted(JDK_DIR.glob("*")) if JDK_DIR.exists() else []
    if not homes:
        import jdk

        JDK_DIR.mkdir(parents=True, exist_ok=True)
        jdk.install("17", jre=True, path=str(JDK_DIR))
        homes = sorted(JDK_DIR.glob("*"))
    home = homes[-1]
    os.environ["JAVA_HOME"] = str(home)
    os.environ["PATH"] = str(home / "bin") + os.pathsep + os.environ["PATH"]


class LanguageToolLocal:
    name = "languagetool"

    def __init__(self, lang: str = "en-US"):
        _ensure_java()
        import language_tool_python

        self.tool = language_tool_python.LanguageTool(lang)

    def spans(self, texts):
        out = []
        for t in texts:
            out.append([(m.offset, m.offset + m.error_length) for m in self.tool.check(t)])
        return out

    def close(self):
        self.tool.close()


SYSTEMS = {"redline": RedlineGrammar, "harper": Harper, "languagetool": LanguageToolLocal,
           "redline-vennify": lambda: RedlineGrammar("vennify/t5-base-grammar-correction")}
