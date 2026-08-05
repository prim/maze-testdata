-module(maze_nif_resource_fixture).
-on_load(init/0).
-export([start/0, block_normal/1, block_dirty_cpu/1, block_dirty_io/1,
         make_resource/3, stats/0]).

-define(SHARED_BINARY_BYTES, 1048576).

init() ->
    Library = os:getenv("MAZE_NIF_LIBRARY"),
    erlang:load_nif(Library, 0).

block_normal(_Binary) ->
    erlang:nif_error(nif_not_loaded).

block_dirty_cpu(_Binary) ->
    erlang:nif_error(nif_not_loaded).

block_dirty_io(_Binary) ->
    erlang:nif_error(nif_not_loaded).

make_resource(_Target, _Slot, _Monitor) ->
    erlang:nif_error(nif_not_loaded).

stats() ->
    erlang:nif_error(nif_not_loaded).

start() ->
    process_flag(trap_exit, true),
    process_flag(scheduler, 4),
    Target = spawn(fun holder/0),
    {Resource1, Resource1Data, ResourceType} = make_resource(Target, 0, 1),
    {Resource2, Resource2Data, ResourceType} = make_resource(Target, 1, 0),
    SharedBinary = binary:copy(<<16#b6>>, ?SHARED_BINARY_BYTES),
    DirtyCPU = spawn_opt(fun() -> block_dirty_cpu(SharedBinary) end,
                         [link, {scheduler, 2}]),
    DirtyIO = spawn_opt(fun() -> block_dirty_io(SharedBinary) end,
                        [link, {scheduler, 3}]),
    _ = wait_count(2, 2000),
    Normal = spawn_opt(fun() -> block_normal(SharedBinary) end,
                       [link, {scheduler, 1}]),
    Stats = wait_count(3, 2000),
    {3, NormalEnv, DirtyCPUEnv, DirtyIOEnv, IndependentEnv,
     ResourceType, Resource1Data, Resource2Data, NativeAllocation,
     EnvironmentBinaryBytes} = Stats,
    GroundTruth =
        io_lib:format(
          "os_pid=~s~n"
          "otp_release=~s~n"
          "erts_version=~s~n"
          "normal_pid=~p~n"
          "dirty_cpu_pid=~p~n"
          "dirty_io_pid=~p~n"
          "target_pid=~p~n"
          "normal_env=~p~n"
          "dirty_cpu_env=~p~n"
          "dirty_io_env=~p~n"
          "independent_env=~p~n"
          "resource_type=~p~n"
          "resource1_data=~p~n"
          "resource2_data=~p~n"
          "native_allocation=~p~n"
          "shared_binary_bytes=~p~n"
          "environment_binary_bytes=~p~n",
          [os:getpid(), erlang:system_info(otp_release),
           erlang:system_info(version), Normal, DirtyCPU, DirtyIO, Target,
           NormalEnv, DirtyCPUEnv, DirtyIOEnv, IndependentEnv, ResourceType,
           Resource1Data, Resource2Data, NativeAllocation,
           byte_size(SharedBinary), EnvironmentBinaryBytes]),
    Path = os:getenv("MAZE_ERLANG_GROUND_TRUTH"),
    ok = file:write_file(Path, GroundTruth),
    io:format("READY FOR GCORE MAZE_ERLANG_NIF_FIXTURE_READY os_pid=~s normal=~p "
              "dirty_cpu=~p dirty_io=~p ground_truth=~s~n",
              [os:getpid(), Normal, DirtyCPU, DirtyIO, Path]),
    keep_alive({Target, Resource1, Resource2, SharedBinary,
                Normal, DirtyCPU, DirtyIO, Stats}).

wait_count(_Count, 0) ->
    erlang:error(nif_fixture_timeout);
wait_count(Count, Attempts) ->
    Ready = stats(),
    case element(1, Ready) of
        Count -> Ready;
        _Other ->
            timer:sleep(10),
            wait_count(Count, Attempts - 1)
    end.

holder() ->
    receive
        stop -> ok
    after 60000 ->
        holder()
    end.

keep_alive(State) ->
    receive
        stop -> ok
    after 60000 ->
        keep_alive(State)
    end.
