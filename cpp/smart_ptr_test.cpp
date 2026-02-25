/**
 * C++ shared_ptr / unique_ptr 智能指针测试
 *
 * 测试目标：验证 Maze 能否通过 StructClassifyInfo + PtrClassifyInfo
 *   正确追踪智能指针指向的对象。
 *
 * 编译命令：
 *   g++ -g -O0 -std=c++11 -o smart_ptr_test smart_ptr_test.cpp
 */

#include <cstdio>
#include <cstdlib>
#include <unistd.h>
#include <memory>
#include <vector>

class Player
{
public:
    int id;
    double hp;
    double mp;
    char name[32];
    virtual ~Player() {}
};

class Bullet
{
public:
    int bullet_id;
    double speed;
    double damage;
    virtual ~Bullet() {}
};

class Effect
{
public:
    int effect_id;
    int duration;
    double power;
    virtual ~Effect() {}
};

// 全局容器
std::vector<std::shared_ptr<Player>> g_shared_players;
std::vector<std::unique_ptr<Bullet>> g_unique_bullets;
std::vector<std::shared_ptr<Effect>> g_shared_effects;

int main()
{
    printf("============================================\n");
    printf("C++ Smart Pointer Test - PID: %d\n", getpid());
    printf("============================================\n");

    printf("\nsizeof(Player) = %zu\n", sizeof(Player));
    printf("sizeof(Bullet) = %zu\n", sizeof(Bullet));
    printf("sizeof(Effect) = %zu\n", sizeof(Effect));

    const int N_PLAYER = 3000;
    const int N_BULLET = 5000;
    const int N_EFFECT = 4000;

    // Phase 1: shared_ptr<Player>
    printf("\n[Phase 1] Creating %d shared_ptr<Player>...\n", N_PLAYER);
    g_shared_players.reserve(N_PLAYER);
    for (int i = 0; i < N_PLAYER; i++)
    {
        auto p = std::make_shared<Player>();
        p->id = i;
        p->hp = 100.0 + i;
        p->mp = 50.0 + i;
        snprintf(p->name, sizeof(p->name), "player_%04d", i);
        g_shared_players.push_back(p);
    }
    printf("  Done: %zu shared_ptr<Player>\n", g_shared_players.size());

    // Phase 2: unique_ptr<Bullet>
    printf("\n[Phase 2] Creating %d unique_ptr<Bullet>...\n", N_BULLET);
    g_unique_bullets.reserve(N_BULLET);
    for (int i = 0; i < N_BULLET; i++)
    {
        auto b = std::make_unique<Bullet>();
        b->bullet_id = i;
        b->speed = 10.0 + i * 0.1;
        b->damage = 5.0 + i * 0.5;
        g_unique_bullets.push_back(std::move(b));
    }
    printf("  Done: %zu unique_ptr<Bullet>\n", g_unique_bullets.size());

    // Phase 3: shared_ptr<Effect> (多引用)
    printf("\n[Phase 3] Creating %d shared_ptr<Effect>...\n", N_EFFECT);
    g_shared_effects.reserve(N_EFFECT);
    for (int i = 0; i < N_EFFECT; i++)
    {
        auto e = std::make_shared<Effect>();
        e->effect_id = i;
        e->duration = 10 + i % 100;
        e->power = 1.0 + i * 0.01;
        g_shared_effects.push_back(e);
    }
    printf("  Done: %zu shared_ptr<Effect>\n", g_shared_effects.size());

    printf("\n============================================\n");
    printf(">>> READY FOR GCORE <<<\n");
    printf("gcore %d\n", getpid());
    printf("============================================\n");

    while (1) { sleep(3600); }
    return 0;
}
