/**
 * TC-B007: 大内存进程栈变量收集测试
 * 
 * 测试目的：验证栈变量收集功能在大内存进程下的性能和稳定性
 * 
 * 测试场景：
 * - 内存占用较大的进程（模拟大内存场景）
 * - 栈变量数量较多
 * 
 * 预期结果：
 * - 扫描时间合理
 * - 内存占用合理
 * - 无 OOM 或超时
 */

#include <iostream>
#include <unistd.h>
#include <cstring>
#include <vector>

// 非多态类
struct LargeMemNode {
    int id;
    char padding[56];  // 使对象大小为 64 字节
    LargeMemNode(int _id) : id(_id) {}
};

// 分配一些内存来模拟大内存进程
void allocateLargeMemory() {
    // 分配约 50MB 内存（模拟大内存场景）
    const int NUM_LARGE_BLOCKS = 50;
    std::vector<char*> large_blocks;
    
    for (int i = 0; i < NUM_LARGE_BLOCKS; i++) {
        char* block = new char[1024 * 1024];  // 1MB each
        memset(block, 'L', 1024 * 1024);
        large_blocks.push_back(block);
    }
    
    std::cout << "Allocated " << NUM_LARGE_BLOCKS << " MB of memory" << std::endl;
}

// 创建多个栈变量
void createManyStackVariables() {
    // 创建 50 个栈变量
    LargeMemNode* nodes[50];
    
    for (int i = 0; i < 50; i++) {
        nodes[i] = new LargeMemNode(i);
    }
    
    std::cout << "Created 50 LargeMemNode objects on stack" << std::endl;
    
    std::cout << ">>> READY FOR GCORE <<<" << std::endl;
    std::cout << "PID: " << getpid() << std::endl;
    
    while (true) {
        sleep(3600);
    }
    
    // 防止编译器优化
    for (int i = 0; i < 50; i++) {
        (void)nodes[i];
    }
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "Large Memory Test - PID: " << getpid() << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;
    
    // 分配大内存
    allocateLargeMemory();
    
    // 创建多个栈变量
    createManyStackVariables();
    
    return 0;
}
