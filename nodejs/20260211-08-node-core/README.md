# 08-node-core: Node.js 核心模块对象测试

验证 Maze 对 Node.js 核心模块对象的识别能力。

## 测试数据

| 对象类型 | 数量 | 说明 |
|----------|------|------|
| EventEmitter | 1,000 | 带 2 个事件监听器 |
| Stream.Readable | 1,000 | 可读流 |
| Stream.Writable | 1,000 | 可写流 |
| Stream.Transform | 1,000 | 转换流 |
| URL | 1,000 | URL 对象 |
| URLSearchParams | 1,000 | URL 查询参数 |
| crypto.Hash | 1,000 | SHA256 哈希 |
| zlib.Gzip | 1,000 | Gzip 压缩流 |
| vm.Script | 1,000 | VM 脚本 |
| MessageChannel | 1,000 | 消息通道 |

## 文件说明

- `test.js` — 测试源代码
- `validate.py` — 验证脚本
- `coredump-*.tar.gz` — 打包的 coredump 文件

## 运行测试

```bash
python3 testdata/run_test.py nodejs/20260211-08-node-core
```
