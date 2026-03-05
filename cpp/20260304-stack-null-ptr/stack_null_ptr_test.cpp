/**
 * TC-B001: 空指针和 NULL 处理测试
 * 
 * 测试目的：验证栈变量收集功能能正确处理空指针和无效地址
 * 
 * 测试场景：
 * - 局部指针变量显式赋值为 nullptr
 * - 局部指针变量未初始化（野指针）
 * - 局部指针变量指向已 delete 的对象
 * 
 * 预期结果：
 * - 空指针（nullptr/NULL）被过滤，不进入 stack_locals
 * - 无效地址（0x0 或内核地址）被过滤
 * - 已释放内存的指针被过滤（size == 0）
 * - 无崩溃或异常
 */

#include <iostream>
#include <unistd.h>
#include <cstring>

// 非多态类
struct TestObject {
    int id;
    char data[32];
    TestObject(int _id) : id(_id) {
        memset(data, 'X', sizeof(data));
    }
};

// 函数：测试空指针场景
void testNullPointers() {
    // 有效对象（应该被识别）
    TestObject* valid_obj = new TestObject(1);
    
    // 空指针（应该被过滤）
    TestObject* null_ptr = nullptr;
    TestObject* null_ptr2 = NULL;
    
    // 零值（应该被过滤）
    TestObject* zero_ptr = (TestObject*)0;
    
    // 内核地址（应该被过滤）
    TestObject* kernel_ptr = (TestObject*)0xffffffffff600000;
    
    // 低地址（应该被过滤）
    TestObject* low_ptr = (TestObject*)0x100;
    
    // 未初始化指针（野指针，应该被过滤）
    TestObject* wild_ptr;
    // 故意不初始化，让它包含随机值
    
    // 已释放的对象（应该被过滤）
    TestObject* deleted_obj = new TestObject(999);
    delete deleted_obj;  // 释放后指针成为悬空指针
    
    std::cout << "valid_obj: " << valid_obj << std::endl;
    std::cout << "null_ptr: " << null_ptr << std::endl;
    std::cout << "null_ptr2: " << null_ptr2 << std::endl;
    std::cout << "zero_ptr: " << zero_ptr << std::endl;
    std::cout << "kernel_ptr: " << kernel_ptr << std::endl;
    std::cout << "low_ptr: " << low_ptr << std::endl;
    std::cout << "wild_ptr: " << wild_ptr << std::endl;
    std::cout << "deleted_obj (dangling): " << deleted_obj << std::endl;
    
    std::cout << ">>> READY FOR GCORE <<<" << std::endl;
    std::cout << "PID: " << getpid() << std::endl;
    
    while (true) {
        sleep(3600);
    }
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "Null Pointer Test - PID: " << getpid() << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;
    std::cout << "Test scenarios:" << std::endl;
    std::cout << "- 1 valid TestObject (should be detected)" << std::endl;
    std::cout << "- 1 nullptr (should be filtered)" << std::endl;
    std::cout << "- 1 NULL (should be filtered)" << std::endl;
    std::cout << "- 1 zero address (should be filtered)" << std::endl;
    std::cout << "- 1 kernel address (should be filtered)" << std::endl;
    std::cout << "- 1 low address (should be filtered)" << std::endl;
    std::cout << "- 1 wild pointer (should be filtered)" << std::endl;
    std::cout << "- 1 dangling pointer (should be filtered)" << std::endl;
    std::cout << std::endl;
    
    testNullPointers();
    
    return 0;
}
