# GT Copy Review Agent

Paste a Figma frame URL, Claude reads the copy, and posts improvement suggestions as comments directly on the design.

## Setup

### 1. Clone and install

```bash
cd figma-copy-agent
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
FIGMA_TOKEN=figd_...          # optional — can be entered in the UI instead
```

Get your Figma token at: **Figma → Settings → Security → Personal access tokens**

### 3. Run

```bash
uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000)

---

## Using the app

1. Open a Figma file and select the frame you want reviewed
2. Copy the URL (it should include `?node-id=...`)
3. Paste it into the app
4. Add optional PM context (e.g. "This is the renewal flow for Academy plans")
5. Click **Review copy & post comments**
6. Switch back to Figma — comments will appear anchored to each text element

---

## Deploying for your team

### Railway / Render (recommended)

1. Push this folder to a GitHub repo
2. Connect to [Railway](https://railway.app) or [Render](https://render.com)
3. Set environment variables: `ANTHROPIC_API_KEY`, `FIGMA_TOKEN`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Fly.io

```bash
fly launch
fly secrets set ANTHROPIC_API_KEY=... FIGMA_TOKEN=...
fly deploy
```

---

## Notes

- The Figma URL **must include a `node-id`** — select a frame in Figma and copy the URL from the browser
- The agent skips labels, numbers, prices, dates, and UI chrome — it focuses on headlines, CTAs, body copy, and nudges
- Each teammate can provide their own Figma token in the UI, or you can set a shared one server-side
