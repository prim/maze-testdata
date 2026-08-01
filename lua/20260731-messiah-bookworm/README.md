# Lua Messiah Bookworm Fixture

**日期**: 2026-07-31
**目标**: 使用真实 H72 Lua 5.4.2 与 `asiocore.so` 回归 Messiah shared_ptr、property、map/list 和路径分类。

## 覆盖范围

- `area_map` 子类固定 `int/float/str/bool` property。
- `area_map` / `area_list` 中的 simple value。
- list 的 `VALUE_TYPE` 指向带固定 property 的 map 子类。
- map/list 多层嵌套以及 `%d` list path 归一化。
- generic map/list 按 property path 拆分。
- list 自身声明固定 property 不会物化；后续赋值只是普通运行时属性。
- phmap、fix-props vector、shared_ptr control block 深层 ownership。
- 真实 `space_wrapper -> area -> entity -> area_impl.props_` 在线 ownership 链。
- `area_map` 固定 scalar、嵌套 map、typed list 和 generic map 经 `entity.mimpl_` 读取。

fixture 创建 96 个 player entity、64 个 NPC entity、16 个挂入 area/world 的 online entity，以及
对应的 property tree。Lua 全局 `MESSIAH_FIXTURE` 保持 entity、area、props、space 和 holder 的强引用，
直到 `maze-gen-coredump.py` 完成抓取。

## 直接执行

在 Maze 主仓库根目录执行：

```bash
git -C testdata lfs pull --include='lua/20260731-messiah-bookworm/*.tar.gz'
python3 testdata/run_test.py lua/20260731-messiah-bookworm
```

runner 会依次执行 Maze tar workflow、生成 `maze-result.json`、加载 `validate.py`。validator 检查：

- entity 和主要 property path 的精确数量；
- 6 种 Messiah native binding 的精确数量；
- `shallow_fallback=0`；
- `Unknown=0B`；
- `CountGoroutineError: 0`；
- `diff(alloc-mpm)=0B`。

手工执行等价流程：

```bash
./maze --tar testdata/lua/20260731-messiah-bookworm/coredump-*.tar.gz \
  --text --json-output --rmlog --limit 500 | tee ./tmp/messiah-test-output.log

MAZE_TEST_MAZE_LOG="$PWD/maze.log" \
MAZE_TEST_OUTPUT_LOG="$PWD/tmp/messiah-test-output.log" \
python3 testdata/lua/20260731-messiah-bookworm/validate.py maze-result.json
```

## Property 脚本

完整对象代码在 `fixture.lua`。核心规则是 map 可以定义固定 property：

```lua
local Item = class("FixtureItem", asiocore.area_map)
Item.__property_all__ = dict(item_id=0, name="", count=0)
Item.__property_flag__ = dict()
class_ready(Item)
```

list 自身没有具名固定 property。需要“list 元素带 property”时，让 `VALUE_TYPE` 指向 map class：

```lua
local Inventory = class("FixtureInventory", asiocore.area_list)
Inventory.VALUE_TYPE = Item
Inventory.__property_all__ = dict()
Inventory.__property_flag__ = dict()
class_ready(Inventory)
```

`fixture.lua` 中的 `verify_list_property_boundary()` 还会在输出 `READY FOR GCORE` 前验证 list 上伪造的
`label/count` 默认值仍为 `nil`，且不进入 `debug_get_prop_types()`。

## 在线 ownership 脚本

`area` 构造函数和 space 挂接不是常规对象赋值。生产 `asiocore.so` 的实际 Lua 契约是：

```lua
local space = WorldSpace("fixture-world", 1001, holder, dict())
local entity = OnlineEntity()
local area = OnlineArea("FixtureOnlineEntity", false, entity, 0)

entity:set_area(area)
area:set_space("fixture-world")

local props = area:prop()
props.health = 5001
props.nested.score = 10

assert(area:owner() == entity)
assert(entity:get_area() == area)
assert(area:get_space() == "fixture-world")
assert(entity.health == props.health)
assert(entity.nested == props.nested)

props.health = props.health + 1       -- native property 的正式写入口
assert(entity.health == props.health)

local native_health = props.health
entity.health = native_health + 100000
assert(props.health == native_health) -- 只是 entity 的 Lua 动态字段
assert(entity.health ~= props.health) -- 同名动态字段遮蔽 mimpl_ 读取
```

`area:set_space()` 接受 space id 字符串，不接受 `space_wrapper` Instance；`area:get_space()` 也返回
字符串。`entity:set_area()` 建立 `entity.area_` 和 `entity.mimpl_`，因此 entity 能读取
`area_impl.props_` 的同一对象图。fixture 从 `area:prop()` 写 native property；直接写
`entity.health` 会成为普通 Lua 动态字段，不代表写回 native property。
`asiocore.entity` 的 Lua method 表也没有 native setter；读路径和写路径有意不对称：entity 经
`mimpl_` 读取，写入必须经 `entity:get_area():prop()`（或已保存的 `props`）完成。fixture 会先写
`props` 并由 entity 读取，随后只在第一个在线 entity 上写同名动态字段，确认 native 值未变且读取
被遮蔽。生产扩展中再赋 `nil` 也不能可靠恢复这个 fallback，因此业务代码不应直接写 property 同名
的 entity 字段。

## 重新构造 fixture

### 环境证据

生产 core 的 libc banner 是 `Debian GLIBC 2.36-9+deb12u4`。构造镜像固定为：

```text
debian:bookworm-20240211-slim
sha256:d02c76d82364cedca16ba3ed6f9102406fa9fa8833076a609cabf14270f43dfc
```

`Dockerfile` 把 APT 固定到 2024-02-11 Debian snapshot，只安装抓 core 所需的 Python/GDB，避免
`apt update` 把运行时升级到其他 libc revision。

`prepare_runtime.py` 同时固定 H72 manifest 中的 loader MD5
`395f1f15882967bfbff866832ccac983`；该文件的 banner 是
`Debian GLIBC 2.36-9+deb12u4`，与 libc 和固定镜像一致。

### 从已提交 fixture 恢复运行时

这是日常刷新方式。`prepare_runtime.py` 读取 tar 内的 `*.md5` manifest，按 MD5 校验并恢复
`lua`、`asiocore.so`、jemalloc 和依赖库：

```bash
python3 testdata/lua/20260731-messiah-bookworm/prepare_runtime.py
python3 testdata/lua/20260731-messiah-bookworm/generate_fixture.py
```

新文件生成到 `./tmp/h72-messiah-generated/`，不会直接覆盖已提交 fixture。

### 从原始 H72 job 首次构造

先按 Maze UUID workflow 下载 job，使 `27020.md5` 和 ELF cache 可用，再执行：

```bash
python3 testdata/lua/20260731-messiah-bookworm/generate_fixture.py \
  --manifest db/h72-n7910ljw-27020/27020.md5 \
  --elf-dir db/elf
```

生成器执行链：

1. `prepare_runtime.py` 恢复并逐文件校验 H72 运行时；
2. 构建固定 Debian snapshot 容器；
3. `exec_fixture.py` 用 `execve` 启动生产 Lua，避免 `stdbuf` 注入额外共享库；
4. `fixture.lua` 创建对象并输出 `READY FOR GCORE`；
5. 标准 `cmd/maze-gen-coredump.py` 执行 gcore、maps/ELF 收集和 tar 打包；
6. 输出写入仓库内 `./tmp/`，不使用宿主 `/tmp`。

生成新 tar 后，先用手工命令重放并验证，再替换本目录旧 tar。tar 由 Git LFS 管理。

当前提交 fixture：

```text
file:   coredump-59-1785543643.tar.gz
size:   226,741,195 bytes
sha256: d80ac1641c35196c93d4c5dcbc7c24c94e83e02ba326edae81e0859c43ad48bf
```

其正式基线为 `area=16`、`area_map=1850`、`area_list=1374`、
`area_prop_index_obj=7`、`entity=176`、`space_wrapper=1`，共 `3424` 个 Messiah native
bindings。在线 schema 的 class/default 对象使 `FixtureOnlineNested` 和 `FixtureOnlineNumbers`
各为 17 个：1 个 schema 实例加 16 个在线对象实例。

## 文件说明

| 文件 | 作用 |
|---|---|
| `fixture.lua` | 完整 Messiah entity/property/container 构造代码 |
| `validate.py` | 结果、日志、计数和守恒验证 |
| `prepare_runtime.py` | 从 tar 或 Maze ELF cache 恢复生产运行时 |
| `exec_fixture.py` | 无额外 preload 的 Python-to-Lua exec wrapper |
| `generate_fixture.py` | Docker build + 标准 coredump 生成编排 |
| `Dockerfile` | 精确 Debian snapshot 与抓取工具环境 |
| `coredump-*.tar.gz` | 由真实生产 Lua/asiocore 生成的 Git LFS fixture |
