package main

import (
	"fmt"
	"os"
	"reflect"
	"runtime"
	"runtime/debug"
	"time"
)

type Node struct {
	ID       int
	Name     string
	Payload  []byte
	Next     *Node
	Children []*Node
}

type Blob struct {
	Marker uint64
	Data   [504]byte
}

var (
	GlobalRoot   *Node
	GlobalBytes  []byte
	GlobalMap    map[string]*Node
	GlobalIface  any
	GlobalGCProg any
	Block        = make(chan struct{})
)

//go:noinline
func makeGarbage() {
	garbage := make([]*Blob, 4096)
	for index := range garbage {
		garbage[index] = &Blob{Marker: uint64(index) + 0xfeed0000}
	}
	runtime.KeepAlive(garbage)
}

//go:noinline
func holdOnStack(root *Node) {
	<-Block
	runtime.KeepAlive(root)
}

func main() {
	nodes := make([]*Node, 256)
	for index := range nodes {
		nodes[index] = &Node{
			ID:      index,
			Name:    "maze-go-core-fixture-node",
			Payload: make([]byte, 4096+index%4),
		}
		if index > 0 {
			nodes[index-1].Next = nodes[index]
		}
	}
	nodes[0].Children = []*Node{nodes[64], nodes[128], nodes[192]}

	GlobalRoot = nodes[0]
	GlobalBytes = make([]byte, 3<<20)
	GlobalMap = map[string]*Node{
		"root": nodes[0],
		"mid":  nodes[128],
		"tail": nodes[255],
	}
	GlobalIface = nodes[192]
	gcProgType := reflect.ArrayOf(20000, reflect.TypeOf((*Node)(nil)))
	gcProgValue := reflect.New(gcProgType).Elem()
	for _, index := range []int{0, 8191, 16384, 19999} {
		gcProgValue.Index(index).Set(reflect.ValueOf(nodes[224+index%4]))
	}
	GlobalGCProg = gcProgValue.Interface()
	go holdOnStack(nodes[200])

	runtime.GC()
	debug.SetGCPercent(-1)
	makeGarbage()
	fmt.Printf("READY FOR GCORE pid=%d root=%p nodes=%d large=%d\n",
		os.Getpid(), GlobalRoot, len(nodes), len(GlobalBytes))
	for {
		time.Sleep(time.Hour)
	}
}
