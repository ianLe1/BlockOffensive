# NeoForge 1.21.1 运行期严格性清单（编译期查不出来，只在实机启动时炸）

> 来源：FPSMatch 1.20.1/Forge → 1.21.1/NeoForge 移植的实机启动调试（2026-10-04）。
> 这些规则 1.20.1 Forge **不校验**，所以上游代码全都带着这些「违规写法」，移植时必须主动清掉。
> 判定工具：`tools/scan_bus.py`（规则 1）、`tools/scan_supertypes.py`（规则 2 + 3）。

---

## 规则 1：`IEventBus#register(Object)` 校验 `@SubscribeEvent` 参数的事件总线归属

**现象**（致命，服务端 `Failed to start the minecraft server`）：

```
java.lang.IllegalArgumentException: Method public void net.ptcrys.fpsmatch.FPSMatch.onEnqueue(
    net.neoforged.fml.event.lifecycle.InterModEnqueueEvent) has @SubscribeEvent annotation,
    but takes an argument that is not valid for this bus
```

**触发模式**：类里既有 `NeoForge.EVENT_BUS.register(this)`（game 总线），又有一个 `@SubscribeEvent`
方法，其参数是 **mod 总线事件**（`net.neoforged.fml.event.IModBusEvent` 的子类型）。

**已知的 mod 总线事件**（必须用 javap **递归**查父类/接口才能判定——`javap` 只列直接父类与直接接口，
`InterModEnqueueEvent` 的类声明里根本没有 `IModBusEvent` 字样，是它的父类 `ParallelDispatchEvent`
才 implements）：

| mod 总线事件 |
| --- |
| `net.neoforged.fml.event.lifecycle.FMLCommonSetupEvent` |
| `net.neoforged.fml.event.lifecycle.FMLClientSetupEvent` |
| `net.neoforged.fml.event.lifecycle.InterModEnqueueEvent` |
| `net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent` |
| `net.neoforged.neoforge.client.event.RegisterKeyMappingsEvent` |
| `net.neoforged.neoforge.client.event.RegisterGuiLayersEvent` |
| `net.neoforged.neoforge.client.event.EntityRenderersEvent$RegisterRenderers` |
| `net.neoforged.neoforge.client.event.RegisterColorHandlersEvent` |

**修法**（二选一）：
1. 若该方法已经由 `modEventBus.addListener(this::xxx)` 登记 → 直接**删掉 `@SubscribeEvent` 注解**，行为完全等价。
2. 否则把该方法挪进一个只在 mod 总线注册的类（`@EventBusSubscriber(bus = Bus.MOD)` 或 `modEventBus.register(...)`）。

---

## 规则 2：`@EventBusSubscriber` 的类自身必须至少有一个 `@SubscribeEvent` 方法

**现象**（致命，mod 加载失败）：

```
[ne.ne.fm.ja.AutomaticEventSubscriber/LOADING]: Failed to register class Lnet/ptcrys/fpsmatch/core/map/BaseMap; with @EventBusSubscriber annotation
java.lang.IllegalArgumentException: class net.ptcrys.fpsmatch.core.map.BaseMap has no @SubscribeEvent methods, but register was called anyway
  → [ne.ne.fm.ja.FMLModContainer/LOADING]: Failed to register automatic subscribers. ModID: fpsmatch
  → FPSMatch (fpsmatch) has failed to load correctly
```

**修法**：删掉那个历史残留的 `@EventBusSubscriber` 注解。

**判定要点**：删之前要确认「该方法/父类确实没有任何事件订阅」。若**父类**带订阅而子类不带注解，
那注解是必需的、不能删——但这时往往撞上规则 3。

---

## 规则 3：被注册为监听器的类，其**父类**不允许带 `@SubscribeEvent` 方法

**现象**（致命，mod 加载失败）：

```
java.lang.IllegalArgumentException: Attempting to register a listener object of type class ...EditToolItem,
however its supertype class ...FPSMToolItem has a @SubscribeEvent method:
    public static void ...FPSMToolItem.onLeftClickEmpty(net.neoforged.neoforge.event.entity.player.PlayerInteractEvent$LeftClickEmpty).
This is not allowed! Only the listener object can have @SubscribeEvent methods.
    at net.neoforged.bus.EventBus.checkSupertypes(EventBus.java:151)
    at net.neoforged.bus.EventBus.checkSupertypes(EventBus.java:156)
    at net.neoforged.bus.EventBus.register(EventBus.java:102)
```

注意 `checkSupertypes` 是**递归**的（栈里两帧），所以隔代父类一样会炸。

**修法**：把带 `@SubscribeEvent` 的方法从「会被继承的基类」里搬出去，放进一个**平级的、不参与继承的**订阅持有类，
让原方法变成普通静态方法，由新类转调。

FPSMatch 的实际做法：
- `common/item/tool/FPSMToolItem.java`：删掉类上的 `@EventBusSubscriber`，删掉 `onLeftClickEmpty` 上的 `@SubscribeEvent`
  （方法体保留，仍可被外部调用）。
- 新增 `common/item/tool/ToolItemEvents.java`：`@EventBusSubscriber(modid = FPSMatch.MODID, bus = EventBusSubscriber.Bus.GAME)`
  + `@SubscribeEvent public static void onLeftClickEmpty(PlayerInteractEvent.LeftClickEmpty event) { FPSMToolItem.onLeftClickEmpty(event); }`。
- 于是 `EditToolItem extends FPSMToolItem` 自己带 `@EventBusSubscriber` + 自己的 `@SubscribeEvent` 就合法了。

---

## 排除的噪声（**不要**去修）

- `RuntimeDistCleaner/DISTXFORM: Attempted to load class net/minecraft/client/... for invalid dist DEDICATED_SERVER`
  （`net.minecraft.client.Minecraft`、`net.minecraft.client.sounds.SoundEngine`、`net.minecraft.client.gui.Font$DisplayMode`）
  —— 来自 **tacztweaks** 的 mixin（`tacztweaks.mixins.json` 的
  `feature.gameplay.behaviour.bullet_protection.ProtectionEnchantmentMixin`、
  `feature.sound_physics_evaluate.SoundEngineMixin`）与 **ldlib2**
  （`com.lowdragmc.lowdraglib2.editor.resource.IRendererResource`，经 Rhino `CachedClassInfo.getDeclaredMethods`）。
  移植前就存在，无害。
- `Error loading class: com/mrcrayfish/controllable/...`、`net/minecraft/client/renderer/MultiBufferSource$BufferSource`、
  `net/minecraft/client/particle/TextureSheetParticle` —— 客户端类在专用服务端缺失的正常 mixin 警告。
- `AutoModpack: Visit failed: .../taczpackupgrader (NoSuchFileException)` —— 无害。

---

## 类路径备忘（javap 判定 `IModBusEvent` 时三个 jar 缺一不可）

```
.gradle-home/caches/modules-2/files-2.1/net.neoforged.fancymodloader/loader/4.0.45/4a0968c2ec6234d58e0a9ed97acafc08cc8f33b5/loader-4.0.45.jar
    ↑ net.neoforged.fml.common.EventBusSubscriber 与 net.neoforged.fml.event.IModBusEvent
.gradle-home/caches/modules-2/files-2.1/net.neoforged/neoforge/21.1.253/37f196cd52e85a3bb5d48f40f8b7d13c29a00ecb/neoforge-21.1.253-universal.jar
    ↑ IModBusEvent 的实现类
.gradle-home/caches/neoformruntime/intermediate_results/compiledWithNeoForge_a0046ebdf41f634b0b890c000fcb8b87f4d1d9fd_output.jar
    ↑ Minecraft 类
.gradle-home/caches/modules-2/files-2.1/net.neoforged/bus/8.0.5/5b2d33285ab5d1554e9798ad98c40d6ea3868bd5/bus-8.0.5.jar
    ↑ net.neoforged.bus.*
```

## 还有一类「资源文件里的类名」bug

`src/main/resources/kubejs.plugins.txt` 里写的是**全限定类名**。FPSMatch 上游写成了
`com.ptcrys.fpsmatch.compat.kubejs.FPSMatchKubeJSPlugin`（应为 `net.ptcrys.*`），
导致 `[KubeJS/]: Failed to load plugin ... ClassNotFoundException`。
移植时请一并核对所有 `kubejs.plugins.txt` / `META-INF/services/*` / 反射配置里的包前缀。
