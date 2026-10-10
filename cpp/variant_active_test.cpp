/**
 * C++ std::variant 活跃成员测试
 *
 * 测试目标：只跟 _M_index 指向的活跃成员。
 *   - std::variant<Payload*, long>：一半存 Payload*；另一半存 long，
 *     其数值是只经 void* 持有的 Other 的地址。若跟进非活跃的 Payload* 成员，
 *     Other 会被误识别为 Payload。
 *   - std::variant<Payload2*, Other2*>：两个成员都是指针且目标大小相同，
 *     若两者都跟进，归属只能按类型名决定，Payload2 会被误识别为 Other2。
 *
 * 期望：Payload ~1000、Payload2 ~1000、Other2 ~1000
 *       （修复前：Payload ~2000、Payload2 0、Other2 ~2000）。
 *
 * 编译命令：
 *   g++ -g -O0 -std=c++17 -o variant_active_test variant_active_test.cpp
 */

#include <cstdio>
#include <unistd.h>
#include <variant>
#include <vector>

struct Payload
{
    long a, b, c;
};

struct Other
{
    long q, w, e;
};

struct Payload2
{
    long a, b, c, d;
};

struct Other2
{
    long q, w, e, r;
};

struct Holder
{
    std::variant<Payload *, long> v;
    std::variant<Payload2 *, Other2 *> w;
    long id;
};

std::vector<Holder *> g_holders;
std::vector<void *> g_others;

int main()
{
    printf("C++ Variant Active Test - PID: %d\n", getpid());
    for (int i = 0; i < 2000; i++)
    {
        Holder *h = new Holder();
        h->id = i;
        if (i % 2)
        {
            Other *o = new Other{-i, -i, -i};
            g_others.push_back(o);
            h->v = (long)o; // 活跃成员是整数，数值看起来像指针
            h->w = new Other2{i, i, i, i};
        }
        else
        {
            h->v = new Payload{i, i, i};
            h->w = new Payload2{i, i, i, i};
        }
        g_holders.push_back(h);
    }
    printf("holders=%zu others=%zu\n", g_holders.size(), g_others.size());

    printf(">>> READY FOR GCORE <<<\n");
    printf("gcore %d\n", getpid());
    fflush(stdout);
    while (1)
    {
        sleep(3600);
    }
    return 0;
}
