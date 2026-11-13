// CN 4.2.8 animation state adapter for Iris's native Scaredy-shroom framework.
// No rank multipliers, global clock replacement, or persistent profile changes.
using Byte = unsigned char;
using Word = unsigned int;

template<class T> static T &field(Byte *object, Word offset) {
    return *reinterpret_cast<T *>(object + offset);
}
template<class R, class... Args> static R native(Word base, Word offset, Args... args) {
    return reinterpret_cast<R (*)(Args...)>(base + offset)(args...);
}
template<class R, class... Args> static R method(Byte *object, Word slot, Args... args) {
    return field<R (*)(Byte *, Args...)>(field<Byte *>(object, 0), slot)(object, args...);
}
static void trace(Word base, const char *event, Byte *plant, Word value) {
#if IRIS_DARK_TRACE
    native<int>(base, 0xe8c10, 3, "IrisDark", "Scaredy %s plant=%p value=%u", event, plant, value);
#endif
}

static int play(Word base, Byte *rig, const char *label, bool loop) {
    char *text;
    char allocator;
    Word empty[6] = {};
    native<void>(base, 0xb75560, &text, label, &allocator);
    const int result = native<int>(base, loop ? 0x44d220 : 0x44d0b0,
                                   rig, &text, loop ? 3 : 0, empty, empty);
    if (__atomic_fetch_sub(reinterpret_cast<int *>(text - 4), 1, __ATOMIC_ACQ_REL) <= 0)
        native<void>(base, 0xb76c4c, text - 12, &allocator);
    return result;
}

// The final eight bytes are ephemeral: time of the last nearby enemy, and the
// transition phase. The original framework/PeashooterPFHelper occupies 0x20.
static Byte *allocate(Word base) {
    Byte *framework = native<Byte *>(base, 0xb363dc, 0x28u);
    field<float>(framework, 0x20) = 0;
    field<Word>(framework, 0x24) = 0;
    return framework;
}

static void update(Word base, Byte *framework) {
    Byte *plant = field<Byte *>(framework, 4);
    Byte *app = **reinterpret_cast<Byte ***>(base + 0xd00838);
    Byte *board = app ? field<Byte *>(app, 0x6c0) : nullptr;
    if (!plant || !board || native<bool>(base, 0x1872a8, board)) return;
    Byte *clock = *reinterpret_cast<Byte **>(base + 0xd4ed90);
    if (!clock) return;
    const float now = field<float>(clock, 0x1c);
    auto &lastDanger = field<float>(framework, 0x20);
    auto &phase = field<Word>(framework, 0x24);
    auto &state = field<Word>(plant, 0x48);
    if (state != 4 && state != 6) {
        phase = 0;
        lastDanger = now;
        return;
    }
    Byte *rig = method<Byte *>(plant, 0x70);
    if (!rig) return;
    const bool danger = native<bool>(base, 0x3feea4, framework);
    if (danger) lastDanger = now;
    if (state == 4) {
        phase = 0;
        if (danger && play(base, rig, "hide", false) != -1) {
            state = 6;
            field<Word>(rig, 0x180) = 6;
            phase = 1;
            trace(base, "hide", plant, 1);
        }
        return;
    }
    // A restored native plant can already be cowering. Reconstruct the idle
    // animation instead of relying on transient fields from the former run.
    if (!phase) {
        if (play(base, rig, "hide_idle", true) == -1) return;
        field<Word>(rig, 0x180) = 6;
        phase = 2;
        lastDanger = now;
    }
    if (phase == 3) {
        if (danger) {
            if (play(base, rig, "hide", false) != -1) phase = 1;
        } else if (!native<bool>(base, 0x44da38, rig)) {
            method<void>(rig, 0x8c);
            state = 4;
            phase = 0;
            trace(base, "awake", plant, 0);
        }
        return;
    }
    if (phase == 1) {
        if (native<bool>(base, 0x44da38, rig)) return;
        if (play(base, rig, "hide_idle", true) == -1) return;
        phase = 2;
        trace(base, "hidden", plant, 2);
    }
    // Game time is already paused/scaled by Iris. Wall-clock time would make
    // the plant rise immediately after resuming a pause or switching apps.
    if (!danger && now - lastDanger >= 1.0f && play(base, rig, "hide_end", false) != -1) {
        phase = 3;
        trace(base, "rise", plant, 3);
    }
}

static Word adjustDamage(Word base, Word *args) {
    Byte *output = reinterpret_cast<Byte *>(args[0]);
    Byte *framework = reinterpret_cast<Byte *>(args[1]);
    Byte *input = reinterpret_cast<Byte *>(args[2]);
    // The old engine owns the condition vector's copy constructor. Preserve
    // its allocation/refcount rules rather than shallow-copying DamageInfo.
    native<void>(base, 0x13f310, output, framework, input);
    Byte *plant = field<Byte *>(framework, 4);
    const Word phase = field<Word>(framework, 0x24);
    if (plant && field<Word>(plant, 0x48) == 6 && (phase == 2 || phase == 3)
            && !(field<Word>(input, 8) & 2) && field<float>(output, 4) > 0)
        field<float>(output, 4) *= 0.9f;
    return args[0];
}

static void updatePlantfood(Word base, Byte *framework) {
    Byte *plant = field<Byte *>(framework, 4);
    if (!plant) return;
    Word handle[2] = {};
    native<void>(base, 0x39e838, handle, plant);
    Byte *properties = native<Byte *>(base, 0x13f3c4, handle);
    if (properties) {
        float point[3] = {field<float>(plant, 0x10), field<float>(plant, 0x14), 0};
        Byte *actions = field<Byte *>(properties, 0x30);
        Byte *end = field<Byte *>(properties, 0x34);
        if (actions && end - actions >= 2 * 0x60)
            native<void>(base, 0x3cdf88, framework + 8, plant, point,
                         field<Word>(plant, 0x44), actions + 0x60);
    }
    native<void>(base, 0x13dea0, handle, 0u, 0u, 0u);
}

static bool equal(const char *a, const char *b) {
    if (!a || !b) return false;
    while (*a && *a == *b) { ++a; ++b; }
    return *a == *b;
}

static bool canKnockback(Byte *entity) {
    if (!entity) return false;
    Byte *type = method<Byte *>(entity, 0);
    bool zombie = false;
    for (Word depth = 0; type && depth < 32; ++depth, type = field<Byte *>(type, 8)) {
        const char *name = field<const char *>(type, 4);
        if (equal(name, "ZombieGargantuar") || equal(name, "ZombieGargantuarMech")
                || equal(name, "ZombieZombossMech") || equal(name, "ZombieMech")
                || equal(name, "ZombiePirateCannon") || equal(name, "ZombiePirateParrot")
                || equal(name, "ZombieParrot") || equal(name, "ZombiePiano")
                || equal(name, "ZombieCowboyPiano") || equal(name, "ZombieBull")
                || equal(name, "ZombieCowboyBull") || equal(name, "ZombieDarkKing") || equal(name, "ZombieIrisKing")
                || equal(name, "ZombieTreasureYeti")) return false;
        if (equal(name, "Zombie")) zombie = true;
    }
    return zombie;
}

static void knockback(Word base, Byte *zombie, float distance, float height, float duration) {
    Byte *app = **reinterpret_cast<Byte ***>(base + 0xd00838);
    Byte *board = app ? field<Byte *>(app, 0x6c0) : nullptr;
    if (!board) return;
    Byte *manager = native<Byte *>(base, 0x28b850, board);
    if (!manager) return;
    float target[3] = {field<float>(zombie, 0x10) + distance, field<float>(zombie, 0x14), 0};
    // Match the engine's empty weak/string/callback descriptor. Its movement
    // scheduler takes owned copies; never hand it a shallow string or null.
    Word context[10] = {};
    char allocator;
    native<void>(base, 0xb75560, context + 2, "", &allocator);
    context[3] = base + 0xccbfd8;
    native<void>(base, 0x67a3d8, manager, zombie, target, height, duration, context, 1u);
    // The literal empty string uses libstdc++'s static empty representation.
    // Its destructor is a no-op; decrementing/freeing it would corrupt COW.
}

static Word projectileImpact(Word base, Word *args) {
    Byte *projectile = reinterpret_cast<Byte *>(args[0]);
    Byte *target = reinterpret_cast<Byte *>(args[1]);
    Byte *properties = field<Byte *>(projectile, 0x10);
    if (!properties) {
        properties = native<Byte *>(base, 0x413bbc, projectile + 0x18);
        field<Byte *>(projectile, 0x10) = properties;
    }
    if (properties && equal(field<const char *>(properties, 0x80), "iris_scaredy_plantfood")) {
        const bool eligible = canKnockback(target);
        trace(base, "PF impact", target, eligible);
        if (eligible) knockback(base, target, 2.0f * 64.0f, 5.0f, 0.1f);
    }
    return native<Word>(base, 0x489930, projectile, target);
}

struct EntityList { Byte **begin, **end, **capacity; };
static EntityList nearby(Word base, Byte *plant, Word mask) {
    // GridRect is x/column, y/row, width, height. Iris Plant stores its row
    // at 0x58 and column at 0x5c (confirmed by the native reflection).
    int rect[4] = {int(field<Word>(plant, 0x5c)) - 1,
                   int(field<Word>(plant, 0x58)) - 1, 3, 3};
    EntityList result = {};
    native<void>(base, 0x248120, &result, mask, rect);
    return result;
}
static void releaseList(Word base, EntityList &list) {
    if (list.begin) native<void>(base, 0xb36928, list.begin);
}
static void startFood(Word base, Byte *framework) {
    Byte *plant = field<Byte *>(framework, 4);
    const bool cowering = plant && field<Word>(plant, 0x48) == 6;
    native<void>(base, 0x3fecc8, framework);
    trace(base, "PF start", plant, field<Word>(framework, 0x14));
    // The initial area impulse is distinct from the small push attached to
    // each projectile. Heavy enemies retain the publisher's exclusion list.
    if (cowering) {
        auto zombies = nearby(base, plant, 2);
        for (auto p = zombies.begin; p != zombies.end; ++p)
            if (canKnockback(*p)) knockback(base, *p, 100.0f, 50.0f, 0.5f);
        releaseList(base, zombies);
    }
}
static void startFoodChain(Word base, Byte *framework) {
    Byte *plant = field<Byte *>(framework, 4);
    if (!plant) return;
    // Take the snapshot before activating anyone; every plant starts once,
    // without another player charge or recursive proximity propagation.
    // Board masks are plant=1, zombie=2, grid item=4. A mask of four
    // finds gravestones rather than the neighboring mushrooms.
    auto plants = nearby(base, plant, 1);
    startFood(base, framework);
    for (auto p = plants.begin; p != plants.end; ++p) {
        Byte *other = *p;
        if (!other || other == plant || !field<Byte>(other, 0x60)
                || field<Word>(other, 0x48) == 3 || method<bool>(other, 0x74)) continue;
        Byte *fw = field<Byte *>(other, 0x30);
        if (fw && field<Word>(fw, 0) == base + 0xce6458) {
            startFood(base, fw);
            trace(base, "PF proximity", other, 35);
        }
    }
    releaseList(base, plants);
}

extern "C" __attribute__((section(".text.entry")))
Word iris_scaredy(Word base, Byte *framework, Word mode) {
    if (!mode) return reinterpret_cast<Word>(allocate(base));
    if (mode == 2) return adjustDamage(base, reinterpret_cast<Word *>(framework));
    if (mode == 3) {
        updatePlantfood(base, framework);
        return 0;
    }
    if (mode == 4) return projectileImpact(base, reinterpret_cast<Word *>(framework));
    if (mode == 5) {
        startFoodChain(base, framework);
        return 0;
    }
    update(base, framework);
    return 0;
}
