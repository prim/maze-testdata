package main

import (
	"fmt"
	"os"
	"reflect"
	"runtime"
	"runtime/debug"
	"time"
	"unsafe"
)

// KnownPayload and UnsafePayload deliberately have the same size. Maze may
// name the first object because a typed *KnownPayload root reaches it. The
// second object stays live through unsafe.Pointer, which carries no element
// type, so allocation size alone is not sufficient type evidence.
type KnownPayload struct {
	Marker uint64
	Bytes  [120]byte
}

type UnsafePayload struct {
	Marker uint64
	Bytes  [120]byte
}

// InteriorPayload is kept alive only by a pointer into Bytes. The pointer
// proves liveness and the pointed-to byte's type, but not the type at the
// allocation's canonical start.
type InteriorPayload struct {
	Marker uint64
	Bytes  [2040]byte
}

// ClosurePayload is reachable only through a compiler-generated closure
// environment. The Go runtime has the pointer bitmap needed by GC, but the
// closure allocation has no ordinary source-level struct type from which Maze
// can propagate the captured field's business type.
type ClosurePayload struct {
	Marker uint64
	Bytes  [120]byte
}

type StackPayload struct {
	Marker uint64
	Bytes  [120]byte
}

type GarbageA struct {
	ID      uint64
	Peer    *GarbageB
	Payload [48]byte
}

type GarbageB struct {
	ID      uint64
	Peer    *GarbageA
	Payload [48]byte
}

var (
	GlobalKnown        *KnownPayload
	GlobalUnsafe       unsafe.Pointer
	GlobalInterior     *byte
	GlobalClosure      func() uint64
	GlobalDynamic      any
	GlobalStop         chan struct{}
	GlobalEscapeSink   any
	GlobalGarbageCount int
)

//go:noinline
func makeUnsafeOnly() unsafe.Pointer {
	value := &UnsafePayload{Marker: 0x2222222222222222}
	value.Bytes[17] = 0x22
	return unsafe.Pointer(value)
}

//go:noinline
func makeInteriorOnly() *byte {
	value := &InteriorPayload{Marker: 0x3333333333333333}
	value.Bytes[17] = 0x33
	return &value.Bytes[17]
}

//go:noinline
func makeClosure() func() uint64 {
	value := &ClosurePayload{Marker: 0x4444444444444444}
	value.Bytes[17] = 0x44
	return func() uint64 {
		runtime.KeepAlive(value)
		return value.Marker
	}
}

// makeDynamic constructs a type that has no compile-time DWARF DIE. Its
// runtime abi.Type still provides size and pointer-shape evidence, so Maze can
// publish a conservative reflect.generatedType... placeholder.
//
//go:noinline
func makeDynamic() any {
	typ := reflect.StructOf([]reflect.StructField{
		{Name: "Label", Type: reflect.TypeOf("")},
		{Name: "Next", Type: reflect.TypeOf((*int)(nil))},
		{Name: "Count", Type: reflect.TypeOf(uint64(0))},
	})
	value := reflect.New(typ).Elem()
	next := new(int)
	*next = 55
	value.Field(0).SetString("reflect-generated-value")
	value.Field(1).Set(reflect.ValueOf(next))
	value.Field(2).SetUint(0x5555555555555555)
	return value.Interface()
}

//go:noinline
func forceHeap(value any) {
	GlobalEscapeSink = value
	GlobalEscapeSink = nil
}

//go:noinline
func retainTypedOnStack(ready chan<- uintptr, stop <-chan struct{}) {
	value := &StackPayload{Marker: 0x6666666666666666}
	value.Bytes[17] = 0x66
	forceHeap(value)
	ready <- uintptr(unsafe.Pointer(value))
	<-stop
	runtime.KeepAlive(value)
}

// makeGarbageCycles creates allocations that remain in in-use spans because
// GC is disabled, but that have no global, stack, or runtime root after this
// function returns. Maze reports their bytes as aggregate garbage rather than
// inventing per-object types or root paths.
//
//go:noinline
func makeGarbageCycles(count int) {
	holders := make([]*GarbageA, count)
	for i := range holders {
		a := &GarbageA{ID: uint64(i)}
		b := &GarbageB{ID: uint64(i)}
		a.Peer = b
		b.Peer = a
		holders[i] = a
	}
	runtime.KeepAlive(holders)
}

type interfaceWords struct {
	typ  unsafe.Pointer
	data unsafe.Pointer
}

func closureAddress(fn *func() uint64) unsafe.Pointer {
	return *(*unsafe.Pointer)(unsafe.Pointer(fn))
}

func dynamicDataAddress(value *any) unsafe.Pointer {
	return (*interfaceWords)(unsafe.Pointer(value)).data
}

func interiorBaseAddress() unsafe.Pointer {
	offset := int(unsafe.Offsetof(InteriorPayload{}.Bytes)) + 17
	return unsafe.Add(unsafe.Pointer(GlobalInterior), -offset)
}

func main() {
	runtime.GC()
	debug.SetGCPercent(-1)

	GlobalKnown = &KnownPayload{Marker: 0x1111111111111111}
	GlobalKnown.Bytes[17] = 0x11
	GlobalUnsafe = makeUnsafeOnly()
	GlobalInterior = makeInteriorOnly()
	GlobalClosure = makeClosure()
	GlobalDynamic = makeDynamic()

	GlobalStop = make(chan struct{})
	stackReady := make(chan uintptr, 1)
	go retainTypedOnStack(stackReady, GlobalStop)
	stackAddress := <-stackReady

	GlobalGarbageCount = 10_000
	makeGarbageCycles(GlobalGarbageCount)

	fmt.Printf("pid=%d go=%s\n", os.Getpid(), runtime.Version())
	fmt.Printf("known_typed_root=%p size=%d expected=main.KnownPayload\n", GlobalKnown, unsafe.Sizeof(*GlobalKnown))
	fmt.Printf("unsafe_only=%p size=%d expected=unk128\n", GlobalUnsafe, unsafe.Sizeof(UnsafePayload{}))
	fmt.Printf("interior_base=%p interior_pointer=%p size=%d expected=unk2048\n", interiorBaseAddress(), GlobalInterior, unsafe.Sizeof(InteriorPayload{}))
	fmt.Printf("closure_environment=%p captured_marker=%#x expected=unknown-closure-shape\n", closureAddress(&GlobalClosure), GlobalClosure())
	fmt.Printf("reflect_value=%p runtime_type=%q expected=reflect.generatedType...\n", dynamicDataAddress(&GlobalDynamic), reflect.TypeOf(GlobalDynamic))
	fmt.Printf("typed_stack_root=%#x size=%d expected=main.StackPayload\n", stackAddress, unsafe.Sizeof(StackPayload{}))
	fmt.Printf("unrooted_cycles=%d pairs object_bytes=%d expected=aggregate-garbage-only\n", GlobalGarbageCount, GlobalGarbageCount*int(unsafe.Sizeof(GarbageA{})+unsafe.Sizeof(GarbageB{})))
	fmt.Println(">>> READY FOR MAZE LIVE PROFILE <<<")

	for {
		time.Sleep(time.Hour)
	}
}
