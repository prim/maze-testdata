/**
 * TC-B006: 引用类型处理测试
 * 
 * 测试目的：验证栈变量收集功能能正确处理引用类型
 * 
 * 测试场景：
 * - 使用引用类型参数：void func(MyClass& ref)
 * - 函数内有局部引用变量
 * 
 * 预期结果：
 * - TYPE_CODE_REF 类型的局部变量被正确识别
 * - 引用的目标地址被正确收集（引用在内存中表现为指针）
 */

#include <iostream>
#include <unistd.h>
#include <cstring>

// 非多态类
struct RefTarget {
    int id;
    char data[24];
    RefTarget(int _id) : id(_id) {
        memset(data, 'R', sizeof(data));
    }
};

// 函数：使用引用参数
void processByReference(RefTarget& ref, RefTarget* ptr) {
    // 局部引用变量
    RefTarget& local_ref = ref;
    
    // 局部指针变量
    RefTarget* local_ptr = ptr;
    
    std::cout << "Reference parameter at: " << &ref << std::endl;
    std::cout << "Pointer parameter at: " << ptr << std::endl;
    std::cout << "Local reference at: " << &local_ref << std::endl;
    std::cout << "Local pointer at: " << local_ptr << std::endl;
    
    std::cout << ">>> READY FOR GCORE <<<" << std::endl;
    std::cout << "PID: " << getpid() << std::endl;
    
    while (true) {
        sleep(3600);
    }
}

// 函数：返回引用的函数
RefTarget& getReference(RefTarget& obj) {
    return obj;
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "Reference Type Test - PID: " << getpid() << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;
    
    // 创建对象
    RefTarget* obj1 = new RefTarget(1);
    RefTarget* obj2 = new RefTarget(2);
    
    std::cout << "Created RefTarget objects:" << std::endl;
    std::cout << "  obj1: " << obj1 << std::endl;
    std::cout << "  obj2: " << obj2 << std::endl;
    std::cout << std::endl;
    
    // 使用引用传递
    RefTarget& ref1 = *obj1;
    RefTarget& ref2 = getReference(*obj2);
    
    std::cout << "Reference variables:" << std::endl;
    std::cout << "  ref1 refers to obj1" << std::endl;
    std::cout << "  ref2 refers to obj2" << std::endl;
    std::cout << std::endl;
    
    // 调用函数
    processByReference(ref1, obj2);
    
    return 0;
}
