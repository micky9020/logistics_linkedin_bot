import os, re, json, hashlib, time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote
import feedparser, requests
from dotenv import load_dotenv

load_dotenv()
BASE = Path(__file__).parent
HISTORY = BASE / 'posted.json'
VIDEO_DIR = BASE / 'videos'
TOPICS = {
    'supply_chain': ['supply chain', 'supply chains', 'cadena de suministro', 'resilience'],
    'shipping': ['shipping', 'container', 'port congestion', 'maritime', 'freight'],
    'warehousing': ['warehouse', 'warehousing', 'fulfillment', 'robotics'],
    'last_mile': ['last mile', 'delivery', 'logistics delivery'],
    'technology': ['logistics ai', 'supply chain ai', 'digital twin', 'logistics automation'],
}
QUERIES = ['logistics supply chain', 'maritime shipping freight', 'warehouse automation logistics']

def news():
    items = []
    for query in QUERIES:
        url = 'https://news.google.com/rss/search?q=' + quote(query + ' when:3d') + '&hl=en-US&gl=US&ceid=US:en'
        feed = feedparser.parse(requests.get(url, timeout=20).content)
        for entry in feed.entries:
            try:
                dt = parsedate_to_datetime(entry.published).astimezone(timezone.utc)
            except (ValueError, AttributeError, TypeError):
                continue
            if dt < datetime.now(timezone.utc) - timedelta(days=3):
                continue
            title = re.sub(r'<[^>]*>', '', entry.title)
            key = hashlib.sha256(entry.link.encode()).hexdigest()
            items.append({'title': title, 'url': entry.link, 'date': dt.isoformat(), 'id': key})
    return list({x['id']: x for x in items}.values())

def classify(title):
    t = title.lower()
    scores = {k: sum(1 for word in words if word in t) for k, words in TOPICS.items()}
    category = max(scores, key=scores.get)
    return category if scores[category] else None

def select_story(items, posted):
    classified = [(item, classify(item['title'])) for item in items if item['id'] not in posted]
    counts = {key: sum(cat == key for _, cat in classified) for key in TOPICS}
    ranked = [(counts[cat], item['date'], item, cat) for item, cat in classified if cat]
    ranked.sort(reverse=True)
    if not ranked:
        raise RuntimeError('No fresh, relevant, unpublished stories found.')
    return ranked[0][2], ranked[0][3], counts

def draft(item, category, counts):
    # This template does not invent facts not present in the headline.
    title = item['title'].rsplit(' - ', 1)[0]
    return (f'🚚 Logistics watch: {title}\n\n'
            f'Why it matters: This development could affect how logistics teams plan '
            f'capacity, manage operational risk, or evaluate costs. The precise impact '
            f'depends on the details of the reported event.\n\n'
            f'Our video illustrates the broader {category.replace("_", " ")} context; '
            f'it is not footage of the reported event.\n\n'
            f'Source: {item["url"]}\n\n'
            f'What would this mean for your operations?\n\n'
            f'#Logistics #SupplyChain #Transportation')

def headers():
    return {'Authorization': 'Bearer ' + os.environ['LINKEDIN_ACCESS_TOKEN'],
            'Linkedin-Version': os.getenv('LINKEDIN_VERSION', '202610'),
            'X-Restli-Protocol-Version': '2.0.0', 'Content-Type': 'application/json'}

def checked(response):
    response.raise_for_status()
    return response

def upload_video(path, owner):
    root = 'https://api.linkedin.com/rest/videos'
    size = path.stat().st_size
    if not (75000 <= size <= 500_000_000):
        raise ValueError('Video must be an MP4 between 75 KB and 500 MB.')
    init = checked(requests.post(root + '?action=initializeUpload', headers=headers(), json={
        'initializeUploadRequest': {'owner': owner, 'fileSizeBytes': size,
                                    'uploadCaptions': False, 'uploadThumbnail': False}}, timeout=30)).json()['value']
    part_ids = []
    with path.open('rb') as f:
        for part in init['uploadInstructions']:
            first, last = part['firstByte'], part['lastByte']
            f.seek(first)
            data = f.read(last - first + 1)
            response = checked(requests.put(part['uploadUrl'], data=data,
                                            headers={'Content-Type': 'application/octet-stream'}, timeout=120))
            part_id = response.headers.get('ETag')
            if not part_id:
                raise RuntimeError('Upload response missing ETag for video part.')
            part_ids.append(part_id.strip('"'))
    checked(requests.post(root + '?action=finalizeUpload', headers=headers(), json={
        'finalizeUploadRequest': {'video': init['video'], 'uploadToken': init.get('uploadToken', ''),
                                  'uploadedPartIds': part_ids}}, timeout=30))
    for _ in range(30):
        status = checked(requests.get(root + '/' + quote(init['video'], safe=''), headers=headers(), timeout=30)).json()
        state = status.get('status')
        if state == 'AVAILABLE':
            return init['video']
        if state in ('PROCESSING_FAILED', 'FAILED'):
            raise RuntimeError('Video processing failed: ' + str(status))
        time.sleep(10)
    raise TimeoutError('Video is still processing; do not retry publishing without checking status.')

def publish(text, video_urn, owner):
    payload = {'author': owner, 'commentary': text, 'visibility': 'PUBLIC',
               'distribution': {'feedDistribution': 'MAIN_FEED', 'targetEntities': [], 'thirdPartyDistributionChannels': []},
               'content': {'media': {'id': video_urn, 'title': 'Logistics industry context'}},
               'lifecycleState': 'PUBLISHED', 'isReshareDisabledByAuthor': False}
    response = checked(requests.post('https://api.linkedin.com/rest/posts', headers=headers(), json=payload, timeout=30))
    return response.headers.get('x-restli-id', 'published (post ID unavailable)')

def main():
    posted = json.loads(HISTORY.read_text()) if HISTORY.exists() else {}
    story, category, counts = select_story(news(), posted)
    video = VIDEO_DIR / (category + '.mp4')
    if not video.is_file():
        raise FileNotFoundError(f'Add a licensed context video: {video}')
    text = draft(story, category, counts)
    print('TREND COUNTS:', counts, '\nSTORY:', story['title'], '\nVIDEO:', video, '\n\nPOST:\n', text)
    if os.getenv('AUTO_PUBLISH', 'false').lower() != 'true':
        print('\nDRY RUN: nothing was published. Set AUTO_PUBLISH=true to publish.')
        return
    owner = os.environ['LINKEDIN_AUTHOR_URN']
    urn = upload_video(video, owner)
    post_id = publish(text, urn, owner)
    posted[story['id']] = {'url': story['url'], 'post_id': post_id, 'date': datetime.now(timezone.utc).isoformat()}
    HISTORY.write_text(json.dumps(posted, indent=2))
    print('PUBLISHED:', post_id)

if __name__ == '__main__':
    main()
