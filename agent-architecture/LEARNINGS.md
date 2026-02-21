# Python Learnings (from a JavaScript/TypeScript Developer)

## Environment & Setup

### 1. `venv` = Python's `node_modules`
Isolates dependencies per project. Without it, `pip install` puts packages globally.
```bash
python3 -m venv venv        # create
source venv/bin/activate     # activate (shows (venv) in terminal)
deactivate                   # deactivate
```

### 2. `requirements.txt` = Python's `package.json`
Lists dependencies, one per line. Unlike npm, `pip install` does NOT auto-update this file.
```bash
pip install -r requirements.txt    # install from file
pip freeze > requirements.txt      # lock exact versions (like package-lock.json)
```

### 3. `pip install` and `requirements.txt` are disconnected
In Node, `npm install express` updates `package.json`. In Python, you manually maintain `requirements.txt`. There is no auto-sync.

### 4. `.env` files don't auto-load
Need `python-dotenv` package + `load_dotenv()` call. Must load BEFORE any imports that use env vars.
```python
from dotenv import load_dotenv
load_dotenv()                        # must come before lib imports

from lib.embed import embed_text     # now this can read env vars
```

### 5. `.gitignore` — same concept as Node
```
venv/    # like node_modules/
.env     # like .env.local
```

### 6. `>` overwrites a file, `>>` appends
```bash
echo "first" > file.txt     # overwrites
echo "second" >> file.txt   # appends
```
`printf` handles `\n` for newlines, `echo` does not by default.

### 7. `mkdir -p` creates parent directories
`touch` only creates files, won't create missing parent directories. Use:
```bash
mkdir -p scripts && touch scripts/index_knowledge.py
```

### 8. Python extension + Pylance in VS Code
Gives TypeScript-like autocomplete. After installing, select the venv interpreter:
`Cmd+Shift+P` → "Python: Select Interpreter" → pick the one inside `venv/`.

---

## Syntax Differences (JavaScript → Python)

### 9. `function` → `def`, `{` → `:`
```javascript
// JavaScript
function greet(name) {
    return "hello " + name
}
```
```python
# Python
def greet(name):
    return "hello " + name
```

### 10. camelCase → snake_case
Python convention for variables, functions, and parameters.
```javascript
// JavaScript
const myClient = new Client({ apiKey: "..." })
function getText(inputText) { }
```
```python
# Python
my_client = Client(api_key="...")
def get_text(input_text):
```

### 11. Named arguments use `=` not `:`
```javascript
// JavaScript
client.embed({ model: "voyage-3" })
```
```python
# Python
client.embed(model="voyage-3")     # = not :
client.embed(model: "voyage-3")    # WRONG — JavaScript syntax
```

### 12. Booleans and null are capitalized
| JavaScript | Python |
|---|---|
| `true` | `True` |
| `false` | `False` |
| `null` | `None` |

Using lowercase `true` in Python = undefined variable error.

### 13. No semicolons
Python doesn't use `;` at end of lines. Won't crash, but not Pythonic.

### 14. No parentheses needed around `if` conditions
```javascript
// JavaScript
if (x > 5) { }
```
```python
# Python
if x > 5:        # no parens needed
if (x > 5):      # works but not Pythonic
```

### 15. `== None` → `is None`
Python convention: use `is None` and `is not None` for None checks.
```python
if result is None:        # correct
if result == None:        # works but not Pythonic
```

### 16. Enum syntax
```javascript
// JavaScript/TypeScript
type AgentType = "single" | "multi"
```
```python
# Python (in JSON schema)
"enum": ["single", "multi"]       # list, not pipe operator
```

---

## Data Structures

### 17. Dicts = JavaScript objects (but no dot access)
```javascript
// JavaScript
const chunk = { text: "hello", score: 0.95 }
chunk.text           // works
chunk["text"]        // works
```
```python
# Python
chunk = {"text": "hello", "score": 0.95}
chunk["text"]        # works
chunk.text           # ERROR — dicts don't support dot access
```
Keys must always be quoted in Python dicts.

### 18. Spread operator: `...` → `**`
```javascript
// JavaScript
const updated = { ...chunk, score: 0.9 }
```
```python
# Python
updated = {**chunk, "score": 0.9}
```

### 19. SDK objects use dot notation, dicts use brackets
The Anthropic SDK returns objects (not dicts):
```python
response[0].input    # correct — SDK object
response[0].name     # correct — SDK object
response[0]["input"] # WRONG — these aren't dicts
```
Your own dicts use brackets:
```python
chunk["text"]        # correct — your dict
chunk.text           # WRONG — dicts don't support this
```

---

## Functions & Loops

### 20. `self` = Python's explicit `this`
Must be the first parameter in every class method.
```javascript
// JavaScript — this is implicit
class Chunk {
    constructor(text) { this.text = text }
}
```
```python
# Python — self is explicit
class Chunk:
    def __init__(self, text):    # self required
        self.text = text
```

### 21. `lambda` = arrow function
```javascript
// JavaScript
arr.sort((a, b) => b.score - a.score)
const getScore = (x) => x.score
```
```python
# Python
arr.sort(key=lambda x: x["score"], reverse=True)
get_score = lambda x: x["score"]
```

### 22. `.sort()` returns `None` — can't chain
```javascript
// JavaScript — returns the array, can chain
return arr.sort((a, b) => b.score - a.score).slice(0, 3)
```
```python
# Python — sort() mutates in place, returns None
arr.sort(key=lambda x: x["score"], reverse=True)
return arr[:top_k]    # must be separate line

# Or use sorted() for a one-liner (returns new list)
return sorted(arr, key=lambda x: x["score"], reverse=True)[:top_k]
```

### 23. List comprehension = `.filter()` and `.map()`
```javascript
// JavaScript
const mdFiles = files.filter(f => f.endsWith('.md'))
const scores = chunks.map(c => c.score)
```
```python
# Python
md_files = [f for f in files if f.endswith(".md")]
scores = [c["score"] for c in chunks]
```

### 24. `zip()` pairs elements from two lists
```javascript
// JavaScript
const dot = vecA.map((a, i) => a * vecB[i]).reduce((s, v) => s + v, 0)
```
```python
# Python
dot = sum(a * b for a, b in zip(vec_a, vec_b))
```
`a` and `b` are defined inside the `for` — they're loop variables. Python reads right to left: `for` defines, left side uses.

### 25. `sum(... for ...)` = `.reduce()`
Generator expression inside `sum()`. Like `array.reduce((acc, val) => acc + val, 0)`.

### 26. `** 0.5` = `Math.sqrt()`
```python
norm = sum(a * a for a in vec) ** 0.5    # square root
```

### 27. `[:top_k]` = `.slice(0, topK)`
```python
arr[:3]      # first 3 items
arr[1:4]     # items at index 1, 2, 3
arr[::-1]    # reversed (step of -1)
arr[::1]     # NOT reversed — step of 1 is forward
```

---

## Strings & Files

### 28. f-strings = template literals
```javascript
// JavaScript
`knowledge/${file}`
```
```python
# Python
f"knowledge/{file}"
```

### 29. Triple quotes = multi-line strings
```python
prompt = """
This is a
multi-line string
"""
```
Like backtick strings in JavaScript.

### 30. `.endswith()` not `.endsWith()`
Python is all lowercase — no camelCase in built-in methods.
```python
file.endswith(".md")     # correct
file.endsWith(".md")     # WRONG — JavaScript syntax
```

### 31. `.strip()` = `.trim()`
```python
text.strip()        # removes whitespace from both ends
```

### 32. Reading files
```python
with open("file.txt", "r") as f:
    text = f.read()
```
`with` auto-closes the file when done (like try/finally). `os.listdir()` = `fs.readdirSync()`.

### 33. `"key" not in dict` checks for key existence
```python
if "tasks" not in output:     # correct — checks for key
if tasks not in output:       # WRONG — tasks is undefined variable, needs quotes
```

---

## Framework & Architecture

### 34. FastAPI = Express / Next.js API routes
Receives requests. Not the same as `fetch` (which sends requests).
```python
@app.post("/generate")
def create_request(request: GenerateRequest):
    return {"result": "done"}
```

### 35. uvicorn = `next start`
The process that runs FastAPI:
```bash
uvicorn app:app --reload    # like next dev (auto-reload on changes)
```

### 36. `BaseModel` = TypeScript interface for request body
```python
from pydantic import BaseModel

class GenerateRequest(BaseModel):
    query: str

# FastAPI auto-validates the request body against this shape
@app.post("/generate")
def create_request(request: GenerateRequest):
    query = request.query
```

### 37. Anthropic SDK — `input_schema` not `parameters`
Tool definitions use `input_schema` with `type: "object"` and `properties` wrapper:
```python
{
    "name": "my_tool",
    "description": "what it does",
    "input_schema": {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "..."}
        },
        "required": ["param"]
    }
}
```

### 38. `max_tokens` must be large enough
Spec files are long. `max_tokens=4096` wasn't enough for three files — Claude cut off before generating `tasks`. Bumped to `8192`.

---

## Common Mistakes Made

### 39. Variable name mismatches
Python won't catch this until runtime:
```python
file_text_chunks = []           # defined here
for chunk in text_chunks:       # WRONG — different name, crashes at runtime
```
Always double-check variable names match between definition and usage.

### 40. Loop variable vs list variable confusion
```python
for file_text_chunks in text_chunks:    # WRONG — overwrites the list with each item
for text_chunk in file_text_chunks:     # CORRECT — singular item from plural list
```

### 41. `f.read().split("##")` produces empty first chunk
Text before the first `##` becomes an empty string. Filter it:
```python
chunks = [c.strip() for c in f.read().split("##") if c.strip()]
```

### 42. Import order matters for env vars
If `embed.py` reads `os.environ["KEY"]` at import time, `load_dotenv()` must run BEFORE the import. Otherwise: `KeyError`.

### 43. Python catches errors at runtime, not in the editor
Unlike TypeScript, Python won't show red squiggles for most mistakes. Missing `self`, wrong variable names, wrong argument counts — all crash at runtime. Type hints help but aren't enforced. Test early and often.

---

## Cosine Similarity Math

### 44. The formula
```
score = dot_product / (norm_a × norm_b)
```
- **Dot product:** multiply matching pairs from two vectors and sum them
- **Norm:** square each value, sum them, take square root (the "length" of a vector)
- **Divide:** removes the length, keeps only the angle between vectors
- **Score range:** -1 (opposite) to 0 (unrelated) to 1 (identical)
- **Why it works:** similar meanings produce similar numbers in similar positions

### 45. Sort descending for similarity
Score of 1 = most similar. You want best matches first = descending order.
