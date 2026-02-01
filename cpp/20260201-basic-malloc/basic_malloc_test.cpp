/**
 * C++ 基础内存分配测试
 *
 * 测试目的：
 *   验证 Maze 能正确识别 C++ 类实例和 malloc 分配的内存块
 *
 * 内存布局：
 *   - 80000 个 class A 实例 (每个 8 bytes，含虚函数表指针)
 *   - 80000 个 16 bytes malloc 块
 *   - 80000 个 32 bytes malloc 块
 *   - 80000 个 64 bytes malloc 块
 *
 * 编译命令：
 *   g++ -g -o basic_malloc_test basic_malloc_test.cpp
 *
 * 使用方法：
 *   1. 编译并运行: ./basic_malloc_test
 *   2. 看到 ">>> READY FOR GCORE <<<" 后执行 gcore
 *   3. 使用 maze-tar-coredump.py 打包
 */

#include <cstdio>
#include <cstdlib>
#include <unistd.h>
#include <vector>

class A
{
public:
	virtual void func() {}
};

// 保存指针防止被优化掉
std::vector<A *> class_instances;
std::vector<void *> malloc_16;
std::vector<void *> malloc_32;
std::vector<void *> malloc_64;

int main()
{
	const int N = 80000;

	printf("============================================================\n");
	printf("C++ Basic Malloc Test - PID: %d\n", getpid());
	printf("============================================================\n");

	printf("\nAllocating memory...\n");
	printf("  - %d class A instances (8 bytes each, with vtable)\n", N);
	printf("  - %d malloc(16) blocks\n", N);
	printf("  - %d malloc(32) blocks\n", N);
	printf("  - %d malloc(64) blocks\n", N);

	// 预分配 vector 容量
	class_instances.reserve(N);
	malloc_16.reserve(N);
	malloc_32.reserve(N);
	malloc_64.reserve(N);

	for (int i = 0; i < N; i++)
	{
		A *a = new A();
		void *p0 = malloc(16);
		void *p1 = malloc(32);
		void *p2 = malloc(64);

		// 保存指针
		class_instances.push_back(a);
		malloc_16.push_back(p0);
		malloc_32.push_back(p1);
		malloc_64.push_back(p2);

		// 进度显示
		if ((i + 1) % 20000 == 0)
		{
			printf("  Progress: %d/%d\n", i + 1, N);
		}
	}

	printf("\nAllocation complete!\n");
	printf("  class A instances: %zu\n", class_instances.size());
	printf("  malloc(16) blocks: %zu\n", malloc_16.size());
	printf("  malloc(32) blocks: %zu\n", malloc_32.size());
	printf("  malloc(64) blocks: %zu\n", malloc_64.size());

	// 输出标志性结束符号
	printf("\n============================================================\n");
	printf(">>> READY FOR GCORE <<<\n");
	printf("gcore %d\n", getpid());
	printf("============================================================\n");

	printf("\nWaiting for coredump generation...\n");
	printf("Press Ctrl+C to exit after gcore is done.\n");

	// 保持进程运行
	while (1)
	{
		sleep(3600);
	}

	return 0;
}
