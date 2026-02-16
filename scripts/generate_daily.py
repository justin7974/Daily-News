#!/usr/bin/env python3
"""
生成Daily News日报 - 优化版
"""

import feedparser
import json
import subprocess
import sys
from datetime import datetime, timedelta
import os
import re

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def parse_date(date_str):
    if not date_str:
        return None
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    return None

def fetch_rss_articles(config_path, target_date):
    """抓取RSS文章"""
    sources = load_json(config_path)
    start_time = target_date.replace(hour=8, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(days=1)
    
    articles = []
    for source in sources[:20]:  # 限制源数量
        try:
            feed = feedparser.parse(source['url'])
            if not hasattr(feed, 'entries'):
                continue
            
            for entry in feed.entries[:5]:  # 每个源最多5篇
                published = parse_date(entry.get('published') or entry.get('pubDate') or entry.get('updated'))
                if published:
                    if published.tzinfo:
                        published = published.replace(tzinfo=None)
                    if start_time <= published < end_time:
                        articles.append({
                            'title': entry.get('title', '无标题'),
                            'link': entry.get('link', ''),
                            'summary': (entry.get('summary') or entry.get('description') or '')[:400],
                            'source': source['name'],
                            'category': source.get('category', ''),
                        })
        except Exception as e:
            pass
    
    return articles

def fetch_twitter_batch(handles, target_date):
    """批量抓取Twitter"""
    start_time = target_date.replace(hour=8, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(days=1)
    
    all_tweets = []
    for handle in handles:
        try:
            result = subprocess.run(
                ['bird', 'search', f'from:{handle}', '-n', '5', '--plain'],
                capture_output=True, text=True, timeout=20
            )
            if result.returncode != 0:
                continue
            
            lines = result.stdout.split('\n')
            current = {}
            for line in lines:
                line = line.strip()
                if not line or line.startswith('─'):
                    if current.get('text') and 'date' in current:
                        try:
                            tweet_date = datetime.strptime(current['date'], '%a %b %d %H:%M:%S %z %Y')
                            tweet_date = tweet_date.replace(tzinfo=None)
                            if start_time <= tweet_date < end_time:
                                current['handle'] = handle
                                all_tweets.append(current)
                        except:
                            pass
                    current = {}
                    continue
                
                if line.startswith('date:'):
                    current['date'] = line[5:].strip()
                elif line.startswith('url:'):
                    current['url'] = line[4:].strip()
                elif line and not line.startswith('@') and not line.startswith('>'):
                    current['text'] = line[:350]
        except:
            pass
    
    return all_tweets

def generate_markdown(date_str, articles, tweets):
    lines = [f"# Daily News | {date_str}", ""]
    
    # RSS
    lines.extend(["## RSS 日报", ""])
    
    # 重点推荐
    featured = articles[:6] if len(articles) >= 6 else articles
    if featured:
        lines.extend(["### 🔥 重点推荐", ""])
        for i, a in enumerate(featured, 1):
            lines.append(f"**{i}. {a['title']}** ({a['source']})")
            lines.append(a['link'])
            lines.append("")
            if a.get('summary'):
                summary = a['summary'].replace('\n', ' ')[:250]
                lines.append(f"{summary}...")
                lines.append("")
            lines.append("🦐点评：值得关注的技术动态")
            lines.append("")
    
    # 其他新闻
    others = articles[6:12]
    if others:
        lines.extend(["### 📌 其他新闻", ""])
        for a in others:
            lines.append(f"**{a['title']}** ({a['source']})")
            lines.append(a['link'])
            lines.append("")
    
    # Twitter
    lines.extend(["## Twitter KOL 日报", ""])
    
    # 分类推文
    ai_handles = ['karpathy', 'emollick', 'Hesamation', 'vasuman', 'EXM7777', 'kloss_xyz']
    startup_handles = ['gregisenberg', 'levelsio', 'marclou', 'MengTo', 'rileybrown']
    
    ai_tweets = [t for t in tweets if t['handle'] in ai_handles][:5]
    startup_tweets = [t for t in tweets if t['handle'] in startup_handles][:5]
    other_tweets = [t for t in tweets if t['handle'] not in ai_handles + startup_handles][:5]
    
    if ai_tweets:
        lines.extend(["### 🧠 AI 技术前沿", ""])
        for t in ai_tweets:
            lines.append(f"**@{t['handle']}**")
            lines.append(f"> {t.get('text', '')}")
            if t.get('url'):
                lines.append(f"🔗 {t['url']}")
            lines.append("")
    
    if startup_tweets:
        lines.extend(["### 🚀 创业动态", ""])
        for t in startup_tweets:
            lines.append(f"**@{t['handle']}**")
            lines.append(f"> {t.get('text', '')}")
            if t.get('url'):
                lines.append(f"🔗 {t['url']}")
            lines.append("")
    
    if other_tweets:
        lines.extend(["### 💬 观点与洞察", ""])
        for t in other_tweets:
            lines.append(f"**@{t['handle']}**")
            lines.append(f"> {t.get('text', '')}")
            if t.get('url'):
                lines.append(f"🔗 {t['url']}")
            lines.append("")
    
    lines.append("*Generated by 小虾 🦐*")
    return '\n'.join(lines)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 generate_daily.py YYYY-MM-DD")
        sys.exit(1)
    
    date_str = sys.argv[1]
    target_date = datetime.strptime(date_str, '%Y-%m-%d')
    
    base_dir = "/Users/justin/Library/CloudStorage/Dropbox/CC/Projects/Daily News"
    
    print(f"📅 生成 {date_str} 日报...", file=sys.stderr)
    
    # 抓取RSS
    print("🔄 RSS...", file=sys.stderr)
    articles = fetch_rss_articles(f"{base_dir}/config/rss_sources.json", target_date)
    print(f"   {len(articles)}篇", file=sys.stderr)
    
    # 抓取Twitter
    print("🔄 Twitter...", file=sys.stderr)
    kols = load_json(f"{base_dir}/config/twitter_kols.json")
    all_handles = []
    for group in kols.get('groups', {}).values():
        all_handles.extend(group)
    tweets = fetch_twitter_batch(all_handles, target_date)
    print(f"   {len(tweets)}条", file=sys.stderr)
    
    # 生成
    print("📝 Markdown...", file=sys.stderr)
    md = generate_markdown(date_str, articles, tweets)
    
    output_path = f"{base_dir}/content/{date_str}.md"
    with open(output_path, 'w') as f:
        f.write(md)
    
    print(f"✅ {output_path}", file=sys.stderr)
    print(json.dumps({"articles": len(articles), "tweets": len(tweets)}))
