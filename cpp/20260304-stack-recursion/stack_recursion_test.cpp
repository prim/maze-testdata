/**
 * TC-B003: 递归函数深度处理测试
 * 
 * 测试目的：验证栈变量收集功能能正确处理深层递归调用
 * 
 * 测试场景：
 * - 递归深度 100+
 * - 每层递归有局部指针变量
 * 
 * 预期结果：
 * - 所有递归帧的局部变量被收集
 * - 无栈溢出或无限循环
 * - 同一地址被多个帧引用时，Go 端去重机制正常工作
 */

#include <iostream>
#include <unistd.h>
#include <cstring>

// 非多态类
struct RecursionNode {
    int depth;
    int data[16];  // 填充一些数据
    RecursionNode(int d) : depth(d) {
        for (int i = 0; i < 16; i++) {
            data[i] = d * 100 + i;
        }
    }
};

// 递归函数，每层创建一个对象
void recursiveFunction(int depth, int max_depth) {
    // 每层创建一个对象
    RecursionNode* node = new RecursionNode(depth);
    
    // 输出进度
    if (depth % 20 == 0) {
        std::cout << "Recursion depth: " << depth << ", node at " << node << std::endl;
    }
    
    if (depth >= max_depth) {
        // 达到最大深度，准备 gcore
        std::cout << ">>> READY FOR GCORE <<<" << std::endl;
        std::cout << "PID: " << getpid() << std::endl;
        std::cout << "Max recursion depth: " << max_depth << std::endl;
        
        while (true) {
            sleep(3600);
        }
    } else {
        // 继续递归
        recursiveFunction(depth + 1, max_depth);
    }
    
    // 防止编译器优化（实际上不会执行到这里）
    (void)node;
}

int main() {
    const int MAX_DEPTH = 100;  // 100 层递归
    
    std::cout << "========================================" << std::endl;
    std::cout << "Recursion Depth Test - PID: " << getpid() << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;
    std::cout << "Max recursion depth: " << MAX_DEPTH << std::endl;
    std::cout << "Expected objects: " << MAX_DEPTH << " RecursionNode instances" << std::endl;
    std::cout << std::endl;
    
    recursiveFunction(1, MAX_DEPTH);
    
    return 0;
}
