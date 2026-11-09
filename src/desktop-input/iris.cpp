// Iris 1.6.257161 ARMv7. This runs on the original game's input thread.
using Byte = unsigned char;
using Word = unsigned int;

struct Touch {
    Word id, pad;
    int x, y, previousX, previousY;
    Word taps, padding, time[2], phase;
};

template<class T> T &field(Byte *object, Word offset) {
    return *reinterpret_cast<T *>(object + offset);
}

template<class R, class... Args>
R native(Word base, Word offset, Args... args) {
    return reinterpret_cast<R (*)(Args...)>(base + offset)(args...);
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

static void touch(Byte *app, Word slot, Touch *event) {
    Byte *table = field<Byte *>(app, 0);
    field<void (*)(Byte *, Touch *)>(table, slot)(app, event);
}

static bool click(Word base, Byte *app, Byte *board, Byte *control, Touch &event) {
    if (!control || !native<bool>(base, 0x537ffc, control)) return false;
    int center[2];
    native<void>(base, 0x5385c0, center, control);
    if (native<Byte *>(base, 0x537174, center[0], center[1], 200) != control) return false;

    event.id = 0x7ffffffe;
    event.taps = 1;
    event.x = event.previousX = center[0];
    event.y = event.previousY = center[1];
    event.phase = 0;
    touch(app, 0x1b0, &event);
    if (field<Byte *>(app, 0x6c0) == board) {
        event.phase = 3;
        touch(app, 0x1b4, &event);
    }
    return true;
}

static void moveCursor(Word base, Byte *board, int x, int y) {
    Byte *cursor = field<Byte *>(board, 0x640);
    if (!cursor || field<Byte>(cursor, 0x10) || field<Word>(cursor, 0x14)) return;
    int point[2] = {x, y};
    native<void>(base, 0x1841fc, board, point);
    field<float>(cursor, 4) = point[0];
    field<float>(cursor, 8) = point[1];
}

static Byte *seedSlot(Word base, Byte *board, int key) {
    if (!field<Byte *>(board, 0x62c)) return nullptr;
    Byte *bank = native<Byte *>(base, 0x17a22c, board);
    if (!bank || !native<bool>(base, 0x537ffc, bank)) return nullptr;
    Word begin = field<Word>(bank, 0x120);
    Word end = field<Word>(bank, 0x124);
    if (!begin || end < begin || end - begin > 32 * 64 || (end - begin) % 64) return nullptr;

    struct Card { Byte *widget; int y; };
    Card cards[32];
    int count = 0;
    for (Word address = begin; address < end; address += 64) {
        Byte *card = native<Byte *>(base, 0x1eb238, reinterpret_cast<Byte *>(address) + 0x28);
        if (!card || !native<bool>(base, 0x537ffc, card)) continue;
        // Scripted/gift cards are separate from this bank's primary card vector.
        int center[2];
        native<void>(base, 0x5385c0, center, card);
        int index = count++;
        while (index > 0 && cards[index - 1].y > center[1]) {
            cards[index] = cards[index - 1];
            --index;
        }
        cards[index] = {card, center[1]};
    }

    int index = -1;
    if (key >= 8 && key <= 11) index = key - 8;
    if (key == 45) index = 4;
    if (key == 51) index = 5;
    if (key == 33) index = 6;
    if (key == 46) index = 7;
    if (key == 54 || key == 52) {
        index = 0;
        Byte *cursor = field<Byte *>(board, 0x640);
        if (cursor && field<Word>(cursor, 0) == base + 0xce2208) {
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

extern "C" __attribute__((section(".text.entry")))
void irisDesktop(Word base, Byte *driver, Touch *event) {
    Byte *app = field<Byte *>(driver, 0x44);
    if (!app || field<Word>(app, 0) != base + 0xcdd258) return;
    Byte *board = field<Byte *>(app, 0x6c0);
    if (!board || field<Byte>(driver, 0xdd)) return;

    const Word state = field<Word>(board, 0xa8);
    if (state != 4 && state != 5) return;
    if (event->phase == 5) {
        native<void>(base, 0x9e8340, driver, event);
        moveCursor(base, board, event->x, event->y);
        return;
    }

    if (event->x == 100) {
        Byte *cursor = field<Byte *>(board, 0x640);
        if (cursor && !field<Word>(cursor, 0x14))
            native<void>(base, 0x192a1c, board);
        return;
    }

    const char *name = nullptr;
    switch (event->x) {
        case 32: name = "UIShovel"; break;     // D
        case 34: name = "UIPlantfood"; break;  // F
        case 62: name = "UIPauseButton"; break; // Space
    }
    Byte *control = name ? widget(base, name) : seedSlot(base, board, event->x);
    click(base, app, board, control, *event);
}
