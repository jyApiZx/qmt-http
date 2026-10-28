# 解除大 QMT 文件读写限制

# 同花顺交易接口

**同花顺交易接口，L1、L2 行情接口。直连券商，无需启动客户端，支持大部分券商。产品介绍见 [thsapi.com](https://thsapi.com/)。技术支持请联系 [Telegram：@Thsapi](https://t.me/Thsapi)**

不点屏幕，不抢鼠标，程序直接连券商。下载后用模拟盘就能测查询、下单和撤单。已经有项目时，打开 [AI 代做提示词](https://thsapi.com/ai.html)，把提示词交给正在改项目的 AI。行情有 L1，也有十档、买卖队列和逐笔。

账户安全说明：接口不上传交易密码、持仓、委托或成交；本地授权不连接授权服务器。价格和开通方式见 [官网授权方式](https://thsapi.com/#license)。完整的联网范围、安全测试和自行核验方法见 [账户安全与授权](https://thsapi.com/security.html)。这里说的是 DLL 授权；本仓库的 HTTP 服务仍应使用 token，并只部署在可信网络中。

大 QMT 内置策略不能读写外部文件，配置、股票池、买卖信号和日志也读不到。本仓库用 HTTP 把这些内容放到另一台机器上，策略里只保留地址和 token，不再打开本地文件。

调用形式与大 QMT 里常见的 HTTP 取数一致：向 `http://主机:端口/tq?token=...` 发送

```json
{"method": "接口名", "params": {}}
```

配置、信号和日志不依赖 DLL。服务目录里放了 `thsapi.dll` 之后，才可以用下面的交易方法。没放 DLL 时，这几个方法会返回找不到文件，原来的三个方法不受影响。

交易用同花顺交易接口，程序直接连券商。客户端下单慢，界面操作也容易漏单、错单。`thsapi.dll` 用来把下单、撤单和查询做准、做快。交易包：[64 位](https://github.com/jyApiZx/stockapi/releases/download/v1.0.6.2/thsapi_1.0.6.2_x64.zip)、[32 位](https://github.com/jyApiZx/stockapi/releases/download/v1.0.6.2/thsapi_1.0.6.2_x32.zip)。说明见 [stockapi](https://github.com/jyApiZx/stockapi)。先调用 `login`，再查资金和持仓。

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
| `login` | 有 `thsapi.dll` 时登录券商 |
| `balance` | 查资金 |
| `positions` | 查持仓 |
| `orders` | 查当日委托 |
| `send_order` | 下单 |
| `cancel_order` | 撤单 |

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
