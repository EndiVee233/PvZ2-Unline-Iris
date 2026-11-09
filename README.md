# PvZ2 Unline EN

`en` 是独立的北美版开发分支。基线是本目录提供的 `Plants+Vs+Zombies+2_1.6.257161na.apk`。原始 APK 放在项目根目录，解包资源和反汇编文件放在 `work/`。这些本地文件均由 Git 忽略。

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

需要 Python 3.11+、Java、Apktool 2.10.0 和 Android SDK Build Tools。当前机器可用以下命令。已把 CN 的 Apktool 复制到 `tools/apktool.jar`。在另一台机器上可以用 `--apktool` 指向现有副本。

```powershell
python scripts/prepare_baseline.py --build-tools Y:/Android/Sdk/build-tools/34.0.0
```

脚本核对原始 APK 的 SHA-256 和签名，导出 Manifest 与 Smali、内置 OBB、下载器数据库、RSB 资源组名以及文件哈希。默认输出 `work/baseline/`。重复运行时指定新的 `--output` 目录。

已用 Apktool 从解包结果重建未签名 APK。包名、版本、启动入口和 ABI 与样本一致。引擎及两个内置容器均逐字节核对一致。设备启动仍待验证。

## 启动路径与下一步

`PvZ2GameActivity.onCreate` 在检查扩展文件前调用 `SavesRestoring.DoSmth`，后者将内置 OBB 解包到应用的 `getObbDir()`。`FrameworkInfo_SysGetMainExpansionFilePath` 则从下载器数据库的主扩展条目定位文件。数据库记载 `217845760` 字节，随包 OBB 实际为 `170442752` 字节。现有 `expansionFileDelivered` 只检查路径和文件是否存在。尺寸差异是否影响后续加载，需要在设备上验证。

下一步是用独立包名建立测试版，验证首次离线解包、进入教程和冷启动存档，再逐项移植桌面输入等功能。若要支持 Android 14，样本的 `targetSdk 18` 低于系统的安装门槛，需要单独处理并测试存储权限。 [Android 14 安装限制](https://developer.android.com/about/versions/14/behavior-changes-all#minimum-target-api-level)
