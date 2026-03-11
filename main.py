import os
import re
import json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import anthropic

app = FastAPI()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
FIGMA_TOKEN = os.environ.get("FIGMA_TOKEN")

TONE_OF_VOICE = """
You are a UX copy expert for Game Theory, a sports platform in India.

PRODUCT CONTEXT:
- Academy = coaching plans for kids under 18, managed by their parents via the app
- All Access = unlimited sports membership for adults, self-managed
- Both products are for users in Bangalore, India

TONE OF VOICE:
- Sporty and motivating — energy of a good coach, not a corporate app
- Personal — use first name where available, always reference the child's name for Academy
- Forward-moving — always point ahead, never dwell on failure or loss
- Positive framing — "access paused" not "plan expired", "ended" not "expired"
- Benefit-first CTAs — lead with what the user gains
- Conversational, not legal — plain English for disclaimers
- For Academy: every headline and CTA should centre on the CHILD, not the parent
- For All Access: first-person adult framing, streak and access continuity are the hooks

RULES:
- Sentence case everywhere except ALL-CAPS section labels (used sparingly)
- Contractions are fine: you're, don't, let's
- Max one exclamation mark per screen, only on genuine celebrations
- "up to" not "upto" — always two words
- "in case" not "incase"
- Avoid: "Don't worry", "Are you sure", "mandatory", "Please note", "kindly", "hassle-free"
- CTAs: imperative verb + optional context ("Book now", "Claim offer", "Get back on the court")
- "Remind later" → "Not now" for soft dismissals
- "View Offer" → "Claim offer"
- "Expired" → "ended" or "paused"
"""


class ReviewRequest(BaseModel):
    figma_url: str
    pm_context: str = ""
    figma_token: str = ""
    anthropic_key: str = ""


def parse_figma_url(url: str):
    match = re.search(r'figma\.com/design/([^/]+)', url)
    if not match:
        raise ValueError("Invalid Figma URL")
    file_key = match.group(1)
    node_id = None
    node_match = re.search(r'node-id=([^&]+)', url)
    if node_match:
        node_id = node_match.group(1).replace('-', ':')
    return file_key, node_id


def get_figma_nodes(file_key: str, node_id: str, token: str):
    headers = {"X-Figma-Token": token}
    r = httpx.get(
        f"https://api.figma.com/v1/files/{file_key}/nodes?ids={node_id}",
        headers=headers, timeout=30
    )
    r.raise_for_status()
    return r.json()


def get_screen_frames(file_key: str, node_id: str, token: str):
    """Get metadata to find screen frames and text nodes."""
    headers = {"X-Figma-Token": token}
    r = httpx.get(
        f"https://api.figma.com/v1/files/{file_key}/nodes?ids={node_id}",
        headers=headers, timeout=30
    )
    r.raise_for_status()
    data = r.json()

    frames = []
    text_nodes = []

    def walk(node, parent_frame=None):
        ntype = node.get("type", "")
        nid = node.get("id", "")
        name = node.get("name", "")
        bbox = node.get("absoluteBoundingBox", {})

        if ntype == "FRAME" and parent_frame is None:
            # Top-level frame — treat as a screen
            frames.append({
                "id": nid,
                "name": name,
                "x": bbox.get("x", 0),
                "y": bbox.get("y", 0),
                "width": bbox.get("width", 0),
                "height": bbox.get("height", 0),
            })
            for child in node.get("children", []):
                walk(child, parent_frame=nid)
        elif ntype == "TEXT":
            text_nodes.append({
                "id": nid,
                "text": name,
                "abs_x": bbox.get("x", 0),
                "abs_y": bbox.get("y", 0),
            })
            for child in node.get("children", []):
                walk(child, parent_frame=parent_frame)
        else:
            for child in node.get("children", []):
                walk(child, parent_frame=parent_frame)

    for node_data in data.get("nodes", {}).values():
        doc = node_data.get("document", {})
        for child in doc.get("children", []):
            walk(child)

    return frames, text_nodes


def match_text_to_frame(text_nodes, frames):
    """Match each text node to the screen frame that contains it."""
    matched = []
    for tn in text_nodes:
        tx, ty = tn["abs_x"], tn["abs_y"]
        for frame in frames:
            fx, fy = frame["x"], frame["y"]
            fw, fh = frame["width"], frame["height"]
            if fx <= tx <= fx + fw and fy <= ty <= fy + fh:
                matched.append({
                    **tn,
                    "frame_id": frame["id"],
                    "frame_name": frame["name"],
                    "offset_x": round(tx - fx),
                    "offset_y": round(ty - fy),
                })
                break
    return matched


def post_figma_comment(file_key: str, frame_id: str, offset_x: int, offset_y: int, message: str, token: str):
    headers = {"X-Figma-Token": token, "Content-Type": "application/json"}
    payload = {
        "message": message,
        "client_meta": {
            "node_id": frame_id,
            "node_offset": {"x": offset_x, "y": offset_y},
            "stable_path": [frame_id]
        }
    }
    r = httpx.post(
        f"https://api.figma.com/v1/files/{file_key}/comments",
        headers=headers, json=payload, timeout=15
    )
    r.raise_for_status()
    return r.json()


@app.post("/review")
async def review_figma(req: ReviewRequest):
    figma_token = req.figma_token or FIGMA_TOKEN
    if not figma_token:
        raise HTTPException(status_code=400, detail="Figma token required")

    anthropic_key = req.anthropic_key or ANTHROPIC_API_KEY
    if not anthropic_key:
        raise HTTPException(status_code=400, detail="Anthropic API key required")

    try:
        file_key, node_id = parse_figma_url(req.figma_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not node_id:
        raise HTTPException(status_code=400, detail="URL must include a node-id")

    # Get Figma data
    try:
        frames, text_nodes = get_screen_frames(file_key, node_id, figma_token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Figma API error: {e}")

    if not text_nodes:
        raise HTTPException(status_code=400, detail="No text nodes found in this frame")

    matched = match_text_to_frame(text_nodes, frames)

    # Build copy list for Claude
    copy_summary = "\n".join([
        f"[{m['frame_name']}] node:{m['id']} | \"{m['text']}\""
        for m in matched
        if len(m['text']) > 2 and not m['text'].replace(',', '').replace('.', '').replace(' ', '').isdigit()
    ])

    # Ask Claude for copy improvements
    client = anthropic.Anthropic(api_key=anthropic_key)

    prompt = f"""You are reviewing app copy for Game Theory, a sports platform.

{f'PM CONTEXT: {req.pm_context}' if req.pm_context else ''}

Here is the copy found in this Figma frame, grouped by screen:
{copy_summary}

For each piece of copy that can be improved, respond with a JSON array of suggestions.
Each suggestion should have:
- "node_id": the node ID from above (e.g. "671:8808")
- "suggestion": the improved copy (just the copy itself, no explanation inline)
- "reason": one sentence explaining why

Only suggest changes for copy that genuinely needs improvement.
Skip labels, names, numbers, prices, dates, and UI chrome that doesn't need copywriting.
Focus on: headlines, CTAs, body copy, success/error messages, empty states, nudges.

Respond with ONLY a valid JSON array, no other text."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=TONE_OF_VOICE,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'^```\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    try:
        suggestions = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Claude returned invalid JSON: {raw[:200]}")

    # Build a lookup from node_id to frame info
    node_lookup = {m['id']: m for m in matched}

    # Post comments to Figma
    posted = []
    errors = []
    for s in suggestions:
        node_id_s = s.get("node_id", "")
        node_info = node_lookup.get(node_id_s)
        if not node_info:
            errors.append(f"Node {node_id_s} not found in matched nodes")
            continue

        message = f"{s['suggestion']}\n\n{s['reason']}"
        try:
            result = post_figma_comment(
                file_key,
                node_info["frame_id"],
                node_info["offset_x"],
                node_info["offset_y"],
                message,
                figma_token
            )
            posted.append({
                "node_id": node_id_s,
                "text": node_info["text"],
                "suggestion": s["suggestion"],
                "reason": s["reason"],
                "comment_id": result.get("id"),
            })
        except Exception as e:
            errors.append(f"Failed to post comment for {node_id_s}: {e}")

    return {
        "posted": len(posted),
        "comments": posted,
        "errors": errors,
    }


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html") as f:
        return f.read()
