# .NET 10 managed heap fixture (Workstation GC)

This Linux x64 fixture covers managed objects/types, object graphs, boxed values, strings,
jagged and multidimensional arrays, LOH, POH, dependent handles, weak references, static,
thread-static, strong, pinned and finalizer roots, collectible ALC metadata, Task continuation/
awaiter relationships, AggregateException inner chains, and a separate native allocation.
The async fixture includes a pending `ValueTask<int>` backed by a custom
`IValueTaskSource<int>`/`ManualResetValueTaskSourceCore<int>`, including token, source status,
continuation and continuation-state evidence. A second pending operation is deliberately reset
while its old async state machine is retained, providing deterministic token/version mismatch
evidence without invoking target code from the analyzer.
It retains the same `CollectiblePayload` type from both the default and a named collectible ALC,
covering same-name/same-assembly type identity and ALC disambiguation.
Two independent static fields retain one shared payload through separate holders, providing a
deterministic multiple-shortest-GC-root-path assertion.
It also keeps one named thread holding a business lock while a second named thread blocks on it,
so the dump contains deterministic SyncBlock contention evidence.
The collection fixture retains a colliding ConcurrentDictionary node chain with removed and
updated entries, deliberately corrupted count/cycle dictionaries for partial semantics, HashSet
free-list entries, Queue wrap-around state and Stack top-to-bottom ordering. Its object and
primitive variants cover string, reference, null and primitive content without treating removed
nodes, free entries or unused backing-array slots as live business values. ConcurrentQueue coverage adds FIFO
traversal across multiple segments with removed slots, while ConcurrentStack adds LIFO node traversal,
primitive/object/null payloads and deliberately cyclic segment/node chains for strict partial semantics. The queue
fixture forces the analyzer to interpret freeze offsets and per-slot sequence numbers rather than treating segment
arrays as ordinary ring-buffer contents. It also covers LinkedList circular next/prev traversal and SortedList
parallel key/value arrays, including
removed/updated entries and deliberately inconsistent count/capacity state for strict partial output.
ConcurrentBag adds two owner-thread work-stealing queues, duplicate/string/reference/null/primitive values and
removed-value exclusion. Separate closed generic types corrupt the queue link, add/take count and current operation
to prove strict partial behavior without treating stale array slots as business content. Its `SnapshotOrder` follows
the runtime snapshot layout but deliberately makes no insertion, FIFO, LIFO or sorting promise.
BlockingCollection adds bounded and unbounded owners over exact ConcurrentQueue, ConcurrentStack and ConcurrentBag
backings. The fixture covers duplicate/string/null/primitive content, adding-open, completing, adding-completed,
completed-empty and disposed states, producer/consumer cancellation, semaphore count mismatch, active adders and a
custom `IProducerConsumerCollection<T>` backing that must remain unsupported/partial. The analyzer reports outer
capacity, completion and waiter state while preserving the validated backing's FIFO/LIFO/SnapshotOrder semantics.
Channels add multi-reader unbounded, single-reader unbounded, bounded and (on .NET 10+) rendezvous owners. The fixture
covers FIFO business content, duplicate/string/reference/null/primitive values, removed-slot exclusion, open,
draining and completed-empty states, blocked readers/writers, a corrupted bounded count and the runtime-specific
waiter-list layouts. Pending blocked-writer payload is deliberately not exported as buffered content; unsupported
priority-channel shapes remain explicit partial results instead of being guessed from similar private fields.
PriorityQueue covers element/priority pairs in the official unordered heap-array order, removed roots and a
corrupted size. ReadOnlyCollection covers exact List/array backings, while ReadOnlyDictionary covers exact
Dictionary/SortedList backings. Derived custom IList/IDictionary backings are retained as deterministic partial
negative cases so the analyzer cannot silently guess arbitrary interface implementations.
The immutable fixture covers boxed/default ImmutableArray, structurally shared ImmutableList and
ImmutableDictionary/ImmutableHashSet roots, hash collisions, ImmutableQueue front-to-back and ImmutableStack
top-to-bottom order. Primitive variants, removed/updated values, corrupted counts and a deliberate stack cycle
exercise strict shape/content partial semantics and node-level memoization.
ImmutableSortedDictionary and ImmutableSortedSet add AVL in-order `ComparerOrder` coverage with object/null/string/
primitive values, custom comparers, structurally shared sibling roots and removed/updated values. Distinct closed
generic types retain count-mismatch and self-cycle corruption cases without competing for the bounded
`object_samples` type slot.
The six mutable Immutable collection builders cover array capacity/count, list AVL order, hash dictionary/set
collision buckets and sorted dictionary/set comparer order. Their business cases retain string/reference/null/
primitive values after remove/update operations; separate closed generic types retain array/dictionary count
mismatches and a sorted-set self-cycle as strict partial cases.
FrozenDictionary/FrozenSet cover ordinal-string and default-hash concrete classes, empty instances, Int32
hash-code-backed storage, .NET 10 dense integral full/optional value shapes, object/null/string/primitive content,
removed/updated values and strict partial output for mismatched/null backings. The fixture intentionally retains the
runtime-selected concrete classes rather than assuming every frozen collection has one common array layout.
The deliberately corrupted ConcurrentDictionary count and cycle cases use distinct closed generic types, so both
remain independently observable under the bounded, type-diverse `object_samples` presentation policy.
The business-value fixture adds deterministic enum, DateTime/DateTimeOffset, TimeSpan, Guid, Decimal, Nullable,
DateOnly and TimeOnly fields. Unique List<DateTimeOffset>, Dictionary<Guid, Decimal>, enum-array and boxed-value
roots verify that field display, container summaries/search tokens and boxed object summaries all use the same
offline formatter without invoking target code.
StaticValueRoots and ThreadValueRoots retain deterministic primitive, string, enum, DateTime, Guid, Decimal,
Nullable and reference values. The named `maze-dotnet-fixture-root` thread owns the initialized thread-static
records; `UntouchedStaticValues` is materialized without running its explicit type initializer and must remain
uninitialized in the dump. Both static reference forms point to the same SharedChild for retained/reachability
downstream assertions.

Regenerate from the Maze repository root:

```bash
dotnet build testdata/dotnet/20260802-managed-heap-workstation/MazeDotnetFixture.csproj \
  -c Release --artifacts-path tmp/dotnet-fixture-artifacts

python3 cmd/maze-gen-coredump.py \
  -o testdata/dotnet/20260802-managed-heap-workstation \
  "MAZE_EXPECT_SERVER_GC=0 dotnet tmp/dotnet-fixture-artifacts/bin/MazeDotnetFixture/release/MazeDotnetFixture.dll"
```

Run:

```bash
python3 testdata/run_test.py dotnet/20260802-managed-heap-workstation
```
