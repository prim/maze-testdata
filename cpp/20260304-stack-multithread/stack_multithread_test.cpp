/**
 * TC-B004: 多线程栈变量收集测试
 * 
 * 测试目的：验证栈变量收集功能能正确处理多线程场景
 * 
 * 测试场景：
 * - 创建 10+ 线程
 * - 每线程有独立的局部指针变量
 * 
 * 预期结果：
 * - 所有线程的栈变量被收集
 * - stack_locals 中包含各线程的变量，thread ID 正确
 * - 线程切换无异常
 */

#include <iostream>
#include <unistd.h>
#include <cstring>
#include <thread>
#include <vector>
#include <atomic>

// 非多态类
struct ThreadObject {
    int thread_id;
    int object_id;
    char data[32];
    ThreadObject(int tid, int oid) : thread_id(tid), object_id(oid) {
        memset(data, 'T', sizeof(data));
    }
};

// 原子计数器，用于同步
std::atomic<int> ready_count(0);
std::atomic<bool> all_ready(false);

// 线程函数
void threadFunction(int thread_id) {
    // 每个线程创建 3 个对象
    ThreadObject* obj1 = new ThreadObject(thread_id, 1);
    ThreadObject* obj2 = new ThreadObject(thread_id, 2);
    ThreadObject* obj3 = new ThreadObject(thread_id, 3);
    
    std::cout << "Thread " << thread_id << " created objects at " 
              << obj1 << ", " << obj2 << ", " << obj3 << std::endl;
    
    // 标记此线程已就绪
    ready_count++;
    
    // 等待所有线程就绪
    while (!all_ready) {
        usleep(10000);  // 10ms
    }
    
    // 保持运行，保持局部变量在栈上
    while (true) {
        sleep(3600);
    }
    
    // 防止编译器优化
    (void)obj1;
    (void)obj2;
    (void)obj3;
}

int main() {
    const int NUM_THREADS = 10;  // 10 个线程
    
    std::cout << "========================================" << std::endl;
    std::cout << "Multi-thread Stack Locals Test - PID: " << getpid() << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;
    std::cout << "Number of threads: " << NUM_THREADS << std::endl;
    std::cout << "Objects per thread: 3" << std::endl;
    std::cout << "Total expected objects: " << (NUM_THREADS * 3) << std::endl;
    std::cout << std::endl;
    
    // 创建线程
    std::vector<std::thread> threads;
    for (int i = 0; i < NUM_THREADS; i++) {
        threads.emplace_back(threadFunction, i);
    }
    
    // 等待所有线程就绪
    std::cout << "Waiting for all threads to be ready..." << std::endl;
    while (ready_count < NUM_THREADS) {
        usleep(10000);
    }
    
    std::cout << "All threads ready!" << std::endl;
    std::cout << ">>> READY FOR GCORE <<<" << std::endl;
    std::cout << "PID: " << getpid() << std::endl;
    
    // 通知所有线程继续
    all_ready = true;
    
    // 主线程等待
    for (auto& t : threads) {
        t.join();
    }
    
    return 0;
}
