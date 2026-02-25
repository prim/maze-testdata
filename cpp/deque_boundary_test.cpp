/**
 * C++ Deque 边界元素测试
 *
 * Bug: DequeClassifyInfo 边界检查失效 (custom.go:139/156)
 *   curNode 在 line 139 自增后，line 156 的边界比较永远为 false
 *   导致 deque 首尾 buffer 中无效元素被错误收集
 *
 * 测试方法：
 *   创建 deque，push 大量元素后 pop_front 一部分
 *   使 _M_start.cur 不在 buffer 起始位置
 *   如果 bug 存在：首 buffer 中已 pop 的元素也会被遍历
 *
 * 编译命令：
 *   g++ -g -O0 -std=c++11 -o deque_boundary_test deque_boundary_test.cpp
 */

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unistd.h>
#include <deque>
#include <vector>

class Task
{
public:
    int task_id;
    double priority;
    void *callback;
    virtual ~Task() {}
};

// 全局容器
std::vector<std::deque<Task *> *> g_deques;
std::vector<Task *> g_all_tasks;
int g_total_alive = 0;

int main()
{
    printf("============================================\n");
    printf("C++ Deque Boundary Test - PID: %d\n", getpid());
    printf("============================================\n");

    printf("\nsizeof(Task) = %zu\n", sizeof(Task));

    const int N_DEQUE = 200;
    const int PUSH_COUNT = 100;
    const int POP_COUNT = 30;

    // Phase 1: 创建 deque，push 元素后 pop_front 一部分
    // 这样 _M_start.cur 不在 buffer 起始位置
    printf("\n[Phase 1] Creating %d deques, push %d, pop_front %d each...\n",
           N_DEQUE, PUSH_COUNT, POP_COUNT);
    g_deques.reserve(N_DEQUE);
    for (int d = 0; d < N_DEQUE; d++)
    {
        std::deque<Task *> *dq = new std::deque<Task *>();
        for (int j = 0; j < PUSH_COUNT; j++)
        {
            Task *t = new Task();
            t->task_id = d * 1000 + j;
            t->priority = j * 0.1;
            t->callback = nullptr;
            dq->push_back(t);
            g_all_tasks.push_back(t);
        }
        // pop_front 使首 buffer 有空洞
        for (int j = 0; j < POP_COUNT; j++)
        {
            dq->pop_front();
        }
        g_deques.push_back(dq);
    }
    g_total_alive = N_DEQUE * (PUSH_COUNT - POP_COUNT);
    printf("  Done: %zu deques\n", g_deques.size());
    printf("  Total alive tasks in deques: %d\n", g_total_alive);
    printf("  Total Task objects allocated: %zu\n", g_all_tasks.size());

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
