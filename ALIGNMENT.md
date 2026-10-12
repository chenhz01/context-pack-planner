# ALIGNMENT — context-pack-planner

16-point deliverable alignment for R13. Evidence measured 2026-10-11,
Python 3.13.14, Windows 10.

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | 可运行核心代码，纯标准库 | PASS | 仅 import `argparse/hashlib/json/sys`；3.13.14 运行 |
| 2 | CLI 入口 argparse | PASS | `--manifest/--out` + stdin；self-test 覆盖文件/stdin/缺失/损坏 |
| 3 | self_test.py 存在且可运行 | PASS | `python self_test.py` exit 0 |
| 4 | 用例数 ≥40 | PASS | 57 checks（SUMMARY: PASS 57/57），实测 2026-10-11 |
| 5 | 三类用例 | PASS | 功能 ~28（packing/优先级/截断/哈希）；异常 ~17（13 种 manifest 变体、损坏 JSON）；极端 ~14（300 文档、Unicode/emoji 名、5000 字符名、深层交互） |
| 6 | 末行 `SUMMARY: PASS n/n` | PASS | `SUMMARY: PASS 57/57` |
| 7 | README 英文文章级 | PASS | 全英文 10 章节 |
| 8 | README 首段 ≤60 词 | PASS | 首段 58 词 |
| 9 | Quickstart 标耗时 | PASS | "~0.2 s, measured" + 复现命令 |
| 10 | why-not-X ≥3 替代含真锚 | PASS | reaatech/context-window-planner (0★)、Zion-support/zion-context-window-planner (0★)、mertcanaltin/composto (78★)，均出自 _r13_design.json anchors |
| 11 | Minimal Fallback | PASS | 6 行 Python 贪心 fallback + 损失说明 |
| 12 | Design Trade-offs | PASS | 4 条：greedy vs 最优背包、整文档 vs 压缩、声明 tokens vs 内嵌估算、must fail-loud |
| 13 | Limits & Second-order Effects | PASS | 4 条：成本说谎、priority 膨胀二阶效应、贪心搁浅预算、预算抬升效应 |
| 14 | FAQ 含 When NOT to use | PASS | 4 问含 "When NOT to use this?" |
| 15 | Core Assumptions ≥3 + 置信度 + as of | PASS | 4 条假设；"Confidence: high … medium … As of 2026-10-11" |
| 16 | LICENSE/CHANGELOG/数字纪律/零真名 | PASS | MIT ("zhengming contributors")；v0.1.0→v0.1.1 留痕；89% 引用处标注 "per its README"、耗时实测；无真名/密钥 |
