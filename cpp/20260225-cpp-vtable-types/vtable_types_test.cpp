/**
 * C++ vtable 类型识别测试
 *
 * 测试目的：
 *   验证 Maze 能正确识别多种 C++ 类的 vtable，区分不同类型，
 *   并检测同类对象数组（连续 vtable 扫描）。
 *
 * 内存布局：
 *   - 10000 个 Dog 实例
 *   - 5000 个 Cat 实例
 *   - 3000 个 GoldFish 实例
 *   - 1 个 Dog[200] 连续数组（测试同类对象数组检测）
 *
 * 编译命令：
 *   g++ -g -O0 -std=c++11 -o vtable_types_test vtable_types_test.cpp
 *
 * 使用方法：
 *   1. 编译并运行
 *   2. 看到 ">>> READY FOR GCORE <<<" 后执行 gcore
 *   3. 使用 maze-tar-coredump.py 打包
 */

#include <cstdio>
#include <cstdlib>
#include <unistd.h>
#include <vector>

class Animal
{
public:
    int id;
    virtual ~Animal() {}
    virtual const char *speak() { return "..."; }
};

class Dog : public Animal
{
public:
    int breed;
    virtual const char *speak() override { return "woof"; }
};

class Cat : public Animal
{
public:
    int color;
    virtual const char *speak() override { return "meow"; }
};

class GoldFish : public Animal
{
public:
    int tank_id;
    float weight;
    virtual const char *speak() override { return "blub"; }
};

// 保存指针防止被优化掉
std::vector<Animal *> g_dogs;
std::vector<Animal *> g_cats;
std::vector<Animal *> g_fish;
Dog *g_dog_array = nullptr;

int main()
{
    printf("============================================================\n");
    printf("C++ Vtable Types Test - PID: %d\n", getpid());
    printf("============================================================\n");

    const int N_DOG = 10000;
    const int N_CAT = 5000;
    const int N_FISH = 3000;
    const int N_ARRAY = 200;

    printf("\nAllocating objects...\n");
    printf("  - %d Dog instances\n", N_DOG);
    printf("  - %d Cat instances\n", N_CAT);
    printf("  - %d GoldFish instances\n", N_FISH);
    printf("  - 1 Dog[%d] array\n", N_ARRAY);

    g_dogs.reserve(N_DOG);
    g_cats.reserve(N_CAT);
    g_fish.reserve(N_FISH);

    printf("\n[Phase 1] Allocating Dog instances...\n");
    for (int i = 0; i < N_DOG; i++)
    {
        Dog *d = new Dog();
        d->id = i;
        d->breed = i % 50;
        g_dogs.push_back(d);
    }
    printf("  Done: %zu Dogs\n", g_dogs.size());

    printf("\n[Phase 2] Allocating Cat instances...\n");
    for (int i = 0; i < N_CAT; i++)
    {
        Cat *c = new Cat();
        c->id = N_DOG + i;
        c->color = i % 10;
        g_cats.push_back(c);
    }
    printf("  Done: %zu Cats\n", g_cats.size());

    printf("\n[Phase 3] Allocating GoldFish instances...\n");
    for (int i = 0; i < N_FISH; i++)
    {
        GoldFish *f = new GoldFish();
        f->id = N_DOG + N_CAT + i;
        f->tank_id = i % 100;
        f->weight = 0.5f + (i % 20) * 0.1f;
        g_fish.push_back(f);
    }
    printf("  Done: %zu GoldFish\n", g_fish.size());

    printf("\n[Phase 4] Allocating Dog[%d] array...\n", N_ARRAY);
    g_dog_array = new Dog[N_ARRAY];
    for (int i = 0; i < N_ARRAY; i++)
    {
        g_dog_array[i].id = 100000 + i;
        g_dog_array[i].breed = i % 10;
    }
    printf("  Done: Dog array at %p\n", (void *)g_dog_array);

    printf("\nAllocation complete!\n");
    printf("  sizeof(Animal)   = %zu\n", sizeof(Animal));
    printf("  sizeof(Dog)      = %zu\n", sizeof(Dog));
    printf("  sizeof(Cat)      = %zu\n", sizeof(Cat));
    printf("  sizeof(GoldFish) = %zu\n", sizeof(GoldFish));

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
