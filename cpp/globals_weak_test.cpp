/**
 * C++ 全局符号与弱分类测试
 *
 * 测试目的：
 *   验证 Maze 能正确收集全局/静态变量（CollectGlobal），
 *   以及对无 vtable 的 malloc 块进行弱分类（指针链追踪、嵌入 vtable 检测）。
 *
 * 内存布局：
 *   - 全局对象 g_config (Config 类，有 vtable + vector<string>)
 *   - 全局 vector g_id_pool (10000 个 int)
 *   - 全局 unordered_map g_registry (5000 个 kv，value 指向 Record*)
 *   - 5000 个 Record 实例（有 vtable）
 *   - 5000 个 Point3D 实例（无 vtable，纯 POD，通过 g_registry 指针可追踪）
 *   - 1000 个 Node 链表节点（无 vtable，有 next 指针链）
 *
 * 编译命令：
 *   g++ -g -O0 -std=c++11 -o globals_weak_test globals_weak_test.cpp
 *
 * 使用方法：
 *   1. 编译并运行
 *   2. 看到 ">>> READY FOR GCORE <<<" 后执行 gcore
 *   3. 使用 maze-tar-coredump.py 打包
 */

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unistd.h>
#include <vector>
#include <string>
#include <unordered_map>

// 有 vtable 的配置类 — 测试全局符号收集
class Config
{
public:
    int max_connections;
    int timeout_ms;
    std::vector<std::string> server_list;
    virtual ~Config() {}
};

// 有 vtable 的记录类
class Record
{
public:
    int id;
    double score;
    std::string label;
    virtual ~Record() {}
};

// 无 vtable 的纯 POD — 测试弱分类
struct Point3D
{
    double x, y, z;
};

// 无 vtable 但有指针 — 测试弱分类的指针链追踪
struct Node
{
    int value;
    Node *next;
};

// =========================================================
// 全局变量 — 测试 CollectGlobal
// =========================================================
Config g_config;
static std::vector<int> g_id_pool;
static std::unordered_map<int, Record *> g_registry;

// 保存堆分配指针防止被优化掉
std::vector<Point3D *> g_points;
Node *g_list_head = nullptr;

int main()
{
    printf("============================================================\n");
    printf("C++ Globals & Weak Classification Test - PID: %d\n", getpid());
    printf("============================================================\n");

    const int N_RECORD = 5000;
    const int N_POINT = 5000;
    const int N_NODE = 1000;

    printf("\nAllocating objects...\n");
    printf("  - 1 global Config (with vector<string>)\n");
    printf("  - 1 global vector<int> (10000 ints)\n");
    printf("  - 1 global unordered_map<int, Record*> (%d entries)\n", N_RECORD);
    printf("  - %d Record instances (with vtable)\n", N_RECORD);
    printf("  - %d Point3D instances (no vtable, POD)\n", N_POINT);
    printf("  - %d Node linked list (no vtable, pointer chain)\n", N_NODE);

    // Phase 1: 初始化全局 Config
    printf("\n[Phase 1] Initializing g_config...\n");
    g_config.max_connections = 1024;
    g_config.timeout_ms = 30000;
    for (int i = 0; i < 100; i++)
    {
        char buf[64];
        snprintf(buf, sizeof(buf), "server_%03d.example.com:8080", i);
        g_config.server_list.push_back(buf);
    }
    printf("  Done: g_config.server_list.size() = %zu\n",
           g_config.server_list.size());

    // Phase 2: 填充全局 g_id_pool
    printf("\n[Phase 2] Filling g_id_pool...\n");
    g_id_pool.reserve(10000);
    for (int i = 0; i < 10000; i++)
        g_id_pool.push_back(i);
    printf("  Done: g_id_pool.size() = %zu\n", g_id_pool.size());

    // Phase 3: Record 实例 + g_registry
    printf("\n[Phase 3] Allocating Record instances...\n");
    for (int i = 0; i < N_RECORD; i++)
    {
        Record *r = new Record();
        r->id = i;
        r->score = i * 1.5;
        char buf[64];
        snprintf(buf, sizeof(buf), "record_label_%05d_padding", i);
        r->label = buf;
        g_registry[i] = r;

        if ((i + 1) % 1000 == 0)
            printf("  Progress: %d/%d\n", i + 1, N_RECORD);
    }
    printf("  Done: g_registry.size() = %zu\n", g_registry.size());

    // Phase 4: Point3D 实例（无 vtable，纯 POD）
    printf("\n[Phase 4] Allocating Point3D instances...\n");
    g_points.reserve(N_POINT);
    for (int i = 0; i < N_POINT; i++)
    {
        Point3D *p = new Point3D();
        p->x = i * 0.1;
        p->y = i * 0.2;
        p->z = i * 0.3;
        g_points.push_back(p);

        if ((i + 1) % 1000 == 0)
            printf("  Progress: %d/%d\n", i + 1, N_POINT);
    }
    printf("  Done: g_points.size() = %zu\n", g_points.size());

    // Phase 5: Node 链表（无 vtable，指针链）
    printf("\n[Phase 5] Building Node linked list...\n");
    g_list_head = nullptr;
    for (int i = 0; i < N_NODE; i++)
    {
        Node *n = new Node();
        n->value = i;
        n->next = g_list_head;
        g_list_head = n;
    }
    // 统计链表长度
    int list_len = 0;
    for (Node *cur = g_list_head; cur; cur = cur->next)
        list_len++;
    printf("  Done: linked list length = %d\n", list_len);

    printf("\nAllocation complete!\n");
    printf("  sizeof(Config)  = %zu\n", sizeof(Config));
    printf("  sizeof(Record)  = %zu\n", sizeof(Record));
    printf("  sizeof(Point3D) = %zu\n", sizeof(Point3D));
    printf("  sizeof(Node)    = %zu\n", sizeof(Node));

    printf("\n============================================================\n");
    printf(">>> READY FOR GCORE <<<\n");
    printf("gcore %d\n", getpid());
    printf("============================================================\n");

    printf("\nWaiting for coredump generation...\n");
    printf("Press Ctrl+C to exit after gcore is done.\n");

    while (1)
    {
        sleep(3600);
    }

    return 0;
}
