#!/usr/bin/env python3
"""
RSS抓取脚本 - 用于Daily News项目
抓取指定日期范围内的RSS文章
"""

import feedparser
import json
import sys
from datetime import datetime, timedelta
import time

def load_rss_sources(config_path):
    with open(config_path, 'r') as f:
        return json.load(f)

def parse_date(date_str):
    """解析各种日期格式"""
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%d %H:%M:%S',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    return None

def fetch_feed(url, name):
    """抓取单个RSS源"""
    try:
        import socket
        # 设置超时
        socket.setdefaulttimeout(15)
        feed = feedparser.parse(url, timeout=15)
        if feed.bozo:
            print(f"⚠️ {name}: 解析警告", file=sys.stderr)
        return feed
    except Exception as e:
        print(f"❌ {name}: 抓取失败 - {e}", file=sys.stderr)
        return None

def is_in_date_range(entry, start_date, end_date):
    """检查文章是否在指定日期范围内"""
    published = None
    
    # 尝试各种日期字段
    for field in ['published', 'pubDate', 'updated', 'created']:
        if hasattr(entry, field):
            date_str = getattr(entry, field)
            if date_str:
                published = parse_date(date_str)
                if published:
                    break
    
    if not published:
        return False
    
    # 转换为无时区 aware 进行比较
    if published.tzinfo:
        published = published.replace(tzinfo=None)
    
    return start_date <= published <= end_date

def fetch_all_rss(config_path, target_date):
    """
    抓取所有RSS源，返回指定日期范围的文章
    target_date: datetime对象，抓取当天08:00到次日08:00的文章
    """
    sources = load_rss_sources(config_path)
    
    # 计算时间范围：当天08:00到次日08:00
    start_time = target_date.replace(hour=8, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(days=1)
    
    print(f"📅 抓取日期范围: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}")
    
    all_articles = []
    
    for source in sources:
        name = source['name']
        url = source['url']
        category = source.get('category', '')
        
        print(f"🔄 正在抓取: {name}...", file=sys.stderr)
        feed = fetch_feed(url, name)
        
        if not feed or not hasattr(feed, 'entries'):
            print(f"⚠️ {name}: 无内容", file=sys.stderr)
            continue
        
        for entry in feed.entries:
            if is_in_date_range(entry, start_time, end_time):
                article = {
                    'title': entry.get('title', '无标题'),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', entry.get('description', '')),
                    'published': entry.get('published', entry.get('pubDate', '')),
                    'source': name,
                    'category': category,
                    'author': entry.get('author', '')
                }
                all_articles.append(article)
        
        time.sleep(0.5)  # 避免请求过快
    
    return all_articles

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 fetch_rss.py <config_path> <YYYY-MM-DD>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    date_str = sys.argv[2]
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        print(f"❌ 日期格式错误: {date_str}")
        sys.exit(1)
    
    articles = fetch_all_rss(config_path, target_date)
    print(json.dumps(articles, ensure_ascii=False, indent=2))
