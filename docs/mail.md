# Gmail 文件交付

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
