using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Frozen;
using System.Collections.Immutable;
using System.Collections.ObjectModel;
using System.Reflection;
using System.Runtime;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Runtime.Loader;
using System.Threading.Channels;
using System.Threading.Tasks.Sources;

internal static class Program
{
    private const int NativeBytes = 123_456;
    private static readonly ManualResetEventSlim ThreadStop = new(false);
    private static readonly ManualResetEventSlim ThreadReady = new(false);
    private static readonly ManualResetEventSlim FinalizerStarted = new(false);
    private static readonly ManualResetEventSlim MonitorOwnerReady = new(false);
    private static readonly MonitorFixtureLock MonitorLock = new();
    private static GCHandle _strongHandle;
    private static GCHandle _pinnedHandle;

    public static void Main()
    {
        FixtureState state = FixtureState.Create();
        FixtureRoots.State = state;
        StaticValueRoots.Initialize(state.SharedChild);
        FixtureRoots.DependentTable.Add(state.DependentKey, new DependentValue(7001));
        InstallMultiRoots();

        _strongHandle = GCHandle.Alloc(state.HandleRoot, GCHandleType.Normal);
        _pinnedHandle = GCHandle.Alloc(state.PinnedHandleBytes, GCHandleType.Pinned);

        nint nativeAddress = Marshal.AllocHGlobal(NativeBytes);
        Marshal.WriteByte(nativeAddress, 0, 0x5a);
        Marshal.WriteByte(nativeAddress, NativeBytes - 1, 0xa5);
        state.NativeAllocation = new NativeAllocationHolder(nativeAddress, NativeBytes);

        state.AsyncTask = HoldAsyncState(state.AsyncPayload, state.AsyncGate.Task);
        state.AsyncValueTask = HoldValueTaskState(state.ValueTaskSource, state.AsyncPayload);
        state.StaleValueTask = HoldValueTaskState(state.ReusedValueTaskSource, state.AsyncPayload);
        state.ReusedValueTaskSource.Reset();
        state.CollectibleObject = CreateCollectiblePayload(out AssemblyLoadContext collectibleContext);
        state.CollectibleContext = collectibleContext;

        Thread thread = new(() =>
        {
            ThreadRoots.Current = new ThreadRootHolder(6001);
            ThreadValueRoots.Initialize(state.SharedChild);
            ThreadReady.Set();
            ThreadStop.Wait();
            GC.KeepAlive(ThreadRoots.Current);
        })
        {
            IsBackground = true,
            Name = "maze-dotnet-fixture-root",
        };
        thread.Start();
        ThreadReady.Wait();

        Thread monitorOwner = new(() =>
        {
            lock (MonitorLock)
            {
                MonitorOwnerReady.Set();
                ThreadStop.Wait();
            }
        })
        {
            IsBackground = true,
            Name = "maze-dotnet-monitor-owner",
        };
        monitorOwner.Start();
        MonitorOwnerReady.Wait();

        Thread monitorWaiter = new(() =>
        {
            lock (MonitorLock)
            {
            }
        })
        {
            IsBackground = true,
            Name = "maze-dotnet-monitor-waiter",
        };
        monitorWaiter.Start();
        if (!SpinWait.SpinUntil(
                () => (monitorWaiter.ThreadState & ThreadState.WaitSleepJoin) != 0,
                TimeSpan.FromSeconds(10)))
        {
            throw new InvalidOperationException($"Monitor waiter did not block: {monitorWaiter.ThreadState}");
        }

        state.WeakReference = CreateWeakReference();
        for (int attempt = 0; attempt < 4 && IsWeakTargetAlive(state.WeakReference); attempt++)
        {
            GC.Collect();
            GC.WaitForPendingFinalizers();
            GC.Collect();
        }
        if (IsWeakTargetAlive(state.WeakReference))
            throw new InvalidOperationException("WeakTarget unexpectedly remained alive");

        QueueFinalizerRoot();

        bool expectServer = Environment.GetEnvironmentVariable("MAZE_EXPECT_SERVER_GC") == "1";
        if (GCSettings.IsServerGC != expectServer)
            throw new InvalidOperationException($"Server GC mismatch: actual={GCSettings.IsServerGC}, expected={expectServer}");

        Console.WriteLine(
            $"FIXTURE server_gc={GCSettings.IsServerGC} processors={Environment.ProcessorCount} " +
            $"graph={state.GraphNodes.Length} loh={state.LargeObjects.Length} poh={state.PinnedObjects.Length}");
        GC.KeepAlive(typeof(UntouchedStaticValues));
        Console.WriteLine("READY FOR GCORE");
        Console.Out.Flush();

        ThreadStop.Wait();
        GC.KeepAlive(state);
    }

    private static async Task<int> HoldAsyncState(AsyncStatePayload payload, Task gate)
    {
        await gate.ConfigureAwait(false);
        return payload.Value;
    }

    private static async ValueTask<int> HoldValueTaskState(
        FixtureValueTaskSource source, AsyncStatePayload payload)
    {
        int value = await source.CreateValueTask();
        return value + payload.Value;
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static void InstallMultiRoots()
    {
        MultiRootPayload payload = new(11001);
        FixtureRoots.MultiRootLeft = new MultiRootHolder("left", payload);
        FixtureRoots.MultiRootRight = new MultiRootHolder("right", payload);
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static WeakReference<WeakTarget> CreateWeakReference()
    {
        return new WeakReference<WeakTarget>(new WeakTarget(8001));
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static bool IsWeakTargetAlive(WeakReference<WeakTarget> weakReference)
    {
        return weakReference.TryGetTarget(out _);
    }

    private static void QueueFinalizerRoot()
    {
        CreateBlockingFinalizer();
        GC.Collect();
        if (!FinalizerStarted.Wait(TimeSpan.FromSeconds(10)))
            throw new InvalidOperationException("Finalizer thread did not start");

        CreateFinalizerQueueRoot();
        GC.Collect();
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static void CreateBlockingFinalizer()
    {
        _ = new BlockingFinalizer();
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static void CreateFinalizerQueueRoot()
    {
        _ = new FinalizerQueueRoot();
    }

    internal static void WaitInFinalizer()
    {
        FinalizerStarted.Set();
        ThreadStop.Wait();
    }

    private static object CreateCollectiblePayload(out AssemblyLoadContext context)
    {
        context = new AssemblyLoadContext("maze-fixture-collectible", isCollectible: true);
        string assemblyPath = Environment.GetEnvironmentVariable("MAZE_FIXTURE_ASSEMBLY_PATH")
            ?? Assembly.GetExecutingAssembly().Location;
        if (string.IsNullOrWhiteSpace(assemblyPath))
            throw new InvalidOperationException(
                "Single-file fixture requires MAZE_FIXTURE_ASSEMBLY_PATH to an external fixture assembly");
        using FileStream stream = File.OpenRead(assemblyPath);
        Assembly assembly = context.LoadFromStream(stream);
        Type payloadType = assembly.GetType(nameof(CollectiblePayload), throwOnError: true)!;
        return Activator.CreateInstance(payloadType, 10001)!;
    }
}

internal static class FixtureRoots
{
    public static FixtureState? State;
    public static MultiRootHolder? MultiRootLeft;
    public static MultiRootHolder? MultiRootRight;
    public static readonly ConditionalWeakTable<DependentKey, DependentValue> DependentTable = new();
}

internal static class ThreadRoots
{
    [ThreadStatic]
    public static ThreadRootHolder? Current;
}

internal static class StaticValueRoots
{
    public static int Count;
    public static string? Label;
    public static FixtureLifecycle Lifecycle;
    public static DateTime OccurredAt;
    public static Guid CorrelationId;
    public static decimal Amount;
    public static int? OptionalCount;
    public static SharedChild? Reference;
    public static object? MissingReference;

    public static void Initialize(SharedChild reference)
    {
        Count = 314159;
        Label = "maze-static-business-value";
        Lifecycle = FixtureLifecycle.Ready;
        OccurredAt = new DateTime(2026, 8, 3, 12, 34, 56, DateTimeKind.Utc).AddTicks(7890);
        CorrelationId = Guid.Parse("13572468-2468-1357-aaaa-bbbbccccdddd");
        Amount = 987654321.012300m;
        OptionalCount = 2718;
        Reference = reference;
        MissingReference = null;
    }
}

internal static class ThreadValueRoots
{
    [ThreadStatic] public static int Count;
    [ThreadStatic] public static string? Label;
    [ThreadStatic] public static DateTime OccurredAt;
    [ThreadStatic] public static Guid CorrelationId;
    [ThreadStatic] public static SharedChild? Reference;
    [ThreadStatic] public static object? MissingReference;

    public static void Initialize(SharedChild reference)
    {
        Count = 161803;
        Label = "maze-thread-static-business-value";
        OccurredAt = new DateTime(2026, 8, 3, 23, 45, 1, DateTimeKind.Utc).AddTicks(2345);
        CorrelationId = Guid.Parse("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee");
        Reference = reference;
        MissingReference = null;
    }
}

internal static class UntouchedStaticValues
{
    static UntouchedStaticValues()
    {
        Count = 123;
        Label = "must-not-be-reported-as-initialized";
    }

    public static int Count;
    public static string? Label;
}

internal sealed class FixtureState
{
    public required GraphNode[] GraphNodes { get; init; }
    public required SharedChild SharedChild { get; init; }
    public required object[] BoxedValues { get; init; }
    public required StringHolder[] Strings { get; init; }
    public required ArrayHolder Arrays { get; init; }
    public required LargeObjectHolder[] LargeObjects { get; init; }
    public required PinnedObjectHolder[] PinnedObjects { get; init; }
    public required GenericBox<int>[] GenericBoxes { get; init; }
    public required NestedContainer.NestedNode[] NestedNodes { get; init; }
    public required FinalizableObject[] Finalizables { get; init; }
    public required DependentKey DependentKey { get; init; }
    public required HandleRootHolder HandleRoot { get; init; }
    public required byte[] PinnedHandleBytes { get; init; }
    public required FixtureException Exception { get; init; }
    public required AggregateException AggregateException { get; init; }
    public required AsyncStatePayload AsyncPayload { get; init; }
    public required TaskCompletionSource<bool> AsyncGate { get; init; }
    public required FixtureValueTaskSource ValueTaskSource { get; init; }
    public required FixtureValueTaskSource SucceededValueTaskSource { get; init; }
    public required FixtureValueTaskSource FaultedValueTaskSource { get; init; }
    public required FixtureValueTaskSource CanceledValueTaskSource { get; init; }
    public required FixtureValueTaskSource ReusedValueTaskSource { get; init; }
    public Task<int>? AsyncTask { get; set; }
    public ValueTask<int> AsyncValueTask { get; set; }
    public ValueTask<int> StaleValueTask { get; set; }
    public WeakReference<WeakTarget>? WeakReference { get; set; }
    public NativeAllocationHolder? NativeAllocation { get; set; }
    public AssemblyLoadContext? CollectibleContext { get; set; }
    public object? CollectibleObject { get; set; }
    public required CollectiblePayload DefaultCollectibleObject { get; init; }
    public required CollectionFixtures Collections { get; init; }
    public required BusinessValueFixtures BusinessValues { get; init; }

    public static FixtureState Create()
    {
        SharedChild shared = new(42);
        GraphNode[] graph = Enumerable.Range(0, 64).Select(index => new GraphNode(index)).ToArray();
        for (int index = 0; index < graph.Length; index++)
        {
            graph[index].Next = graph[(index + 1) % graph.Length];
            graph[index].Shared = shared;
            graph[index].Optional = index % 2 == 0 ? null : graph[0];
        }

        CollectionFixtures collections = CollectionFixtures.Create(graph);

        return new FixtureState
        {
            GraphNodes = graph,
            SharedChild = shared,
            BoxedValues = Enumerable.Range(0, 32).Select(index => (object)new FixtureValue(index, index + 0.5)).ToArray(),
            Strings = Enumerable.Range(0, 24).Select(index => new StringHolder($"maze-string-{index:D2}")).ToArray(),
            Arrays = new ArrayHolder(graph),
            LargeObjects = Enumerable.Range(0, 3).Select(index => new LargeObjectHolder(index)).ToArray(),
            PinnedObjects = Enumerable.Range(0, 4).Select(index => new PinnedObjectHolder(index)).ToArray(),
            GenericBoxes = Enumerable.Range(0, 11).Select(index => new GenericBox<int>(index)).ToArray(),
            NestedNodes = Enumerable.Range(0, 7).Select(index => new NestedContainer.NestedNode(index)).ToArray(),
            Finalizables = Enumerable.Range(0, 13).Select(index => new FinalizableObject(index)).ToArray(),
            DependentKey = new DependentKey(7000),
            HandleRoot = new HandleRootHolder(5001),
            PinnedHandleBytes = new byte[8192],
            Exception = new FixtureException("fixture exception", new InvalidOperationException("fixture inner")),
            AggregateException = new AggregateException(
                "fixture aggregate",
                new InvalidOperationException("aggregate-one"),
                new ArgumentException("aggregate-two")),
            AsyncPayload = new AsyncStatePayload(9001),
            AsyncGate = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously),
            ValueTaskSource = new FixtureValueTaskSource(),
            SucceededValueTaskSource = FixtureValueTaskSource.Succeeded(12001),
            FaultedValueTaskSource = FixtureValueTaskSource.Faulted(
                new InvalidOperationException("fixture value task fault")),
            CanceledValueTaskSource = FixtureValueTaskSource.Faulted(
                new OperationCanceledException("fixture value task canceled")),
            ReusedValueTaskSource = new FixtureValueTaskSource(),
            DefaultCollectibleObject = new CollectiblePayload(10000),
            Collections = collections,
            BusinessValues = BusinessValueFixtures.Create(),
        };
    }
}

internal sealed class GraphNode(int id)
{
    public int Id { get; } = id;
    public GraphNode? Next { get; set; }
    public SharedChild? Shared { get; set; }
    public GraphNode? Optional { get; set; }
}

internal sealed record SharedChild(int Value);
internal readonly record struct FixtureValue(int Id, double Value);

internal enum FixtureLifecycle : short
{
    Unknown = 0,
    Ready = 7,
    Failed = -1,
}

[Flags]
internal enum FixturePermissions : uint
{
    None = 0,
    Read = 1,
    Write = 2,
    Execute = 4,
    ReadWrite = Read | Write,
}

internal sealed class BusinessValueFixtures
{
    public required FixtureLifecycle Lifecycle { get; init; }
    public required FixtureLifecycle UnmappedLifecycle { get; init; }
    public required FixturePermissions Permissions { get; init; }
    public required DateTime UtcWhen { get; init; }
    public required DateTime UnspecifiedWhen { get; init; }
    public required DateTimeOffset OffsetWhen { get; init; }
    public required TimeSpan Duration { get; init; }
    public required Guid CorrelationId { get; init; }
    public required decimal Amount { get; init; }
    public required int? PresentCount { get; init; }
    public required int? MissingCount { get; init; }
    public required DateTime? OptionalWhen { get; init; }
    public required DateOnly BusinessDate { get; init; }
    public required TimeOnly BusinessTime { get; init; }
    public required List<DateTimeOffset> Timeline { get; init; }
    public required Dictionary<Guid, decimal> AmountsById { get; init; }
    public required FixtureLifecycle[] LifecycleHistory { get; init; }
    public required object[] BoxedBusinessValues { get; init; }

    public static BusinessValueFixtures Create()
    {
        DateTime utc = new DateTime(2024, 5, 6, 7, 8, 9, 123, DateTimeKind.Utc).AddTicks(4567);
        DateTime unspecified = new DateTime(2030, 12, 31, 23, 59, 58, 987,
            DateTimeKind.Unspecified).AddTicks(6543);
        DateTimeOffset offset = new DateTimeOffset(2025, 6, 7, 8, 9, 10, 321,
            TimeSpan.FromMinutes(330)).AddTicks(7654);
        TimeSpan duration = new TimeSpan(2, 3, 4, 5, 678).Add(TimeSpan.FromTicks(9012));
        Guid correlationId = Guid.Parse("01234567-89ab-cdef-0123-456789abcdef");
        decimal amount = -1234567890.012300m;
        DateTimeOffset earlier = new DateTimeOffset(2020, 1, 2, 3, 4, 5, 600,
            TimeSpan.FromHours(-4)).AddTicks(7000);

        return new BusinessValueFixtures
        {
            Lifecycle = FixtureLifecycle.Ready,
            UnmappedLifecycle = (FixtureLifecycle)123,
            Permissions = FixturePermissions.ReadWrite,
            UtcWhen = utc,
            UnspecifiedWhen = unspecified,
            OffsetWhen = offset,
            Duration = duration,
            CorrelationId = correlationId,
            Amount = amount,
            PresentCount = 4242,
            MissingCount = null,
            OptionalWhen = utc,
            BusinessDate = new DateOnly(2024, 5, 6),
            BusinessTime = new TimeOnly(7, 8, 9, 123).Add(TimeSpan.FromTicks(4567)),
            Timeline = [earlier, offset],
            AmountsById = new Dictionary<Guid, decimal>
            {
                [correlationId] = amount,
                [Guid.Parse("fedcba98-7654-3210-fedc-ba9876543210")] = 42.500m,
            },
            LifecycleHistory = [FixtureLifecycle.Unknown, FixtureLifecycle.Ready, FixtureLifecycle.Failed],
            BoxedBusinessValues =
            [
                correlationId,
                amount,
                utc,
                offset,
                duration,
                FixtureLifecycle.Ready,
                new DateOnly(2024, 5, 6),
                new TimeOnly(7, 8, 9, 123).Add(TimeSpan.FromTicks(4567)),
            ],
        };
    }
}

internal sealed record StringHolder(string Value);
internal sealed record GenericBox<T>(T Value);
internal sealed record HandleRootHolder(int Value);
internal sealed record ThreadRootHolder(int Value);
internal sealed record DependentKey(int Value);
internal sealed record DependentValue(int Value);
internal sealed record AsyncStatePayload(int Value);
internal sealed record CustomBlockingValue(string Value);

internal sealed class FixtureList<T> : List<T> { }

internal sealed class FixtureDictionary<TKey, TValue> : Dictionary<TKey, TValue> where TKey : notnull { }

internal sealed class FixtureProducerConsumerCollection<T>(IEnumerable<T> values) :
    IProducerConsumerCollection<T>
{
    private readonly ConcurrentQueue<T> _values = new(values);

    public int Count => _values.Count;
    public bool IsSynchronized => false;
    public object SyncRoot => throw new NotSupportedException();

    public bool TryAdd(T item)
    {
        _values.Enqueue(item);
        return true;
    }

    public bool TryTake(out T item) => _values.TryDequeue(out item!);
    public T[] ToArray() => _values.ToArray();
    public void CopyTo(T[] array, int index) => _values.CopyTo(array, index);
    public void CopyTo(Array array, int index) => ((ICollection)_values).CopyTo(array, index);
    public IEnumerator<T> GetEnumerator() => _values.GetEnumerator();
    IEnumerator IEnumerable.GetEnumerator() => GetEnumerator();
}

internal sealed class CollectionFixtures
{
    public required ConcurrentDictionary<string, object?> BusinessConcurrentDictionary { get; init; }
    public required ConcurrentDictionary<int, int> PrimitiveConcurrentDictionary { get; init; }
    public required ConcurrentDictionary<string, string> CountMismatchConcurrentDictionary { get; init; }
    // Keep the corruption cases on distinct closed generic types. object_samples
    // intentionally reserves only one entry per CLR type before applying its
    // global cap, so sharing the exact type would make one real-dump assertion
    // depend on an unrelated presentation score.
    public required ConcurrentDictionary<int, string> CycleConcurrentDictionary { get; init; }
    public required ConcurrentQueue<object?> BusinessConcurrentQueue { get; init; }
    public required ConcurrentQueue<int> PrimitiveConcurrentQueue { get; init; }
    public required ConcurrentQueue<long> CycleConcurrentQueue { get; init; }
    public required ConcurrentStack<object?> BusinessConcurrentStack { get; init; }
    public required ConcurrentStack<int> PrimitiveConcurrentStack { get; init; }
    public required ConcurrentStack<long> CycleConcurrentStack { get; init; }
    public required ConcurrentBag<object?> BusinessConcurrentBag { get; init; }
    public required ConcurrentBag<int> PrimitiveConcurrentBag { get; init; }
    public required ConcurrentBag<long> CycleConcurrentBag { get; init; }
    public required ConcurrentBag<short> CountMismatchConcurrentBag { get; init; }
    public required ConcurrentBag<byte> CurrentOperationConcurrentBag { get; init; }
    public required BlockingCollection<string?> BusinessBlockingCollection { get; init; }
    public required BlockingCollection<uint> CompletedBlockingCollection { get; init; }
    public required BlockingCollection<ulong> CompletedEmptyBlockingCollection { get; init; }
    public required BlockingCollection<CustomBlockingValue> CustomBlockingCollection { get; init; }
    public required BlockingCollection<short> CountMismatchBlockingCollection { get; init; }
    public required BlockingCollection<byte> CompletingBlockingCollection { get; init; }
    public required BlockingCollection<ushort> DisposedBlockingCollection { get; init; }
    public required Channel<string?> BusinessUnboundedChannel { get; init; }
    public required Channel<int> SingleReaderUnboundedChannel { get; init; }
    public required Channel<object?> BusinessBoundedChannel { get; init; }
    public required Channel<uint> DrainingBoundedChannel { get; init; }
    public required Channel<ulong> CompletedEmptyUnboundedChannel { get; init; }
    public required Channel<short> CountMismatchBoundedChannel { get; init; }
    public required Channel<byte> BlockedWriterChannel { get; init; }
    public required Task BlockedChannelWrite { get; init; }
    public required Channel<ushort> BlockedReaderChannel { get; init; }
    public required Task<ushort> BlockedChannelRead { get; init; }
    public required Channel<long>? RendezvousChannel { get; init; }
    public required HashSet<object?> BusinessSet { get; init; }
    public required HashSet<int> PrimitiveSet { get; init; }
    public required Queue<object?> WrappedQueue { get; init; }
    public required Queue<int> PrimitiveQueue { get; init; }
    public required Stack<object?> BusinessStack { get; init; }
    public required Stack<int> PrimitiveStack { get; init; }
    public required LinkedList<object?> BusinessLinkedList { get; init; }
    public required LinkedList<int> PrimitiveLinkedList { get; init; }
    public required LinkedList<string> CountMismatchLinkedList { get; init; }
    public required SortedList<string, object?> BusinessSortedList { get; init; }
    public required SortedList<int, int> PrimitiveSortedList { get; init; }
    public required SortedList<string, string> CountMismatchSortedList { get; init; }
    public required PriorityQueue<object?, int> BusinessPriorityQueue { get; init; }
    public required PriorityQueue<int, int> PrimitivePriorityQueue { get; init; }
    public required PriorityQueue<string, int> CountMismatchPriorityQueue { get; init; }
    public required ReadOnlyCollection<object?> BusinessReadOnlyCollection { get; init; }
    public required ReadOnlyCollection<int> ArrayReadOnlyCollection { get; init; }
    public required ReadOnlyCollection<string> CustomReadOnlyCollection { get; init; }
    public required ReadOnlyDictionary<string, object?> BusinessReadOnlyDictionary { get; init; }
    public required ReadOnlyDictionary<int, int> SortedReadOnlyDictionary { get; init; }
    public required ReadOnlyDictionary<string, string> CustomReadOnlyDictionary { get; init; }
    public required object BoxedImmutableArray { get; init; }
    public required object DefaultImmutableArray { get; init; }
    public required ImmutableList<object?> BusinessImmutableList { get; init; }
    public required ImmutableList<object?> SiblingImmutableList { get; init; }
    public required ImmutableList<int> PrimitiveImmutableList { get; init; }
    public required ImmutableList<string> CountMismatchImmutableList { get; init; }
    public required ImmutableDictionary<string, object?> BusinessImmutableDictionary { get; init; }
    public required ImmutableDictionary<string, object?> SiblingImmutableDictionary { get; init; }
    public required ImmutableDictionary<int, int> PrimitiveImmutableDictionary { get; init; }
    public required ImmutableDictionary<string, string> CountMismatchImmutableDictionary { get; init; }
    public required ImmutableSortedDictionary<string, object?> BusinessImmutableSortedDictionary { get; init; }
    public required ImmutableSortedDictionary<string, object?> SiblingImmutableSortedDictionary { get; init; }
    public required ImmutableSortedDictionary<int, int> PrimitiveImmutableSortedDictionary { get; init; }
    public required ImmutableSortedDictionary<string, string> CountMismatchImmutableSortedDictionary { get; init; }
    public required ImmutableSortedDictionary<long, string> CycleImmutableSortedDictionary { get; init; }
    public required ImmutableHashSet<object?> BusinessImmutableSet { get; init; }
    public required ImmutableHashSet<object?> SiblingImmutableSet { get; init; }
    public required ImmutableHashSet<int> PrimitiveImmutableSet { get; init; }
    public required ImmutableHashSet<string> CountMismatchImmutableSet { get; init; }
    public required ImmutableSortedSet<object?> BusinessImmutableSortedSet { get; init; }
    public required ImmutableSortedSet<object?> SiblingImmutableSortedSet { get; init; }
    public required ImmutableSortedSet<int> PrimitiveImmutableSortedSet { get; init; }
    public required ImmutableSortedSet<string> CountMismatchImmutableSortedSet { get; init; }
    public required ImmutableSortedSet<long> CycleImmutableSortedSet { get; init; }
    public required ImmutableQueue<object?> BusinessImmutableQueue { get; init; }
    public required ImmutableQueue<int> PrimitiveImmutableQueue { get; init; }
    public required ImmutableStack<object?> BusinessImmutableStack { get; init; }
    public required ImmutableStack<int> PrimitiveImmutableStack { get; init; }
    public required ImmutableStack<string> CycleImmutableStack { get; init; }
    public required ImmutableArray<object?>.Builder BusinessImmutableArrayBuilder { get; init; }
    public required ImmutableArray<string>.Builder CountMismatchImmutableArrayBuilder { get; init; }
    public required ImmutableList<object?>.Builder BusinessImmutableListBuilder { get; init; }
    public required ImmutableDictionary<string, object?>.Builder BusinessImmutableDictionaryBuilder { get; init; }
    public required ImmutableDictionary<long, string>.Builder CountMismatchImmutableDictionaryBuilder { get; init; }
    public required ImmutableHashSet<object?>.Builder BusinessImmutableSetBuilder { get; init; }
    public required ImmutableSortedDictionary<string, object?>.Builder BusinessImmutableSortedDictionaryBuilder { get; init; }
    public required ImmutableSortedSet<object?>.Builder BusinessImmutableSortedSetBuilder { get; init; }
    public required ImmutableSortedSet<long>.Builder CycleImmutableSortedSetBuilder { get; init; }
    public required FrozenDictionary<string, object?> BusinessFrozenDictionary { get; init; }
    public required FrozenDictionary<int, int> Int32FrozenDictionary { get; init; }
    public required FrozenDictionary<byte, string> DenseFullFrozenDictionary { get; init; }
    public required FrozenDictionary<short, string> DenseOptionalFrozenDictionary { get; init; }
    public required FrozenDictionary<Guid, string> CountMismatchFrozenDictionary { get; init; }
    public required FrozenDictionary<string, string> EmptyFrozenDictionary { get; init; }
    public required FrozenSet<object?> BusinessFrozenSet { get; init; }
    public required FrozenSet<string> OrdinalFrozenSet { get; init; }
    public required FrozenSet<int> Int32FrozenSet { get; init; }
    public required FrozenSet<long> CountMismatchFrozenSet { get; init; }
    public required FrozenSet<string> EmptyFrozenSet { get; init; }

    public static CollectionFixtures Create(GraphNode[] graph)
    {
        ConcurrentDictionary<string, object?> businessConcurrentDictionary = new(
            concurrencyLevel: 4, capacity: 7, comparer: ConstantHashStringComparer.Instance);
        businessConcurrentDictionary["maze-concurrent-string"] = "maze-concurrent-value";
        businessConcurrentDictionary["maze-concurrent-reference"] = graph[6];
        businessConcurrentDictionary["maze-concurrent-null"] = null;
        businessConcurrentDictionary["maze-concurrent-removed"] = "maze-concurrent-removed-value";
        businessConcurrentDictionary["maze-concurrent-updated"] = "maze-concurrent-old-value";
        businessConcurrentDictionary["maze-concurrent-updated"] = "maze-concurrent-new-value";
        if (!businessConcurrentDictionary.TryRemove("maze-concurrent-removed", out _))
            throw new InvalidOperationException("ConcurrentDictionary removal fixture was not installed");

        ConcurrentDictionary<int, int> primitiveConcurrentDictionary = new();
        primitiveConcurrentDictionary[101] = 1001;
        primitiveConcurrentDictionary[202] = 2002;
        primitiveConcurrentDictionary[303] = 3003;
        if (!primitiveConcurrentDictionary.TryRemove(202, out _))
            throw new InvalidOperationException("Primitive ConcurrentDictionary removal fixture was not installed");

        ConcurrentDictionary<string, string> countMismatchConcurrentDictionary = new()
        {
            ["maze-concurrent-count-partial-0"] = "count-partial-value-0",
            ["maze-concurrent-count-partial-1"] = "count-partial-value-1",
        };
        CorruptConcurrentDictionaryCount(countMismatchConcurrentDictionary);

        ConcurrentDictionary<int, string> cycleConcurrentDictionary = new()
        {
            [1701] = "maze-concurrent-cycle-partial",
        };
        CorruptConcurrentDictionaryCycle(cycleConcurrentDictionary);

        ConcurrentQueue<object?> businessConcurrentQueue = new();
        for (int index = 0; index < 30; index++)
            businessConcurrentQueue.Enqueue($"maze-concurrent-queue-discard-{index:D2}");
        businessConcurrentQueue.Enqueue("maze-concurrent-queue-removed");
        businessConcurrentQueue.Enqueue("maze-concurrent-queue-first");
        businessConcurrentQueue.Enqueue(graph[38]);
        businessConcurrentQueue.Enqueue(null);
        businessConcurrentQueue.Enqueue("maze-concurrent-queue-last");
        for (int index = 0; index < 31; index++)
        {
            if (!businessConcurrentQueue.TryDequeue(out _))
                throw new InvalidOperationException("ConcurrentQueue removal fixture was not installed");
        }

        ConcurrentQueue<int> primitiveConcurrentQueue = new();
        primitiveConcurrentQueue.Enqueue(111);
        primitiveConcurrentQueue.Enqueue(222);
        primitiveConcurrentQueue.Enqueue(333);
        if (!primitiveConcurrentQueue.TryDequeue(out int concurrentQueueRemoved) || concurrentQueueRemoved != 111)
            throw new InvalidOperationException("Primitive ConcurrentQueue removal fixture was not installed");
        primitiveConcurrentQueue.Enqueue(444);

        ConcurrentQueue<long> cycleConcurrentQueue = new();
        cycleConcurrentQueue.Enqueue(1701L);
        CorruptConcurrentQueueCycle(cycleConcurrentQueue);

        ConcurrentStack<object?> businessConcurrentStack = new();
        businessConcurrentStack.Push("maze-concurrent-stack-bottom");
        businessConcurrentStack.Push(graph[39]);
        businessConcurrentStack.Push(null);
        businessConcurrentStack.Push("maze-concurrent-stack-removed");
        if (!businessConcurrentStack.TryPop(out object? concurrentStackRemoved) ||
            !string.Equals(concurrentStackRemoved as string, "maze-concurrent-stack-removed",
                StringComparison.Ordinal))
            throw new InvalidOperationException("ConcurrentStack removal fixture was not installed");
        businessConcurrentStack.Push("maze-concurrent-stack-top");

        ConcurrentStack<int> primitiveConcurrentStack = new();
        primitiveConcurrentStack.Push(111);
        primitiveConcurrentStack.Push(222);
        primitiveConcurrentStack.Push(333);

        ConcurrentStack<long> cycleConcurrentStack = new();
        cycleConcurrentStack.Push(1702L);
        CorruptConcurrentStackCycle(cycleConcurrentStack);

        ConcurrentBag<object?> businessConcurrentBag = new();
        Thread firstBagOwner = new(() =>
        {
            businessConcurrentBag.Add("maze-concurrent-bag-first");
            businessConcurrentBag.Add(graph[40]);
            businessConcurrentBag.Add("maze-concurrent-bag-removed-first");
            if (!businessConcurrentBag.TryTake(out object? removed) ||
                !string.Equals(removed as string, "maze-concurrent-bag-removed-first", StringComparison.Ordinal))
                throw new InvalidOperationException("First ConcurrentBag removal fixture was not installed");
        });
        firstBagOwner.Start();
        firstBagOwner.Join();
        Thread secondBagOwner = new(() =>
        {
            businessConcurrentBag.Add(null);
            businessConcurrentBag.Add("maze-concurrent-bag-duplicate");
            businessConcurrentBag.Add("maze-concurrent-bag-duplicate");
            businessConcurrentBag.Add("maze-concurrent-bag-last");
            businessConcurrentBag.Add("maze-concurrent-bag-removed-second");
            if (!businessConcurrentBag.TryTake(out object? removed) ||
                !string.Equals(removed as string, "maze-concurrent-bag-removed-second", StringComparison.Ordinal))
                throw new InvalidOperationException("Second ConcurrentBag removal fixture was not installed");
        });
        secondBagOwner.Start();
        secondBagOwner.Join();

        ConcurrentBag<int> primitiveConcurrentBag = new();
        primitiveConcurrentBag.Add(111);
        primitiveConcurrentBag.Add(222);
        primitiveConcurrentBag.Add(333);
        if (!primitiveConcurrentBag.TryTake(out int removedBagValue) || removedBagValue != 333)
            throw new InvalidOperationException("Primitive ConcurrentBag removal fixture was not installed");
        primitiveConcurrentBag.Add(444);

        ConcurrentBag<long> cycleConcurrentBag = new([1703L]);
        CorruptConcurrentBagCycle(cycleConcurrentBag);

        ConcurrentBag<short> countMismatchConcurrentBag = new([17, 18]);
        CorruptConcurrentBagCount(countMismatchConcurrentBag);

        ConcurrentBag<byte> currentOperationConcurrentBag = new([23]);
        CorruptConcurrentBagCurrentOperation(currentOperationConcurrentBag);

        BlockingCollection<string?> businessBlockingCollection = new(new ConcurrentQueue<string?>(), 8);
        businessBlockingCollection.Add("maze-blocking-removed");
        businessBlockingCollection.Add("maze-blocking-first");
        businessBlockingCollection.Add("maze-blocking-middle");
        businessBlockingCollection.Add(null);
        businessBlockingCollection.Add("maze-blocking-duplicate");
        businessBlockingCollection.Add("maze-blocking-duplicate");
        businessBlockingCollection.Add("maze-blocking-last");
        if (!string.Equals(businessBlockingCollection.Take() as string, "maze-blocking-removed",
                StringComparison.Ordinal))
            throw new InvalidOperationException("BlockingCollection removal fixture was not installed");

        BlockingCollection<uint> completedBlockingCollection = new(new ConcurrentStack<uint>());
        completedBlockingCollection.Add(111);
        completedBlockingCollection.Add(222);
        completedBlockingCollection.Add(333);
        if (completedBlockingCollection.Take() != 333)
            throw new InvalidOperationException("Completed BlockingCollection removal fixture was not installed");
        completedBlockingCollection.Add(444);
        completedBlockingCollection.CompleteAdding();

        BlockingCollection<ulong> completedEmptyBlockingCollection = new(new ConcurrentBag<ulong>());
        completedEmptyBlockingCollection.Add(1704UL);
        if (completedEmptyBlockingCollection.Take() != 1704UL)
            throw new InvalidOperationException("Empty BlockingCollection removal fixture was not installed");
        completedEmptyBlockingCollection.CompleteAdding();

        FixtureProducerConsumerCollection<CustomBlockingValue> customBlockingBacking =
            new([new CustomBlockingValue("maze-blocking-custom-partial")]);
        BlockingCollection<CustomBlockingValue> customBlockingCollection = new(customBlockingBacking);

        BlockingCollection<short> countMismatchBlockingCollection = new(5);
        countMismatchBlockingCollection.Add(17);
        countMismatchBlockingCollection.Add(18);
        CorruptBlockingCollectionOccupiedCount(countMismatchBlockingCollection);

        BlockingCollection<byte> completingBlockingCollection = new(new ConcurrentStack<byte>());
        completingBlockingCollection.Add(23);
        SetRequiredField(completingBlockingCollection, "_currentAdders", int.MinValue | 1);

        BlockingCollection<ushort> disposedBlockingCollection = new(4);
        disposedBlockingCollection.Add(1111);
        disposedBlockingCollection.Add(2222);
        disposedBlockingCollection.Dispose();

        Channel<string?> businessUnboundedChannel = Channel.CreateUnbounded<string?>(
            new UnboundedChannelOptions
            {
                SingleReader = false,
                SingleWriter = true,
                AllowSynchronousContinuations = true,
            });
        businessUnboundedChannel.Writer.TryWrite("maze-channel-removed");
        businessUnboundedChannel.Writer.TryWrite("maze-channel-first");
        businessUnboundedChannel.Writer.TryWrite("maze-channel-middle");
        businessUnboundedChannel.Writer.TryWrite(null);
        businessUnboundedChannel.Writer.TryWrite("maze-channel-duplicate");
        businessUnboundedChannel.Writer.TryWrite("maze-channel-duplicate");
        businessUnboundedChannel.Writer.TryWrite("maze-channel-last");
        if (!businessUnboundedChannel.Reader.TryRead(out string? removedChannelValue) ||
            !string.Equals(removedChannelValue, "maze-channel-removed", StringComparison.Ordinal))
            throw new InvalidOperationException("Unbounded Channel removal fixture was not installed");

        Channel<int> singleReaderUnboundedChannel = Channel.CreateUnbounded<int>(
            new UnboundedChannelOptions
            {
                SingleReader = true,
                SingleWriter = true,
                AllowSynchronousContinuations = false,
            });
        singleReaderUnboundedChannel.Writer.TryWrite(111);
        singleReaderUnboundedChannel.Writer.TryWrite(222);
        singleReaderUnboundedChannel.Writer.TryWrite(333);
        if (!singleReaderUnboundedChannel.Reader.TryRead(out int removedSingleReaderValue) ||
            removedSingleReaderValue != 111)
            throw new InvalidOperationException("Single-reader Channel removal fixture was not installed");
        singleReaderUnboundedChannel.Writer.TryWrite(444);

        Channel<object?> businessBoundedChannel = Channel.CreateBounded<object?>(
            new BoundedChannelOptions(8)
            {
                FullMode = BoundedChannelFullMode.Wait,
                SingleReader = false,
                SingleWriter = false,
                AllowSynchronousContinuations = false,
            });
        businessBoundedChannel.Writer.TryWrite("maze-bounded-channel-removed");
        businessBoundedChannel.Writer.TryWrite("maze-bounded-channel-first");
        businessBoundedChannel.Writer.TryWrite(graph[42]);
        businessBoundedChannel.Writer.TryWrite(null);
        businessBoundedChannel.Writer.TryWrite("maze-bounded-channel-duplicate");
        businessBoundedChannel.Writer.TryWrite("maze-bounded-channel-duplicate");
        businessBoundedChannel.Writer.TryWrite("maze-bounded-channel-last");
        if (!businessBoundedChannel.Reader.TryRead(out object? removedBoundedValue) ||
            !string.Equals(removedBoundedValue as string, "maze-bounded-channel-removed", StringComparison.Ordinal))
            throw new InvalidOperationException("Bounded Channel removal fixture was not installed");

        Channel<uint> drainingBoundedChannel = Channel.CreateBounded<uint>(3);
        drainingBoundedChannel.Writer.TryWrite(1111);
        drainingBoundedChannel.Writer.TryWrite(2222);
        if (!drainingBoundedChannel.Writer.TryComplete())
            throw new InvalidOperationException("Draining Channel completion fixture was not installed");

        Channel<ulong> completedEmptyUnboundedChannel = Channel.CreateUnbounded<ulong>();
        completedEmptyUnboundedChannel.Writer.TryWrite(1705UL);
        if (!completedEmptyUnboundedChannel.Reader.TryRead(out ulong completedRemoved) || completedRemoved != 1705UL ||
            !completedEmptyUnboundedChannel.Writer.TryComplete())
            throw new InvalidOperationException("Completed-empty Channel fixture was not installed");

        Channel<short> countMismatchBoundedChannel = Channel.CreateBounded<short>(4);
        countMismatchBoundedChannel.Writer.TryWrite(17);
        countMismatchBoundedChannel.Writer.TryWrite(18);
        CorruptBoundedChannelCount(countMismatchBoundedChannel);

        Channel<byte> blockedWriterChannel = Channel.CreateBounded<byte>(1);
        blockedWriterChannel.Writer.TryWrite(23);
        Task blockedChannelWrite = Environment.Version.Major >= 9
            ? blockedWriterChannel.Writer.WriteAsync(42).AsTask()
            : Task.CompletedTask;
        if (Environment.Version.Major >= 9 && blockedChannelWrite.IsCompleted)
            throw new InvalidOperationException("Blocked Channel writer fixture did not block");

        Channel<ushort> blockedReaderChannel = Channel.CreateUnbounded<ushort>();
        Task<ushort> blockedChannelRead = Environment.Version.Major >= 9
            ? blockedReaderChannel.Reader.ReadAsync().AsTask()
            : Task.FromResult((ushort)0);
        if (Environment.Version.Major >= 9 && blockedChannelRead.IsCompleted)
            throw new InvalidOperationException("Blocked Channel reader fixture did not block");

        Channel<long>? rendezvousChannel = Environment.Version.Major >= 10
            ? Channel.CreateBounded<long>(
                new BoundedChannelOptions(0)
                {
                    FullMode = BoundedChannelFullMode.Wait,
                    SingleReader = false,
                    SingleWriter = false,
                    AllowSynchronousContinuations = false,
                })
            : null;

        HashSet<object?> businessSet =
        [
            "maze-set-keep-string",
            graph[7],
            null,
            "maze-set-deleted-slot",
        ];
        if (!businessSet.Remove("maze-set-deleted-slot"))
            throw new InvalidOperationException("HashSet removal fixture was not installed");

        HashSet<int> primitiveSet = [101, 202, 303];
        if (!primitiveSet.Remove(202))
            throw new InvalidOperationException("Primitive HashSet removal fixture was not installed");

        Queue<object?> wrappedQueue = new(8);
        for (int index = 0; index < 5; index++)
            wrappedQueue.Enqueue($"maze-queue-discard-{index}");
        wrappedQueue.Enqueue("maze-queue-front");
        wrappedQueue.Enqueue(graph[8]);
        wrappedQueue.Enqueue(null);
        for (int index = 0; index < 5; index++)
            _ = wrappedQueue.Dequeue();
        wrappedQueue.Enqueue("maze-queue-wrap-0");
        wrappedQueue.Enqueue(8080);
        wrappedQueue.Enqueue("maze-queue-wrap-2");
        wrappedQueue.Enqueue(graph[10]);
        wrappedQueue.Enqueue("maze-queue-back");

        Queue<int> primitiveQueue = new(4);
        foreach (int value in new[] { 11, 22, 33, 44 })
            primitiveQueue.Enqueue(value);
        _ = primitiveQueue.Dequeue();
        _ = primitiveQueue.Dequeue();
        primitiveQueue.Enqueue(55);
        primitiveQueue.Enqueue(66);

        Stack<object?> businessStack = new(8);
        businessStack.Push("maze-stack-bottom");
        businessStack.Push(graph[9]);
        businessStack.Push(null);
        businessStack.Push("maze-stack-removed-slot");
        _ = businessStack.Pop();
        businessStack.Push("maze-stack-top");

        Stack<int> primitiveStack = new(8);
        primitiveStack.Push(1001);
        primitiveStack.Push(2002);
        primitiveStack.Push(3003);
        _ = primitiveStack.Pop();
        primitiveStack.Push(4004);

        LinkedList<object?> businessLinkedList = new();
        businessLinkedList.AddLast("maze-linked-first");
        businessLinkedList.AddLast(graph[11]);
        object? nullLinkedItem = null;
        businessLinkedList.AddLast(nullLinkedItem);
        LinkedListNode<object?> removedLinkedNode = businessLinkedList.AddLast("maze-linked-removed");
        businessLinkedList.AddLast("maze-linked-last");
        businessLinkedList.Remove(removedLinkedNode);

        LinkedList<int> primitiveLinkedList = new([1111, 2222, 3333]);
        if (!primitiveLinkedList.Remove(2222))
            throw new InvalidOperationException("Primitive LinkedList removal fixture was not installed");
        primitiveLinkedList.AddLast(4444);

        LinkedList<string> countMismatchLinkedList = new(
            ["maze-linked-count-partial-0", "maze-linked-count-partial-1"]);
        SetRequiredField(countMismatchLinkedList, "count", countMismatchLinkedList.Count + 1);

        SortedList<string, object?> businessSortedList = new(StringComparer.Ordinal)
        {
            ["maze-sorted-updated"] = "maze-sorted-old-value",
            ["maze-sorted-null"] = null,
            ["maze-sorted-graph"] = graph[12],
            ["maze-sorted-alpha"] = "maze-sorted-value",
            ["maze-sorted-removed"] = "maze-sorted-removed-value",
        };
        businessSortedList["maze-sorted-updated"] = "maze-sorted-new-value";
        if (!businessSortedList.Remove("maze-sorted-removed"))
            throw new InvalidOperationException("SortedList removal fixture was not installed");

        SortedList<int, int> primitiveSortedList = new()
        {
            [303] = 3003,
            [101] = 1001,
            [202] = 2002,
        };
        if (!primitiveSortedList.Remove(202))
            throw new InvalidOperationException("Primitive SortedList removal fixture was not installed");

        SortedList<string, string> countMismatchSortedList = new(StringComparer.Ordinal)
        {
            ["maze-sorted-count-partial-0"] = "sorted-count-partial-value-0",
            ["maze-sorted-count-partial-1"] = "sorted-count-partial-value-1",
        };
        Array sortedKeys = (Array)ReadRequiredField(countMismatchSortedList, "keys");
        SetRequiredField(countMismatchSortedList, "_size", sortedKeys.Length + 1);

        PriorityQueue<object?, int> businessPriorityQueue = new(8);
        businessPriorityQueue.Enqueue("maze-priority-later", 30);
        businessPriorityQueue.Enqueue(graph[13], 10);
        businessPriorityQueue.Enqueue(null, 20);
        businessPriorityQueue.Enqueue("maze-priority-removed", 5);
        if (!Equals(businessPriorityQueue.Dequeue(), "maze-priority-removed"))
            throw new InvalidOperationException("PriorityQueue removal fixture was not installed");
        businessPriorityQueue.Enqueue("maze-priority-urgent", 1);

        PriorityQueue<int, int> primitivePriorityQueue = new();
        primitivePriorityQueue.Enqueue(7007, 70);
        primitivePriorityQueue.Enqueue(1001, 10);
        primitivePriorityQueue.Enqueue(4004, 40);
        if (primitivePriorityQueue.Dequeue() != 1001)
            throw new InvalidOperationException("Primitive PriorityQueue removal fixture was not installed");

        PriorityQueue<string, int> countMismatchPriorityQueue = new();
        countMismatchPriorityQueue.Enqueue("maze-priority-count-partial", 1);
        Array priorityNodes = (Array)ReadRequiredField(countMismatchPriorityQueue, "_nodes");
        SetRequiredField(countMismatchPriorityQueue, "_size", priorityNodes.Length + 1);

        List<object?> readOnlyListBacking =
        [
            "maze-readonly-list-first",
            graph[14],
            null,
            "maze-readonly-list-removed",
            "maze-readonly-list-last",
        ];
        readOnlyListBacking.RemoveAt(3);
        ReadOnlyCollection<object?> businessReadOnlyCollection = readOnlyListBacking.AsReadOnly();
        ReadOnlyCollection<int> arrayReadOnlyCollection = Array.AsReadOnly(new[] { 1212, 3434, 5656 });
        FixtureList<string> customListBacking =
        [
            "maze-readonly-custom-partial-0",
            "maze-readonly-custom-partial-1",
        ];
        ReadOnlyCollection<string> customReadOnlyCollection = new(customListBacking);

        Dictionary<string, object?> readOnlyDictionaryBacking = new(StringComparer.Ordinal)
        {
            ["maze-readonly-dictionary-alpha"] = "maze-readonly-dictionary-value",
            ["maze-readonly-dictionary-graph"] = graph[15],
            ["maze-readonly-dictionary-null"] = null,
            ["maze-readonly-dictionary-updated"] = "maze-readonly-dictionary-old-value",
            ["maze-readonly-dictionary-removed"] = "maze-readonly-dictionary-removed-value",
        };
        readOnlyDictionaryBacking["maze-readonly-dictionary-updated"] = "maze-readonly-dictionary-new-value";
        readOnlyDictionaryBacking.Remove("maze-readonly-dictionary-removed");
        ReadOnlyDictionary<string, object?> businessReadOnlyDictionary = new(readOnlyDictionaryBacking);

        SortedList<int, int> readOnlySortedBacking = new()
        {
            [909] = 9009,
            [707] = 7007,
            [808] = 8008,
        };
        readOnlySortedBacking.Remove(808);
        ReadOnlyDictionary<int, int> sortedReadOnlyDictionary = new(readOnlySortedBacking);

        FixtureDictionary<string, string> customDictionaryBacking = new()
        {
            ["maze-readonly-custom-dictionary-partial"] = "custom-dictionary-partial-value",
        };
        ReadOnlyDictionary<string, string> customReadOnlyDictionary = new(customDictionaryBacking);

        object boxedImmutableArray = ImmutableArray.Create<object?>(
            "maze-immutable-array-first", graph[16], null, "maze-immutable-array-last");
        object defaultImmutableArray = default(ImmutableArray<string>);

        ImmutableList<object?> immutableListBase = ImmutableList.Create<object?>(
            "maze-immutable-list-first", graph[17], null, "maze-immutable-list-shared");
        ImmutableList<object?> businessImmutableList = immutableListBase
            .Add("maze-immutable-list-removed")
            .Remove("maze-immutable-list-removed")
            .Add("maze-immutable-list-last")
            .Add(graph[18]);
        ImmutableList<object?> siblingImmutableList = immutableListBase.Add("maze-immutable-list-sibling");
        ImmutableList<int> primitiveImmutableList = ImmutableList.Create(111, 222, 333).Remove(222).Add(444);
        ImmutableList<string> countMismatchImmutableList =
            ImmutableList.Create("maze-immutable-list-count-partial-0", "maze-immutable-list-count-partial-1");
        object immutableListRoot = ReadRequiredField(countMismatchImmutableList, "_root");
        int immutableListCount = (int)ReadRequiredField(immutableListRoot, "_count");
        SetRequiredField(immutableListRoot, "_count", immutableListCount + 1);

        ImmutableDictionary<string, object?> immutableDictionaryBase =
            ImmutableDictionary.Create<string, object?>(ConstantHashStringComparer.Instance)
                .Add("maze-immutable-dictionary-alpha", "maze-immutable-dictionary-value")
                .Add("maze-immutable-dictionary-graph", graph[19])
                .Add("maze-immutable-dictionary-shared", "maze-immutable-dictionary-shared-value");
        ImmutableDictionary<string, object?> businessImmutableDictionary = immutableDictionaryBase
            .Add("maze-immutable-dictionary-null", null)
            .Add("maze-immutable-dictionary-updated", "maze-immutable-dictionary-old-value")
            .SetItem("maze-immutable-dictionary-updated", "maze-immutable-dictionary-new-value")
            .Add("maze-immutable-dictionary-removed", "maze-immutable-dictionary-removed-value")
            .Remove("maze-immutable-dictionary-removed");
        ImmutableDictionary<string, object?> siblingImmutableDictionary =
            immutableDictionaryBase.Add("maze-immutable-dictionary-sibling", graph[20]);
        ImmutableDictionary<int, int> primitiveImmutableDictionary =
            ImmutableDictionary<int, int>.Empty.Add(101, 1001).Add(202, 2002).Remove(202).Add(303, 3003);
        ImmutableDictionary<string, string> countMismatchImmutableDictionary =
            ImmutableDictionary<string, string>.Empty
                .Add("maze-immutable-dictionary-count-partial", "immutable-dictionary-count-partial-value");
        SetRequiredField(countMismatchImmutableDictionary, "_count", countMismatchImmutableDictionary.Count + 1);

        ImmutableSortedDictionary<string, object?> immutableSortedDictionaryBase =
            ImmutableSortedDictionary.Create<string, object?>(StringComparer.Ordinal)
                .Add("maze-immutable-sorted-dictionary-alpha", "maze-immutable-sorted-dictionary-value")
                .Add("maze-immutable-sorted-dictionary-graph", graph[25])
                .Add("maze-immutable-sorted-dictionary-shared", "maze-immutable-sorted-dictionary-shared-value");
        ImmutableSortedDictionary<string, object?> businessImmutableSortedDictionary =
            immutableSortedDictionaryBase
                .Add("maze-immutable-sorted-dictionary-null", null)
                .Add("maze-immutable-sorted-dictionary-updated", "maze-immutable-sorted-dictionary-old-value")
                .SetItem("maze-immutable-sorted-dictionary-updated", "maze-immutable-sorted-dictionary-new-value")
                .Add("maze-immutable-sorted-dictionary-removed", "maze-immutable-sorted-dictionary-removed-value")
                .Remove("maze-immutable-sorted-dictionary-removed");
        ImmutableSortedDictionary<string, object?> siblingImmutableSortedDictionary =
            immutableSortedDictionaryBase.Add("maze-immutable-sorted-dictionary-sibling", graph[26]);
        ImmutableSortedDictionary<int, int> primitiveImmutableSortedDictionary =
            ImmutableSortedDictionary<int, int>.Empty
                .Add(101, 1001).Add(202, 2002).Remove(202).Add(303, 3003);
        ImmutableSortedDictionary<string, string> countMismatchImmutableSortedDictionary =
            ImmutableSortedDictionary<string, string>.Empty
                .Add("maze-immutable-sorted-dictionary-count-partial", "sorted-dictionary-count-partial-value");
        SetRequiredField(countMismatchImmutableSortedDictionary, "_count",
            countMismatchImmutableSortedDictionary.Count + 1);
        ImmutableSortedDictionary<long, string> cycleImmutableSortedDictionary =
            ImmutableSortedDictionary<long, string>.Empty
                .Add(1701L, "maze-immutable-sorted-dictionary-cycle-partial");
        object cycleImmutableSortedDictionaryRoot = ReadRequiredField(cycleImmutableSortedDictionary, "_root");
        SetRequiredField(cycleImmutableSortedDictionaryRoot, "_left", cycleImmutableSortedDictionaryRoot);

        ImmutableHashSet<object?> immutableSetBase = ImmutableHashSet.Create<object?>(
            ConstantHashObjectComparer.Instance,
            "maze-immutable-set-first", graph[21], null, "maze-immutable-set-shared");
        ImmutableHashSet<object?> businessImmutableSet = immutableSetBase
            .Add("maze-immutable-set-removed")
            .Remove("maze-immutable-set-removed")
            .Add("maze-immutable-set-last")
            .Add(graph[22]);
        ImmutableHashSet<object?> siblingImmutableSet = immutableSetBase.Add("maze-immutable-set-sibling");
        ImmutableHashSet<int> primitiveImmutableSet = ImmutableHashSet.Create(1111, 2222, 3333).Remove(2222).Add(4444);
        ImmutableHashSet<string> countMismatchImmutableSet =
            ImmutableHashSet.Create("maze-immutable-set-count-partial");
        SetRequiredField(countMismatchImmutableSet, "_count", countMismatchImmutableSet.Count + 1);

        ImmutableSortedSet<object?> immutableSortedSetBase = ImmutableSortedSet<object?>.Empty
            .WithComparer(FixtureObjectComparer.Instance)
            .Add(null)
            .Add("maze-immutable-sorted-set-first")
            .Add(graph[27])
            .Add("maze-immutable-sorted-set-shared");
        ImmutableSortedSet<object?> businessImmutableSortedSet = immutableSortedSetBase
            .Add("maze-immutable-sorted-set-removed")
            .Remove("maze-immutable-sorted-set-removed")
            .Add("maze-immutable-sorted-set-last")
            .Add(graph[28]);
        ImmutableSortedSet<object?> siblingImmutableSortedSet =
            immutableSortedSetBase.Add("maze-immutable-sorted-set-sibling");
        ImmutableSortedSet<int> primitiveImmutableSortedSet =
            ImmutableSortedSet.Create(1111, 2222, 3333).Remove(2222).Add(4444);
        ImmutableSortedSet<string> countMismatchImmutableSortedSet =
            ImmutableSortedSet.Create("maze-immutable-sorted-set-count-partial");
        object countMismatchImmutableSortedSetRoot = ReadRequiredField(countMismatchImmutableSortedSet, "_root");
        int countMismatchImmutableSortedSetCount =
            (int)ReadRequiredField(countMismatchImmutableSortedSetRoot, "_count");
        SetRequiredField(countMismatchImmutableSortedSetRoot, "_count",
            countMismatchImmutableSortedSetCount + 1);
        ImmutableSortedSet<long> cycleImmutableSortedSet =
            ImmutableSortedSet.Create(1701L);
        object cycleImmutableSortedSetRoot = ReadRequiredField(cycleImmutableSortedSet, "_root");
        SetRequiredField(cycleImmutableSortedSetRoot, "_left", cycleImmutableSortedSetRoot);

        ImmutableQueue<object?> businessImmutableQueue = ImmutableQueue<object?>.Empty
            .Enqueue("maze-immutable-queue-removed")
            .Enqueue("maze-immutable-queue-first")
            .Enqueue(graph[23])
            .Enqueue(null)
            .Dequeue()
            .Enqueue("maze-immutable-queue-last");
        ImmutableQueue<int> primitiveImmutableQueue = ImmutableQueue<int>.Empty
            .Enqueue(111).Enqueue(222).Enqueue(333).Dequeue().Enqueue(444);

        ImmutableStack<object?> businessImmutableStack = ImmutableStack<object?>.Empty
            .Push("maze-immutable-stack-bottom")
            .Push(graph[24])
            .Push(null)
            .Push("maze-immutable-stack-top");
        ImmutableStack<int> primitiveImmutableStack = ImmutableStack<int>.Empty.Push(111).Push(222).Push(333);
        ImmutableStack<string> cycleImmutableStack = ImmutableStack<string>.Empty
            .Push("maze-immutable-stack-cycle-partial");
        SetRequiredField(cycleImmutableStack, "_tail", cycleImmutableStack);

        ImmutableArray<object?>.Builder businessImmutableArrayBuilder = ImmutableArray.CreateBuilder<object?>(8);
        businessImmutableArrayBuilder.Add("maze-immutable-array-builder-removed");
        businessImmutableArrayBuilder.Add("maze-immutable-array-builder-first");
        businessImmutableArrayBuilder.Add(graph[32]);
        businessImmutableArrayBuilder.Add(null);
        businessImmutableArrayBuilder.RemoveAt(0);
        businessImmutableArrayBuilder.Add("maze-immutable-array-builder-last");
        ImmutableArray<string>.Builder countMismatchImmutableArrayBuilder = ImmutableArray.CreateBuilder<string>(1);
        countMismatchImmutableArrayBuilder.Add("maze-immutable-array-builder-partial");
        SetRequiredField(countMismatchImmutableArrayBuilder, "_count", 2);

        ImmutableList<object?>.Builder businessImmutableListBuilder = ImmutableList.CreateBuilder<object?>();
        businessImmutableListBuilder.Add("maze-immutable-list-builder-removed");
        businessImmutableListBuilder.Add("maze-immutable-list-builder-first");
        businessImmutableListBuilder.Add(graph[33]);
        businessImmutableListBuilder.Add(null);
        businessImmutableListBuilder.Remove("maze-immutable-list-builder-removed");
        businessImmutableListBuilder.Add("maze-immutable-list-builder-last");

        ImmutableDictionary<string, object?>.Builder businessImmutableDictionaryBuilder =
            ImmutableDictionary.CreateBuilder<string, object?>(ConstantHashStringComparer.Instance);
        businessImmutableDictionaryBuilder["maze-immutable-dictionary-builder-alpha"] =
            "maze-immutable-dictionary-builder-value";
        businessImmutableDictionaryBuilder["maze-immutable-dictionary-builder-graph"] = graph[34];
        businessImmutableDictionaryBuilder["maze-immutable-dictionary-builder-null"] = null;
        businessImmutableDictionaryBuilder["maze-immutable-dictionary-builder-updated"] =
            "maze-immutable-dictionary-builder-old-value";
        businessImmutableDictionaryBuilder["maze-immutable-dictionary-builder-updated"] =
            "maze-immutable-dictionary-builder-new-value";
        businessImmutableDictionaryBuilder["maze-immutable-dictionary-builder-removed"] =
            "maze-immutable-dictionary-builder-removed-value";
        businessImmutableDictionaryBuilder.Remove("maze-immutable-dictionary-builder-removed");
        ImmutableDictionary<long, string>.Builder countMismatchImmutableDictionaryBuilder =
            ImmutableDictionary.CreateBuilder<long, string>();
        countMismatchImmutableDictionaryBuilder[1701L] = "maze-immutable-dictionary-builder-partial";
        SetRequiredField(countMismatchImmutableDictionaryBuilder, "_count", 2);

        ImmutableHashSet<object?>.Builder businessImmutableSetBuilder =
            ImmutableHashSet.CreateBuilder<object?>(ConstantHashObjectComparer.Instance);
        businessImmutableSetBuilder.Add("maze-immutable-set-builder-removed");
        businessImmutableSetBuilder.Add("maze-immutable-set-builder-first");
        businessImmutableSetBuilder.Add(graph[35]);
        businessImmutableSetBuilder.Add(null);
        businessImmutableSetBuilder.Remove("maze-immutable-set-builder-removed");
        businessImmutableSetBuilder.Add("maze-immutable-set-builder-last");

        ImmutableSortedDictionary<string, object?>.Builder businessImmutableSortedDictionaryBuilder =
            ImmutableSortedDictionary.CreateBuilder<string, object?>(StringComparer.Ordinal);
        businessImmutableSortedDictionaryBuilder["maze-immutable-sorted-dictionary-builder-alpha"] =
            "maze-immutable-sorted-dictionary-builder-value";
        businessImmutableSortedDictionaryBuilder["maze-immutable-sorted-dictionary-builder-graph"] = graph[36];
        businessImmutableSortedDictionaryBuilder["maze-immutable-sorted-dictionary-builder-null"] = null;
        businessImmutableSortedDictionaryBuilder["maze-immutable-sorted-dictionary-builder-updated"] =
            "maze-immutable-sorted-dictionary-builder-old-value";
        businessImmutableSortedDictionaryBuilder["maze-immutable-sorted-dictionary-builder-updated"] =
            "maze-immutable-sorted-dictionary-builder-new-value";
        businessImmutableSortedDictionaryBuilder["maze-immutable-sorted-dictionary-builder-removed"] =
            "maze-immutable-sorted-dictionary-builder-removed-value";
        businessImmutableSortedDictionaryBuilder.Remove("maze-immutable-sorted-dictionary-builder-removed");

        ImmutableSortedSet<object?>.Builder businessImmutableSortedSetBuilder =
            ImmutableSortedSet.CreateBuilder<object?>(FixtureObjectComparer.Instance);
        businessImmutableSortedSetBuilder.Add(null);
        businessImmutableSortedSetBuilder.Add("maze-immutable-sorted-set-builder-first");
        businessImmutableSortedSetBuilder.Add(graph[37]);
        businessImmutableSortedSetBuilder.Add("maze-immutable-sorted-set-builder-removed");
        businessImmutableSortedSetBuilder.Remove("maze-immutable-sorted-set-builder-removed");
        businessImmutableSortedSetBuilder.Add("maze-immutable-sorted-set-builder-last");
        ImmutableSortedSet<long>.Builder cycleImmutableSortedSetBuilder =
            ImmutableSortedSet.CreateBuilder<long>();
        cycleImmutableSortedSetBuilder.Add(1701L);
        object cycleImmutableSortedSetBuilderRoot = ReadRequiredField(cycleImmutableSortedSetBuilder, "_root");
        SetRequiredField(cycleImmutableSortedSetBuilderRoot, "_left", cycleImmutableSortedSetBuilderRoot);

        Dictionary<string, object?> frozenDictionarySource = new(StringComparer.Ordinal)
        {
            ["maze-frozen-dictionary-alpha"] = "maze-frozen-dictionary-value",
            ["maze-frozen-dictionary-graph"] = graph[29],
            ["maze-frozen-dictionary-null"] = null,
            ["maze-frozen-dictionary-shared"] = "maze-frozen-dictionary-shared-value",
            ["maze-frozen-dictionary-updated"] = "maze-frozen-dictionary-old-value",
            ["maze-frozen-dictionary-removed"] = "maze-frozen-dictionary-removed-value",
        };
        frozenDictionarySource["maze-frozen-dictionary-updated"] = "maze-frozen-dictionary-new-value";
        frozenDictionarySource.Remove("maze-frozen-dictionary-removed");
        for (int index = 0; index < 24; index++)
            frozenDictionarySource[$"maze-frozen-dictionary-filler-{index:D2}"] = index;
        FrozenDictionary<string, object?> businessFrozenDictionary =
            frozenDictionarySource.ToFrozenDictionary(StringComparer.Ordinal);

        Dictionary<int, int> int32FrozenDictionarySource = [];
        for (int index = 0; index < 20; index++)
            int32FrozenDictionarySource[101 + index * 1_000_000] = 1001 + index;
        FrozenDictionary<int, int> int32FrozenDictionary = int32FrozenDictionarySource.ToFrozenDictionary();
        FrozenDictionary<byte, string> denseFullFrozenDictionary = new Dictionary<byte, string>
        {
            [0] = "maze-frozen-dense-full-zero",
            [1] = "maze-frozen-dense-full-one",
            [2] = "maze-frozen-dense-full-two",
        }.ToFrozenDictionary();
        FrozenDictionary<short, string> denseOptionalFrozenDictionary = new Dictionary<short, string>
        {
            [-3] = "maze-frozen-dense-optional-minus-three",
            [0] = "maze-frozen-dense-optional-zero",
            [2] = "maze-frozen-dense-optional-two",
        }.ToFrozenDictionary();
        FrozenDictionary<Guid, string> countMismatchFrozenDictionary = new Dictionary<Guid, string>
        {
            [Guid.Parse("11111111-1111-1111-1111-111111111111")] = "maze-frozen-dictionary-partial-one",
            [Guid.Parse("22222222-2222-2222-2222-222222222222")] = "maze-frozen-dictionary-partial-two",
        }.ToFrozenDictionary();
        SetRequiredField(countMismatchFrozenDictionary, "_values",
            new[] { "maze-frozen-dictionary-partial-one" });

        HashSet<object?> frozenSetSource = new(ConstantHashObjectComparer.Instance)
        {
            null,
            "maze-frozen-set-first",
            "maze-frozen-set-shared",
            graph[30],
            graph[31],
            "maze-frozen-set-removed",
        };
        frozenSetSource.Remove("maze-frozen-set-removed");
        for (int index = 0; index < 20; index++)
            frozenSetSource.Add($"maze-frozen-set-filler-{index:D2}");
        FrozenSet<object?> businessFrozenSet = frozenSetSource.ToFrozenSet(ConstantHashObjectComparer.Instance);

        HashSet<string> ordinalFrozenSetSource = new(StringComparer.Ordinal);
        for (int index = 0; index < 24; index++)
            ordinalFrozenSetSource.Add($"maze-frozen-ordinal-set-{index:D2}");
        FrozenSet<string> ordinalFrozenSet = ordinalFrozenSetSource.ToFrozenSet(StringComparer.Ordinal);
        HashSet<int> int32FrozenSetSource = [];
        for (int index = 0; index < 20; index++)
            int32FrozenSetSource.Add(1111 + index * 1_000_000);
        FrozenSet<int> int32FrozenSet = int32FrozenSetSource.ToFrozenSet();
        FrozenSet<long> countMismatchFrozenSet = new HashSet<long> { 1701L, 1702L }.ToFrozenSet();
        SetRequiredField(countMismatchFrozenSet, "_items", null!);

        return new CollectionFixtures
        {
            BusinessConcurrentDictionary = businessConcurrentDictionary,
            PrimitiveConcurrentDictionary = primitiveConcurrentDictionary,
            CountMismatchConcurrentDictionary = countMismatchConcurrentDictionary,
            CycleConcurrentDictionary = cycleConcurrentDictionary,
            BusinessConcurrentQueue = businessConcurrentQueue,
            PrimitiveConcurrentQueue = primitiveConcurrentQueue,
            CycleConcurrentQueue = cycleConcurrentQueue,
            BusinessConcurrentStack = businessConcurrentStack,
            PrimitiveConcurrentStack = primitiveConcurrentStack,
            CycleConcurrentStack = cycleConcurrentStack,
            BusinessConcurrentBag = businessConcurrentBag,
            PrimitiveConcurrentBag = primitiveConcurrentBag,
            CycleConcurrentBag = cycleConcurrentBag,
            CountMismatchConcurrentBag = countMismatchConcurrentBag,
            CurrentOperationConcurrentBag = currentOperationConcurrentBag,
            BusinessBlockingCollection = businessBlockingCollection,
            CompletedBlockingCollection = completedBlockingCollection,
            CompletedEmptyBlockingCollection = completedEmptyBlockingCollection,
            CustomBlockingCollection = customBlockingCollection,
            CountMismatchBlockingCollection = countMismatchBlockingCollection,
            CompletingBlockingCollection = completingBlockingCollection,
            DisposedBlockingCollection = disposedBlockingCollection,
            BusinessUnboundedChannel = businessUnboundedChannel,
            SingleReaderUnboundedChannel = singleReaderUnboundedChannel,
            BusinessBoundedChannel = businessBoundedChannel,
            DrainingBoundedChannel = drainingBoundedChannel,
            CompletedEmptyUnboundedChannel = completedEmptyUnboundedChannel,
            CountMismatchBoundedChannel = countMismatchBoundedChannel,
            BlockedWriterChannel = blockedWriterChannel,
            BlockedChannelWrite = blockedChannelWrite,
            BlockedReaderChannel = blockedReaderChannel,
            BlockedChannelRead = blockedChannelRead,
            RendezvousChannel = rendezvousChannel,
            BusinessSet = businessSet,
            PrimitiveSet = primitiveSet,
            WrappedQueue = wrappedQueue,
            PrimitiveQueue = primitiveQueue,
            BusinessStack = businessStack,
            PrimitiveStack = primitiveStack,
            BusinessLinkedList = businessLinkedList,
            PrimitiveLinkedList = primitiveLinkedList,
            CountMismatchLinkedList = countMismatchLinkedList,
            BusinessSortedList = businessSortedList,
            PrimitiveSortedList = primitiveSortedList,
            CountMismatchSortedList = countMismatchSortedList,
            BusinessPriorityQueue = businessPriorityQueue,
            PrimitivePriorityQueue = primitivePriorityQueue,
            CountMismatchPriorityQueue = countMismatchPriorityQueue,
            BusinessReadOnlyCollection = businessReadOnlyCollection,
            ArrayReadOnlyCollection = arrayReadOnlyCollection,
            CustomReadOnlyCollection = customReadOnlyCollection,
            BusinessReadOnlyDictionary = businessReadOnlyDictionary,
            SortedReadOnlyDictionary = sortedReadOnlyDictionary,
            CustomReadOnlyDictionary = customReadOnlyDictionary,
            BoxedImmutableArray = boxedImmutableArray,
            DefaultImmutableArray = defaultImmutableArray,
            BusinessImmutableList = businessImmutableList,
            SiblingImmutableList = siblingImmutableList,
            PrimitiveImmutableList = primitiveImmutableList,
            CountMismatchImmutableList = countMismatchImmutableList,
            BusinessImmutableDictionary = businessImmutableDictionary,
            SiblingImmutableDictionary = siblingImmutableDictionary,
            PrimitiveImmutableDictionary = primitiveImmutableDictionary,
            CountMismatchImmutableDictionary = countMismatchImmutableDictionary,
            BusinessImmutableSortedDictionary = businessImmutableSortedDictionary,
            SiblingImmutableSortedDictionary = siblingImmutableSortedDictionary,
            PrimitiveImmutableSortedDictionary = primitiveImmutableSortedDictionary,
            CountMismatchImmutableSortedDictionary = countMismatchImmutableSortedDictionary,
            CycleImmutableSortedDictionary = cycleImmutableSortedDictionary,
            BusinessImmutableSet = businessImmutableSet,
            SiblingImmutableSet = siblingImmutableSet,
            PrimitiveImmutableSet = primitiveImmutableSet,
            CountMismatchImmutableSet = countMismatchImmutableSet,
            BusinessImmutableSortedSet = businessImmutableSortedSet,
            SiblingImmutableSortedSet = siblingImmutableSortedSet,
            PrimitiveImmutableSortedSet = primitiveImmutableSortedSet,
            CountMismatchImmutableSortedSet = countMismatchImmutableSortedSet,
            CycleImmutableSortedSet = cycleImmutableSortedSet,
            BusinessImmutableQueue = businessImmutableQueue,
            PrimitiveImmutableQueue = primitiveImmutableQueue,
            BusinessImmutableStack = businessImmutableStack,
            PrimitiveImmutableStack = primitiveImmutableStack,
            CycleImmutableStack = cycleImmutableStack,
            BusinessImmutableArrayBuilder = businessImmutableArrayBuilder,
            CountMismatchImmutableArrayBuilder = countMismatchImmutableArrayBuilder,
            BusinessImmutableListBuilder = businessImmutableListBuilder,
            BusinessImmutableDictionaryBuilder = businessImmutableDictionaryBuilder,
            CountMismatchImmutableDictionaryBuilder = countMismatchImmutableDictionaryBuilder,
            BusinessImmutableSetBuilder = businessImmutableSetBuilder,
            BusinessImmutableSortedDictionaryBuilder = businessImmutableSortedDictionaryBuilder,
            BusinessImmutableSortedSetBuilder = businessImmutableSortedSetBuilder,
            CycleImmutableSortedSetBuilder = cycleImmutableSortedSetBuilder,
            BusinessFrozenDictionary = businessFrozenDictionary,
            Int32FrozenDictionary = int32FrozenDictionary,
            DenseFullFrozenDictionary = denseFullFrozenDictionary,
            DenseOptionalFrozenDictionary = denseOptionalFrozenDictionary,
            CountMismatchFrozenDictionary = countMismatchFrozenDictionary,
            EmptyFrozenDictionary = FrozenDictionary<string, string>.Empty,
            BusinessFrozenSet = businessFrozenSet,
            OrdinalFrozenSet = ordinalFrozenSet,
            Int32FrozenSet = int32FrozenSet,
            CountMismatchFrozenSet = countMismatchFrozenSet,
            EmptyFrozenSet = FrozenSet<string>.Empty,
        };
    }

    private static void CorruptConcurrentDictionaryCount<TKey, TValue>(ConcurrentDictionary<TKey, TValue> value)
        where TKey : notnull
    {
        object tables = ReadRequiredField(value, "_tables");
        int[] counts = (int[])ReadRequiredField(tables, "_countPerLock");
        counts[0] = checked(counts[0] + 1);
    }

    private static void CorruptConcurrentQueueCycle<T>(ConcurrentQueue<T> value)
    {
        object head = ReadRequiredField(value, "_head");
        SetRequiredField(head, "_nextSegment", head);
    }

    private static void CorruptConcurrentStackCycle<T>(ConcurrentStack<T> value)
    {
        object head = ReadRequiredField(value, "_head");
        SetRequiredField(head, "_next", head);
    }

    private static void CorruptConcurrentBagCycle<T>(ConcurrentBag<T> value)
    {
        object queue = ReadRequiredField(value, "_workStealingQueues");
        SetRequiredField(queue, "_nextQueue", queue);
    }

    private static void CorruptConcurrentBagCount<T>(ConcurrentBag<T> value)
    {
        object queue = ReadRequiredField(value, "_workStealingQueues");
        FieldInfo? field = FindInstanceField(queue.GetType(), "_addTakeCount");
        if (field?.GetValue(queue) is not int count)
            throw new InvalidOperationException("ConcurrentBag WorkStealingQueue._addTakeCount was not found");
        field.SetValue(queue, checked(count + 1));
    }

    private static void CorruptConcurrentBagCurrentOperation<T>(ConcurrentBag<T> value)
    {
        object queue = ReadRequiredField(value, "_workStealingQueues");
        FieldInfo? field = FindInstanceField(queue.GetType(), "_currentOp");
        if (field is null)
            throw new InvalidOperationException("ConcurrentBag WorkStealingQueue._currentOp was not found");
        object operation = field.FieldType.IsEnum ? Enum.ToObject(field.FieldType, 1) : 1;
        field.SetValue(queue, operation);
    }

    private static void CorruptBlockingCollectionOccupiedCount<T>(BlockingCollection<T> value)
    {
        object occupied = ReadRequiredField(value, "_occupiedNodes");
        FieldInfo? currentCount = FindInstanceField(occupied.GetType(), "m_currentCount");
        if (currentCount?.GetValue(occupied) is not int count)
            throw new InvalidOperationException("BlockingCollection occupied semaphore count was not found");
        currentCount.SetValue(occupied, checked(count + 1));
    }

    private static void CorruptBoundedChannelCount<T>(Channel<T> value)
    {
        object items = ReadRequiredField(value, "_items");
        Array array = (Array)ReadRequiredField(items, "_array");
        SetRequiredField(items, "_size", checked(array.Length + 1));
    }

    private static void CorruptConcurrentDictionaryCycle<TKey, TValue>(ConcurrentDictionary<TKey, TValue> value)
        where TKey : notnull
    {
        object tables = ReadRequiredField(value, "_tables");
        Array buckets = (Array)ReadRequiredField(tables, "_buckets");
        FieldInfo? nodeField = buckets.GetType().GetElementType()?.GetField(
            "_node", BindingFlags.Instance | BindingFlags.NonPublic);
        if (nodeField is null)
            throw new InvalidOperationException("ConcurrentDictionary VolatileNode._node was not found");
        object? node = null;
        foreach (object? bucket in buckets)
        {
            if (bucket is not null && nodeField.GetValue(bucket) is object candidate)
            {
                node = candidate;
                break;
            }
        }
        if (node is null)
            throw new InvalidOperationException("ConcurrentDictionary cycle fixture has no node");
        FieldInfo? nextField = node.GetType().GetField("_next", BindingFlags.Instance | BindingFlags.NonPublic);
        if (nextField is null)
            throw new InvalidOperationException("ConcurrentDictionary Node._next was not found");
        nextField.SetValue(node, node);
    }

    private static object ReadRequiredField(object value, string name)
    {
        FieldInfo? field = FindInstanceField(value.GetType(), name);
        return field?.GetValue(value) ??
               throw new InvalidOperationException($"{value.GetType().FullName}.{name} was not found");
    }

    private static void SetRequiredField(object value, string name, object fieldValue)
    {
        FieldInfo? field = FindInstanceField(value.GetType(), name);
        if (field is null)
            throw new InvalidOperationException($"{value.GetType().FullName}.{name} was not found");
        field.SetValue(value, fieldValue);
    }

    private static FieldInfo? FindInstanceField(Type type, string name)
    {
        for (Type? current = type; current is not null; current = current.BaseType)
        {
            FieldInfo? field = current.GetField(name,
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly);
            if (field is not null)
                return field;
        }
        return null;
    }
}

internal sealed class ConstantHashStringComparer : IEqualityComparer<string>
{
    public static ConstantHashStringComparer Instance { get; } = new();
    public bool Equals(string? left, string? right) => StringComparer.Ordinal.Equals(left, right);
    public int GetHashCode(string value) => 17;
}

internal sealed class ConstantHashObjectComparer : IEqualityComparer<object?>
{
    public static ConstantHashObjectComparer Instance { get; } = new();
    public new bool Equals(object? left, object? right) => object.Equals(left, right);
    public int GetHashCode(object? value) => 17;
}

internal sealed class FixtureObjectComparer : IComparer<object?>
{
    public static FixtureObjectComparer Instance { get; } = new();

    public int Compare(object? left, object? right)
    {
        if (ReferenceEquals(left, right))
            return 0;
        if (left is null)
            return -1;
        if (right is null)
            return 1;
        int leftRank = left is string ? 0 : left is GraphNode ? 1 : 2;
        int rightRank = right is string ? 0 : right is GraphNode ? 1 : 2;
        if (leftRank != rightRank)
            return leftRank.CompareTo(rightRank);
        if (left is string leftString && right is string rightString)
            return StringComparer.Ordinal.Compare(leftString, rightString);
        if (left is GraphNode leftNode && right is GraphNode rightNode)
            return leftNode.Id.CompareTo(rightNode.Id);
        return StringComparer.Ordinal.Compare(left.ToString(), right.ToString());
    }
}

internal sealed class FixtureValueTaskSource : IValueTaskSource<int>
{
    private ManualResetValueTaskSourceCore<int> _core = new()
    {
        RunContinuationsAsynchronously = true,
    };

    public ValueTask<int> CreateValueTask() => new(this, _core.Version);
    public void Reset() => _core.Reset();
    public static FixtureValueTaskSource Succeeded(int result)
    {
        FixtureValueTaskSource source = new();
        source._core.SetResult(result);
        return source;
    }

    public static FixtureValueTaskSource Faulted(Exception error)
    {
        FixtureValueTaskSource source = new();
        source._core.SetException(error);
        return source;
    }

    public int GetResult(short token) => _core.GetResult(token);
    public ValueTaskSourceStatus GetStatus(short token) => _core.GetStatus(token);
    public void OnCompleted(Action<object?> continuation, object? state, short token,
        ValueTaskSourceOnCompletedFlags flags) => _core.OnCompleted(continuation, state, token, flags);
}
internal sealed record NativeAllocationHolder(nint Address, int Size);
internal sealed record MultiRootHolder(string Name, MultiRootPayload Payload);
internal sealed record MultiRootPayload(int Value);
public sealed record CollectiblePayload(int Value = 10001);
internal sealed record WeakTarget(int Value);
internal sealed class MonitorFixtureLock
{
}

internal sealed class ArrayHolder
{
    public ArrayHolder(GraphNode[] nodes)
    {
        Integers = Enumerable.Range(0, 128).ToArray();
        Jagged =
        [
            nodes[..16],
            nodes[16..32],
            nodes[32..48],
            nodes[48..64],
        ];
        Matrix = new GraphNode?[4, 4];
        for (int row = 0; row < 4; row++)
            for (int column = 0; column < 4; column++)
                Matrix[row, column] = nodes[row * 4 + column];
    }

    public int[] Integers { get; }
    public GraphNode[][] Jagged { get; }
    public GraphNode?[,] Matrix { get; }
}

internal sealed class LargeObjectHolder
{
    public LargeObjectHolder(int id)
    {
        Id = id;
        Payload = new byte[100_000];
        Payload[0] = checked((byte)id);
    }

    public int Id { get; }
    public byte[] Payload { get; }
}

internal sealed class PinnedObjectHolder
{
    public PinnedObjectHolder(int id)
    {
        Id = id;
        Payload = GC.AllocateArray<byte>(4096, pinned: true);
        Payload[0] = checked((byte)id);
    }

    public int Id { get; }
    public byte[] Payload { get; }
}

internal static class NestedContainer
{
    internal sealed record NestedNode(int Value);
}

internal sealed class FinalizableObject(int id)
{
    public int Id { get; } = id;

    ~FinalizableObject()
    {
        GC.KeepAlive(Id);
    }
}

internal sealed class BlockingFinalizer
{
    ~BlockingFinalizer()
    {
        Program.WaitInFinalizer();
    }
}

internal sealed class FinalizerQueueRoot
{
    ~FinalizerQueueRoot()
    {
    }
}

internal sealed class FixtureException(string message, Exception innerException) : Exception(message, innerException);
