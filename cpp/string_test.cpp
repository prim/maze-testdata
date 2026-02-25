/**
 * C++ std::string 内存归类测试
 *
 * 测试目标：验证 Maze 对 std::string 的内存归类能力
 *   - SSO (Small String Optimization): 短字符串存在对象内部，不分配堆内存
 *   - 长字符串: 堆上分配 char[] 缓冲区
 *   - 包含 string 成员的结构体
 *
 * 编译命令：
 *   g++ -g -O0 -std=c++11 -o string_test string_test.cpp
 */

#include <cstdio>
#include <cstdlib>
#include <unistd.h>
#include <string>
#include <vector>

class UserProfile
{
public:
    int uid;
    std::string username;     // 短字符串 (SSO)
    std::string bio;          // 长字符串 (堆分配)
    double score;
    virtual ~UserProfile() {}
};

class LogEntry
{
public:
    int log_id;
    std::string message;      // 长字符串
    std::string source;       // 短字符串
    int level;
    virtual ~LogEntry() {}
};

// 全局容器
std::vector<UserProfile *> g_profiles;
std::vector<LogEntry *> g_logs;
std::vector<std::string *> g_raw_strings;

int main()
{
    printf("============================================\n");
    printf("C++ String Test - PID: %d\n", getpid());
    printf("============================================\n");

    printf("\nsizeof(std::string)  = %zu\n", sizeof(std::string));
    printf("sizeof(UserProfile)  = %zu\n", sizeof(UserProfile));
    printf("sizeof(LogEntry)     = %zu\n", sizeof(LogEntry));

    const int N_PROFILE = 3000;
    const int N_LOG     = 4000;
    const int N_RAW_STR = 5000;

    // Phase 1: UserProfile (短username + 长bio)
    printf("\n[Phase 1] Creating %d UserProfile...\n", N_PROFILE);
    g_profiles.reserve(N_PROFILE);
    for (int i = 0; i < N_PROFILE; i++)
    {
        UserProfile *p = new UserProfile();
        p->uid = i;
        char buf[16];
        snprintf(buf, sizeof(buf), "user%04d", i);
        p->username = buf;  // SSO: ~8 chars
        p->bio = std::string(200, 'A' + (i % 26));  // 长字符串: 200 chars
        p->score = 100.0 + i;
        g_profiles.push_back(p);
    }
    printf("  Done: %zu UserProfile\n", g_profiles.size());

    // Phase 2: LogEntry (长message + 短source)
    printf("\n[Phase 2] Creating %d LogEntry...\n", N_LOG);
    g_logs.reserve(N_LOG);
    for (int i = 0; i < N_LOG; i++)
    {
        LogEntry *e = new LogEntry();
        e->log_id = i;
        e->message = std::string(300, 'X' + (i % 3));  // 长字符串: 300 chars
        char src[16];
        snprintf(src, sizeof(src), "srv%02d", i % 10);
        e->source = src;  // SSO: ~5 chars
        e->level = i % 5;
        g_logs.push_back(e);
    }
    printf("  Done: %zu LogEntry\n", g_logs.size());

    // Phase 3: 裸 std::string* (长字符串，无 vtable)
    printf("\n[Phase 3] Creating %d raw std::string*...\n", N_RAW_STR);
    g_raw_strings.reserve(N_RAW_STR);
    for (int i = 0; i < N_RAW_STR; i++)
    {
        std::string *s = new std::string(150, 'a' + (i % 26));
        g_raw_strings.push_back(s);
    }
    printf("  Done: %zu raw strings\n", g_raw_strings.size());

    printf("\n============================================\n");
    printf(">>> READY FOR GCORE <<<\n");
    printf("gcore %d\n", getpid());
    printf("============================================\n");

    while (1) { sleep(3600); }
    return 0;
}
