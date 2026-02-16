#!/usr/bin/env python3
"""
轻量级RSS抓取 - 快速版
"""
import feedparser
import json
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request

def fetch_single_feed(args):
    name, url, category, start_time, end_time = args
    try:
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:10]:  # 限制每源数量
            pub = entry.get('published') or entry.get('updated') or entry.get('pubDate')
            if pub:
                try:
                    # 尝试解析日期
                    for fmt in ['%Y-%m-%dT%H:%M:%S%z', '%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%dT%H:%M:%SZ']:
                        try:
                            dt = datetime.strptime(pub.replace('Z', '+0000'), fmt)
                            dt = dt.replace(tzinfo=None)
                            if start_time <= dt < end_time:
                                articles.append({
                                    'title': entry.get('title', '无标题'),
                                    'link': entry.get('link', ''),
                                    'summary': (entry.get('summary') or entry.get('description') or '')[:400],
                                    'source': name,
                                    'date': dt.strftime('%Y-%m-%d %H:%M')
                                })
                            break
                        except:
                            continue
                except:
                    pass
        return articles
    except Exception as e:
        return []

def fetch_rss_fast(config_path, target_date):
    with open(config_path) as f:
        sources = json.load(f)
    
    start_time = target_date.replace(hour=8, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(days=1)
    
    # 选择关键源
    priority_sources = [s for s in sources if s.get('category') in ['AI', 'Startup', 'VC']][:15]
    other_sources = [s for s in sources if s not in priority_sources][:15]
    selected = priority_sources + other_sources
    
    args_list = [(s['name'], s['url'], s.get('category', ''), start_time, end_time) for s in selected]
    
    all_articles = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_single_feed, args): args for args in args_list}
        for future in as_completed(futures):
            articles = future.result()
            all_articles.extend(articles)
    
    return all_articles

if __name__ == '__main__':
    date_str = sys.argv[1]
    target = datetime.strptime(date_str, '%Y-%m-%d')
    base_dir = "/Users/justin/Library/CloudStorage/Dropbox/CC/Projects/Daily News"
    articles = fetch_rss_fast(f"{base_dir}/config/rss_sources.json", target)
    print(json.dumps(articles, ensure_ascii=False))
