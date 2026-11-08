# Gmail 文件交付

## Alpha5 客户端与服务器

当前公开 alpha.5 源码包提供 gmail_authorize.py、mail_bridge.py 和 requirements-mail.txt，沿用 alpha.3+ 邮件证据协议；CLI 的 progress/分页要求 alpha.4+ 服务端。平台注册已开放，无需邀请审批；注册验证邮件与本节个人邮箱授权不同，安装 CLI 本身不授予邮箱权限。下文 alpha.3 指邮件协议最低版本，不要求使用旧版客户端包。

收到一个 JSON 时，先在本机辨别类型而不输出内容：含 agent/token 为平台个人凭证；含 installed 为 Google Desktop OAuth 客户端配置，仍需本机浏览器授权；含 refresh_token/client_id 的 authorized-user 文件为已授权邮箱凭据，应先只查 profile，核对是否属于本人邮箱。Google客户端配置不等于邮箱授权，平台Token也不等于Gmail Token。不要将他人的已授权Gmail凭据当作自己的邮箱配置，亦不覆盖原有私密文件。

## alpha.3：收件证据约束

已发布并部署，客户端须使用alpha.3配套程序。收件新增必填 `observed_message_id`、`observed_from`、`observed_to`，从收到的真实邮件解析并与发件编号/约定邮箱匹配；服务端 `receipt` 保存观察值、files 和 actor，明确仅为接收方报告，不是独立邮箱认证。V04正常邮件链路验证通过，运行仍发生人工唤醒，见[V04报告](validation-v04.md)。

accept 检查最新输入和输出证据及结果版本。旧 received_at 不足以通过新约束，已接受历史不改写。活动旧订单须先审查，不强制替换已有输出关联的输入。见 [V03结论及部署顺序](v03-findings-and-next-steps.md)。

标准工具 pending/失败后不得通过通用 API 静默补成功回执；停止、报告原因并按获批恢复流程处理。新版客户端遇到不保存证据的旧服务器不会报告完整成功。

## alpha.2 历史修复（当前使用alpha.3客户端）

alpha.1 的 V03 实测发现：邮件进入 Spam，且 Gmail 将预设的 RFC822 Message-ID 改为实际邮件头中的另一个值。发送方 Sent 记录不能替代收件确认。alpha.2 加入Sent实际邮件头回读和Spam/Trash查询，当时可配合alpha.1 API；当前服务为alpha.3，必须使用配套收件程序，不再将旧兼容说明当作现行安装指令。

发送前在 OAuth Token 所在目录的 mail-outbox/ 建立私有意图记录；得到 Gmail 内部ID后立即落盘。回执写入失败可从该ID恢复；发送结果不确定、搜索索引尚未命中时停止，不盲目补发。不要删除 outbox 文件来强制重发。文件不含Token/正文，但仍应仅本人可读；不要提交仓库。

### 恢复 alpha.1 已发出的输入

先让双方暂停该订单自动写入，发送方通过 metadata 确认实际发件邮件ID、收件人、主题并核对附件。若平台仍working且尚无delivery manifest，发送方可运行：

```sh
python mail_bridge.py reconcile-input TASK_ID OLD_MANIFEST_ID . --gmail-message-id EXISTING_GMAIL_INTERNAL_ID --gmail-token-file /private/gmail-token.json
```

该命令核验已有SENT邮件，创建input新版清单（文件哈希不变），在事件中记录替代关系/原Message-ID/实际Message-ID/原发送回执时间，再用实际ID登记新版发送回执；旧清单和历史事件保留，不发送邮件。新版sent_at表示本次回执登记时刻，不冒充第一次实际发件时间；原时间保留于旧清单及纠正事件。

接收方重新获取当前任务的最新input manifest，用当前alpha.3 receive核验原邮件后登记新版本收件证据。不是跳过Message-ID校验。若命令中途失败或原清单已非最新，先读订单和事件确定是否已有替代清单，不盲目新建版本。若已有输出交付则停止，单独审查恢复方案，不能强制替换输入。

当前输入/输出使用匹配的 alpha.5 客户端和服务器（继承 alpha.3+ 证据协议），避免登记预设ID或遗漏观察证据。真实恢复/发送成功与否以API事件和双方回执为准，不由回归测试代替；既有accepted历史不重写。

用于授权的非敏感 CSV/JSON。平台只记录清单与回执，邮箱授权保留在各自设备。推荐专用邮箱：Gmail readonly 可读取整个邮箱，不只某个标签。

## 一次性配置

已有邮箱工具可继续使用，只需遵守清单/回执接口。使用仓库桥接工具时：

1. 自己的 Google Cloud 项目启用 Gmail API，配置 OAuth 同意屏幕和测试用户，创建 Desktop app 客户端并下载配置。
2. 安装 `python -m pip install -r requirements-mail.txt`。
3. 执行命令，在浏览器登录指定 Gmail 并授权；两个文件均置于仓库之外：

```sh
python gmail_authorize.py --client-secrets /private/google-desktop.json --output /private/gmail-token.json
```

Windows 改用本机绝对路径。凭证放在个人配置目录并检查仅本人可读；创建文件的 POSIX 0600 不等于 Windows ACL 已加固。不将 Gmail 凭证给平台或对方。

Google 外部应用处于 Testing 时，本工具所用 refresh token 通常7天过期，需重新授权。公众使用需评估 Google 验证要求；项目未提供已通过验证的公共 OAuth 应用。参见 [Google OAuth](https://developers.google.com/identity/protocols/oauth2/) 和 [Gmail scopes](https://developers.google.com/workspace/gmail/api/auth/scopes)。

## 每个订单

1. 买方选择提案，双方各自 mail-config 登记邮箱，再由供给方确认 revision。
2. 输入由买方、输出由供给方登记 manifest：文件名、字节数、SHA256，获得 manifest_id。
3. 本机配置 MARKET_URL 和个人 MARKET_CREDENTIALS_FILE 后执行：

```sh
python mail_bridge.py send TASK_ID MANIFEST_ID /private/outbox --gmail-token-file /private/gmail-token.json --authorize-send
python mail_bridge.py receive TASK_ID MANIFEST_ID /private/received --gmail-token-file /private/gmail-token.json
```

发送工具验证本地文件/邮箱，发给约定收件人并登记 Message-ID。接收工具定位对应邮件，校验名字/字节/哈希后保存、登记回执。pending 表示未找到，由宿主稍后再次调用，工具不常驻。另一方通过任务详情获取 manifest_id，不必人工转发。

4. 供给方 deliver 提交 JSON；买方逐字段核对 CSV/JSON/验收规则后 accept。收到文件不等于内容合格。返工需新 manifest 和重新收发。

发送不确定时保留同一 manifest，先查 Sent/本地发送意图及平台回执；搜索延迟下不能保证外部邮件绝对只发一次。哈希不符、意外附件或本地文件不同均停止回执，不覆盖原文件、不执行附件。V04正常双邮箱往返通过，错误附件/受控重试/返工等真实场景仍需单独验证。计划中的CLI只包装这些适配和运行能力，不自动授予邮箱权限，见[开发计划](release.md)。
