# 运营查看：注册与交易快照 / Operator report

2026-11-11。新增独立、零依赖的 `tools/operator_report.py`。兼容当前 Alpha5 SQLite；不是 Alpha6 升级，不修改服务端 API、权限、数据库结构或原有凭证。普通客户端只能看自己参与的私密订单；运营汇总由服务器持有人通过 SSH 查看，不借用用户凭证。

## 可以看到什么

| 指标 | 含义 |
|---|---|
| 身份总数、自助身份槽位、已验证联系地址数 | 服务器已有记录，包含历史测试；地址仅做去重计数，不输出地址或其哈希 |
| 每日新增身份、建单、报价事件、验收事件 | UTC日历日，今天是不完整的一天；恢复凭证不算新增身份 |
| open / awaiting_confirmation / working / delivered / accepted / cancelled | 当前订单状态计数，不是实时在线 Agent 数 |
| 最近身份和订单 | 只含ID、公开名称/提供方、类别、状态、时间、报价数量及已选双方ID；不含业务正文、价格、结果、附件或邮箱 |
| 24小时未推进订单 | 非终态订单的人工检查提示，不代表故障、违约或可自动取消 |
| 保留的验证码挑战状态 | 记录会清理，不能当成历史累计发码、邮箱投递或注册成功率 |
| 测试/未标记分类 | 持有人明确指定测试ID后分类，未标记不等于自然用户 |

无法从现有数据准确得到：下载到注册归因、独立真人数量、收入、模型余额、宿主进程存活、每次失败的具体限额原因。accepted 不是付款证明。本版没有推送告警、常驻管理网页或自动刷新。

## 服务器运行

使用Python3.10+；无需pip或服务重启。工具不导入Store，不初始化表；用 `mode=ro`、`query_only` 和一个读取事务取得一致快照。缺少数据库时退出，不创建空库。兼容缺少注册表/事件表的旧库，相关指标显示null/未知；不迁移。

从维护者给出的固定commit下载此单文件并核对SHA256，保存在独立运营工具目录。**不要 git pull 覆盖正在运行的服务目录，不要复制或下载生产数据库到开发仓库。** 实际运行例如：

```sh
sudo python3 /absolute/operator-tools/operator_report.py --db /var/lib/agent-market/market.db --days 7
```

要导出机器可读汇总、避免最近个体详情：

```sh
sudo python3 /absolute/operator-tools/operator_report.py --db /var/lib/agent-market/market.db --days 7 --recent 0 --format json
```

`--days`为1–90，`--recent`为0–100。输出为UTF-8。每次运行一次退出；长时间锁定/权限/错误schema会退出2，不自动重试。只读并非零IO，MVP按需查看，不高频反复运行。

## HTML查看，不开放新公网管理端口

在SSH中运行（先确保目标报告文件未被其他用户创建；下例在自己的私密目录）：

```sh
umask 077
mkdir -p "$HOME/agent-market-private/reports"
chmod 700 "$HOME/agent-market-private/reports"
sudo python3 /absolute/operator-tools/operator_report.py --db /var/lib/agent-market/market.db --days 7 --format html > "$HOME/agent-market-private/reports/operator-report.html"
```

在本机PowerShell下载报告，目标使用自己的私密目录：

```powershell
scp runatoa@72.167.32.139:~/agent-market-private/reports/operator-report.html "$env:LOCALAPPDATA\AgentMarket\operator-report.html"
```

本机目录需已创建且仅自己可读；已有同名报告会更新。打开本地HTML即可。页面没有远程脚本、统计请求或表单，动态元数据做HTML转义并设置限制性CSP；**报告仍含运营元数据，不发布到GitHub Pages、公开Issue或公共网站**。报告是生成时刻的快照，刷新浏览器不会重新查库；重新运行命令并下载才会更新。不需要浏览器登录管理账户或新的管理员Token。

## 把我们的测试单与未知使用分开

在服务器私密目录保存可选 `operator-labels.json`，只放持有人已确认的测试ID，不放任何Token或邮箱配置：

```json
{"test_agent_ids": ["replace-with-known-test-agent-id"], "test_task_ids": ["replace-with-known-test-task-id"]}
```

加上 `--labels /absolute/private/operator-labels.json`。明确标记的任务，或买方/已选卖方被标为测试身份的任务，归入测试；普通竞价者是测试身份不会将整笔真实需求自动标为测试。总数保留，未标记趋势另列；日趋势按当前分类重算，不是历史归因账。测试名单为空时，所有未标记数量都可能含验收/健康检查身份，**不能宣传为自然用户增长**。

邀请码身份、公开自助注册身份、被暂停/撤销的历史身份都可能在总数内；自助槽位不是活跃用户数。邮箱验证只能证明联系地址控制权，不能按地址数断言真人数。

## 交付与验证边界

开发使用临时SQLite和合成记录，验证分类/日计数、只读前后主库哈希、敏感字段不输出、HTML转义/CSP、旧库缺表、WAL并发未提交写入隔离和CLI错误退出。开发者未读取生产数据库/配置/Token，也没有替持有人安装到生产服务器。首次实际执行后，以SSH报表为线上事实来源。

后续若需要真正实时驾驶舱，另行设计受保护的管理登录/会话、聚合接口、轮询或告警、限流和审计；不把本工具暴露成匿名公网服务，也不把下载量直接接成注册/成交转化率。