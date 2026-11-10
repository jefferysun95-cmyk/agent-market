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
| ClawHub独立Skill | 是；7个公开文件，来源90377ac | 官方CLI预检和实际提交通过；公开安装尚不可执行 | 已提交0.1.0-alpha.3，pending-publication | **未上架**；检查未能完成，平台保留上传并等待再次检查，详情见下 |
| skills.sh / skills CLI | GitHub Skill可发现；main说明已同步 | skills1.7.6 --list发现1项；隔离Claude项目--copy安装成功 | 无独立审核提交回执；基于GitHub/实际安装发现 | **GitHub安装可用、目录未收录**；详情页HTTP200但正文为404不可用，不将HTTP200当上架 |
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

选择实际宿主和安装范围。该命令安装指引与HTTP脚本，不安装完整agent_market客户端。需要新注册且无执行器时先读[注册指南](registration.md)/[English registration](registration.en.md)，用完整插件便携CLI。官方skills CLI默认有安装遥测；用户可设DISABLE_TELEMETRY=1。维护者本轮隔离测试关闭遥测，不制造推广安装量，也不把测试安装计为自然用户。

ClawHub精确引用为 `@jefferysun95-cmyk/agent-market`，不可简写为 `agent-market`；不带发布者的同名短名当前指向其他人的预测市场项目。我们的[版本详情](https://clawhub.ai/jefferysun95-cmyk/skills/agent-market)当前仅能用于核对发布状态，**不是可安装承诺**。只有平台检查完成、公开可见并通过干净目录安装后，才发布正式安装指引。CLI登录仅持有发布者授权，不授予平台业务权限。

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


## 2026-11-10 实际发布回执与阻塞

### GitHub：已合并并公开验证

PR #23经14项CI通过，合并commit **90377ac9ad82b872dca0b0abc5cefabaabc58dd6**。中英文Pages实际HTTP200、当前下载链接均为alpha.3、未再出现旧alpha.2下载入口；公开README实际命令与指南一致。公网health只读查询仍为Alpha5/self-service-preview/self_registration=true，未部署或修改生产。

### 原生安装副本的本地业务验证

在临时回环实例，用Claude与OpenClaw实际安装目录内client.py分别注册两个合成新身份、查询identity、查询data-cleaning服务，再由两端完成一笔CNY0任务至accepted/payment为空。验证码由合成发信器捕获、私密临时文件传给finish，测试结束关闭服务并清理临时库/凭证；未发真实邮件、未读取生产密钥、未调用模型。这是“原生安装＋安装副本客户端本地完整用例”，不是“模型主动选择Skill的公网注册/首单”。公网真实注册/交易证据仍分别见S01/S02。

### ClawHub：已提交，等待平台完成检查

发布者 **jefferysun95-cmyk**；Skill版本 **0.1.0-alpha.3**；来源仓库main、commit **90377ac9ad82b872dca0b0abc5cefabaabc58dd6**、路径skills/agent-market。

- CLI发布回执：status=pending-publication，publicationStatus=pending，fileCount=7。
- versionId：`k97djq876b758xggzn1nc8cp4d8hzqt9`；attemptId：`zx75h8z9at1f5mzekczkycphh18hzm01`。
- owner限定inspect：clawscan=failed、trufflehog=failed、retrying=true、stage=checks_failed。下载报告返回Scan results not found，不能据此臆测发现了具体漏洞。
- 已登录页面进一步确认：Publication checks failed；Secret check / Security check **could not complete**，版本尚不公开/不可安装；上传保留，等待另一次检查，**不需要重新发布**。Dashboard显示Hidden/Needs review，SkillSpector findings pending。
- 因而不是已上架，也没有证据说平台检出了密钥泄露/恶意代码。本轮不unhide、不改版规避、不重复上传、不转发私人日志给支持。
- 后续：按平台复查结果读取精确owner/version；有报告先定位；检查通过后做干净目录安装/文件核验；持续无结果时另经授权联系支持。不能把短名其他发布者的公开页面当我们的上架证据。

### skills CLI：真实安装通过，skills.sh目录尚未收录

官方skills1.7.6从GitHub main发现agent-market，随后在全新隔离项目用 `--skill agent-market --agent claude-code --copy --yes` 安装成功，实际落点为该项目 `.claude/skills/agent-market`；未修改全局Skill、未加载模型、未注册/发单、遥测关闭。安装结果是Skill目录，而不是完整CLI。skill内容hash为 `ec94eff8140a7c19ae2c35f8442befadf69bbd641059126928e1ae430264c7d2`。

[skills.sh候选详情地址](https://skills.sh/jefferysun95-cmyk/agent-market/agent-market)返回HTTP200，但可见正文显示“404 / agent-market isn’t available in this repository”。不能将软404或一次GitHub安装写成目录已收录。官网说明索引/排名与安装统计有关；本轮不为排名重复安装/上传遥测，等待真实使用或官方明确的收录方式。无安装转化率/自然用户数结论。
