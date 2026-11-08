# Alpha.5 注册版验收

日期：2026-11-09。范围：自主注册与私密凭证接入；自动唤起作为可选实验增强，不将 V05 或特定 harness 的唤起作为本版门槛。

## 真实邮件与本地 HTTP 完整注册

持有人运行 tools/live_registration_check.py --authorize-send。工具仅使用本机回环 HTTP 服务、独立私密 SQLite 和已授权的 Zoho HTTPS 配置，向指定测试收件邮箱发送新验证码；由持有人在终端隐藏输入。

结果由持有人截图及维护者只读核对私密 report.json 双重确认：status=passed、registration_completed=true、credentials_saved=true、identity_check=true；mail_delivery=owner_entered_matching_code、token_displayed=false、production_changed=false、local_test_only=true。没有重发、补造旧 challenge 状态、回显验证码或创建线上身份。测试结束关闭回环监听。

此前首封邮件真实收件通过但 HTTP 201 被误判，记录仍保留；本次为修复后新的 challenge，真实经过 start → 新码 → finish → 私密凭证 → 带 Bearer 的 GET /me，不复用旧码。具体缺陷与修复见[历史验证](validation-registration-local.md)。

## 发布检查

代码回归、干净 wheel 安装/卸载、发布包与固定 commit 一致性、GitHub CI 和开发备份按最终发布记录分别确认，未完成前不提前宣称通过。源码/Skill/wheel/升级脚本提供校验值；旧 Release/tag 不改动。

本地 Alpha5 候选完整回归 102 项：101 通过，1 项因目录符号链接权限不足跳过。干净虚拟环境安装 1.1.0a5 wheel 后，注册/私密凭证、既有 CLI 与合成宿主步骤、同版重装和卸载保留私密文件通过。升级脚本 bash -n 通过，Nginx/配置/旧记录保护三项模拟检查通过；不是生产部署或真实回滚演练。

## 可选功能与边界

显式运行器、检查点、停止/恢复、需求发现与宿主接口随源码保留；默认不会启动，也不会申请宿主管理权限。通用无人值守、所有 harness 自动唤起、V05、模型账户故障自动恢复都没有因此通过。旧 Windows 宿主清理曾遇文件占用，后续未复现不等于根因修复。

MCP 沿用个人 Bearer 而非完整平台 OAuth；文件任务的个人邮箱授权独立，平台验证邮箱不授权读取收件箱。免费交易/邮件测试不能证明支付需求、复购、独立邮箱认证或生产 SLA。

## 部署与剩余实测

用户选择在现有 SSH 窗口执行[升级步骤](deploy-alpha5.md)。在激活成功及读取公网 health 之前，不能把 GitHub 发布等同于线上升级。仍须公网新用户注册/旧凭证检查；更广泛 harness、独立新用户和生产回滚演练继续跟进。平台保持单服务和 SQLite。

### 实际上线确认（2026-11-09）

运营者报告已完成 prepare、私密配置上传和 activate。维护者独立读取公网：health.ok=true、version=1.1.0-alpha.5、mode=self-service-preview、self_registration=true；无凭证 GET /me 和 POST /mcp 均返回 401。部署所用固定提交/标签仍为 ccea7b2d4e648f69b5313081fab3c7cad0323897 / v1.1.0-alpha.5，本文档后续更新不移动该标签或改变线上代码。

持有人随后在自己的电脑执行外部公网新注册，使用全新测试身份 Alpha5PublicCheck，在终端隐藏输入生产服务发送的新验证码。维护者只读核对私密 report.json：status=passed、public_registration=true、credentials_saved=true、identity_check=true、server_version=1.1.0-alpha.5、token_displayed=false、tasks_created=false。该次注册使用公网 API，而非先前回环服务，不复用本地测试凭证。没有发布虚构任务或付款。

维护者使用本机原 AngelX 凭证只读调用公网 GET /me，认证成功且身份与升级前 ID 匹配；没有使用 Quincey/Richard 的凭证、改写旧身份或旧订单。旧数据库指纹检查由运营者的激活脚本负责，本次没有直接读取服务器数据库或猜测备份路径/当前账户数量。

结论：Alpha5 自主注册 MVP 已完成上线和首次公网注册验收。范围仍是用户主动启动的注册测试版；自动唤起保持显式可选实验，更广泛独立用户、交易复购与生产回滚演练继续跟进。API Key、验证码、个人 Token 和生产数据未写入本记录。
