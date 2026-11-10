#include <jni.h>
#include <link.h>
#include <cstdint>
#include <cstring>

static int findGame(dl_phdr_info *info, size_t, void *output) {
    if (!info->dlpi_name) return 0;
    const char *leaf = std::strrchr(info->dlpi_name, '/');
    if (std::strcmp(leaf ? leaf + 1 : info->dlpi_name, "libPVZ2.so") != 0) return 0;
    *static_cast<std::uintptr_t *>(output) = info->dlpi_addr;
    return 1;
}

extern "C" JNIEXPORT jlong JNICALL
Java_com_popcap_SexyAppFramework_IrisSpeedFeedback_poll(JNIEnv *, jclass) {
    // The game and renderer call this on the same GL thread as the input patch.
    static std::uintptr_t base = 0;
    if (!base) dl_iterate_phdr(findGame, &base);
    if (!base) return 0;
    auto &pending = *reinterpret_cast<volatile std::uint32_t *>(base + 0xdf9774);
    std::uint32_t mode = pending;
    if (!mode) return 0;
    pending = 0;

    auto *app = **reinterpret_cast<const unsigned char *const *const *>(base + 0xd00838);
    // SexyAppBase's SfxVolume, as used by the original options slider.
    float gain = app ? static_cast<float>(*reinterpret_cast<const double *>(app + 0x88)) : 0.0f;
    std::uint32_t gainBits;
    std::memcpy(&gainBits, &gain, sizeof(gainBits));
    return static_cast<jlong>((static_cast<std::uint64_t>(gainBits) << 32) | mode);
}
