#pragma once

#include <cstddef>
#include <cstdint>

namespace iris::recovered {

// ARM32 object passed to the original touch callbacks at 0x009f0298.
struct alignas(8) TouchEvent {
    std::uint32_t id;
    std::uint32_t reserved;
    std::int32_t x;
    std::int32_t y;
    std::int32_t previousX;
    std::int32_t previousY;
    std::int32_t tapCount;
    double timestamp;
    std::uint32_t phase;
};

static_assert(offsetof(TouchEvent, timestamp) == 32);
static_assert(offsetof(TouchEvent, phase) == 40);
static_assert(sizeof(TouchEvent) == 48);

inline constexpr std::size_t touchPacketSize = 48;

enum class TouchRoute {
    ignored,
    began,
    moved,
    ended,
    cancelled,
};

// Read a complete little-endian touch packet and identify the original handler.
// The original dispatcher trusts the buffer length. This interface also handles
// truncated packets, leaving the cursor and event untouched on failure.
bool readTouchEvent(const std::uint8_t*& cursor, std::size_t remaining, TouchEvent& event);
TouchRoute originalTouchRoute(std::uint32_t phase);

// Eight signed fields at offset 0xb0 of the original coordinate transform.
struct TouchCoordinateTransform {
    std::int32_t destinationX;
    std::int32_t destinationY;
    std::int32_t destinationWidth;
    std::int32_t destinationHeight;
    std::int32_t sourceX;
    std::int32_t sourceY;
    std::int32_t sourceWidth;
    std::int32_t sourceHeight;
};

static_assert(sizeof(TouchCoordinateTransform) == 32);

// The original function at 0x009d9390 updates both axes only if both divisors exist.
void transformTouchCoordinates(const TouchCoordinateTransform& transform, std::int32_t& x, std::int32_t& y);

struct BoardTouchTransform {
    std::int32_t offsetX; // Board + 0x28
    std::int32_t offsetY; // Board + 0x2c
    float scale;          // Board + 0x678
    float originX;        // Board + 0x67c
    float originY;        // Board + 0x680
};

// Board point conversion at 0x001841fc, used by the Iris desktop hover hook.
void transformBoardTouch(const BoardTouchTransform& transform, std::int32_t& x, std::int32_t& y);

} // namespace iris::recovered
