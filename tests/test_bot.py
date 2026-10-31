from datetime import datetime, timezone

from bot import classify, draft, select_story


def test_classify_shipping():
    assert classify('Maritime shipping faces delays') == 'shipping'


def test_unrelated_topic_is_skipped():
    assert classify('A local restaurant opens') is None


def test_deduplicates_published_urls():
    stories = [
        {'id': 'a', 'title': 'Maritime shipping delays', 'date': '2026-10-31T10:00:00+00:00', 'url': 'https://example.com/a'},
        {'id': 'b', 'title': 'Warehouse robotics upgrade', 'date': '2026-10-31T11:00:00+00:00', 'url': 'https://example.com/b'},
    ]
    chosen, category, _ = select_story(stories, {'a': {}})
    assert chosen['id'] == 'b'
    assert category == 'warehousing'


def test_draft_links_source_and_labels_context_video():
    story = {'title': 'Maritime shipping report - Example News', 'url': 'https://example.com/story'}
    post = draft(story, 'shipping', {})
    assert story['url'] in post
    assert 'not footage of the reported event' in post
