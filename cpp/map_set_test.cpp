/**
 * C++ std::map / std::set 红黑树测试
 *
 * 测试目标：验证 Maze 对红黑树容器中元素的识别能力
 *
 * 已知状态：cpp package 没有注册 std::map/set 的 TYPE_CODE，
 *   map/set 会走通用的 StructClassifyInfo 路径。
 *   红黑树节点通过指针链连接，Maze 需要通过 PtrClassifyInfo 追踪。
 *
 * 编译命令：
 *   g++ -g -O0 -std=c++11 -o map_set_test map_set_test.cpp
 */

#include <cstdio>
#include <cstdlib>
#include <unistd.h>
#include <map>
#include <set>
#include <vector>
#include <string>

class Monster
{
public:
    int id;
    double hp;
    double attack;
    void *ai_state;
    virtual ~Monster() {}
};

class Weapon
{
public:
    int weapon_id;
    int damage;
    char name[32];
    virtual ~Weapon() {}
};

// 全局容器
std::map<int, Monster *> *g_monster_map;
std::set<Weapon *> *g_weapon_set;
std::map<std::string, int> *g_config_map;
std::vector<Monster *> g_all_monsters;
std::vector<Weapon *> g_all_weapons;

int main()
{
    printf("============================================\n");
    printf("C++ Map/Set Test - PID: %d\n", getpid());
    printf("============================================\n");

    printf("\nsizeof(Monster) = %zu\n", sizeof(Monster));
    printf("sizeof(Weapon) = %zu\n", sizeof(Weapon));

    const int N_MONSTER = 5000;
    const int N_WEAPON = 3000;
    const int N_CONFIG = 2000;

    // Phase 1: map<int, Monster*>
    printf("\n[Phase 1] Creating map with %d monsters...\n", N_MONSTER);
    g_monster_map = new std::map<int, Monster *>();
    g_all_monsters.reserve(N_MONSTER);
    for (int i = 0; i < N_MONSTER; i++)
    {
        Monster *m = new Monster();
        m->id = i;
        m->hp = 100.0 + i;
        m->attack = 10.0 + i * 0.5;
        m->ai_state = nullptr;
        (*g_monster_map)[i] = m;
        g_all_monsters.push_back(m);
    }
    printf("  map size: %zu\n", g_monster_map->size());

    // Phase 2: set<Weapon*>
    printf("\n[Phase 2] Creating set with %d weapons...\n", N_WEAPON);
    g_weapon_set = new std::set<Weapon *>();
    g_all_weapons.reserve(N_WEAPON);
    for (int i = 0; i < N_WEAPON; i++)
    {
        Weapon *w = new Weapon();
        w->weapon_id = i;
        w->damage = 50 + i;
        snprintf(w->name, sizeof(w->name), "wpn_%04d", i);
        g_weapon_set->insert(w);
        g_all_weapons.push_back(w);
    }
    printf("  set size: %zu\n", g_weapon_set->size());

    // Phase 3: map<string, int>
    printf("\n[Phase 3] Creating config map with %d entries...\n", N_CONFIG);
    g_config_map = new std::map<std::string, int>();
    for (int i = 0; i < N_CONFIG; i++)
    {
        char key[64];
        snprintf(key, sizeof(key), "config_key_%06d", i);
        (*g_config_map)[std::string(key)] = i * 10;
    }
    printf("  config map size: %zu\n", g_config_map->size());

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
