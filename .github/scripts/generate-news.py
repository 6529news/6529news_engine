#!/usr/bin/env python3
"""
6529 NEWS - AI News Generator
FIXED cards: SR Top 3, Memes Top 3, Minting Status, Sales Recap
CONDITIONAL: punk6529 activity, dive bar hot topic, new submissions
HEADLINE BAR: dive bar topics, pebbles market, high sales, sweeps
TICKER: 24h volume, 24h sales, floor, leaderboard
"""

import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta

# === CONFIG ===
OPENROUTER_KEY = os.environ.get('OPENROUTER_KEY', '')
OPENSEA_KEY = os.environ.get('OPENSEA_KEY', '')
AI_MODEL = 'nvidia/nemotron-3-super-120b-a12b:free'
GIST_ID = os.environ.get('GIST_ID', '')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')

MEMES_WAVE_ID = 'b6128077-ea78-4dd9-b381-52c4eadb2077'
SR_WAVE_ID = 'd22e3046-a00e-48b9-b245-a339a44c37cd'
DIVEBAR_WAVE_ID = 'b38288e6-ca9d-45ce-8323-3dc5e094f04e'
PUNK6529_HANDLE = 'punk6529'
PUNK6529_PFP = 'https://d3lqz0a4bldqgf.cloudfront.net/pfp/production/413e24a8-b2d2-4746-a10e-d66575d0043f.webp?d=1714229232938'

MEMES_CONTRACT = '0x33fd426905f149f8376e227d0c9d3340aad17af1'
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'waves-config.json')


def fetch_json(url, headers=None):
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (compatible; 6529News/1.0)')
    req.add_header('Accept', 'application/json')
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  Fetch error: {e}")
        return None


def format_tdh(tdh):
    if tdh >= 1_000_000: return f"{tdh/1_000_000:.1f}M"
    if tdh >= 1_000: return f"{tdh/1_000:.0f}K"
    return str(tdh)


def ai_summarize(prompt_text, max_tokens=250):
    """Call AI for summarization. Returns None on failure."""
    if not OPENROUTER_KEY:
        return None
    try:
        body = json.dumps({
            'model': AI_MODEL,
            'messages': [{'role': 'user', 'content': prompt_text}],
            'max_tokens': max_tokens, 'temperature': 0.5
        }).encode()
        req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
            data=body, headers={'Authorization': f'Bearer {OPENROUTER_KEY}', 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
        return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"  AI error: {e}")
        return None


# =============================================
# 1. TOP 3 LEADERBOARD (Memes + SuperRare)
# =============================================
def fetch_ranked_drops(wave_id, limit=10):
    """Fetch ranked drops from a wave using the leaderboard endpoint (correct ranking)."""
    data = fetch_json(f'https://api.6529.io/api/waves/{wave_id}/leaderboard?page_size={limit}')
    if not data or 'drops' not in data:
        return []

    all_ranked = []
    for d in data['drops'][:limit]:
        parts = d.get('parts') or []
        media = parts[0].get('media', []) if parts else []
        img = None
        media_type = 'image'
        if media:
            url = media[0].get('url', '')
            mime = media[0].get('mime_type', '')
            if mime == 'text/html':
                # HTML submission: look for preview_image in metadata.additional_media
                for m in d.get('metadata', []):
                    if m.get('data_key') == 'additional_media':
                        try:
                            extra = json.loads(m['data_value'])
                            preview_url = extra.get('preview_image', '')
                            if preview_url and preview_url.startswith('https://'):
                                # Verify URL is accessible
                                try:
                                    req = urllib.request.Request(preview_url, method='HEAD')
                                    req.add_header('User-Agent', 'Mozilla/5.0 (compatible; 6529News/1.0)')
                                    with urllib.request.urlopen(req, timeout=5) as r:
                                        if r.status == 200 and not r.headers.get('Content-Type', '').startswith('text/html'):
                                            img = preview_url
                                            if preview_url.lower().endswith(('.mp4', '.webm', '.mov')):
                                                media_type = 'video'
                                except:
                                    print(f"    preview_image not accessible: {preview_url[:60]}")
                        except: pass
                        break
            elif url.startswith('https://'):
                img = url
                if mime.startswith('video/') or url.lower().endswith(('.mp4', '.webm', '.mov')):
                    media_type = 'video'
        all_ranked.append({
            'rank': d.get('rank', 0), 'title': d.get('title') or 'Untitled',
            'author': d['author']['handle'],
            'current_tdh': d.get('realtime_rating', 0),
            'projected_tdh': d.get('rating_prediction', 0),
            'voters': d.get('raters_count', 0),
            'img': img, 'media_type': media_type
        })
    return all_ranked


def build_top_memes():
    """Top 3 Memes by projected vote (rating_prediction)."""
    print("Building Top Memes...")
    all_ranked = fetch_ranked_drops(MEMES_WAVE_ID, 10)
    all_ranked.sort(key=lambda x: x['projected_tdh'], reverse=True)
    top3 = all_ranked[:3]

    if not top3: return []

    # Countdown to next checkpoint (decisions Mon/Wed/Fri at 16:00 UTC)
    countdown_text = ''
    now = datetime.now(timezone.utc)
    for i in range(0, 8):
        d = now + timedelta(days=i)
        if d.weekday() in {0, 2, 4}:
            checkpoint = d.replace(hour=16, minute=0, second=0, microsecond=0)
            if checkpoint > now:
                delta = checkpoint - now
                hours = int(delta.total_seconds() // 3600)
                mins = int((delta.total_seconds() % 3600) // 60)
                if hours >= 24:
                    countdown_text = f' Next selection in {hours // 24}d {hours % 24}h.'
                else:
                    countdown_text = f' Next selection in {hours}h {mins}m.'
                break

    # Always show #1's preview; fallback to first with image if #1 has none
    preview = top3[0] if top3[0].get('img') else next((s for s in top3 if s.get('img')), None)
    image = {'url': preview['img'], 'label': f"{preview['title']} - {preview['author']}", 'type': preview.get('media_type', 'image')} if preview else None

    summary = ' | '.join([f"\"{s['title']}\" by {s['author']} ({format_tdh(s['projected_tdh'])} projected TDH, {s['voters']} voters)" for s in top3])
    summary += countdown_text

    return [{
        'category': 'TOP MEMES',
        'headline': f"{top3[0]['author']} Leads with {format_tdh(top3[0]['projected_tdh'])} Projected TDH",
        'summary': summary,
        'source': 'The Memes - Main Stage',
        'link': f'https://6529.io/waves/{MEMES_WAVE_ID}',
        'image': image,
        'dataBoxes': [{'label': s['author'], 'value': format_tdh(s['projected_tdh']), 'sub': f"proj. ({s['voters']} votes)"} for s in top3]
    }]


def build_top_superrare():
    """Top 10 SuperRare by current vote, random featured preview."""
    import random
    print("Building Top SuperRare...")
    all_ranked = fetch_ranked_drops(SR_WAVE_ID, 10)
    all_ranked.sort(key=lambda x: x['current_tdh'], reverse=True)
    top10 = all_ranked[:10]
    top3 = top10[:3]

    if not top3: return []

    # Pick a random artist from top 10 with an image for the preview
    with_img = [s for s in top10 if s.get('img')]
    featured = random.choice(with_img) if with_img else top3[0]
    image = {'url': featured['img'], 'label': f"{featured['author']} ({format_tdh(featured['current_tdh'])})", 'type': featured.get('media_type', 'image')} if featured.get('img') else None

    # Headline changes based on whether featured is #1 or not
    feat_rank = next((i for i, s in enumerate(top10) if s['author'] == featured['author']), 0)
    if feat_rank == 0:
        headline = f"{featured['author']} Leads with {format_tdh(featured['current_tdh'])} TDH"
    else:
        headline = f"#{feat_rank+1} {featured['author']} — {format_tdh(featured['current_tdh'])} TDH"

    summary = ' | '.join([f"{s['author']} ({format_tdh(s['current_tdh'])})" for s in top10 if s['current_tdh'] > 0])

    return [{
        'category': 'TOP SUPERRARE',
        'headline': headline,
        'summary': summary,
        'source': 'SuperRare x 6529',
        'link': f'https://6529.io/waves/{SR_WAVE_ID}',
        'image': image,
        'dataBoxes': [{'label': s['author'], 'value': format_tdh(s['current_tdh']), 'sub': f"TDH ({s['voters']} votes)"} for s in top3]
    }]


# =============================================
# 2. MINTING STATUS
# =============================================
def get_minted_card_image(title):
    """Try to find the image for a card by checking the NFT API (already minted cards have CDN thumbnails)."""
    data = fetch_json(f'https://api.6529.io/api/nfts?contract={MEMES_CONTRACT}&page_size=5&sort=id&sort_direction=desc')
    if not data or not data.get('data'):
        return None
    for nft in data['data']:
        if nft.get('name', '').strip().lower() == title.strip().lower():
            img = nft.get('image') or nft.get('thumbnail')
            if img:
                return img
    return None


def get_winners(count=2):
    """Get the latest N wave decision winners. [0]=most recent, [1]=previous."""
    data = fetch_json(f'https://api.6529.io/api/waves/{MEMES_WAVE_ID}/decisions?page_size={count}')
    if not data or not data.get('data'):
        return []
    results = []
    for dec in data['data'][:count]:
        results.append(_parse_winner(dec))
    return [r for r in results if r]


def _parse_winner(dec):
    """Parse a single decision into winner info."""
    decision_time = datetime.fromtimestamp(dec['decision_time'] / 1000, tz=timezone.utc)
    winners = dec.get('winners', [])
    if not winners:
        return None
    drop = winners[0]['drop']
    author = drop.get('author', {}).get('handle', '?')
    title = drop.get('title') or 'Untitled'
    tdh = drop.get('realtime_rating', 0)
    voters = drop.get('raters_count', 0)

    # Try to get image: 1) from minted NFT CDN, 2) from drop media (only if it's an image), 3) from author's drop media on CDN
    img_url = get_minted_card_image(title)

    img_media_type = 'image'
    if not img_url:
        parts = drop.get('parts') or []
        media = parts[0].get('media', []) if parts else []
        if media:
            mime = media[0].get('mime_type', '')
            url = media[0].get('url', '')
            # Use if it's an image or video served from a reliable CDN
            if (mime.startswith('image/') or mime.startswith('video/')) and not url.startswith('ipfs://'):
                img_url = url
                if mime.startswith('video/'):
                    img_media_type = 'video'
            elif url.startswith('https://d3lqz0a4bldqgf.cloudfront.net/'):
                img_url = url  # 6529 CDN, always works

    # Fallback: use the wave picture if no card image available
    if not img_url:
        wave_data = fetch_json(f'https://api.6529.io/api/waves/{MEMES_WAVE_ID}')
        if wave_data and wave_data.get('picture'):
            img_url = wave_data['picture']

    image = {'url': img_url, 'label': f'{title} - {author}', 'type': img_media_type} if img_url else None

    # Top supporter from top_raters
    top_supporter = None
    top_raters = drop.get('top_raters', [])
    if top_raters:
        handle = top_raters[0].get('profile', {}).get('handle') or top_raters[0].get('handle')
        top_tdh = top_raters[0].get('rating', 0)
        if handle:
            top_supporter = f'{handle} ({format_tdh(top_tdh)} TDH)'

    return {
        'image': image, 'title': title, 'author': author,
        'tdh': tdh, 'voters': voters, 'top_supporter': top_supporter,
        'decision_time': decision_time
    }


def build_minting_status():
    """
    3 states based on the latest wave decision winner:
    - MINTING TODAY: it's a mint day (Mon/Wed/Fri), the winner from the last checkpoint is being minted
    - STILL MINTING: it's a mint day, minting is ongoing (after ~12:00 UTC)
    - NEXT DROP: it's not a mint day, show when the next one is + current #1
    Uses /decisions endpoint for the actual winning card.
    """
    print("Checking minting status...")
    now = datetime.now(timezone.utc)
    mint_days = {0: 'Monday', 2: 'Wednesday', 4: 'Friday'}

    # Get last 2 decisions: [0]=most recent selection, [1]=previous (currently minting)
    winners = get_winners(2)
    latest = winners[0] if len(winners) > 0 else None   # just selected (NEXT MINT)
    current = winners[1] if len(winners) > 1 else latest  # currently minting

    if latest:
        print(f"  Latest selection: \"{latest['title']}\" by {latest['author']}")
    if current and current != latest:
        print(f"  Currently minting: \"{current['title']}\" by {current['author']}")

    # Helper: build TDH description for a winner
    def tdh_for(w):
        if not w: return ''
        desc = f' "{w["title"]}" by {w["author"]} — {format_tdh(w["tdh"])} TDH from {w["voters"]} voters.'
        if w.get('top_supporter'):
            desc += f' Top supporter: {w["top_supporter"]}.'
        return desc

    # =============================================
    # MINTING SCHEDULE
    # Selection: Mon/Wed/Fri 17:00 UTC (18:00 CET)
    # Mint: 2 days after selection (Mon→Wed, Wed→Fri, Fri→Mon=3 days)
    # Times are CET-based: midnight CET = 23:00 UTC
    #
    # Uses TWO selections: prev_sel (card being minted) + latest_sel (card just selected)
    # CARD 1 (current mint): MINTING TOMORROW → MINTING TODAY → STILL MINTING
    # CARD 2 (next mint): NEXT MINT (appears during MINTING TODAY/STILL MINTING)
    # =============================================

    SEL_HOUR = 16  # 16:00 UTC = 17:00 CET
    MIDNIGHT_CET = 23
    END_STILL = 15
    sel_to_mint_offset = {0: 2, 2: 2, 4: 3}

    # Find last TWO selections
    sels = []
    for i in range(14):
        d = now - timedelta(days=i)
        if d.weekday() in mint_days:
            sel = d.replace(hour=SEL_HOUR, minute=0, second=0, microsecond=0)
            if sel <= now:
                sels.append(sel)
                if len(sels) >= 2: break

    latest_sel = sels[0] if sels else None
    prev_sel = sels[1] if len(sels) > 1 else None

    # Find next selection
    next_selection = None
    for i in range(0, 8):
        d = now + timedelta(days=i)
        if d.weekday() in mint_days:
            sel = d.replace(hour=SEL_HOUR, minute=0, second=0, microsecond=0)
            if sel > now:
                next_selection = sel
                break

    latest_image = latest['image'] if latest else None
    latest_desc = tdh_for(latest)
    current_image = current['image'] if current else None
    current_desc = tdh_for(current)

    cards = []

    # --- CARD 1: Current minting (from PREVIOUS selection) ---
    if prev_sel:
        p_offset = sel_to_mint_offset[prev_sel.weekday()]
        p_mint = prev_sel + timedelta(days=p_offset)
        p_start = p_mint.replace(hour=MIDNIGHT_CET) - timedelta(days=1)
        p_end = p_mint.replace(hour=MIDNIGHT_CET)
        p_still_end = p_mint.replace(hour=END_STILL) + timedelta(days=1)

        if p_start <= now < p_end:
            cards.append({
                'category': 'MINTING TODAY', 'headline': 'MINTING TODAY',
                'summary': f"A new Meme Card is being minted today!{current_desc}",
                'source': 'The Memes', 'link': 'https://6529.io/the-memes',
                'image': current_image, 'dataBoxes': None
            })
        elif p_end <= now < p_still_end:
            cards.append({
                'category': 'STILL MINTING', 'headline': 'STILL MINTING',
                'summary': f"Current card is still minting.{current_desc}",
                'source': 'The Memes', 'link': 'https://6529.io/the-memes',
                'image': current_image, 'dataBoxes': None
            })

    # --- CARD 2: Next minting (from LATEST selection) ---
    if latest_sel:
        l_offset = sel_to_mint_offset[latest_sel.weekday()]
        l_mint = latest_sel + timedelta(days=l_offset)
        l_start = l_mint.replace(hour=MIDNIGHT_CET) - timedelta(days=1)
        l_end = l_mint.replace(hour=MIDNIGHT_CET)
        l_still_end = l_mint.replace(hour=END_STILL) + timedelta(days=1)
        l_mint_day_name = mint_days.get(l_mint.weekday(), '')

        if latest_sel <= now < l_start:
            # Between selection and midnight CET before mint = MINTING TOMORROW (or MINTING MONDAY etc)
            cards.append({
                'category': f'MINTING {l_mint_day_name.upper()}', 'headline': f"Minting {l_mint_day_name}",
                'summary': f"{latest_desc}" if latest_desc else f"Next card to be minted.",
                'source': 'The Memes', 'link': 'https://6529.io/the-memes',
                'image': latest_image, 'dataBoxes': None
            })
        elif l_start <= now < l_end:
            # If not already showing MINTING TODAY from prev_sel
            if not any(c['category'] == 'MINTING TODAY' for c in cards):
                cards.append({
                    'category': 'MINTING TODAY', 'headline': 'MINTING TODAY',
                    'summary': f"A new Meme Card is being minted today!{latest_desc}",
                    'source': 'The Memes', 'link': 'https://6529.io/the-memes',
                    'image': latest_image, 'dataBoxes': None
                })
        elif l_end <= now < l_still_end:
            if not any(c['category'] == 'STILL MINTING' for c in cards):
                cards.append({
                    'category': 'STILL MINTING', 'headline': 'STILL MINTING',
                    'summary': f"Current card is still minting.{latest_desc}",
                    'source': 'The Memes', 'link': 'https://6529.io/the-memes',
                    'image': latest_image, 'dataBoxes': None
                })

    # --- Fallback: NEXT DROP if no cards ---
    if not cards and next_selection:
        next_day_name = mint_days[next_selection.weekday()]
        delta = next_selection - now
        hours_left = int(delta.total_seconds() // 3600)
        countdown = f'{hours_left // 24}d {hours_left % 24}h' if hours_left >= 24 else f'{hours_left}h'
        cards.append({
            'category': 'NEXT DROP',
            'headline': f"Next Drop: {next_day_name} ({next_selection.strftime('%b %d')})",
            'summary': f"Next selection in {countdown}.{latest_desc}",
            'source': 'The Memes', 'link': 'https://6529.io/the-memes',
            'image': latest_image, 'dataBoxes': None
        })

    return cards


# =============================================
# 3. SALES RECAP (24h)
# =============================================
def build_sales_recap():
    print("Building sales recap...")
    stats = fetch_json(f'https://api.opensea.io/api/v2/collections/thememes6529/stats', {'X-API-KEY': OPENSEA_KEY})
    sales_data = fetch_json(f'https://api.opensea.io/api/v2/events/collection/thememes6529?event_type=sale&limit=50', {'X-API-KEY': OPENSEA_KEY})

    if not stats: return [], [], []

    floor = stats['total'].get('floor_price', 0)
    floor_sym = stats['total'].get('floor_price_symbol', 'ETH')
    vol_24h = stats['intervals'][0].get('volume', 0) if stats.get('intervals') else 0
    sales_24h = stats['intervals'][0].get('sales', 0) if stats.get('intervals') else 0

    all_sales = []
    high_sales = []
    sweeps = {}
    headline_extras = []
    now = datetime.now(timezone.utc)
    twenty_four_h_ago = now - timedelta(hours=24)

    if sales_data and 'asset_events' in sales_data:
        for e in sales_data['asset_events']:
            # Filter: only sales within last 24h
            ts = e.get('event_timestamp')
            if ts:
                if isinstance(ts, (int, float)):
                    sale_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                else:
                    sale_dt = datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
                if sale_dt < twenty_four_h_ago:
                    continue
            price = int(e['payment']['quantity']) / 1e18
            name = e['nft']['name']
            card_id = e['nft']['identifier']
            all_sales.append({'name': name, 'price': price, 'card_id': card_id})
            if price >= 0.3:
                high_sales.append(f'"{name}" {price:.3f} ETH')
            sweeps[card_id] = sweeps.get(card_id, 0) + 1

    # Sort by price, take top 3 unique cards
    all_sales.sort(key=lambda x: x['price'], reverse=True)
    seen_ids = set()
    top_sales = []
    for s in all_sales:
        if s['card_id'] not in seen_ids:
            seen_ids.add(s['card_id'])
            top_sales.append(s)
        if len(top_sales) >= 3:
            break

    highest = top_sales[0] if top_sales else {'name': '', 'price': 0, 'card_id': ''}
    sweep_cards = [(cid, cnt) for cid, cnt in sweeps.items() if cnt >= 5]

    summary = f'{sales_24h} sales in 24h for {vol_24h:.2f} ETH.'
    if highest['price'] > 0:
        summary += f' Highest: "{highest["name"]}" at {highest["price"]:.3f} ETH.'
    if sweep_cards:
        summary += f' Sweep detected: {len(sweep_cards)} card(s) with 5+ sales.'

    # Build images for top 3 sales
    sales_images = []
    for sale in top_sales:
        nft_data = fetch_json(f'https://api.6529.io/api/nfts?contract={MEMES_CONTRACT}&id={sale["card_id"]}')
        if nft_data:
            nfts = nft_data.get('data', nft_data) if isinstance(nft_data, dict) else nft_data
            if isinstance(nfts, list) and nfts:
                img_url = nfts[0].get('thumbnail') or nfts[0].get('image')
                if img_url:
                    mime = (nfts[0].get('mime_type') or nfts[0].get('media_type') or '')
                    s_type = 'video' if mime.startswith('video/') or img_url.lower().endswith(('.mp4','.webm','.mov')) else 'image'
                    sales_images.append({'url': img_url, 'label': f'{sale["name"]} - {sale["price"]:.3f} ETH', 'type': s_type})

    sales_image = sales_images[0] if sales_images else None

    news = [{
        'category': 'SALES RECAP',
        'headline': f'{sales_24h} Sales Today - {vol_24h:.2f} ETH Volume',
        'summary': summary,
        'source': 'OpenSea', 'link': 'https://opensea.io/collection/thememes6529',
        'image': sales_image,
        'images': sales_images,  # top 3 for grid display
        'dataBoxes': [
            {'label': 'Sales 24h', 'value': str(sales_24h), 'sub': ''},
            {'label': 'Volume 24h', 'value': f'{vol_24h:.2f}', 'sub': 'ETH'},
            {'label': 'Top Sale', 'value': f'{highest["price"]:.3f}', 'sub': highest['name'][:20] if highest['name'] else ''},
            {'label': 'Floor', 'value': str(floor), 'sub': floor_sym}
        ]
    }]

    # Build headline extras for the NEWS bar
    # CONDITIONAL: Sweep alert only
    for cid, cnt in sweep_cards[:1]:
        headline_extras.append(f"SWEEP ALERT: CARD #{cid} - {cnt} SALES IN 24H")

    # 7d data for ticker
    intervals = stats.get('intervals', [])
    vol_7d = intervals[1].get('volume', 0) if len(intervals) > 1 else 0
    sales_7d = intervals[1].get('sales', 0) if len(intervals) > 1 else 0

    # Pebbles market + last sale time for headline
    pebbles = fetch_json('https://api.opensea.io/api/v2/collections/pebbles-by-zeblocks/stats', {'X-API-KEY': OPENSEA_KEY})
    if pebbles:
        p_floor = pebbles['total'].get('floor_price', 0)
        p_vol = pebbles['intervals'][0].get('volume', 0) if pebbles.get('intervals') else 0
        p_sales = pebbles['intervals'][0].get('sales', 0) if pebbles.get('intervals') else 0
        pebbles_text = f"PEBBLES: FLOOR {p_floor} ETH | {p_sales} SALES"
        # Get last Pebbles sale event
        p_events = fetch_json('https://api.opensea.io/api/v2/events/collection/pebbles-by-zeblocks?event_type=sale&limit=1', {'X-API-KEY': OPENSEA_KEY})
        if p_events and p_events.get('asset_events'):
            last_sale_ts = p_events['asset_events'][0].get('event_timestamp')
            if last_sale_ts:
                if isinstance(last_sale_ts, (int, float)):
                    last_sale_dt = datetime.fromtimestamp(last_sale_ts, tz=timezone.utc)
                else:
                    last_sale_dt = datetime.fromisoformat(str(last_sale_ts).replace('Z', '+00:00'))
                delta = datetime.now(timezone.utc) - last_sale_dt
                hours_ago = int(delta.total_seconds() // 3600)
                if hours_ago < 1:
                    mins_ago = int(delta.total_seconds() // 60)
                    pebbles_text += f' | LAST SALE {mins_ago}m AGO'
                elif hours_ago < 24:
                    pebbles_text += f' | LAST SALE {hours_ago}h AGO'
                else:
                    days_ago = hours_ago // 24
                    pebbles_text += f' | LAST SALE {days_ago}d AGO'
        headline_extras.append(pebbles_text)

    ticker_data = [{
        'name': 'Memes', 'floor': floor, 'floor_sym': floor_sym,
        'vol_24h': vol_24h, 'sales_24h': sales_24h,
        'vol_7d': vol_7d, 'sales_7d': sales_7d
    }]

    return news, headline_extras, ticker_data


# =============================================
# 3b. PEBBLES SALES (conditional: any sales in 24h)
# =============================================
# =============================================
# 3a. SR NEW SUBMISSIONS (last 7 days, best by TDH)
# =============================================
def build_sr_submissions():
    print("Checking SuperRare submissions (last 7 days)...")
    cutoff_ms = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp() * 1000)

    all_drops = []
    sn = 999999
    for _ in range(15):
        data = fetch_json(f'https://api.6529.io/api/drops?wave_id={SR_WAVE_ID}&drop_type=PARTICIPATION&limit=20&serial_no_less_than={sn}')
        if not data: break
        all_drops += data
        sn = data[-1]['serial_no']
        if data[-1]['created_at'] < cutoff_ms: break

    if not all_drops: return []

    recent = []
    for d in all_drops:
        if d['created_at'] >= cutoff_ms:
            parts = d.get('parts') or []
            media = parts[0].get('media', []) if parts else []
            if not media:
                continue  # Only count actual art submissions with media
            img = None
            m_type = 'image'
            mime = media[0].get('mime_type', '')
            url = media[0].get('url', '')
            if (mime.startswith('image/') or mime.startswith('video/')) and not url.startswith('ipfs://'):
                img = url
                if mime.startswith('video/'):
                    m_type = 'video'
            elif url.startswith('https://d3lqz0a4bldqgf.cloudfront.net/'):
                img = url
            recent.append({
                'title': d.get('title') or 'Untitled',
                'author': d['author']['handle'],
                'tdh': d.get('realtime_rating', 0),
                'img': img, 'media_type': m_type
            })

    if not recent: return []

    recent.sort(key=lambda x: x['tdh'], reverse=True)
    count = len(recent)

    # Best with media — prefer jpeg/gif (more likely artwork than png screenshots), then video
    with_img = [s for s in recent if s.get('img')]
    preferred = [s for s in with_img if any(ext in s['img'].lower() for ext in ['.jpg', '.jpeg', '.gif', 'image/jpeg', 'image/gif'])]
    best = (preferred or with_img or recent)[0]
    image = {'url': best['img'], 'label': best['author'], 'type': best.get('media_type', 'image')} if best.get('img') else None

    # Summary: just artist names, no TDH
    artists = list(dict.fromkeys(s['author'] for s in recent))
    summary = f'{count} SuperRare submission{"s" if count > 1 else ""} this week: {", ".join(artists[:6])}.'

    print(f"  {count} submissions, featured: {best['author']} ({format_tdh(best['tdh'])})")
    return [{
        'category': 'SR SUBMISSIONS',
        'headline': f'{count} SuperRare Submission{"s" if count > 1 else ""} This Week',
        'summary': summary,
        'source': 'SuperRare x 6529',
        'link': f'https://6529.io/waves/{SR_WAVE_ID}',
        'image': image, 'dataBoxes': None
    }]


def build_pebbles_sales():
    print("Checking Pebbles sales...")
    if not OPENSEA_KEY:
        return []
    stats = fetch_json('https://api.opensea.io/api/v2/collections/pebbles-by-zeblocks/stats', {'X-API-KEY': OPENSEA_KEY})
    if not stats:
        return []

    floor = stats['total'].get('floor_price', 0)
    floor_sym = stats['total'].get('floor_price_symbol', 'ETH')
    vol_24h = stats['intervals'][0].get('volume', 0) if stats.get('intervals') else 0
    sales_24h = stats['intervals'][0].get('sales', 0) if stats.get('intervals') else 0

    if sales_24h == 0:
        print("  No Pebbles sales in 24h")
        return []

    print(f"  Pebbles: {sales_24h} sales, {vol_24h:.3f} ETH vol, floor {floor}")
    return [{
        'category': 'PEBBLES',
        'headline': f'Pebbles: {sales_24h} Sales - {vol_24h:.3f} ETH',
        'summary': f'{sales_24h} Pebbles sold in the last 24h for a total of {vol_24h:.3f} ETH. Current floor: {floor} {floor_sym}.',
        'source': 'OpenSea', 'link': 'https://opensea.io/collection/pebbles-by-zeblocks',
        'image': None,
        'dataBoxes': [
            {'label': 'Sales 24h', 'value': str(sales_24h), 'sub': ''},
            {'label': 'Volume', 'value': f'{vol_24h:.3f}', 'sub': 'ETH'},
            {'label': 'Floor', 'value': str(floor), 'sub': floor_sym}
        ]
    }]


# =============================================
# 3c. GRADIENTS SALES (conditional: any sales in 24h)
# =============================================
def build_gradients_sales():
    print("Checking Gradients sales...")
    if not OPENSEA_KEY:
        return []
    stats = fetch_json('https://api.opensea.io/api/v2/collections/6529gradient/stats', {'X-API-KEY': OPENSEA_KEY})
    if not stats:
        return []

    floor = stats['total'].get('floor_price', 0)
    floor_sym = stats['total'].get('floor_price_symbol', 'ETH')
    vol_24h = stats['intervals'][0].get('volume', 0) if stats.get('intervals') else 0
    sales_24h = stats['intervals'][0].get('sales', 0) if stats.get('intervals') else 0

    if sales_24h == 0:
        print("  No Gradients sales in 24h")
        return []

    print(f"  Gradients: {sales_24h} sales, {vol_24h:.3f} ETH vol, floor {floor}")
    return [{
        'category': 'GRADIENTS',
        'headline': f'Gradients: {sales_24h} Sales - {vol_24h:.3f} ETH',
        'summary': f'{sales_24h} Gradients sold in the last 24h for a total of {vol_24h:.3f} ETH. Current floor: {floor} {floor_sym}.',
        'source': 'OpenSea', 'link': 'https://opensea.io/collection/6529gradient',
        'image': None,
        'dataBoxes': [
            {'label': 'Sales 24h', 'value': str(sales_24h), 'sub': ''},
            {'label': 'Volume', 'value': f'{vol_24h:.3f}', 'sub': 'ETH'},
            {'label': 'Floor', 'value': str(floor), 'sub': floor_sym}
        ]
    }]


# =============================================
# 4. PUNK6529 (conditional: wrote in last 24h)
# =============================================
def build_punk6529():
    print("Checking punk6529...")
    try:
        drops = fetch_json(f'https://api.6529.io/api/drops?author={PUNK6529_HANDLE}&limit=20')
    except Exception as e:
        print(f"  API exception: {e}")
        drops = None

    if not drops or not isinstance(drops, list) or len(drops) == 0:
        print(f"  No drops data (got: {type(drops).__name__}) — adding fallback headline")
        return [], ["PUNK6529 LAST SEEN: (data unavailable)"]

    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    one_hour = now_ms - 3600 * 1000
    twenty_four_h = now_ms - 24 * 3600 * 1000
    recent = [d for d in drops if d.get('created_at', 0) > twenty_four_h]
    very_recent = [d for d in drops if d.get('created_at', 0) > one_hour]

    headline_extra = []

    # FIXED: Always show last seen (from most recent drop ever)
    last = drops[0]
    last_dt = datetime.fromtimestamp(last.get('created_at', 0)/1000, tz=timezone.utc)
    wave_name = (last.get('wave') or {}).get('name') or 'unknown'

    if very_recent:
        latest_wave = (very_recent[0].get('wave') or {}).get('name') or 'unknown'
        headline_extra.append(f"PUNK6529 ACTIVE NOW IN {latest_wave.upper()}")
        if recent:
            headline_extra.append(f"PUNK6529: {len(recent)} MESSAGES TODAY")
    else:
        headline_extra.append(f"PUNK6529 LAST SEEN: {wave_name} ({last_dt.strftime('%b %d %H:%M UTC')})")
        if recent:
            headline_extra.append(f"PUNK6529: {len(recent)} MESSAGES TODAY")

    print(f"  punk6529: {len(recent)} recent, {len(very_recent)} very_recent, headlines: {headline_extra}")

    if not recent or len(recent) < 5:
        if recent:
            print(f"  Only {len(recent)} msgs in 24h (need 5+)")
        return [], headline_extra

    # Get messages for AI summary
    messages = []
    waves_active = set()
    for d in recent[:15]:
        content = (d['parts'][0].get('content') or '')[:200] if d.get('parts') else ''
        waves_active.add(d.get('wave', {}).get('name', '?'))
        if content and len(content) > 20:
            messages.append(content)

    summary = ai_summarize(
        f"Summarize what punk6529 (a key figure in the 6529 NFT community) talked about in these messages. 2-3 sentences, factual:\n\n" +
        '\n'.join([f'- {m}' for m in messages[:8]])
    )
    if not summary:
        best = [m for m in messages if len(m) > 40][:2]
        summary = f'punk6529 posted {len(recent)} messages in {", ".join(waves_active)}. ' + ' | '.join([f'"{q[:80]}"' for q in best])

    print(f"  Active: {len(recent)} msgs")
    return [{
        'category': '6529 TALKS',
        'headline': f'punk6529: {len(recent)} Messages Today',
        'summary': summary,
        'source': list(waves_active)[0] if waves_active else 'Network',
        'link': 'https://6529.io/punk6529',
        'image': {'url': PUNK6529_PFP, 'label': 'punk6529'},
        'dataBoxes': None
    }], []


# =============================================
# 5. HOT WAVE DETECTION (any wave with 200+ msgs/h)
# =============================================
HOT_THRESHOLD = 200

def build_hot_wave():
    """
    Scans ALL active waves. Headline: most active wave in last 4h.
    If any wave hits 200+ msgs/h → main news card with AI summary + wave picture.
    Efficient: 1 call to /waves, then 1 call per recently active wave (max ~10).
    """
    print("Checking hot waves...")
    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    one_h_ago = now_ms - 3600 * 1000
    four_h_ago = now_ms - 4 * 3600 * 1000

    waves = fetch_json('https://api.6529.io/api/waves?limit=20')
    if not waves or not isinstance(waves, list):
        return [], []

    skip = {'QUORUM', 'quorum'}
    active = []
    hot_wave = None

    for w in waves[:15]:
        if w['name'] in skip:
            continue
        latest = w.get('metrics', {}).get('latest_drop_timestamp', 0)
        if latest < four_h_ago:
            continue

        drops = fetch_json(f'https://api.6529.io/api/drops?wave_id={w["id"]}&limit=50')
        if not drops:
            continue
        msgs_1h = sum(1 for d in drops if d['created_at'] > one_h_ago)
        msgs_4h = sum(1 for d in drops if d['created_at'] > four_h_ago)

        if msgs_4h >= 3:
            active.append({'name': w['name'], 'count_4h': msgs_4h, 'count_1h': msgs_1h, 'wave': w})

        # Hot check: if 50 msgs in first page from last hour, paginate to confirm
        if msgs_1h >= 50 and not hot_wave:
            all_drops = list(drops)
            sn = drops[-1]['serial_no']
            for _ in range(8):
                page = fetch_json(f'https://api.6529.io/api/drops?wave_id={w["id"]}&limit=50&serial_no_less_than={sn}')
                if not page: break
                all_drops += page
                sn = page[-1]['serial_no']
                if page[-1]['created_at'] < one_h_ago: break
            total_1h = sum(1 for d in all_drops if d['created_at'] > one_h_ago)
            if total_1h >= HOT_THRESHOLD:
                hot_wave = {'wave': w, 'drops': [d for d in all_drops if d['created_at'] > one_h_ago], 'msgs_1h': total_1h}

    active.sort(key=lambda x: x['count_4h'], reverse=True)

    # Headline: most active wave
    headline_extras = []
    if active:
        top = active[:3]
        headline_extras.append(f"ACTIVE: {' | '.join(a['name'] + ' (' + str(a['count_4h']) + ')' for a in top)}")
        print(f"  Active: {[a['name'] + '(' + str(a['count_4h']) + ')' for a in top]}")
    else:
        print("  No active waves in last 4h")

    if not hot_wave:
        return [], headline_extras

    # === HOT WAVE: AI summary ===
    w = hot_wave['wave']
    recent = hot_wave['drops']
    msgs_1h = hot_wave['msgs_1h']

    weighted_msgs = []
    authors = set()
    for d in recent:
        parts = d.get('parts') or []
        content = (parts[0].get('content') or '')[:250] if parts else ''
        ad = d.get('author', {})
        author = ad.get('handle', '?')
        level = ad.get('level', 0) or 0
        if content and len(content) > 10:
            weighted_msgs.append({'author': author, 'level': level, 'content': content})
            authors.add(author)

    weighted_msgs.sort(key=lambda x: x['level'], reverse=True)
    prompt_msgs = []
    for m in weighted_msgs:
        if m['level'] >= 50:
            prompt_msgs.append(f"@{m['author']} (lv{m['level']}): {m['content'][:200]}")
        elif len(prompt_msgs) < 15:
            prompt_msgs.append(f"@{m['author']}: {m['content'][:100]}")

    summary = ai_summarize(
        f"What topic is being discussed right now in \"{w['name']}\" (6529 community)? "
        f"MAX 2 short sentences. @username format. No filler:\n\n" +
        '\n'.join(prompt_msgs[:15]), max_tokens=100)
    if not summary:
        top = weighted_msgs[:2]
        summary = ' '.join(f"@{m['author']}: \"{m['content'][:50]}\"" for m in top)

    topic_title = ai_summarize(
        f"3-5 word title for this topic. No quotes:\n\n{summary}", max_tokens=20)
    if not topic_title or len(topic_title) > 50:
        topic_title = f"{msgs_1h} msgs/h"
    topic_title = topic_title.strip().strip('"\'.')

    wave_pic = {'url': w['picture'], 'label': w['name']} if w.get('picture') else None
    wname = w['name']
    print(f"  HOT: {wname} — {msgs_1h} msgs/h, topic: {topic_title}")

    return [{
        'category': f'HOT IN {wname.upper()[:30]}',
        'headline': f"Hot in {wname} — {topic_title}",
        'summary': summary,
        'source': wname,
        'link': f'https://6529.io/waves/{w["id"]}',
        'image': wave_pic, 'dataBoxes': None
    }], headline_extras


# =============================================
# 6. NEW SUBMISSIONS (24h, best by TDH)
# =============================================
def build_new_submissions():
    # Last 7 days rolling
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    cutoff_ms = int(cutoff.timestamp() * 1000)
    print(f"Checking new Memes submissions (last 7 days, since {cutoff.strftime('%a %b %d')})...")

    # Paginate fully to get ALL drops in 7 days
    all_drops = []
    sn = 999999
    for _ in range(30):
        data = fetch_json(f'https://api.6529.io/api/drops?wave_id={MEMES_WAVE_ID}&drop_type=PARTICIPATION&limit=50&serial_no_less_than={sn}')
        if not data: break
        all_drops += data
        sn = data[-1]['serial_no']
        if data[-1]['created_at'] < cutoff_ms: break

    if not all_drops: return []

    recent = []
    for d in all_drops:
        if d['created_at'] >= cutoff_ms:
            parts = d.get('parts') or []
            media = parts[0].get('media', []) if parts else []
            if not media:
                continue  # No media = not a submission (just text)
            title = d.get('title') or ''
            tdh = d.get('realtime_rating', 0)
            mime = media[0].get('mime_type', '')
            url = media[0].get('url', '')

            # Preview media: images < 5MB, or videos
            img = None
            m_type = 'image'
            if (mime.startswith('image/') or mime.startswith('video/')) and not url.startswith('ipfs://'):
                if mime.startswith('video/'):
                    img = url
                    m_type = 'video'
                else:
                    try:
                        req = urllib.request.Request(url, method='HEAD')
                        req.add_header('User-Agent', 'Mozilla/5.0 (compatible; 6529News/1.0)')
                        with urllib.request.urlopen(req, timeout=5) as r:
                            size = int(r.headers.get('Content-Length', 0))
                            if size < 5_000_000:
                                img = url
                    except:
                        img = url  # If HEAD fails, include anyway

            recent.append({
                'title': title or 'Untitled',
                'author': d['author']['handle'],
                'tdh': tdh,
                'img': img, 'media_type': m_type
            })

    if not recent: return []

    # Deduplicate by author — keep highest TDH per author
    recent.sort(key=lambda x: x['tdh'], reverse=True)
    seen_authors = set()
    unique = []
    for s in recent:
        if s['author'] not in seen_authors:
            seen_authors.add(s['author'])
            unique.append(s)
    count = len(unique)

    # Top 3 media (images/videos, already filtered for size < 5MB)
    with_img = [s for s in unique if s.get('img')]
    top_images = [{'url': s['img'], 'label': f'{s["author"]} ({format_tdh(s["tdh"])})', 'type': s.get('media_type', 'image')} for s in with_img[:3]]

    # Summary: ranked unique artists by TDH
    ranked = [f'{s["author"]} ({format_tdh(s["tdh"])})' for s in unique if s['tdh'] > 0][:8]
    summary = f'{count} submissions this week. Ranking: {" | ".join(ranked)}.' if ranked else f'{count} submissions this week.'

    image = top_images[0] if top_images else None

    print(f"  {count} unique artists, top: {unique[0]['author']} ({format_tdh(unique[0]['tdh'])})")
    return [{
        'category': 'NEW MEMES SUBMISSIONS',
        'headline': f'{count} New Memes Submission{"s" if count > 1 else ""} (7d)',
        'summary': summary,
        'source': 'Main Stage',
        'link': f'https://6529.io/waves/{MEMES_WAVE_ID}',
        'image': image, 'images': top_images, 'dataBoxes': None
    }]


# =============================================
# 7. TDH ON SUBMISSIONS (Main Stage total)
# =============================================
def build_tdh_on_submissions():
    """FIXED headline: total TDH across all Main Stage submissions."""
    print("Calculating TDH on submissions...")
    all_drops = []
    sn = 999999
    for _ in range(30):
        data = fetch_json(f'https://api.6529.io/api/drops?wave_id={MEMES_WAVE_ID}&drop_type=PARTICIPATION&limit=50&serial_no_less_than={sn}')
        if not data: break
        all_drops += data
        sn = data[-1]['serial_no']
        if len(data) < 50: break

    total_tdh = sum(d.get('realtime_rating', 0) for d in all_drops)
    count = len(all_drops)
    print(f"  {count} submissions, total TDH: {format_tdh(total_tdh)}")
    return [f"TDH ON SUBMISSIONS: {format_tdh(total_tdh)} ({count} SUBMISSIONS)"]


# =============================================
# 8. NAKAMOTO SALES (conditional, check OpenSea)
# =============================================
NAKA_COLLECTION = 'nakamoto-freedom-by-punk6529'

def build_naka_sales():
    """CONDITIONAL headline: any Nakamoto card sale in last hour."""
    print("Checking Nakamoto sales...")
    if not OPENSEA_KEY:
        return []
    events = fetch_json(
        f'https://api.opensea.io/api/v2/events/collection/{NAKA_COLLECTION}?event_type=sale&limit=10',
        {'X-API-KEY': OPENSEA_KEY}
    )
    if not events or not events.get('asset_events'):
        print("  No Nakamoto events")
        return []

    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    headlines = []

    for e in events['asset_events']:
        ts = e.get('event_timestamp')
        if not ts:
            continue
        if isinstance(ts, (int, float)):
            sale_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        else:
            sale_dt = datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
        if sale_dt >= one_hour_ago:
            price = int(e['payment']['quantity']) / 1e18
            name = e['nft'].get('name', 'Nakamoto Card')
            headlines.append(f"NAKA SALE: \"{name}\" {price:.3f} ETH")

    if headlines:
        print(f"  {len(headlines)} Nakamoto sales in last hour")
    else:
        print("  No recent Nakamoto sales")
    return headlines


# =============================================
# 9. DIVE BAR ACTIVITY (messages in last hour)
# =============================================
def build_divebar_activity():
    """FIXED headline: message count in maybe's dive bar last 6 hours."""
    print("Checking dive bar activity...")
    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    six_h_ago = now_ms - 6 * 3600 * 1000
    total = 0
    sn = 999999
    for _ in range(30):
        drops = fetch_json(f'https://api.6529.io/api/drops?wave_id={DIVEBAR_WAVE_ID}&limit=50&serial_no_less_than={sn}')
        if not drops or not isinstance(drops, list) or len(drops) == 0:
            break
        total += sum(1 for d in drops if d.get('created_at', 0) > six_h_ago)
        sn = drops[-1]['serial_no']
        if drops[-1].get('created_at', 0) < six_h_ago:
            break
    print(f"  Dive bar: {total} msgs in last 6h")
    return [f"DIVE BAR: {total} MSGS IN LAST 6H"]


# =============================================
# OUTPUT
# =============================================
def fetch_network_stats():
    """Fetch Network TDH, Full Set Bid, Collection Holders, Full Set Holders."""
    print("Fetching network stats...")
    total_tdh = 0
    total_bid = 0
    page = 1
    while True:
        data = fetch_json(f'https://api.6529.io/api/memes_extended_data?page_size=50&page={page}')
        if not data or not data.get('data'):
            break
        for item in data['data']:
            total_tdh += item.get('boosted_tdh', 0) or 0
            total_bid += item.get('highest_offer', 0) or 0
        if not data.get('next'):
            break
        page += 1

    # Scrape holder counts from 6529nfts.io
    holders = 0
    full_set = 0
    try:
        import re
        req = urllib.request.Request('https://www.6529nfts.io/memes/collection-holder-insights',
            headers={'User-Agent': 'Mozilla/5.0 (compatible; 6529News/1.0)', 'Accept': 'text/html'})
        html = urllib.request.urlopen(req, timeout=15).read().decode()
        # Extract from HTML table cells (format: "Label</td><td...>VALUE</td>")
        h_match = re.findall(r'Collection Holder[^<]*</td><td[^>]*>([0-9,]+)', html)
        f_match = re.findall(r'Full Set Holder[^<]*</td><td[^>]*>([0-9,]+)', html)
        # Take the last match (the actual value, not the title reference)
        if h_match:
            holders = int(h_match[-1].replace(',', ''))
        if f_match:
            full_set = int(f_match[-1].replace(',', ''))
    except Exception as e:
        print(f"  Holder scrape error: {e}")

    print(f"  Network TDH: {format_tdh(total_tdh)}, Full Set Bid: {total_bid:.2f} ETH, Holders: {holders}, Full Set: {full_set}")
    return total_tdh, total_bid, holders, full_set


def build_output(news, ticker_data, headline_extras, top_memes_data=None):
    ticker = []

    # Network stats
    network_tdh, full_set_bid, holders, full_set_holders = fetch_network_stats()
    if network_tdh > 0:
        ticker.append({'label': 'Network TDH', 'value': format_tdh(network_tdh)})
    if full_set_bid > 0:
        ticker.append({'label': 'Full Set Bid', 'value': f'{full_set_bid:.1f} ETH'})
    if holders > 0:
        ticker.append({'label': 'Holders', 'value': f'{holders:,}'})
    if full_set_holders > 0:
        ticker.append({'label': 'Full Set', 'value': str(full_set_holders)})

    # Memes #1 only
    if top_memes_data and len(top_memes_data) > 0:
        m = top_memes_data[0]
        ticker.append({'label': f"#1 {m['author']}", 'value': f"{format_tdh(m['projected_tdh'])} TDH"})

    # Sales data: 24h + 7d (ETH only)
    for m in ticker_data:
        if m.get('vol_24h', 0) > 0:
            ticker.append({'label': '24h Vol', 'value': f"{m['vol_24h']:.2f} ETH"})
        if m.get('vol_7d', 0) > 0:
            ticker.append({'label': '7d Vol', 'value': f"{m['vol_7d']:.2f} ETH"})

    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'model': AI_MODEL,
        'news': news[:10],
        'ticker': ticker,
        'headline_extras': headline_extras[:10]
    }


def update_gist(output):
    if not GITHUB_TOKEN or not GIST_ID: return
    body = json.dumps({'files': {'news-latest.json': {'content': json.dumps(output, indent=2)}}}).encode()
    req = urllib.request.Request(f'https://api.github.com/gists/{GIST_ID}', data=body, method='PATCH',
        headers={'Authorization': f'Bearer {GITHUB_TOKEN}', 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as r: print("Gist updated")
    except Exception as e: print(f"Gist error: {e}")


# =============================================
# HEADLINE: NEW WAVES
# =============================================
def build_new_waves_headline():
    """Check if new waves were created in last 24h."""
    print("Checking new waves...")
    waves = fetch_json('https://api.6529.io/api/waves?limit=10')
    if not waves or not isinstance(waves, list):
        return []

    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    twenty_four_h = now_ms - 24 * 3600 * 1000
    headlines = []

    skip = {'QUORUM', 'quorum'}
    new_waves = [w for w in waves if w.get('created_at', 0) > twenty_four_h and w['name'] not in skip]
    if new_waves:
        names = [w['name'] for w in new_waves[:3]]
        if len(new_waves) == 1:
            headlines.append(f"NEW WAVE: \"{names[0]}\"")
        else:
            headlines.append(f"NEW WAVES ({len(new_waves)}): {' | '.join(names)}")

    return headlines


# =============================================
# MAIN
# =============================================
def main():
    print(f"=== 6529 NEWS Generator ===")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")

    all_news = []
    all_headlines = []

    # --- CARD ORDER: Minting → Memes Top → New Submissions → SR Top → Dive Bar → punk6529 ---

    print("\n--- 1. Minting Status ---")
    all_news += build_minting_status()

    print("\n--- 2. Top Memes ---")
    # Also fetch ranked drops for ticker
    top_memes_ranked = fetch_ranked_drops(MEMES_WAVE_ID, 10)
    top_memes_ranked.sort(key=lambda x: x['projected_tdh'], reverse=True)
    all_news += build_top_memes()

    print("\n--- 3. New Submissions ---")
    all_news += build_new_submissions()

    print("\n--- 4. Top SuperRare ---")
    all_news += build_top_superrare()

    print("\n--- 4b. SR Submissions ---")
    all_news += build_sr_submissions()

    # Hot wave removed — dive bar activity tracked via build_divebar_activity()

    print("\n--- 6. punk6529 (conditional) ---")
    p6529_news, p6529_headlines = build_punk6529()
    all_news += p6529_news
    all_headlines += p6529_headlines

    print("\n--- Sales Recap (card + headlines) ---")
    sales_news, sales_headlines, ticker_data = build_sales_recap()
    all_news += sales_news
    all_headlines += sales_headlines

    print("\n--- Pebbles Sales (conditional) ---")
    all_news += build_pebbles_sales()

    print("\n--- Gradients Sales (conditional) ---")
    all_news += build_gradients_sales()

    print("\n--- Dive Bar activity (headline) ---")
    all_headlines += build_divebar_activity()

    print("\n--- Nakamoto Sales (conditional headline) ---")
    all_headlines += build_naka_sales()

    # --- BUILD OUTPUT ---
    output = build_output(all_news, ticker_data, all_headlines, top_memes_ranked[:3])

    # --- PRESERVE DATA: if ticker is empty/sparse, keep previous values ---
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'news-latest.json')
    try:
        with open(out_path) as f:
            prev = json.load(f)
        # If new ticker has fewer items than previous, merge missing from previous
        if len(output['ticker']) < len(prev.get('ticker', [])):
            prev_labels = {t['label'] for t in output['ticker']}
            for t in prev['ticker']:
                if t['label'] not in prev_labels:
                    output['ticker'].append(t)
            print(f"  Preserved {len(output['ticker']) - len(prev_labels)} ticker items from previous run")
    except:
        pass

    print(f"\n--- Total: {len(output['news'])} cards, {len(output['ticker'])} ticker, {len(output['headline_extras'])} headlines ---")

    # --- PUBLISH ---
    update_gist(output)
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Written to {out_path}\nDone!")


if __name__ == '__main__':
    main()
