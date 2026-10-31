# Logistics Trend → LinkedIn Video Publisher

A Python automation that discovers recent logistics headlines via Google News RSS, scores recurring logistics themes, selects a relevant **licensed MP4**, generates a conservative contextual LinkedIn caption, and optionally uploads/publishes the post through LinkedIn's official APIs. Includes GitHub Actions for scheduled execution and tests.

> **Default mode is a preview.** Publishing only occurs when `AUTO_PUBLISH=true`, and requires LinkedIn API permissions and credentials. RSS topic frequency is a trend *proxy*, not an official LinkedIn trending feed. The script does not use a generative AI model or create video footage.

## Repository structure

```text
.
├── .github/workflows/
│   ├── publish.yml       # Weekday schedule + manual launch
│   └── tests.yml         # CI unit tests
├── videos/               # Your licensed MP4 video library
├── tests/test_bot.py
├── bot.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Local setup

Requires Python 3.10+.

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env    # On Windows, copy .env.example .env
python bot.py
```

Copy your own appropriately licensed video clips to `videos/`, using the filenames in `videos/README.md`. The clip matching the selected topic must be available or the program will stop before posting.

For publication, fill in `.env` and set `AUTO_PUBLISH=true`. Preview the content and ensure it is accurate before enabling automatic publication. **Never commit your `.env` or access token.**

## LinkedIn access

Create a LinkedIn developer app and acquire a valid OAuth token authorized to publish on the intended identity. Personal posting generally requires `w_member_social`; organization posting requires approved organization access and permissions. Set `LINKEDIN_AUTHOR_URN` to `urn:li:person:<ID>` or `urn:li:organization:<ID>` accordingly. LinkedIn restricts API products and may require app review. Use a currently supported `LINKEDIN_VERSION` (YYYYMM) and verify the [Posts API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api) and [Videos API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/videos-api) documentation for your app. Tokens expire and are not automatically refreshed by this project.

## Run on GitHub Actions

1. Create a **private GitHub repository** and push this directory (instructions below). Add the authorized MP4 clips to the `videos/` directory (large videos may require an external storage integration).
2. Go to **Settings → Secrets and variables → Actions → Secrets**. Create `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_AUTHOR_URN`.
3. In **Variables**, create `LINKEDIN_VERSION` with a currently supported YYYYMM version and `AUTO_PUBLISH` set to `false` for preview, or `true` only after successful tests and review.
4. Go to **Actions → Publish logistics update to LinkedIn → Run workflow** for a manual test.
5. The schedule runs Monday–Friday at **14:00 UTC (09:00 Lima)**. GitHub scheduled workflows can run late or be skipped under load. Scheduled workflows run from the default branch and may be disabled after prolonged inactivity in public repositories.

**History:** `posted.json` is cached between successful scheduled runs using GitHub Actions cache, so already posted headlines are normally skipped. Caches can be evicted or lost: this is *best-effort* duplicate prevention, not durable exactly-once posting. For production, use a persistent store or query your own published posts before retrying ambiguous API failures. Upload success followed by a dropped response can also cause a duplicate; check the LinkedIn feed before retrying.

**Preview caveat:** You must still provide at least one matching category MP4 for the selected story. In preview mode, the bot never uploads media or calls the publishing API.


## Testing

```bash
pip install pytest
python -m pytest -q
```

## Operational safeguards and limitations

- Only own or licensed contextual video content may be used; the caption explicitly states it is not footage of the news event.
- Article data comes from Google News RSS headlines, not full article verification. Generated posts are cautious templates, not independently fact-checked reporting.
- A matching video may be missing, RSS may be unavailable, and platform API endpoints/permissions can change; these cause the run to fail rather than publish unsupported content.
- Posts are public when enabled. Verify your access, facts, source, and branding before automated publishing.
- Cache state is not a database. Use a persistent external store for reliability across parallel systems and cache eviction.
