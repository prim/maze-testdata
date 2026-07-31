io.stdout:setvbuf("no")

local runtime_dir = os.getenv("MESSIAH_RUNTIME_DIR")
assert(runtime_dir and runtime_dir ~= "", "MESSIAH_RUNTIME_DIR is required")
package.cpath = runtime_dir .. "/?.so;" .. package.cpath

local asiocore = require("asiocore")

local function ready(class_value)
    class_ready(class_value)
    return class_value
end

local function map_class(name, properties, value_type)
    local class_value = class(name, asiocore.area_map)
    class_value.__property_all__ = properties or dict()
    class_value.__property_flag__ = dict()
    if value_type ~= nil then
        class_value.VALUE_TYPE = value_type
    end
    return ready(class_value)
end

local function list_class(name, value_type)
    local class_value = class(name, asiocore.area_list)
    class_value.__property_all__ = dict()
    class_value.__property_flag__ = dict()
    class_value.VALUE_TYPE = value_type
    return ready(class_value)
end

local schema_holders = {}
local function build_schema_index(name, class_value)
    local holder_name = name .. "SchemaHolder"
    local holder = class(holder_name, asiocore.entity)
    asiocore.regist_class(holder_name, holder)
    ready(holder)
    asiocore.set_prop_index(holder, class_value)
    schema_holders[#schema_holders + 1] = holder
    return holder
end

local IntList = list_class("FixtureIntList", "int")
local FloatList = list_class("FixtureFloatList", "float")
local StringList = list_class("FixtureStringList", "str")
local CustomListType = list_class("CustomListType", "None")
local CustomFloatListType = list_class("CustomFloatListType", "float")
local CustomMapType = map_class("CustomMapType", nil, "None")
local CustomIntMapType = map_class("CustomIntMapType", nil, "int")

local Stats = map_class("FixtureStats", dict(
    health=0,
    mana=0,
    speed=0.0,
    title="",
    alive=false,
    checkpoints=IntList,
    samples=FloatList,
    labels=CustomMapType,
    history=CustomListType
))

local Modifier = map_class("FixtureModifier", dict(
    kind="",
    amount=0.0,
    enabled=false
))

local ModifierList = list_class("FixtureModifierList", Modifier)

local Item = map_class("FixtureItem", dict(
    item_id=0,
    name="",
    count=0,
    weight=0.0,
    bound=false,
    modifiers=ModifierList,
    attributes=CustomMapType
))

local Inventory = list_class("FixtureInventory", Item)

local PlayerProperties = map_class("FixturePlayerProperties", dict(
    guid=0,
    name="",
    level=0,
    online=false,
    rating=0.0,
    stats=Stats,
    inventory=Inventory,
    tags=StringList,
    counters=CustomIntMapType,
    state=CustomMapType,
    events=CustomListType,
    position=CustomFloatListType
))

local NpcProperties = map_class("FixtureNpcProperties", dict(
    guid=0,
    template_id=0,
    name="",
    hostile=false,
    aggro_radius=0.0,
    stats=Stats,
    loot=Inventory,
    blackboard=CustomMapType,
    patrol=CustomFloatListType,
    decisions=CustomListType
))

local OnlineNested = map_class("FixtureOnlineNested", dict(
    score=0,
    note="",
    active=false
))

local OnlineNumbers = list_class("FixtureOnlineNumbers", "int")

local OnlineProperties = map_class("FixtureOnlineProperties", dict(
    guid=0,
    health=0,
    name="",
    enabled=false,
    nested=OnlineNested,
    values=OnlineNumbers,
    metadata=CustomMapType
))

build_schema_index("FixtureStats", Stats)
build_schema_index("FixtureModifier", Modifier)
build_schema_index("FixtureItem", Item)

local PlayerEntity = ready(class("FixturePlayerEntity", asiocore.entity))
local NpcEntity = ready(class("FixtureNpcEntity", asiocore.entity))
local OnlineEntity = ready(class("FixtureOnlineEntity", asiocore.entity))
asiocore.regist_class("FixturePlayerEntity", PlayerEntity)
asiocore.regist_class("FixtureNpcEntity", NpcEntity)
asiocore.regist_class("FixtureOnlineEntity", OnlineEntity)
asiocore.set_prop_index(PlayerEntity, PlayerProperties)
asiocore.set_prop_index(NpcEntity, NpcProperties)
asiocore.set_prop_index(OnlineEntity, OnlineProperties)

local OnlineArea = ready(class("FixtureOnlineArea", asiocore.area))
local WorldSpace = ready(class("FixtureWorldSpace", asiocore.space))

local function verify_list_property_boundary()
    local ListWithProps = class("ProbeListWithProps", asiocore.area_list)
    ListWithProps.VALUE_TYPE = "int"
    ListWithProps.__property_all__ = dict(label="", count=0)
    ListWithProps.__property_flag__ = dict()
    ready(ListWithProps)

    local Root = map_class("ProbeListPropertyRoot", dict(items=ListWithProps))
    local holder = build_schema_index("ProbeListPropertyRoot", Root)
    local root = Root()

    assert(root.items.label == nil, "area_list unexpectedly materialized fixed label prop")
    assert(root.items.count == nil, "area_list unexpectedly materialized fixed count prop")
    assert(tostring(root.items:debug_get_prop_types()) == "[]",
        "area_list fixed props unexpectedly entered native schema")

    root.items:append(7)
    root.items.label = "runtime-only"
    root.items.count = 1
    assert(root.items[1] == 7 and root.items.label == "runtime-only" and root.items.count == 1)
    assert(tostring(root.items:debug_get_prop_types()) == "[Simple Int]")
    print("List fixed property boundary: PASS")
    return holder, root
end

local list_boundary_holder, list_boundary_root = verify_list_property_boundary()

local function make_modifier(seed, index)
    local value = Modifier()
    value.kind = "modifier-" .. index
    value.amount = seed * 0.01 + index * 0.1
    value.enabled = index % 2 == 0
    return value
end

local function make_item(seed, index)
    local value = Item()
    value.item_id = seed * 100 + index
    value.name = "item-" .. seed .. "-" .. index
    value.count = index + 1
    value.weight = index * 1.25
    value.bound = index % 2 == 1
    value.modifiers:append(make_modifier(seed, 1))
    value.modifiers:append(make_modifier(seed, 2))
    value.attributes["quality"] = index + 3
    value.attributes["source"] = "fixture"
    return value
end

local function fill_stats(value, seed)
    value.health = 1000 + seed
    value.mana = 250 + seed
    value.speed = 5.5 + seed * 0.01
    value.title = "unit-" .. seed
    value.alive = seed % 3 ~= 0
    value.checkpoints:append(seed)
    value.checkpoints:append(seed + 10)
    value.samples:append(seed * 0.5)
    value.samples:append(seed * 0.75)
    value.labels["region"] = "west"
    value.labels["tier"] = seed % 5
    value.history:append("spawn")
    value.history:append(seed)
end

local function make_player(seed)
    local props = PlayerProperties()
    props.guid = 100000 + seed
    props.name = "player-" .. seed
    props.level = 20 + seed % 60
    props.online = seed % 2 == 0
    props.rating = 1000.0 + seed * 1.5
    fill_stats(props.stats, seed)
    props.inventory:append(make_item(seed, 1))
    props.inventory:append(make_item(seed, 2))
    props.tags:append("player")
    props.tags:append("fixture")
    props.counters["wins"] = seed % 17
    props.counters["losses"] = seed % 9
    props.state["mode"] = "active"
    props.state["sequence"] = seed
    props.events:append("login")
    props.events:append(seed)
    props.position:append(seed * 1.0)
    props.position:append(seed * 2.0)
    props.position:append(seed * -0.5)

    local entity = PlayerEntity()
    entity.props = props
    entity.fixture_kind = "player"
    return entity, props
end

local function make_npc(seed)
    local props = NpcProperties()
    props.guid = 200000 + seed
    props.template_id = 7000 + seed % 11
    props.name = "npc-" .. seed
    props.hostile = seed % 2 == 1
    props.aggro_radius = 8.0 + seed * 0.02
    fill_stats(props.stats, seed + 1000)
    props.loot:append(make_item(seed + 1000, 1))
    props.blackboard["target"] = seed * 3
    props.blackboard["state"] = "patrol"
    props.patrol:append(seed * 1.25)
    props.patrol:append(seed * 2.5)
    props.decisions:append("idle")
    props.decisions:append("move")

    local entity = NpcEntity()
    entity.props = props
    entity.fixture_kind = "npc"
    return entity, props
end

local fixture = {
    players = {},
    player_properties = {},
    npcs = {},
    npc_properties = {},
    plain_maps = {},
    plain_lists = {},
    online_entities = {},
    online_areas = {},
    online_properties = {},
    schema_holders = schema_holders,
    list_boundary_holder = list_boundary_holder,
    list_boundary_root = list_boundary_root,
}

for index = 1, 96 do
    local entity, props = make_player(index)
    fixture.players[index] = entity
    fixture.player_properties[index] = props
end

for index = 1, 64 do
    local entity, props = make_npc(index)
    fixture.npcs[index] = entity
    fixture.npc_properties[index] = props
end

for index = 1, 32 do
    local plain_map = asiocore.area_map()
    local plain_list = asiocore.area_list()
    plain_map["index"] = index
    plain_map["enabled"] = index % 2 == 0
    plain_list:append(index)
    plain_list:append("plain")
    fixture.plain_maps[index] = plain_map
    fixture.plain_lists[index] = plain_list
end

fixture.world_holder = fixture.players[1]
fixture.world_space = WorldSpace("fixture-world", 1001, fixture.world_holder, dict())

for index = 1, 16 do
    local entity = OnlineEntity()
    local area = OnlineArea("FixtureOnlineEntity", false, entity, 0)
    entity:set_area(area)
    area:set_space("fixture-world")

    local props = area:prop()
    props.guid = 300000 + index
    props.health = 5000 + index
    props.name = "online-" .. index
    props.enabled = index % 2 == 0
    props.nested.score = index * 10
    props.nested.note = "owned-" .. index
    props.nested.active = true
    props.values:append(index)
    props.values:append(index * 2)
    props.metadata["shard"] = index % 4
    props.metadata["source"] = "area_impl"

    assert(area:owner() == entity, "online area owner mismatch")
    assert(entity:get_area() == area, "online entity area link mismatch")
    assert(area:get_space() == "fixture-world", "online area space link mismatch")
    assert(entity.health == props.health, "entity.mimpl_ scalar read mismatch")
    assert(entity.nested == props.nested, "entity.mimpl_ nested map read mismatch")
    assert(entity.values == props.values, "entity.mimpl_ nested list read mismatch")
    assert(entity.metadata == props.metadata, "entity.mimpl_ generic map read mismatch")

    fixture.online_entities[index] = entity
    fixture.online_areas[index] = area
    fixture.online_properties[index] = props
end

_G.MESSIAH_FIXTURE = fixture

local sample = fixture.player_properties[1]
print("Lua version: " .. _VERSION)
print("Fixture entities: players=" .. #fixture.players .. " npcs=" .. #fixture.npcs)
print("Fixture root properties: players=" .. #fixture.player_properties .. " npcs=" .. #fixture.npc_properties)
print("Fixture online ownership: entities=" .. #fixture.online_entities ..
    " areas=" .. #fixture.online_areas .. " space=" .. tostring(fixture.world_space))
print("Fixture nested paths:", tostring(sample.stats:path()), tostring(sample.inventory:path()),
    tostring(sample.inventory[1]:path()), tostring(sample.inventory[1].modifiers:path()),
    tostring(sample.state:path()), tostring(sample.events:path()))
print("Fixture root types:", tostring(sample:debug_get_prop_types()))
print("Fixture stats types:", tostring(sample.stats:debug_get_prop_types()))
print("Fixture item types:", tostring(sample.inventory[1]:debug_get_prop_types()))
print("READY FOR GCORE")

while true do
    os.execute("sleep 3600")
end
