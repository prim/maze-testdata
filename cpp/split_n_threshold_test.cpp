/**
 * C++ 1拆N 阈值测试
 *
 * Bug: ResultClassify 1拆N 阈值 n>5 (cpp.go:970)
 *   malloc 块中包含 2-5 个相同结构体时不会被拆分
 *   导致只计为 1 个对象，漏算 N-1 个
 *
 * 测试方法：
 *   用 malloc 分配 N*sizeof(Widget) 大小的块
 *   只在第一个位置 placement new（有 vtable）
 *   其余位置 memset(0)（无 vtable）
 *   CollectVtable 只识别第一个对象
 *   ResultClassify 发现 piecesize/sz1 = N
 *   当 n<=5 时不拆分 → 漏算
 *
 * 编译命令：
 *   g++ -g -O0 -std=c++11 -o split_n_threshold_test split_n_threshold_test.cpp
 */

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unistd.h>
#include <new>
#include <vector>

// 带虚函数的类型，确保有 vtable
class Widget
{
public:
    int id;
    double value;
    void *ref;  // 指针字段
    virtual ~Widget() {}
};

// 全局容器，防止被优化掉
// 只存第一个 Widget 的指针（即 malloc 块起始地址）
std::vector<Widget *> g_split2;  // n=2, 不满足 n>5
std::vector<Widget *> g_split3;  // n=3, 不满足 n>5
std::vector<Widget *> g_split5;  // n=5, 不满足 n>5
std::vector<Widget *> g_split8;  // n=8, 满足 n>5 (对照组)

int main()
{
    printf("============================================\n");
    printf("C++ 1-to-N Split Threshold Test - PID: %d\n", getpid());
    printf("============================================\n");

    printf("\nsizeof(Widget) = %zu\n", sizeof(Widget));

    const int N2 = 3000;
    const int N3 = 3000;
    const int N5 = 2000;
    const int N8 = 1000;

    // Phase 1: 每块 malloc(sizeof(Widget)*2), 只在首位 placement new
    printf("\n[Phase 1] Split-2: %d blocks...\n", N2);
    g_split2.reserve(N2);
    for (int i = 0; i < N2; i++)
    {
        size_t block_sz = sizeof(Widget) * 2;
        void *mem = malloc(block_sz);
        memset(mem, 0, block_sz);
        Widget *w = new (mem) Widget();
        w->id = i;
        w->value = i * 0.1;
        w->ref = nullptr;
        g_split2.push_back(w);
    }
    printf("  Done: %zu blocks of 2\n", g_split2.size());

    // Phase 2: 每块 malloc(sizeof(Widget)*3)
    printf("\n[Phase 2] Split-3: %d blocks...\n", N3);
    g_split3.reserve(N3);
    for (int i = 0; i < N3; i++)
    {
        size_t block_sz = sizeof(Widget) * 3;
        void *mem = malloc(block_sz);
        memset(mem, 0, block_sz);
        Widget *w = new (mem) Widget();
        w->id = 200000 + i;
        w->value = i * 0.3;
        w->ref = nullptr;
        g_split3.push_back(w);
    }
    printf("  Done: %zu blocks of 3\n", g_split3.size());

    // Phase 3: 每块 malloc(sizeof(Widget)*5)
    printf("\n[Phase 3] Split-5: %d blocks...\n", N5);
    g_split5.reserve(N5);
    for (int i = 0; i < N5; i++)
    {
        size_t block_sz = sizeof(Widget) * 5;
        void *mem = malloc(block_sz);
        memset(mem, 0, block_sz);
        Widget *w = new (mem) Widget();
        w->id = 500000 + i;
        w->value = i * 0.5;
        w->ref = nullptr;
        g_split5.push_back(w);
    }
    printf("  Done: %zu blocks of 5\n", g_split5.size());

    // Phase 4: 每块 malloc(sizeof(Widget)*8) — 对照组
    printf("\n[Phase 4] Split-8: %d blocks...\n", N8);
    g_split8.reserve(N8);
    for (int i = 0; i < N8; i++)
    {
        size_t block_sz = sizeof(Widget) * 8;
        void *mem = malloc(block_sz);
        memset(mem, 0, block_sz);
        Widget *w = new (mem) Widget();
        w->id = 800000 + i;
        w->value = i * 0.8;
        w->ref = nullptr;
        g_split8.push_back(w);
    }
    printf("  Done: %zu blocks of 8\n", g_split8.size());

    // 期望的内存统计：
    // 如果 1拆N 正确工作（无阈值限制）：
    //   split2: 3000 块 * sizeof(Widget)*2 = 3000 块
    //   split3: 3000 块 * sizeof(Widget)*3 = 3000 块
    //   split5: 2000 块 * sizeof(Widget)*5 = 2000 块
    //   split8: 1000 块 * sizeof(Widget)*8 = 1000 块
    // 每块只有 1 个 Widget 对象，但 malloc 块大小是 N 倍
    // 如果 n>5 阈值存在：
    //   split2/3/5 的块不会被拆分，整块算作 1 个 Widget 的大小
    //   split8 的块会被拆分
    printf("\nExpected memory per block:\n");
    printf("  split2: %zu bytes/block (Widget=%zu, ratio=2)\n",
           sizeof(Widget) * 2, sizeof(Widget));
    printf("  split3: %zu bytes/block (Widget=%zu, ratio=3)\n",
           sizeof(Widget) * 3, sizeof(Widget));
    printf("  split5: %zu bytes/block (Widget=%zu, ratio=5)\n",
           sizeof(Widget) * 5, sizeof(Widget));
    printf("  split8: %zu bytes/block (Widget=%zu, ratio=8)\n",
           sizeof(Widget) * 8, sizeof(Widget));

    printf("\n============================================\n");
    printf(">>> READY FOR GCORE <<<\n");
    printf("gcore %d\n", getpid());
    printf("============================================\n");

    printf("\nWaiting for coredump generation...\n");
    printf("Press Ctrl+C to exit after gcore is done.\n");

    while (1)
    {
        sleep(3600);
    }

    return 0;
}
