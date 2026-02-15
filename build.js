const fs = require('fs');
const path = require('path');
const { marked } = require('marked');

const CONTENT_DIR = path.join(__dirname, 'content');
const TEMPLATE_DIR = path.join(__dirname, 'templates');
const STATIC_DIR = path.join(__dirname, 'static');
const DIST_DIR = path.join(__dirname, 'dist');

// ===== 工具函数 =====

function extractUrl(text) {
  // [text](url)
  const md = text.match(/\[([^\]]*)\]\(([^)]+)\)/);
  if (md) return { text: md[1], url: md[2] };
  // bare url
  const bare = text.match(/(https?:\/\/\S+)/);
  if (bare) return { text: '', url: bare[1] };
  return null;
}

function extractAllUrls(text) {
  const urls = [];
  const re = /\[([^\]]*)\]\(([^)]+)\)/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    urls.push({ text: m[1], url: m[2] });
  }
  if (urls.length === 0) {
    const bare = text.match(/(https?:\/\/\S+)/);
    if (bare) urls.push({ text: '', url: bare[1] });
  }
  return urls;
}

function getSource(url) {
  try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return ''; }
}

function stripMarkdown(text) {
  return text
    .replace(/\[([^\]]*)\]\([^)]+\)/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .trim();
}

function escapeHtml(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function inlineMarkdown(text) {
  // 简单内联 markdown：bold, links, code
  let html = escapeHtml(text);
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  // 恢复链接（需要在 escapeHtml 之前处理）
  return html;
}

function renderInline(text) {
  // 先处理链接，再 escape 剩余
  let result = '';
  let lastIndex = 0;
  const linkRe = /\[([^\]]*)\]\(([^)]+)\)/g;
  let m;
  while ((m = linkRe.exec(text)) !== null) {
    result += escapeHtml(text.slice(lastIndex, m.index));
    result += `<a href="${escapeHtml(m[2])}" target="_blank" rel="noopener">${escapeHtml(m[1])}</a>`;
    lastIndex = m.index + m[0].length;
  }
  result += escapeHtml(text.slice(lastIndex));
  // bold
  result = result.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  return result;
}

// ===== 日期工具 =====

const EPOCH = new Date(2024, 9, 11); // 第1期：2024-10-11

function issueNumber(dateStr) {
  const d = new Date(dateStr);
  const diff = Math.floor((d - EPOCH) / (1000 * 60 * 60 * 24));
  return Math.max(1, diff + 1);
}

function formatDateDisplay(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日 · 星期${weekdays[d.getDay()]}`;
}

function formatDateShort(dateStr) {
  const parts = dateStr.split('-');
  return `${parts[1]}-${parts[2]}`;
}

// ===== 解析器 =====

function parseFile(content) {
  const lines = content.split('\n');

  // 提取日期
  const titleLine = lines.find(l => l.startsWith('# '));
  const dateMatch = titleLine && titleLine.match(/(\d{4}-\d{2}-\d{2})/);
  const date = dateMatch ? dateMatch[1] : 'unknown';

  // 按 H2 分大段
  const h2Sections = [];
  let currentH2 = null;

  for (const line of lines) {
    if (line.startsWith('## ')) {
      currentH2 = { title: line.slice(3).trim(), lines: [] };
      h2Sections.push(currentH2);
    } else if (currentH2) {
      currentH2.lines.push(line);
    }
  }

  // 识别 RSS 和 Twitter 段落
  let rssRaw = null;
  let twitterRaw = null;
  for (const s of h2Sections) {
    const t = s.title.toLowerCase();
    if (t.includes('rss') || t.includes('日报') && !t.includes('twitter') && !t.includes('kol')) {
      if (!rssRaw) rssRaw = s;
    }
    if (t.includes('twitter') || t.includes('kol')) {
      if (!twitterRaw) twitterRaw = s;
    }
  }

  const rss = rssRaw ? parseH2Section(rssRaw.lines, 'rss') : [];
  const twitter = twitterRaw ? parseH2Section(twitterRaw.lines, 'twitter') : [];

  const rssCount = rss.reduce((n, s) => n + s.items.length, 0);
  const tweetCount = twitter.reduce((n, s) => n + s.items.length, 0);

  return { date, rss, twitter, rssCount, tweetCount };
}

function parseH2Section(lines, type) {
  // 按 H3 分子段
  const sections = [];
  let current = null;

  for (const line of lines) {
    if (line.startsWith('### ')) {
      const raw = line.slice(4).trim();
      // 提取 emoji 和标题
      const emojiMatch = raw.match(/^(\S+)\s+(.+)/);
      const emoji = emojiMatch ? emojiMatch[1] : '';
      const title = emojiMatch ? emojiMatch[2].replace(/^[—–-]\s*/, '') : raw;
      current = { emoji, title, rawLines: [] };
      sections.push(current);
    } else if (current) {
      current.rawLines.push(line);
    }
  }

  // 解析每个子段的条目
  return sections.map(s => ({
    emoji: s.emoji,
    title: s.title,
    items: type === 'rss' ? parseRssItems(s.rawLines) : parseTweetItems(s.rawLines)
  })).filter(s => s.items.length > 0);
}

function parseRssItems(lines) {
  const items = [];
  let current = null;

  function pushCurrent() {
    if (current && (current.title || current.description)) {
      // 从标题或描述中提取 URL
      if (!current.url) {
        const urls = extractAllUrls(current.title + ' ' + current.description);
        if (urls.length > 0) current.url = urls[0].url;
      }
      current.title = stripMarkdown(current.title || '');
      current.description = stripMarkdown(current.description || '');
      if (!current.source && current.url) current.source = getSource(current.url);
      items.push(current);
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // 跳过空行、分隔线、meta 行、footer
    if (trimmed === '' || trimmed === '---' || trimmed.startsWith('>')) continue;
    if (trimmed.startsWith('*🦐') || trimmed.startsWith('*(')) continue;

    // 模式1：编号 bold 标题 **N. Title**
    const numberedBold = trimmed.match(/^\*\*(\d+)\.\s*(.+?)\*\*\s*$/);
    if (numberedBold) {
      pushCurrent();
      current = { title: numberedBold[2], description: '', url: null, source: '' };
      continue;
    }

    // 模式2：bold 子分组标题（不是条目，是分组标题）
    // 判断：独立 bold 行，后面跟 bullet list
    const boldOnly = trimmed.match(/^\*\*(.+?)\*\*\s*$/);
    if (boldOnly && !trimmed.match(/^\*\*\d+\./)) {
      // 检查后续行是否是 bullet
      const nextNonEmpty = lines.slice(i + 1).find(l => l.trim() !== '');
      if (nextNonEmpty && nextNonEmpty.trim().startsWith('-')) {
        pushCurrent();
        // 这是分组标题，作为 groupTitle 条目
        items.push({ groupTitle: boldOnly[1] });
        current = null;
        continue;
      } else {
        // 独立的 bold 标题条目
        pushCurrent();
        current = { title: boldOnly[1], description: '', url: null, source: '' };
        continue;
      }
    }

    // 模式3：bullet 带链接 - [Title](url)：description 或 - [Title](url)
    const bulletLink = trimmed.match(/^-\s+\[([^\]]+)\]\(([^)]+)\)(?:\s*[：:]\s*(.*))?/);
    if (bulletLink) {
      pushCurrent();
      current = {
        title: bulletLink[1],
        description: bulletLink[3] || '',
        url: bulletLink[2],
        source: getSource(bulletLink[2])
      };
      continue;
    }

    // 模式4：bullet 带 bold — - **Title** — [domain](url)
    const bulletBold = trimmed.match(/^-\s+\*\*(.+?)\*\*\s*[—–-]+\s*(.*)/);
    if (bulletBold) {
      pushCurrent();
      const link = extractUrl(bulletBold[2]);
      current = {
        title: bulletBold[1],
        description: '',
        url: link ? link.url : null,
        source: link ? getSource(link.url) : ''
      };
      continue;
    }

    // 模式5：bullet 带普通文本 - Title text — [domain](url) 或 - Description
    const bulletPlain = trimmed.match(/^-\s+(.+)/);
    if (bulletPlain) {
      const text = bulletPlain[1];
      const link = extractUrl(text);
      if (link && !current) {
        // 新条目
        pushCurrent();
        current = {
          title: stripMarkdown(text.replace(/\[([^\]]*)\]\([^)]+\)/, '').replace(/[—–-]+\s*$/, '').trim()),
          description: '',
          url: link.url,
          source: getSource(link.url)
        };
      } else if (current) {
        // 续行描述
        if (current.description) current.description += ' ';
        current.description += text;
        if (link && !current.url) {
          current.url = link.url;
          if (!current.source) current.source = getSource(link.url);
        }
      }
      continue;
    }

    // 模式6：独立链接行 [text](url) 或 [url](url)
    const standaloneLink = trimmed.match(/^\[([^\]]*)\]\(([^)]+)\)\s*$/);
    if (standaloneLink) {
      if (current && !current.url) {
        current.url = standaloneLink[2];
        current.source = getSource(standaloneLink[2]);
      } else if (!current) {
        pushCurrent();
        current = {
          title: standaloneLink[1] || getSource(standaloneLink[2]),
          description: '',
          url: standaloneLink[2],
          source: getSource(standaloneLink[2])
        };
      }
      continue;
    }

    // 模式7：裸 URL 行
    const bareUrl = trimmed.match(/^(https?:\/\/\S+)\s*$/);
    if (bareUrl) {
      if (current && !current.url) {
        current.url = bareUrl[1];
        current.source = getSource(bareUrl[1]);
      }
      continue;
    }

    // 续行文本（描述段落）
    if (current && trimmed.length > 0) {
      if (current.description) current.description += ' ';
      current.description += trimmed;
    }
  }

  pushCurrent();
  return items;
}

function parseTweetItems(lines) {
  const items = [];
  let current = null;

  function pushCurrent() {
    if (current && (current.summary || current.handle)) {
      items.push(current);
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (trimmed === '' || trimmed === '---') continue;
    if (trimmed.startsWith('*🦐') || trimmed.startsWith('>')) continue;

    // 模式1: **Name** (profile_url) 带 profile 链接
    const nameProfile = trimmed.match(/^\*\*(.+?)\*\*\s*\(?(https?:\/\/x\.com\/(\w+))\)?/);
    if (nameProfile) {
      pushCurrent();
      current = {
        displayName: nameProfile[1].replace(/^@/, ''),
        handle: nameProfile[3],
        summary: '',
        tweetUrl: null,
        profileUrl: nameProfile[2]
      };
      continue;
    }

    // 模式2: **@handle — Title** 或 **@handle** text
    const boldHandle = trimmed.match(/^\*\*@?(\w+)\s*[—–-]+\s*(.+?)\*\*/);
    if (boldHandle) {
      pushCurrent();
      current = {
        displayName: '',
        handle: boldHandle[1],
        summary: boldHandle[2],
        tweetUrl: null,
        profileUrl: `https://x.com/${boldHandle[1]}`
      };
      continue;
    }

    // 模式2b: 🔥 **@handle — Title**
    const fireBoldHandle = trimmed.match(/^🔥?\s*\*\*@?(\w+)\s*[—–-]+\s*(.+?)\*\*/);
    if (fireBoldHandle) {
      pushCurrent();
      current = {
        displayName: '',
        handle: fireBoldHandle[1],
        summary: fireBoldHandle[2],
        tweetUrl: null,
        profileUrl: `https://x.com/${fireBoldHandle[1]}`
      };
      continue;
    }

    // 模式3: **Name** text（无 @ 无 profile url）
    const boldName = trimmed.match(/^\*\*(\w[\w\s]*?)\*\*\s*(.*)/);
    if (boldName && !trimmed.startsWith('- ')) {
      const name = boldName[1].trim();
      // 判断是否是 KOL 名称（首字母大写、或已知名称）
      if (name.length > 1 && name[0] === name[0].toUpperCase()) {
        pushCurrent();
        const handle = name.toLowerCase().replace(/\s+/g, '');
        current = {
          displayName: name,
          handle: handle,
          summary: boldName[2] || '',
          tweetUrl: null,
          profileUrl: `https://x.com/${handle}`
        };
        continue;
      }
    }

    // 模式4: - **@handle** text（bullet 带 bold handle）
    const bulletHandle = trimmed.match(/^-\s+\*\*@?(\w+)\*\*\s*(.*)/);
    if (bulletHandle) {
      pushCurrent();
      current = {
        displayName: '',
        handle: bulletHandle[1],
        summary: stripMarkdown(bulletHandle[2] || ''),
        tweetUrl: null,
        profileUrl: `https://x.com/${bulletHandle[1]}`
      };
      continue;
    }

    // 模式5: 编号条目 1. **handle** (url) — text
    const numbered = trimmed.match(/^\d+\.\s+\*\*@?(\w+)\*\*\s*\(?(https?:\/\/\S+)\)?\s*[—–-]?\s*(.*)/);
    if (numbered) {
      pushCurrent();
      current = {
        displayName: '',
        handle: numbered[1],
        summary: stripMarkdown(numbered[3] || ''),
        tweetUrl: numbered[2].includes('/status/') ? numbered[2] : null,
        profileUrl: `https://x.com/${numbered[1]}`
      };
      continue;
    }

    // 链接行: → [text](url) 或 [text](url) 或 - [text](url)
    const linkLine = trimmed.match(/^[→\-]?\s*\[([^\]]*)\]\(([^)]+)\)/);
    if (linkLine && linkLine[2].includes('x.com')) {
      if (current) {
        if (!current.tweetUrl && linkLine[2].includes('/status/')) {
          current.tweetUrl = linkLine[2];
        } else if (!current.tweetUrl) {
          current.tweetUrl = linkLine[2];
        }
      }
      continue;
    }

    // 独立 x.com URL 行
    const xUrl = trimmed.match(/^\[?(?:https?:\/\/)?(x\.com\/\S+)/);
    if (xUrl || (trimmed.startsWith('https://x.com/') || trimmed.startsWith('[https://x.com/'))) {
      const urlMatch = trimmed.match(/(https:\/\/x\.com\/\S+)/);
      if (urlMatch && current) {
        const url = urlMatch[1].replace(/[\])]$/, '');
        if (!current.tweetUrl && url.includes('/status/')) {
          current.tweetUrl = url;
        } else if (!current.tweetUrl) {
          current.tweetUrl = url;
        }
      }
      continue;
    }

    // 子 bullet 带链接 （缩进）
    const subBulletLink = trimmed.match(/^-\s+\[([^\]]+)\]\(([^)]+)\)/);
    if (subBulletLink && line.startsWith('  ')) {
      if (current) {
        if (subBulletLink[2].includes('x.com') && !current.tweetUrl) {
          current.tweetUrl = subBulletLink[2];
        }
        // 可能有多条推文链接，追加为额外条目
        if (current.tweetUrl && subBulletLink[2].includes('x.com') && subBulletLink[2] !== current.tweetUrl) {
          // 保存当前，创建新条目
          const prevHandle = current.handle;
          const prevName = current.displayName;
          pushCurrent();
          current = {
            displayName: prevName,
            handle: prevHandle,
            summary: subBulletLink[1],
            tweetUrl: subBulletLink[2],
            profileUrl: `https://x.com/${prevHandle}`
          };
        }
      }
      continue;
    }

    // bullet 带推文链接的描述
    const bulletWithTweet = trimmed.match(/^-\s+(.+)\[推文\]\(([^)]+)\)/);
    if (bulletWithTweet) {
      if (current) {
        // 这是当前作者的一条推文
        if (current.summary && current.tweetUrl) {
          // 已有内容，先保存再新建
          pushCurrent();
          current = {
            displayName: current.displayName,
            handle: current.handle,
            summary: stripMarkdown(bulletWithTweet[1].trim()),
            tweetUrl: bulletWithTweet[2],
            profileUrl: current.profileUrl
          };
        } else {
          current.summary = stripMarkdown(bulletWithTweet[1].trim());
          current.tweetUrl = bulletWithTweet[2];
        }
      }
      continue;
    }

    // 引号文本或续行
    if (current && trimmed.length > 0 && !trimmed.startsWith('#')) {
      const text = trimmed.replace(/^[""]/, '').replace(/[""]$/, '');
      if (current.summary) current.summary += ' ';
      current.summary += stripMarkdown(text);
    }
  }

  pushCurrent();
  return items;
}

// ===== HTML 渲染 =====

function renderNewsItem(item) {
  if (item.groupTitle) {
    return `<div class="group-title">${escapeHtml(item.groupTitle)}</div>\n`;
  }

  const titleHtml = item.url
    ? `<a href="${escapeHtml(item.url)}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a>`
    : escapeHtml(item.title);

  let html = `<div class="news-item">\n`;
  html += `  <div class="news-title">${titleHtml}</div>\n`;
  if (item.description) {
    html += `  <div class="news-summary">${escapeHtml(item.description)}</div>\n`;
  }
  if (item.source) {
    html += `  <div class="news-meta"><span class="news-source">${escapeHtml(item.source)}</span></div>\n`;
  }
  html += `</div>\n`;
  return html;
}

function renderTweetItem(item) {
  let html = `<div class="tweet-item">\n`;
  html += `  <div class="tweet-author">`;
  html += `<span class="tweet-name">${escapeHtml(item.displayName || item.handle)}</span>`;
  html += ` <span class="tweet-handle">@${escapeHtml(item.handle)}</span>`;
  html += `</div>\n`;
  if (item.summary) {
    html += `  <div class="tweet-content">${escapeHtml(item.summary)}</div>\n`;
  }
  if (item.tweetUrl) {
    html += `  <a href="${escapeHtml(item.tweetUrl)}" target="_blank" rel="noopener" class="tweet-link">查看推文 →</a>\n`;
  }
  html += `</div>\n`;
  return html;
}

function renderSection(title, sections) {
  if (sections.length === 0) {
    return `<section class="section">\n<h2 class="section-title">${title}</h2>\n<div class="empty-state">暂无内容</div>\n</section>\n`;
  }

  let html = `<section class="section">\n<h2 class="section-title">${title}</h2>\n`;
  for (const section of sections) {
    html += `<h3 class="category-header">${section.emoji} ${escapeHtml(section.title)}</h3>\n`;
    for (const item of section.items) {
      if (section === sections[0] && sections === sections) {
        // 判断不了类型，根据 item 结构判断
      }
      if (item.handle !== undefined) {
        html += renderTweetItem(item);
      } else {
        html += renderNewsItem(item);
      }
    }
  }
  html += `</section>\n`;
  return html;
}

// ===== 构建 =====

function build() {
  // 确保 dist 目录存在
  if (!fs.existsSync(DIST_DIR)) fs.mkdirSync(DIST_DIR, { recursive: true });

  // 读取模板
  const issueTemplate = fs.readFileSync(path.join(TEMPLATE_DIR, 'issue.html'), 'utf-8');
  const indexTemplate = fs.readFileSync(path.join(TEMPLATE_DIR, 'index.html'), 'utf-8');

  // 扫描 content 目录
  const files = fs.readdirSync(CONTENT_DIR).filter(f => f.endsWith('.md'));

  // 分离主文件和 opus-twitter 变体
  const mainFiles = files.filter(f => f.match(/^\d{4}-\d{2}-\d{2}\.md$/));
  const opusFiles = files.filter(f => f.includes('-opus-twitter'));

  // 解析所有文件
  const issues = [];
  for (const file of mainFiles) {
    const content = fs.readFileSync(path.join(CONTENT_DIR, file), 'utf-8');
    const data = parseFile(content);

    // 检查是否有 opus-twitter 变体
    const opusFile = opusFiles.find(f => f.startsWith(data.date));
    if (opusFile) {
      const opusContent = fs.readFileSync(path.join(CONTENT_DIR, opusFile), 'utf-8');
      const opusData = parseFile(opusContent);
      const opusTweetCount = opusData.twitter.reduce((n, s) => n + s.items.length, 0);
      if (opusTweetCount > data.tweetCount) {
        data.twitter = opusData.twitter;
        data.tweetCount = opusTweetCount;
      }
    }

    issues.push(data);
  }

  // 按日期排序
  issues.sort((a, b) => a.date.localeCompare(b.date));

  // 分配期号
  for (const issue of issues) {
    issue.issueNum = issueNumber(issue.date);
  }

  const allDates = issues.map(d => d.date);

  // 生成每日页面
  for (let i = 0; i < issues.length; i++) {
    const data = issues[i];
    const prevDate = i > 0 ? issues[i - 1].date : null;
    const nextDate = i < issues.length - 1 ? issues[i + 1].date : null;

    const rssHtml = renderSection('📰 RSS 日报', data.rss);
    const twitterHtml = renderSection('🐦 Twitter KOL 日报', data.twitter);

    const html = issueTemplate
      .replace(/\{\{TITLE\}\}/g, `小虾日报 #${data.issueNum} | ${data.date}`)
      .replace(/\{\{DESCRIPTION\}\}/g, `小虾日报 ${data.date} — ${data.rssCount} 篇文章, ${data.tweetCount} 条推文`)
      .replace(/\{\{DATE_SHORT\}\}/g, formatDateShort(data.date))
      .replace(/\{\{DATE_DISPLAY\}\}/g, formatDateDisplay(data.date))
      .replace(/\{\{ISSUE_NUMBER\}\}/g, String(data.issueNum))
      .replace(/\{\{RSS_COUNT\}\}/g, String(data.rssCount))
      .replace(/\{\{TWEET_COUNT\}\}/g, String(data.tweetCount))
      .replace(/\{\{RSS_SECTION\}\}/g, rssHtml)
      .replace(/\{\{TWITTER_SECTION\}\}/g, twitterHtml)
      .replace(/\{\{PREV_LINK\}\}/g, prevDate ? `${prevDate}.html` : '#')
      .replace(/\{\{NEXT_LINK\}\}/g, nextDate ? `${nextDate}.html` : '#')
      .replace(/\{\{PREV_DISABLED\}\}/g, prevDate ? '' : 'disabled')
      .replace(/\{\{NEXT_DISABLED\}\}/g, nextDate ? '' : 'disabled');

    fs.writeFileSync(path.join(DIST_DIR, `${data.date}.html`), html);
    console.log(`  ✓ ${data.date}.html (${data.rssCount} RSS, ${data.tweetCount} tweets)`);
  }

  // 生成归档页
  const archiveItems = issues.slice().reverse().map(data => {
    return `<a href="${data.date}.html" class="archive-item">
  <span class="archive-date">${data.date}</span>
  <span class="archive-num">#${data.issueNum}</span>
  <span class="archive-stats">${data.rssCount} 文章 · ${data.tweetCount} 推文</span>
  <span class="archive-arrow">›</span>
</a>`;
  }).join('\n');

  const indexHtml = indexTemplate.replace('{{ARCHIVE_ITEMS}}', archiveItems);
  fs.writeFileSync(path.join(DIST_DIR, 'index.html'), indexHtml);
  console.log(`  ✓ index.html (${issues.length} issues)`);

  // 复制静态文件
  for (const file of fs.readdirSync(STATIC_DIR)) {
    fs.copyFileSync(path.join(STATIC_DIR, file), path.join(DIST_DIR, file));
  }
  console.log('  ✓ static files copied');

  // .nojekyll
  fs.writeFileSync(path.join(DIST_DIR, '.nojekyll'), '');

  console.log(`\nDone! ${issues.length} issues built to dist/`);
}

// 运行
console.log('Building daily news site...\n');
build();
