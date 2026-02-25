# 10-webapi: Web API 兼容对象测试

验证 Maze 对 Web API 兼容对象的识别能力。

## 测试数据

| 对象类型 | 数量 | 说明 |
|----------|------|------|
| TextEncoder | 1,000 | UTF-8 编码器 |
| TextDecoder | 1,000 | UTF-8 解码器 |
| AbortController | 1,000 | 中止控制器 |
| Blob | 1,000 | 二进制大对象 |
| Headers | 1,000 | HTTP 头部 |
| Response | 1,000 | HTTP 响应 |
| Request | 1,000 | HTTP 请求 |
| FormData | 1,000 | 表单数据 |
| ReadableStream | 1,000 | 可读流 |
| WritableStream | 1,000 | 可写流 |

注意: 多数 Web API 对象是 C++ 后端实现，Maze 通过关联的 JS 对象间接识别。

## 文件说明

- `test.js` — 测试源代码
- `validate.py` — 验证脚本
- `coredump-*.tar.gz` — 打包的 coredump 文件

## 运行测试

```bash
python3 testdata/run_test.py nodejs/20260211-10-webapi
```
