# 国际版黑暗时代核对与当前移植范围

2026-11-12 从 [PvZ2 Android 归档](https://archive.org/details/pv-z-2-android) 下载国际 ROW 2.5.1 APK 和 main.32 OBB，包含黑暗时代上下篇。归档 ZIP SHA-1 为 `c35128162d2a6e8f384079a2ec9233e2d2eab9e6`，与归档元数据一致；仅离线解包，未安装国际版或替换 Iris 引擎。采用早期完整黑暗时代版本，避免把后期阶级系统作为移植依赖。

角色名单以安装包内 ZombieTypes/PropertySheets 和 DARK 关卡引用为依据，不以网页百科或名字相似作为实装证据。下载来源、APK/OBB 的 SHA-256 及机器可读范围见 `src/dark/international-policy.json`。

当前范围已按用户后续决定扩展：接入盗贼、大法师、迷雾、中文版植物和真正的剧院/百步穿僵；僵尸博士取消移植，保留原型，原第30夜改为全阵容传送带。`international-policy.json` 保留最初国际版范围快照，构建使用 `port-policy.json`；实现与验收边界见 [逐关清单](dark-ages-level-status.md)。

## 僵尸

| 数据名 | 国际版存在 | 当前 Iris 原生类 | 本轮策略 |
|---|---|---|---|
| `zombossmech_dark` | 是 | 不接入安装包 | 用户取消移植；保留已做原型，原关替换为传送带 |
| `dark` | 是 | `ZombieBasic`（基线已有，现已适配） | 从 Aster 接素材和兼容属性，不带阶级 |
| `dark_armor1` | 是 | `ZombieBasic`（基线已有，现已适配） | 从 Aster 接素材和兼容属性，不带阶级 |
| `dark_armor2` | 是 | `ZombieBasic`（基线已有，现已适配） | 从 Aster 接素材和兼容属性，不带阶级 |
| `dark_flag` | 是 | `ZombieBasic`（基线已有，现已适配） | 从 Aster 接素材和兼容属性，不带阶级 |
| `dark_armor3` | 是 | `ZombieBasic`（基线已有，现已适配） | 从 Aster 接素材和兼容属性，不带阶级 |
| `dark_imp` | 是 | `ZombieImp`（基线已有，现已适配） | 从 Aster 接素材和兼容属性，不带阶级 |
| `dark_imp_dragon` | 是 | `ZombieFutureImp`（基线已有，现已适配） | 从 Aster 接素材和兼容属性，不带阶级 |
| `dark_gargantuar` | 是 | `ZombieGargantuar`（基线已有，现已适配） | 从 Aster 接素材和兼容属性，不带阶级 |
| `dark_wizard` | 是 | `ZombieDarkWizard`（基线已有，现已适配） | 从 Aster 接素材和兼容属性，不带阶级 |
| `dark_juggler` | 是 | `ZombieDarkJuggler`（基线缺少，现以独立类适配） | 从 Aster 接素材和兼容属性，不带阶级 |
| `dark_king` | 是 | `ZombieDarkKing`（基线缺少，现以独立类适配） | 从 Aster 接素材和兼容属性，不带阶级 |
| `dark_archmage` | 无同名定义 | 独立睡眠施法适配 | 用户后续明确移植，不再替换 |
| `dark_cavalry` | 无同名定义 | 不导入 | 出怪引用替换为 `dark_armor3` |
| `dark_cavalry_rider` | 无同名定义 | 不导入 | 出怪引用替换为 `dark_armor3` |
| `dark_rogue` | 无同名定义 | 独立隐身与路灯显隐适配 | 用户后续明确移植，不再替换 |
| `kongfu_basic` | 无同名定义 | 不导入 | 出怪引用替换为 `dark` |
| `dark_basic` | 无同名定义 | 不导入 | 出怪引用替换为 `dark` |

国际版的 `dark_armor3` 是重甲骑士；Aster `dark_cavalry` 是骑马僵尸，二者不能因中文名称相近混为一谈。变羊巫师 `dark_wizard` 在国际版存在，催眠法师 `dark_archmage` 不在上述国际版定义中。

## 机制与植物

- 国际版有速度药水 `zombiepotion_speed`、韧性药水 `zombiepotion_toughness`，对应 `GridItemZombiePotion` 与 `ZombiePotionModuleProperties`。Aster 药水属性的资源名、三层效果和音效字段与国际版一致；Iris 缺这两个原生类，需要真正补行为，不能只加入贴图声称已完成。
- 国际版普通黑暗时代有阳光菇、小喷菇、大喷菇、阳光豆、磁力菇；催眠菇、花生也有原生定义。不能把这些尚未移植的植物当成中国版独占而删除。
- 迷雾不属于本页最初国际版范围；用户后续明确要求移植，现接入独立模块、迷雾绘制和路灯照明/大招。
- 剧院/百步穿僵曾在 r34 使用空关占位。用户后续确认移植，现接入实际模块、角色、道路/升级、箭种/计分和结算，不再以空关发布。

## r33 反馈与纠正

- 用户实际完成第 1 夜，但无法找到第 3 夜。只读存档核对：第 1 夜通关已记录于世界 7，导入地图却使用世界 5，奖励/第 3 夜记录因此写入错误世界；地图应统一为 7，不应删存档或要求用户重玩来掩盖问题。
- Aster 第 2 夜有 ZombiePotions 对象，但 LevelDefinition.Modules 并未引用它；第 23、27 夜也有未引用药水配置。r33 扫描所有对象而未区分引用闭包过度判定了这些关卡。后续转换先剪除未引用对象，再判断依赖；仍需剔除未引用的未知类，因为 Iris 在读取对象时就会创建实例。
- 本页是核对与实施依据，不代表列出的所有内容已经移植或验收。

## 原生接口核对与后续接入点

下列地址是 ELF 相对地址；Ghidra 工程显示地址另加 `0x10000`。下表记录基线引擎差异与逆向接入点，不能当作当前版本的待实现清单，也不能直接跨版本搬运机器码。

| 机制 | 国际 ROW 2.5.1 | Iris 对应情况 |
|---|---|---|
| 小丑接球/反射 | `0x703628` 判断可接投射物，`0x7037ac` 隐藏并入队，`0x702eac` 延迟发射，`0x703088` 重设速度、攻击阵营及来源 | `ZombieDarkKnight` 的 `0x63022c` 仅是旧式偏转；没有接球队列、spin 状态，不能改个类名冒充小丑 |
| 药水被吃/踩碎 | `GridItemZombiePotion` 的 `0x2ae890` 根据伤害来源处理；普通僵尸消耗后逐级替换药水状态，最多三层，踩碎与被吃分别播放效果 | 缺 `GridItemZombiePotion` 和 `ZombiePotionModuleProperties`；须补生成、碰撞、增益/叠层、摧毁及存档行为 |
| 药水生成 | `0x733210` 选空位，避开植物/药水，按已有药水数量降低某行权重；模块保存 `m_nextPotionSpawnTime` | 不能用随机墓碑代替药水生成 |
| 变羊巫师 | Aster PAM 的 `sheep` 段包括 `Casting_Start`、`Casting_Fire`、`use_action` 命令 | Iris `0x6336f8` 已有施法状态，但 rig 请求 `casting_start/fire/loop`，时间属性是标量；须翻译动画段和时间范围、接上羊与命中特效 |
| 国王 | 国际版使用 `ZombieDarkKing`，有专属动画与加冕逻辑 | Iris `ZombieDarkBlacksmith`（`0x62dab0`、`0x62dd1c`）会制造/抛头盔，但动画要求 `makehelm/throwhelm`；不是正式国王的等价实现 |
| 巨人与小鬼 | Iris 已有 `ZombieGargantuar`、`ZombieImp` | 需导入 Aster 正式 Dark 根组、转单次抛小鬼阈值和动画层；不得影响已验收的未来机甲巨人补丁 |
| 专属音频 | ROW 2.5.1 bank 版本 88；Aster bank 版本 112 | Iris 使用 88。沿用未来世界已验证的方法：兼容事件树加 Aster WEM，不能直接把 112 bank 原样覆盖 |

国际版及 Iris 的反编译输出保存在忽略目录 `work/dark-audit/row-*-decomp/`、`actors-decomp/`、`grid-decomp/`。国际版 Ghidra 导入时分析达 300 秒上限，按需反编译已经生成，不应称为全库完成反编译。

全量关卡引用检查另发现 Aster `dark16` 的 `SunHoldout`、`dark19` 的 `ChallengeModule` 各有重名对象。已在 canonical_level 中按核对后的后定义消歧，并对原配置和源文件哈希做断言；来源发生变化时拒绝构建。
