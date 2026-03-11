# GT Copy Review Agent

Paste a Figma frame URL, Claude reads the copy, and posts improvement suggestions as comments directly on the design.

**Live app → [steadfast-gratitude-production.up.railway.app](https://steadfast-gratitude-production.up.railway.app)**

---

## Using the app

1. Open a Figma file, select the frame you want reviewed, and copy the URL from your browser (it should include `?node-id=...`)
2. Paste it into the app
3. Add optional PM context (e.g. "This is the renewal flow for Academy plans — kids under 18, parent-managed")
4. Enter your Figma token and Anthropic API key (see below)
5. Click **Review copy & post comments**
6. Switch back to Figma — suggestions appear as comments anchored to each text element

---

## Getting your API keys

**Figma token** — needed to read designs and post comments:
- Figma → top-left menu → **Settings → Security → Personal access tokens** → Generate token
- Looks like `figd_...`

**Anthropic API key** — needed to run Claude:
- [console.anthropic.com](https://console.anthropic.com) → API Keys → Create key
- Looks like `sk-ant-...`
- Each review costs a few cents — monitor usage at console.anthropic.com

---

## Notes

- The Figma URL **must include a `node-id`** — click on a frame in Figma first, then copy the URL from the browser
- The agent focuses on headlines, CTAs, body copy, success/error messages, and nudges — it skips labels, prices, dates, and UI chrome
- Comments are posted under your Figma account (whoever's token is used)

---

## Running locally

```bash
git clone https://github.com/veluthoor/figma-copy-agent.git
cd figma-copy-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000)
