/**
 * mimalloc 多线程内存分配测试
 *
 * 测试目的：
 *   验证 Maze 能正确识别多线程环境下使用 mimalloc 分配器的内存块
 *
 * 线程设计：
 *   - 1 个主线程 + 7 个子线程，共 8 个线程
 *   - 内存分配任务随机分配给各线程
 *   - 每个线程执行大量随机 malloc/free 操作（操作数 >= 10倍分配块数）
 *   - 最终保持的内存块数量与原设计一致
 *
 * 内存布局（最终状态）：
 *   - 20000 个 16 bytes malloc 块
 *   - 20000 个 32 bytes malloc 块
 *   - 20000 个 64 bytes malloc 块
 *   - 10000 个 128 bytes malloc 块
 *   - 10000 个 256 bytes malloc 块
 *   - 10000 个 512 bytes malloc 块
 *   - 10000 个 1024 bytes malloc 块
 *   - 100 个 1MB malloc 块
 *   - 100 个 2MB malloc 块
 *   - 100 个 3MB malloc 块
 *
 * 编译命令：
 *   g++ -g -O0 -pthread -ldl -o mi_alloc_multithread_test mi_alloc_multithread_test.cpp
 *
 * 运行方式 (通过 LD_PRELOAD 加载 mimalloc)：
 *   LD_PRELOAD=/path/to/libmimalloc.so ./mi_alloc_multithread_test
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
#include <thread>
#include <mutex>
#include <random>
#include <algorithm>
#include <atomic>
#include <dlfcn.h>
#include <stdint.h>

// mimalloc API 函数指针类型
// mimalloc 1.0.0 使用的 API
typedef void (*mi_stats_print_t)(void *out);
typedef void (*mi_stats_reset_t)(void);
typedef size_t (*mi_good_size_t)(size_t size);
typedef void *(*mi_malloc_t)(size_t size);
typedef void (*mi_free_t)(void *p);

mi_stats_print_t g_mi_stats_print = nullptr;
mi_stats_reset_t g_mi_stats_reset = nullptr;
mi_good_size_t g_mi_good_size = nullptr;
mi_malloc_t g_mi_malloc = nullptr;
mi_free_t g_mi_free = nullptr;

void init_mimalloc_api()
{
	g_mi_stats_print = (mi_stats_print_t)dlsym(RTLD_DEFAULT, "mi_stats_print");
	g_mi_stats_reset = (mi_stats_reset_t)dlsym(RTLD_DEFAULT, "mi_stats_reset");
	g_mi_good_size = (mi_good_size_t)dlsym(RTLD_DEFAULT, "mi_good_size");
	g_mi_malloc = (mi_malloc_t)dlsym(RTLD_DEFAULT, "mi_malloc");
	g_mi_free = (mi_free_t)dlsym(RTLD_DEFAULT, "mi_free");

	if (g_mi_stats_print)
		printf("[mimalloc] mi_stats_print API found\n");
	else
		printf("[mimalloc] mi_stats_print API not found (not using mimalloc?)\n");

	if (g_mi_malloc)
		printf("[mimalloc] mi_malloc API found\n");

	if (g_mi_good_size)
	{
		printf("[mimalloc] mi_good_size API found\n");
		printf("[mimalloc] Size class examples:\n");
		size_t test_sizes[] = {16, 32, 64, 128, 256, 512, 1024, 2048, 4096};
		for (size_t s : test_sizes)
			printf("  mi_good_size(%zu) = %zu\n", s, g_mi_good_size(s));
	}
}

void print_mimalloc_stats()
{
	if (!g_mi_stats_print)
	{
		printf("\n[mimalloc stats] Not available (mi_stats_print not found)\n");
		return;
	}

	printf("\n============================================================\n");
	printf("mimalloc Statistics:\n");
	printf("============================================================\n");

	// mi_stats_print(NULL) 输出到 stderr
	// g_mi_stats_print(nullptr);

	size_t expected_allocated =
		20000 * 16 +
		20000 * 32 +
		20000 * 64 +
		10000 * 128 +
		10000 * 256 +
		10000 * 512 +
		10000 * 1024 +
		100 * 1024 * 1024 +
		100 * 2 * 1024 * 1024 +
		100 * 3 * 1024 * 1024;

	printf("\n  Expected user allocation: %zu bytes (%.2f MB)\n",
		   expected_allocated, expected_allocated / (1024.0 * 1024.0));

	printf("\n  Expected counts:\n");
	printf("    malloc(16):               20000\n");
	printf("    malloc(32):               20000\n");
	printf("    malloc(64):               20000\n");
	printf("    malloc(128):              10000\n");
	printf("    malloc(256):              10000\n");
	printf("    malloc(512):              10000\n");
	printf("    malloc(1024):             10000\n");
	printf("    malloc(1MB):              100\n");
	printf("    malloc(2MB):              100\n");
	printf("    malloc(3MB):              100\n");
}

const int NUM_THREADS = 8;

std::mutex g_mutex;
std::vector<void *> g_malloc_16;
std::vector<void *> g_malloc_32;
std::vector<void *> g_malloc_64;
std::vector<void *> g_malloc_128;
std::vector<void *> g_malloc_256;
std::vector<void *> g_malloc_512;
std::vector<void *> g_malloc_1024;
std::vector<void *> g_malloc_1m;
std::vector<void *> g_malloc_2m;
std::vector<void *> g_malloc_3m;

std::atomic<int> g_threads_done(0);
std::atomic<bool> g_keep_running(true);

struct AllocTask
{
	size_t size;
	int target_count;
};

void fill_memory(void *ptr, size_t size, unsigned char pattern)
{
	if (size <= 1024)
		memset(ptr, pattern, size);
	else
	{
		((char *)ptr)[0] = pattern;
		((char *)ptr)[size - 1] = pattern;
	}
}

struct SizeState
{
	size_t size;
	int target_count;
	int current_count;
	unsigned char fill_pattern;
	std::vector<void *> ptrs;
};

unsigned char get_fill_pattern(size_t size)
{
	switch (size)
	{
	case 16:
		return 0x11;
	case 32:
		return 0x22;
	case 64:
		return 0x33;
	case 128:
		return 0x44;
	case 256:
		return 0x55;
	case 512:
		return 0x66;
	case 1024:
		return 0x77;
	case 1 * 1024 * 1024:
		return 0xAA;
	case 2 * 1024 * 1024:
		return 0xBB;
	case 3 * 1024 * 1024:
		return 0xCC;
	default:
		return 0xFF;
	}
}

void thread_worker(int thread_id, std::vector<AllocTask> tasks)
{
	printf("  Thread %d: starting with %zu task types\n", thread_id, tasks.size());

	if (tasks.empty())
	{
		printf("  Thread %d: completed (no tasks)\n", thread_id);
		g_threads_done++;
		return;
	}

	std::mt19937 rng(thread_id * 12345 + 67890);

	std::vector<SizeState> states;
	int total_target = 0;
	for (const auto &task : tasks)
	{
		if (task.target_count > 0)
		{
			SizeState s;
			s.size = task.size;
			s.target_count = task.target_count;
			s.current_count = 0;
			s.fill_pattern = get_fill_pattern(task.size);
			states.push_back(s);
			total_target += task.target_count;
		}
	}

	if (states.empty())
	{
		printf("  Thread %d: completed (no valid tasks)\n", thread_id);
		g_threads_done++;
		return;
	}

	int min_operations = total_target * 10;
	std::uniform_int_distribution<int> extra_ops_dist(0, total_target * 2);
	int total_operations = min_operations + extra_ops_dist(rng);

	std::uniform_int_distribution<size_t> size_picker(0, states.size() - 1);

	for (int op = 0; op < total_operations; op++)
	{
		size_t idx = size_picker(rng);
		SizeState &st = states[idx];

		bool do_malloc = false;
		int remaining_ops = total_operations - op;
		int diff = st.target_count - st.current_count;

		if (st.current_count == 0)
		{
			do_malloc = true;
		}
		else if (remaining_ops <= (int)states.size() * (std::abs(diff) + 10))
		{
			do_malloc = (diff > 0);
		}
		else
		{
			double malloc_prob = 0.5;
			if (diff > 0)
				malloc_prob = 0.5 + 0.3 * ((double)diff / st.target_count);
			else if (diff < 0)
				malloc_prob = 0.5 - 0.3 * ((double)(-diff) / st.target_count);

			malloc_prob = std::max(0.2, std::min(0.8, malloc_prob));

			std::uniform_real_distribution<double> prob_dist(0.0, 1.0);
			do_malloc = (prob_dist(rng) < malloc_prob);
		}

		if (do_malloc)
		{
			void *ptr = malloc(st.size);
			if (ptr)
			{
				fill_memory(ptr, st.size, st.fill_pattern);
				st.ptrs.push_back(ptr);
				st.current_count++;
			}
		}
		else
		{
			if (!st.ptrs.empty())
			{
				std::uniform_int_distribution<int> idx_dist(0, (int)st.ptrs.size() - 1);
				int pidx = idx_dist(rng);
				free(st.ptrs[pidx]);
				st.ptrs[pidx] = st.ptrs.back();
				st.ptrs.pop_back();
				st.current_count--;
			}
		}
	}

	for (auto &st : states)
	{
		while (st.current_count < st.target_count)
		{
			void *ptr = malloc(st.size);
			if (ptr)
			{
				fill_memory(ptr, st.size, st.fill_pattern);
				st.ptrs.push_back(ptr);
				st.current_count++;
			}
		}
		while (st.current_count > st.target_count)
		{
			if (!st.ptrs.empty())
			{
				free(st.ptrs.back());
				st.ptrs.pop_back();
				st.current_count--;
			}
		}
	}

	{
		std::lock_guard<std::mutex> lock(g_mutex);

		for (auto &st : states)
		{
			if (st.size == 16)
				g_malloc_16.insert(g_malloc_16.end(), st.ptrs.begin(), st.ptrs.end());
			else if (st.size == 32)
				g_malloc_32.insert(g_malloc_32.end(), st.ptrs.begin(), st.ptrs.end());
			else if (st.size == 64)
				g_malloc_64.insert(g_malloc_64.end(), st.ptrs.begin(), st.ptrs.end());
			else if (st.size == 128)
				g_malloc_128.insert(g_malloc_128.end(), st.ptrs.begin(), st.ptrs.end());
			else if (st.size == 256)
				g_malloc_256.insert(g_malloc_256.end(), st.ptrs.begin(), st.ptrs.end());
			else if (st.size == 512)
				g_malloc_512.insert(g_malloc_512.end(), st.ptrs.begin(), st.ptrs.end());
			else if (st.size == 1024)
				g_malloc_1024.insert(g_malloc_1024.end(), st.ptrs.begin(), st.ptrs.end());
			else if (st.size == 1 * 1024 * 1024)
				g_malloc_1m.insert(g_malloc_1m.end(), st.ptrs.begin(), st.ptrs.end());
			else if (st.size == 2 * 1024 * 1024)
				g_malloc_2m.insert(g_malloc_2m.end(), st.ptrs.begin(), st.ptrs.end());
			else if (st.size == 3 * 1024 * 1024)
				g_malloc_3m.insert(g_malloc_3m.end(), st.ptrs.begin(), st.ptrs.end());
		}

	}

	printf("  Thread %d: completed\n", thread_id);
	g_threads_done++;

	// 工作线程等待，不退出，避免触发 mimalloc abandon 机制
	// 线程退出会导致 mimalloc 将其 segment 标记为 abandoned，
	// 其他线程 reclaim 后可能清零 page metadata (xblock_size 等)
	if (thread_id != 0)
	{
		while (g_keep_running.load())
			sleep(1);
	}
}

std::vector<int> distribute_randomly(int total, int num_parts, std::mt19937 &rng)
{
	std::vector<int> result(num_parts, 0);

	if (total <= 0 || num_parts <= 0)
		return result;

	std::vector<int> cuts;
	cuts.push_back(0);
	cuts.push_back(total);

	std::uniform_int_distribution<int> dist(0, total);
	for (int i = 0; i < num_parts - 1; i++)
		cuts.push_back(dist(rng));

	std::sort(cuts.begin(), cuts.end());

	for (int i = 0; i < num_parts; i++)
		result[i] = cuts[i + 1] - cuts[i];

	std::shuffle(result.begin(), result.end(), rng);

	return result;
}

int main()
{
	setbuf(stdout, NULL);

	printf("============================================================\n");
	printf("mimalloc Multithread Malloc Test - PID: %d\n", getpid());
	printf("============================================================\n");

	init_mimalloc_api();

	const int N = 20000;
	const int M = 10000;
	const int L = 100;

	printf("\nTarget allocations:\n");
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

	printf("\nThreads: %d (1 main + %d workers)\n", NUM_THREADS, NUM_THREADS - 1);

	std::random_device rd;
	std::mt19937 rng(rd());

	printf("\nDistributing tasks to threads...\n");

	std::vector<std::vector<AllocTask>> thread_tasks(NUM_THREADS);

	auto dist_16 = distribute_randomly(N, NUM_THREADS, rng);
	for (int t = 0; t < NUM_THREADS; t++)
		if (dist_16[t] > 0)
			thread_tasks[t].push_back({16, dist_16[t]});

	auto dist_32 = distribute_randomly(N, NUM_THREADS, rng);
	for (int t = 0; t < NUM_THREADS; t++)
		if (dist_32[t] > 0)
			thread_tasks[t].push_back({32, dist_32[t]});

	auto dist_64 = distribute_randomly(N, NUM_THREADS, rng);
	for (int t = 0; t < NUM_THREADS; t++)
		if (dist_64[t] > 0)
			thread_tasks[t].push_back({64, dist_64[t]});

	auto dist_128 = distribute_randomly(M, NUM_THREADS, rng);
	for (int t = 0; t < NUM_THREADS; t++)
		if (dist_128[t] > 0)
			thread_tasks[t].push_back({128, dist_128[t]});

	auto dist_256 = distribute_randomly(M, NUM_THREADS, rng);
	for (int t = 0; t < NUM_THREADS; t++)
		if (dist_256[t] > 0)
			thread_tasks[t].push_back({256, dist_256[t]});

	auto dist_512 = distribute_randomly(M, NUM_THREADS, rng);
	for (int t = 0; t < NUM_THREADS; t++)
		if (dist_512[t] > 0)
			thread_tasks[t].push_back({512, dist_512[t]});

	auto dist_1024 = distribute_randomly(M, NUM_THREADS, rng);
	for (int t = 0; t < NUM_THREADS; t++)
		if (dist_1024[t] > 0)
			thread_tasks[t].push_back({1024, dist_1024[t]});

	auto dist_1m = distribute_randomly(L, NUM_THREADS, rng);
	for (int t = 0; t < NUM_THREADS; t++)
		if (dist_1m[t] > 0)
			thread_tasks[t].push_back({1 * 1024 * 1024, dist_1m[t]});

	auto dist_2m = distribute_randomly(L, NUM_THREADS, rng);
	for (int t = 0; t < NUM_THREADS; t++)
		if (dist_2m[t] > 0)
			thread_tasks[t].push_back({2 * 1024 * 1024, dist_2m[t]});

	auto dist_3m = distribute_randomly(L, NUM_THREADS, rng);
	for (int t = 0; t < NUM_THREADS; t++)
		if (dist_3m[t] > 0)
			thread_tasks[t].push_back({3 * 1024 * 1024, dist_3m[t]});

	printf("\nTask distribution:\n");
	for (int t = 0; t < NUM_THREADS; t++)
	{
		int total_blocks = 0;
		for (const auto &task : thread_tasks[t])
			total_blocks += task.target_count;
		printf("  Thread %d: %zu task types, %d total blocks\n", t, thread_tasks[t].size(), total_blocks);
	}

	g_malloc_16.reserve(N);
	g_malloc_32.reserve(N);
	g_malloc_64.reserve(N);
	g_malloc_128.reserve(M);
	g_malloc_256.reserve(M);
	g_malloc_512.reserve(M);
	g_malloc_1024.reserve(M);
	g_malloc_1m.reserve(L);
	g_malloc_2m.reserve(L);
	g_malloc_3m.reserve(L);

	printf("\nStarting threads...\n");
	std::vector<std::thread> threads;

	for (int t = 1; t < NUM_THREADS; t++)
	{
		threads.emplace_back(thread_worker, t, thread_tasks[t]);
		threads.back().detach();
	}

	thread_worker(0, thread_tasks[0]);

	// 等待所有线程完成分配（线程不会退出，避免 mimalloc abandon）
	while (g_threads_done.load() < NUM_THREADS)
		usleep(100000);

	printf("\nAll threads completed allocations!\n");

	printf("\nFinal allocation counts:\n");
	printf("  malloc(16) blocks: %zu (expected: %d)\n", g_malloc_16.size(), N);
	printf("  malloc(32) blocks: %zu (expected: %d)\n", g_malloc_32.size(), N);
	printf("  malloc(64) blocks: %zu (expected: %d)\n", g_malloc_64.size(), N);
	printf("  malloc(128) blocks: %zu (expected: %d)\n", g_malloc_128.size(), M);
	printf("  malloc(256) blocks: %zu (expected: %d)\n", g_malloc_256.size(), M);
	printf("  malloc(512) blocks: %zu (expected: %d)\n", g_malloc_512.size(), M);
	printf("  malloc(1024) blocks: %zu (expected: %d)\n", g_malloc_1024.size(), M);
	printf("  malloc(1MB) blocks: %zu (expected: %d)\n", g_malloc_1m.size(), L);
	printf("  malloc(2MB) blocks: %zu (expected: %d)\n", g_malloc_2m.size(), L);
	printf("  malloc(3MB) blocks: %zu (expected: %d)\n", g_malloc_3m.size(), L);

	bool valid = true;
	if (g_malloc_16.size() != (size_t)N)
		valid = false;
	if (g_malloc_32.size() != (size_t)N)
		valid = false;
	if (g_malloc_64.size() != (size_t)N)
		valid = false;
	if (g_malloc_128.size() != (size_t)M)
		valid = false;
	if (g_malloc_256.size() != (size_t)M)
		valid = false;
	if (g_malloc_512.size() != (size_t)M)
		valid = false;
	if (g_malloc_1024.size() != (size_t)M)
		valid = false;
	if (g_malloc_1m.size() != (size_t)L)
		valid = false;
	if (g_malloc_2m.size() != (size_t)L)
		valid = false;
	if (g_malloc_3m.size() != (size_t)L)
		valid = false;

	if (valid)
		printf("\n[OK] All counts match expected values!\n");
	else
		printf("\n[ERROR] Count mismatch detected!\n");

	print_mimalloc_stats();

	// 输出所有大块内存的地址，用于调试验证
	printf("\nLarge block addresses:\n");
	printf("  malloc(1MB) addresses (%zu blocks):\n", g_malloc_1m.size());
	for (size_t i = 0; i < g_malloc_1m.size(); i++)
		printf("    [%zu] %p\n", i, g_malloc_1m[i]);
	printf("  malloc(2MB) addresses (%zu blocks):\n", g_malloc_2m.size());
	for (size_t i = 0; i < g_malloc_2m.size(); i++)
		printf("    [%zu] %p\n", i, g_malloc_2m[i]);
	printf("  malloc(3MB) addresses (%zu blocks):\n", g_malloc_3m.size());
	for (size_t i = 0; i < g_malloc_3m.size(); i++)
		printf("    [%zu] %p\n", i, g_malloc_3m[i]);

	printf("\n============================================================\n");
	printf(">>> READY FOR GCORE <<<\n");
	printf("gcore %d\n", getpid());
	printf("============================================================\n");

	printf("\nWaiting for coredump generation...\n");
	printf("Press Ctrl+C to exit after gcore is done.\n");

	while (1)
		sleep(3600);

	return 0;
}
