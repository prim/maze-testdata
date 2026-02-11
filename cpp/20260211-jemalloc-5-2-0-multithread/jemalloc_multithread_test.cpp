/**
 * jemalloc 多线程内存分配测试
 *
 * 测试目的：
 *   验证 Maze 能正确识别多线程环境下使用 jemalloc 分配器的内存块
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
 *   g++ -g -O0 -pthread -ldl -o jemalloc_multithread_test jemalloc_multithread_test.cpp
 *
 * 运行方式 (通过 LD_PRELOAD 加载 jemalloc)：
 *   LD_PRELOAD=/path/to/libjemalloc.so.2 ./jemalloc_multithread_test
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

typedef int (*mallctl_t)(const char *name, void *oldp, size_t *oldlenp, void *newp, size_t newlen);
typedef int (*mallctlnametomib_t)(const char *name, size_t *mibp, size_t *miblenp);
typedef int (*mallctlbymib_t)(const size_t *mib, size_t miblen, void *oldp, size_t *oldlenp, void *newp, size_t newlen);

mallctl_t g_mallctl = nullptr;
mallctlnametomib_t g_mallctlnametomib = nullptr;
mallctlbymib_t g_mallctlbymib = nullptr;

void init_jemalloc_api()
{
	g_mallctl = (mallctl_t)dlsym(RTLD_DEFAULT, "mallctl");
	g_mallctlnametomib = (mallctlnametomib_t)dlsym(RTLD_DEFAULT, "mallctlnametomib");
	g_mallctlbymib = (mallctlbymib_t)dlsym(RTLD_DEFAULT, "mallctlbymib");

	if (g_mallctl)
		printf("[jemalloc] mallctl API found\n");
	else
		printf("[jemalloc] mallctl API not found (not using jemalloc?)\n");
}

void print_jemalloc_stats()
{
	if (!g_mallctl)
	{
		printf("\n[jemalloc stats] Not available (mallctl not found)\n");
		return;
	}

	uint64_t epoch = 1;
	size_t sz = sizeof(epoch);
	if (g_mallctl("epoch", &epoch, &sz, &epoch, sz) != 0)
	{
		printf("\n[jemalloc stats] Failed to update epoch\n");
		return;
	}

	size_t allocated = 0, active = 0, metadata = 0, resident = 0, mapped = 0;
	sz = sizeof(size_t);

	bool stats_available = true;
	if (g_mallctl("stats.allocated", &allocated, &sz, nullptr, 0) != 0) stats_available = false;
	if (g_mallctl("stats.active", &active, &sz, nullptr, 0) != 0) stats_available = false;
	if (g_mallctl("stats.metadata", &metadata, &sz, nullptr, 0) != 0) stats_available = false;
	if (g_mallctl("stats.resident", &resident, &sz, nullptr, 0) != 0) stats_available = false;
	if (g_mallctl("stats.mapped", &mapped, &sz, nullptr, 0) != 0) stats_available = false;

	if (!stats_available)
	{
		printf("\n[jemalloc stats] Stats not available (jemalloc may not be compiled with --enable-stats)\n");
		return;
	}

	printf("\n============================================================\n");
	printf("jemalloc Statistics:\n");
	printf("============================================================\n");
	printf("  allocated: %zu bytes (%.2f MB)\n", allocated, allocated / (1024.0 * 1024.0));
	printf("  active:    %zu bytes (%.2f MB)\n", active, active / (1024.0 * 1024.0));
	printf("  metadata:  %zu bytes (%.2f MB)\n", metadata, metadata / (1024.0 * 1024.0));
	printf("  resident:  %zu bytes (%.2f MB)\n", resident, resident / (1024.0 * 1024.0));
	printf("  mapped:    %zu bytes (%.2f MB)\n", mapped, mapped / (1024.0 * 1024.0));

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

	if (!g_mallctlnametomib || !g_mallctlbymib)
	{
		printf("  (mallctlbymib not available, skipping per-bin stats)\n");
		return;
	}

	unsigned nbins = 0;
	sz = sizeof(nbins);
	if (g_mallctl("arenas.nbins", &nbins, &sz, nullptr, 0) != 0)
	{
		printf("  (Failed to get arenas.nbins)\n");
		return;
	}

	size_t bin_size_mib[4];
	size_t bin_size_miblen = 4;
	if (g_mallctlnametomib("arenas.bin.0.size", bin_size_mib, &bin_size_miblen) != 0)
	{
		printf("  (Failed to get bin size MIB)\n");
		return;
	}

	size_t bin_curregs_mib[6];
	size_t bin_curregs_miblen = 6;
	if (g_mallctlnametomib("stats.arenas.0.bins.0.curregs", bin_curregs_mib, &bin_curregs_miblen) != 0)
	{
		printf("  (Failed to get bin curregs MIB, stats may not be available)\n");
		return;
	}

	printf("\n  Per-bin statistics (small allocations):\n");
	printf("  %10s  %12s  %15s\n", "bin_size", "count", "total_bytes");
	printf("  %10s  %12s  %15s\n", "--------", "-----", "-----------");

	const unsigned MALLCTL_ARENAS_ALL = 4096;
	bin_curregs_mib[2] = MALLCTL_ARENAS_ALL;

	for (unsigned i = 0; i < nbins; i++)
	{
		bin_size_mib[2] = i;
		size_t bin_size = 0;
		sz = sizeof(bin_size);
		if (g_mallctlbymib(bin_size_mib, bin_size_miblen, &bin_size, &sz, nullptr, 0) != 0)
			continue;

		bin_curregs_mib[4] = i;
		size_t curregs = 0;
		sz = sizeof(curregs);
		if (g_mallctlbymib(bin_curregs_mib, bin_curregs_miblen, &curregs, &sz, nullptr, 0) != 0)
			continue;

		if (curregs > 0)
		{
			size_t total = bin_size * curregs;
			printf("  %10zu  %12zu  %15zu\n", bin_size, curregs, total);
		}
	}

	unsigned nlextents = 0;
	sz = sizeof(nlextents);
	if (g_mallctl("arenas.nlextents", &nlextents, &sz, nullptr, 0) == 0 && nlextents > 0)
	{
		size_t lextent_size_mib[4];
		size_t lextent_size_miblen = 4;
		size_t lextent_curlextents_mib[6];
		size_t lextent_curlextents_miblen = 6;

		if (g_mallctlnametomib("arenas.lextent.0.size", lextent_size_mib, &lextent_size_miblen) == 0 &&
			g_mallctlnametomib("stats.arenas.0.lextents.0.curlextents", lextent_curlextents_mib, &lextent_curlextents_miblen) == 0)
		{
			printf("\n  Per-lextent statistics (large allocations):\n");
			printf("  %10s  %12s  %15s\n", "size", "count", "total_bytes");
			printf("  %10s  %12s  %15s\n", "----", "-----", "-----------");

			lextent_curlextents_mib[2] = MALLCTL_ARENAS_ALL;

			for (unsigned i = 0; i < nlextents; i++)
			{
				lextent_size_mib[2] = i;
				size_t lextent_size = 0;
				sz = sizeof(lextent_size);
				if (g_mallctlbymib(lextent_size_mib, lextent_size_miblen, &lextent_size, &sz, nullptr, 0) != 0)
					continue;

				lextent_curlextents_mib[4] = i;
				size_t curlextents = 0;
				sz = sizeof(curlextents);
				if (g_mallctlbymib(lextent_curlextents_mib, lextent_curlextents_miblen, &curlextents, &sz, nullptr, 0) != 0)
					continue;

				if (curlextents > 0)
				{
					size_t total = lextent_size * curlextents;
					if (total >= 1024 * 1024)
						printf("  %7zuMB  %12zu  %12zuMB\n", lextent_size / (1024 * 1024), curlextents, total / (1024 * 1024));
					else if (total >= 1024)
						printf("  %7zuKB  %12zu  %12zuKB\n", lextent_size / 1024, curlextents, total / 1024);
					else
						printf("  %10zu  %12zu  %15zu\n", lextent_size, curlextents, total);
				}
			}
		}
	}

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
	case 16: return 0x11;
	case 32: return 0x22;
	case 64: return 0x33;
	case 128: return 0x44;
	case 256: return 0x55;
	case 512: return 0x66;
	case 1024: return 0x77;
	case 1 * 1024 * 1024: return 0xAA;
	case 2 * 1024 * 1024: return 0xBB;
	case 3 * 1024 * 1024: return 0xCC;
	default: return 0xFF;
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
}

std::vector<int> distribute_randomly(int total, int num_parts, std::mt19937 &rng)
{
	std::vector<int> result(num_parts, 0);

	if (total <= 0 || num_parts <= 0) return result;

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
	printf("============================================================\n");
	printf("jemalloc Multithread Malloc Test - PID: %d\n", getpid());
	printf("============================================================\n");

	init_jemalloc_api();

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
		threads.emplace_back(thread_worker, t, thread_tasks[t]);

	thread_worker(0, thread_tasks[0]);

	for (auto &t : threads)
		t.join();

	printf("\nAll threads completed!\n");

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
	if (g_malloc_16.size() != (size_t)N) valid = false;
	if (g_malloc_32.size() != (size_t)N) valid = false;
	if (g_malloc_64.size() != (size_t)N) valid = false;
	if (g_malloc_128.size() != (size_t)M) valid = false;
	if (g_malloc_256.size() != (size_t)M) valid = false;
	if (g_malloc_512.size() != (size_t)M) valid = false;
	if (g_malloc_1024.size() != (size_t)M) valid = false;
	if (g_malloc_1m.size() != (size_t)L) valid = false;
	if (g_malloc_2m.size() != (size_t)L) valid = false;
	if (g_malloc_3m.size() != (size_t)L) valid = false;

	if (valid)
		printf("\n[OK] All counts match expected values!\n");
	else
		printf("\n[ERROR] Count mismatch detected!\n");

	print_jemalloc_stats();

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
