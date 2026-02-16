#!/usr/bin/env python3
"""
完整日报生成器 - 优化版
"""
import feedparser
import json
import subprocess
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

def fetch_single_feed(args):
    name, url, category, start_time, end_time = args
    try:
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:10]:
            pub = entry.get('published') or entry.get('updated') or entry.get('pubDate')
            if pub:
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
                                'date': dt.strftime('%Y-%m-%d %H:%M'),
                                'category': category
                            })
                        break
                    except:
                        continue
        return articles
    except:
        return []

def fetch_rss(config_path, target_date):
    with open(config_path) as f:
        sources = json.load(f)
    
    start_time = target_date.replace(hour=8, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(days=1)
    
    # 选择关键源
    priority = [s for s in sources if s.get('category') in ['AI', 'Startup', 'VC']][:15]
    others = [s for s in sources if s not in priority][:15]
    selected = priority + others
    
    args_list = [(s['name'], s['url'], s.get('category', ''), start_time, end_time) for s in selected]
    
    all_articles = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_single_feed, args) for args in args_list]
        for future in futures:
            all_articles.extend(future.result())
    
    return sorted(all_articles, key=lambda x: x.get('category', '') == 'AI', reverse=True)

def fetch_twitter_for_user(handle, target_date):
    start_time = target_date.replace(hour=8, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(days=1)
    
    try:
        result = subprocess.run(['bird', 'search', f'from:{handle}', '-n', '5', '--plain'],
                              capture_output=True, text=True, timeout=20)
        if result.returncode != 0:
            return []
        
        tweets = []
        lines = result.stdout.split('\n')
        current = {}
        for line in lines:
            line = line.strip()
            if not line or line.startswith('─'):
                if current.get('text') and 'date' in current:
                    try:
                        dt = datetime.strptime(current['date'], '%a %b %d %H:%M:%S %z %Y')
                        dt = dt.replace(tzinfo=None)
                        if start_time <= dt < end_time:
                            tweets.append({
                                'handle': handle,
                                'text': current['text'][:350],
                                'url': current.get('url', ''),
                                'date': dt.strftime('%m-%d %H:%M')
                            })
                    except:
                        pass
                current = {}
                continue
            if line.startswith('date:'):
                current['date'] = line[5:].strip()
            elif line.startswith('url:'):
                current['url'] = line[4:].strip()
            elif line and not line.startswith('@') and not line.startswith('>'):
                current['text'] = line
        return tweets
    except:
        return []

def fetch_twitter(kols_config, target_date):
    with open(kols_config) as f:
        kols = json.load(f)
    
    all_handles = []
    for group, handles in kols.get('groups', {}).items():
        all_handles.extend(handles)
    
    all_tweets = []
    # 串行抓取Twitter，避免API限制
    for handle in all_handles[:15]:  # 限制数量
        tweets = fetch_twitter_for_user(handle, target_date)
        all_tweets.extend(tweets)
    
    return all_tweets

def generate_markdown(date_str, articles, tweets):
    lines = [f"# Daily News | {date_str}", ""]
    
    # RSS部分
    lines.extend(["## RSS 日报", ""])
    
    # 重点推荐（至少5篇）
    ai_articles = [a for a in articles if a.get('category') in ['AI', 'Startup', 'VC']]
    other_articles = [a for a in articles if a not in ai_articles]
    featured = (ai_articles + other_articles)[:6]
    
    if featured:
        lines.extend(["### 🔥 重点推荐", ""])
        for i, a in enumerate(featured, 1):
            lines.append(f"**{i}. {a['title']}** ({a['source']})")
            lines.append(a['link'])
            lines.append("")
            if a.get('summary'):
                summary = a['summary'].replace('\n', ' ')[:280]
                lines.append(f"{summary}...")
                lines.append("")
            lines.append("🦐点评：值得关注的技术/行业动态")
            lines.append("")
    
    # 其他新闻
    others = [a for a in articles if a not in featured][:8]
    if others:
        lines.extend(["### 📌 其他新闻", ""])
        for a in others:
            lines.append(f"**{a['title']}** ({a['source']})")
            lines.append(a['link'])
            lines.append("")
    
    # Twitter部分
    lines.extend(["## Twitter KOL 日报", ""])
    
    # 分类
    ai_handles = ['karpathy', 'emollick', 'Hesamation', 'vasuman', 'EXM7777', 'kloss_xyz', 'godofprompt']
    startup_handles = ['gregisenberg', 'levelsio', 'marclou', 'MengTo', 'rileybrown', 'corbin_braun', 'jackfriks']
    
    ai_tweets = [t for t in tweets if t['handle'] in ai_handles][:6]
    startup_tweets = [t for t in tweets if t['handle'] in startup_handles][:5]
    insight_tweets = [t for t in tweets if t['handle'] not in ai_handles + startup_handles][:5]
    
    if ai_tweets:
        lines.extend(["### 🧠 AI 技术前沿", ""])
        for t in ai_tweets:
            lines.append(f"**@{t['handle']}** ({t.get('date', '')})")
            lines.append(f"> {t['text']}")
            if t.get('url'):
                lines.append(f"🔗 {t['url']}")
            lines.append("")
    
    if startup_tweets:
        lines.extend(["### 🚀 创业动态", ""])
        for t in startup_tweets:
            lines.append(f"**@{t['handle']}** ({t.get('date', '')})")
            lines.append(f"> {t['text']}")
            if t.get('url'):
                lines.append(f"🔗 {t['url']}")
            lines.append("")
    
    if insight_tweets:
        lines.extend(["### 💬 观点与洞察", ""])
        for t in insight_tweets:
            lines.append(f"**@{t['handle']}** ({t.get('date', '')})")
            lines.append(f"> {t['text']}")
            if t.get('url'):
                lines.append(f"🔗 {t['url']}")
            lines.append("")
    
    lines.append("*Generated by 小虾 🦐*")
    return '\n'.join(lines)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 generate.py YYYY-MM-DD")
        sys.exit(1)
    
    date_str = sys.argv[1]
    target = datetime.strptime(date_str, '%Y-%m-%d')
    base = "/Users/justin/Library/CloudStorage/Dropbox/CC/Projects/Daily News"
    
    print(f"📅 {date_str}: RSS...", file=sys.stderr)
    articles = fetch_rss(f"{base}/config/rss_sources.json", target)
    print(f"   {len(articles)} articles", file=sys.stderr)
    
    print(f"📅 {date_str}: Twitter...", file=sys.stderr)
    tweets = fetch_twitter(f"{base}/config/twitter_kols.json", target)
    print(f"   {len(tweets)} tweets", file=sys.stderr)
    
    md = generate_markdown(date_str, articles, tweets)
    
    out_path = f"{base}/content/{date_str}.md"
    with open(out_path, 'w') as f:
        f.write(md)
    
    result = {"date": date_str, "articles": len(articles), "tweets": len(tweets), "path": out_path}
    print(json.dumps(result))
