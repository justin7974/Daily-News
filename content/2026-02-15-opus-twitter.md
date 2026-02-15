# Twitter KOL 日报 - 2026-02-15

## 🧠 AI研究前沿

1. **karpathy** (https://x.com/karpathy/status/2022862247568642485) — 将 micrograd 从 243 行精简到 200 行纯 Python 实现 GPT 训练+推理，无任何依赖。每个 op 只返回局部梯度，backward() 负责链式法则乘法。代码恰好分三栏：Dataset/Tokenizer/Autograd | GPT模型 | Training/Inference

2. **karpathy** (https://x.com/karpathy/status/2022041235188580788) — 作为天使投资人支持 Simile AI 发布。Simile 探索 LLM 作为「群体模拟器」的方向——为什么只模拟一个人格，而不模拟整个人群？预训练 LLM 的原始形态本就是互联网多元人群的模拟引擎

3. **emollick** (https://x.com/emollick/status/2022676591596515728) — 预言"AI不能做原创科学"到"AI当然能做科学"的转变将像此前每次 AI 转变一样发生：先是过度乐观的宣传，然后聪明人开始用 AI 辅助，然后 AI 承担更多工作，然后小发现，然后…

4. **emollick** (https://x.com/emollick/status/2022658647378268361) — 评价中国新 LLM Seed 2.0：benchmark impressive，但代码生成和广泛知识仍有差距。如果不是开源权重，这将代表 AI 市场的重大转变——中国 AI 的策略一直是免费发布模型

5. **emollick** (https://x.com/emollick/status/2022794509977866704) — 随着 AI 进步，能够验证 AI 输出的人越来越少（引用数学家评价 AI 证明）。需要开始认真思考这个问题：多个 AI 协作验证？还是其他方案？

6. **vasuman** (https://x.com/vasuman/status/2022538769694683368) — 强烈建议现在就开始实验开源模型。MiniMax M2.5 感觉接近 SOTA，100tps 跑一小时不到一美元。下一个开源模型可能超越美国最好的闭源模型，这对美国 AI 实验室应该是"terrifying"的

7. **vasuman** (https://x.com/vasuman/status/2022816632817750215) — Codex 的 context compaction 能力远超 Claude Code。Compaction（理解该删什么、该保留什么）是通往 AGI 的关键短期杠杆

8. **Hesamation** (https://x.com/Hesamation/status/2022824698875126169) — 如果一家公司花 3 个月才发现 AI 在编造关键指标，而且没人核查过一次，那蠢的恐怕不是 AI。另外，也许不要用 3B 本地模型来运营整家公司

9. **Hesamation** (https://x.com/Hesamation/status/2022820372098224261) — 推荐 Paul Graham 2002 年关于"品味"的文章：品味不是个人偏好，是可学习的技能。好设计是简洁的、永恒的、解决正确问题的、看起来轻松但背后极其努力的。在 AI 时代，品味将更加重要

10. **Hesamation** (https://x.com/Hesamation/status/2022763867277856780) — 当下最核心的技能不是提示工程也不是编码，而是精准的 bullshit detector。AI 越来越擅长听起来聪明，所以你必须真的变聪明

## 🤖 AI Agent系统

11. **EXM7777** (https://x.com/EXM7777/status/2022778630468956395) — 自动化的未来不再是拖拽画布，而是桌上一个 $600 的盒子（Mac Mini + OpenClaw）替代 n8n 运行整个业务逻辑：定时任务、自我修复的 Agent、模型升级即性能提升。一旦管道完全开放，没人会回到平台

12. **EXM7777** (https://x.com/EXM7777/status/2022732074424340857) — 最好的 OpenClaw setup 来自不会写代码的人——因为他们无法暴力解决问题，只能把想法表达得极其清晰。提示能力在未来多年都至关重要，直到模型能直接读取大脑意图

13. **EXM7777** (https://x.com/EXM7777/status/2022695334334599676) — 分享当前 AI 技术栈：写作 Claude Opus 4.6 + Kimi K2.5，编码 GPT-5.3-Codex + Opus 4.6，通用 MiniMax M2.5，图片 Nano Banana Pro，视频 Seedance 2.0

14. **EXM7777** (https://x.com/EXM7777/status/2022673537644007497) — 预测：2026 年最好的 AI 模型将是开源的

15. **rileybrown** (https://x.com/rileybrown/status/2022391822094639378) — 新 OpenClaw 技能：YouTube 缩略图 Moodboard。让 AI 搜索 YouTube → 找到表现最好的相似视频 → 拉取缩略图 → 用 Nano Banana API 换脸 → 生成 PDF。25分钟完成

16. **jackfriks** (https://x.com/jackfriks/status/2022840872342020264) — 爱上口袋里的真实 AI 助手 WACKO（OpenClaw agent），永远不睡觉

## ✍️ 提示工程

17. **rryssf_** (https://x.com/rryssf_/status/2022838288864940348) — Max Planck 研究所分析 28 万份学术演讲转录发现：人类正在口语中越来越多地使用 ChatGPT 偏好的词汇。"delve" 使用增加 48%，"adept" 增加 51%，且 58% 是自然口语而非照稿念。这是"模型坍塌"，只是模型是我们自己

18. **rryssf_** (https://x.com/rryssf_/status/2022838342287790239) — 文化演化反馈循环：如果人类已经在吸收 AI 语言模式并作为"人类"语言输出，那即使是"人类生成"的训练数据也不再纯粹是人类的了。人类数据和 AI 数据的界限正在消融

19. **godofprompt** (https://x.com/godofprompt/status/2022613091415134504) — Claude 产品管理提示工程系列：10 个 PM 专用 prompt，涵盖 Post-Mortem 分析、功能失败诊断等。号称将每周工作从 60 小时压缩到 38 小时

20. **EXM7777** (https://x.com/EXM7777/status/2022416497151480042) — 营销 prompt 的 10x 提升方法：使用 AIDA、PAS、PSB、SPIN 等框架引导 LLM 的逻辑流程，而不是直接堆需求

## 🎨 创作营销

21. **eptwts** (https://x.com/eptwts/status/2022735281728770389) — 辣评：对大多数人来说 clawdbot 没用。不如围绕真正推动业务的少数任务构建专用 Agent。真正的操盘手不用 AI 也比那些追潮流的人赚得多

22. **egeberkina** (https://x.com/egeberkina/status/2022775791239499809) — 用 Seedance 2.0 制作了一个出人意料结局的短视频

23. **egeberkina** (https://x.com/egeberkina/status/2022696016131313669) — 分享 AI 图像风格变换 prompt "microdot"，展示了惊艳的视觉效果

24. **0xROAS** (https://x.com/0xROAS/status/2022775202627600737) — 反驳"AI 内容比人工贵"的论点：你们根本不知道 AI 内容正在以多大的规模被生产

25. **steipete** (https://x.com/steipete/status/2022809868558639272) — OpenClaw 作者：Context compaction 最终应该在 π（协议层）解决

## 🚀 独立开发创业

26. **corbin_braun** (https://x.com/corbin_braun/status/2022792888359489960) — 引发争论：GPT-5.3 Codex High > Opus 4.6（说是"popular opinion"）

27. **corbin_braun** (https://x.com/corbin_braun/status/2022794014794326297) — 将为 Thumio 推送模板大更新和 insert-me 工具升级

28. **levelsio** (https://x.com/levelsio/status/2022754572918456445) — 庆幸 X 平台将严厉打击自动化和垃圾信息，表示 bot 可以存在但必须标记为 bot

29. **levelsio** (https://x.com/levelsio/status/2022687619541356975) — 有了 AI 和机器人，大部分低技能岗位不再需要。保持低质量移民意味着永远不会自动化这些岗位。真正需要的是技术工人：电工、水管工、医生、工程师

30. **rileybrown** (https://x.com/rileybrown/status/2022233277206241563) — 正在构建让多个 Agent 在他睡觉时互相交流的内部 moltbook，轮流主持。下周汇报结果

---

🦐 小虾 Twitter 日报 (Opus) | 2026-02-15
