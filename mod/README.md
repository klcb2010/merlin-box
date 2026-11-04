# merlin-box mod layer

本目录保存 klcb2010 对 LandDuck/merlin-box 的注入式修改。

- 上游源码保持原样；构建/同步时由 apply.py 对工作树应用可重复的定点修改。
- 上游同步只以正式、非预发布 Release 的 tag 为准。
- .github/workflows/ 和根目录 README 在同步时排除，已有 Actions 不会被覆盖。
- upstream-release.txt 记录最后成功同步的上游 Release tag。

## 当前注入内容

1. AnyTLS：订阅 URI 转换及 Web UI 节点导入，复用上游已有 AnyTLS 数据模型和出站结构。
2. 订阅拉取：对常见订阅服务的 User-Agent 做有限回退；URL 的路径后缀（包括 .jpg）和查询参数（包括 route=1）原样保留，不擅自改写链接。

过滤/排序 UI 属于独立的大改造，待订阅导入链路稳定后再实施。
