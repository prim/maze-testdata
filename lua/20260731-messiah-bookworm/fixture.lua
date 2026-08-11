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

-- Mirrors the object/container matrix in python/20260129-complex-types-311,
-- using only schemas accepted by the production H72 property runtime.
local ComplexLeaf = map_class("FixtureComplexLeaf", dict(
    leaf_id=0,
    name="",
    score=0.0,
    active=false,
    tags=StringList,
    metadata=CustomMapType
))

local ComplexLeafList = list_class("FixtureComplexLeafList", ComplexLeaf)
local ComplexLeafMap = map_class("FixtureComplexLeafMap", nil, ComplexLeaf)
local ComplexListMatrix = list_class("FixtureComplexListMatrix", IntList)

local ComplexTreeLeaf = map_class("FixtureComplexTreeLeaf", dict(
    value=0,
    label=""
))

local ComplexTreeBranch = map_class("FixtureComplexTreeBranch", dict(
    value=0,
    label="",
    left=ComplexTreeLeaf,
    right=ComplexTreeLeaf
))

local ComplexTreeRoot = map_class("FixtureComplexTreeRoot", dict(
    value=0,
    label="",
    left=ComplexTreeBranch,
    right=ComplexTreeBranch
))

local ComplexProperties = map_class("FixtureComplexProperties", dict(
    serial=0,
    name="",
    enabled=false,
    ratio=0.0,
    short_text="",
    long_text="",
    unicode_text="",
    empty_map=CustomMapType,
    single_map=CustomMapType,
    mixed_map=CustomMapType,
    nested_map=CustomMapType,
    growth_map=CustomMapType,
    empty_list=CustomListType,
    single_list=CustomListType,
    mixed_list=CustomListType,
    nested_lists=CustomListType,
    growth_list=CustomListType,
    matrix=ComplexListMatrix,
    leaves=ComplexLeafList,
    leaf_lookup=ComplexLeafMap,
    tree=ComplexTreeRoot
))

-- H72 equivalents of the PropObj/PropDict/PropList combinations documented
-- in dev-log/2026-08-11-y2-server-property-usage.md.
local Y2Stat = map_class("FixtureY2Stat", dict(
    health=0,
    attack_power=0,
    label=""
))

local Y2IntMap = map_class("FixtureY2IntMap", nil, "int")
local Y2IntList = list_class("FixtureY2IntList", "int")

local Y2ObjNest = map_class("FixtureY2ObjNest", dict(
    stat=Y2Stat,
    bonuses=Y2IntMap,
    history=Y2IntList
))

local Y2ObjDict = map_class("FixtureY2ObjDict", nil, Y2Stat)
local Y2DictDict = map_class("FixtureY2DictDict", nil, Y2IntMap)
local Y2ListDict = map_class("FixtureY2ListDict", nil, Y2IntList)
local Y2ObjList = list_class("FixtureY2ObjList", Y2Stat)
local Y2DictList = list_class("FixtureY2DictList", Y2IntMap)
local Y2ListList = list_class("FixtureY2ListList", Y2IntList)

local Y2Equip = map_class("FixtureY2Equip", dict(
    equip_id=0,
    level=1,
    locked=false,
    name="",
    attributes=CustomMapType
))

local Y2EquipDict = map_class("FixtureY2EquipDict", nil, Y2Equip)

local Y2FormationItem = map_class("FixtureY2FormationItem", dict(
    member_id=0,
    slot=0,
    unit_id=0,
    active=false,
    label=""
))

local Y2Formation = map_class("FixtureY2Formation", nil, Y2FormationItem)

local Y2FormationInfo = map_class("FixtureY2FormationInfo", dict(
    name="",
    content=Y2Formation,
    history=Y2IntList
))

local Y2FormationDict = map_class("FixtureY2FormationDict", nil, Y2FormationInfo)

local Y2BaseRecord = map_class("FixtureY2BaseRecord", dict(
    record_id=0,
    created_at=0,
    label=""
))

local Y2DerivedRecord = class("FixtureY2DerivedRecord", Y2BaseRecord)
-- The minimal H72 runtime has no y2 AvatMeta, so spell out the merged schema.
Y2DerivedRecord.__property_all__ = dict(
    record_id=0,
    created_at=0,
    label="",
    revision=0,
    state=""
)
Y2DerivedRecord.__property_flag__ = dict()
ready(Y2DerivedRecord)
local Y2DerivedRecordList = list_class("FixtureY2DerivedRecordList", Y2DerivedRecord)

local Y2Properties = map_class("FixtureY2Properties", dict(
    userid=0,
    level=1,
    remain_exp=0,
    head_url="config_0",
    online=false,
    rating=0.0,
    obj_nest=Y2ObjNest,
    obj_dict=Y2ObjDict,
    dict_dict=Y2DictDict,
    list_dict=Y2ListDict,
    obj_list=Y2ObjList,
    dict_list=Y2DictList,
    list_list=Y2ListList,
    equips=Y2EquipDict,
    formations=Y2FormationDict,
    reviewed_sections=Y2IntList,
    extensions=CustomMapType,
    records=Y2DerivedRecordList
))

build_schema_index("FixtureStats", Stats)
build_schema_index("FixtureModifier", Modifier)
build_schema_index("FixtureItem", Item)
build_schema_index("FixtureComplexLeaf", ComplexLeaf)
build_schema_index("FixtureComplexTreeLeaf", ComplexTreeLeaf)
build_schema_index("FixtureComplexTreeBranch", ComplexTreeBranch)
build_schema_index("FixtureComplexTreeRoot", ComplexTreeRoot)
build_schema_index("FixtureY2Stat", Y2Stat)
build_schema_index("FixtureY2ObjNest", Y2ObjNest)
build_schema_index("FixtureY2Equip", Y2Equip)
build_schema_index("FixtureY2FormationItem", Y2FormationItem)
build_schema_index("FixtureY2FormationInfo", Y2FormationInfo)
build_schema_index("FixtureY2BaseRecord", Y2BaseRecord)
build_schema_index("FixtureY2DerivedRecord", Y2DerivedRecord)

local PlayerEntity = ready(class("FixturePlayerEntity", asiocore.entity))
local NpcEntity = ready(class("FixtureNpcEntity", asiocore.entity))
local OnlineEntity = ready(class("FixtureOnlineEntity", asiocore.entity))
local ComplexEntity = ready(class("FixtureComplexEntity", asiocore.entity))
local Y2Entity = ready(class("FixtureY2Entity", asiocore.entity))
asiocore.regist_class("FixturePlayerEntity", PlayerEntity)
asiocore.regist_class("FixtureNpcEntity", NpcEntity)
asiocore.regist_class("FixtureOnlineEntity", OnlineEntity)
asiocore.regist_class("FixtureComplexEntity", ComplexEntity)
asiocore.regist_class("FixtureY2Entity", Y2Entity)
asiocore.set_prop_index(PlayerEntity, PlayerProperties)
asiocore.set_prop_index(NpcEntity, NpcProperties)
asiocore.set_prop_index(OnlineEntity, OnlineProperties)
asiocore.set_prop_index(ComplexEntity, ComplexProperties)
asiocore.set_prop_index(Y2Entity, Y2Properties)

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

local function make_complex_leaf(seed, label)
    local value = ComplexLeaf()
    value.leaf_id = seed
    value.name = label
    value.score = seed * 0.125
    value.active = seed % 2 == 0
    value.tags:append("complex")
    value.tags:append(label)
    value.metadata["seed"] = seed
    value.metadata["unicode"] = "属性-" .. seed
    return value
end

local function fill_tree_node(value, seed, label)
    value.value = seed
    value.label = label
end

local function make_complex(seed)
    local props = ComplexProperties()
    props.serial = 400000 + seed
    props.name = "complex-" .. seed
    props.enabled = seed % 2 == 0
    props.ratio = seed * 1.25
    props.short_text = "s" .. seed
    props.long_text = "long-" .. seed .. "-" .. string.rep("x", 1024)
    props.unicode_text = "中文字符串-你好世界-" .. seed

    props.single_map["only"] = seed
    props.mixed_map["integer"] = seed
    props.mixed_map["float"] = seed + 0.5
    props.mixed_map["string"] = "mixed-" .. seed
    props.mixed_map["boolean"] = seed % 2 == 0

    local level3 = CustomMapType()
    level3["answer"] = seed * 42
    level3["label"] = "level-3"
    local level2 = CustomMapType()
    level2["level3"] = level3
    local level1 = CustomMapType()
    level1["level2"] = level2
    props.nested_map["level1"] = level1

    for index = 1, 160 do
        props.growth_map["key-" .. index] = seed * 1000 + index
        props.growth_list:append(seed * 1000 + index)
    end
    props.growth_map["replace"] = "before"
    props.growth_map["replace"] = "after"
    props.growth_map["deleted"] = seed
    props.growth_map:pop("deleted")
    assert(props.growth_map["replace"] == "after", "complex map overwrite failed")
    assert(props.growth_map["deleted"] == nil, "complex map pop failed")

    props.growth_list:append("remove-me")
    props.growth_list:remove("remove-me")
    assert(#props.growth_list == 160, "complex list remove failed")

    props.single_list:append(seed)
    props.mixed_list:append(seed)
    props.mixed_list:append(seed + 0.75)
    props.mixed_list:append("mixed-" .. seed)
    props.mixed_list:append(seed % 2 == 0)

    for row_index = 1, 3 do
        local nested_row = CustomListType()
        nested_row:append(seed * 100 + row_index)
        nested_row:append("row-" .. row_index)
        nested_row:append(row_index % 2 == 0)
        props.nested_lists:append(nested_row)

        local typed_row = IntList()
        typed_row:append(seed * 100 + row_index)
        typed_row:append(seed * 100 + row_index + 10)
        props.matrix:append(typed_row)
    end

    for index = 1, 8 do
        props.leaves:append(make_complex_leaf(seed * 100 + index, "list-leaf-" .. index))
    end
    for index = 1, 16 do
        local key = "map-leaf-" .. index
        props.leaf_lookup[key] = make_complex_leaf(seed * 1000 + index, key)
    end

    fill_tree_node(props.tree, seed, "root")
    fill_tree_node(props.tree.left, seed * 10 + 1, "left")
    fill_tree_node(props.tree.right, seed * 10 + 2, "right")
    fill_tree_node(props.tree.left.left, seed * 100 + 1, "left-left")
    fill_tree_node(props.tree.left.right, seed * 100 + 2, "left-right")
    fill_tree_node(props.tree.right.left, seed * 100 + 3, "right-left")
    fill_tree_node(props.tree.right.right, seed * 100 + 4, "right-right")

    assert(#props.empty_list == 0 and #props.single_list == 1)
    assert(props.empty_map["missing"] == nil and props.single_map["only"] == seed)
    assert(props.nested_map["level1"]["level2"]["level3"]["answer"] == seed * 42)
    assert(props.matrix[3][2] == seed * 100 + 13)
    assert(props.leaf_lookup["map-leaf-16"].leaf_id == seed * 1000 + 16)

    local entity = ComplexEntity()
    entity.props = props
    entity.fixture_kind = "complex"
    return entity, props
end

local function make_y2_stat(seed, label)
    local value = Y2Stat()
    value.health = 100 + seed
    value.attack_power = 20 + seed
    value.label = label
    return value
end

local function make_y2_equip(seed, index)
    local value = Y2Equip()
    value.equip_id = seed * 100 + index
    value.level = index + seed % 5
    value.locked = index % 2 == 0
    value.name = "equip-" .. seed .. "-" .. index
    value.attributes["quality"] = index + 3
    value.attributes["owner"] = seed
    return value
end

local function make_y2_formation(seed, index)
    local value = Y2FormationInfo()
    value.name = "formation-" .. seed .. "-" .. index
    value.history:append(seed * 10 + index)
    value.history:append(seed * 10 + index + 100)
    for slot = 1, 4 do
        local member = Y2FormationItem()
        member.member_id = seed * 1000 + index * 10 + slot
        member.slot = slot
        member.unit_id = 90000 + seed * 100 + slot
        member.active = slot % 2 == 1
        member.label = "slot-" .. slot
        value.content[slot] = member
    end
    return value
end

local function make_y2_properties(seed)
    local props = Y2Properties()
    props.userid = 500000 + seed
    props.level = 10 + seed
    props.remain_exp = seed * 125
    props.head_url = "config_" .. seed
    props.online = seed % 2 == 0
    props.rating = 1500.0 + seed * 2.5

    local detached = {}
    props.obj_nest.stat.health = seed * 10
    props.obj_nest.stat.attack_power = seed * 2
    props.obj_nest.stat.label = "before-replacement"
    props.obj_nest.bonuses[1] = seed
    props.obj_nest.history:append(seed)
    detached[#detached + 1] = props.obj_nest

    local replacement_nest = Y2ObjNest()
    replacement_nest.stat.health = seed * 10 + 1
    replacement_nest.stat.attack_power = seed * 2 + 1
    replacement_nest.stat.label = "after-replacement"
    replacement_nest.bonuses[2] = seed + 1
    replacement_nest.history:append(seed + 1)
    props.obj_nest = replacement_nest

    props.obj_dict[1] = make_y2_stat(seed * 100 + 1, "dict-object")

    local nested_dict = Y2IntMap()
    nested_dict[10] = seed * 1000 + 10
    nested_dict[20] = seed * 1000 + 20
    props.dict_dict[1] = nested_dict

    local dict_sequence = Y2IntList()
    dict_sequence:append(seed * 100 + 1)
    dict_sequence:append(seed * 100 + 2)
    props.list_dict[1] = dict_sequence

    local first_list_stat = make_y2_stat(seed * 100 + 2, "before-list-replacement")
    props.obj_list:append(first_list_stat)
    detached[#detached + 1] = first_list_stat
    local replacement_stat = make_y2_stat(seed * 100 + 3, "after-list-replacement")
    props.obj_list[1] = replacement_stat

    local list_dict = Y2IntMap()
    list_dict[1] = seed * 1000 + 1
    list_dict[2] = seed * 1000 + 2
    props.dict_list:append(list_dict)

    local list_sequence = Y2IntList()
    list_sequence:append(seed * 10 + 1)
    list_sequence:append(seed * 10 + 2)
    props.list_list:append(list_sequence)

    for index = 1, 4 do
        local key = "equip-" .. index
        props.equips[key] = make_y2_equip(seed, index)
    end
    for index = 1, 3 do
        props.formations[index] = make_y2_formation(seed, index)
    end
    for index = 1, 10 do
        props.reviewed_sections:append(seed * 100 + index)
    end

    props.extensions["server_only"] = "runtime-" .. seed
    props.extensions["db_visible"] = seed * 10
    local audit = CustomMapType()
    audit["created_by"] = "fixture"
    audit["revision"] = seed
    props.extensions["audit"] = audit

    for index = 1, 3 do
        local record = Y2DerivedRecord()
        record.record_id = seed * 100 + index
        record.created_at = 1786400000 + seed * 10 + index
        record.label = "record-" .. index
        record.revision = index
        record.state = index % 2 == 0 and "ready" or "pending"
        props.records:append(record)
    end

    assert(props.obj_nest == replacement_nest)
    assert(props.obj_nest.stat.health == seed * 10 + 1)
    assert(props.obj_nest.bonuses[2] == seed + 1)
    assert(props.obj_nest.history[1] == seed + 1)
    assert(props.obj_dict[1].health == seed * 100 + 101)
    assert(props.dict_dict[1][20] == seed * 1000 + 20)
    assert(props.list_dict[1][2] == seed * 100 + 2)
    assert(props.obj_list[1] == replacement_stat)
    assert(props.dict_list[1][2] == seed * 1000 + 2)
    assert(props.list_list[1][2] == seed * 10 + 2)
    assert(props.formations[3].content[4].slot == 4)
    assert(props.records[3].state == "pending")

    local entity = Y2Entity()
    entity.props = props
    entity.fixture_kind = "y2-property-matrix"
    return entity, props, detached
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
    complex_entities = {},
    complex_properties = {},
    y2_entities = {},
    y2_properties = {},
    y2_detached = {},
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

for index = 1, 12 do
    local entity, props = make_complex(index)
    fixture.complex_entities[index] = entity
    fixture.complex_properties[index] = props
end

for index = 1, 12 do
    local entity, props, detached = make_y2_properties(index)
    fixture.y2_entities[index] = entity
    fixture.y2_properties[index] = props
    fixture.y2_detached[index] = detached
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
    assert(entity.health == props.health,
        "entity.mimpl_ scalar read mismatch: entity=" .. tostring(entity.health) ..
        " props=" .. tostring(props.health))
    assert(entity.nested == props.nested, "entity.mimpl_ nested map read mismatch")
    assert(entity.values == props.values, "entity.mimpl_ nested list read mismatch")
    assert(entity.metadata == props.metadata, "entity.mimpl_ generic map read mismatch")

    props.health = props.health + 1
    assert(entity.health == props.health, "native property writeback mismatch")
    if index == 1 then
        local native_health = props.health
        entity.health = native_health + 100000
        assert(props.health == native_health, "entity dynamic field leaked into native props")
        assert(entity.health == native_health + 100000, "entity dynamic field write mismatch")
    end

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
print("Fixture complex properties: entities=" .. #fixture.complex_entities ..
    " growth-map=160 growth-list=160")
print("Fixture y2 property matrix: entities=" .. #fixture.y2_entities ..
    " obj-dict-list=3x3 equips=4 formations=3")
print("Fixture nested paths:", tostring(sample.stats:path()), tostring(sample.inventory:path()),
    tostring(sample.inventory[1]:path()), tostring(sample.inventory[1].modifiers:path()),
    tostring(sample.state:path()), tostring(sample.events:path()))
print("Fixture root types:", tostring(sample:debug_get_prop_types()))
print("Fixture stats types:", tostring(sample.stats:debug_get_prop_types()))
print("Fixture item types:", tostring(sample.inventory[1]:debug_get_prop_types()))
print("Fixture complex paths:", tostring(fixture.complex_properties[1].nested_map:path()),
    tostring(fixture.complex_properties[1].nested_lists:path()),
    tostring(fixture.complex_properties[1].leaf_lookup:path()),
    tostring(fixture.complex_properties[1].tree:path()))
print("Fixture y2 paths:", tostring(fixture.y2_properties[1].obj_nest:path()),
    tostring(fixture.y2_properties[1].dict_dict:path()),
    tostring(fixture.y2_properties[1].list_dict:path()),
    tostring(fixture.y2_properties[1].dict_list:path()),
    tostring(fixture.y2_properties[1].formations:path()),
    tostring(fixture.y2_properties[1].records:path()))
print("READY FOR GCORE")

if os.getenv("MESSIAH_FIXTURE_SMOKE") == "1" then
    print("FIXTURE SMOKE PASS")
    return
end

while true do
    os.execute("sleep 3600")
end
