# BlockOffensive — 1.21.1 / NeoForge 移植

把 [BlockOffensive](https://github.com/PhasetransCrystal/BlockOffensive)（1.20.1 Forge）移植到
**Minecraft 1.21.1 + NeoForge 21.1.253**。分支 `1.21.1-neoforge-port`。

上游：`PhasetransCrystal/BlockOffensive`，GPL-3.0-only。移植基于上游 `6a4481e`。
BlockOffensive 是 FPSMatch 的玩法附属，提供 `cs` / `csdm`（爆破与团队死斗）。

## 状态

| 项 | 结果 |
|---|---|
| 编译 | 错误 742 → 0（`./gradlew build --offline` exit=0） |
| 单测 | 2 个 JUnit5 单测真跑通过（`useJUnitPlatform()` 需显式声明，否则 Gradle 默认 JUnit4 引擎会静默跳过） |
| 产物 | `build/libs/blockoffensive-1.1-1.21.1-port.jar` |
| 服务端实机 | 与 FPSMatch / codPattern 同服启动成功：`Done (1.224s)` |

## 构建

```bash
GRADLE_USER_HOME=$PWD/.gradle-home ./gradlew build --offline
```

`libs/` 需要第三方 jar，见 [libs/README.md](libs/README.md)（不入库）。
其中 `fpsmatch-1.3.0-1.21.1-port.jar` 由本组织的 FPSMatch 移植分支编译产出。
**不要跑 `./gradlew clean`**（原因同 FPSMatch）。

jar 是可复现的：`preserveFileTimestamps=false` + `reproducibleFileOrder=true`。

## 文档

- [PORT-NOTES.md](PORT-NOTES.md) — 移植记录，含 **7 条未在游戏内验证的风险**
  （ArmPose 退化为 `ArmPose.BLOCK` 的视觉损失、ItemStack 过网走 CODEC JSON、三个兼容层被删、
  `renderEntityInInventoryFollowsAngle` 裁剪、`ClientLevel.addPlayer`→`addEntity`、
  `FPSMGunReloadEvent` 无 `isCanceled` 守卫、皮肤/HUD 观感）。
- [NEOFORGE-1.21.1-RUNTIME-RULES.md](NEOFORGE-1.21.1-RUNTIME-RULES.md) — 7 条运行期规则的完整说明书
  （错误原文、触发模式、修法、javap 类路径备忘、不要修的噪声清单）。

## 许可

上游 GPL-3.0-only，本移植同样以 GPL-3.0-only 发布，见 [LICENSE](LICENSE)。
依 GPLv3 §5(a) 声明：本分支相对上游做了修改，修改内容即上述移植改动。
