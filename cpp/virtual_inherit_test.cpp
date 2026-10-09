/**
 * C++ 虚继承 vtable address point 测试
 *
 * 测试目标：带虚基类的类，Itanium ABI 主 vtable 前有 vbase offset 槽，
 *   对象 vptr = _ZTV + 24（或更多），而不是常规的 _ZTV + 16。
 *   验证 Maze 能用真实 address point 识别这些堆对象。
 *   对象只通过 void* 持有，排除“全局类型化指针遍历”这条识别路径，
 *   结果完全依赖 vtable 识别。std::ostringstream 覆盖 libstdc++ 中
 *   basic_ios 虚继承的常见场景。
 *   VBase::payload 指向的 Payload 无 vtable，只能经虚基类字段遍历定型：
 *   虚基类偏移在运行时由 vtable 的 vbase offset 槽决定，不是常量字段。
 *
 * 编译命令（默认 PIE，RTTI 槽在加载时重定位）：
 *   g++ -g -O0 -std=c++11 -o virtual_inherit_test virtual_inherit_test.cpp
 */

#include <cstdio>
#include <cstdlib>
#include <sstream>
#include <unistd.h>
#include <vector>

// 无 vtable 的负载对象，只被虚基类字段引用
struct Payload
{
    long payload_id;
    long payload_value;
    double payload_weight;
    long payload_extra;
};

class VBase
{
public:
    long base_id;
    Payload *payload;
    virtual ~VBase() {}
};

static Payload *new_payload(int i)
{
    Payload *payload = new Payload();
    payload->payload_id = i;
    payload->payload_value = i * 11;
    payload->payload_weight = i * 0.25;
    payload->payload_extra = -i;
    return payload;
}

// 单虚基类：vtable 前有 1 个 vbase offset
class VSingle : public virtual VBase
{
public:
    long single_value;
    double single_weight;
    virtual void tick() {}
    virtual ~VSingle() {}
};

// 菱形继承：Left/Right 均虚继承 VBase
class VLeft : public virtual VBase
{
public:
    long left_value;
    virtual void left() {}
    virtual ~VLeft() {}
};

class VRight : public virtual VBase
{
public:
    long right_value;
    virtual void right() {}
    virtual ~VRight() {}
};

class VDiamond : public VLeft, public VRight
{
public:
    long diamond_value;
    char tag[24];
    virtual ~VDiamond() {}
};

// 普通基类 + 虚基类混合
class Plain
{
public:
    long plain_value;
    virtual ~Plain() {}
};

class VMixed : public Plain, public virtual VBase
{
public:
    long mixed_value;
    virtual ~VMixed() {}
};

// 对照组：无虚基类，vptr = _ZTV + 16
class Control
{
public:
    long control_value;
    virtual ~Control() {}
};

// 只用 void* 持有，类型信息只能来自对象首字 vptr
std::vector<void *> g_singles;
std::vector<void *> g_diamonds;
std::vector<void *> g_mixed;
std::vector<void *> g_controls;
std::vector<void *> g_streams;

int main()
{
    printf("============================================\n");
    printf("C++ Virtual-Inherit Test - PID: %d\n", getpid());
    printf("============================================\n");

    printf("sizeof(VSingle)  = %zu\n", sizeof(VSingle));
    printf("sizeof(VDiamond) = %zu\n", sizeof(VDiamond));
    printf("sizeof(VMixed)   = %zu\n", sizeof(VMixed));
    printf("sizeof(Control)  = %zu\n", sizeof(Control));

    const int N_SINGLE = 3000;
    const int N_DIAMOND = 2000;
    const int N_MIXED = 2500;
    const int N_CONTROL = 4000;
    const int N_STREAM = 1500;

    for (int i = 0; i < N_SINGLE; i++)
    {
        VSingle *obj = new VSingle();
        obj->base_id = i;
        obj->payload = new_payload(i);
        obj->single_value = i * 2;
        obj->single_weight = i * 0.5;
        g_singles.push_back(obj);
    }
    for (int i = 0; i < N_DIAMOND; i++)
    {
        VDiamond *obj = new VDiamond();
        obj->base_id = i;
        obj->payload = new_payload(i);
        obj->left_value = i;
        obj->right_value = -i;
        obj->diamond_value = i * 3;
        snprintf(obj->tag, sizeof(obj->tag), "diamond-%d", i);
        g_diamonds.push_back(obj);
    }
    for (int i = 0; i < N_MIXED; i++)
    {
        VMixed *obj = new VMixed();
        obj->base_id = i;
        obj->payload = new_payload(i);
        obj->plain_value = i;
        obj->mixed_value = i * 7;
        g_mixed.push_back(obj);
    }
    for (int i = 0; i < N_CONTROL; i++)
    {
        Control *obj = new Control();
        obj->control_value = i;
        g_controls.push_back(obj);
    }
    for (int i = 0; i < N_STREAM; i++)
    {
        std::ostringstream *stream = new std::ostringstream();
        *stream << "stream-" << i;
        g_streams.push_back(stream);
    }
    printf("Created VSingle=%zu VDiamond=%zu VMixed=%zu Control=%zu ostringstream=%zu\n",
           g_singles.size(), g_diamonds.size(), g_mixed.size(), g_controls.size(), g_streams.size());

    printf("\n============================================\n");
    printf(">>> READY FOR GCORE <<<\n");
    printf("gcore %d\n", getpid());
    printf("============================================\n");

    while (1)
    {
        sleep(3600);
    }
    return 0;
}
