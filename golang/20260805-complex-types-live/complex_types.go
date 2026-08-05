package main

import (
	"container/list"
	"container/ring"
	"fmt"
	"math"
	"os"
	"runtime"
	"runtime/debug"
	"sync"
	"time"
)

type UserID uint64

type EntityStatus uint8

const (
	StatusUnknown EntityStatus = iota
	StatusActive
	StatusSleeping
)

type SimpleClass struct {
	Marker uint64
}

type Point struct {
	X float64
	Y float64
}

type Rectangle struct {
	X      int
	Y      int
	Width  int
	Height int
}

type Tuple1 struct {
	First int
}

type Tuple2 struct {
	First  int
	Second int
}

type Tuple3 struct {
	First  int
	Second string
	Third  float64
}

type MixedTuple struct {
	Values [6]any
	Tail   []int
}

type Person struct {
	ID       UserID
	Name     string
	Age      uint8
	Email    string
	Tags     []string
	Metadata map[string]string
}

type Item struct {
	SKU      string
	Quantity int
	Weight   float32
}

type GameEntity struct {
	EntityID  uint64
	Position  Point
	HP        int32
	Status    EntityStatus
	Inventory []Item
	Owner     *Person
	Flags     map[string]bool
	Payload   []byte
}

type TreeNode struct {
	Value  int
	Label  string
	Left   *TreeNode
	Right  *TreeNode
	Parent *TreeNode
}

type Config struct {
	Host    string
	Port    uint16
	Debug   bool
	Timeout time.Duration
}

type Audit struct {
	CreatedAt time.Time
	UpdatedAt time.Time
}

type Player struct {
	Audit
	Person *Person
	Level  int
	Health float64
	Items  []Item
	Config *Config
}

type ByteRecord struct {
	Kind    string
	Data    []byte
	Fixed   [32]byte
	Mutable bool
}

type StringRecord struct {
	Kind  string
	Value string
}

type NumericBox struct {
	Signed   int64
	Unsigned uint64
	Float    float64
	Complex  complex128
	Flag     bool
}

type Shape interface {
	Area() float64
	Kind() string
}

type Circle struct {
	Center Point
	Radius float64
	Owner  *Person
}

func (circle *Circle) Area() float64 {
	return math.Pi * circle.Radius * circle.Radius
}

func (circle *Circle) Kind() string {
	return "circle"
}

type BoxShape struct {
	Bounds Rectangle
	Owner  *Person
}

func (box *BoxShape) Area() float64 {
	return float64(box.Bounds.Width * box.Bounds.Height)
}

func (box *BoxShape) Kind() string {
	return "rectangle"
}

type Box[T any] struct {
	Value T
	Next  *Box[T]
}

type Pair[K comparable, V any] struct {
	Key   K
	Value V
}

type Transform func(int) int

type CallbackHolder struct {
	Name      string
	Transform Transform
}

type FixtureError struct {
	Code    int
	Message string
	Cause   error
}

func (failure *FixtureError) Error() string {
	return fmt.Sprintf("fixture error %d: %s", failure.Code, failure.Message)
}

type Envelope struct {
	Kind  string
	Value any
	Err   error
}

type BaseRecord struct {
	ID        uint64
	CreatedAt time.Time
}

type CompositeRecord struct {
	BaseRecord
	Config *Config
	Owner  *Person
	Lookup map[string]*Person
	Matrix [][]int
	Mixed  []any
}

type FixtureStore struct {
	Counts map[string]int

	EmptySlices  [][]int
	SingleSlices [][]int
	TenSlices    [][]int
	MixedSlices  [][]any
	NestedSlices [][][]int

	Tuple1s     []*Tuple1
	Tuple2s     []*Tuple2
	Tuple3s     []*Tuple3
	MixedTuples []*MixedTuple

	SimpleClasses []*SimpleClass
	Persons       []*Person
	Entities      []*GameEntity
	TreeNodes     []*TreeNode
	Players       []*Player
	Configs       []*Config

	SmallSets  []map[int]struct{}
	LargeSets  []map[int]struct{}
	FrozenSets []*[4]int

	ByteRecords   []*ByteRecord
	SimpleMaps    []map[string]int64
	NestedMaps    []map[string]any
	WideMaps      []map[string]int
	IndexMaps     []map[int]*TreeNode
	ConcurrentMap []*sync.Map
	Counters      []map[string]int

	Strings  []*StringRecord
	Numerics []*NumericBox
	Lists    []*list.List
	Points   []*Point
	Rects    []*Rectangle

	Rings      []*ring.Ring
	Shapes     []Shape
	Boxes      []*Box[*Person]
	Pairs      []*Pair[string, *TreeNode]
	Channels   []chan *TreeNode
	Callbacks  []*CallbackHolder
	Envelopes  []*Envelope
	Composites []*CompositeRecord
}

var (
	GlobalStore        *FixtureStore
	GlobalSamplePerson *Person
	GlobalSampleEntity *GameEntity
	GlobalSampleTree   *TreeNode
	GlobalSampleBox    *Box[*Person]
	GlobalSampleShape  Shape
	Park               = make(chan struct{})
)

func createSlices(store *FixtureStore) {
	store.EmptySlices = make([][]int, 0, 1000)
	for range 1000 {
		store.EmptySlices = append(store.EmptySlices, make([]int, 0))
	}

	store.SingleSlices = make([][]int, 0, 1000)
	for index := range 1000 {
		store.SingleSlices = append(store.SingleSlices, []int{index})
	}

	store.TenSlices = make([][]int, 0, 500)
	for index := range 500 {
		values := make([]int, 10)
		for offset := range values {
			values[offset] = index*10 + offset
		}
		store.TenSlices = append(store.TenSlices, values)
	}

	store.MixedSlices = make([][]any, 0, 200)
	for index := range 200 {
		store.MixedSlices = append(store.MixedSlices, []any{
			index,
			fmt.Sprintf("mixed-%d", index),
			float64(index) + 0.25,
			nil,
			index%2 == 0,
		})
	}

	store.NestedSlices = make([][][]int, 0, 100)
	for index := range 100 {
		store.NestedSlices = append(store.NestedSlices, [][]int{
			{index, index + 1},
			{index + 2, index + 3},
			{index + 4, index + 5},
		})
	}
	store.Counts["slice variants"] = 2800
}

func createTuples(store *FixtureStore) {
	for index := range 1000 {
		store.Tuple1s = append(store.Tuple1s, &Tuple1{First: index})
	}
	for index := range 800 {
		store.Tuple2s = append(store.Tuple2s, &Tuple2{First: index, Second: index * 2})
	}
	for index := range 500 {
		store.Tuple3s = append(store.Tuple3s, &Tuple3{
			First: index, Second: fmt.Sprintf("item-%d", index), Third: float64(index),
		})
	}
	for index := range 200 {
		store.MixedTuples = append(store.MixedTuples, &MixedTuple{
			Values: [6]any{index, "tuple", 3.14, nil, true, complex(float64(index), float64(index+1))},
			Tail:   []int{1, 2, 3},
		})
	}
	store.Counts["tuple structs"] = 2500
}

func createClassInstances(store *FixtureStore) {
	for index := range 500 {
		store.SimpleClasses = append(store.SimpleClasses, &SimpleClass{Marker: 0xface0000 + uint64(index)})
	}

	for index := range 1000 {
		store.Persons = append(store.Persons, &Person{
			ID:    UserID(index + 1),
			Name:  fmt.Sprintf("user_%d", index),
			Age:   uint8(20 + index%50),
			Email: fmt.Sprintf("user%d@example.com", index),
			Tags:  []string{"golang", fmt.Sprintf("group-%d", index%16)},
			Metadata: map[string]string{
				"locale": "zh-CN",
				"tier":   fmt.Sprintf("tier-%d", index%4),
			},
		})
	}

	for index := range 300 {
		store.Entities = append(store.Entities, &GameEntity{
			EntityID: uint64(index + 1),
			Position: Point{X: float64(index * 10), Y: float64(index * 20)},
			HP:       100,
			Status:   StatusActive,
			Inventory: []Item{
				{SKU: "sword", Quantity: 1, Weight: 5.5},
				{SKU: "shield", Quantity: 1, Weight: 8.25},
				{SKU: "potion", Quantity: 3, Weight: 0.5},
			},
			Owner:   store.Persons[index%len(store.Persons)],
			Flags:   map[string]bool{"alive": true, "elite": index%10 == 0},
			Payload: []byte(fmt.Sprintf("entity-payload-%04d", index)),
		})
	}

	for index := range 200 {
		root := &TreeNode{Value: index, Label: fmt.Sprintf("root-%d", index)}
		left := &TreeNode{Value: index * 2, Label: fmt.Sprintf("left-%d", index), Parent: root}
		right := &TreeNode{Value: index*2 + 1, Label: fmt.Sprintf("right-%d", index), Parent: root}
		root.Left = left
		root.Right = right
		store.TreeNodes = append(store.TreeNodes, root, left, right)
	}
	store.Counts["class-like structs"] = 2400
}

func createDataRecords(store *FixtureStore) {
	for index := range 300 {
		store.Configs = append(store.Configs, &Config{
			Host:    fmt.Sprintf("server%d.example.com", index),
			Port:    uint16(8000 + index),
			Debug:   index%2 == 0,
			Timeout: time.Duration(index+1) * time.Second,
		})
	}

	for index := range 500 {
		created := time.Unix(1_800_000_000+int64(index), 0).UTC()
		store.Players = append(store.Players, &Player{
			Audit:  Audit{CreatedAt: created, UpdatedAt: created.Add(time.Minute)},
			Person: store.Persons[index%len(store.Persons)],
			Level:  index % 100,
			Health: 100.0 - float64(index%50),
			Items:  []Item{{SKU: "sword", Quantity: 1}, {SKU: "potion", Quantity: 2}},
			Config: store.Configs[index%len(store.Configs)],
		})
	}
	store.Counts["data records"] = 800
}

func createSets(store *FixtureStore) {
	for index := range 500 {
		store.SmallSets = append(store.SmallSets, map[int]struct{}{
			index: {}, index + 1: {}, index + 2: {},
		})
	}
	for index := range 300 {
		set := make(map[int]struct{}, 20)
		for value := index; value < index+20; value++ {
			set[value] = struct{}{}
		}
		store.LargeSets = append(store.LargeSets, set)
	}
	for index := range 400 {
		store.FrozenSets = append(store.FrozenSets, &[4]int{index, index + 1, index + 2, index + 3})
	}
	store.Counts["set analogues"] = 1200
}

func appendByteRecord(store *FixtureStore, kind string, data []byte, mutable bool) {
	record := &ByteRecord{Kind: kind, Data: data, Mutable: mutable}
	copy(record.Fixed[:], data)
	store.ByteRecords = append(store.ByteRecords, record)
}

func createBytes(store *FixtureStore) {
	for index := range 500 {
		appendByteRecord(store, "short", []byte(fmt.Sprintf("hello%d", index)), false)
	}
	for range 300 {
		appendByteRecord(store, "medium", []byte(fmt.Sprintf("%0100s", "x")), false)
	}
	for range 200 {
		appendByteRecord(store, "large", make([]byte, 1000), false)
	}
	for index := range 400 {
		appendByteRecord(store, "mutable", []byte(fmt.Sprintf("data_%d", index)), true)
	}
	store.Counts["byte records"] = 1400
}

func createMaps(store *FixtureStore) {
	for index := range 1000 {
		store.SimpleMaps = append(store.SimpleMaps, map[string]int64{
			"id": int64(index), "value": int64(index * 10),
		})
	}

	for index := range 500 {
		store.NestedMaps = append(store.NestedMaps, map[string]any{
			"user": map[string]any{
				"id": index,
				"profile": map[string]any{
					"name":     fmt.Sprintf("user_%d", index),
					"settings": map[string]string{"theme": "dark", "lang": "zh"},
				},
			},
		})
	}

	for index := range 300 {
		wide := make(map[string]int, 20)
		for key := range 20 {
			wide[fmt.Sprintf("key_%d", key)] = index*20 + key
		}
		store.WideMaps = append(store.WideMaps, wide)
	}

	for index := range 200 {
		store.IndexMaps = append(store.IndexMaps, map[int]*TreeNode{
			index:     store.TreeNodes[(index*3)%len(store.TreeNodes)],
			index + 1: store.TreeNodes[(index*3+1)%len(store.TreeNodes)],
		})
	}

	for index := range 200 {
		mapping := &sync.Map{}
		mapping.Store("person", store.Persons[index%len(store.Persons)])
		mapping.Store(index, store.Entities[index%len(store.Entities)])
		store.ConcurrentMap = append(store.ConcurrentMap, mapping)
	}

	for range 200 {
		store.Counters = append(store.Counters, map[string]int{"a": 3, "b": 2, "c": 1})
	}
	store.Counts["map variants"] = 2400
}

func createStrings(store *FixtureStore) {
	for index := range 1000 {
		store.Strings = append(store.Strings, &StringRecord{Kind: "short", Value: fmt.Sprintf("str_%d", index)})
	}
	for index := range 500 {
		store.Strings = append(store.Strings, &StringRecord{
			Kind: "medium", Value: fmt.Sprintf("medium_string_%d_%050s", index, "x"),
		})
	}
	for index := range 200 {
		store.Strings = append(store.Strings, &StringRecord{
			Kind: "long", Value: fmt.Sprintf("long_string_%d_%0500s", index, "y"),
		})
	}
	for index := range 300 {
		store.Strings = append(store.Strings, &StringRecord{
			Kind: "unicode", Value: fmt.Sprintf("中文字符串_%d_你好世界", index),
		})
	}
	store.Counts["string records"] = 2000
}

func createNumerics(store *FixtureStore) {
	for index := range 500 {
		store.Numerics = append(store.Numerics, &NumericBox{
			Signed: int64(10_000_000 + index), Unsigned: uint64(index), Flag: index%2 == 0,
		})
	}
	for index := range 500 {
		store.Numerics = append(store.Numerics, &NumericBox{
			Float: float64(index) * math.Pi, Unsigned: uint64(index), Flag: true,
		})
	}
	for index := range 300 {
		store.Numerics = append(store.Numerics, &NumericBox{
			Complex: complex(float64(index), float64(index+1)), Signed: int64(index),
		})
	}
	store.Counts["numeric boxes"] = 1300
}

func createCollections(store *FixtureStore) {
	for index := range 300 {
		values := list.New()
		for offset := range 6 {
			values.PushBack(&Item{SKU: fmt.Sprintf("list-%d-%d", index, offset), Quantity: offset + 1})
		}
		store.Lists = append(store.Lists, values)
	}
	for index := range 400 {
		store.Points = append(store.Points, &Point{X: float64(index), Y: float64(index * 2)})
	}
	for index := range 300 {
		store.Rects = append(store.Rects, &Rectangle{X: index, Y: index, Width: 100, Height: 50})
	}
	store.Counts["collection records"] = 1000
}

func createGoSpecific(store *FixtureStore) {
	for index := range 100 {
		values := ring.New(8)
		cursor := values
		for offset := range 8 {
			cursor.Value = &Pair[string, int]{
				Key: fmt.Sprintf("ring-%d-%d", index, offset), Value: index*8 + offset,
			}
			cursor = cursor.Next()
		}
		store.Rings = append(store.Rings, values)
	}

	for index := range 100 {
		store.Shapes = append(store.Shapes, &Circle{
			Center: Point{X: float64(index), Y: float64(-index)},
			Radius: float64(index%10 + 1),
			Owner:  store.Persons[index],
		})
		store.Shapes = append(store.Shapes, &BoxShape{
			Bounds: Rectangle{X: index, Y: index, Width: index%20 + 1, Height: index%30 + 1},
			Owner:  store.Persons[index+100],
		})
	}

	var previous *Box[*Person]
	for index := range 200 {
		current := &Box[*Person]{Value: store.Persons[index], Next: previous}
		store.Boxes = append(store.Boxes, current)
		previous = current
	}

	for index := range 200 {
		store.Pairs = append(store.Pairs, &Pair[string, *TreeNode]{
			Key: fmt.Sprintf("tree-%d", index), Value: store.TreeNodes[index*3],
		})
	}

	for index := range 50 {
		channel := make(chan *TreeNode, 4)
		channel <- store.TreeNodes[index*3]
		channel <- store.TreeNodes[index*3+1]
		store.Channels = append(store.Channels, channel)
	}

	for index := range 100 {
		offset := index
		store.Callbacks = append(store.Callbacks, &CallbackHolder{
			Name: fmt.Sprintf("closure-%d", index),
			Transform: func(value int) int {
				return value + offset
			},
		})
	}

	for index := range 100 {
		failure := &FixtureError{Code: index, Message: fmt.Sprintf("failure-%d", index)}
		store.Envelopes = append(store.Envelopes, &Envelope{
			Kind: "person-or-error", Value: store.Persons[index], Err: failure,
		})
	}

	for index := range 50 {
		store.Composites = append(store.Composites, &CompositeRecord{
			BaseRecord: BaseRecord{ID: uint64(index), CreatedAt: time.Unix(1_800_100_000+int64(index), 0)},
			Config:     store.Configs[index],
			Owner:      store.Persons[index],
			Lookup: map[string]*Person{
				"owner": store.Persons[index], "peer": store.Persons[index+1],
			},
			Matrix: [][]int{{index, index + 1}, {index + 2, index + 3}},
			Mixed:  []any{store.Entities[index], store.Shapes[index], store.Boxes[index]},
		})
	}
	store.Counts["Go-specific objects"] = 1000
}

//go:noinline
func holdOnStack(index int, value any) {
	stackRoots := [3]any{value, fmt.Sprintf("stack-root-%d", index), &NumericBox{Signed: int64(index)}}
	<-Park
	runtime.KeepAlive(stackRoots)
}

func main() {
	store := &FixtureStore{Counts: make(map[string]int)}
	createSlices(store)
	createTuples(store)
	createClassInstances(store)
	createDataRecords(store)
	createSets(store)
	createBytes(store)
	createMaps(store)
	createStrings(store)
	createNumerics(store)
	createCollections(store)
	createGoSpecific(store)

	GlobalStore = store
	GlobalSamplePerson = store.Persons[777]
	GlobalSampleEntity = store.Entities[123]
	GlobalSampleTree = store.TreeNodes[301]
	GlobalSampleBox = store.Boxes[len(store.Boxes)-1]
	GlobalSampleShape = store.Shapes[111]

	for index := range 16 {
		if index%2 == 0 {
			go holdOnStack(index, store.TreeNodes[index*3+1])
		} else {
			go holdOnStack(index, store.Persons[900+index])
		}
	}

	runtime.GC()
	debug.SetGCPercent(-1)

	var memory runtime.MemStats
	runtime.ReadMemStats(&memory)
	order := []string{
		"slice variants",
		"tuple structs",
		"class-like structs",
		"data records",
		"set analogues",
		"byte records",
		"map variants",
		"string records",
		"numeric boxes",
		"collection records",
		"Go-specific objects",
	}
	total := 0

	fmt.Println("============================================================")
	fmt.Println("Complex Types Test Process - Go")
	fmt.Printf("PID: %d\n", os.Getpid())
	fmt.Printf("Go Version: %s\n", runtime.Version())
	fmt.Printf("HeapAlloc: %d bytes\n", memory.HeapAlloc)
	fmt.Println("Coverage counts:")
	for _, category := range order {
		count := store.Counts[category]
		total += count
		fmt.Printf("  %-24s %d\n", category+":", count)
	}
	fmt.Printf("Total logical objects: %d\n", total)
	fmt.Printf("Sample Person:      %p (%s)\n", GlobalSamplePerson, GlobalSamplePerson.Name)
	fmt.Printf("Sample GameEntity:  %p (owner=%p)\n", GlobalSampleEntity, GlobalSampleEntity.Owner)
	fmt.Printf("Sample TreeNode:    %p (parent=%p)\n", GlobalSampleTree, GlobalSampleTree.Parent)
	fmt.Printf("Sample Generic Box: %p (value=%p next=%p)\n", GlobalSampleBox, GlobalSampleBox.Value, GlobalSampleBox.Next)
	fmt.Printf("Sample Map:         %p\n", store.SimpleMaps[321])
	fmt.Printf("Sample Channel:     %p\n", store.Channels[17])
	fmt.Printf("Sample Shape:       %T\n", GlobalSampleShape)
	fmt.Println("============================================================")
	fmt.Println(">>> READY FOR GCORE <<<")
	fmt.Println("Sleeping forever... (Ctrl+C to exit)")

	for {
		time.Sleep(time.Hour)
	}
}
