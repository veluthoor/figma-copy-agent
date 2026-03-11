# GT Copy Review Agent

Paste a Figma frame URL, Claude reads the copy, and posts improvement suggestions as comments directly on the design.

---

## Teammate setup (5 minutes)

Everyone runs this locally with their own API credentials — no shared keys.

### 1. Clone the repo

```bash
git clone https://github.com/veluthoor/figma-copy-agent.git
cd figma-copy-agent
```

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Get your API keys

**Anthropic API key** (needed to run Claude):
- Go to [console.anthropic.com](https://console.anthropic.com) → API Keys → Create key
- It looks like `sk-ant-...`

**Figma token** (needed to read designs and post comments):
- In Figma: top-left menu → **Settings → Security → Personal access tokens** → Generate token
- It looks like `figd_...`
- You can also enter this in the UI each time instead of saving it

### 4. Add your keys

```bash
cp .env.example .env
```

Open `.env` and fill in your keys:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
FIGMA_TOKEN=figd_your-token-here   # optional if you prefer to enter it in the UI
```

### 5. Run

```bash
uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000)

---

## Using the app

1. Open a Figma file, select the frame you want reviewed, and copy the URL from your browser (it should include `?node-id=...`)
2. Paste the URL into the app
3. Add optional PM context (e.g. "This is the renewal flow for Academy plans — kids under 18, parent-managed")
4. Click **Review copy & post comments**
5. Switch back to Figma — suggestions appear as comments anchored to each text element

---

## Notes

- The Figma URL **must include a `node-id`** — click on a frame in Figma first, then copy the URL
- The agent focuses on headlines, CTAs, body copy, success/error messages, and nudges — it skips labels, prices, dates, and UI chrome
- Comments are posted under your Figma account (whoever's token is used)
- Each run costs a few cents in Anthropic API credits — check [console.anthropic.com](https://console.anthropic.com) to monitor usage
