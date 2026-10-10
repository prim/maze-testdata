/**
 * C++ std::optional 残留指针测试
 *
 * 测试目标：std::optional<T*> 被 reset() 后，_M_engaged 变为 false，
 *   但 payload 字节仍保留旧指针。旧对象释放后内存被同样大小的 Other 复用，
 *   若遍历不看判别字段，会把 Other 误识别为 Payload。
 *
 *   - 2000 个 Holder，各含 std::optional<Payload*>
 *   - 1000 个保持 engaged：Payload 只经 optional 引用，应被识别
 *   - 1000 个 reset() 后 delete，随后分配 Other（只经 void* 持有，可能复用该内存）
 *
 * 期望：C++ Payload 约 1000 个（修复前为约 2000 个）。
 *
 * 编译命令：
 *   g++ -g -O0 -std=c++17 -o optional_stale_test optional_stale_test.cpp
 */

#include <cstdio>
#include <optional>
#include <unistd.h>
#include <vector>

struct Payload
{
    long a, b, c;
};

struct Other
{
    long q, w, e;
};

struct Holder
{
    std::optional<Payload *> p;
    long id;
};

std::vector<Holder *> g_holders;
std::vector<void *> g_others;

int main()
{
    printf("C++ Optional Stale Test - PID: %d\n", getpid());
    for (int i = 0; i < 2000; i++)
    {
        Holder *h = new Holder();
        h->id = i;
        h->p = new Payload{i, i, i};
        if (i % 2)
        {
            Payload *x = *h->p;
            h->p.reset(); // _M_engaged=false，payload 字节仍是 x
            delete x;
            g_others.push_back(new Other{-i, -i, -i}); // 通常复用 x 的内存
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
