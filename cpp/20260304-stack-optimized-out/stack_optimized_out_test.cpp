/**
 * TC-B002: Optimized Out 变量处理测试
 * 
 * 测试目的：验证栈变量收集功能能正确处理被编译器优化的变量
 * 
 * 测试场景：
 * - 使用 -O2 编译优化
 * - 函数内有指针局部变量，但在 coredump 时刻可能已被优化
 * 
 * 预期结果：
 * - <optimized out> 的变量被过滤
 * - GDB 端不收集值为 <optimized out> 的符号
 * - 无异常抛出
 */

#include <iostream>
#include <unistd.h>
#include <cstring>

// 非多态类
struct OptimizedTest {
    int id;
    char data[64];
    OptimizedTest(int _id) : id(_id) {
        memset(data, 'O', sizeof(data));
    }
};

// 强制内联的函数，可能导致变量被优化
inline __attribute__((always_inline)) void inlineFunction() {
    // 这些变量可能在优化后被消除
    OptimizedTest* temp1 = new OptimizedTest(1);
    OptimizedTest* temp2 = new OptimizedTest(2);
    
    // 使用 volatile 防止某些优化
    volatile int dummy = temp1->id + temp2->id;
    (void)dummy;
    
    // 继续执行，不释放对象
    std::cout << "Inline function objects created" << std::endl;
}

// 多层调用，测试优化场景
void level3() {
    OptimizedTest* l3_obj = new OptimizedTest(3);
    (void)l3_obj;  // 防止未使用警告
    
    std::cout << ">>> READY FOR GCORE <<<" << std::endl;
    std::cout << "PID: " << getpid() << std::endl;
    
    while (true) {
        sleep(3600);
    }
}

void level2() {
    OptimizedTest* l2_obj = new OptimizedTest(2);
    // 调用 level3，l2_obj 可能在 level3 的栈帧中不可见或被优化
    level3();
    (void)l2_obj;
}

void level1() {
    OptimizedTest* l1_obj = new OptimizedTest(1);
    // 调用 level2
    level2();
    (void)l1_obj;
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "Optimized Out Test - PID: " << getpid() << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;
    std::cout << "Compile with: g++ -g -O2 for optimization" << std::endl;
    std::cout << "Some variables may be optimized out" << std::endl;
    std::cout << std::endl;
    
    // 先调用内联函数
    inlineFunction();
    
    // 进入多层调用
    level1();
    
    return 0;
}
