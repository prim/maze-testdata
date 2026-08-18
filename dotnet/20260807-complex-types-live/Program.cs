using System.Collections.Concurrent;
using System.Collections.Immutable;
using System.Numerics;
using System.Runtime.CompilerServices;

namespace MazeCSharpComplexTypes;

public sealed class SimpleClass
{
    public int Marker;
}

public sealed class PersonClass
{
    public string Name = "";
    public int Age;
    public string Email = "";
    public List<string> Tags = new();
    public Dictionary<string, string> Metadata = new();
}

public sealed class Point
{
    public double X;
    public double Y;
}

public sealed class Rectangle
{
    public int X;
    public int Y;
    public int Width;
    public int Height;
}

public sealed class GameEntity
{
    public int EntityId;
    public Point Position = new();
    public int HitPoints;
    public List<string> Inventory = new();
    public Dictionary<string, object> Status = new();
    public PersonClass? Owner;
    public SharedAsset? Shared;
}

public sealed class TreeNode
{
    public int Value;
    public string Label = "";
    public TreeNode? Left;
    public TreeNode? Right;
    public TreeNode? Parent;
}

public sealed class Tuple1
{
    public int First;
}

public sealed class Tuple2
{
    public int First;
    public int Second;
}

public sealed class Tuple3
{
    public int First;
    public string Second = "";
    public double Third;
}

public sealed class MixedTuple
{
    public object?[] Values = Array.Empty<object?>();
    public List<int> Tail = new();
}

public sealed class SharedAsset
{
    public byte[] Data = Array.Empty<byte>();
    public string Name = "";
}

public sealed class SharedHolder
{
    public int Id;
    public SharedAsset Asset = null!;
}

public sealed class CycleNode
{
    public string Name = "";
    public CycleNode? Next;
}

public sealed class WeakNode
{
    public byte[] Payload = Array.Empty<byte>();
}

public static class Root
{
    public static readonly List<object> Storage = new();
    public static readonly SharedAsset Shared = new()
    {
        Name = "shared-complex-types-asset",
        Data = new byte[2 * MiB],
    };
    public static readonly List<SharedHolder> SharedHolders = new();
    public static CycleNode? RootedCycle;
    public static WeakReference<WeakNode>? WeakControl;

    public const int KiB = 1024;
    public const int MiB = 1024 * 1024;
}

internal static class Program
{
    public static void Main()
    {
        BuildLists();
        BuildTupleLikeObjects();
        BuildCustomClasses();
        BuildSets();
        BuildByteTypes();
        BuildDictionaries();
        BuildStrings();
        BuildNumericTypes();
        BuildCollections();
        BuildSharedAndCycleControls();

        PrintSummary("initial");
        Console.WriteLine($"PID: {Environment.ProcessId}");
        Console.WriteLine("READY FOR MAZE");
        Console.Out.Flush();

        string? command;
        while ((command = Console.ReadLine()) is not null)
        {
            switch (command.Trim().ToLowerInvariant())
            {
                case "gc":
                    FullGc();
                    PrintSummary("after-gc");
                    break;
                case "summary":
                    PrintSummary("manual");
                    break;
                case "exit":
                    return;
                default:
                    Console.WriteLine("COMMANDS gc summary exit");
                    break;
            }
        }
    }

    private static void BuildLists()
    {
        for (int i = 0; i < 1000; i++) Root.Storage.Add(new List<int>());
        for (int i = 0; i < 1000; i++) Root.Storage.Add(new List<int> { i });
        for (int i = 0; i < 500; i++) Root.Storage.Add(Enumerable.Range(i * 10, 10).ToList());
        for (int i = 0; i < 200; i++)
        {
            Root.Storage.Add(new List<object?> { i, $"mixed-{i}", i + 0.25, null, i % 2 == 0 });
        }
        for (int i = 0; i < 100; i++)
        {
            Root.Storage.Add(new List<List<int>>
            {
                new() { i, i + 1 }, new() { i + 2, i + 3 }, new() { i + 4, i + 5 },
            });
        }
    }

    private static void BuildTupleLikeObjects()
    {
        for (int i = 0; i < 1000; i++) Root.Storage.Add(new Tuple1 { First = i });
        for (int i = 0; i < 800; i++) Root.Storage.Add(new Tuple2 { First = i, Second = i * 2 });
        for (int i = 0; i < 500; i++)
        {
            Root.Storage.Add(new Tuple3 { First = i, Second = $"tuple-{i}", Third = i + 0.5 });
        }
        for (int i = 0; i < 200; i++)
        {
            Root.Storage.Add(new MixedTuple
            {
                Values = new object?[] { i, $"mixed-tuple-{i}", i + 0.5, null, true, new byte[] { 1, 2, 3 } },
                Tail = new List<int> { i, i + 1, i + 2 },
            });
        }
    }

    private static void BuildCustomClasses()
    {
        for (int i = 0; i < 500; i++) Root.Storage.Add(new SimpleClass { Marker = i });
        for (int i = 0; i < 1000; i++)
        {
            Root.Storage.Add(new PersonClass
            {
                Name = $"user-{i:D4}",
                Age = 20 + i % 50,
                Email = $"user-{i:D4}@example.com",
                Tags = new List<string> { "maze", "complex", $"tag-{i % 10}" },
                Metadata = new Dictionary<string, string>
                {
                    ["region"] = i % 2 == 0 ? "ap-east" : "us-east",
                    ["tier"] = i % 3 == 0 ? "gold" : "standard",
                },
            });
        }
        for (int i = 0; i < 300; i++)
        {
            PersonClass owner = new() { Name = $"owner-{i}", Age = 30, Email = $"owner-{i}@example.com" };
            Root.Storage.Add(owner);
            Root.Storage.Add(new GameEntity
            {
                EntityId = i,
                Position = new Point { X = i * 10.0, Y = i * 20.0 },
                HitPoints = 100,
                Inventory = new List<string> { "sword", "shield", "potion" },
                Status = new Dictionary<string, object> { ["alive"] = true, ["level"] = 1 + i % 10 },
                Owner = owner,
                Shared = Root.Shared,
            });
        }
        for (int i = 0; i < 200; i++)
        {
            TreeNode root = new() { Value = i, Label = $"root-{i}" };
            TreeNode left = new() { Value = i * 2, Label = $"left-{i}", Parent = root };
            TreeNode right = new() { Value = i * 2 + 1, Label = $"right-{i}", Parent = root };
            root.Left = left;
            root.Right = right;
            Root.Storage.Add(root);
            Root.Storage.Add(left);
            Root.Storage.Add(right);
        }
    }

    private static void BuildSets()
    {
        for (int i = 0; i < 500; i++) Root.Storage.Add(new HashSet<int> { i, i + 1, i + 2 });
        for (int i = 0; i < 300; i++) Root.Storage.Add(new HashSet<int>(Enumerable.Range(i, 20)));
        for (int i = 0; i < 400; i++) Root.Storage.Add(ImmutableHashSet.Create(i, i + 1, i + 2, i + 3));
    }

    private static void BuildByteTypes()
    {
        for (int i = 0; i < 500; i++) Root.Storage.Add(System.Text.Encoding.UTF8.GetBytes($"hello-{i}"));
        for (int i = 0; i < 300; i++) Root.Storage.Add(Enumerable.Repeat((byte)(i % 251), 100).ToArray());
        for (int i = 0; i < 200; i++) Root.Storage.Add(Enumerable.Repeat((byte)(i % 251), 1000).ToArray());
        for (int i = 0; i < 400; i++) Root.Storage.Add(new byte[32 + (i % 4) * 16]);
    }

    private static void BuildDictionaries()
    {
        for (int i = 0; i < 1000; i++) Root.Storage.Add(new Dictionary<string, int> { ["id"] = i, ["value"] = i * 10 });
        for (int i = 0; i < 500; i++)
        {
            Root.Storage.Add(new Dictionary<string, object>
            {
                ["user"] = new Dictionary<string, object>
                {
                    ["id"] = i,
                    ["profile"] = new Dictionary<string, string> { ["name"] = $"user-{i}", ["lang"] = "zh" },
                },
            });
        }
        for (int i = 0; i < 300; i++)
        {
            Dictionary<string, int> wide = new();
            for (int j = 0; j < 20; j++) wide[$"key-{j}"] = j + i;
            Root.Storage.Add(wide);
        }
        for (int i = 0; i < 200; i++) Root.Storage.Add(new SortedDictionary<string, int> { ["first"] = i, ["second"] = i + 1 });
        for (int i = 0; i < 200; i++) Root.Storage.Add(new ConcurrentDictionary<string, int> { ["a"] = i, ["b"] = i + 1 });
        for (int i = 0; i < 200; i++) Root.Storage.Add(new Dictionary<string, int> { ["a"] = i * 3, ["b"] = i * 5, ["c"] = i * 7 });
    }

    private static void BuildStrings()
    {
        for (int i = 0; i < 1000; i++) Root.Storage.Add($"str-{i:D4}");
        for (int i = 0; i < 500; i++) Root.Storage.Add($"medium-string-{i:D4}-" + new string('x', 50));
        for (int i = 0; i < 200; i++) Root.Storage.Add($"long-string-{i:D4}-" + new string('y', 500));
        for (int i = 0; i < 300; i++) Root.Storage.Add($"中文字符串-{i:D4}-你好世界");
    }

    private static void BuildNumericTypes()
    {
        for (int i = 0; i < 500; i++) Root.Storage.Add(10_000_000L + i);
        for (int i = 0; i < 500; i++) Root.Storage.Add(i * 3.14159);
        for (int i = 0; i < 300; i++) Root.Storage.Add(new Complex(i, i + 1));
    }

    private static void BuildCollections()
    {
        for (int i = 0; i < 300; i++) Root.Storage.Add(new Queue<int>(new[] { 1, 2, 3, 4, 5, i }));
        for (int i = 0; i < 400; i++) Root.Storage.Add(new Point { X = i, Y = i * 2.0 });
        for (int i = 0; i < 300; i++) Root.Storage.Add(new Rectangle { X = i, Y = i, Width = 100, Height = 50 });
    }

    private static void BuildSharedAndCycleControls()
    {
        for (int i = 0; i < 96; i++) Root.SharedHolders.Add(new SharedHolder { Id = i, Asset = Root.Shared });
        CycleNode first = new() { Name = "rooted-cycle-a" };
        CycleNode second = new() { Name = "rooted-cycle-b" };
        first.Next = second;
        second.Next = first;
        Root.RootedCycle = first;

        Root.WeakControl = CreateWeakControl();
        FullGc();
        Console.WriteLine($"WEAK_CONTROL_ALIVE={Root.WeakControl.TryGetTarget(out _)}");
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static WeakReference<WeakNode> CreateWeakControl()
    {
        return new WeakReference<WeakNode>(new WeakNode { Payload = new byte[256 * Root.KiB] });
    }

    private static void FullGc()
    {
        GC.Collect(GC.MaxGeneration, GCCollectionMode.Forced, blocking: true, compacting: true);
        GC.WaitForPendingFinalizers();
        GC.Collect(GC.MaxGeneration, GCCollectionMode.Forced, blocking: true, compacting: true);
    }

    private static void PrintSummary(string phase)
    {
        Console.WriteLine($"SUMMARY phase={phase} pid={Environment.ProcessId} storage={Root.Storage.Count} " +
            "lists=2800 tuples=2500 classes=2400 sets=1200 bytes=1400 dicts=2400 strings=2000 " +
            "numeric=1300 collections=1000 shared_holders=96 rooted_cycle=2 weak_control=1");
    }
}
