# 小红书文案引擎注册表

本文件把两个已拉取到 `vendor/` 的外部开源 skill 接入 `xiaohongshu-publishing` 的文案阶段。它们是文案方法来源，不改变本技能的登录、素材只读、事实追溯、用户确认和发布安全门。版本和提交哈希见 [vendor-manifest.md](vendor-manifest.md)。

## 路由规则

| 用户意图 | 默认引擎 | 说明 |
|---|---|---|
| 只想写一篇自然的小红书文案、种草笔记、好物分享 | `zhongcao` | 单篇内容优先，强调口语化、移动端节奏、标题和标签 |
| 系统做品牌内容、账号定位、内容矩阵、内容日历或长期增长 | `xiaohongshu-skills` | 先做策略与内容系统，再落到单篇文案 |
| 同时需要品牌策略和一篇可发布笔记 | 先 `xiaohongshu-skills`，后 `zhongcao` | 前者确定人群/定位/内容支柱，后者完成自然成稿 |
| 用户明确点名某个引擎 | 按用户点名 | 点名优先于默认路由，但仍须遵守本技能的安全门 |

## `zhongcao` 单篇自然文案模式

本地来源：`vendor/zhongcao/SKILL.md`；上游：<https://github.com/1-SKILL/zhongcao>

执行要点：

1. 先读取本地 `vendor/zhongcao/SKILL.md`；写作前检查 `vendor/zhongcao/latest-rules.json`，以当次获取到的平台规则、标签策略和限流词为准；网络不可用时标记规则版本待确认，不伪称已同步。
2. 明确分享对象、笔记类型、重点卖点和目标人设；缺失项可采用低风险默认值，但不得虚构使用体验。
3. 输出 5 个标题备选、完整正文、8–15 个分层标签和配图建议。标题、段落长度、emoji 密度和标签数量以当前规则为参考，不机械套模板。
4. 口吻应像真实分享，短段落、移动端友好；产品参数、效果和体验只使用已确认资料，避免“最好、绝对、立刻见效”等无法证明表述。

## `xiaohongshu-skills` 品牌内容模式

本地来源：`vendor/xiaohongshu-skills/`；上游：<https://github.com/vivy-yi/xiaohongshu-skills>

该仓库是按内容创作、账号运营、互动运营、数据分析、电商转化、平台规则、工具生态、营销推广和增长策略组织的系统知识库。不要一次性加载全部技能；按任务选择最小相关集合：

| 场景 | 最小推荐子技能路径 |
|---|---|
| 单次图文 | `skills/01-内容创作/graphic-content-creation/SKILL.md`、`title-writing/SKILL.md`、`copywriting-skills/SKILL.md`、`cover-design/SKILL.md`、`hashtag-optimization/SKILL.md` |
| 品牌账号 | `skills/02-账号运营/account-positioning/SKILL.md`、`persona-building/SKILL.md`、`content-calendar/SKILL.md`、`content-matrix/SKILL.md`、`content-consistency/SKILL.md` |
| 电商种草 | `skills/04-电商转化/seeding-content-creation/SKILL.md`，必要时增加 `skills/01-内容创作/seeding-copywriting/SKILL.md` |
| 复盘迭代 | `skills/03-数据分析/content-performance-analysis/SKILL.md`、`competitor-analysis/SKILL.md`、`data-analytics/SKILL.md` |
| 风险控制 | `skills/05-平台规则/compliance/SKILL.md`、`content-review/SKILL.md`、`copyright/SKILL.md` |

表内相对路径均以 `vendor/xiaohongshu-skills/` 为根。只有实际任务需要时才读取对应文件；路径不存在时先检索同类名称，不猜造内容。

系统模式的最小交付物为：品牌/账号简报、目标人群、内容支柱、选题或内容日历、单篇创作规范、指标与复盘建议。只有用户需要发布单篇笔记时，才进入单篇文案输出，不把策略建议冒充产品事实。

## 统一输入与输出契约

输入至少记录：产品/主题、目标人群、使用场景、已确认参数与卖点、限制条件、禁用词、品牌口吻和是否需要配图/发布。

输出至少包含：标题（必要时多版本）、正文、话题标签、配图或封面建议、事实来源与待确认项。涉及产品的内容必须先经过产品简报确认，再进入小红书成稿确认。

## 冲突处理与质量门

- 外部 skill 的语气模板、标签建议或“爆款”表达，不得覆盖本技能的事实追溯、不得虚构体验、不得夸大功效和不得绕过用户确认。
- 中文小红书图文仍遵循本技能的中文店铺图片优先规则；外部引擎只负责内容方法，不替代素材筛选和逐项检查。
- 平台规则、敏感词和标签可能变化；每次使用应注明规则来源和检查时间，并在无法获取时明确提示。
- 发布前仍必须展示预览摘要并取得用户明确确认；“生成文案”不等于“发布”。

## 来源与维护

- `zhongcao`：单篇种草文案与动态规则参考，已拉取到 `vendor/zhongcao/`，内含 `SKILL.md` 和 `latest-rules.json`。
- `xiaohongshu-skills`：品牌化、全链路运营技能索引，已拉取到 `vendor/xiaohongshu-skills/`；按需读取相关子技能。
- 本注册表只维护路由和边界，不复制外部仓库全部内容；外部仓库更新后，以链接中的最新文档为准，并在发布记录中记录实际采用的引擎与规则版本。
