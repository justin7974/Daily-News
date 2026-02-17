#!/usr/bin/env python3
"""
微信公众号预抓取脚本
直接读取本地 we-mp-rss SQLite 数据库，输出 JSON 到 stdout

用法:
  python3 fetch_wechat.py YYYY-MM-DD [--log]

时间窗口: 前一天 08:00 CST → 当天 08:00 CST
输出: JSON 到 stdout（含 title, link, mp_name, summary, content）
"""
import json
import re
import sqlite3
import sys
import os
from datetime import datetime, timedelta, timezone

# 北京时间 = UTC+8
CST = timezone(timedelta(hours=8))

DB_PATH = os.path.expanduser(
    "~/Library/CloudStorage/Dropbox/CC/Projects/we-mp-rss/data/db.db"
)

# ===== PR/软文过滤 =====

# 标题中出现这些关键词 → 大概率是 PR 软文或低价值内容，直接过滤
TITLE_BLACKLIST = [
    r'送\s*\d+\s*条提示词',    # "送 200 条提示词！"
    r'小白也能',               # 教程引流
    r'极简教程',               # 教程引流
    r'手把手教你',             # 教程引流
    r'免费领取',
    r'限时免费',
    r'优惠券',
    r'折扣码',
    r'抽奖',
    r'转发.*抽',
    r'赠送.*名额',
    r'扫码.*领',
    r'加群',
    r'星球',                   # 知识星球引流
    r'知识星球',
]

# 正文中出现这些特征 → 标记为疑似 PR（不直接过滤，标记让 LLM 判断）
CONTENT_PR_SIGNALS = [
    r'本文由.*提供',
    r'本文系.*投稿',
    r'广告|推广|赞助',
    r'点击阅读原文.*购买',
    r'扫码.*购买',
    r'优惠价|限时特价|立即抢购',
    r'品牌合作|商务合作',
]


def is_title_blacklisted(title):
    """标题命中黑名单 → 直接过滤"""
    for pattern in TITLE_BLACKLIST:
        if re.search(pattern, title):
            return True
    return False


def count_pr_signals(content):
    """统计正文中 PR 信号数量"""
    if not content:
        return 0
    count = 0
    for pattern in CONTENT_PR_SIGNALS:
        if re.search(pattern, content[:3000]):  # 只检查前 3000 字
            count += 1
    return count


def is_short_fragment(title, content):
    """检测朋友圈式碎片内容（title 很长像正文、没有实际 content）"""
    # title 超过 80 字且没有全文 → 大概率是朋友圈/转发碎片
    if len(title) > 80 and (not content or len(content) < 100):
        return True
    return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_wechat.py YYYY-MM-DD [--log]", file=sys.stderr)
        sys.exit(1)

    date_str = sys.argv[1]
    do_log = '--log' in sys.argv

    base_dir = "/Users/justin/Library/CloudStorage/Dropbox/CC/Projects/Daily News"
    log_dir = os.path.join(base_dir, "fetch_log")

    if not os.path.exists(DB_PATH):
        print(f"❌ 数据库不存在: {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    # 时间窗口: 前一天 08:00 CST → 当天 08:00 CST
    target = datetime.strptime(date_str, '%Y-%m-%d')
    start_cst = datetime(target.year, target.month, target.day, 8, 0, 0, tzinfo=CST) - timedelta(days=1)
    end_cst = datetime(target.year, target.month, target.day, 8, 0, 0, tzinfo=CST)

    # 转为 UTC 时间戳（秒）
    start_ts = int(start_cst.timestamp())
    end_ts = int(end_cst.timestamp())

    print(f"📅 时间窗口 (CST): {start_cst.strftime('%Y-%m-%d %H:%M')} → {end_cst.strftime('%Y-%m-%d %H:%M')}", file=sys.stderr)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 查询文章 + 公众号名称
    # we-mp-rss 表结构:
    #   articles: id, mp_id, title, url, description, content, publish_time, ...
    #   feeds: id, mp_name, ...
    # publish_time 是 Unix 时间戳（秒）
    query = """
        SELECT
            a.title,
            a.url,
            a.content,
            a.description,
            a.publish_time,
            f.mp_name
        FROM articles a
        JOIN feeds f ON a.mp_id = f.id
        WHERE a.publish_time >= ? AND a.publish_time < ?
        ORDER BY a.publish_time DESC
    """

    rows = conn.execute(query, (start_ts, end_ts)).fetchall()
    conn.close()

    articles = []
    filtered_count = 0
    for row in rows:
        title = (row['title'] or '').strip()
        url = (row['url'] or '').strip()
        content = (row['content'] or '').strip()
        description = (row['description'] or '').strip()
        mp_name = (row['mp_name'] or '').strip()
        publish_time = row['publish_time']

        # === 过滤层 ===

        # 1. 标题黑名单 → 直接跳过
        if is_title_blacklisted(title):
            print(f"  ⛔ 标题过滤: [{mp_name}] {title[:50]}", file=sys.stderr)
            filtered_count += 1
            continue

        # 2. 朋友圈碎片内容 → 直接跳过
        if is_short_fragment(title, content):
            print(f"  ⛔ 碎片过滤: [{mp_name}] {title[:50]}", file=sys.stderr)
            filtered_count += 1
            continue

        # 格式化时间
        if publish_time:
            dt = datetime.fromtimestamp(publish_time, tz=CST)
            pub_str = dt.strftime('%Y-%m-%d %H:%M CST')
        else:
            pub_str = ''

        has_content = bool(content and len(content) > 100)

        # 3. PR 信号检测 → 标记但不过滤（留给 LLM 最终判断）
        pr_signals = count_pr_signals(content)

        # summary 优先用全文截取，无全文则用 description
        summary_text = content[:500] if has_content else description[:500]

        article = {
            'title': title,
            'link': url,
            'mp_name': mp_name,
            'summary': summary_text,
            'has_full_content': has_content,
            'content_length': len(content) if content else 0,
            'publish_time': pub_str,
        }

        # 有 PR 信号时标记，提醒 LLM 注意
        if pr_signals > 0:
            article['pr_warning'] = f"检测到 {pr_signals} 个疑似 PR/推广信号"

        articles.append(article)

    total = len(rows)
    kept = len(articles)
    print(f"✅ {kept} 篇文章（过滤 {filtered_count} 篇，{sum(1 for a in articles if a['has_full_content'])} 篇有全文）", file=sys.stderr)
    if filtered_count > 0:
        print(f"  📋 过滤原因: 标题黑名单/朋友圈碎片", file=sys.stderr)

    # 输出 JSON
    print(json.dumps(articles, ensure_ascii=False, indent=2))

    # 写日志
    if do_log:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{date_str}-wechat.json")
        log_data = {
            'date': date_str,
            'window_cst': f"{start_cst.strftime('%Y-%m-%d %H:%M')} → {end_cst.strftime('%Y-%m-%d %H:%M')}",
            'total_articles': len(articles),
            'with_content': sum(1 for a in articles if a['has_full_content']),
            'article_links': [a['link'] for a in articles],
        }
        with open(log_file, 'w') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        print(f"📝 日志已写入 {log_file}", file=sys.stderr)


if __name__ == '__main__':
    main()
