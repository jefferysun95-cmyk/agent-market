# Gmail 文件交付

## alpha.2 客户端修复

alpha.1 的 V03 实测发现：邮件进入 Spam，且 Gmail 将预设的 RFC822 Message-ID 改为实际邮件头中的另一个值。发送方 Sent 记录不能替代收件确认。alpha.2 发送后用 Gmail 内部消息ID读取实际 Sent 副本，核验字节及邮件头，再登记实际 Message-ID；收件查询显式 includeSpamTrash=true。此修复可直接配合已部署的 alpha.1 API，不要求先升级订单服务。

发送前在 OAuth Token 所在目录的 mail-outbox/ 建立私有意图记录；得到 Gmail 内部ID后立即落盘。回执写入失败可从该ID恢复；发送结果不确定、搜索索引尚未命中时停止，不盲目补发。不要删除 outbox 文件来强制重发。文件不含Token/正文，但仍应仅本人可读；不要提交仓库。

### 恢复 alpha.1 已发出的输入

先让双方暂停该订单自动写入，发送方通过 metadata 确认实际发件邮件ID、收件人、主题并核对附件。若平台仍working且尚无delivery manifest，发送方可运行：

```sh
python mail_bridge.py reconcile-input TASK_ID OLD_MANIFEST_ID . --gmail-message-id EXISTING_GMAIL_INTERNAL_ID --gmail-token-file /private/gmail-token.json
```

该命令核验已有SENT邮件，创建input新版清单（文件哈希不变），在事件中记录替代关系/原Message-ID/实际Message-ID/原发送回执时间，再用实际ID登记新版发送回执；旧清单和历史事件保留，不发送邮件。新版sent_at表示本次回执登记时刻，不冒充第一次实际发件时间；原时间保留于旧清单及纠正事件。

接收方重新获取当前任务的最新input manifest，用alpha.2 receive核验原邮件后登记新版本收件回执。不是跳过Message-ID校验。若命令中途失败或原清单已非最新，先读订单和事件确定是否已有替代清单，不盲目新建版本。若已有输出交付则停止，单独审查恢复方案，不能强制替换输入。

后续 Richard 的输出发送也应使用alpha.2，避免再次登记预设ID。真实恢复/输出发送成功与否以API事件和双方回执为准，不由回归测试代替。

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

发送不确定时保留同一 manifest，先查 Sent/平台回执。工具按稳定 Message-ID 查已发送邮件，但搜索延迟下不能保证绝对只发一次。哈希不符、意外附件或本地文件不同均停止回执，不覆盖原文件、不执行附件。真实双邮箱测试待完成。
