# BlockOffensive 1.20.1/Forge → 1.21.1/NeoForge 移植说明（PORT-NOTES）

- **上游**：`/home/lee/.local/share/PrismLauncher/instances/hhs枪战/.fpsmatch/BlockOffensive-master/`（GPL-3.0-only，作者 SSOrangeCATY）
- **目标栈**：Minecraft 1.21.1 / NeoForge 21.1.253 / Java 21 / ModDevGradle `net.neoforged.moddev` 2.0.148
- **移植副本**：`blockoffensive-port/`（本次工作**只写这里**；未触碰 `fpsmatch-port/`、`codpattern-port/`、`server/`、`minecraft/`）
- **模板**：兄弟移植 `../fpsmatch-port/`（同作者的 FPSMatch 移植版，网络/事件/GUI 层的适配范式照抄它）
- **产物**：`build/libs/blockoffensive-1.1-1.21.1-port.jar` — 3,377,574 B，sha256 `6a89cb708916021bd3c6ba56106380c75923f7903168b0b0866fad32490ba268`（535 条目 / 295 class，内嵌 4 个 soundlibs jarJar）
- 另有 `build/libs/blockoffensive-1.1-1.21.1-port-sources.jar`（2,573,635 B）
- **可复现构建**：已对全部归档任务设 `preserveFileTimestamps = false` + `reproducibleFileOrder = true`（`tools/fix_l.py`）。实测连续 3 次 `rm -f build/libs/*.jar && ./gradlew build --offline` 得到同一 sha256。**此前没有该配置、同源码两次构建哈希不同**（实测 `c34a1471…` vs `0c9a2737…`），所以本文件早期写的哈希只是「当时那一次快照」，不能当身份标识——现已修正为可复现哈希。

## 结果

| 指标 | 值 |
|---|---|
| `./gradlew compileJava --offline` | **exit=0，0 错误**（`compile-final.log`） |
| `./gradlew build --offline` | **exit=0**，`:test` 执行 **2 个 JUnit 5 单测全过**（`build-final.log`、`build/reports/tests/test/index.html`） |
| 编译错误轨迹 | **742 → 445 → 338 → 294 → 173 → 159 → 110 → 63 → 2 → 0** |

关于 `compileTestJava`：随包的 `src/test/java/.../CSEconomyRulesTest.java`（上游的经济规则单测）需要 JUnit 5，
而本机 Gradle 缓存里只有 `junit-bom` 的 pom、**没有 junit jar**，`--offline` 无法下载 ⇒ 最初 `build` 止步于
`:compileTestJava`（主 jar 其实已经产出）。处置见 `tools/fix_k.py`：把 JUnit 5.10.2 的 7 个 jar 预先放进
`libs/test/`，用 `testImplementation fileTree('libs/test')` 离线引用（**不进主 jar、不改变运行时行为**），
并显式 `useJUnitPlatform()`——否则 Gradle 默认走 JUnit 4 引擎，会把 JUnit 5 测试**静默跳过**（实测改动前报 `0 个测试`，
改动后 `2 个测试`）。现在整条 `build` 全绿，不再需要 `-x compileTestJava`。

本模组的 gametest 全部放在 `src/main/java/.../gametest/`，因此 `compileJava` 已经把
`DeathmatchLifecycleGameTests` / `ShopDropGameTests` / `ShopRefundGameTests` / `ListenerModuleEditorGameTests` /
`ShopEditorGameTests` / `ScoreboardStatsGameTests` 全部编译通过（它们要在游戏内运行，不随 `build` 执行）。

## 复现

```bash
cd blockoffensive-port
python3 tools/fix_a.py && python3 tools/fix_b.py && python3 tools/fix_c.py \
  && python3 tools/fix_d.py && python3 tools/fix_e.py && python3 tools/fix_f.py \
  && python3 tools/fix_g.py && python3 tools/fix_h.py && python3 tools/fix_i.py \
  && python3 tools/fix_j.py && python3 tools/fix_k.py && python3 tools/fix_l.py
GRADLE_USER_HOME=$PWD/.gradle-home ./gradlew compileJava --offline --console=plain
GRADLE_USER_HOME=$PWD/.gradle-home ./gradlew build --offline
```

所有脚本**幂等**且带命中数断言（重复运行不会静默改坏；多数脚本支持 `--dry`）。
**幂等性实测**（把 12 个 `fix_*.py` 按顺序再跑一遍，然后对 `src/` + `build.gradle` + `libs/` 共 349 个文件做 md5 比对）：
全部 exit=0，且**全树逐字节未被改动**。`fix_g` / `fix_h` / `fix_d` / `fix_e` 用「幂等门禁」（先检查关键标记是否已全部落地，
全中则整体跳过）；`fix_f` / `fix_j` 用「先追加后归一」的自幂等写法。

**一处我造成并已修复的真实缺陷（如实记录）**：`fix_f.py` 最早的 parseColor 规则写成「在调用后追加
`.result().orElseThrow()`」，**重跑会在已改好的代码上再追加一次**，产出
`TextColor.parseColor(...).result().orElseThrow().result().orElseThrow()`（不能编译），波及
`util/ThrowableType.java`（5 处）、`util/BOUtil.java`、`entity/CompositionC4Entity.java`、`item/CompositionC4.java`。
后果是「当时那句 exit=0 / 那个 sha256」属于**被改坏之前的树**，不能作为交付证据。
现已：① `tools/fix_j.py` 做双写归一（实测折叠 8 处，跑完自检无残留）；② `tools/fix_f.py` 改成「规则跑完后再归一」，
既幂等又能自修复历史双写；③ 在**修好的树**上重新 `compileJava`（`compile-final.log` exit=0）与 `build`（`build-final.log` exit=0），
本文件的哈希/字节数均已按重建结果更新。

**不要跑 `./gradlew clean`**：`build/moddev/artifacts/neoforge-21.1.253-merged.jar` 是离线编译的前提，
NeoForge 工件不在 `.gradle-home` 里，clean 掉就再也解析不出来。要强制全量重编请用
`find src/main/java -name '*.java' -exec touch {} +`。

## tools/ 脚本

| 脚本 | 职责 | 错误数变化 |
|---|---|---|
| `fix_a.py` | 包/类重命名表：`net.minecraftforge.registries.{DeferredRegister,RegistryObject,ForgeRegistries}` 特判 → `net.neoforged.neoforge.registries.*`；`common.ForgeConfigSpec`→`ModConfigSpec`、`common.MinecraftForge`→`NeoForge`、`api.distmarker`、`eventbus.api`、`fml.common.Mod.EventBusSubscriber`→`net.neoforged.fml.common.EventBusSubscriber`；`RegistryObject<T>`→`DeferredHolder<T,T>`；`EventBusSubscriber.Bus.FORGE`→`.GAME` | 742→445 |
| `fix_b.py` | 网络垫片：`NetworkEvent.Context`→`PayloadContext`(×49)、import 换(×33)、补 `NetworkPacketRegister` import(×16)、`send(PLAYER.with)`→`sendToPlayer`(×13)、`sendToServer`→`NPR.sendToServer`(×12)、`NetworkDirection`→`PayloadDirection`(×2)、主类构造器换 2 参、`onRegisterPackets` | 445→338 |
| `fix_c.py` | TickEvent 拆类：`ClientTickEvent`→`.Post`(×8)、`ServerTickEvent`→`.Post`(×3)、`PlayerTickEvent`→`.Post`(×2) + 12 处 phase 守卫删除；`LivingHurt/AttackEvent`→`LivingIncomingDamageEvent`(×10)；`BuiltInRegistries.*.getValue(`→`.get(`(×3) | 338→294 |
| `fix_d.py` | 裁剪三个兼容层及其调用点（详见下节） | 294→173 |
| `fix_e.py` | `DistExecutor` 不存在 → `ClientPacketExecutor`（6 个 S2C 包）+ `CSScoreboardSync.apply` 私有转公开 + `TestItem`/`BlockOffensive` 调用点 | 173→159 |
| `fix_f.py` | 序列化层：`writeComponent/readComponent`→`ComponentSerialization.TRUSTED_CONTEXT_FREE_STREAM_CODEC`；`writeItem/readItem`→`writeJsonWithCodec/readJsonWithCodec(ItemStack.CODEC)`；`FriendlyByteBuf::writeUUID` 等方法引用→显式类型 lambda；`TextColor.parseColor`→`.result().orElseThrow()`；gametest 的 NBT→DataComponents | 159→110 |
| `fix_g.py` | GUI/HUD 层：`ForgeGui`/`VanillaGuiOverlay`/`RenderGuiOverlayEvent`→`VanillaGuiLayers`/`RenderGuiLayerEvent`；`IHudRenderer` 1.21.1 三方法签名；`Tesselator.getBuilder()`→`Tesselator.begin(...)`+`BufferUploader` | 110→63 |
| `fix_h.py` | 大长尾 29 文件（皮肤/事件/注册泛型/ArmPose/音频/网络垫片/gametest 等，详见下节） | 63→2 |
| `fix_i.py` | `ShopDropGameTests` 反射断言补 `NoSuchMethodException` catch | 2→0 |
| `fix_j.py` | 幂等归一：把被叠加多次的 `.result().orElseThrow()` 折叠回一个（修复 `fix_f` 早期版本的双写产物），跑完自检全树无残留 | 0（修复性） |
| `fix_k.py` | 离线 JUnit 5：下载 7 个 junit jar 进 `libs/test/`，build.gradle 加 `testImplementation fileTree('libs/test')` + `useJUnitPlatform()`，让 `compileTestJava`/`test` 离线可跑 | 0（构建完整性） |
| `fix_l.py` | 可复现构建：所有归档任务 `preserveFileTimestamps=false` + `reproducibleFileOrder=true` | 0（可复现性） |
| `errs.py` | 工具：`python3 tools/errs.py compile-N.log [正则]` → 按文件汇总，或列匹配站点的 `符号:`/`位置:`/`需要:`/`找到:` 细节 | — |
| `scan_bus.py` | 工具：扫描 `@SubscribeEvent` 参数类型属于 game 还是 mod 总线，比对类级 `@EventBusSubscriber` 声明。NeoForge 1.21.1 的 `IEventBus.register(Object)` 会强校验，挂错总线直接 `Failed to start` | — |

## 裁剪清单（每个都记录：删了什么、为什么、上游在哪）

裁剪判据**不是**「编译不过就删」，而是：这些兼容层的上游调用点**全部**裹在
`BOImpl.isXxxLoaded()` / `FPSMImpl.findXxxMod()` 守卫里，而被探测的三个模组**不在本整合包内**
（已核对 `server/mods/` 与 `minecraft/mods/` 共 132 个 jar，无 hit-indication / counterstrikegrenade /
PhysicsMod / gd656killicon）。因此运行时这些分支判定恒为假——
「删掉兼容类 + 把守卫分支变成空」**精确等价于「模组未安装」**，而不是删功能。

| 删除/置空 | 为什么 | 上游路径 |
|---|---|---|
| `compat/PhysicsModCompat.java` | 依赖 `net.diebuddies.*`/`physx.*`，包内无 PhysicsMod | `src/main/java/net/ptcrys/blockoffensive/compat/PhysicsModCompat.java` |
| `compat/HitIndicationCompat.java` | 依赖 `com.rosymaple.hitindication.*`，包内无 hit-indication | 同上目录 |
| `compat/CSGrenadeCompat.java` | 依赖 `club.pisquad.minecraft.csgrenades.*`，包内无 counterstrikegrenade | 同上目录 |
| `net/PxDeathCompatS2CPacket.java` | 只在 PhysicsMod 兼容路径上发送 | `src/main/java/net/ptcrys/blockoffensive/net/` |
| `net/PxRagdollRemovalCompatS2CPacket.java` | 同上 | 同上 |
| `command/BOPhysicsRagdollDebugCommand.java` | 只用于调试 PhysicsMod 布娃娃，无 PhysicsMod 即无对象可调 | `src/main/java/net/ptcrys/blockoffensive/command/` |
| `BlockOffensive.registerCompat()` 清空 | 上述兼容层的注册入口 | `BlockOffensive.java` |
| `CSDeathMessageHud` / `CSGameHud` 中的守卫块删除 | `BOImpl.isHitIndicationLoaded()` 恒 false | `client/screen/hud/` |
| `map/CSMap.java` 去掉 `\|\| (FPSMImpl.findCounterStrikeGrenadesMod() && CSGrenadeCompat.is(entity))`；`sendPhysicsRagdollRemovalPacket(UUID)` / `sendPhysicsDeathPacket(ServerPlayer)` 置空 | 同上 | `map/CSMap.java` |
| `map/CSGameMap.java` 去掉 `sendPhysicsRagdollRemovalPacket(PxRagdollRemovalCompatS2CPacket.ALL)` | 同上 | `map/CSGameMap.java` |
| `net/BOPacketRegistration.java` 去掉两个 `Px*CompatS2CPacket.class,` 条目（索引 10/11） | 类已删。**注意：旧版按数组下标硬编码方向表，索引 `2 \|\| 6 \|\| 9` 是 C2S，绝不能在索引 ≤ 9 处增删条目** | `net/BOPacketRegistration.java` |
| `command/BOCommandRegister.java` 去掉 2 处 `BOPhysicsRagdollDebugCommand.fpsmCommand()` | 同上 | `command/BOCommandRegister.java` |
| `compat/BOMenuIntegration.registerModsPage()` 重写为 `container.registerExtensionPoint(IConfigScreenFactory.class, factory)` | 1.21.1 没有 Forge 的 `ConfigScreenHandler`/菜单页扩展点 | `compat/BOMenuIntegration.java` |

**没有删的**：`compat/BOImpl.java`（探测函数全部保留、返回 false）、`compat/PhysicsDeathProxyGuard.java`、
`compat/ProxiedRagdollRegistry.java`（自包含，不依赖外部模组类）。

### 恢复的依赖（不是裁剪）

上游 `dependencies.gradle` 用 `jarJar` 内嵌四个纯 Java 声音库（jlayer/jorbis/vorbisspi/tritonus-share）。
1.21.1 的 ModDevGradle 提供真实的 `jarJar` configuration + task，因此**原样恢复**：
`build.gradle` 里同时声明 `jarJar` 与 `compileOnly`（MDG 的 `jarJar` 会进编译类路径——这一点已实证：
补上之后 `javazoom.jl.decoder` 的 14 个「找不到符号」清零）。
产物内可见 `META-INF/jarjar/{jlayer,jorbis,vorbisspi,tritonus-share}*.jar`。

## 新增文件（1.21.1 上必须自造的小件）

| 文件 | 作用 |
|---|---|
| `net/ClientPacketRegistry.java` | `ConcurrentHashMap<Class<?>, Consumer<Object>>` + `register`/`handle` |
| `net/ClientPacketExecutor.java` | 取代被删的 `DistExecutor`：`enqueueWork(() -> { if (FMLEnvironment.dist == Dist.CLIENT) ClientPacketRegistry.handle(packet); }); setPacketHandled(true)` |
| `client/net/BOClientPacketRegistrar.java` | 6 个 S2C 包的客户端 handler 注册，由 `BOClientBootstrap.onClientSetup` 调用（**纯客户端**，只在 `Dist.CLIENT` 的 MOD 总线上初始化） |

## 行为/保真度差异（有意的取舍，逐条列出）

1. **`ItemStack` 过网走 JSON codec**：`buf.writeItem(x)` → `buf.writeJsonWithCodec(ItemStack.CODEC, x)`。
   原因：fpsmatch 的网络垫片把包体签名钉死在纯 `FriendlyByteBuf`，而 1.21.1 的 `ItemStack.STREAM_CODEC`
   要求 `RegistryFriendlyByteBuf`。**风险**：比流编解码更慢、NBT 走 JSON 数值表示（大 NBT 可能失真/体积膨胀）。
   涉及 `DeathMessageS2CPacket` / `ShopNearbyDropsS2CPacket` / `ShopDropPickupResultS2CPacket` /
   `IntroSequenceS2CPacket` / `KillCamS2CPacket`。
   Component 侧没有这个问题（`ComponentSerialization.TRUSTED_CONTEXT_FREE_STREAM_CODEC` 吃纯 `ByteBuf`）。
2. **自定义手臂姿势退化**：`HumanoidModel.ArmPose.create("ITEM_C4", true, …)` 在 1.21.1 不存在
   （`ArmPose` 是 final enum + `IExtensibleEnum`，自定义项要走 NeoForge 枚举扩展
   `enumextensions.json` + `EnumProxy`）。本次退化为 `ArmPose.BLOCK`，
   **丢失 C4 持握时双臂内旋 30° 的视觉**（纯客户端视觉，不影响玩法）。
   位置：`item/CompositionC4.java`。
3. **`renderEntityInInventoryFollowsAngle` 换了签名并新增裁剪框**：1.21.1 是
   `(GuiGraphics, int x0, int y0, int x1, int y1, int scale, float yOffset, float angX, float angY, LivingEntity)`，
   内部 `enableScissor(x0,y0,x1,y1)`。旧调用 `(graphics, x, y, scale, 0.9f, 0, this)` 改为
   `(graphics, x - scale, y - scale, x + scale, y + scale, scale, 0.9f, 0f, 0f, this)`
   （中心不变）。**风险**：新裁剪框是 ±scale 的方框，对特别高的姿势可能比旧版多裁一点。
   位置：`client/shop/ShopPlayerPreview.java`。
4. **`FPSMGunReloadEvent` 的取消守卫被删**：移植版 fpsmatch 的这个事件 `extends Event` 且**没有**
   实现 `ICancellableEvent`，`event.isCanceled()` 不存在。`map/CSGameEvents.onGunReload` 里
   `if (event.isCanceled()) return;` 已删。**语义变化**：那个事件本来就没人取消，删除等价。
5. **`ClientLevel.addPlayer(int, AbstractClientPlayer)` 不存在** → `ClientLevel.addEntity(Entity)`，
   实体 id 由 `ClientLevel` 自行分配。`IntroClientController.PREVIEW_ENTITY_ID_BASE` 因此**变成未使用常量**
   （旧版靠它给预览演员占一组固定 id）。清理时用的是 `player.getId()`，仍有效。
6. **`getChannelFromCache(X.class).sendToServer(payload)` → `NetworkPacketRegister.sendToServer(payload)`**：
   移植版垫片没有 channel 对象，只有静态发送方法；内部 `TYPES` 是 **static** Map，所以 BO 自己注册的包
   也能被找到。影响 4 处（`ShopDropClientState`×2、`CSGameShopScreen`×1、`ShopDropGameTests`×1）。
7. **`PlayerInteractEvent` 在 1.21.1 基类不可取消**：只有 `RightClickBlock`/`LeftClickBlock`
   （`setUseBlock/setUseItem(TriState)`）与 `RightClickItem`（`setCanceled`）有拦截手段。
   - `item/CompositionC4.onRightClickBlock`：`Event.Result.ALLOW/DENY` → `TriState.TRUE/FALSE`（等价）。
   - `intro/IntroRuntimeController.onInteract`：改成 `instanceof` 分派到三个子类。
     **覆盖面差异**：旧版一网打尽所有 `PlayerInteractEvent` 子类（含 `EntityInteract*`），
     新版只覆盖左右键方块与右键物品。开场锁定期内的实体交互不再被拦。
8. **`ShopDropGameTests.shopResultChannelIsRegistered` 的断言换了判据**：1.21.1 没有
   「通道 + varint 鉴别码」，每个包是独立的 `CustomPacketPayload`，垫片的 `TYPES` 是私有的。
   断言改为「反射 payload 契约」（静态 `encode(T, FriendlyByteBuf)` + 静态 `decode(FriendlyByteBuf)`），
   违约时垫片注册会在运行时直接抛异常，所以这个断言仍然是有效的（只是不再直接读注册表）。
9. **`DeathmatchLifecycleGameTests` 的登录链判据换了判据**：旧版读 `ClientboundCustomPayloadPacket` 的
   `getIdentifier()=="fpsmatch:main"` 再 `readVarInt()` 取鉴别码；1.21.1 没有这种封装，
   改为直接比对载荷里的上游包类（`ReflectivePayload.body().getClass()`）。
   **测试强度实际更强**（验的是包类本身，不再是鉴别码），但不再覆盖「编解码字节流」这一层。
10. **`ShopDropGameTests` 里 `vanilla.setThrower(UUID.randomUUID())` 已删**：
    1.21.1 `ItemEntity.setThrower` 收 `Entity`（不再收 UUID），而本模组的拾取判定
    （`ShopDropPickupService.ownerUuid`）只读 **target UUID**，不看 thrower。所以该行对被测行为无影响，
    删掉并把注释改为说明「不设 target 即公开掉落」。
11. **`CompositionC4.getUseDuration(ItemStack)` → `(ItemStack, LivingEntity)`**：1.21.1 给该方法加了
    `LivingEntity` 参数。返回值 80 tick 不变。
12. **`throwable/kinetic` 音频解码器换了类**：`com.mojang.blaze3d.audio.OggAudioStream` →
    `net.minecraft.client.sounds.JOrbisAudioStream`。`readAll()`/`getFormat()` 是
    `FloatSampleSource`/`FiniteAudioStream` 的 default 方法，调用点未改。
13. **`TextColor.parseColor` 现在返回 `DataResult<TextColor>`**：补 `.result().orElseThrow()`（8 处）。
    原生色值都是常量字面量，永不失败。

## 尚未验证 / 剩余风险（如实声明）

**本次工作只验证到「编译 0 错误 + 产出 jar」。jar 从未在游戏里加载过**，以下都**未实测**：

1. **运行时 mixin 注入**：`blockoffensive.mixins.json` 里 `plugin: BlockOffensiveMixinPlugin`、
   `client.PlayerInfoInvoker`、`client.ClientPacketListenerAccessor`、`client.ShopPreviewPoseMixin`、
   `tacz.IntroTaczAnimationManagerMixin` 等 15 个 mixin 只过了编译，没过 Mixin 的注入校验。
   注意 `compatibilityLevel` 仍是上游的 `JAVA_8`（对 Java 21 目标通常无碍，但未实测）。
2. **网络往返**：包体 `encode`/`decode` 在 1.21.1 上**原本就能编译通过**（逐字节转发），
   但 `ItemStack` 走 JSON codec 这一条（差异 1）只在编译层验证过，没有实机收发。
3. **`Registries`/`DeferredRegister` 的注册顺序**与 `RegisterPayloadHandlersEvent` 的绑定时机。
4. **GUI 分层**：`CSGameHud` 现在实现的是 fpsmatch 的 `IHudRenderer`（1.21.1 形状），
   由 `FPSMGameHudManager.INSTANCE.registerHud("cs"/"csdm", …)` 挂进 fpsmatch 自己的
   `RegisterGuiLayersEvent`。BO **不需要**再注册自己的 GUI layer（这点已确认代码路径），但效果未实测。
5. **`VanillaGuiLayers` 名对照**：`MOUNT_HEALTH` → `VEHICLE_HEALTH` 是按 NeoForge 常量表改的，
   血量/护甲/食物/热键栏/经验条/载具血量的隐藏行为需要实机看一眼。
6. **裁剪的正确性**依赖「包内确实没有那三个模组」这一前提（已核对 132 个 jar）。
   若后续往整合包里加回 hit-indication / counterstrikegrenade / PhysicsMod，
   这些兼容层需要从上游恢复并重新移植。
7. **`IntroClientController` 预览演员的实体 id**：旧版用固定 id 段 `-2100500000 - i`，
   新版交给 `ClientLevel` 分配（差异 5）。若下游有代码依赖那组 id，会失效（已核对 `removeEntity` 用的是
   `player.getId()`，但未穷尽检查）。
