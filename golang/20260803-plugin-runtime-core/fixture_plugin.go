package main

import "runtime"

type PluginNode struct {
	Index    int
	Name     string
	Next     *PluginNode
	Children []*PluginNode
	Payload  []byte
}

var (
	PluginGlobal *PluginNode
	PluginLarge  []byte
	Hold         = make(chan struct{})
)

//go:noinline
func holdPluginRoot(root *PluginNode) {
	<-Hold
	runtime.KeepAlive(root)
}

func makeNodes(begin, count int) []*PluginNode {
	nodes := make([]*PluginNode, count)
	for index := range nodes {
		nodes[index] = &PluginNode{
			Index:   begin + index,
			Name:    "maze-go-plugin-node",
			Payload: make([]byte, 4096),
		}
		if index > 0 {
			nodes[index-1].Next = nodes[index]
		}
	}
	return nodes
}

func BuildGraph() any {
	public := makeNodes(0, 128)
	private := makeNodes(128, 64)
	public[0].Children = []*PluginNode{public[32], public[64], public[96]}
	private[0].Children = []*PluginNode{private[32], private[63]}
	PluginGlobal = private[0]
	PluginLarge = make([]byte, 5<<20)
	for index := range PluginLarge {
		PluginLarge[index] = byte(index)
	}
	go holdPluginRoot(public[100])
	return public[0]
}
