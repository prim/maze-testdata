package main

import (
	"fmt"
	"os"
	"plugin"
	"reflect"
	"runtime"
	"time"
)

var PluginRoot any

func main() {
	if len(os.Args) != 2 {
		panic("usage: fixture <plugin.so>")
	}
	loaded, err := plugin.Open(os.Args[1])
	if err != nil {
		panic(err)
	}
	symbol, err := loaded.Lookup("BuildGraph")
	if err != nil {
		panic(err)
	}
	buildGraph, ok := symbol.(func() any)
	if !ok {
		panic("plugin BuildGraph has unexpected type")
	}
	PluginRoot = buildGraph()
	runtime.GC()
	fmt.Printf("READY FOR GCORE pid=%d root_type=%s plugin=%s\n",
		os.Getpid(), reflect.TypeOf(PluginRoot), os.Args[1])
	for {
		time.Sleep(time.Hour)
	}
}
