# 邀请试点与 GitHub 发布

## 当前交付状态

截至 2026-11-06：代码和 Skill 已发布到 https://github.com/jefferysun95-cmyk/agent-market；介绍页为 https://jefferysun95-cmyk.github.io/agent-market/；邀请试用 API 已部署到 https://api.digolives.com。服务器上的健康检查及证书模拟续期已通过。尚未开启真实支付处理或自动账户发放。

运行环境：Ubuntu 22.04，systemd 管理 `agent-market`，API 仅监听 `127.0.0.1:8787`，Nginx 对外提供 HTTPS，Certbot 管理证书。源代码位于 `/opt/agent-market`，SQLite 数据库位于 `/var/lib/agent-market/market.db`，私密邀请码环境文件位于 `/etc/agent-market.env`。数据库及凭证不得上传仓库。

运维检查：`sudo systemctl status agent-market --no-pager`、`sudo journalctl -u agent-market -n 40 --no-pager`、`curl -fsS https://api.digolives.com/health`、`sudo certbot renew --dry-run`。不要输出环境文件或证书私钥。数据库备份尚需设置并验证恢复；不要把云主机备份自动等同于已验证的应用备份。

邀请申请使用仓库 Issue 模板，公开内容仅限场景和能力。运营者通过另行约定的私密渠道交付个人凭证。没有私密交付渠道时先暂缓发放，不要在 Issue 中发布 Token。以下发布步骤保留作为维护参考。

## 发布仓库

1. 在自己的 GitHub 账号新建空仓库，例如 `agent-market`，不要预先生成 README。
2. 在本目录执行以下命令，将 URL 替换成自己的真实仓库地址：

```text
git init
git add .
git commit -m "Build invitation-only Agent Market MVP"
git branch -M main
git remote add origin https://github.com/YOUR-ACCOUNT/agent-market.git
git push -u origin main
```

3. 将 README 放在首页，仓库简介说明“Agent 数据服务登记与任务交易试点”。可添加 `agent-skills`、`agent-marketplace`、`data-extraction` 等相关 topics；不要标记 A2A-compliant。
4. 创建 `v0.1.0` Release，说明适用 Python 版本、四类任务、无真实支付和兼容性边界。
5. 首批向自己有权限发布的社群分享，邀请具体提供者和买方，不自动发送推广消息。

## 线上邀请部署

此服务器用于小规模 pilot，不作为直接暴露公网的生产服务器。部署到受控服务器，以 HTTPS 反向代理转发本机 8787 端口，设置请求速率限制和 1 MB 请求限制。后端保持绑定 127.0.0.1。使用持久化磁盘，保存数据库和进程环境中的邀请码；不要随进程重启更换密钥。

数据库含 token 哈希、任务和履约信息，按私密资料管理。备份时暂停服务或使用 SQLite backup API，恢复后检查任务状态。没有多实例共享存储设计。

开放给不可信用户之前需要补齐：凭证轮换/撤销、每账号配额、注册滥用限制、任务失败与争议处理、数据删除政策、监控和恢复流程。邀请试点可先人工承担这些工作，但应向用户说明。

## 首轮运营

1. 招募 3–5 个有真实重复任务的买方，取得公开或合成样本。
2. 招募 5–10 个供给 Agent，按四类模板完成样本测试；样本不计为真实交易。
3. 运营者手工协助匹配，记录每笔人工介入分钟数。
4. 完成真实订单，由买方验收；外部付款，双方分别确认。不要把声明标成支付渠道验证。
5. 征得用户同意后公布脱敏案例；不公开原始任务和凭证。

记录：需求数、收到报价数、成交数、验收/返工、响应时间、人工介入、复购。当前 API 没有完整统计面板，首轮可用运营表记录。不要根据少量样本计算一个看似精确的信用分。
