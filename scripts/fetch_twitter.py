#!/usr/bin/env python3
"""
Twitter KOL 预抓取脚本
20 KOL 并发抓取，输出 JSON

用法:
  python3 fetch_twitter.py YYYY-MM-DD [--log]

时间窗口: 前一天 08:00 CST → 当天 08:00 CST
输出: JSON 到 stdout
退出码: 0=成功, 1=参数错误, 2=ct0过期(403)
"""
import subprocess
import json
import sys
import os
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

CST = timezone(timedelta(hours=8))


def parse_bird_date(date_str):
    """解析 bird CLI 输出的日期，返回 aware UTC datetime"""
    formats = [
        '%a %b %d %H:%M:%S %z %Y',   # Mon Feb 16 19:50:40 +0000 2026
        '%a, %d %b %Y %H:%M:%S %z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except (ValueError, OverflowError):
            continue
    return None


def fetch_user_tweets(handle, start_utc, end_utc):
    """用 bird CLI 抓取单个 KOL 的推文"""
    try:
        result = subprocess.run(
            ['bird', 'search', f'from:{handle}', '-n', '10', '--json'],
            capture_output=True, text=True, timeout=20
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            if '403' in stderr or 'ct0' in stderr.lower():
                return [], 'ct0_expired'
            return [], f'error: {stderr[:100]}'

        tweets = []
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            # 尝试 plain 模式解析
            return fetch_user_tweets_plain(handle, start_utc, end_utc)

        if isinstance(data, list):
            for tweet in data:
                dt = None
                for date_field in ('createdAt', 'created_at', 'date', 'timestamp'):
                    if date_field in tweet:
                        dt = parse_bird_date(str(tweet[date_field]))
                        if dt:
                            break

                if not dt or not (start_utc <= dt < end_utc):
                    continue

                tweet_id = tweet.get('id') or tweet.get('tweet_id') or ''
                text = tweet.get('text') or tweet.get('full_text') or ''
                handle_from_tweet = tweet.get('author', {}).get('username', handle)
                is_reply = bool(tweet.get('inReplyToStatusId')
                                or tweet.get('in_reply_to_status_id')
                                or text.startswith('@'))

                tweets.append({
                    'handle': handle,
                    'text': text[:500],
                    'tweet_id': str(tweet_id),
                    'url': f"https://x.com/{handle}/status/{tweet_id}" if tweet_id else '',
                    'is_reply': is_reply,
                    'date': dt.strftime('%Y-%m-%d %H:%M UTC'),
                })
        return tweets, 'ok'
    except subprocess.TimeoutExpired:
        return [], 'timeout'
    except Exception as e:
        return [], str(e)[:100]


def fetch_user_tweets_plain(handle, start_utc, end_utc):
    """Fallback: 用 bird plain 模式抓取"""
    try:
        result = subprocess.run(
            ['bird', 'search', f'from:{handle}', '-n', '10', '--plain'],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode != 0:
            return [], f'plain_error: {result.stderr[:100]}'

        tweets = []
        current = {}
        for line in result.stdout.split('\n'):
            line = line.strip()
            if not line or line.startswith('─'):
                if current.get('text') and current.get('date'):
                    dt = parse_bird_date(current['date'])
                    if dt and start_utc <= dt < end_utc:
                        tweet_id = current.get('id', '')
                        is_reply = current.get('text', '').startswith('@')
                        tweets.append({
                            'handle': handle,
                            'text': current['text'][:500],
                            'tweet_id': str(tweet_id),
                            'url': current.get('url', ''),
                            'is_reply': is_reply,
                            'date': dt.strftime('%Y-%m-%d %H:%M UTC'),
                        })
                current = {}
                continue
            if line.startswith('date:'):
                current['date'] = line[5:].strip()
            elif line.startswith('url:'):
                current['url'] = line[4:].strip()
            elif line.startswith('id:'):
                current['id'] = line[3:].strip()
            elif not line.startswith('>') and not line.startswith('@'):
                current.setdefault('text', line)
        return tweets, 'ok'
    except Exception as e:
        return [], str(e)[:100]


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_twitter.py YYYY-MM-DD [--log]", file=sys.stderr)
        sys.exit(1)

    date_str = sys.argv[1]
    do_log = '--log' in sys.argv

    base_dir = "/Users/justin/Library/CloudStorage/Dropbox/CC/Projects/Daily News"
    kols_path = os.path.join(base_dir, "config/twitter_kols.json")
    log_dir = os.path.join(base_dir, "fetch_log")

    with open(kols_path) as f:
        kols_config = json.load(f)

    # 收集所有 handle
    all_handles = []
    for group, handles in kols_config.get('groups', {}).items():
        for h in handles:
            if h not in all_handles:
                all_handles.append(h)

    # 时间窗口: 前一天 08:00 CST → 当天 08:00 CST
    # = 前一天 00:00 UTC → 当天 00:00 UTC
    target = datetime.strptime(date_str, '%Y-%m-%d')
    start_utc = datetime(target.year, target.month, target.day, 0, 0, 0, tzinfo=timezone.utc) - timedelta(days=1)
    end_utc = datetime(target.year, target.month, target.day, 0, 0, 0, tzinfo=timezone.utc)

    print(f"📅 时间窗口 (UTC): {start_utc.strftime('%Y-%m-%d %H:%M')} → {end_utc.strftime('%Y-%m-%d %H:%M')}", file=sys.stderr)
    print(f"🐦 抓取 {len(all_handles)} 个 KOL...", file=sys.stderr)

    # 并发抓取
    all_tweets = []
    statuses = {}
    ct0_expired = False

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(fetch_user_tweets, h, start_utc, end_utc): h
            for h in all_handles
        }
        for future in as_completed(futures):
            handle = futures[future]
            tweets, status = future.result()
            statuses[handle] = {'count': len(tweets), 'status': status}
            all_tweets.extend(tweets)
            if status == 'ct0_expired':
                ct0_expired = True

    # 统计
    ok_count = sum(1 for s in statuses.values() if s['status'] == 'ok')
    original = sum(1 for t in all_tweets if not t.get('is_reply'))
    replies = sum(1 for t in all_tweets if t.get('is_reply'))

    print(f"✅ {ok_count}/{len(all_handles)} KOL 成功，{len(all_tweets)} 条推文（{original} 原创 + {replies} 回复）", file=sys.stderr)

    if ct0_expired:
        print("⚠️ ct0 过期！部分 KOL 获取失败（403）", file=sys.stderr)

    # 输出 JSON
    print(json.dumps(all_tweets, ensure_ascii=False, indent=2))

    # 写日志
    if do_log:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{date_str}-twitter.json")
        log_data = {
            'date': date_str,
            'window_utc': f"{start_utc.isoformat()} → {end_utc.isoformat()}",
            'total_tweets': len(all_tweets),
            'original': original,
            'replies': replies,
            'kol_statuses': statuses,
        }
        with open(log_file, 'w') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        print(f"📝 日志已写入 {log_file}", file=sys.stderr)

    # ct0 过期时退出码 2
    if ct0_expired:
        sys.exit(2)


if __name__ == '__main__':
    main()
