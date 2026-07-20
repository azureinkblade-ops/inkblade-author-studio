"""
Post the 2026-07-19 asset reel to Buffer (IG Reel + TikTok + X).
Uses the committed reel-assets-2026-07-19.mp4 (public raw URL).
Caption is persona-voiced (Faceless Growth Operator / Short-Form Video Director):
Author Education + Product Promotion tone, concrete deliverable, one CTA, LAUNCH 20%.

Run:  python post_reel_2026-07-19.py          # dry-run (prints captions + asset check)
      python post_reel_2026-07-19.py --post   # publish to Studio Buffer
"""
import os, argparse, requests, json

ENV = r"C:\Users\David\Documents\Automation tool\.env.local"
GRAPHQL = "https://api.buffer.com"
CHANNELS = {"instagram": "6a57ad0180cc80cdcabc46a9",
            "tiktok": "6a57b1d480cc80cdcabc985a",
            "x": "6a57b1f680cc80cdcabc993b"}
REEL_VIDEO = ("https://raw.githubusercontent.com/azureinkblade-ops/inkblade-author-studio/"
              "main/assets/posts/reel-assets-2026-07-19.mp4")

FRAG = ('... on PostActionSuccess { post { id text status } } '
        '... on MutationError { message } '
        '... on InvalidInputError { message } '
        '... on LimitReachedError { message } '
        '... on RestProxyError { message } '
        '... on UnexpectedError { message }')


def load_key():
    ids = {}
    for line in open(ENV, encoding="utf-8"):
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        ids[k.strip()] = v.strip()
    key = ids.get("BUFFER_STUDIO_API_KEY")
    if not key:
        raise SystemExit("No BUFFER_STUDIO_API_KEY")
    if "BUFFER_STUDIO_CHANNEL_IDS" in ids:
        for pair in ids["BUFFER_STUDIO_CHANNEL_IDS"].split(","):
            if ":" in pair:
                net, cid = pair.split(":", 1)
                if net.strip() in CHANNELS:
                    CHANNELS[net.strip()] = cid.strip()
    return key


VIDEO_ASSET = [{"video": {"url": REEL_VIDEO}}]

# Persona-voiced caption (Author Education / Product Promotion). One CTA, LAUNCH 20%.
CAPTION = (
    "I don't have time to make graphics. Here is the fix. "
    "The Inkblade Author Studio hands fantasy and LitRPG authors a full promo system: "
    "350 captions, promo layouts, a release calendar, and 100 ready-to-post images. "
    "One chapter becomes a full week of content. "
    "LAUNCH is on, 20% off with code LAUNCH at the link in bio. "
    "#authortools #bookmarketing #selfpublishing #fantasywriter #litrpg"
)

# X gets a tighter cut (<=280 chars), same persona voice + one CTA.
CAPTION_X = (
    "I don't have time to make graphics. Here is the fix. "
    "350 captions, promo layouts, a release calendar, 100 images. "
    "One chapter = a week of content. "
    "LAUNCH 20% off with code LAUNCH. Link in bio. "
    "#authortools #bookmarketing #litrpg"
)

POSTS = [
    {"channel": "instagram", "text": CAPTION, "assets": VIDEO_ASSET,
     "metadata": {"instagram": {"type": "reel", "shouldShareToFeed": True}}},
    {"channel": "tiktok", "text": CAPTION, "assets": [{"video": {"url": REEL_VIDEO}}],
     "metadata": {}},
    {"channel": "x", "text": CAPTION_X,
     "assets": [{"video": {"url": REEL_VIDEO}}], "metadata": {}},
]


def create(key, p):
    cid = CHANNELS[p["channel"]]
    payload = {"text": p["text"], "channelId": cid, "schedulingType": "automatic",
               "mode": "addToQueue", "saveToDraft": False, "assets": p["assets"],
               "metadata": p["metadata"]}
    q = 'mutation CreatePost($input: CreatePostInput!) { createPost(input:$input) { %s } }' % FRAG
    r = requests.post(GRAPHQL, headers={"Authorization": f"Bearer {key}",
                      "Content-Type": "application/json"},
                      json={"query": q, "variables": {"input": payload}}, timeout=30)
    return r.status_code, r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", action="store_true")
    args = ap.parse_args()
    key = load_key()
    if args.post:
        for p in POSTS:
            sc, res = create(key, p)
            print(f"[{p['channel']}] HTTP {sc} -> {res.get('data', {}).get('createPost', res)}")
    else:
        print("DRY-RUN\n")
        for p in POSTS:
            n = len(p["text"])
            flag = "" if (p["channel"] != "x" or n <= 280) else f"  <-- X OVER 280 ({n})"
            print(f"[{p['channel']}] text={n} chars, assets={len(p['assets'])}, meta={p['metadata']}{flag}")
        print(f"\nReel URL: {REEL_VIDEO}")


if __name__ == "__main__":
    main()
