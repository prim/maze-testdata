# Maze Elixir 1.18.4 known-object fixture.
#
# This standalone script builds a set of live BEAM objects with known values so
# Maze's inventory/search/object/ref/root-path/aggregate can be reconciled
# against ground truth. It is captured with cmd/maze-gen-coredump.py after
# printing READY FOR GCORE; the VM is kept alive with --no-halt.
#
# The ground truth below is stored both in persistent_term (where Maze decodes
# key/value texts) and printed to stdout as an inspect term for the capture log.
#
# The struct is defined in its own top-level module so it is already compiled
# when the rest of the script is evaluated.

defmodule MazeFixture do
  @moduledoc "Known-object struct fixture."
  defstruct [:name, :value, :ref]
end

defmodule MazeWorker do
  @moduledoc "GenServer fixture with state, process dictionary and mailbox."
  use GenServer

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def init(opts) do
    Process.put(:maze_worker_dict, {:maze_worker_value, opts[:seed], self()})
    {:ok, %{seed: opts[:seed], role: "worker"}}
  end

  def handle_call(:state, _from, state), do: {:reply, state, state}
  def handle_info(message, state), do: {:noreply, Map.put(state, :last, message)}
end

defmodule MazeSupervisor do
  @moduledoc "Supervisor fixture hosting MazeWorker and a sleeping Task."
  use Supervisor

  def start_link(_opts) do
    Supervisor.start_link(__MODULE__, [], name: __MODULE__)
  end

  def init(_opts) do
    children = [
      {MazeWorker, [seed: 1234]},
      {Task, fn -> Process.sleep(600_000) end}
    ]
    Supervisor.init(children, strategy: :one_for_one)
  end
end

defmodule MazeElixirFixture do
  @moduledoc "Top-level fixture driver; run/0 builds every known object."

  def run do
    # --- Known atoms (referencing creates them in the atom table) ---
    :maze_elixir_ready
    :elixir_maze_atom
    :elixir_fixture_sentinel

    # --- Terms with known values ---
    fixture_struct = %MazeFixture{name: "maze", value: 42, ref: make_ref()}
    big_map = %{"key1" => 1, "key2" => :two, "key3" => [1, 2, 3], "nested" => %{"a" => :b}}
    maze_tuple = {:maze_tuple, 1, "two", :three}
    maze_list = [1, 2, 3, "four", :five]
    maze_bignum = 123_456_789_012_345_678_901_234_567_890

    # --- Shared large Binary plus a sub-binary (ErlSubBits into a refc) ---
    big_binary = :binary.copy(<<0, 1, 2, 3, 4, 5, 6, 7>>, 1000) # 8000 bytes
    # OTP 27 binary_part/3 (erts_bif_binary.c:1952 -> erts_build_sub_bitstring)
    # unconditionally materializes a slice whose size <= ERL_ONHEAP_BITS_LIMIT
    # (64 bytes) as a HEAP_BITSTRING (erl_bits.c); slices above the limit keep an
    # ErlSubBits referencing the parent refc Binary. The fixture therefore keeps
    # BOTH forms live with distinct, locatable process-dictionary keys:
    #   small_slice16 : a 16-byte slice that is a detached heap bitstring
    #                   (logical 16, NO chain to the 8000-byte refc);
    #   sub_binary100 : a 100-byte slice that stays a genuine sub-bits view
    #                   (referenced_byte_size == 8000) -> BinRef -> the 8000-byte
    #                   refc Binary.
    small_slice16 = binary_part(big_binary, 8, 16)
    sub_binary100 = binary_part(big_binary, 8, 100)

    # --- Closure / capture: the fun captures the bignum and the struct value ---
    maze_capture = fn x -> x + maze_bignum + fixture_struct.value end
    closure_ref = maze_capture.(1)

    # --- Process dictionary on the capturing (script) process ---
    Process.put(:maze_pdict, {:maze_pdict_value, 42, "dict"})

    # --- Named ETS table with known rows (tuple keys = first element) ---
    :ets.new(:maze_ets, [:named_table, :set, :public])
    :ets.insert(:maze_ets, {:maze_row_a, 1, "one"})
    :ets.insert(:maze_ets, {:maze_row_b, 2, "two"})
    :ets.insert(:maze_ets, {:maze_row_c, 3, maze_bignum})

    # --- Supervisor only; do NOT start a second MazeWorker (name collision) ---
    {:ok, _supervisor} = MazeSupervisor.start_link([])
    worker = Process.whereis(MazeWorker)

    # Suspend the worker so its mailbox is stable at capture time, then queue
    # two known messages (one carries the shared big_binary itself) and a long
    # timer that fires long after the core is captured.
    :sys.suspend(worker)
    send(worker, {:maze_message, "seed", 1234})
    send(worker, {:maze_shared_binary, big_binary})
    send(worker, {:maze_message, "second", maze_bignum})
    Process.send_after(worker, {:maze_timer_message, "late"}, 600_000)

    # --- persistent_term ground truth (Maze decodes key/value texts) ---
    # The big_binary itself and the captured closure itself are kept alive here
    # so Maze proves the shared refc Binary, the sub-binary and the closure,
    # not only derived result values.
    :persistent_term.put({:maze, :persistent}, %{
      struct: fixture_struct,
      map: big_map,
      tuple: maze_tuple,
      list: maze_list,
      bignum: maze_bignum,
      binary: big_binary,
      sub_binary: sub_binary100,
      closure: maze_capture,
      closure_result: closure_ref,
      atom: :elixir_fixture_sentinel
    })

    # Keep both views live on the fixture process heap with distinct keys so the
    # core contains BOTH the detached 16-byte slice (no referent chain) and the
    # 100-byte genuine sub-bits (with a referent chain to the shared refc Binary).
    Process.put(:maze_small_slice16_live, small_slice16)
    Process.put(:maze_sub_binary100_live, sub_binary100)

    # --- Queued mailbox on the script process (never read before capture) ---
    send(self(), {:maze_queued, "script-mailbox", maze_bignum})
    send(self(), {:maze_queued, "second", 7})

    # --- Timer / monitor / link ---
    Process.send_after(self(), :maze_timer_fired, 600_000)
    Process.monitor(worker)
    spawn_link(fn -> Process.sleep(600_000) end)

    # --- Ground-truth term for the capture log (inspect, not JSON) ---
    ground_truth =
      %{
        elixir_version: System.version(),
        build_info_otp: System.build_info()[:otp_release],
        erlang_otp: List.to_string(:erlang.system_info(:otp_release)),
        erts: List.to_string(:erlang.system_info(:version)),
        bignum: Integer.to_string(maze_bignum),
        binary_size: byte_size(big_binary),
        small_slice16_size: byte_size(small_slice16),
        small_slice16_referenced_size: :binary.referenced_byte_size(small_slice16),
        sub_binary100_size: byte_size(sub_binary100),
        sub_binary100_referenced_size: :binary.referenced_byte_size(sub_binary100),
        struct_name: fixture_struct.name,
        struct_value: fixture_struct.value,
        closure_result: closure_ref,
        atom: :elixir_fixture_sentinel,
        ets_rows: :ets.info(:maze_ets, :size),
        pdict: Process.get(:maze_pdict),
        process_count: :erlang.system_info(:process_count),
        atom_count: :erlang.system_info(:atom_count),
        elixir_system_loaded: Code.ensure_loaded?(Elixir.System),
        elixir_kernel_loaded: Code.ensure_loaded?(Elixir.Kernel),
        worker_pid: inspect(worker),
        supervisor_pid: inspect(Process.whereis(MazeSupervisor)),
        fixture_pid: inspect(self()),
        worker_mailbox_size: worker |> Process.info(:message_queue_len) |> elem(1),
        worker_link_count: worker |> Process.info(:links) |> elem(1) |> length(),
        fixture_mailbox_size: self() |> Process.info(:message_queue_len) |> elem(1),
        fixture_monitor_count: self() |> Process.info(:monitors) |> elem(1) |> length(),
        fixture_timer_set: true
      }

    # Persist a stable machine-readable ground truth when the capture harness
    # points MAZE_ELIXIR_GROUND_TRUTH at a file (all values are flat strings).
    case System.get_env("MAZE_ELIXIR_GROUND_TRUTH") do
      nil ->
        :ok

      path ->
        lines = [
          "elixir_version=#{ground_truth.elixir_version}",
          "build_info_otp=#{ground_truth.build_info_otp}",
          "erlang_otp=#{ground_truth.erlang_otp}",
          "erts=#{ground_truth.erts}",
          "bignum=#{ground_truth.bignum}",
          "binary_size=#{ground_truth.binary_size}",
          "small_slice16_size=#{ground_truth.small_slice16_size}",
          "small_slice16_referenced_size=#{ground_truth.small_slice16_referenced_size}",
          "sub_binary100_size=#{ground_truth.sub_binary100_size}",
          "sub_binary100_referenced_size=#{ground_truth.sub_binary100_referenced_size}",
          "struct_name=#{ground_truth.struct_name}",
          "struct_value=#{ground_truth.struct_value}",
          "closure_result=#{ground_truth.closure_result}",
          "atom=#{ground_truth.atom}",
          "ets_rows=#{ground_truth.ets_rows}",
          "process_count=#{ground_truth.process_count}",
          "atom_count=#{ground_truth.atom_count}",
          "elixir_system_loaded=#{ground_truth.elixir_system_loaded}",
          "elixir_kernel_loaded=#{ground_truth.elixir_kernel_loaded}",
          "worker_pid=#{ground_truth.worker_pid}",
          "supervisor_pid=#{ground_truth.supervisor_pid}",
          "fixture_pid=#{ground_truth.fixture_pid}",
          "worker_mailbox_size=#{ground_truth.worker_mailbox_size}",
          "worker_link_count=#{ground_truth.worker_link_count}",
          "fixture_mailbox_size=#{ground_truth.fixture_mailbox_size}",
          "fixture_monitor_count=#{ground_truth.fixture_monitor_count}",
          "fixture_timer_set=#{ground_truth.fixture_timer_set}"
        ]

        File.write!(path, Enum.join(lines, "\n") <> "\n")
    end

    IO.puts(
      "MAZE_ELIXIR_GROUND_TRUTH=" <>
        inspect(ground_truth, limit: :infinity, printable_limit: :infinity)
    )

    IO.puts("READY FOR GCORE")
    # Keep the VM alive; the capture script gcores the PID shortly after READY.
    Process.sleep(600_000)
  end
end

MazeElixirFixture.run()
