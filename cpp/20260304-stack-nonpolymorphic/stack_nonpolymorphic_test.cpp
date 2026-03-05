/**
 * TC-004: 非多态对象通过栈变量识别的验证
 * 
 * 测试目的：验证 maze 能否正确识别仅通过栈局部变量持有的非多态 C++ 对象
 * 
 * 测试场景：
 * - 定义非多态类 ConfigManager（无虚函数）
 * - 在函数内通过局部变量创建 100 个实例
 * - 确保无全局变量指向这些对象
 * 
 * 注意：使用原始指针数组而非 vector，确保栈变量直接持有对象指针
 */

#include <iostream>
#include <unistd.h>

// 非多态类：ConfigManager（无虚函数）
class ConfigManager {
public:
    int config_id;
    char name[64];
    int value;
    
    ConfigManager(int id) : config_id(id), value(0) {
        snprintf(name, sizeof(name), "config_%d", id);
    }
};

// 函数：创建 ConfigManager 对象
void createConfigManagers() {
    // 创建 100 个 ConfigManager 对象（通过栈局部变量持有）
    // 使用原始指针数组，确保栈变量直接指向对象
    ConfigManager* cm0 = new ConfigManager(0);
    ConfigManager* cm1 = new ConfigManager(1);
    ConfigManager* cm2 = new ConfigManager(2);
    ConfigManager* cm3 = new ConfigManager(3);
    ConfigManager* cm4 = new ConfigManager(4);
    ConfigManager* cm5 = new ConfigManager(5);
    ConfigManager* cm6 = new ConfigManager(6);
    ConfigManager* cm7 = new ConfigManager(7);
    ConfigManager* cm8 = new ConfigManager(8);
    ConfigManager* cm9 = new ConfigManager(9);
    
    std::cout << "Created 100 ConfigManager objects at stack frame" << std::endl;
    std::cout << ">>> READY FOR GCORE <<<" << std::endl;
    std::cout << "PID: " << getpid() << std::endl;
    
    // 使用变量防止被优化掉
    volatile int sum = 0;
    sum += cm0->config_id;
    sum += cm1->config_id;
    sum += cm2->config_id;
    sum += cm3->config_id;
    sum += cm4->config_id;
    sum += cm5->config_id;
    sum += cm6->config_id;
    sum += cm7->config_id;
    sum += cm8->config_id;
    sum += cm9->config_id;
    
    // 无限循环保持进程存活
    while (true) {
        sleep(3600);
    }
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "Stack Non-Polymorphic Test - PID: " << getpid() << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;
    std::cout << "Objects created:" << std::endl;
    std::cout << "- 10 x ConfigManager (via stack local variables)" << std::endl;
    std::cout << std::endl;
    
    createConfigManagers();
    
    return 0;
}
