# GitHub 搜索与展示维护 / GitHub discovery maintenance

更新：2026-11-11。依据现有 Alpha5 业务说明优化项目发现与安装转化；不是搜索排名、Trending 上榜或注册增长保证。[安装](installation-overview.zh.md) · [业务边界](business-workflow.md) · [渠道台账](distribution-status.md)

## 当前定位与关键词

- 名称保持 **agent-market / Agent Market**。未来展示品牌按 [Run7 计划](brand-transition-plan.md)单独实施；本轮不更换仓库、包、Skill、插件、Registry、URL 或凭证。
- 仓库 About 描述：**Connect AI agents to delegate data tasks, find matching capabilities and collaborate across harnesses. Discover suppliers, agree on terms and verify results. Free preview.**
- GitHub Homepage 指向英文页面 `https://jefferysun95-cmyk.github.io/agent-market/index.en.html`；网站原中文页面仍保留。
- 8 个 Topics：`agent-to-agent`, `agent-communication`, `agent-collaboration`, `task-delegation`, `agent-matching`, `agent-marketplace`, `ai-agents`, `mcp-server`。
- 标签以用户意图为主：Agent间交互与沟通、协作、任务委派、供需匹配；保留AI Agents和MCP Server作为定位入口。独特性来自业务组合和简介，不为独特而创造无法理解的品牌标签。`agent-matching`表示当前能力/类别发现、筛选与提案比较，不宣称已经实现智能推荐或自动撮合；`agent-to-agent`不表示已实现A2A官方协议。Python/CLI/OpenClaw等实现与兼容信息保留在正文和安装指南，不占据本轮主要需求标签。
- 自然覆盖概念：agent-to-agent task marketplace、AI agents、Agent Skills、MCP、CLI、data services、data cleaning、task outsourcing。不是预测市场、A2A 协议实现、模型 API 网关或支付产品，不添加这些不相符标签。

GitHub 官方说明 Topics 可用于分类与发现；不据此声称具体排名提升。[Topics 官方说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics)

## 本轮修改范围

| 项目 | 处理 |
|---|---|
| Repository About / Topics | 使用上述简介、8个标签和原主页；GitHub API 写入后读回核对，保留本机操作前后快照 |
| README 首屏 | 中英文同步：一句话用途、CI/MIT/明确版本徽章、流程 SVG、一个 Skill 安装命令及执行器前提 |
| 安装路径 | 原生完整插件、独立 Skill + 执行器、便携 CLI、远程 MCP 分开；不假称一条命令完成注册或所有宿主均通过 |
| 功能与证据 | 四种数据场景、订单步骤、邮箱可选、免费预览；H02/S02/N01/V04证据集中链接，保留人工/确定性/参与方回执边界 |
| 基础维护 | 现有 MIT、Release、CI、Bug/Feature/接入帮助 Issue模板、PR模板、CONTRIBUTING/SECURITY 保留；无需为活跃度重复创建 |
| 图示 | `assets/agent-market-workflow.svg` 是静态业务示意，不是演示截图、真实流量或实时驾驶舱；后续真实操作录像另做 |
| 版本 | 纯文档/元数据变更，不增加应用版本、重打历史 Release 或部署服务；按合并commit独立开发备份 |

仓库 MIT 与 ClawHub 六个文件经持有人授权的 MIT-0 发布是不同范围；首屏 MIT 徽章描述仓库许可，不改变独立渠道许可。

## 站内推广按顺序继续

1. **本轮：基础信息与首屏**。通过 PR/CI合并文档，读取公开 main/元数据确认；保留原运行代码与下载包。
2. **Discussions 社区入口（待执行）**。可以开启功能并准备 Announcements / Q&A；不重复发广告。发布前用渠道台账核对版本、能力和风险；本轮仅提供下方草稿，不新增公开讨论。
3. **Awesome 清单（待筛选/提交）**。优先查阅 Agent Skills、MCP servers、AI agent tools 对应维护者规则，再选最匹配条目。候选资料入口：`modelcontextprotocol/servers`、`punkpeye/awesome-mcp-servers`、`VoltAgent/awesome-agent-skills`。它们只是待核对候选，不宣称接受本项目或已满足贡献条件。先检查是否已有同名条目、活动状态、许可/质量/排序规则，再提交一条准确链接；不向无关 Issues 广告、不批量重复提交。
4. **Profile（待执行）**。发布者主页置顶本仓库，按实际工作介绍项目；个人 README 是独立仓库工作，不在本次仓库修改中自动创建。Sponsors仅在有真实资助需求时单独评估，不作为可信度或排名承诺。
5. **后续3–7天与长期**。按真实反馈回复Issue、修复安装问题并更新文档；有实际功能/修复才发Release。真实操作演示、首笔任务/复用反馈优先于Star。无需为上榜制造提交或虚增版本。

GitHub Marketplace 不是任意 Agent 服务/Skill 的通用上架渠道；当前项目没有 GitHub Action 产品，不为流量伪装成 Action。其余宿主官方目录继续按独立台账，不混作 GitHub 发布。

## 不采用未经证实的热度公式

没有在本次依据中取得可复现的 GitHub 搜索或 Trending 排名公式。因此不把“相对历史增速”“小语言榜更容易”“讨论/提交直接提高搜索权重”“长期不推必然降权”等当成事实或验收指标。把 Trending 作为可能的自然发现结果，不作为可控交付，不承诺上榜时间。

不买Star、互刷、制造安装量、无关标签或垃圾讨论。不用维护者自测安装/注册冒充真实用户。[GitHub 官方项目发现说明](https://docs.github.com/en/get-started/exploring-projects-on-github/finding-ways-to-contribute-to-open-source-on-github)

## 发布公告草稿（未发布）

> **Agent Market Alpha5: connect your Agent to outside data capabilities**
>
> Discover data-service suppliers, compare proposals and verify deliveries through a shared task lifecycle. Use a full OpenClaw plugin, Skill + CLI/HTTP, or compatible remote MCP. Self-service email registration is open; existing users reuse their credentials.
>
> This preview is for CNY 0 free tests. Payments and escrow are not implemented; scheduled discovery and model autonomy are not enabled by installation. Cursor's official application remains under review. Start with the bilingual installation overview and report onboarding friction using a non-sensitive example. Never post credentials or verification codes.

实际发布时链接主分支 `docs/installation-overview.md`、`docs/installation-overview.zh.md` 与 `docs/distribution-status.md`；不把本草稿当已发送公告。

## 衡量效果

漏斗：发现/访问 → 安装成功 → 新身份注册成功 → 首笔任务验收 → 再次使用。独立报告各入口，记录日期和测试排除口径。下载不等于安装，身份不等于独立自然人，accepted不等于付款或独立认证的交付质量。

当前[只读运营报表](operator-report.md)能显示显式测试分类与未标记增量，没有安装来源归因；来源未知保持未知。首批9个已知测试身份/9笔订单的分类和基线由运营者私密保存，不把ID/联系邮箱放入推广素材。后续可记录人工汇总，不先扩建跟踪基础设施。

## 后续编辑检查

- 中英文用途、版本、CNY0边界、安装包区别、已提交/已上架状态一致。
- 当前安装命令可追溯到安装说明；初始注册不能被“三行跑起来”宣传省略。
- CI徽章绑定main现有workflow；版本徽章标preview，不伪称stable/latest或全部测试已通过。
- About/Topics 属仓库设置，Git源码不保存它们；备份中附本次公开元数据操作快照，并在未来变更前核对GitHub实际值。
- 新功能、真实业务验证、发布和部署分别记账；重要文档交付附commit备份，不覆盖旧资产。


## English-first repository presentation — 2026-11-11

The root `README.md` is the canonical English landing page. `README.zh.md` is the optional Chinese translation. Keep `README.en.md` as a synchronized English compatibility copy so existing links remain valid. Both languages link to each other; current English onboarding links point to the root README. GitHub About is English and its homepage points to the existing English website. Historical releases and previously submitted directory snapshots are not repackaged or resubmitted. Chinese internal plans/evidence retain their existing paths; this is a default-entry change, not a claim that every historical document has been translated. Future source bundles include the Chinese README and workflow illustration so the new first-screen links work offline.
