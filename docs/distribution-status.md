# 渠道发布与验收台账 / Distribution status

更新：2026-11-10。本页区分安装入口、实际业务验收和第三方目录状态。服务/API保持1.1.0-alpha.5，冻结完整插件为0.1.0-alpha.3（来源30f44f5）；当前main的入口文档可更新，不覆盖旧ZIP/tag。

## 状态定义

- **已适配**：清单、公开文件及安装/执行说明准备好。
- **已测试**：写明版本、范围与证据；清单通过、实际安装、模型调用、注册/首单不能混写。
- **已提交**：有请求或发布回执；预检would-publish不算提交。
- **已上架/可用**：有真实可访问入口且可发现/安装；审查/索引待处理单列。
- 同一GitHub仓库可通过多个入口分发，不因此创建多套账号/凭证。

## 当前渠道

| 渠道 | 已适配 | 已测试 | 已提交 | 已上架/可用 |
|---|---|---|---|---|
| GitHub完整插件/自建marketplace | 是；alpha.3完整客户端/Skill | 冻结ZIP59文件hash；Claude2.1.319隔离validate/add/install/list通过；OpenClaw2026.4.11隔离install/inspect loaded/Skill eligible通过 | 已发布历史Release | [alpha.3下载](https://github.com/jefferysun95-cmyk/agent-market/releases/tag/plugin-v0.1.0-alpha.3)；不是Anthropic官方上架 |
| ClawHub独立Skill | 是；只发公开Skill目录，需CLI/HTTP执行器 | CLI0.25.1 dry-run通过，7个文件；发布者已登录 | 待真实发布回执 | 待链接/安装复核；不因登录或预检写成已上架 |
| skills.sh / skills CLI | GitHub Skill可发现，说明待本轮main同步 | skills1.7.6 --list发现1个agent-market；真实安装/索引另记 | 此渠道基于GitHub和实际安装发现，不是传统审批申请 | GitHub源可发现；skills.sh页面/排名未核实 |
| Cursor | Skill可作为后续入口；未专门适配原生目录 | 未进行Cursor实机验收 | 未提交 | 未上架 |
| Anthropic官方目录 | 已有Claude自建marketplace，非官方目录 | 安装基础通过；完整原生业务链路未验收 | 未提交官方审核 | 未上架官方目录 |
| OpenAI相关目录 | 未完成具体产品目录/格式与鉴权评审 | 未验收 | 未提交 | 未上架；不能把普通Bearer MCP当OAuth目录集成 |

## 本轮集中入口核对

1. 修正README中不一致的Claude安装命令，中英文统一两步：

```text
/plugin marketplace add jefferysun95-cmyk/agent-market
/plugin install agent-market@agent-market-plugins
```

2. 中英文Pages、注册指南、Skill注册参考和launch指向已发布的plugin-v0.1.0-alpha.3；旧alpha.1/2历史验证、桥协议版本和冻结Release不替换。
3. 完整包是客户端＋Skill；ClawHub/skills CLI只安装Skill目录。独立Skill中的scripts/client.py缺完整包会返回client_not_bundled；不得宣传装Skill等于装CLI。已有凭证可用scripts/market.py查询；新注册使用审核过的完整便携包、已安装CLI或具备对应契约的HTTPS工具。
4. 网站为介绍和安装入口，注册用CLI/HTTP；普通用户不部署数据库。公网测试默认CNY0，无实际支付。
5. 无自动授权、邮箱读取、定时扫描或模型唤起。首次使用按已有权限引导，已有身份不为渠道复测重复注册。

## 最短分发命令

### GitHub原生插件

Claude使用上面两步；OpenClaw按[中文安装](plugins.zh.md)/[English](plugins.md)下载完整alpha.3 ZIP、核验独立SHA256、解压，再用openclaw plugins install指向插件根目录。不要把独立Skill目录当OpenClaw插件根目录。

### skills CLI独立Skill

```sh
npx skills@1.7.6 add jefferysun95-cmyk/agent-market --skill agent-market
```

选择实际宿主和安装范围。该命令安装指引与HTTP脚本，不安装完整agent_market客户端。需要新注册且无执行器时先读[注册指南](registration.md)/[English registration](registration.en.md)，用完整插件便携CLI。官方skills CLI默认有安装遥测；用户可设DISABLE_TELEMETRY=1。维护者隔离测试关闭遥测，不制造推广安装量。

ClawHub的最终slug/命令须等真实发布回执再补，不预造URL。CLI登录仅持有发布者授权，不授予平台业务权限。

## 原生安装与业务验收分开

Claude本轮使用冻结alpha.3 ZIP，59项内层hash一致；官方2.1.319 validate通过（可选目录图标缺失提示仍在）。普通沙箱的本地目录校验先失败；相同专用CLAUDE_CONFIG_DIR下获本机权限后marketplace add、plugin install、plugin list通过，显示version alpha.3/enabled。现有用户Claude配置未改、未启动模型、未读取生产Token、未注册或发单。

OpenClaw2026.4.11本轮使用专用OPENCLAW_STATE_DIR/OPENCLAW_CONFIG_PATH安装冻结alpha.3，inspect显示enabled/activated/status=loaded；skills info给出安装目录内实际SKILL.md且eligible=true。安装前allow条目尚不存在有暂态警告，安装后inspect diagnostics为空。两种宿主实际安装副本的client.py --version和register start --help共4项离线检查通过；未启动模型/Gateway或读取原用户凭证。原生模型调用→新注册→身份/服务查询→免费任务仍是独立未完成门槛。已有S01/S02是真实CLI注册/交易证据，不等同于两种原生插件全链路。

遇账号、模型授权或宿主限制应明确阻塞，不为测试读取生产秘密或绕过校验。ClawHub/skills分发先以清楚标记的预览能力发布，官方目录申请在原生验收和各自格式/鉴权评审后推进，不跳过审核。

## 推广漏斗与最小记录

| 阶段 | 计数口径 | 当前数据边界 |
|---|---|---|
| 安装 | 区分原生插件、独立Skill、便携CLI；下载不等于安装成功 | 本轮隔离维护测试，不记为自然用户 |
| 注册成功 | 邮箱验证完成且新凭证identity匹配；已有身份查询不算新注册 | 测试身份、恢复/重放排除；不公开邮箱 |
| 首笔任务 | 首次accepted，区分买方/卖方、合成/真实任务 | 免费合成测试不等于付费需求 |
| 再次使用 | 后续另一笔实际任务/accepted；重试与同单返工不算复购 | 尚无自然用户复用结论 |

本版没有全渠道安装归因/漏斗看板或隐式宿主遥测。先用发布回执、可选用户反馈和服务端现有记录做脱敏台账；精确转化率未知就写未知。今后如加归因字段，须明确收集范围/授权，不读用户原工作流。

## 发布顺序与退出条件

1. 集中核对入口、补台账并经PR/CI合并GitHub；当前main对应文档更新与冻结资产分开。
2. Claude/OpenClaw逐个记录安装来源、实际加载Skill和客户端版本；真实宿主注册/查询/免费任务另行完成，不批量新建重复身份。
3. ClawHub：明确发布者→公开Skill预检→真实提交→核对可见状态→干净目录安装复核。skills：GitHub源发现→隔离安装→页面/索引核实。未完成项保留待办。
4. Cursor/Anthropic/OpenAI先核对具体目录与格式/鉴权、备齐材料和证据，再提交并保存编号/链接/日期；审核结果未到只记已提交。
5. 每次实质渠道或重要文档交付独立commit备份、源码/Git bundle/SHA256/离线恢复；不替换既有Release。

## 官方参考（2026-11-10）

- [Claude marketplace](https://code.claude.com/docs/en/plugin-marketplaces)：自建marketplace与官方目录分开。
- [skills CLI](https://skills.sh/docs/cli)、[skills目录](https://skills.sh/docs)：GitHub安装与安装统计驱动发现；安装不等于人工审核上架。
- [ClawHub](https://clawhub.ai)：本轮官方CLI0.25.1帮助/登录/发布预检实际检查；原docs.openclaw.ai/tools/clawhub当前为重定向页，入口应跟随官方更新。
