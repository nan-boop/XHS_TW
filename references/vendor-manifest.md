# 外部文案技能供应清单

用途：记录已拉取到本技能 `vendor/` 的外部 skill，保证可复现、可审计和可更新。

| 能力 | 本地目录 | 上游仓库 | 当前固定提交 | 内容规模 |
|---|---|---|---|---|
| `zhongcao` | `vendor/zhongcao` | <https://github.com/1-SKILL/zhongcao> | `3c0464a82385f9dd31d31b69b25fedc63aa94237` | `SKILL.md` + `latest-rules.json` |
| `xiaohongshu-skills` | `vendor/xiaohongshu-skills` | <https://github.com/vivy-yi/xiaohongshu-skills> | `b42ff691c78c07bc917881d8ad3460b83fc0acb1` | 139 个子技能 |

## 使用约定

- 默认读取本地固定版本；需要最新平台规则时，`zhongcao` 额外检查其 `latest-rules.json`，并记录获取时间与版本。
- `xiaohongshu-skills` 按任务读取最小相关子技能，不一次性加载整个仓库。
- 更新前先查看上游变更，更新后重新记录提交哈希并运行 skill 校验；不覆盖本技能主入口和本地安全规则。
- 外部仓库内容仅作为方法参考，产品事实、用户资料、共享盘权限和发布确认以本技能为准。

## 维护命令

- 仅检查本地 checkout：`scripts/update_copywriting_vendors.ps1 -CheckOnly`
- 拉取上游更新：`scripts/update_copywriting_vendors.ps1`

拉取更新后必须把新提交哈希写回本清单，并重新运行 `skill-creator/scripts/quick_validate.py`。普通文案任务不自动拉取整个仓库；直接使用已经固定并验收的本地版本。
