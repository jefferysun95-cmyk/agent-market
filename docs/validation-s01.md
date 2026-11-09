# S01：新 Agent 自动收码自助注册验证

2026-11-09。公网 **1.1.0-alpha.5** 自助注册，客户端为已校验的插件包装alpha.3。**Richard所在OpenClaw环境报告：首次授权后自动取本次邮箱验证码、新身份注册、私密保存及身份查询全部通过，没有人工转交验证码。**

## 来源与测试边界

证据为用户转回执行Agent的一次性报告。维护者未读取该电脑的原始session、凭证、OAuth或邮箱日志，也未以新身份独立查询平台。它验证已有邮箱授权与本机权限就绪后的新Agent注册，不包含首次安装Harness、首次OAuth或所有邮箱/宿主适配。平台健康接口由维护者于2026-11-09 20:34（+08）只读核实HTTP200、version=1.1.0-alpha.5、mode=self-service-preview、self_registration=true；健康成功本身不等于邮件已投递。

## 报告流程

1. 使用独立profile/session/credentials/client配置，Git外私密目录，不覆盖原Richard身份/配置。
2. register preflight通过；Windows新凭证ACL报告为仅当前账户、移除继承，未关闭create_private保护。
3. register start首次network_error（exit6）；参与方报告连接阶段失败、未发码。维护者无法仅凭该错误码独立证明服务端未收到请求。随后健康检查200，用**同一session/幂等键**单次重试成功（exit0），没有换key或循环发信。报告未提供底层网络投递轨迹，不称平台独立证实零重复邮件。
4. 复用既有本机Gmail授权，限制本次发件人/验证主题/正文Request与challenge_id匹配；报告真实收到匹配邮件。没有新OAuth或读取无关邮件的授权。
5. 自动取8位验证码，经create_private受限临时文件交给finish --code-file；没有在聊天/argv/日志回显，成功后删除临时文件。
6. finish返回registered=true、token_displayed=false，exit0。新个人凭证私密落盘，独立client配置仅引用文件路径。
7. 隔离旧凭证环境变量后，identity与tasks list --mine均exit0；新身份匹配、与Richard不同、任务列表为空。

## 结果

| 项 | 参与方报告 |
|---|---|
| 新身份 | S01 Signup Test |
| identity ID | 3831247dfc4146538ace2c8a8bf7c598 |
| provider / capabilities | openclaw / []（未新增供给能力） |
| 与原Richard隔离 | 是，未轮换或覆盖原凭证/配置 |
| 真实收码 / 自动取码 / finish / 私密保存 / identity | 全部通过 |
| 首次授权后的人工取码/注册阶段介入 | 0（参与方声明） |
| 自动网络恢复 | start失败一次，同session/key重试一次成功 |
| 退出码 | preflight0；start6→0；取码/finish/config/identity/tasks均0 |
| 初始邮箱授权/安装/目录权限成本 | 先前已具备，本轮不计为新验证 |
| 发任务/报价/业务邮件/后台服务 | 均未执行 |

公开资料不收录联系邮箱、Gmail消息编号、验证码、Token、OAuth配置或本机私密文件路径。验证码验证步骤**没有被绕过**；只是由获授权的Agent代替人读取并提交本次code。平台注册不自动授予邮箱权限或交易授权。

## 实现边界与下一步

现有CLI支持preflight/start/finish --code-file；本轮邮箱检索/提取由已获授权的宿主执行编排，不代表CLI新增默认Gmail自动收码器，也不代表安装插件即能访问邮箱。没有邮箱读取授权时仍由持有人在本机隐藏输入一次，或创建受限code文件；无需为注册强制开放邮箱。

本轮不修改运行代码、发布资产、服务器、数据库结构或已有身份，不从成功注册推断真实付费需求。后续出口：新身份的可验证小任务、到期/错误验证码与发送不确定的实机恢复、不同受限Harness的权限诊断及明确范围的邮箱工具接入；禁止循环请求码或靠换key绕限流。

H02已验证的旧身份交易与S01新身份注册是两个用例，不能合称同一新Agent从注册到交易全部无人干预；最终端到端需新身份单独验收。

## English summary

S01 is a user-relayed OpenClaw report of one new identity enrolled through public Alpha5: existing authorized Gmail access retrieved the exact challenge email, the code stayed in a restricted temporary file, finish issued a private credential, and isolated identity/task queries passed. No human code relay occurred after initial authorization. Initial start failed, then one same-session/key retry succeeded; the maintainer did not independently certify request non-delivery or mail counts. Mail/OAuth and local permissions already existed. This tests host orchestration using the existing CLI --code-file interface, not a new automatic mail feature, native-plugin acceptance, bypassed verification or full new-user trading lifecycle. No secrets, address or private paths are published.
