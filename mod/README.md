# merlin-box mod layer

本目录保存 klcb2010 对 LandDuck/merlin-box 的注入式修改。

- 上游源码保持原样；构建/同步时由 apply.py 对工作树应用可重复的定点修改。
- 上游同步只以正式、非预发布 Release 的 tag 为准。
- .github/workflows/ 和根目录 README 在同步时排除，已有 Actions 不会被覆盖。
- upstream-release.txt 记录最后成功同步的上游 Release tag。

## 当前注入内容

1. AnyTLS：订阅 URI 转换及 Web UI 节点导入，复用上游已有 AnyTLS 数据模型和出站结构。
2. 订阅拉取：对常见订阅服务的 User-Agent 做有限回退；URL 的路径后缀（包括 .jpg）和查询参数（包括 route=1）原样保留，不擅自改写链接。
3. 节点列表：增加本地关键字搜索、协议筛选、名称/服务器/协议排序，并始终将默认节点置顶。
4. 路由器更新：更新检查和安装包下载改为指向 klcb2010/merlin-box，避免用户更新时被上游版本覆盖魔改。
5. 版本号：在上游版本后追加 .1 作为本仓库补丁版本，确保同一上游 Release 下的后续魔改版本仍可正常升级。
