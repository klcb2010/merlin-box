#!/usr/bin/env python3
"""Apply klcb2010's repeatable source injections to an upstream checkout."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    file_path = ROOT / path
    source = file_path.read_text(encoding="utf-8")
    if new.strip() in source:
        return
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one patch anchor, found {count}")
    file_path.write_text(source.replace(old, new, 1), encoding="utf-8")


def patch_python() -> None:
    path = "tools/sub2box/main.py"
    file_path = ROOT / path
    source = file_path.read_text(encoding="utf-8")
    old_fetch = '''def fetch_subscription(url: str, timeout: int = 15) -> str:
    """拉取订阅内容"""
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"
    }
    print_success(f"正在拉取订阅: {url}")
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text.strip()
'''
    new_fetch = '''def fetch_subscription(url: str, timeout: int = 15) -> str:
    """拉取订阅内容；保留原始 URL 路径和查询参数，并兼容常见订阅 UA。"""
    user_agents = [
        "clash.meta",
        "v2rayNG/1.9.38",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
    ]
    headers = {"Accept": "*/*", "Cache-Control": "no-cache"}
    print_success(f"正在拉取订阅: {url}")
    last_error = None
    for user_agent in user_agents:
        try:
            response = requests.get(
                url,
                headers={**headers, "User-Agent": user_agent},
                timeout=timeout,
                allow_redirects=True,
            )
            if response.status_code in (401, 403, 406, 429) or response.status_code >= 500:
                last_error = requests.HTTPError(
                    f"HTTP {response.status_code} with User-Agent {user_agent}",
                    response=response,
                )
                continue
            response.raise_for_status()
            return response.text.strip()
        except requests.RequestException as exc:
            last_error = exc
    raise last_error or RuntimeError("订阅请求失败")
'''
    if "mod: klcb subscription-fetch-fallback" not in source:
        if source.count(old_fetch) != 1:
            raise RuntimeError(f"{path}: fetch_subscription anchor not found uniquely")
        source = source.replace(old_fetch, new_fetch + "\n# mod: klcb subscription-fetch-fallback\n", 1)

    parse_anchor = '''def parse_uri(uri: str) -> Dict[str, Any] | None:
    """统一解析各种协议 URI"""
'''
    anytls_func = '''def parse_anytls(uri: str) -> Dict[str, Any] | None:
    """解析 anytls:// 并生成 sing-box anytls outbound。"""
    try:
        parsed = urlparse(uri)
        password = unquote(parsed.username or "")
        server = parsed.hostname
        port = parsed.port or 443
        if not password or not server:
            raise ValueError("AnyTLS URI 缺少密码或服务器")
        if is_local_ip(server):
            print_warning(f"跳过本地 IP 节点: {server}")
            return None
        query = parse_qs(parsed.query)
        sni = query.get("sni", [server])[0] or server
        name = unquote(parsed.fragment) if parsed.fragment else f"anytls-{server}"
        return {
            "type": "anytls",
            "tag": name,
            "server": server,
            "server_port": port,
            "password": password,
            "tls": {"enabled": True, "server_name": sni},
        }
    except Exception:
        print_warning(f"跳过无法解析的 AnyTLS URI: {uri}")
        return None


'''
    if "def parse_anytls(" not in source:
        if source.count(parse_anchor) != 1:
            raise RuntimeError(f"{path}: parse_uri anchor not found uniquely")
        source = source.replace(parse_anchor, anytls_func + parse_anchor, 1)

    branch_anchor = '''    if uri.startswith("ss://"):
        return parse_ss(uri)
'''
    branch_new = '''    if uri.startswith("anytls://"):
        return parse_anytls(uri)
    if uri.startswith("ss://"):
        return parse_ss(uri)
'''
    if "return parse_anytls(uri)" not in source:
        if source.count(branch_anchor) != 1:
            raise RuntimeError(f"{path}: protocol dispatch anchor not found uniquely")
        source = source.replace(branch_anchor, branch_new, 1)
    file_path.write_text(source, encoding="utf-8")



def patch_go_fetch() -> None:
    path = "ui/server/tools/helper.go"
    old = '''// fetchSubscription 拉取订阅链接内容并返回去除首尾空白后的文本。
func fetchSubscription(rawURL string, timeout time.Duration) (string, error) {
	headers := map[string]string{
		"User-Agent": "clash.meta",
	}
	logger.Success("正在拉取订阅: " + rawURL)
	req, err := http.NewRequest(http.MethodGet, rawURL, nil)
	if err != nil {
		return "", err
	}
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	client := &http.Client{Timeout: timeout}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return "", fmt.Errorf("HTTP 请求失败: %s", resp.Status)
	}
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(body)), nil
}
'''
    new = '''// fetchSubscription 拉取订阅链接内容；不根据扩展名改写 URL，完整保留查询参数。
func fetchSubscription(rawURL string, timeout time.Duration) (string, error) {
	logger.Success("正在拉取订阅: " + rawURL)
	userAgents := []string{
		"clash.meta",
		"v2rayNG/1.9.38",
		"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
	}
	client := &http.Client{Timeout: timeout}
	var lastErr error
	for _, userAgent := range userAgents {
		req, err := http.NewRequest(http.MethodGet, rawURL, nil)
		if err != nil {
			return "", err
		}
		req.Header.Set("User-Agent", userAgent)
		req.Header.Set("Accept", "*/*")
		req.Header.Set("Cache-Control", "no-cache")
		resp, err := client.Do(req)
		if err != nil {
			lastErr = err
			continue
		}
		if resp.StatusCode == http.StatusUnauthorized ||
			resp.StatusCode == http.StatusForbidden ||
			resp.StatusCode == http.StatusNotAcceptable ||
			resp.StatusCode == http.StatusTooManyRequests ||
			resp.StatusCode >= 500 {
			lastErr = fmt.Errorf("HTTP 请求失败: %s (User-Agent: %s)", resp.Status, userAgent)
			resp.Body.Close()
			continue
		}
		if resp.StatusCode < 200 || resp.StatusCode >= 300 {
			status := resp.Status
			resp.Body.Close()
			return "", fmt.Errorf("HTTP 请求失败: %s", status)
		}
		body, readErr := io.ReadAll(resp.Body)
		resp.Body.Close()
		if readErr != nil {
			lastErr = readErr
			continue
		}
		return strings.TrimSpace(string(body)), nil
	}
	if lastErr == nil {
		lastErr = fmt.Errorf("订阅请求失败")
	}
	return "", lastErr
}
'''
    replace_once(path, old, new)


def patch_go_parser() -> None:
    path = "ui/server/tools/sub2box.go"
    parse_anchor = '''// parseURI 按协议分发 URI 到对应解析函数。
func parseURI(uri string) map[string]any {
'''
    anytls_func = '''// parseAnyTLS 解析 anytls:// URI 并转换为 sing-box AnyTLS outbound。
func parseAnyTLS(rawURI string) map[string]any {
	u, err := url.Parse(rawURI)
	if err != nil || u.Hostname() == "" || u.User == nil {
		logger.Warn("跳过无法解析的 AnyTLS URI: " + rawURI)
		return nil
	}
	password, hasPassword := u.User.Password()
	if !hasPassword || password == "" {
		password = u.User.Username()
	}
	if password == "" {
		logger.Warn("跳过密码为空的 AnyTLS URI: " + rawURI)
		return nil
	}
	server := u.Hostname()
	if isLocalIP(server) {
		logger.Warn("跳过本地 IP AnyTLS 节点: " + server)
		return nil
	}
	port := 443
	if p := u.Port(); p != "" {
		n, parseErr := strconv.Atoi(p)
		if parseErr != nil || n < 1 || n > 65535 {
			logger.Warn("跳过端口无效的 AnyTLS URI: " + rawURI)
			return nil
		}
		port = n
	}
	name, _ := url.QueryUnescape(u.Fragment)
	if name == "" {
		name = "anytls-" + server
	}
	sni := u.Query().Get("sni")
	if sni == "" {
		sni = server
	}
	return map[string]any{
		"type":        "anytls",
		"tag":         name,
		"server":      server,
		"server_port": port,
		"password":    password,
		"tls": map[string]any{
			"enabled":     true,
			"server_name": sni,
		},
	}
}

'''
    replace_once(path, parse_anchor, anytls_func + parse_anchor)
    branch_anchor = '''	case strings.HasPrefix(uri, "ss://"):
		return parseSS(uri)
'''
    branch_new = '''	case strings.HasPrefix(uri, "anytls://"):
		return parseAnyTLS(uri)
	case strings.HasPrefix(uri, "ss://"):
		return parseSS(uri)
'''
    replace_once(path, branch_anchor, branch_new)


def patch_go_node_import() -> None:
    path = "ui/server/tools/sub2nodes.go"
    save_anchor = '''// getOutboundField 从 outbound 中按 key 取出子配置并转换为指定类型，缺失或解析失败时返回零值
'''
    save_func = '''// saveAnytlsNode 将 AnyTLS outbound 保存到订阅分组。
func saveAnytlsNode(outbound map[string]any, category string) bool {
	password, _ := outbound["password"].(string)
	tls := getOutboundField[db.TLSConfig](outbound, "tls")
	nodeBase := getNodeBase("anytls", category, outbound)
	if nodeBase == nil {
		logger.Error("保存 AnyTLS 节点失败: 无法解析服务器地址")
		return false
	}
	node := db.AnytlsNode{
		NodeBase: *nodeBase,
		Password: password,
		NodeTls:  db.NodeTls{Tls: tls},
	}
	return persistNode(node.NodeBase, node)
}

'''
    replace_once(path, save_anchor, save_func + save_anchor)
    switch_anchor = '''			case "vless":
				if saveVlessNode(outbound, category) {
					writeNodes++
				}
'''
    switch_new = '''			case "anytls":
				if saveAnytlsNode(outbound, category) {
					writeNodes++
				}
			case "vless":
				if saveVlessNode(outbound, category) {
					writeNodes++
				}
'''
    replace_once(path, switch_anchor, switch_new)



def patch_node_list() -> None:
    path = "ui/front/scripts-dev/pages/home/NodeList.js"
    state_anchor = '''        this.state = {
            nodeList: []
        };
'''
    state_new = '''        this.state = {
            nodeList: [],
            keyword: "",
            typeFilter: "all",
            sortBy: "default"
        };
'''
    replace_once(path, state_anchor, state_new)

    render_anchor = '''    render() {
        const components = [];
'''
    render_new = '''    render() {
        const components = [];
        const {nodeList, keyword, typeFilter, sortBy} = this.state;
        const query = keyword.trim().toLowerCase();
        const types = Array.from(new Set(nodeList.map(node => node.type).filter(Boolean))).sort();
        const typeOptions = [
            {value: "all", label: "全部协议"},
            ...types.map(type => ({value: type, label: type.toUpperCase()}))
        ];
        const sortOptions = [
            {value: "default", label: "默认顺序"},
            {value: "name", label: "名称 A-Z"},
            {value: "name_desc", label: "名称 Z-A"},
            {value: "server", label: "服务器 A-Z"},
            {value: "type", label: "协议类型"}
        ];
        const visibleNodes = nodeList.filter(node => {
            const matchesType = typeFilter === "all" || node.type === typeFilter;
            const searchable = [node.name, node.server, node.type]
                .filter(Boolean).join(" ").toLowerCase();
            return matchesType && (!query || searchable.includes(query));
        });
        if (sortBy !== "default") {
            visibleNodes.sort((a, b) => {
                if (!!a.is_default !== !!b.is_default) {
                    return a.is_default ? -1 : 1;
                }
                const left = String(
                    sortBy === "server" ? a.server :
                    sortBy === "type" ? a.type : a.name
                ).toLowerCase();
                const right = String(
                    sortBy === "server" ? b.server :
                    sortBy === "type" ? b.type : b.name
                ).toLowerCase();
                return sortBy === "name_desc"
                    ? right.localeCompare(left)
                    : left.localeCompare(right);
            });
        }
'''
    replace_once(path, render_anchor, render_new)

    toolbar_anchor = '''            <div className="node-list">
                {this.state.nodeList.map(node => this.#renderCard(node))}
'''
    toolbar_new = '''            <div className="node-filter-bar" style={{display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", marginBottom: 14}}>
                <antd.Input
                    placeholder="搜索节点名称、服务器地址或协议"
                    allowClear
                    value={keyword}
                    onChange={(event) => this.setState({keyword: event.target.value})}
                    style={{flex: "1 1 220px", minWidth: 180}}
                />
                <antd.Select
                    value={typeFilter}
                    onChange={(value) => this.setState({typeFilter: value})}
                    options={typeOptions}
                    style={{width: 130}}
                />
                <antd.Select
                    value={sortBy}
                    onChange={(value) => this.setState({sortBy: value})}
                    options={sortOptions}
                    style={{width: 130}}
                />
                <span style={{fontSize: 12, color: "#888", whiteSpace: "nowrap"}}>
                    显示 {visibleNodes.length} / {nodeList.length}
                </span>
            </div>
            <div className="node-list">
                {visibleNodes.length > 0
                    ? visibleNodes.map(node => this.#renderCard(node))
                    : <div style={{padding: 20, textAlign: "center", color: "#888"}}>没有符合条件的节点</div>}
'''
    replace_once(path, toolbar_anchor, toolbar_new)




def patch_fork_updater() -> None:
    replace_once(
        "merlin-box.sh",
        '      VERSION=$(get_github_latest_release "LandDuck/merlin-box")',
        '      VERSION=$(get_github_latest_release "klcb2010/merlin-box")',
    )
    replace_once(
        "sh/tool.sh",
        'local latest_version=$(get_github_latest_release "LandDuck/merlin-box")',
        'local latest_version=$(get_github_latest_release "klcb2010/merlin-box")',
    )
    replace_once(
        "sh/tool.sh",
        'https://github.com/LandDuck/merlin-box/releases/download/v\${latest_version}/',
        'https://github.com/klcb2010/merlin-box/releases/download/v\${latest_version}/',
    )

def main() -> None:
    patch_python()
    patch_go_fetch()
    patch_go_parser()
    patch_go_node_import()
    patch_node_list()
    patch_fork_updater()
    print("mod injections applied")


if __name__ == "__main__":
    main()
