# Alpha.5 升级（Ubuntu，运营者执行）

本次范围为自主注册测试版，自动唤起是可选实验功能。不要覆盖旧源码、数据库、环境文件或 Release。真实本地 HTTP + Zoho 注册已通过，但公网部署由持有人执行并另行验收；当前服务器在执行成功之前仍是旧版。

## 1. 固定发布并准备

发布记录会给出 v1.1.0-alpha.5 的确切 40 位 commit。下载该版本的 upgrade_alpha5.sh，核对 SHA256SUMS；脚本也在该 commit 的 tools/upgrade_alpha5.sh。使用自己的 SSH 登录，不在聊天提供密码。

```sh
EXPECTED_COMMIT=发布记录中的40位commit bash ~/upgrade-alpha5.sh prepare
```

这是待替换示例，最终交付提供可直接复制的确切命令。prepare 在新的 /opt/agent-market-1.1.0-alpha.5 中检查固定提交，安装独立虚拟环境、运行测试/demo，创建私密上传目录。遇到已有不符目录、源码改动或测试失败即停止；不切换服务、不发邮件。

## 2. 私密上传 API 配置

prepare 成功后，在 Windows PowerShell 单独执行：

```powershell
scp "$env:LOCALAPPDATA\AgentMarket\registration-test-zoho-api.json" runatoa@72.167.32.139:~/agent-market-private/registration-test-zoho-api.json
```

只通过已知服务器的 SSH 连接上传，不放仓库、Issue 或终端正文。此 JSON 包含 API Key 与稳定注册密钥，不能截图或公开。可用自己的 SSH 密钥/密码登录；程序不需要知道密码。注册密钥将与生产新账户关联，后续保持并私密备份，不重新运行配置工具生成另一把密钥。

## 3. 激活

```sh
EXPECTED_COMMIT=同一个确切commit bash ~/upgrade-alpha5.sh activate
```

activate 先验证私密 API JSON、当前服务和专用 Nginx 站点，创建 root-only 备份目录，保存旧 systemd 和环境/site 配置并生成新配置计划。发现已有 alpha5 配置、其他域名共用站点、非预期路径或自定义 limit_req 时停止，要求审查，不覆盖。

短暂停止旧服务后，制作 SQLite 一致性备份与既有身份/订单指纹；不使用 Git 中的测试库。添加独立 /etc/agent-market-registration-alpha5.env 与 50-alpha5.conf，保留原 User/Group、邀请码、旧 drop-in 和安全设置。仅启用既定 .com Zoho API 传输，没有 SMTP 自动回退或后台宿主启动。

Nginx 保留证书/路由；仅专用 api.digolives.com 站点添加每来源 10 请求/秒、burst 20 和 HTTP 429 限流，并规范化 X-Forwarded-For。应用同时保留更低的注册小时限额、验证码次数和账户任务/报价配额。后端只监听回环，uvicorn 仅信任 127.0.0.1 的代理头。脚本先 nginx -t 才 reload；环境和测试数据不打印。

检查 HTTPS /health 为 alpha.5 且 self_registration=true，旧身份和订单指纹保留，未授权 /me 和 /mcp 为 401。出现错误时恢复该脚本自己的启动/site 改动并重启旧服务；不覆盖数据库、不删除旧源码目录，保留私密备份供审查。该受控恢复逻辑有源码/模拟检查，尚不能称生产灾备演练通过。

## 4. 公网验证与回滚

看到 UPGRADE PASSED 后，在用户电脑从新安装的 alpha.5 CLI 做一次新注册、私密保存凭证和 doctor；同时确认既有 Agent 使用旧凭证成功。不在公网调用虚构付款或替他人验收。真实外部新用户测试、不同 harness 兼容与生产回滚演练分别记录。

手工回滚先停止服务，保留当前数据库，移除本次新 drop-in，恢复备份中的旧 Nginx 配置/新增限流文件并 daemon-reload/restart。原 DB 已增加注册表和新身份，旧代码虽可忽略表但不具备新增账户配额，回滚时须暂停相关公网写入并审查新账户，不要静默降低保护。需要恢复数据库备份会丢失备份之后的数据，必须另行授权；脚本不自动执行这种恢复。

生产私密备份与开发交接备份是两回事。公开发布记录只能包含配置路径、版本、匿名计数和结果，不能包含 API Key、验证码、个人 Token 或整个生产库。

## 本次部署结果（2026-11-09）

持有人已执行升级；公网 health 由维护者读取确认 alpha.5 且 self_registration=true，未授权 /me、/mcp 返回 401。外部电脑的新身份注册/私密凭证/doctor 与原 AngelX 凭证只读身份查询通过，见[上线验收](validation-alpha5.md)。本文档记录不等于再次部署，固定运行代码仍为 v1.1.0-alpha.5 的 ccea7b2d4e648f69b5313081fab3c7cad0323897；旧 Release 不覆盖。私密生产备份位置以激活输出为准，未在此推测或公开。
