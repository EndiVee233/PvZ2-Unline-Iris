# Unline 系列
[PvZ2-Unline:Aster](https://github.com/EndiVee233/PvZ2-Unline-Aster)

PvZ2-Unline:Iris


# PvZ2-Unline:Iris

Iris 基于《植物大战僵尸 2》北美版 1.6.257161，面向 Windows Subsystem for Android 和支持 ARM32 的 Android 环境。项目提供离线构建脚本和逐步恢复的 Java、C++ 源码。

[下载 APK](https://github.com/EndiVee233/PvZ2-Unline-Iris/releases) · [构建说明](BUILD.md) · [恢复进度](RECOVERY_STATUS.md) · [来源与权利声明](NOTICE.md) · 


## 特性

- 内置扩展包首次启动后解压到应用私有目录，存档也写入应用私有目录。
- 游戏启动和本地流程绕过 Google Play 登录、云存档、旧扩展下载器及在线支付。
- 语言可从设置中切换，支持英语、德语、西班牙语、法语、意大利语、巴西葡萄牙语和简体中文。
- Iris 桌面输入支持卡槽快捷键、鼠标悬停与种植十字提示、右键取消、中键能量豆、加速和收集。[键位与实现](docs/source-recovery.md#桌面键鼠)
- 未来世界沿用 Iris 原地图与关卡，补齐 Aster 的战场、机甲巨人表现、香橼音效和音乐。
- 黑暗时代接入 Aster 原地图的 39 个关卡位置、植物、僵尸、药水、迷雾、文艺大剧院和百步穿僵，不导入阶级系统。原僵王关改为全阵容传送带。[范围及验证状态](docs/dark-ages-level-status.md)
- Releases 使用独立包名 `com.pvz2unline.iris`；中间构建仍使用北美包名，发布前须按构建说明转换。升级安装需与已安装 APK 使用同一签名。

黑暗时代仍有动画、音效、布局与玩法细节待完善，尚未逐关完整验收。后续版本会按实测反馈继续微调；本次发布不代表所有细节已经与 Aster 一致。失去焦点后冻结、点击图鉴后可能闪退的问题仍列为待办。

## 从源码构建

按[构建说明](BUILD.md)准备本地北美基线 APK、Aster 素材和工具链。生成的 APK、反编译目录、原始游戏资源和密钥存放在 Git 忽略的本地目录。

截至第三轮，Iris 构建中有 28 个 DEX 类从恢复的 Java 源码编译。C++ 静态库可以独立编译，游戏 APK 仍使用 ARM32 原生引擎 `libPVZ2.so`。各轮证据和验证范围见[恢复记录](docs/source-recovery.md)。
