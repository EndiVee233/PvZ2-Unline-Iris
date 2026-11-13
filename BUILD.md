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
python -m pip install Pillow texture2ddecoder fonttools py3rijndael pyelftools unicorn capstone
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
| 主菜单及玩家管理标题、按钮、选卡、暂停、星系和奖励标题 | `FZSEJW.TTF` |
| 玩家名牌、教程说明、确认框正文、图鉴和商店说明 | `FZY4JW.TTF` |
| 关卡标题、开战倒数和波次警告 | `FZKATJW.TTF` |
| 阳光、卡牌费用及 HUD 数字槽 | `FBUSV8C5EI.TTF` |
| 疯狂戴夫的台词 | `FZKATJW.TTF` |
| 潘妮、僵王头像的台词 | `FZY4JW.TTF` |

Iris 在共享字体槽中为选定文案指定字形，关卡号、玩家名等运行时填入的内容继续由原控件绘制。

可用 `--row-obb` 接入从国际服安装包提取的 OBB。此次使用国际服 13.5.2（1064）。在通过尺寸、偏移和相似度检查的情况下，优先使用 ZH 图集，其次从国际服补齐。参见 [国际服安装包页面](https://www.apkmirror.com/apk/electronic-arts/plants-vs-zombies-2-2/plants-vs-zombies-2-international-13-5-2-release/plants-vs-zombies-2-international-13-5-2-android-apk-download/)。

```powershell
python scripts/prepare_localized_resources.py --cn-workspace ../PvZ2-Unline-Aster --cn-apk Y:/pvz2-builds/v162/PvZ2-Unline-v162.apk --row-obb work/donor/row-13.5.2.obb --output work/localized-row
python scripts/build_lite.py --jdk "$env:JAVA_HOME" --sdk "$env:ANDROID_HOME" --expansion work/localized-row/main.7.com.ea.game.pvz2_na.obb --cn-apk Y:/pvz2-builds/v163/PvZ2-Unline-Aster-v163.apk --output work/iris
```

构建需要 JDK 21、Android SDK 34、Build Tools 34.0.0 和 NDK 27.0.12077973。将 `JAVA_HOME` 和 `ANDROID_HOME` 设为本机工具链目录，并按本机情况替换示例的 APK 路径。Aster 目录可用 `--cn-workspace` 指定。输出是本地签名 APK。签名密钥、素材和备份均位于已忽略的 `work/` 目录。

使用 `--custom-font <本地 TTF 路径>` 可指定简体中文选卡页、旅程标题、暂停标题和音量标签的字体。其他按钮的字形来自 Aster 的 `FZKATJW.TTF`。旅程标题会在游戏填入玩家名后替换其中的 ASCII 字形。

简体中文构建默认使用 `src/locales/zh-CN.json`。可用 `--zh-cn <JSON 路径>` 测试另一份译文。修改文本时保留键名和格式占位符。

恢复未来世界时，在构建命令中加入 `--future-obbs <ROW 1.4.244592 OBB> <ROW 2.1.1 OBB>`。脚本校验两份 OBB 的 SHA-256，优先从 1.4 提取原生地图、背景和角色资源，再用 2.1.1 补齐缺失组。Iris 自带的世界地图、星门条件、关卡波次和支线路线仍作为游戏配置使用。

构建从 Aster 提取未来战场背景、香橼命中采样，以及机甲巨人的本体、激光动画、整套贴图和音效采样。机甲巨人属性按 Iris 引擎支持的字段移植，沿用 Iris 的波次选择和出怪权重。巨人在充能、扫射和收招期间停止行走，光束只在扫射阶段从眼部画到命中点。每只巨人用一个灼痕跟随当前落点，并在收招或中断时触发 Aster 的结束音效。香橼动画和适配旧 Wwise 引擎的音效结构由 ROW 2.1.1 提供。音乐使用与 Aster 对应的正式版未来世界音轨，保留 Iris 的播放事件、音量和波次切换。

`--dark-ages` 额外接入黑暗时代资源、音乐和经过兼容审查的 Aster 关卡。关卡来源、特殊关卡和归档副本见 [黑暗时代关卡清单](docs/dark-ages-level-status.md)。构建核对 `src/dark/levels.json` 中开放关卡的源 JSON 哈希；请勿直接扩大白名单来绕过缺失的原生模块。此流程不导入 Aster 阶级系统；最终适配普通关、药水、迷雾、文艺大剧院、百步穿僵及 39 个原地图位置。原僵王关按用户要求改为包含 13 种植物、13 种普通僵尸的传送带。已开始的僵王原型仅保留在源码与审计目录，不接入构建。额外传入 `--cn-scaredy-apk <已审计官方中文版 4.2.8 APK>` 接入胆小菇。

新增植物的存档编号见 `src/dark/plant-ids.json`，由原生枚举构造器统一注册；不能使用 PlantTypes 资源对象的顺序充当解锁编号。原有 46 个编号保持不变。`scripts/check_iris_plant_ids.py <libPVZ2.so>` 执行原始构造器和正反查询，检查名称、成长形态、存档编号与原生字符串移动所有权。

## 单独编译恢复的原生代码

原生静态库可以独立构建。使用 CMake 3.16+ 和支持 C++17 的编译器。下面以 Android NDK ARMv7 构建为例，`ANDROID_NDK_HOME` 指向 NDK 目录。命令在 Iris 仓库根目录运行。

```powershell
cmake -S src/recovered/native -B work/native-recovered -G Ninja "-DCMAKE_TOOLCHAIN_FILE=$env:ANDROID_NDK_HOME/build/cmake/android.toolchain.cmake" -DANDROID_ABI=armeabi-v7a -DANDROID_PLATFORM=android-21 -DCMAKE_BUILD_TYPE=Release
cmake --build work/native-recovered
```

输出为 `libiris_native_recovered.a`。ARM 对照需要原始北美 APK，详见[验证命令](docs/source-recovery.md)。

发布 Iris 前，用 Aster 仓库的 `scripts/rename_unline_apk.py iris` 处理构建出的 APK，
将 Android 包名设为 `com.pvz2unline.iris`。命令和签名说明见 Aster 的 `BUILD.md`。
