#!/bin/bash
# 批量生成16天日报

BASE_DIR="/Users/justin/Library/CloudStorage/Dropbox/CC/Projects/Daily News"
cd "$BASE_DIR"

# 日期范围
START_DATE="2026-02-01"
END_DATE="2026-02-16"

# 生成日期列表
echo "📅 生成日期列表..."
python3 << 'EOF'
from datetime import datetime, timedelta

start = datetime(2026, 2, 1)
end = datetime(2026, 2, 16)

dates = []
current = start
while current <= end:
    dates.append(current.strftime('%Y-%m-%d'))
    current += timedelta(days=1)

with open('/tmp/dates_to_generate.txt', 'w') as f:
    for d in dates:
        f.write(d + '\n')

print(f"共 {len(dates)} 天")
EOF

# 逐天生成
echo "🔄 开始逐天生成日报..."
while read date; do
    echo ""
    echo "========================================="
    echo "📅 处理日期: $date"
    echo "========================================="
    
    python3 scripts/generate_daily.py "$date" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✅ $date 生成成功"
    else
        echo "❌ $date 生成失败"
    fi
    
    # 短暂休息避免API限制
    sleep 1
done < /tmp/dates_to_generate.txt

echo ""
echo "🎉 全部完成！"
