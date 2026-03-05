/**
 * TC-B005: 智能指针处理测试
 * 
 * 测试目的：验证栈变量收集功能能正确处理智能指针
 * 
 * 测试场景：
 * - 使用 std::unique_ptr<MyClass> 和 std::shared_ptr<MyClass> 作为局部变量
 * - 确保 MyClass 是非多态类型（无虚表）
 * 
 * 预期结果：
 * - 智能指针作为结构体类型被识别（TYPE_CODE_STRUCT）
 * - 内部的 _M_ptr 成员被解析，指向的 MyClass 对象被识别
 * - 或智能指针本身作为栈变量，其指向的对象通过指针成员推导
 */

#include <iostream>
#include <unistd.h>
#include <cstring>
#include <memory>
#include <vector>

// 非多态类（无虚函数）
class SmartTarget {
public:
    int id;
    char data[48];
    
    SmartTarget(int _id) : id(_id) {
        memset(data, 'S', sizeof(data));
    }
    
    // 注意：没有虚函数，不是多态类
    void print() const {
        std::cout << "SmartTarget " << id << std::endl;
    }
};

// 函数：测试 unique_ptr
void testUniquePtr() {
    std::unique_ptr<SmartTarget> uniq1 = std::make_unique<SmartTarget>(1);
    std::unique_ptr<SmartTarget> uniq2 = std::make_unique<SmartTarget>(2);
    std::unique_ptr<SmartTarget> uniq3 = std::make_unique<SmartTarget>(3);
    
    std::cout << "Created 3 unique_ptr<SmartTarget>" << std::endl;
    std::cout << "  uniq1: " << uniq1.get() << std::endl;
    std::cout << "  uniq2: " << uniq2.get() << std::endl;
    std::cout << "  uniq3: " << uniq3.get() << std::endl;
}

// 函数：测试 shared_ptr
void testSharedPtr() {
    std::shared_ptr<SmartTarget> shared1 = std::make_shared<SmartTarget>(4);
    std::shared_ptr<SmartTarget> shared2 = std::make_shared<SmartTarget>(5);
    std::shared_ptr<SmartTarget> shared3 = std::shared_ptr<SmartTarget>(shared1);  // 共享所有权
    
    std::cout << "Created 3 shared_ptr<SmartTarget> (2 unique objects)" << std::endl;
    std::cout << "  shared1: " << shared1.get() << std::endl;
    std::cout << "  shared2: " << shared2.get() << std::endl;
    std::cout << "  shared3: " << shared3.get() << " (shares with shared1)" << std::endl;
    
    // 等待 gcore
    std::cout << ">>> READY FOR GCORE <<<" << std::endl;
    std::cout << "PID: " << getpid() << std::endl;
    
    while (true) {
        sleep(3600);
    }
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "Smart Pointer Test - PID: " << getpid() << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;
    std::cout << "Testing unique_ptr and shared_ptr" << std::endl;
    std::cout << "Expected SmartTarget objects: 5" << std::endl;
    std::cout << "  - 3 from unique_ptr" << std::endl;
    std::cout << "  - 2 from shared_ptr (one is shared)" << std::endl;
    std::cout << std::endl;
    
    testUniquePtr();
    testSharedPtr();
    
    return 0;
}
