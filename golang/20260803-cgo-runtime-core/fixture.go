package main

/*
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

enum { small_count = 4096, small_size = 1024 };

static void *large_allocation;
static void *small_allocations[small_count];
static volatile int blocker_entered;

static int allocate_native(void) {
	large_allocation = malloc(24 << 20);
	if (large_allocation == NULL) {
		return 0;
	}
	memset(large_allocation, 0xa5, 24 << 20);
	for (int index = 0; index < small_count; index++) {
		small_allocations[index] = malloc(small_size);
		if (small_allocations[index] == NULL) {
			return 0;
		}
		memset(small_allocations[index], index, small_size);
	}
	return 1;
}

static uint64_t native_payload_bytes(void) {
	return (24ULL << 20) + (uint64_t)small_count * small_size;
}

static uintptr_t native_large_address(void) {
	return (uintptr_t)large_allocation;
}

static uintptr_t native_small_address(void) {
	return (uintptr_t)small_allocations[0];
}

static void block_in_c(void) {
	blocker_entered = 1;
	for (;;) {
		sleep(3600);
	}
}

static int is_blocker_entered(void) {
	return blocker_entered;
}
*/
import "C"

import (
	"fmt"
	"os"
	"runtime"
	"time"
)

type Node struct {
	Next    *Node
	Payload []byte
	Index   int
}

var (
	GlobalRoot  *Node
	Large       []byte
	NativeLarge uintptr
	NativeSmall uintptr
)

func main() {
	if C.allocate_native() == 0 {
		panic("native allocation failed")
	}
	NativeLarge = uintptr(C.native_large_address())
	NativeSmall = uintptr(C.native_small_address())
	if NativeLarge == 0 || NativeSmall == 0 {
		panic("native allocation address is zero")
	}

	nodes := make([]*Node, 128)
	for index := range nodes {
		nodes[index] = &Node{Payload: make([]byte, 8192), Index: index}
		if index > 0 {
			nodes[index-1].Next = nodes[index]
		}
	}
	GlobalRoot = nodes[0]
	Large = make([]byte, 8<<20)
	for index := range Large {
		Large[index] = byte(index)
	}

	go C.block_in_c()
	for C.is_blocker_entered() == 0 {
		runtime.Gosched()
	}
	runtime.GC()
	fmt.Printf("READY FOR GCORE pid=%d root=%p nodes=%d go_large=%d native=%d native_large=%#x native_small=%#x\n",
		os.Getpid(), GlobalRoot, len(nodes), len(Large), uint64(C.native_payload_bytes()), NativeLarge, NativeSmall)
	for {
		time.Sleep(time.Hour)
	}
}
