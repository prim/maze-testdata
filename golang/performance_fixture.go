package main

import (
	"flag"
	"fmt"
	"runtime"
	"time"
)

type benchNode struct {
	Next    *benchNode
	Alt     *benchNode
	ID      uint64
	Payload [40]byte
}

var (
	benchRoots    []*benchNode
	benchChecksum uint64
)

func main() {
	objects := flag.Int("objects", 200000, "number of individually allocated heap nodes")
	flag.Parse()
	if *objects < 1 {
		panic("objects must be positive")
	}

	benchRoots = make([]*benchNode, *objects)
	for index := range benchRoots {
		node := &benchNode{ID: uint64(index)}
		node.Payload[0] = byte(index)
		node.Payload[len(node.Payload)-1] = byte(index >> 8)
		benchRoots[index] = node
	}
	for index, node := range benchRoots {
		node.Next = benchRoots[(index+1)%len(benchRoots)]
		node.Alt = benchRoots[(index*104729+17)%len(benchRoots)]
		benchChecksum += node.ID + uint64(node.Payload[0]) + uint64(node.Payload[len(node.Payload)-1])
	}
	runtime.GC()
	runtime.KeepAlive(benchRoots)
	fmt.Printf("READY FOR GCORE objects=%d checksum=%d\n", len(benchRoots), benchChecksum)
	for {
		time.Sleep(time.Hour)
	}
}
