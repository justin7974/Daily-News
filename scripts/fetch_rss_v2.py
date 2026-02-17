#!/usr/bin/env python3
"""
RSS 预抓取脚本 v2
108 源全量并发抓取 + 规则过滤 + tier 排序

用法:
  python3 fetch_rss_v2.py YYYY-MM-DD [--log]

时间窗口: 前一天 08:00 CST → 当天 08:00 CST（即 前一天 00:00 UTC → 当天 00:00 UTC）
输出: JSON 到 stdout
"""
import feedparser
import json
import sys
import os
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from urllib.parse import urlparse

# 北京时间 = UTC+8
CST = timezone(timedelta(hours=8))

CHINA_AI_KEYWORDS = [
    'AI', '人工智能', '大模型', 'LLM', 'GPT', 'Claude', 'Gemini',
    'DeepSeek', '芯片', 'GPU', 'SaaS', '机器人', 'robot',
    '融资', '投资', '估值', 'VC', '创业', '独角兽',
    'AGI', 'Agent', '自动驾驶', '生成式',
]


def parse_entry_date(entry):
    """解析 RSS entry 的发布时间，返回 aware UTC datetime"""
    raw = (entry.get('published') or entry.get('updated')
           or entry.get('pubDate') or entry.get('created'))
    if not raw:
        return None

    # feedparser 已经解析好的 struct_time
    for field in ('published_parsed', 'updated_parsed'):
        parsed = entry.get(field)
        if parsed:
            try:
                from calendar import timegm
                ts = timegm(parsed)
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                pass

    # 手动解析常见格式
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%d %H:%M:%S%z',
        '%Y-%m-%d %H:%M:%S',
    ]
    for fmt in formats:
        try:
            s = raw.strip()
            if fmt.endswith('Z'):
                s = s.replace('+00:00', 'Z').replace('+0000', 'Z')
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                # 无时区信息的假设为 UTC
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except (ValueError, OverflowError):
            continue
    return None


def needs_keyword_filter(source_name):
    """China-AI/VC 源需要关键词过滤"""
    china_sources = ['36kr', '36氪', '量子位', '虎嗅', 'InfoQ', '雷锋网']
    return any(k.lower() in source_name.lower() for k in china_sources)


def matches_keywords(title, summary):
    text = (title + ' ' + summary).lower()
    return any(kw.lower() in text for kw in CHINA_AI_KEYWORDS)


def fetch_single_feed(args):
    """抓取单个 RSS 源，返回时间窗口内的文章列表"""
    name, url, category, tier, start_utc, end_utc = args
    try:
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:15]:
            dt = parse_entry_date(entry)
            if not dt:
                continue
            if not (start_utc <= dt < end_utc):
                continue

            title = entry.get('title', '无标题').strip()
            summary = (entry.get('summary') or entry.get('description') or '')[:500]
            link = entry.get('link', '')

            # China 源关键词过滤
            if needs_keyword_filter(name) and not matches_keywords(title, summary):
                continue

            articles.append({
                'title': title,
                'link': link,
                'summary': summary,
                'source': name,
                'category': category,
                'tier': tier,
                'date': dt.strftime('%Y-%m-%d %H:%M UTC'),
            })
        return articles
    except Exception as e:
        print(f"⚠️ {name}: {e}", file=sys.stderr)
        return []


def load_previous_links(log_dir, target_date_str):
    """读取前一天 fetch log，排除重复文章"""
    prev_date = datetime.strptime(target_date_str, '%Y-%m-%d') - timedelta(days=1)
    prev_file = os.path.join(log_dir, f"{prev_date.strftime('%Y-%m-%d')}.json")
    if not os.path.exists(prev_file):
        return set()
    try:
        with open(prev_file) as f:
            data = json.load(f)
        return set(data.get('article_links', []))
    except Exception:
        return set()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_rss_v2.py YYYY-MM-DD [--log]", file=sys.stderr)
        sys.exit(1)

    date_str = sys.argv[1]
    do_log = '--log' in sys.argv

    base_dir = "/Users/justin/Library/CloudStorage/Dropbox/CC/Projects/Daily News"
    config_path = os.path.join(base_dir, "config/rss_sources.json")
    log_dir = os.path.join(base_dir, "fetch_log")

    with open(config_path) as f:
        sources = json.load(f)

    # 时间窗口: 前一天 08:00 CST → 当天 08:00 CST
    # = 前一天 00:00 UTC → 当天 00:00 UTC
    target = datetime.strptime(date_str, '%Y-%m-%d')
    start_utc = datetime(target.year, target.month, target.day, 0, 0, 0, tzinfo=timezone.utc) - timedelta(days=1)
    end_utc = datetime(target.year, target.month, target.day, 0, 0, 0, tzinfo=timezone.utc)

    print(f"📅 时间窗口 (UTC): {start_utc.strftime('%Y-%m-%d %H:%M')} → {end_utc.strftime('%Y-%m-%d %H:%M')}", file=sys.stderr)
    print(f"📅 时间窗口 (CST): {(start_utc+timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')} → {(end_utc+timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')}", file=sys.stderr)
    print(f"📡 抓取 {len(sources)} 个源...", file=sys.stderr)

    # 跨日去重
    prev_links = load_previous_links(log_dir, date_str)

    # 并发抓取
    args_list = [
        (s['name'], s['url'], s.get('category', ''), s.get('tier', 3), start_utc, end_utc)
        for s in sources
    ]

    all_articles = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_single_feed, a): a[0] for a in args_list}
        for future in as_completed(futures):
            result = future.result()
            all_articles.extend(result)

    # 去重: URL 去重 + 跨日去重
    seen = set()
    deduped = []
    for a in all_articles:
        link = a['link']
        if link in seen or link in prev_links:
            continue
        seen.add(link)
        deduped.append(a)

    # 同域名限制 ≤ 5 篇
    domain_count = defaultdict(int)
    filtered = []
    for a in deduped:
        domain = urlparse(a['link']).netloc
        if domain_count[domain] >= 5:
            continue
        domain_count[domain] += 1
        filtered.append(a)

    # 按 tier 排序 (tier 1 优先)
    filtered.sort(key=lambda x: (x.get('tier', 3), x['source']))

    print(f"✅ {len(filtered)} 篇候选文章（去重前 {len(all_articles)}，跨日排除 {len(prev_links)} 链接）", file=sys.stderr)

    # 输出 JSON
    print(json.dumps(filtered, ensure_ascii=False, indent=2))

    # 写日志
    if do_log:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{date_str}.json")
        log_data = {
            'date': date_str,
            'window_utc': f"{start_utc.isoformat()} → {end_utc.isoformat()}",
            'total_fetched': len(all_articles),
            'after_dedup': len(filtered),
            'article_links': [a['link'] for a in filtered],
        }
        with open(log_file, 'w') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        print(f"📝 日志已写入 {log_file}", file=sys.stderr)


if __name__ == '__main__':
    main()
