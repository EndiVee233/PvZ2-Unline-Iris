// Aster tier-one Sun-shroom behavior on Iris's original growth frameworks.
using Byte = unsigned char;
using Word = unsigned int;
template<class T> static T &field(Byte *p, Word offset) {
    return *reinterpret_cast<T *>(p + offset);
}
template<class R, class... A> static R native(Word base, Word offset, A... args) {
    return reinterpret_cast<R (*)(A...)>(base + offset)(args...);
}
template<class R, class... A> static R method(Byte *p, Word slot, A... args) {
    return field<R (*)(Byte *, A...)>(field<Byte *>(p, 0), slot)(p, args...);
}
static float gameTime(Word base) {
    Byte *clock = *reinterpret_cast<Byte **>(base + 0xd4ed90);
    return clock ? field<float>(clock, 0x1c) : 0;
}
static bool equal(const char *a, const char *b) {
    if (!a || !b) return false;
    while (*a && *a == *b) { ++a; ++b; }
    return *a == *b;
}
static void trace(Word base, const char *event, Byte *plant, Word value) {
#if IRIS_DARK_TRACE
    native<int>(base, 0xe8c10, 3, "IrisDark", "Mushroom %s plant=%p value=%u", event, plant, value);
#endif
}
static Byte *properties(Word base, Byte *plant) {
    Word weak[2] = {};
    native<void>(base, 0x39e838, weak, plant);
    Byte *result = native<Byte *>(base, 0x13f3c4, weak);
    native<void>(base, 0x13dea0, weak, 0u, 0u, 0u);
    return result;
}
static bool darkSun(const char *name) {
    const char *prefix = "iris_dark_sun";
    if (!name) return false;
    while (*prefix) if (*name++ != *prefix++) return false;
    return !*name || *name == '_';
}
static void release(Word base, char *text) {
    char allocator;
    if (__atomic_fetch_sub(reinterpret_cast<int *>(text - 4), 1, __ATOMIC_ACQ_REL) <= 0)
        native<void>(base, 0xb76c4c, text - 12, &allocator);
}
static void spawnSun(Word base, Word *args) {
    Byte *framework = reinterpret_cast<Byte *>(args[0]);
    Byte *plant = field<Byte *>(framework, 4);
    Byte *props = plant ? properties(base, plant) : nullptr;
    char *previous = props ? field<char *>(props, 0x8c) : nullptr;
    char *large = nullptr;
    char allocator;
    // Plant-food always releases three full-grown suns, including on the
    // first growth stage. The original native spawn keeps flight and sounds.
    if (plant && field<Word>(plant, 0x48) == 5 && darkSun(previous)) {
        native<void>(base, 0xb75560, &large, "iris_dark_sun_large", &allocator);
        field<char *>(props, 0x8c) = large;
    }
    // The old rig has one use_action marker. Its repeat-action scheduler
    // restarts that animation every frame when fed Aster's count of three.
    // Start one animation, then emit the three native collectibles here.
    const Word count = large ? 3 : 1;
    for (Word i = 0; i < count; ++i)
        native<void>(base, IRIS_SUNSPAWN_ORIGINAL, framework, args[1]);
    if (large) {
        field<char *>(props, 0x8c) = previous;
        release(base, large);
        trace(base, "sun PF spawn", plant, 3 * 75);
    }
}
static void startSunFood(Word base, Byte *framework) {
    native<void>(base, 0x410324, framework);
    Byte *plant = field<Byte *>(framework, 4);
    Byte *props = plant ? properties(base, plant) : nullptr;
    if (props && darkSun(field<const char *>(props, 0x8c)))
        field<Word>(framework, 8) = 1;
}
static void finishFood(Word base, Byte *framework) {
    Byte *plant = field<Byte *>(framework, 4);
    native<void>(base, 0x3ba2c0, framework);
    field<Word>(plant, 0x48) = 4;
    Byte *props = properties(base, plant);
    if (!props || !darkSun(field<const char *>(props, 0x8c))) return;
    Byte *types = *reinterpret_cast<Byte **>(base + 0xd4ec98);
    if (!types) return;
    char *name;
    char allocator;
    native<void>(base, 0xb75560, &name, "sunshroom_stage3", &allocator);
    Byte *node = native<Byte *>(base, 0x195248, types, &name);
    if (node && node != types + 4) {
        Word weak[2] = {};
        native<void>(base, 0x13dea0, weak, field<Word>(node, 0x1c),
                     field<Word>(node, 0x18), field<Word>(node, 0x1c));
        const Word row = native<Word>(base, 0x1a3ee4, plant);
        const Word column = native<Word>(base, 0x1a3eb4, plant);
        // Iris's own mutation reconstructs the model/framework in place and
        // keeps the existing board coordinates and save representation.
        native<void>(base, 0x39df1c, plant, row, column, weak);
        trace(base, "sun PF mature", plant, 3);
        native<void>(base, 0x13dea0, weak, 0u, 0u, 0u);
    }
    release(base, name);
}
static void initializePuff(Word base, Byte *framework) {
    // Reuse the original serialized birth-time field as the preparation
    // sentinel. A separate transient "started" flag would reset the lifetime
    // of a positive birth time restored from a saved battle.
    field<float>(framework, 0x20) = -1.0f;
    field<float>(framework, 0x24) = 0;
    field<Word>(framework, 0x28) = 0;
}
static bool isPlant(Byte *object) {
    if (!object) return false;
    Byte *type = method<Byte *>(object, 0);
    for (Word depth = 0; type && depth < 32; ++depth, type = field<Byte *>(type, 8))
        if (equal(field<const char *>(type, 4), "Plant")) return true;
    return false;
}
static void startPuffFood(Word base, Byte *framework) {
    Byte *source = field<Byte *>(framework, 4);
    const float now = gameTime(base);
    field<float>(framework, 0x20) = now;
    field<Word>(framework, 0x28) = 0;
    native<void>(base, 0x3fa644, framework);
    trace(base, "puff PF start", source, 30);
    Byte *registry = native<Byte *>(base, 0x8821a8);
    Byte *bucket = native<Byte *>(base, 0x888b8c, registry, 0x1fu);
    if (!bucket || !source) return;
    Byte *slots = field<Byte *>(bucket, 4);
    const Word count = field<Word>(bucket, 8);
    if (!slots || count > 16384) return;
    for (Word i = 0; i < count; ++i) {
        Byte *plant = field<Byte *>(slots + i * 32, 8);
        if (!isPlant(plant) || plant == source || !field<Byte>(plant, 0x60)
                || field<Word>(plant, 0x48) == 3) continue;
        Byte *other = field<Byte *>(plant, 0x30);
        if (!other || field<Word>(other, 0) != base + 0xce6058) continue;
        field<float>(other, 0x20) = now;
        if (method<bool>(plant, 0x74)) continue;
        const float dx = float(int(field<Word>(plant, 0x58)) - int(field<Word>(source, 0x58)));
        const float dy = float(int(field<Word>(plant, 0x5c)) - int(field<Word>(source, 0x5c)));
        const float due = now + 0.1f + 0.2f * __builtin_sqrtf(dx * dx + dy * dy);
        if (!field<Word>(other, 0x28) || due < field<float>(other, 0x24))
            field<float>(other, 0x24) = due;
        field<Word>(other, 0x28) = 1;
        trace(base, "puff PF queued", plant, i);
    }
}
static void updatePuff(Word base, Byte *framework) {
    Byte *app = **reinterpret_cast<Byte ***>(base + 0xd00838);
    Byte *board = app ? field<Byte *>(app, 0x6c0) : nullptr;
    if (!board || field<Word>(board, 0xa8) != 5 || native<bool>(base, 0x1872a8, board)) return;
    if (field<float>(framework, 0x20) < 0) {
        // Preplanted mushrooms must not spend their lifespan during the
        // camera pan, dialogue, seed selection or Last Stand preparation.
        field<float>(framework, 0x20) = gameTime(base);
    }
    Byte *plant = field<Byte *>(framework, 4);
    if (field<Word>(framework, 0x28) && gameTime(base) >= field<float>(framework, 0x24)) {
        field<Word>(framework, 0x28) = 0;
        // Call the original start, so a propagated burst never fans out a
        // second time or spends another plant-food charge.
        if (plant && !method<bool>(plant, 0x74) && field<Word>(plant, 0x48) != 3) {
            native<void>(base, 0x3fa644, framework);
            trace(base, "puff PF propagated", plant, 30);
        }
    }
    native<void>(base, 0x3fa754, framework);
}
extern "C" __attribute__((section(".text.entry")))
void iris_mushrooms(Word base, Byte *object, Word mode) {
    switch (mode) {
        case 0: spawnSun(base, reinterpret_cast<Word *>(object)); break;
        case 1: finishFood(base, object); break;
        case 2: initializePuff(base, object); break;
        case 3: startPuffFood(base, object); break;
        case 4: updatePuff(base, object); break;
        case 5: startSunFood(base, object); break;
    }
}
