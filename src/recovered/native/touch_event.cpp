#include "touch_event.hpp"

#include <cmath>
#include <cstring>
#include <limits>

namespace iris::recovered {
namespace {

std::uint32_t readWord(const std::uint8_t* data) {
    return std::uint32_t(data[0]) | (std::uint32_t(data[1]) << 8) |
           (std::uint32_t(data[2]) << 16) | (std::uint32_t(data[3]) << 24);
}

std::int32_t signedWord(std::uint32_t bits) {
    std::int32_t value;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

std::int32_t readSignedWord(const std::uint8_t* data) {
    return signedWord(readWord(data));
}

std::int32_t transformAxis(std::int32_t point, std::int32_t sourceOrigin, std::int32_t sourceExtent,
                           std::int32_t destinationOrigin, std::int32_t destinationExtent) {
    // ARM SUB, MUL and ADD retain the low 32 bits.
    const auto delta = std::uint32_t(point) - std::uint32_t(sourceOrigin);
    const auto numerator = signedWord(delta * std::uint32_t(destinationExtent));
    const auto minimum = std::numeric_limits<std::int32_t>::min();
    const auto scaled = numerator == minimum && sourceExtent == -1 ? minimum : numerator / sourceExtent;
    return signedWord(std::uint32_t(destinationOrigin) + std::uint32_t(scaled));
}

std::int32_t transformBoardAxis(std::int32_t point, std::int32_t offset, float origin, float scale) {
    const auto floatOffset = static_cast<float>(offset);
    const auto relative = (floatOffset + (static_cast<float>(point) - origin)) / scale;
    const auto translated = double(origin - floatOffset) + double(std::floor(relative));

    // VCVT.S32.F64 rounds toward zero, saturates overflow, and maps NaN to zero.
    if (std::isnan(translated)) {
        return 0;
    }
    if (translated >= std::numeric_limits<std::int32_t>::max()) {
        return std::numeric_limits<std::int32_t>::max();
    }
    if (translated <= std::numeric_limits<std::int32_t>::min()) {
        return std::numeric_limits<std::int32_t>::min();
    }
    return static_cast<std::int32_t>(translated);
}

} // namespace

bool readTouchEvent(const std::uint8_t*& cursor, std::size_t remaining, TouchEvent& event) {
    if (remaining < touchPacketSize) {
        return false;
    }
    const auto timestampBits = std::uint64_t(readWord(cursor + 28)) |
                               (std::uint64_t(readWord(cursor + 32)) << 32);
    double timestamp;
    std::memcpy(&timestamp, &timestampBits, sizeof(timestamp));
    event = {
        readWord(cursor + 4),
        0,
        readSignedWord(cursor + 8),
        readSignedWord(cursor + 12),
        readSignedWord(cursor + 16),
        readSignedWord(cursor + 20),
        readSignedWord(cursor + 24),
        timestamp,
        readWord(cursor + 36),
    };
    cursor += touchPacketSize;
    return true;
}

TouchRoute originalTouchRoute(std::uint32_t phase) {
    switch (phase) {
        case 0: return TouchRoute::began;
        case 1: return TouchRoute::moved;
        case 3: return TouchRoute::ended;
        case 4: return TouchRoute::cancelled;
        default: return TouchRoute::ignored;
    }
}

void transformTouchCoordinates(const TouchCoordinateTransform& transform, std::int32_t& x, std::int32_t& y) {
    if (transform.sourceWidth == 0 || transform.sourceHeight == 0) {
        return;
    }
    x = transformAxis(x, transform.sourceX, transform.sourceWidth,
                      transform.destinationX, transform.destinationWidth);
    y = transformAxis(y, transform.sourceY, transform.sourceHeight,
                      transform.destinationY, transform.destinationHeight);
}

void transformBoardTouch(const BoardTouchTransform& transform, std::int32_t& x, std::int32_t& y) {
    x = transformBoardAxis(x, transform.offsetX, transform.originX, transform.scale);
    y = transformBoardAxis(y, transform.offsetY, transform.originY, transform.scale);
}

} // namespace iris::recovered
