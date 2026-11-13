// Iris 1.6.257161 ARMv7. This runs on the original game's input thread.
using Byte = unsigned char;
using Word = unsigned int;

struct Touch {
    Word id, pad;
    int x, y, previousX, previousY;
    Word taps, padding, time[2], phase;
};

struct Weak {
    Word first, second;
};

struct Preview {
    Byte *board;
    Byte *cursor;
    Byte *app;
};

struct SpeedButton {
    Byte *board;
    Byte *pause;
    int x, y, width, height;
    Word pointerId;
    bool tracking;
    bool pressed;
    bool armed;
};

struct ImageReference {
    Word prefix[3];
    const char *name;
    Weak handle;
};

struct PinchPress {
    Byte *powerup;
    Word id;
    int x, y;
};

struct CoinFade {
    Byte *widget;
    Byte *board;
    Word balance;
    Word pulseAt;
    Word selectionPending;
};

static_assert(sizeof(SpeedButton) == 32 && sizeof(ImageReference) == 24 && sizeof(PinchPress) == 16);

static void copyTouch(Touch &target, const Touch &source) {
    auto *to = reinterpret_cast<volatile Byte *>(&target);
    const auto *from = reinterpret_cast<const volatile Byte *>(&source);
    for (Word index = 0; index < sizeof(Touch); ++index) to[index] = from[index];
}

template<class T> T &field(Byte *object, Word offset) {
    return *reinterpret_cast<T *>(object + offset);
}

template<class R, class... Args>
R native(Word base, Word offset, Args... args) {
    return reinterpret_cast<R (*)(Args...)>(base + offset)(args...);
}

template<class R, class... Args>
R virtualCall(Byte *object, Word slot, Args... args) {
    Byte *table = field<Byte *>(object, 0);
    return field<R (*)(Byte *, Args...)>(table, slot)(object, args...);
}

static Byte *resolve(Word base, const Weak &handle) {
    if (!(handle.first | handle.second)) return nullptr;
    Byte *registry = native<Byte *>(base, 0x8821a8);
    Weak normalized;
    native<void>(base, 0x8890c4, &normalized, registry, &handle);
    Byte *object = nullptr;
    if (normalized.first | normalized.second) {
        Byte *bucket = native<Byte *>(base, 0x888b8c, registry, (normalized.second << 1) >> 18);
        if (bucket) object = native<Byte *>(base, 0x884378, bucket, &normalized);
    }
    native<void>(base, 0x13dea0, &normalized, 0u, 0u, 0u);
    return object;
}

static bool isType(Word base, Byte *object, Word getType) {
    return object && virtualCall<int>(object, 0x10, native<Byte *>(base, getType)) == 1;
}

static bool equal(const char *left, const char *right) {
    if (!left || !right) return false;
    while (*left && *left == *right) {
        ++left;
        ++right;
    }
    return *left == *right;
}

static bool paused(Byte *board) {
    return field<Byte>(board, 0x671) != 0;
}

static bool inBattle(Byte *board) {
    Word state = field<Word>(board, 0xa8);
    return state == 4 || state == 5;
}

static bool playable(Byte *board) {
    return inBattle(board) && !paused(board);
}

static Byte *topModal(Byte *app) {
    Byte *manager = field<Byte *>(app, 0x2b8);
    if (!manager) return nullptr;
    Byte *last = field<Byte *>(manager, 0xac);
    return last && last != manager + 0xa8 ? field<Byte *>(last, 8) : nullptr;
}

static Byte *widget(Word base, const char *name) {
    char *text;
    char allocator;
    native<void>(base, 0xb75560, &text, name, &allocator);
    Byte *result = native<Byte *>(base, 0x536398, &text);
    if (__atomic_fetch_sub(reinterpret_cast<int *>(text - 4), 1, __ATOMIC_ACQ_REL) <= 0)
        native<void>(base, 0xb76c4c, text - 12, &allocator);
    return result;
}

static Byte *powerupButton(Word base, const char *className) {
    Byte *holder = widget(base, "UIPowerupHolder");
    if (!holder || !native<bool>(base, 0x537ffc, holder)) return nullptr;
    Word begin = field<Word>(holder, 0x40);
    Word end = field<Word>(holder, 0x44);
    if (!begin || end < begin || end - begin > 32 * sizeof(Weak) || (end - begin) % sizeof(Weak))
        return nullptr;
    for (Word address = begin; address < end; address += sizeof(Weak)) {
        Byte *button = resolve(base, *reinterpret_cast<const Weak *>(address));
        if (!isType(base, button, 0x45d9b4)) continue;
        Byte *type = resolve(base, field<Weak>(button, 0xf0));
        if (isType(base, type, 0x1331ec) && equal(field<const char *>(type, 8), className))
            return button;
    }
    return nullptr;
}

static void tap(Byte *app, Byte *board, const Touch &source, int x, int y) {
    Touch event;
    copyTouch(event, source);
    event.id = 0x7ffffffe;
    event.taps = 1;
    event.x = event.previousX = x;
    event.y = event.previousY = y;
    event.phase = 0;
    virtualCall<void>(app, 0x1b0, &event);
    if (field<Byte *>(app, 0x6c0) == board) {
        event.x = event.previousX = x;
        event.y = event.previousY = y;
        event.phase = 3;
        virtualCall<void>(app, 0x1b4, &event);
    }
}

static bool click(Word base, Byte *app, Byte *board, Byte *control, const Touch &event) {
    if (!control || !native<bool>(base, 0x537ffc, control)) return false;
    int center[2];
    native<void>(base, 0x5385c0, center, control);
    if (native<Byte *>(base, 0x537174, center[0], center[1], 200) != control) return false;

    tap(app, board, event, center[0], center[1]);
    return true;
}

static Preview &preview(Word base) {
    return *reinterpret_cast<Preview *>(base + 0xdf9708);
}

static void boardPoint(Word base, Byte *board, int x, int y, int (&point)[2]) {
    // WidgetManager subtracts the widget's absolute origin before Board inverts zoom.
    int origin[2];
    Byte *table = field<Byte *>(board, 0);
    field<void (*)(int *, Byte *)>(table, 0x60)(origin, board);
    point[0] = x - origin[0];
    point[1] = y - origin[1];
    native<void>(base, 0x1841fc, board, point);
}

static void moveCursor(Word base, Byte *app, Byte *board, const Touch &source) {
    Byte *cursor = field<Byte *>(board, 0x640);
    if (!cursor || field<Byte>(cursor, 0x10) || field<Word>(cursor, 0x14)) return;
    int point[2];
    boardPoint(base, board, source.x, source.y, point);
    // The plant cursor's move handler also changes it from selected to dragging.
    if (isType(base, cursor, 0x169194)) {
        Touch hover;
        copyTouch(hover, source);
        hover.x = hover.previousX = point[0];
        hover.y = hover.previousY = point[1];
        hover.phase = 1;
        virtualCall<void>(cursor, 0x24, &hover);
    } else {
        field<float>(cursor, 4) = point[0];
        field<float>(cursor, 8) = point[1];
    }
    preview(base) = {board, cursor, app};
}

static void restoreHover(Word base, Byte *driver, Byte *app, Byte *board, const Touch &event) {
    if (event.previousX < 0 || event.previousY < 0) return;
    Touch hover;
    copyTouch(hover, event);
    hover.x = event.previousX;
    hover.y = event.previousY;
    native<void>(base, 0x9e8340, driver, &hover);
    moveCursor(base, app, board, hover);
}

static bool insideBoard(Byte *board, const int (&cell)[2]) {
    return static_cast<Word>(cell[0]) < field<Word>(board, 0x9c)
        && static_cast<Word>(cell[1]) < field<Word>(board, 0xa0);
}

static bool boardCell(Word base, Byte *app, Byte *board, float x, float y, int (&cell)[2]) {
    float scale = field<float>(app, 0x6a0);
    if (!(scale > 0.0f && scale < 16.0f)) return false;
    cell[0] = static_cast<int>(native<float>(base, 0xe8700, (x / scale - 200.0f) / 64.0f));
    cell[1] = static_cast<int>(native<float>(base, 0xe8700, (y / scale - 160.0f) / 76.0f));
    return insideBoard(board, cell);
}

static void drawPending(Word base, Byte *board, Byte *graphics, bool sprite) {
    const Preview &last = preview(base);
    if (last.board != board || !last.app || topModal(last.app) || !playable(board)
            || field<Byte *>(board, 0x634) != field<Byte *>(board, 0x638)) return;
    Byte *cursor = field<Byte *>(board, 0x640);
    if (!cursor || last.cursor != cursor || field<Byte>(cursor, 0x10) || field<Word>(cursor, 0x14)) return;
    if (sprite) {
        // Match the active cursor renderer, inside its existing board zoom transform.
        native<void>(base, 0x7d2810, graphics);
        float originX = field<float>(graphics, 0x18);
        float originY = field<float>(graphics, 0x1c);
        field<float>(graphics, 8) += originX + native<float>(base, 0xe8700,
                (field<float>(cursor, 4) - originX) * field<float>(graphics, 0x10));
        field<float>(graphics, 12) += originY + native<float>(base, 0xe8700,
                (field<float>(cursor, 8) - originY) * field<float>(graphics, 0x14));
        virtualCall<void>(cursor, 0x20, graphics);
        native<void>(base, 0x7d2940, graphics);
        return;
    }
    int cell[2];
    if (isType(base, cursor, 0x169194)) {
        if (virtualCall<int>(cursor, 0x2c) != 1) return;
        Byte *table = field<Byte *>(cursor, 0);
        field<void (*)(int *, Byte *)>(table, 0x30)(cell, cursor);
    } else {
        // Pending tools can preview the hovered tile before a touch drag starts.
        if (!boardCell(base, last.app, board, field<float>(cursor, 4), field<float>(cursor, 8), cell))
            return;
    }
    if (insideBoard(board, cell)) {
        native<void>(base, 0x18d628, board, graphics, cell[0], cell[1]);
    }
}

static void collect(Word base, Byte *app, Byte *board, const Touch &source, bool all) {
    Byte *registry = native<Byte *>(base, 0x8821a8);
    // The original Collectable factory registers board objects in bucket 0x20.
    Byte *bucket = native<Byte *>(base, 0x888b8c, registry, 0x20u);
    if (!bucket) return;
    Byte *slots = field<Byte *>(bucket, 4);
    Word count = field<Word>(bucket, 8);
    if (!slots || count > 16384) return;

    Weak handles[256];
    Word size = 0;
    for (Word index = 0; index < count && size < 256; ++index) {
        Byte *object = field<Byte *>(slots + index * 32, 8);
        if (!isType(base, object, 0x160c64) || (field<Word>(object, 0x38) & 0x80)
                || field<Word>(object, 0x40) == 1) continue;
        const Weak &handle = field<Weak>(object, 8);
        if (handle.first | handle.second) handles[size++] = handle;
    }

    float scale = field<float>(app, 0x6a0);
    if (!(scale > 0.0f && scale < 16.0f)) return;
    Touch event;
    copyTouch(event, source);
    event.phase = 1;
    if (!all) {
        // The original collectable hit test receives board-local, unzoomed coordinates.
        int point[2];
        boardPoint(base, board, source.x, source.y, point);
        event.x = event.previousX = point[0];
        event.y = event.previousY = point[1];
    }
    for (Word index = 0; index < size; ++index) {
        if (field<Byte *>(app, 0x6c0) != board || !playable(board) || topModal(app)) return;
        Byte *object = resolve(base, handles[index]);
        if (!object) continue;
        if (all) {
            int rect[4];
            Byte *table = field<Byte *>(object, 0);
            field<void (*)(int *, Byte *)>(table, 0x4c)(rect, object);
            if (rect[2] <= 0 || rect[3] <= 0) continue;
            event.x = event.previousX = static_cast<int>((rect[0] + rect[2] / 2) * scale);
            event.y = event.previousY = static_cast<int>((rect[1] + rect[3] / 2) * scale);
        }
        virtualCall<int>(object, 0x98, &event);
    }
}

static void toggleSpeed(Word base) {
    // SetTimeScale's original configuration object and our zero-initialized state.
    constexpr Word fast = 0x40000000;
    auto &settings = *reinterpret_cast<Byte **>(base + 0xd4ed90);
    Word *state = reinterpret_cast<Word *>(base + 0xdf9700);
    Word &feedback = *reinterpret_cast<Word *>(base + 0xdf9774);
    if (state[1]) {
        if (settings && field<Word>(settings, 0x28) == fast) {
            field<Word>(settings, 0x28) = state[0];
            if (state[0] != fast) feedback = 1;
        }
        state[1] = 0;
        return;
    }
    state[0] = settings ? field<Word>(settings, 0x28) : 0;
    native<void>(base, 0x3761ec, 0u, 2.0f);
    state[1] = settings && field<Word>(settings, 0x28) == fast;
    if (state[1] && state[0] != fast) feedback = 2;
}

static SpeedButton &speedButton(Word base) {
    return *reinterpret_cast<SpeedButton *>(base + 0xdf9714);
}

static bool dialogueActive(Word base, Byte *app) {
    Byte *npc = field<Byte *>(app, 0xbb0);
    // Same NPC state check used by Board's original pause handlers.
    return npc && native<bool>(base, 0x203dcc, npc);
}

static bool beginCoinDraw(Word base, Byte *coin, Byte *graphics) {
    Byte *app = **reinterpret_cast<Byte ***>(base + 0xd00838);
    Byte *board = app ? field<Byte *>(app, 0x6c0) : nullptr;
    auto &fade = *reinterpret_cast<CoinFade *>(base + 0xdf9778);
    constexpr Word fadeIn = 128;
    constexpr Word holdUntil = fadeIn + 2048;
    constexpr Word hideAt = holdUntil + 2048;
    Word alpha = 255;
    if (!board || !inBattle(board)) {
        fade.widget = nullptr;
    } else {
        Word stamp[2];
        if (native<int>(base, 0xe8e5c, 1, stamp) == 0) {  // clock_gettime(CLOCK_MONOTONIC)
            const Word now = stamp[0] * 1000u + static_cast<Word>(stamp[1] * 0.000001f);
            const int target = field<int>(coin, 0xf0);
            const Word balance = target > 0 ? target : field<Word>(coin, 0xec);
            if (fade.widget != coin || fade.board != board) {
                fade = {coin, board, balance, now - fadeIn, 0};
            } else {
                const Word age = now - fade.pulseAt;
                if (age < fadeIn) alpha = age * 255 / fadeIn;
                else if (age >= hideAt) alpha = 0;
                else if (age >= holdUntil) alpha = (hideAt - age) * 255 / (hideAt - holdUntil);
                if (fade.balance != balance || fade.selectionPending) {
                    fade.balance = balance;
                    fade.selectionPending = 0;
                    // Start from the current opacity and renew the hold period.
                    fade.pulseAt = now - (alpha + 1) / 2;
                }
            }
        }
    }
    if (!alpha) return false;
    native<void>(base, 0x7d2810, graphics);  // Original Graphics::PushState.
    if (alpha != 255) {
        const int tint[4] = {255, 255, 255, static_cast<int>(alpha)};
        const int *color = native<const int *>(base, 0x7d2bb4, graphics);
        const int original[4] = {color[0], color[1], color[2], color[3]};
        // The number renderer sets its own color. Keep opacity on the color stack.
        native<void>(base, 0x7d2aa8, graphics, tint);  // Graphics::SetColor
        native<void>(base, 0x7d2bbc, graphics);  // Graphics::PushColor
        native<void>(base, 0x7d2aa8, graphics, original);
        native<void>(base, 0x7d2de4, graphics, true);  // Graphics::SetColorizeImages
    }
    return true;
}

static bool styledChooser(Word base) {
    if (!*reinterpret_cast<Byte *>(base + 0xdf978c)) return false;
    Byte *app = **reinterpret_cast<Byte ***>(base + 0xd00838);
    Byte *board = app ? field<Byte *>(app, 0x6c0) : nullptr;
    return board && field<Word>(board, 0xa8) == 3;
}

static void styleFontText(Word base, const Word **text, bool tripTitle) {
    const Word *characters = *text;
    const Word length = characters[-3];  // GNU basic_string<wchar_t> representation.
    Word styled[256];
    if (length >= sizeof(styled) / sizeof(*styled)) return;
    bool apply = !tripTitle;
    for (Word index = 0; index < length; ++index) {
        const Word character = characters[index];
        apply |= character >= 0xf880 && character < 0xf8ff;
        // Match MAP_LATIN_BASE and TRIP_GLYPHS in the font builder.
        styled[index] = character >= 0x21 && character <= 0x7e ? 0xf800 + character : character;
    }
    if (apply && length) native<void>(base, 0xb77320, text, styled, length);
}

static void drawSpeedButton(Word base, Byte *pause, Byte *graphics) {
    Byte *app = **reinterpret_cast<Byte ***>(base + 0xd00838);
    if (!app) return;
    Byte *board = field<Byte *>(app, 0x6c0);
    if (!board || !inBattle(board)) return;
    Byte *modal = topModal(app);
    Byte *pauseMenu = field<Byte *>(app, 0xbc4);
    const bool showingPause = paused(board) && pauseMenu && modal == pauseMenu;
    if (!showingPause && (!playable(board) || modal || !native<bool>(base, 0x537ffc, pause))) return;
    int rect[4];
    native<void>(base, 0x534f5c, rect, pause);
    const int offset = -rect[2] - rect[2] / 8;
    if (rect[2] <= 0 || rect[3] <= 0 || rect[0] + offset < 0) return;

    auto &button = speedButton(base);
    if (showingPause || dialogueActive(base, app)) button.armed = button.pressed = false;
    bool active = *reinterpret_cast<Word *>(base + 0xdf9704) != 0;
    bool highlighted = active || (button.tracking && button.pressed);
    auto *references = reinterpret_cast<ImageReference *>(base + 0xdf9734);
    auto &image = references[highlighted];
    image.name = highlighted ? "IMAGE_UI_HUD_INGAME_SPEED_DOWN" : "IMAGE_UI_HUD_INGAME_SPEED";
    Byte *sprite = native<Byte *>(base, 0x1524d8, &image);
    if (!sprite) {
        native<void>(base, 0x13dea0, &image.handle, 0u, 0u, 0u);
        return;
    }
    if (showingPause) {
        // This draw runs after the pause shade. Match Aster's half-bright HUD.
        // The pause button's original PopState restores both graphics settings.
        const int tint[4] = {128, 128, 128, 255};
        native<void>(base, 0x7d2aa8, graphics, tint);  // Graphics::SetColor
        native<void>(base, 0x7d2de4, graphics, true);  // Graphics::SetColorizeImages
    }
    native<void>(base, 0x7d53cc, graphics, sprite, offset, 0, rect[2], rect[3]);
    button.board = board;
    button.pause = pause;
    button.x = rect[0] + offset;
    button.y = rect[1];
    button.width = rect[2];
    button.height = rect[3];
}

static bool speedButtonTouch(Word base, Byte *driver, Byte *app, Byte *board, const Touch &event) {
    auto &button = speedButton(base);
    if (event.phase == 4) {
        button.tracking = false;
        return false;
    }
    const bool tracked = button.tracking && button.pointerId == event.id;
    if (event.phase != 0 && !tracked) return false;
    const bool visible = board && button.board == board && playable(board) && !topModal(app)
        && !field<Byte>(driver, 0xdd) && native<bool>(base, 0x537ffc, button.pause);
    const bool enabled = visible && !dialogueActive(base, app);
    bool inside = false;
    if (visible) {
        Touch point;
        copyTouch(point, event);
        native<void>(base, 0x9e8340, driver, &point);
        inside = static_cast<Word>(point.x - button.x) < static_cast<Word>(button.width)
              && static_cast<Word>(point.y - button.y) < static_cast<Word>(button.height);
    }
    if (event.phase == 0) {
        if (!inside || button.tracking) return false;
        button.pointerId = event.id;
        button.tracking = true;
        button.armed = button.pressed = enabled;
        return true;
    }
    button.armed = button.armed && enabled;
    if (event.phase == 3) {
        button.tracking = false;
        if (inside && button.armed) toggleSpeed(base);
    } else {
        button.pressed = inside && button.armed;
    }
    return true;
}

static Byte *activePinch(Word base, Byte *app, Byte *board) {
    if (!board || !playable(board) || topModal(app)) return nullptr;
    Byte *input = field<Byte *>(board, 0x630);
    if (!input) return nullptr;
    Word begin = field<Word>(input, 0xc);
    Word end = field<Word>(input, 0x10);
    if (!begin || end < begin || end - begin > 24 * 64) return nullptr;
    for (Word address = begin; end - address >= 24; address += 24) {
        auto *delegate = reinterpret_cast<Byte *>(address);
        if (field<Word>(delegate, 4) != base + 0x462bd0 || field<Word>(delegate, 8) != 0
                || !field<Byte>(delegate, 0x10)) continue;
        Byte *powerup = field<Byte *>(delegate, 0xc);
        if (!powerup) continue;
        Word state = field<Word>(powerup, 0x24);
        if (state == 1 || state == 2) return powerup;
    }
    return nullptr;
}

static void pinchPointer(Word base, Byte *driver, Byte *app, Byte *board, const Touch &event) {
    auto &press = *reinterpret_cast<PinchPress *>(base + 0xdf9764);
    if (event.phase == 0) {
        if (press.powerup || field<Word>(driver, 0xc0) != field<Word>(driver, 0xc4)) {
            press.powerup = nullptr;
            return;
        }
        press = {activePinch(base, app, board), event.id, event.x, event.y};
        return;
    }
    if (event.phase == 4) {
        press.powerup = nullptr;
        return;
    }
    if (!press.powerup || press.id != event.id) return;

    // A small amount of mouse drift still counts as a click in WSA.
    int dx = event.x - press.x;
    int dy = event.y - press.y;
    if (dx < -24 || dx > 24 || dy < -24 || dy > 24) {
        press.powerup = nullptr;
        return;
    }
    if (event.phase == 3) {
        Byte *powerup = press.powerup;
        press.powerup = nullptr;
        if (powerup == activePinch(base, app, board)) {
            int center[2] = {event.x, event.y};
            // Route a synthetic pinch from the Android driver, including Board's zoom transform.
            native<void>(base, 0x9e8a08, driver, center, 0, -1.0f);
        }
    }
}

static void plantfoodAtPointer(Word base, Byte *driver, Byte *app, Byte *board, const Touch &source) {
    if (!field<Byte>(board, 0xc4) || source.previousX < 0 || source.previousY < 0) return;
    Touch point;
    copyTouch(point, source);
    point.x = source.previousX;
    point.y = source.previousY;
    native<void>(base, 0x9e8340, driver, &point);
    Byte *hit = native<Byte *>(base, 0x537174, point.x, point.y, 200);
    if (hit && hit != board) return;
    int local[2];
    int cell[2];
    boardPoint(base, board, point.x, point.y, local);
    if (!boardCell(base, app, board, local[0], local[1], cell)) return;

    Byte *cursor = field<Byte *>(board, 0x640);
    const bool temporary = !cursor;
    if (temporary) {
        if (!click(base, app, board, widget(base, "UIPlantfood"), source)
                || field<Byte *>(app, 0x6c0) != board || topModal(app)) return;
        cursor = field<Byte *>(board, 0x640);
    }
    if (!isType(base, cursor, 0x169510) || field<Word>(cursor, 0x14)) return;
    tap(app, board, source, point.x, point.y);
    if (temporary && field<Byte *>(app, 0x6c0) == board && field<Byte *>(board, 0x640) == cursor
            && !field<Word>(cursor, 0x14)) {
        native<void>(base, 0x192a1c, board);
    }
}

static Byte *seedSlot(Word base, Byte *board, int key) {
    int index = -1;
    if (key >= 8 && key <= 11) index = key - 8;
    if (key == 45) index = 4;
    if (key == 51) index = 5;
    if (key == 33) index = 6;
    if (key == 46) index = 7;
    const bool cycle = key == 54 || key == 52;
    if (index < 0 && !cycle) return nullptr;

    // Use the same live UI list as the original touch hit test. Scripted
    // tutorial cards can exist outside the ordinary seed-bank module.
    Word widgets[6];
    Byte *ui = *reinterpret_cast<Byte **>(base + 0xd4e964);
    if (!ui) return nullptr;
    native<void>(base, 0x365ec4, widgets, ui, 0x18u);
    auto *begin = reinterpret_cast<const Weak *>(widgets[2]);
    auto *end = reinterpret_cast<const Weak *>(widgets[3]);
    struct Card { Byte *widget; int x, y; };
    Card cards[32];
    int count = 0;
    for (const Weak *handle = begin; handle != end && count < 32; ++handle) {
        Byte *card = native<Byte *>(base, 0x1eb238, handle);
        if (!card || !native<bool>(base, 0x537ffc, card)) continue;
        int center[2];
        native<void>(base, 0x5385c0, center, card);
        int slot = count++;
        while (slot > 0 && (cards[slot - 1].y > center[1]
                || (cards[slot - 1].y == center[1] && cards[slot - 1].x > center[0]))) {
            cards[slot] = cards[slot - 1];
            --slot;
        }
        cards[slot] = {card, center[0], center[1]};
    }
    native<void>(base, 0x881b84, widgets);

    if (cycle) {
        index = 0;
        Byte *cursor = field<Byte *>(board, 0x640);
        if (isType(base, cursor, 0x169194)) {
            Byte *current = native<Byte *>(base, 0x1eb238, cursor + 0x18);
            for (int i = 0; current && i < count; ++i) {
                if (cards[i].widget != current) continue;
                index = i + (key == 54 ? -1 : 1);
                break;
            }
        }
    }
    return index >= 0 && index < count ? cards[index].widget : nullptr;
}

struct DisplayNameFont {
    int originalSize;
    Byte *font;
};

static Word createDisplayNameFont(Word base, Byte *factory, Byte *descriptor, Word index) {
    auto &nameFont = reinterpret_cast<DisplayNameFont *>(base + 0xdf9790)[index];
    auto &size = field<float>(descriptor, 0x200);
    const float reducedSize = size;
    if (size != nameFont.originalSize) {
        size = static_cast<float>(nameFont.originalSize);
        nameFont.font = native<Byte *>(base, 0xa315bc, factory, descriptor);
        size = reducedSize;
    } else {
        nameFont.font = nullptr;
    }
    return native<Word>(base, 0xa315bc, factory, descriptor);
}

extern "C" __attribute__((section(".text.entry")))
Word irisDesktop(Word base, Byte *driver, Touch *event, Word phase) {
    if (phase < 2) {
        drawPending(base, driver, reinterpret_cast<Byte *>(event), phase == 1);
#if IRIS_DARK_INPUT
        if (phase == 0) {
            auto callback = *reinterpret_cast<void (**)(Byte *, Byte *)>(base + 0xf81088);
            if (callback) callback(driver, reinterpret_cast<Byte *>(event));
            callback = *reinterpret_cast<void (**)(Byte *, Byte *)>(base + 0xf81854);
            if (callback) callback(driver, reinterpret_cast<Byte *>(event));
        }
#endif
        return false;
    }
    if (phase == 2) {
        drawSpeedButton(base, driver, reinterpret_cast<Byte *>(event));
        return false;
    }
    if (phase == 3) return beginCoinDraw(base, driver, reinterpret_cast<Byte *>(event));
    if (phase == 8) {
        const auto *args = reinterpret_cast<const Word *>(driver);
        auto *result = reinterpret_cast<const Word **>(args[0]);
        native<void>(base, 0x6aa094, result, args[1], args[2], args[3]);
        styleFontText(base, result, true);
        return false;
    }
    if (phase == 9) {
        auto *heading = reinterpret_cast<const Word **>(driver);
        native<void>(base, 0x6ab03c, heading, event);
        const Word first = **heading;
        *reinterpret_cast<Byte *>(base + 0xdf978c) = first >= 0xe000 && first <= 0xf8ff;
        return false;
    }
    if (phase == 10 || phase == 11) {
        auto *text = reinterpret_cast<const Word **>(driver);
        if (phase == 10) native<void>(base, 0xb77e28, text, event);
        else native<void>(base, 0x7a791c, text, reinterpret_cast<Word>(event));
        if (styledChooser(base)) styleFontText(base, text, false);
        return false;
    }
    if (phase == 12 || phase == 13) {
        return createDisplayNameFont(base, driver, reinterpret_cast<Byte *>(event), phase - 12);
    }
    Byte *app = field<Byte *>(driver, 0x44);
    if (!app || field<Word>(app, 0) != base + 0xcdd258) return false;
    Byte *board = field<Byte *>(app, 0x6c0);
    if (phase >= 16 && phase <= 20) {
        if (speedButtonTouch(base, driver, app, board, *event)) return true;
#if IRIS_DARK_INPUT
        if (board && playable(board) && !topModal(app) && !field<Byte>(driver, 0xdd)) {
            auto callback = *reinterpret_cast<Word (**)(Byte *, int, int, Word)>(base + 0xf81084);
            if (callback) {
                Touch point;
                copyTouch(point, *event);
                native<void>(base, 0x9e8340, driver, &point);
                int local[2];
                boardPoint(base, board, point.x, point.y, local);
                if (callback(board, local[0], local[1], event->phase)) return true;
            }
            auto theatre = *reinterpret_cast<Word (**)(Byte *, int, int, Word)>(base + 0xf81850);
            if (theatre) {
                Touch point; copyTouch(point, *event); native<void>(base, 0x9e8340, driver, &point);
                int local[2]; boardPoint(base, board, point.x, point.y, local);
                if (theatre(board, local[0], local[1], event->phase)) return true;
            }
        }
#endif
        pinchPointer(base, driver, app, board, *event);
        return false;
    }
    if (!board || field<Byte>(driver, 0xdd)) return false;
    Byte *modal = topModal(app);
    if (event->phase == 6 && event->x == 62 && paused(board)) {
        Byte *menu = field<Byte *>(app, 0xbc4);
        if (menu && modal == menu) {
            native<void>(base, 0x2bd798, app);
            native<void>(base, 0x17d1bc, board, 0);
        }
        return false;
    }
    if (!playable(board) || modal) return false;
#if IRIS_DARK_INPUT
    if (event->phase == 5 || event->phase == 6) {
        auto callback = *reinterpret_cast<Word (**)(Byte *, int, int, Word)>(base + 0xf81084);
        if (callback) {
            Touch point;
            copyTouch(point, *event);
            if (event->phase == 5) {
                native<void>(base, 0x9e8340, driver, &point);
                int local[2];
                boardPoint(base, board, point.x, point.y, local);
                point.x = local[0];
                point.y = local[1];
            }
            if (callback(board, point.x, point.y, event->phase)) return false;
        }
        auto theatre = *reinterpret_cast<Word (**)(Byte *, int, int, Word)>(base + 0xf81850);
        if (theatre) {
            Touch point; copyTouch(point, *event);
            if (event->phase == 5) {
                native<void>(base, 0x9e8340, driver, &point);
                int local[2]; boardPoint(base, board, point.x, point.y, local);
                point.x = local[0]; point.y = local[1];
            }
            if (theatre(board, point.x, point.y, event->phase)) return false;
        }
    }
#endif
    if (event->phase == 5) {
        native<void>(base, 0x9e8340, driver, event);
        moveCursor(base, app, board, *event);
        collect(base, app, board, *event, false);
        return false;
    }

    if (event->x == 100) {
        Byte *cursor = field<Byte *>(board, 0x640);
        if (cursor && !field<Word>(cursor, 0x14)) {
            preview(base).cursor = nullptr;
            native<void>(base, 0x192a1c, board);
        }
        return false;
    }
    if (event->x == 29) { // A
        collect(base, app, board, *event, true);
        return false;
    }
    if (event->x == 50) { // V
        if (!dialogueActive(base, app)) toggleSpeed(base);
        return false;
    }
    if (event->x == 101) {
        plantfoodAtPointer(base, driver, app, board, *event);
        return false;
    }

    const char *name = nullptr;
    switch (event->x) {
        case 32: name = "UIShovel"; break;     // D
        case 34: name = "UIPlantfood"; break;  // F
        case 62: name = "UIPauseButton"; break; // Space
    }
    Byte *control = nullptr;
    switch (event->x) {
        case 30: control = powerupButton(base, "PowerupPinchZombie"); break;  // B
        case 42: control = powerupButton(base, "PowerupFlickZombie"); break;  // N
        case 41: control = powerupButton(base, "PowerupWizardFinger"); break; // M
        default: control = name ? widget(base, name) : seedSlot(base, board, event->x);
    }
    if (click(base, app, board, control, *event) && field<Byte *>(app, 0x6c0) == board)
        restoreHover(base, driver, app, board, *event);
    return false;
}
