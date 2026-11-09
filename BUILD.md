# Iris 构建说明

## 基线

| 项目 | 样本值 |
| --- | --- |
| 包名与版本 | `com.ea.game.pvz2_na` · `1.6.257161` · `versionCode 8` |
| Android SDK | `minSdk 9` · `targetSdk 18` |
| 启动 Activity | `com.popcap.PvZ2.PvZ2GameActivity` |
| 原生引擎 | `lib/armeabi-v7a/libPVZ2.so`，ARM32 |
| 扩展资源 | `assets/extobb.save` 内的 `main.7.com.ea.game.pvz2_na.obb`，RSB v4，588 个资源组 |
| 下载器数据 | `assets/data.save` 内的 `databases/DownloadsDB` |

样本签名校验通过，但签名证书标识为 Android 调试证书，DEX 包含 `com.savegame.SavesRestoring`，因此以这份提供的 APK 为基线，官方原包出处未确认。原生库与 CN 版的 `libSrc.so` 不同。CN 的构建和逆向工具可以复用，原生补丁需要按 EN 引擎重新定位。

## 生成本地分析目录

需要 Python 3.11+、Java、Apktool 2.10.0 和 Android SDK Build Tools。当前机器可用以下命令。将 Apktool 2.10.0 放到 `tools/apktool.jar`。运行 `prepare_baseline.py` 时也可用 `--apktool` 指向现有副本。构建 APK 时使用 `tools/apktool.jar`。

```powershell
python scripts/prepare_baseline.py --build-tools Y:/Android/Sdk/build-tools/34.0.0
```

脚本核对原始 APK 的 SHA-256 和签名，导出 Manifest 与 Smali、内置 OBB、下载器数据库、RSB 资源组名以及文件哈希。默认输出 `work/baseline/`。重复运行时指定新的 `--output` 目录。

已用 Apktool 从解包结果重建未签名 APK。包名、版本、启动入口和 ABI 与样本一致。引擎及两个内置容器均逐字节核对一致。

## 基线启动路径

`PvZ2GameActivity.onCreate` 在检查扩展文件前调用 `SavesRestoring.DoSmth`，后者将内置 OBB 解包到应用的 `getObbDir()`。`FrameworkInfo_SysGetMainExpansionFilePath` 则从下载器数据库的主扩展条目定位文件。数据库记载 `217845760` 字节，随包 OBB 实际为 `170442752` 字节。现有 `expansionFileDelivered` 只检查路径和文件是否存在。尺寸差异是否影响后续加载，需要在设备上验证。

## 语言表与 ZH 素材移植

本地工具依赖 Pillow、`texture2ddecoder`、CN 工作区的 RSB 代码，以及 [PyVZ2](https://github.com/nineteendo/pyvz2) 的 RTON 解码器。当前使用 PyVZ2 提交 `5bdd06336691c53d6963e7f5527f034014cf641d`，放在忽略目录 `tools/pyvz2/`。以本地 ZH v162 APK 为素材输入。

```powershell
python -m pip install Pillow texture2ddecoder fonttools
git clone https://github.com/EndiVee233/PvZ2-Unline-Aster.git ../PvZ2-Unline-Aster
git clone https://github.com/nineteendo/pyvz2.git tools/pyvz2
git -C tools/pyvz2 checkout 5bdd06336691c53d6963e7f5527f034014cf641d
python scripts/prepare_localized_resources.py --cn-workspace ../PvZ2-Unline-Aster --cn-apk Y:/pvz2-builds/v162/PvZ2-Unline-v162.apk
```

- 语言工具导出 EN 内置的六个语言表。可用 `--overlays <目录>` 将 `en-US.json` 等语言文件中的键值覆盖写回 OBB，保留原有占位符和格式标记。`zh-CN.draft.json` 是按共同键和占位符生成的审校稿，缺项使用英语原文。
- 首批替换豌豆射手、向日葵、坚果和卷心菜投手的 1536 档图集部件。按资源 ID、尺寸、偏移和像素相似度筛选 ZH 素材。沿用 EN 图集尺寸、坐标和动画，写回原引擎已有的 RGBA8888 格式，避免替换后再次压成 ETC1。EN 独有部件、其他贴图及低分辨率档保留原资源。
- 仅审计本地 ZH 音频。EN 与 ZH 的同名音乐音频库使用不同版本的 Wwise 格式。已匹配的五段同 ID 流式素材在 ZH 为 8 kHz 单声道，低于 EN 的 32–48 kHz，因此保留 EN 音乐和音频事件。

生成物位于 `work/localized/`，包含可供后续 EN 构建接入的 OBB 和 `extobb.save`，以及前后预览和逐项报告。脚本重读并校验资源表、替换内容和无关分组。游戏内效果待验证。

## Iris 构建

Iris 使用 EN 1.6.257161 的原生引擎，将内置扩展包验证并解压到应用私有目录，存档也使用应用私有目录。Google Play 服务检查、登录、云存档、成就、排行榜、推送注册组件、旧扩展下载器与 Google Play 支付不参与运行。原生 JNI 依赖的 Java 接口保留，并返回离线状态。应用沿用 `com.ea.game.pvz2_na` 和此前 Lite 的签名，可覆盖安装 Lite。

原设置页的 Help 入口改为 Language，沿用原版列表。支持英语、德语、西班牙语、法语、意大利语、巴西葡萄牙语和简体中文，重启游戏后生效。简体中文借用 Aster 的同键文本和字体，缺少对应译文或格式占位符不同的文本仍使用英语。

| 简体中文界面 | 字体来源 |
| --- | --- |
| 按钮、玩家名牌、教程提示、世界地图普通弹窗 | `FZY4JW.TTF` |
| 关卡标题 | `FZKATJW.TTF` |
| 星系页世界名 | `FZSEJW.TTF` |
| 阳光、卡牌费用及 HUD 数字槽 | `FBUSV8C5EI.TTF` |
| 显式标出说话者的戴夫、潘妮、僵王台词 | 依 Aster 的 NPC 配置使用 `BRIANNE.TTF`、`PICO.TTF`、`ASHLEYSCRIPT.TTF` |

Iris 在共享字体槽中为选定文案指定字形，关卡号、玩家名等运行时填入的内容继续由原控件绘制。

可用 `--row-obb` 接入从国际服安装包提取的 OBB。此次使用国际服 13.5.2（1064）。在通过尺寸、偏移和相似度检查的情况下，优先使用 ZH 图集，其次从国际服补齐。参见 [国际服安装包页面](https://www.apkmirror.com/apk/electronic-arts/plants-vs-zombies-2-2/plants-vs-zombies-2-international-13-5-2-release/plants-vs-zombies-2-international-13-5-2-android-apk-download/)。

```powershell
python scripts/prepare_localized_resources.py --cn-workspace ../PvZ2-Unline-Aster --cn-apk Y:/pvz2-builds/v162/PvZ2-Unline-v162.apk --row-obb work/donor/row-13.5.2.obb --output work/localized-row
python scripts/build_lite.py --jdk "$env:JAVA_HOME" --sdk "$env:ANDROID_HOME" --expansion work/localized-row/main.7.com.ea.game.pvz2_na.obb --cn-apk Y:/pvz2-builds/v163/PvZ2-Unline-Aster-v163.apk --output work/iris
```

构建需要 JDK 21、Android SDK 34、Build Tools 34.0.0 和 NDK 27.0.12077973。将 `JAVA_HOME` 和 `ANDROID_HOME` 设为本机工具链目录，并按本机情况替换示例的 APK 路径。Aster 目录可用 `--cn-workspace` 指定。输出是本地签名 APK。签名密钥、素材和备份均位于已忽略的 `work/` 目录。

## 单独编译恢复的原生代码

原生静态库可以独立构建。使用 CMake 3.16+ 和支持 C++17 的编译器。下面以 Android NDK ARMv7 构建为例，`ANDROID_NDK_HOME` 指向 NDK 目录。命令在 Iris 仓库根目录运行。

```powershell
cmake -S src/recovered/native -B work/native-recovered -G Ninja "-DCMAKE_TOOLCHAIN_FILE=$env:ANDROID_NDK_HOME/build/cmake/android.toolchain.cmake" -DANDROID_ABI=armeabi-v7a -DANDROID_PLATFORM=android-21 -DCMAKE_BUILD_TYPE=Release
cmake --build work/native-recovered
```

输出为 `libiris_native_recovered.a`。ARM 对照需要原始北美 APK，详见[验证命令](docs/source-recovery.md)。
