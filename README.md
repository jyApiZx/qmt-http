# qmt-http

# 通达信/同花顺纯协议接口

**提供通达信/同花顺纯协议接口，支持大部分券商。接入请联系 Telegram：`JyApi888`。**

完整函数表和各语言示例见 [stockapi](https://github.com/jyApiZx/stockapi)。

大 QMT 内置策略常常不能读写外部文件，系统环境变量也读不到。配置、股票池、买卖信号和日志改走 HTTP，策略里只保留地址和 token 两个常量。

调用形式与大 QMT 里常见的 HTTP 取数一致：向 `http://主机:端口/tq?token=...` 发送

```json
{"method": "接口名", "params": {}}
```

MiniQMT 已不可用，本仓库不依赖 xtquant。交易和 L2 行情（十档、逐笔成交、逐笔委托）使用上面的纯协议接口。

## 能读写文件的那台机器

```text
python server.py
```

首次运行会在当前目录生成 `token.txt`。编辑 `config.json` 和 `signal.json` 后，策略通过接口读取，不必把这两个文件拷进 QMT。

| 方法 | 作用 |
| --- | --- |
| `get_config` | 账号、股票池、参数 |
| `get_signal` | 当日买卖信号 |
| `put_log` | 把一行结果交给服务端写入 `logs/` |

`GET /ping?token=` 用来确认服务已经起来。token 不对或 HTTP 失败时，客户端直接抛错，策略应停止当次调仓。

## 粘贴进大 QMT

1. 把 `qmt_http.py` 放到策略能 import 的目录。若平台只允许一个策略文件，把 `QmtHttp` 类贴到策略开头。
2. 打开 `strategy_template.py`，填入主机、端口和 `token.txt` 里的 token。文件头是 `#coding:gbk`，保存时用 GBK。
3. 在 `init` 里调用 `get_config`，在 `handlebar` 里调用 `get_signal`。策略代码里不要 `open` 配置或信号文件。

```python
from qmt_http import QmtHttp

http = QmtHttp("YOUR_HTTP_HOST", 17710, "YOUR_TOKEN")
http.ping()
config = http.call("get_config", {})["result"]
signal = http.call("get_signal", {})["result"]
http.call("put_log", {"text": "ok"})
```

服务默认监听 `0.0.0.0:17710`。跨机器访问时在服务所在系统放行该端口。token 出现在 URL 上，只在可信网络里使用。
