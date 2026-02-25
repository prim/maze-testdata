/**
 * C++ 多重继承 / 虚继承 vtable 测试
 *
 * 测试目标：验证 Maze 对多重继承对象的类型识别
 *   多重继承对象有多个 vtable（offset 0 主 vtable + 次级 vtable）
 *   cpp package 只检测 offset 0 的 vtable，次级 vtable 可能被忽略
 *
 * 编译命令：
 *   g++ -g -O0 -std=c++11 -o multi_inherit_test multi_inherit_test.cpp
 */

#include <cstdio>
#include <cstdlib>
#include <unistd.h>
#include <vector>

class Renderable
{
public:
    int render_id;
    double opacity;
    virtual void render() {}
    virtual ~Renderable() {}
};

class Collidable
{
public:
    int collider_id;
    double radius;
    virtual void checkCollision() {}
    virtual ~Collidable() {}
};

class Serializable
{
public:
    int serial_id;
    char format[16];
    virtual void serialize() {}
    virtual ~Serializable() {}
};

// 双重继承
class GameObject : public Renderable, public Collidable
{
public:
    int game_id;
    double x, y, z;
    virtual ~GameObject() {}
};

// 三重继承
class NetworkEntity : public Renderable, public Collidable, public Serializable
{
public:
    int net_id;
    int sync_tick;
    virtual ~NetworkEntity() {}
};

// 单继承对照组
class SimpleNPC : public Renderable
{
public:
    int npc_id;
    double speed;
    virtual ~SimpleNPC() {}
};

// 全局容器
std::vector<GameObject *> g_gameobjects;
std::vector<NetworkEntity *> g_netentities;
std::vector<SimpleNPC *> g_npcs;

int main()
{
    printf("============================================\n");
    printf("C++ Multi-Inherit Test - PID: %d\n", getpid());
    printf("============================================\n");

    printf("\nsizeof(Renderable)    = %zu\n", sizeof(Renderable));
    printf("sizeof(Collidable)    = %zu\n", sizeof(Collidable));
    printf("sizeof(Serializable)  = %zu\n", sizeof(Serializable));
    printf("sizeof(GameObject)    = %zu\n", sizeof(GameObject));
    printf("sizeof(NetworkEntity) = %zu\n", sizeof(NetworkEntity));
    printf("sizeof(SimpleNPC)     = %zu\n", sizeof(SimpleNPC));

    const int N_GAMEOBJ = 4000;
    const int N_NETENT  = 3000;
    const int N_NPC     = 5000;

    // Phase 1: GameObject (双重继承)
    printf("\n[Phase 1] Creating %d GameObject (dual inherit)...\n", N_GAMEOBJ);
    g_gameobjects.reserve(N_GAMEOBJ);
    for (int i = 0; i < N_GAMEOBJ; i++)
    {
        GameObject *obj = new GameObject();
        obj->render_id = i;
        obj->opacity = 1.0;
        obj->collider_id = i;
        obj->radius = 5.0 + i * 0.1;
        obj->game_id = i;
        obj->x = i * 1.0;
        obj->y = i * 2.0;
        obj->z = i * 3.0;
        g_gameobjects.push_back(obj);
    }
    printf("  Done: %zu GameObject\n", g_gameobjects.size());

    // Phase 2: NetworkEntity (三重继承)
    printf("\n[Phase 2] Creating %d NetworkEntity (triple inherit)...\n", N_NETENT);
    g_netentities.reserve(N_NETENT);
    for (int i = 0; i < N_NETENT; i++)
    {
        NetworkEntity *ent = new NetworkEntity();
        ent->render_id = i;
        ent->opacity = 0.8;
        ent->collider_id = i;
        ent->radius = 3.0;
        ent->serial_id = i;
        snprintf(ent->format, sizeof(ent->format), "json");
        ent->net_id = i;
        ent->sync_tick = 100 + i;
        g_netentities.push_back(ent);
    }
    printf("  Done: %zu NetworkEntity\n", g_netentities.size());

    // Phase 3: SimpleNPC (单继承对照组)
    printf("\n[Phase 3] Creating %d SimpleNPC (single inherit)...\n", N_NPC);
    g_npcs.reserve(N_NPC);
    for (int i = 0; i < N_NPC; i++)
    {
        SimpleNPC *npc = new SimpleNPC();
        npc->render_id = i;
        npc->opacity = 1.0;
        npc->npc_id = i;
        npc->speed = 10.0 + i * 0.01;
        g_npcs.push_back(npc);
    }
    printf("  Done: %zu SimpleNPC\n", g_npcs.size());

    printf("\n============================================\n");
    printf(">>> READY FOR GCORE <<<\n");
    printf("gcore %d\n", getpid());
    printf("============================================\n");

    while (1) { sleep(3600); }
    return 0;
}