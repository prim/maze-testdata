/**
 * C++ std::unordered_set 测试
 *
 * 测试目标：验证 Maze 对 unordered_set 中元素的识别能力
 *   unordered_map 已有 TYPE_CODE_CUSTOM_UNORDERED_MAP (1002)
 *   但 unordered_set 没有专门的 TYPE_CODE
 *
 * 编译命令：
 *   g++ -g -O0 -std=c++11 -o unordered_set_test unordered_set_test.cpp
 */

#include <cstdio>
#include <cstdlib>
#include <unistd.h>
#include <unordered_set>
#include <unordered_map>
#include <vector>

class Enemy
{
public:
    int enemy_id;
    double hp;
    double attack;
    virtual ~Enemy() {}
};

struct EnemyHash {
    size_t operator()(const Enemy *e) const {
        return std::hash<int>()(e->enemy_id);
    }
};

struct EnemyEqual {
    bool operator()(const Enemy *a, const Enemy *b) const {
        return a->enemy_id == b->enemy_id;
    }
};

class Item
{
public:
    int item_id;
    double weight;
    char name[32];
    virtual ~Item() {}
};

struct ItemHash {
    size_t operator()(const Item *i) const {
        return std::hash<int>()(i->item_id);
    }
};

struct ItemEqual {
    bool operator()(const Item *a, const Item *b) const {
        return a->item_id == b->item_id;
    }
};

// 全局容器
std::unordered_set<Enemy *, EnemyHash, EnemyEqual> g_enemy_set;
std::unordered_map<int, Item *> g_item_map;
std::vector<Enemy *> g_enemy_vec;
std::vector<Item *> g_item_vec;

int main()
{
    printf("============================================\n");
    printf("C++ Unordered Set Test - PID: %d\n", getpid());
    printf("============================================\n");

    printf("\nsizeof(Enemy) = %zu\n", sizeof(Enemy));
    printf("sizeof(Item)  = %zu\n", sizeof(Item));

    const int N_ENEMY = 4000;
    const int N_ITEM  = 3000;

    // Phase 1: Enemy in unordered_set + vector
    printf("\n[Phase 1] Creating %d Enemy (unordered_set)...\n", N_ENEMY);
    g_enemy_vec.reserve(N_ENEMY);
    for (int i = 0; i < N_ENEMY; i++)
    {
        Enemy *e = new Enemy();
        e->enemy_id = i;
        e->hp = 100.0 + i;
        e->attack = 10.0 + i * 0.5;
        g_enemy_set.insert(e);
        g_enemy_vec.push_back(e);
    }
    printf("  Done: set=%zu, vec=%zu\n",
           g_enemy_set.size(), g_enemy_vec.size());

    // Phase 2: Item in unordered_map + vector
    printf("\n[Phase 2] Creating %d Item (unordered_map)...\n", N_ITEM);
    g_item_vec.reserve(N_ITEM);
    for (int i = 0; i < N_ITEM; i++)
    {
        Item *it = new Item();
        it->item_id = i;
        it->weight = 1.0 + i * 0.1;
        snprintf(it->name, sizeof(it->name), "item_%04d", i);
        g_item_map[i] = it;
        g_item_vec.push_back(it);
    }
    printf("  Done: map=%zu, vec=%zu\n",
           g_item_map.size(), g_item_vec.size());

    printf("\n============================================\n");
    printf(">>> READY FOR GCORE <<<\n");
    printf("gcore %d\n", getpid());
    printf("============================================\n");

    while (1) { sleep(3600); }
    return 0;
}
