/**
 * jemalloc 内存分配测试
 *
 * 测试目的：
 *   验证 Maze 能正确识别使用 jemalloc 分配器的内存块
 *
 * 内存布局：
 *   - 80000 个 class A 实例 (每个 8 bytes，含虚函数表指针)
 *   - 80000 个 16 bytes malloc 块
 *   - 80000 个 32 bytes malloc 块
 *   - 80000 个 64 bytes malloc 块
 *   - 10000 个 128 bytes malloc 块
 *   - 10000 个 256 bytes malloc 块
 *   - 10000 个 512 bytes malloc 块
 *   - 10000 个 1024 bytes malloc 块
 *   - 1000 个 1MB malloc 块
 *   - 1000 个 2MB malloc 块
 *   - 1000 个 3MB malloc 块
 *
 * 编译命令：
 *   g++ -g -O0 -o jemalloc_malloc_test jemalloc_malloc_test.cpp
 *
 * 运行方式 (通过 LD_PRELOAD 加载 jemalloc)：
 *   LD_PRELOAD=/path/to/libjemalloc.so.2 ./jemalloc_malloc_test
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
std::vector<void *> malloc_128;
std::vector<void *> malloc_256;
std::vector<void *> malloc_512;
std::vector<void *> malloc_1024;
std::vector<void *> malloc_1m;
std::vector<void *> malloc_2m;
std::vector<void *> malloc_3m;

int main()
{
	const int N = 80000;
	const int M = 10000;
	const int L = 1000;

	printf("============================================================\n");
	printf("jemalloc Malloc Test - PID: %d\n", getpid());
	printf("============================================================\n");

	printf("\nAllocating memory...\n");
	printf("  - %d class A instances (8 bytes each, with vtable)\n", N);
	printf("  - %d malloc(16) blocks\n", N);
	printf("  - %d malloc(32) blocks\n", N);
	printf("  - %d malloc(64) blocks\n", N);
	printf("  - %d malloc(128) blocks\n", M);
	printf("  - %d malloc(256) blocks\n", M);
	printf("  - %d malloc(512) blocks\n", M);
	printf("  - %d malloc(1024) blocks\n", M);
	printf("  - %d malloc(1MB) blocks\n", L);
	printf("  - %d malloc(2MB) blocks\n", L);
	printf("  - %d malloc(3MB) blocks\n", L);

	// 预分配 vector 容量
	class_instances.reserve(N);
	malloc_16.reserve(N);
	malloc_32.reserve(N);
	malloc_64.reserve(N);
	malloc_128.reserve(M);
	malloc_256.reserve(M);
	malloc_512.reserve(M);
	malloc_1024.reserve(M);
	malloc_1m.reserve(L);
	malloc_2m.reserve(L);
	malloc_3m.reserve(L);

	// 分配 80000 个基础块
	printf("\n[Phase 1] Allocating %d small blocks...\n", N);
	for (int i = 0; i < N; i++)
	{
		A *a = new A();
		void *p0 = malloc(16);
		void *p1 = malloc(32);
		void *p2 = malloc(64);

		// 写入数据防止优化
		memset(p0, 0x11, 16);
		memset(p1, 0x22, 32);
		memset(p2, 0x33, 64);

		class_instances.push_back(a);
		malloc_16.push_back(p0);
		malloc_32.push_back(p1);
		malloc_64.push_back(p2);

		if ((i + 1) % 20000 == 0)
		{
			printf("  Progress: %d/%d\n", i + 1, N);
		}
	}

	// 分配 10000 个中等块
	printf("\n[Phase 2] Allocating %d medium blocks...\n", M);
	for (int i = 0; i < M; i++)
	{
		void *p128 = malloc(128);
		void *p256 = malloc(256);
		void *p512 = malloc(512);
		void *p1024 = malloc(1024);

		memset(p128, 0x44, 128);
		memset(p256, 0x55, 256);
		memset(p512, 0x66, 512);
		memset(p1024, 0x77, 1024);

		malloc_128.push_back(p128);
		malloc_256.push_back(p256);
		malloc_512.push_back(p512);
		malloc_1024.push_back(p1024);

		if ((i + 1) % 5000 == 0)
		{
			printf("  Progress: %d/%d\n", i + 1, M);
		}
	}

	// 分配 1000 个大块
	printf("\n[Phase 3] Allocating %d large blocks...\n", L);
	for (int i = 0; i < L; i++)
	{
		void *p1m = malloc(1 * 1024 * 1024);
		void *p2m = malloc(2 * 1024 * 1024);
		void *p3m = malloc(3 * 1024 * 1024);

		// 只写入首尾各一个字节，避免过度写入
		if (p1m) { ((char *)p1m)[0] = 0xAA; ((char *)p1m)[1048575] = 0xAA; }
		if (p2m) { ((char *)p2m)[0] = 0xBB; ((char *)p2m)[2097151] = 0xBB; }
		if (p3m) { ((char *)p3m)[0] = 0xCC; ((char *)p3m)[3145727] = 0xCC; }

		malloc_1m.push_back(p1m);
		malloc_2m.push_back(p2m);
		malloc_3m.push_back(p3m);

		if ((i + 1) % 200 == 0)
		{
			printf("  Progress: %d/%d\n", i + 1, L);
		}
	}

	printf("\nAllocation complete!\n");
	printf("  class A instances: %zu\n", class_instances.size());
	printf("  malloc(16) blocks: %zu\n", malloc_16.size());
	printf("  malloc(32) blocks: %zu\n", malloc_32.size());
	printf("  malloc(64) blocks: %zu\n", malloc_64.size());
	printf("  malloc(128) blocks: %zu\n", malloc_128.size());
	printf("  malloc(256) blocks: %zu\n", malloc_256.size());
	printf("  malloc(512) blocks: %zu\n", malloc_512.size());
	printf("  malloc(1024) blocks: %zu\n", malloc_1024.size());
	printf("  malloc(1MB) blocks: %zu\n", malloc_1m.size());
	printf("  malloc(2MB) blocks: %zu\n", malloc_2m.size());
	printf("  malloc(3MB) blocks: %zu\n", malloc_3m.size());

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
