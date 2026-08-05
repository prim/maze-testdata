-module(maze_scheduler_active_fixture).
-export([start/0]).

start() ->
    process_flag(trap_exit, true),
    Workers = [spawn_link(fun() -> burn(Index, Index + 1) end)
               || Index <- lists:seq(1, 8)],
    GroundTruth =
        #{os_pid => list_to_integer(os:getpid()),
          otp_release => list_to_binary(erlang:system_info(otp_release)),
          erts_version => list_to_binary(erlang:system_info(version)),
          schedulers => erlang:system_info(schedulers),
          schedulers_online => erlang:system_info(schedulers_online),
          dirty_cpu_schedulers => erlang:system_info(dirty_cpu_schedulers),
          dirty_io_schedulers => erlang:system_info(dirty_io_schedulers),
          workers => [list_to_binary(pid_to_list(Pid)) || Pid <- Workers]},
    Path = os:getenv("MAZE_ERLANG_GROUND_TRUTH"),
    ok = file:write_file(Path, io_lib:format("~p.~n", [GroundTruth])),
    io:format("READY FOR GCORE MAZE_ERLANG_SCHEDULER_FIXTURE_READY os_pid=~s workers=~p ground_truth=~s~n",
              [os:getpid(), Workers, Path]),
    receive
        stop -> ok;
        {'EXIT', _Pid, Reason} -> exit(Reason)
    end.

burn(Salt, Value) ->
    Next = ((Value * 1664525) bxor (Value bsr 7) bxor Salt) band 16#3fffffff,
    burn(Salt, Next).
