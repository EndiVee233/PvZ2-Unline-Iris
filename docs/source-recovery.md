# Iris 源码恢复

在 Iris 的 `en` 分支进行。以原始北美 APK 1.6.257161 的 DEX、Smali 和 `libPVZ2.so` 为依据，用本地 `work/iris-10-wsa/PvZ2-Unline-Iris.apk` 对照 Iris 已有的离线与桌面输入行为。

## 第三轮

- [SexyAppFrameworkActivity.java](../src/recovered/java/com/popcap/SexyAppFramework/SexyAppFrameworkActivity.java)、[AndroidSplashScreen.java](../src/recovered/java/com/popcap/SexyAppFramework/AndroidSplashScreen.java)和 [AndroidAssetUtils.java](../src/recovered/java/com/popcap/SexyAppFramework/AndroidAssetUtils.java)及内部类由 Java 构建。原有离线扩展包路径和桌面键盘状态桥接随 Activity 移入源码。累计 28 个类由 Java 构建，APK 总计 1,495 个 DEX 类。
- [touch_event.cpp](../src/recovered/native/touch_event.cpp)新增棋盘触点坐标转换 `0x001841fc`，对应桌面悬停使用的原生函数。对照覆盖非整数缩放、负值、零缩放、NaN 与饱和边界。71 组对照在 `floorf` 调用边界给原版与恢复代码提供相同结果。伪代码在 `work/source-recovery/native-round3/board_touch_coordinates.c`。
- 本地重建通过签名、对齐和 DEX 声明检查。原生库、内置 OBB 和中文差分数据与 Iris 10 一致。CMake 已成功生成 ARMv7 静态库。此次未启动游戏。

## 第二轮

- [AndroidSurfaceView.java](../src/recovered/java/com/popcap/SexyAppFramework/AndroidSurfaceView.java)及其 5 个内部类、输入法连接、EGL 配置选择器和三个 GLES 渲染器由 Java 构建，取代另外 11 个 Smali 类。鼠标悬停、右键与键盘拦截移入 Java。GLSurfaceView 生命周期及三个私有 JNI 回调保留原签名。
- 已迁移的 21 个类位于 `classes2.dex`，两个 DEX 合计仍有 1,495 个类。活动类仍由 Smali 构建。javac 通过 Aster 的 DEX 声明生成器读取其接口，临时声明 JAR 仅用于编译。
- [touch_event.cpp](../src/recovered/native/touch_event.cpp)加入原生坐标变换 `0x009d9390` 的 C++ 实现。该函数从偏移 `0xb0` 读取两个矩形的原点和尺寸。任一源尺寸为零时两个坐标都保持原值，其余输入使用 ARM32 的 32 位回绕和有符号除法。Ghidra 伪代码在 `work/source-recovery/native-round2/touch_coordinates.c`。
- APK 签名和对齐通过。DEX 对照验证了迁移类的继承关系、非私有字段及方法（含私有 JNI 方法）的签名和标志。原生库、内置 OBB 和中文差分数据与 `iris-10-wsa` 逐字节一致。
- Java 探针通过输入队列和 EGL 属性过滤、候选排序、EGL 失败分支检查。70 组 ARM 坐标对照覆盖负值、32 位回绕、零尺寸和坐标参数别名。未启动游戏，C++ 仍独立于 APK 中的原生引擎。

## 第一轮

| 层 | 本轮产物 |
| --- | --- |
| Java 反编译 | 原包 1,487 个 DEX 类，JADX 导出 659 个 Java 文件。Iris 对照包 1,495 个 DEX 类，导出 661 个 Java 文件。JADX 报出部分代码重组警告，相关实现仍须与 Smali 核对。 |
| Java 重建 | [AndroidUIEventManager.java](../src/recovered/java/com/popcap/SexyAppFramework/AndroidUIEventManager.java)及其 9 个内部类由现有 Iris 构建编译并写入 `classes2.dex`。保留触屏、手势、按键、文字输入、焦点、缓冲不足时重试及 Iris 桌面事件。 |
| 原生分析 | Ghidra 工程在 `work/iris-ghidra/IrisNA.gpr`。`work/source-recovery/native-verified/` 有 28,270 条函数索引，以及 JNI 加载、卸载、触摸分派和四条触摸回调的伪代码。 |
| 原生重建 | [touch_event.cpp](../src/recovered/native/touch_event.cpp)恢复 48 字节触摸包的读取、ARM32 参数布局和原版 phase 分派。恢复接口增加了长度校验。APK 仍链接已有的 `libPVZ2.so`，包括 Iris 原有桌面输入补丁。 |

原版分派入口的 ELF 地址为 `0x009f0298`。phase 0、1、3、4 分别进入 `0x009e8208`、`0x009e8378`、`0x009e8528`、`0x009e8828`。原版忽略 phase 2 和大于 4 的值。Iris 现有补丁在 `0x009f0310` 接管 phase 5 和 6，分别用于桌面指针位置与按键命令。结构中偏移 28 到 31 的 ARM 对齐字节由原函数留空。

## 本地复现

使用 Aster 的 Apktool 和 DEX 声明解析器，按 Aster 的分析记录使用 JADX 1.5.6 和 Ghidra 11.3.2。当前目录为 Iris 根目录，`$env:JAVA_HOME` 指向 JDK 21。原包解包目录为 `work/baseline/decoded`，按[构建说明](../BUILD.md)的 `prepare_baseline.py` 命令生成。[JADX 1.5.6 发布页](https://github.com/skylot/jadx/releases/tag/v1.5.6)

```powershell
$java = "$env:JAVA_HOME\bin\java.exe"
$jadx = 'tools/jadx/lib/jadx-1.5.6-all.jar'
$ghidra = 'tools/ghidra/ghidra_11.3.2_PUBLIC/support/analyzeHeadless.bat'
New-Item -ItemType Directory -Force work/source-recovery, work/iris-ghidra | Out-Null
& $java -cp $jadx jadx.cli.JadxCLI -r --show-bad-code -d work/source-recovery/baseline-java 'Plants+Vs+Zombies+2_1.6.257161na.apk'
& $java -cp $jadx jadx.cli.JadxCLI -r --show-bad-code -d work/source-recovery/iris-java work/iris-10-wsa/PvZ2-Unline-Iris.apk
& $ghidra work/iris-ghidra IrisNA -import work/baseline/decoded/lib/armeabi-v7a/libPVZ2.so -max-cpu 4 -analysisTimeoutPerFile 360 -log work/iris-ghidra/analysis.log
& $ghidra work/iris-ghidra IrisNA -process libPVZ2.so -noanalysis -readOnly -scriptPath scripts/ghidra -postScript ExportIrisNative.java work/source-recovery/native-round3
```

本轮构建使用已有的 `localized-row2` 资源和 Aster v163 语言与字体素材。构建目录需为新目录。校验脚本读取相邻 Aster 目录的 DEX 工具，可用 `--aster` 指定路径。ARM 对照需要 Python 的 `pyelftools`、`unicorn` 和本机 Android NDK。

```powershell
python scripts/build_lite.py --jdk "$env:JAVA_HOME" --expansion work/localized-row2/main.7.com.ea.game.pvz2_na.obb --cn-workspace ../PvZ2-Unline-Aster --cn-apk Y:/pvz2-builds/v163/PvZ2-Unline-Aster-v163.apk --output work/iris-recovered-round3
python scripts/check_recovered_apk.py work/iris-10-wsa/PvZ2-Unline-Iris.apk work/iris-recovered-round3/PvZ2-Unline-Iris.apk
python scripts/check_recovered_touch.py --ndk Y:/Android/Sdk/ndk/27.0.12077973

$android = 'Y:/Android/Sdk/platforms/android-34/android.jar'
$classes = 'work/iris-recovered-round3/classes'
$probe = 'work/source-recovery/java-test-r3'
New-Item -ItemType Directory -Force $probe | Out-Null
& "$env:JAVA_HOME\bin\javac.exe" --release 8 -cp "$classes;$android" -d $probe src/recovered/tests/TouchQueueCheck.java src/recovered/tests/GraphicsConfigChooserCheck.java src/recovered/tests/AssetPathCheck.java src/recovered/tests/fixtures/javax/microedition/khronos/egl/EGLConfig.java
& $java -ea -cp "$probe;$classes;$android" com.popcap.SexyAppFramework.TouchQueueCheck
& $java -ea -cp "$probe;$classes;$android" com.popcap.SexyAppFramework.GraphicsConfigChooserCheck
& $java -ea -cp "$probe;$classes;$android" com.popcap.SexyAppFramework.AssetPathCheck
```

## 第一轮验证结果

- APK 签名与对齐通过。两个 DEX 共 1,495 个类且无重复，只有输入管理器的 10 个类迁移到第二个 DEX。其非私有、非合成的字段和方法签名与对照包一致。原生库、内置 OBB 和中文差分数据逐字节一致。
- Java 探针验证了焦点、桌面 hover 和命令、文字事件、触摸取消以及缓冲不足后重试。ARM 仿真在原版回调入口处截获参数，对照 27 组分派和解包结果，另验证 48 个截断长度。
- 本轮未启动游戏。其余 Java 类仍由原有 Smali 重建。渲染、游戏循环、存档和关卡逻辑仍在原生引擎中。
