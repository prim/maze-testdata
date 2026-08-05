#include "erl_nif.h"

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define ACTIVE_ENVIRONMENTS 3
#define ENV_BINARY_BYTES (256 * 1024)
#define HEAP_LIST_CELLS 50000
#define IOLIST_BYTES 4096

typedef struct {
    uint64_t marker;
    uint64_t slot;
} fixture_resource;

typedef struct {
    ErlNifResourceType *resource_type;
    ErlNifEnv *independent_env;
    ERL_NIF_TERM independent_root;
    void *active_envs[ACTIVE_ENVIRONMENTS];
    void *resource_data[2];
    void *native_allocation;
    int active_count;
    int truth_written;
    int release;
} fixture_state;

static void resource_dtor(ErlNifEnv *env, void *object) {
    (void)env;
    (void)object;
}

static void resource_down(ErlNifEnv *env, void *object,
                          ErlNifPid *pid, ErlNifMonitor *monitor) {
    (void)env;
    (void)object;
    (void)pid;
    (void)monitor;
}

static ErlNifResourceTypeInit resource_type_init = {
    resource_dtor,
    NULL,
    resource_down,
    0,
    NULL,
};

static ERL_NIF_TERM pointer_term(ErlNifEnv *env, const void *pointer) {
    return enif_make_uint64(env, (ErlNifUInt64)(uintptr_t)pointer);
}

static int build_environment_payload(ErlNifEnv *env, ERL_NIF_TERM shared,
                                     ERL_NIF_TERM *result) {
    ERL_NIF_TERM iolist = enif_make_list(env, 0);
    ERL_NIF_TERM list = enif_make_list(env, 0);
    ERL_NIF_TERM owned_binary;
    ErlNifBinary temporary_binary;
    unsigned char *bytes;
    int index;

    for (index = 0; index < IOLIST_BYTES; index++) {
        iolist = enif_make_list_cell(env, enif_make_uint(env, index & 0xff), iolist);
    }
    if (!enif_inspect_iolist_as_binary(env, iolist, &temporary_binary) ||
        temporary_binary.size != IOLIST_BYTES) {
        return 0;
    }

    for (index = 0; index < HEAP_LIST_CELLS; index++) {
        list = enif_make_list_cell(env, enif_make_uint(env, index), list);
    }

    bytes = enif_make_new_binary(env, ENV_BINARY_BYTES, &owned_binary);
    if (bytes == NULL) {
        return 0;
    }
    memset(bytes, 0xa5, ENV_BINARY_BYTES);

    *result = enif_make_tuple4(
        env,
        enif_make_atom(env, "maze_nif_environment_root"),
        list,
        owned_binary,
        enif_make_tuple2(env, iolist, enif_make_copy(env, shared)));
    return 1;
}

static void write_ground_truth(fixture_state *state) {
    const char *path = getenv("MAZE_ERLANG_GROUND_TRUTH");
    FILE *output;

    if (path == NULL ||
        __atomic_exchange_n(&state->truth_written, 1, __ATOMIC_ACQ_REL)) {
        return;
    }
    output = fopen(path, "w");
    if (output == NULL) {
        return;
    }
    fprintf(output,
            "os_pid=%ld\n"
            "normal_env=%llu\n"
            "dirty_cpu_env=%llu\n"
            "dirty_io_env=%llu\n"
            "independent_env=%llu\n"
            "resource_type=%llu\n"
            "resource1_data=%llu\n"
            "resource2_data=%llu\n"
            "native_allocation=%llu\n"
            "shared_binary_bytes=%u\n"
            "environment_binary_bytes=%u\n",
            (long)getpid(),
            (unsigned long long)(uintptr_t)state->active_envs[0],
            (unsigned long long)(uintptr_t)state->active_envs[1],
            (unsigned long long)(uintptr_t)state->active_envs[2],
            (unsigned long long)(uintptr_t)state->independent_env,
            (unsigned long long)(uintptr_t)state->resource_type,
            (unsigned long long)(uintptr_t)state->resource_data[0],
            (unsigned long long)(uintptr_t)state->resource_data[1],
            (unsigned long long)(uintptr_t)state->native_allocation,
            1048576U, ENV_BINARY_BYTES);
    fclose(output);
    fprintf(stderr, "READY FOR GCORE MAZE_ERLANG_NIF_FIXTURE_NATIVE_READY os_pid=%ld truth=%s\n",
            (long)getpid(), path);
    fflush(stderr);
}

static ERL_NIF_TERM block_environment(ErlNifEnv *env, int argc,
                                      const ERL_NIF_TERM argv[], int slot) {
    fixture_state *state = enif_priv_data(env);
    ERL_NIF_TERM root;
    volatile ERL_NIF_TERM keep;

    if (argc != 1 || slot < 0 || slot >= ACTIVE_ENVIRONMENTS ||
        !build_environment_payload(env, argv[0], &root)) {
        return enif_make_badarg(env);
    }
    keep = root;
    __atomic_store_n(&state->active_envs[slot], env, __ATOMIC_RELEASE);
    if (__atomic_add_fetch(&state->active_count, 1, __ATOMIC_ACQ_REL) ==
        ACTIVE_ENVIRONMENTS) {
        write_ground_truth(state);
    }
    while (!__atomic_load_n(&state->release, __ATOMIC_ACQUIRE)) {
        if (keep == 0) {
            return enif_make_badarg(env);
        }
        usleep(10000);
    }
    return (ERL_NIF_TERM)keep;
}

static ERL_NIF_TERM block_normal(ErlNifEnv *env, int argc,
                                 const ERL_NIF_TERM argv[]) {
    return block_environment(env, argc, argv, 0);
}

static ERL_NIF_TERM block_dirty_cpu(ErlNifEnv *env, int argc,
                                    const ERL_NIF_TERM argv[]) {
    return block_environment(env, argc, argv, 1);
}

static ERL_NIF_TERM block_dirty_io(ErlNifEnv *env, int argc,
                                   const ERL_NIF_TERM argv[]) {
    return block_environment(env, argc, argv, 2);
}

static ERL_NIF_TERM make_resource(ErlNifEnv *env, int argc,
                                  const ERL_NIF_TERM argv[]) {
    fixture_state *state = enif_priv_data(env);
    fixture_resource *resource;
    ErlNifPid target;
    ErlNifMonitor monitor;
    ERL_NIF_TERM term;
    int monitor_target;
    int slot;

    if (argc != 3 || !enif_get_local_pid(env, argv[0], &target) ||
        !enif_get_int(env, argv[1], &slot) || slot < 0 || slot >= 2 ||
        !enif_get_int(env, argv[2], &monitor_target)) {
        return enif_make_badarg(env);
    }
    resource = enif_alloc_resource(state->resource_type, sizeof(*resource));
    if (resource == NULL) {
        return enif_make_badarg(env);
    }
    resource->marker = UINT64_C(0x4d415a454e494652);
    resource->slot = (uint64_t)slot;
    if (monitor_target && enif_monitor_process(env, resource, &target, &monitor) != 0) {
        enif_release_resource(resource);
        return enif_make_badarg(env);
    }
    term = enif_make_resource(env, resource);
    __atomic_store_n(&state->resource_data[slot], resource, __ATOMIC_RELEASE);
    enif_release_resource(resource);
    return enif_make_tuple3(env, term, pointer_term(env, resource),
                            pointer_term(env, state->resource_type));
}

static ERL_NIF_TERM stats(ErlNifEnv *env, int argc,
                          const ERL_NIF_TERM argv[]) {
    fixture_state *state = enif_priv_data(env);
    ERL_NIF_TERM values[10];
    (void)argv;
    if (argc != 0) {
        return enif_make_badarg(env);
    }
    values[0] = enif_make_int(
        env, __atomic_load_n(&state->active_count, __ATOMIC_ACQUIRE));
    values[1] = pointer_term(
        env, __atomic_load_n(&state->active_envs[0], __ATOMIC_ACQUIRE));
    values[2] = pointer_term(
        env, __atomic_load_n(&state->active_envs[1], __ATOMIC_ACQUIRE));
    values[3] = pointer_term(
        env, __atomic_load_n(&state->active_envs[2], __ATOMIC_ACQUIRE));
    values[4] = pointer_term(env, state->independent_env);
    values[5] = pointer_term(env, state->resource_type);
    values[6] = pointer_term(
        env, __atomic_load_n(&state->resource_data[0], __ATOMIC_ACQUIRE));
    values[7] = pointer_term(
        env, __atomic_load_n(&state->resource_data[1], __ATOMIC_ACQUIRE));
    values[8] = pointer_term(env, state->native_allocation);
    values[9] = enif_make_uint(env, ENV_BINARY_BYTES);
    return enif_make_tuple_from_array(env, values, 10);
}

static int load(ErlNifEnv *env, void **private_data, ERL_NIF_TERM load_info) {
    fixture_state *state;
    ERL_NIF_TERM nil;
    (void)load_info;

    state = enif_alloc(sizeof(*state));
    if (state == NULL) {
        return -1;
    }
    memset(state, 0, sizeof(*state));
    state->resource_type = enif_open_resource_type_x(
        env, "maze_nif_resource_fixture.resource", &resource_type_init,
        ERL_NIF_RT_CREATE, NULL);
    state->independent_env = enif_alloc_env();
    state->native_allocation = enif_alloc(12345);
    if (state->resource_type == NULL || state->independent_env == NULL ||
        state->native_allocation == NULL) {
        return -1;
    }
    memset(state->native_allocation, 0x5a, 12345);
    nil = enif_make_list(state->independent_env, 0);
    if (!build_environment_payload(state->independent_env, nil,
                                   &state->independent_root)) {
        return -1;
    }
    *private_data = state;
    return 0;
}

static void unload(ErlNifEnv *env, void *private_data) {
    fixture_state *state = private_data;
    (void)env;
    if (state == NULL) {
        return;
    }
    if (state->independent_env != NULL) {
        enif_free_env(state->independent_env);
    }
    if (state->native_allocation != NULL) {
        enif_free(state->native_allocation);
    }
    enif_free(state);
}

static ErlNifFunc functions[] = {
    {"block_normal", 1, block_normal, 0},
    {"block_dirty_cpu", 1, block_dirty_cpu, ERL_NIF_DIRTY_JOB_CPU_BOUND},
    {"block_dirty_io", 1, block_dirty_io, ERL_NIF_DIRTY_JOB_IO_BOUND},
    {"make_resource", 3, make_resource, 0},
    {"stats", 0, stats, 0},
};

ERL_NIF_INIT(maze_nif_resource_fixture, functions, load, NULL, NULL, unload)
