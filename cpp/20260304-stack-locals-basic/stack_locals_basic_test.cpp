/**
 * TC-001: 基础栈变量收集测试
 * 
 * 测试目的：验证 maze 能否正确收集函数栈帧中的局部变量
 * 
 * 测试场景：
 * - 创建非多态类（无虚函数）
 * - 通过函数局部变量持有对象指针
 * - 这些对象只能通过栈变量访问，没有全局引用
 */

#include <iostream>
#include <unistd.h>
#include <cstring>

// 非多态类：Point（无虚函数）
struct Point {
    int x;
    int y;
    Point(int _x, int _y) : x(_x), y(_y) {}
};

// 非多态类：DataBlock（无虚函数）
struct DataBlock {
    char buffer[64];
    int id;
    DataBlock(int _id) : id(_id) {
        memset(buffer, 'A', sizeof(buffer));
    }
};

// 非多态类：SimpleNode（无虚函数）
struct SimpleNode {
    int value;
    SimpleNode* next;
    SimpleNode(int v) : value(v), next(nullptr) {}
};

// 函数：创建 Point 对象，通过局部变量持有
void createPoints() {
    Point* p1 = new Point(10, 20);
    Point* p2 = new Point(30, 40);
    Point* p3 = new Point(50, 60);
    
    // 输出信号，表示对象已创建
    std::cout << "Created 3 Point objects at stack frame" << std::endl;
    
    // 保持局部变量在栈上，进入等待状态
    std::cout << ">>> READY FOR GCORE <<<" << std::endl;
    std::cout << "PID: " << getpid() << std::endl;
    
    // 无限循环保持进程存活
    while (true) {
        sleep(3600);
    }
}

// 函数：创建 DataBlock 对象
void createDataBlocks() {
    DataBlock* d1 = new DataBlock(1);
    DataBlock* d2 = new DataBlock(2);
    
    std::cout << "Created 2 DataBlock objects at stack frame" << std::endl;
    
    // 调用下一个函数，创建更深的栈帧
    createPoints();
}

// 函数：创建 SimpleNode 链表
void createSimpleNodes() {
    SimpleNode* head = new SimpleNode(100);
    head->next = new SimpleNode(200);
    head->next->next = new SimpleNode(300);
    
    std::cout << "Created 3 SimpleNode objects (linked list) at stack frame" << std::endl;
    
    // 调用下一个函数
    createDataBlocks();
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "Stack Locals Basic Test - PID: " << getpid() << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;
    std::cout << "Objects created:" << std::endl;
    std::cout << "- 3 x Point (stack variable p1, p2, p3)" << std::endl;
    std::cout << "- 2 x DataBlock (stack variable d1, d2)" << std::endl;
    std::cout << "- 3 x SimpleNode (stack variable head and linked)" << std::endl;
    std::cout << std::endl;
    
    // 进入函数调用链，创建多层栈帧
    createSimpleNodes();
    
    return 0;
}
