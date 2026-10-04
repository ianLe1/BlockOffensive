# 编译所需的第三方 jar（不入库）

这些是本机编译时放在 `libs/` 的第三方 mod jar。它们各有自己的授权，**不随本仓库分发**。
复现编译时请自行从各自的发布页下载同名版本放进 `libs/`：

| 文件名 | 来源 |
|---|---|
| `architectury-13.0.11-neoforge.jar` | Architectury API |
| `cloth-config-15.0.140-neoforge.jar` | Cloth Config API |
| `curios-neoforge-9.5.1+1.21.1.jar` | Curios API |
| `fpsmatch-1.3.0-1.21.1-port.jar` | 本组织 FPSMatch 1.21.1 移植版，由同分支编译产出 |
| `kotlinforforge-5.12.0-all.jar` | Kotlin for Forge |
| `kubejs-neoforge-2101.7.2-build.377.jar` | KubeJS / Rhino (2101.x) |
| `ldlib2-neoforge-1.21.1-2.2.41-all.jar` | LDLib2 |
| `LesRaisins-Tactical-Equipements-1.21.1-0.4.3.jar` | LesRaisins' Tactical Equipements (lrtactical) |
| `ModernUI-NeoForge-1.21.1-3.13.0.1-universal.jar` | Modern UI (NeoForge) |
| `player-animation-lib-forge-2.0.4+1.21.1.jar` | Player Animator |
| `rhino-2101.2.8-build.91.jar` | KubeJS / Rhino (2101.x) |
| `simplebedrockmodel-2.2.1-neoforge+mc1.21.1.jar` | SimpleBedrockModel（从 TaCZ 的 META-INF/jarjar/ 内提取） |
| `tacz-neoforge-1.21.1-1.1.8-hotfix-r7.jar` | TaCZ / Timeless and Classics Zero (NeoForge 1.21.1) |
| `tacz-tweaks-3.0.0-alpha.10+1.21.1-neoforge.jar` | TaCZ Tweaks |

> 注：这些 jar 只用于**编译期**（`compileOnly fileTree(dir: "libs", include: ["*.jar"])`），运行期由 mods 目录里的正版 jar 提供。
