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
| MCP 官方 Registry | 已纳入下一批准备；服务元数据、命名空间归属及发布格式待核对 | 未进行Registry发布/发现/连接验收 | 未提交 | 未登记；不等于各宿主官方目录收录 |
| Glama | 补充分发渠道；材料与格式待核对 | 未验收 | 未提交 | 未收录 |

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
4. 先完成Claude Code与OpenClaw原生公网验收：宿主实际加载插件/Skill → 独立新身份注册 → 身份/服务查询 → 一笔免费任务；已存在的安装、CLI和回环证据不替代此门槛。随后按Claude（Anthropic）、Cursor、OpenAI官方目录逐项推进；MCP官方Registry加入同一批准备清单，Glama作为补充。先核对各自格式/鉴权、备齐材料和证据，再提交并保存编号/链接/日期；审核结果未到只记已提交。
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


## 2026-11-10 后续核对：支持单、正常安装与原生公网门槛

- ClawHub精确owner/version复查：clawscan=failed、trufflehog=failed、retrying=false、stage=checks_failed。此刻不能再承诺平台会自动重试，也不能从检查未完成推断已检出密钥或恶意代码。
- 经用户明确授权，已向官方仓库提交公开支持 [Issue #4508](https://github.com/openclaw/clawhub/issues/4508)，请求重试现有检查或提供报告。仅公开项目、版本及发布编号，不附私人日志/凭证；等待维护者处理，未重新上传、绕过检查或变更版本。
- 与此前关闭遥测的Claude隔离安装分开：skills1.7.6在新隔离项目对OpenClaw执行一次正常GitHub安装（copy/project），exit0，默认安装遥测未显式关闭，metadata标注publisher-validation。实际目录为项目skills/agent-market，内容hash仍为ec94eff8140a7c19ae2c35f8442befadf69bbd641059126928e1ae430264c7d2。这是维护者测试，不计自然用户；遥测服务是否接收事件未独立确认，不为排名重复安装。
- 本次skills.sh页面网络复查失败；此前可见正文为软404。当前仍记“GitHub正常安装通过，目录收录未确认”，不把HTTP200或安装事件当作收录证明。
- Claude Code当前未登录，用户选择稍后登录；原生模型公网验收待完成。OpenClaw一次只读readiness调用遇90秒外层超时，已退出且无该次遗留Node进程，未进行注册/邮件/订单；不能据此判定插件加载失败。改为当前能响应的原生聊天执行一次新注册与查询，随后另配唯一对手方免费任务，不再反复调试自动唤起。
- 公开支持Issue提交不是渠道上架。Cursor、Anthropic、OpenAI官方目录尚未提交；继续遵守原生验收、各目录格式/权限/隐私材料核对后逐项申请的顺序。


## 下一批准备清单（用户确认，2026-11-10）

1. **先验收原生宿主**：OpenClaw优先，Claude Code待持有人登录后继续。保存真实来源、宿主版本、新注册/查询/免费任务证据及人工介入；超时或权限阻塞立即报告。
2. **官方目录**：Claude → Cursor → OpenAI，逐项核对发布者账号、包格式、公开README/许可证、隐私/权限说明、实际安装与业务证据；缺项先补齐，不预记已提交。
3. **MCP官方Registry并行准备材料**：核对当时的官方发布规范，选择并验证发布者命名空间，准备服务/包版本元数据、HTTPS端点或安装方式、Bearer鉴权说明及连接验证。Registry登记与宿主商店上架分开；若规则与现有远程MCP不兼容先报告，不为登记开放匿名业务接口或宣称完整OAuth已实现。准备工作可以先做，实际发布在原生验收后推进。
4. **Glama补充**：复用已审核公开资料，核对提交条件与可访问性，再提交并记录回执；不抢占原生验收和官方目录的优先级。
5. 每渠道继续分别记录“已适配、已测试、已提交、已上架/可用”。本次仅调整计划，未向上述新目录提交、未增加运行功能、未改线上配置或冻结发布资产。


## OpenClaw 公网验收进展（2026-11-10，用户转回）

原生alpha.3插件由宿主报告loaded/doctor通过；插件目录客户端完成Alpha5公网新注册、identity、3项data-cleaning供给查询、空的个人任务查询。验证码由持有人本机隐藏输入，首次400原因未确定，收到challenge unavailable后仅请求一次新挑战并成功。不能把这一结果写成自动邮箱取码通过。

**门槛仍未全通过**：宿主实际加载旧openclaw-managed Skill，插件内置Skill未选中；免费任务未执行。下一步以可回滚方式处理同名来源，重查宿主实际路径，再复用本轮新身份跑一单纯API/CNY0任务，不重复注册。Gmail链路故障另记，不阻挡纯API任务；重启是否能解决来源冲突尚待验证。详见[插件验收](validation-plugins.md)。


## N01 结案：OpenClaw 原生买方门槛通过（用户转回，2026-11-10）

旧 managed Skill 已备份并移出扫描根，授权重启后宿主实际路径/哈希指向插件内置 Skill（source=openclaw-extra）。复用本轮新身份完成 N01 发布→Richard报价→选择→确认→交付→买方独立21项核验→accepted，CNY0/payment为空。该结果更新上文历史“来源冲突/首单待测”，详见[N01证据](validation-n01.md)。

人工阶段转发不为零；Richard发生一次请求前UTF-16本地修复；accept进程退出码未捕获，记未知。不是无人值守、邮件或付款验证。Claude原生公网门槛仍待持有人登录后完成，官方目录/Registry尚未因本次测试自动提交。


## 后续渠道继续推进 — 2026-11-10

用户确认Claude本机登录受地区限制，不再阻塞其他渠道。Registry远程候选元数据与官方schema校验已就绪；GitHub发布者授权待官方发布器就绪后由持有人完成。Cursor/OpenAI当前规范获取及专用适配仍待确认；Glama实际提交入口要求登录。各渠道均未因准备完成而记为已提交。详见[提交准备清单](directory-submission-readiness.md)。
