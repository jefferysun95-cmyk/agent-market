# Glama 专用测试身份健康验收 / Authenticated health check

日期2026-11-11；服务仍1.1.0-alpha.5，冻结完整插件仍0.1.0-alpha.3。当前技术标识和品牌不变。

## 实际结果

- 公开条目：https://glama.ai/mcp/connectors/io.github.jefferysun95-cmyk/agent-market 。Ownership verified。
- Test Profile：Authentication Type=API Key；Location=Bearer Authentication；API Key Configured。凭证只填Token本身，Glama组装Bearer头；没有写入公开元数据或仓库。
- 管理页最后测试：2026-11-11 **13:19:55 UTC+8**，success / Healthy，836ms。
- 公开概览：**Status Healthy**；Streamable HTTP；协商MCP 2025-11-25；**Available Tools 20**。TDQS当时仍显示Score is being calculated，不声称评分已完成。

## 授权与操作

持有人明确同意创建独立、无业务数据的Glama Health Check身份，并把其新凭证仅保存到Glama Test Profile。通过现有公开自助注册流程：持有人本机隐藏输入新验证码；新凭证独立ACL私密落盘；/me验证名称与capabilities=[]，未使用AngelX、Richard、Quincey等旧业务凭证。

浏览器执行器不能读取该受限文件，且其虚拟剪贴板与本机剪贴板隔离；持有人从临时本机剪贴板手工粘贴并保存。保存后Glama自动测试成功，未再重复点击测试；随后仅在剪贴板仍匹配专用Token时清空。验证码、Token、邮件正文和客户端配置未出现在报告/仓库/备份。

## 证据边界与维护

Glama的Test credentials and health-check safety说明：健康检查初始化MCP，列出工具、提示和资源（含分页）；不调用tools/call、不读resources/read、不执行prompts/get、不请求AI采样。本轮按此范围授权；我们没有执行交易工具、发单、报价、邮箱业务或付款。公开20工具是元数据发现，不是逐工具功能/交易验收。

当前普通Agent Token**没有只读权限范围限制**。capabilities=[]表示未登记供给能力，不收窄API权限；专用空身份、Glama检查行为声明和服务端强制最小权限必须区分。不得把测试凭证作为公共共享身份/用户安装凭证。后续若发现业务调用、凭证泄漏或权限范围变化，应由运营者撤销该专用身份访问并重做授权，不复用其他业务凭证。当前未新增自动轮换或只读scope功能。

初始None鉴权测试HTTP401已查明。成功时公开24小时uptime显示7.1%，包含此前匿名探测失败；这是Glama检查历史比例，不能当作平台实际服务故障率或长期SLA。旧失败保留，不删除历史来美化结果。

## 本机证据（不打包秘密）

公开Healthy与20工具截图、管理页success截图保存于Git外work/distribution-completion；开发交接仅收录本说明与公开资料，不纳入专用Token、注册session、验证码或原始私密配置。GitHub提交/CI与源码备份在文档交付中另行记录；无服务代码部署或冻结资产替换。
