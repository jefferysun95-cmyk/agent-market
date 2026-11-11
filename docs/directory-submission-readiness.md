# 下一批目录：提交材料与真实状态

更新2026-11-11。当前服务Alpha5、冻结完整插件alpha.3、ClawHub独立Skill0.1.0分别记账；不把上架等同于宿主业务验收。当前名称不变，[Run7 Agent Market展示品牌](brand-transition-plan.md)仅列入后续计划。

| 渠道 | 已完成 | 剩余门槛 | 当前状态 |
|---|---|---|---|
| MCP官方Registry | 发布者授权、官方校验、一次成功发布、精确版本active读回 | 后续元数据维护；各宿主连接验证独立 | 已发布，见[回执](../registry/PUBLICATION.json) |
| Claude官方目录 | 自建marketplace安装及隔离验证 | Claude本机地区登录受限；按用户要求暂缓原生公网验收 | 未提交；N01不是Claude证据 |
| Cursor Marketplace | 当前源码专用清单、共享Skill/CLI、官方模板静态校验通过 | Cursor实机加载/已有身份查询/授权免费任务、发布者账号与官方表单 | 未提交；静态校验不是实机验收 |
| OpenAI目录 | 已取得并核对当前官方打包、鉴权及提交说明 | 私人Bearer属API-key方式，门户不提供该连接输入；受保护远程MCP须补兼容OAuth流程，另需账号/隐私/条款/验收 | 未提交；不伪造匿名或把秘密写入配置 |
| Glama | 公开条目、Ownership verified；专用Bearer Test Profile检查Healthy、20个工具已发现 | 后续健康维护；工具定义质量评分与业务工具实测另计 | 已收录已认领，健康/发现通过，见[证据](validation-glama.md) |
| ClawHub | GitHub导入0.1.0；6项文件/哈希和正常隔离安装通过 | 辅助警告及平台自动changelog纠正；旧扫描失败保留 | 已上架可安装，见[验收](validation-clawhub-import.md) |
| skills.sh | 真实可见条目与Skill安装命令 | Snyk W011防护说明更新和后续扫描；不伪造自然安装量 | 已收录 |

## 接下来执行

1. 将已审阅源码/安全说明与中英文入口经PR/CI合入GitHub，确认Pages实际内容，不重打冻结包。
2. Glama已按持有人专项授权创建无业务数据、capabilities为空的测试身份，并保存至Test Profile，检查Healthy且20工具可发现。当前普通Agent Token无只读范围，不能称服务端最小权限已实现；Glama声明健康检查不调用业务工具。后续维护不得换用现有买卖方/管理员凭证，不开放匿名业务接口。
3. Cursor遵循当前官方本地插件目录/重载/Customize核验规则。缺宿主或登录时记录阻塞，不用manifest通过替代实际安装，不静默下载安装宿主或改默认配置。
4. OpenAI OAuth属于单独开发里程碑；本轮不扩展平台认证、资金或生产数据库。
5. 每个渠道保持适配/测试/提交/上架/健康分项证据和版本备份。

## 官方规范（核对2026-11-11）

- Cursor: https://cursor.com/docs/plugins ; https://cursor.com/docs/reference/plugins
- Glama authenticated test profiles: https://glama.ai/mcp/faq
- OpenAI connection limitations: https://developers.openai.com/plugins/deploy/submission ; https://developers.openai.com/plugins/build/auth

## 历史准备过程（下文保留2026-11-10时点，不代表当前阻塞）

## Registry候选的审阅与安全边界

[Registry说明](../registry/README.md)和[公开元数据](../registry/server.json)复用现有单服务，不新增包托管服务或注册规则。请求头只声明个人Token输入，不包含个人值。命名空间仍是候选，GitHub拥有者验证完成前不能宣称已控制Registry名称。

本机下载官方mcp-publisher1.8.9遇慢链路：第一次有界下载45秒未完成，保留部分文件并尝试一次限时续传；未验证完整SHA256前不运行。用户已同意现在设备授权，已打开可见终端再做一次最长10分钟续传；完整校验后仅进入GitHub登录，不自动发布。发布器文件、登录凭据与原始浏览器登录状态只留Git外，不纳入备份。GitHub已有仓库授权不能冒充Registry登录。

## 下一动作

- Registry优先完成元数据与发布者授权，实际发布后保存编号/读回证据；若网络/授权阻塞如实报告，不无限重试。
- Cursor与OpenAI先核对真实规则再创建manifest；不凭记忆制作并宣传兼容包，也不移动旧plugin tag或重打包冻结Release。
- Glama作为补充，账号可用后填写公开仓库/名称/简述，不上传个人Token、邮箱授权或私人日志。
- 各渠道README/中英文安装入口/台账集中更新，重要交付保存独立commit备份；本页不宣称任何新增上架结果。

## 原生安装发现的可复用修正点

同名旧managed Skill可能优先于插件内Skill。先用宿主命令检查实际来源/路径/哈希；备份到扫描根外，再经授权移出旧目录并重启；保留恢复方案。仅plugins loaded不证明插件Skill生效。验证码取码网络失败可用本机隐藏输入，不需要为测试关闭验证。PowerShell写JSON应明确UTF-8，不能把本地解码失败算服务端交易失败。


[中英文可复用提交文案](submission-profile.md)已准备，包含实际认证方式、安装边界与测试证据；不代替渠道要求的隐私政策、条款或原生验收，也不含任何个人凭证。


## Registry状态更新 — 2026-11-10

已完成发布者授权、官方validate、一次401拒绝后的查重/授权刷新及成功发布，并从官方API读回active精确版本。前表未发布门槛已完成，当前事实以[PUBLICATION.json](../registry/PUBLICATION.json)和[渠道台账](distribution-status.md)为准。其他目录仍分别待办，不因Registry登记而自动通过。
