/**
 * C++ STL 容器类型识别测试
 *
 * 测试目的：
 *   验证 Maze 能正确展开 STL 容器（vector, deque, unordered_map, list），
 *   将容器内部分配的内存归属到拥有容器的 C++ 对象。
 *
 * 内存布局：
 *   - 5000 个 Widget 实例，每个含 vector<int*>(10个元素) + string
 *   - 2000 个 Session 实例，每个含 unordered_map<int,string>(20个kv)
 *   - 1000 个 TaskQueue 实例，每个含 deque<int*>(15个) + list<int*>(10个)
 *
 * 编译命令：
 *   g++ -g -O0 -std=c++11 -o containers_test containers_test.cpp
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
#include <deque>
#include <list>
#include <unordered_map>
#include <string>

class Widget
{
public:
    int id;
    std::vector<int *> items;
    std::string name;
    virtual ~Widget()
    {
        for (auto p : items)
            delete p;
    }
};

class Session
{
public:
    int session_id;
    std::unordered_map<int, std::string> data;
    virtual ~Session() {}
};

class TaskQueue
{
public:
    std::deque<int *> pending;
    std::list<int *> completed;
    virtual ~TaskQueue()
    {
        for (auto p : pending)
            delete p;
        for (auto p : completed)
            delete p;
    }
};

// 保存指针防止被优化掉
std::vector<Widget *> g_widgets;
std::vector<Session *> g_sessions;
std::vector<TaskQueue *> g_queues;

int main()
{
    printf("============================================================\n");
    printf("C++ Containers Test - PID: %d\n", getpid());
    printf("============================================================\n");

    const int N_WIDGET = 5000;
    const int N_SESSION = 2000;
    const int N_QUEUE = 1000;

    printf("\nAllocating objects...\n");
    printf("  - %d Widget instances (vector<int*> + string)\n", N_WIDGET);
    printf("  - %d Session instances (unordered_map<int,string>)\n", N_SESSION);
    printf("  - %d TaskQueue instances (deque<int*> + list<int*>)\n", N_QUEUE);

    g_widgets.reserve(N_WIDGET);
    g_sessions.reserve(N_SESSION);
    g_queues.reserve(N_QUEUE);

    // Phase 1: Widget — vector<int*> + string
    printf("\n[Phase 1] Allocating Widget instances...\n");
    for (int i = 0; i < N_WIDGET; i++)
    {
        Widget *w = new Widget();
        w->id = i;
        // 每个 vector 放 10 个 heap int
        for (int j = 0; j < 10; j++)
        {
            int *p = new int(i * 100 + j);
            w->items.push_back(p);
        }
        // 长 string 触发堆分配 (SSO 阈值通常 15-22 bytes)
        char buf[64];
        snprintf(buf, sizeof(buf), "widget_%05d_name_padding_xxxxx", i);
        w->name = buf;
        g_widgets.push_back(w);

        if ((i + 1) % 1000 == 0)
            printf("  Progress: %d/%d\n", i + 1, N_WIDGET);
    }
    printf("  Done: %zu Widgets\n", g_widgets.size());

    // Phase 2: Session — unordered_map<int, string>
    printf("\n[Phase 2] Allocating Session instances...\n");
    for (int i = 0; i < N_SESSION; i++)
    {
        Session *s = new Session();
        s->session_id = i;
        for (int j = 0; j < 20; j++)
        {
            char val[64];
            snprintf(val, sizeof(val), "session_%d_value_%d_padding_xx", i, j);
            s->data[j] = val;
        }
        g_sessions.push_back(s);

        if ((i + 1) % 500 == 0)
            printf("  Progress: %d/%d\n", i + 1, N_SESSION);
    }
    printf("  Done: %zu Sessions\n", g_sessions.size());

    // Phase 3: TaskQueue — deque<int*> + list<int*>
    printf("\n[Phase 3] Allocating TaskQueue instances...\n");
    for (int i = 0; i < N_QUEUE; i++)
    {
        TaskQueue *q = new TaskQueue();
        for (int j = 0; j < 15; j++)
            q->pending.push_back(new int(i * 1000 + j));
        for (int j = 0; j < 10; j++)
            q->completed.push_back(new int(i * 1000 + 100 + j));
        g_queues.push_back(q);

        if ((i + 1) % 200 == 0)
            printf("  Progress: %d/%d\n", i + 1, N_QUEUE);
    }
    printf("  Done: %zu TaskQueues\n", g_queues.size());

    printf("\nAllocation complete!\n");
    printf("  sizeof(Widget)    = %zu\n", sizeof(Widget));
    printf("  sizeof(Session)   = %zu\n", sizeof(Session));
    printf("  sizeof(TaskQueue) = %zu\n", sizeof(TaskQueue));

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
