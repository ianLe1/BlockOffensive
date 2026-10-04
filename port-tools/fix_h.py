#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1.21.1 移植定点修复 H：长尾（皮肤 / 事件 / 实体同步 / 网络垫片 / 界面 / gametest）

判据全部来自 javap 实证与 fpsmatch-port 源码，见 PORT-NOTES.md。
只做机械替换，不改玩法逻辑。幂等。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', 'src', 'main', 'java')
STATS = []
CHANGED = set()


def bump(k, n):
    if n:
        STATS.append('%-64s %d' % (k, n))


def add_import(text, imp):
    line = 'import %s;' % imp
    if line in text:
        return text
    lines = text.split('\n')
    idxs = [i for i, l in enumerate(lines) if l.startswith('import ')]
    if not idxs:
        return text
    for i in idxs:
        if lines[i] > line:
            lines.insert(i, line)
            return '\n'.join(lines)
    lines.insert(idxs[-1] + 1, line)
    return '\n'.join(lines)


def sub(text, old, new, label, expect=None, required=True):
    c = text.count(old)
    if c == 0:
        if required:
            raise SystemExit('未命中（期望 %s）：%s' % (expect, label))
        return text, 0
    if expect is not None and c != expect:
        raise SystemExit('命中数不符：%s 期望 %s 实际 %d' % (label, expect, c))
    bump(label, c)
    return text.replace(old, new), c


def rx(text, pattern, repl, label, expect=None, required=True):
    text, n = re.subn(pattern, repl, text)
    if n == 0 and required:
        raise SystemExit('未命中（期望 %s）：%s' % (expect, label))
    if expect is not None and n != expect:
        raise SystemExit('命中数不符：%s 期望 %s 实际 %d' % (label, expect, n))
    bump(label, n)
    return text, n


FILES = {}


def load(rel):
    if rel not in FILES:
        FILES[rel] = open(os.path.join(ROOT, rel), encoding='utf-8').read()
    return FILES[rel]


def put(rel, text):
    if text != load(rel):
        FILES[rel] = text
        CHANGED.add(rel)


# ── 1. GUI 残留 ─────────────────────────────────────────────────────
def r_gui():
    rel = 'net/ptcrys/blockoffensive/client/screen/hud/CSGameHud.java'
    t = load(rel)
    t, _ = sub(t, 'VanillaGuiLayers.MOUNT_HEALTH', 'VanillaGuiLayers.VEHICLE_HEALTH',
               '%s: MOUNT_HEALTH -> VEHICLE_HEALTH' % rel, expect=1)
    put(rel, t)

    rel = 'net/ptcrys/blockoffensive/client/shop/ShopPresentationEvents.java'
    t = load(rel)
    t, _ = sub(t, 'import net.neoforged.neoforge.client.gui.overlay.VanillaGuiOverlay;',
               'import net.neoforged.neoforge.client.gui.VanillaGuiLayers;', '%s: import' % rel, required=False)
    t, _ = sub(t, 'VanillaGuiOverlay.CROSSHAIR.id()', 'VanillaGuiLayers.CROSSHAIR',
               '%s: CROSSHAIR 比较' % rel, expect=1)
    put(rel, t)


# ── 2. 皮肤族 ───────────────────────────────────────────────────────
SKIN_FILES = [
    'net/ptcrys/blockoffensive/client/screen/hud/CSCompetitiveTabPanel.java',
    'net/ptcrys/blockoffensive/client/screen/hud/CSDMOverlay.java',
    'net/ptcrys/blockoffensive/client/screen/hud/CSDMTabRenderer.java',
    'net/ptcrys/blockoffensive/client/screen/hud/CSMvpHud.java',
    'net/ptcrys/blockoffensive/client/screen/hud/CSGameOverlay.java',
    'net/ptcrys/blockoffensive/client/screen/hud/CSSpectatorHudOverlay.java',
]


def r_skin():
    for rel in SKIN_FILES:
        t = load(rel)
        t, n1 = rx(t, r'(\w+)\.getSkinLocation\(\)', r'\1.getSkin().texture()',
                   '%s: getSkinLocation -> getSkin().texture()' % rel, required=False)
        t, n2 = rx(t, r'(\w+)\.getSkinTextureLocation\(\)', r'\1.getSkin().texture()',
                   '%s: getSkinTextureLocation -> getSkin().texture()' % rel, required=False)
        if n1 + n2 == 0:
            raise SystemExit('该文件没有皮肤站点：' + rel)
        put(rel, t)

    rel = 'net/ptcrys/blockoffensive/client/shop/ShopPlayerPreview.java'
    t = load(rel)
    t, _ = sub(t, '''    @Override
    public ResourceLocation getSkinTextureLocation() {
        return source.getSkinTextureLocation();
    }

    @Override
    public String getModelName() {
        return source.getModelName();
    }

    @Override
    public ResourceLocation getCloakTextureLocation() {
        return null;
    }
''', '''    /** 1.21.1：皮肤/披风/模型三个访问器合并为 getSkin()（PlayerSkin record）。 */
    @Override
    public PlayerSkin getSkin() {
        return source.getSkin();
    }
''', '%s: 三个皮肤 override 合成 getSkin()' % rel, expect=1)
    t, _ = sub(t, 'InventoryScreen.renderEntityInInventoryFollowsAngle(graphics, x, y, scale, 0.9f, 0, this);',
               'InventoryScreen.renderEntityInInventoryFollowsAngle(graphics, x - scale, y - scale, x + scale, y + scale, scale, 0.9f, 0f, 0f, this);',
               '%s: followsAngle 9 参新签名' % rel, expect=1)
    t = add_import(t, 'net.minecraft.client.resources.PlayerSkin')
    put(rel, t)


# ── 3. KillCamManager ───────────────────────────────────────────────
def r_killcam():
    rel = 'net/ptcrys/blockoffensive/client/spec/KillCamManager.java'
    t = load(rel)
    t, _ = sub(t, 'bus = Bus.FORGE', 'bus = Bus.GAME', '%s: Bus.FORGE -> Bus.GAME' % rel, expect=1)
    t, _ = sub(t, '''        Window win = e.getWindow();
        renderDamageDirection(e.getGuiGraphics(), win.getGuiScaledWidth(), win.getGuiScaledHeight(), timeline.shakeProgress(0.0F));
        renderKillHud(Minecraft.getInstance(), e.getGuiGraphics(),
                win.getGuiScaledWidth(), win.getGuiScaledHeight());''',
               '''        GuiGraphics gg = e.getGuiGraphics();
        renderDamageDirection(gg, gg.guiWidth(), gg.guiHeight(), timeline.shakeProgress(0.0F));
        renderKillHud(Minecraft.getInstance(), gg, gg.guiWidth(), gg.guiHeight());''',
               '%s: RenderGuiEvent 无 getWindow' % rel, expect=1)
    t, _ = sub(t, 'Minecraft.getInstance().getSkinManager().getInsecureSkinLocation(new GameProfile(id, name))',
               'Minecraft.getInstance().getSkinManager().getInsecureSkin(new GameProfile(id, name)).texture()',
               '%s: getInsecureSkinLocation -> getInsecureSkin().texture()' % rel, expect=1)
    put(rel, t)


# ── 4. 音频 ─────────────────────────────────────────────────────────
def r_audio():
    rel = 'net/ptcrys/blockoffensive/client/mvp/MvpLocalMusicManager.java'
    t = load(rel)
    t, _ = sub(t, 'import com.mojang.blaze3d.audio.OggAudioStream;',
               'import net.minecraft.client.sounds.JOrbisAudioStream;', '%s: import' % rel, expect=1)
    t, _ = sub(t, 'OggAudioStream ogg = new OggAudioStream(in)) {',
               'JOrbisAudioStream ogg = new JOrbisAudioStream(in)) {', '%s: 构造' % rel, expect=1)
    put(rel, t)


# ── 5. 实体同步 ─────────────────────────────────────────────────────
def r_entity():
    rel = 'net/ptcrys/blockoffensive/entity/CompositionC4Entity.java'
    t = load(rel)
    t, _ = sub(t, '''    protected void defineSynchedData() {
        this.entityData.define(DATA_EXPLOSION_RADIUS, DEFAULT_EXPLOSION_RADIUS);
        this.entityData.define(DATA_DELETE_TIME, 0);
        this.entityData.define(DATA_EXPLOSION_INTERACTION, Level.ExplosionInteraction.NONE.ordinal());
        this.entityData.define(DATA_INSTANT_KILL_RADIUS, DEFAULT_INSTANT_KILL_RADIUS);
    }''', '''    protected void defineSynchedData(SynchedEntityData.Builder builder) {
        builder.define(DATA_EXPLOSION_RADIUS, DEFAULT_EXPLOSION_RADIUS);
        builder.define(DATA_DELETE_TIME, 0);
        builder.define(DATA_EXPLOSION_INTERACTION, Level.ExplosionInteraction.NONE.ordinal());
        builder.define(DATA_INSTANT_KILL_RADIUS, DEFAULT_INSTANT_KILL_RADIUS);
    }''', '%s: defineSynchedData(Builder)' % rel, expect=1)
    t, _ = sub(t, 'super.onAddedToWorld();', 'super.onAddedToLevel();', '%s: super.onAddedToLevel' % rel, expect=1)
    t, _ = sub(t, 'public void onAddedToWorld() {', 'public void onAddedToLevel() {', '%s: onAddedToLevel' % rel, expect=1)
    t, _ = sub(t, 'super.onRemovedFromWorld();', 'super.onRemovedFromLevel();', '%s: super.onRemovedFromLevel' % rel, expect=1)
    t, _ = sub(t, 'public void onRemovedFromWorld() {', 'public void onRemovedFromLevel() {', '%s: onRemovedFromLevel' % rel, expect=1)
    put(rel, t)

    rel = 'net/ptcrys/blockoffensive/entity/BOEntityRegister.java'
    t = load(rel)
    t, _ = sub(t, 'RegistryObject<EntityType<CompositionC4Entity>>',
               'DeferredHolder<EntityType<?>, EntityType<CompositionC4Entity>>', '%s: RegistryObject' % rel, expect=1)
    t, _ = sub(t, 'import net.minecraft.world.entity.EntityType;\n',
               'import net.minecraft.world.entity.EntityType;\n', '%s: noop' % rel, required=False)
    t = add_import(t, 'net.neoforged.neoforge.registries.DeferredHolder')
    put(rel, t)

    rel = 'net/ptcrys/blockoffensive/item/BOItemRegister.java'
    t = load(rel)
    t, _ = sub(t, 'DeferredHolder<BombDisposalKit, BombDisposalKit>', 'DeferredHolder<Item, BombDisposalKit>',
               '%s: DeferredHolder 泛型' % rel, expect=1)
    put(rel, t)


# ── 6. CompositionC4 ────────────────────────────────────────────────
def r_c4_item():
    rel = 'net/ptcrys/blockoffensive/item/CompositionC4.java'
    t = load(rel)
    t, _ = sub(t, 'event.setUseItem(Event.Result.ALLOW);', 'event.setUseItem(TriState.TRUE);',
               '%s: Result.ALLOW -> TriState.TRUE' % rel, expect=1)
    t, _ = sub(t, 'event.setUseBlock(Event.Result.DENY);', 'event.setUseBlock(TriState.FALSE);',
               '%s: Result.DENY -> TriState.FALSE' % rel, expect=1)
    old_lambda = '''            private static final HumanoidModel.ArmPose ITEM_C4 = HumanoidModel.ArmPose.create("ITEM_C4", true, (model, entity, arm) -> {
                float rotationAngle = (float) Math.toRadians(30);  // 将角度设置为 30 度（可以根据需要调整）
                // 右臂旋转
                if (arm == HumanoidArm.RIGHT) {
                    model.rightArm.xRot = -rotationAngle;  // 右臂旋转向中间
                    model.rightArm.yRot = -rotationAngle; // 右臂绕 Y 轴旋转
                }
                // 左臂旋转
                else {
                    model.leftArm.xRot = -rotationAngle;  // 左臂旋转向中间
                    model.leftArm.yRot = rotationAngle;   // 左臂绕 Y 轴旋转（相反方向）
                }
            });'''
    new_lambda = '''            // 1.21.1：HumanoidModel.ArmPose 成了 final enum（IExtensibleEnum），
            // ArmPose.create(...) 被删；自定义姿势要走 NeoForge 枚举扩展（enumextensions.json
            // + EnumProxy）。本移植版退化为 BLOCK（双手持物近似姿势），见 PORT-NOTES.md。
            private static final HumanoidModel.ArmPose ITEM_C4 = HumanoidModel.ArmPose.BLOCK;'''
    t, _ = sub(t, old_lambda, new_lambda, '%s: ArmPose.create -> ArmPose.BLOCK' % rel, expect=1)
    t, _ = sub(t, 'public int getUseDuration(@NotNull ItemStack stack) {',
               'public int getUseDuration(@NotNull ItemStack stack, @NotNull LivingEntity entity) {',
               '%s: getUseDuration 两参' % rel, expect=1)
    t = add_import(t, 'net.neoforged.neoforge.common.util.TriState')
    put(rel, t)


# ── 7. DeathMessage / 命令 ──────────────────────────────────────────
def r_misc_server():
    rel = 'net/ptcrys/blockoffensive/data/DeathMessage.java'
    t = load(rel)
    t, _ = sub(t, 'killer.hasEffect(FPSMEffectRegister.FLASH_BLINDNESS.get())',
               'killer.hasEffect(FPSMEffectRegister.FLASH_BLINDNESS)',
               '%s: hasEffect(Holder<MobEffect>)' % rel, expect=1)
    put(rel, t)

    rel = 'net/ptcrys/blockoffensive/command/BOTaczLiveFireDebugCommand.java'
    t = load(rel)
    t, _ = sub(t, '''                    .setFireMode(FireMode.SEMI)
                    .forceBuild();''', '''                    .setFireMode(FireMode.SEMI)
                    .forceBuild(level.registryAccess());''', '%s: forceBuild(Provider)' % rel, expect=1)
    put(rel, t)


# ── 8. 网络垫片：getChannelFromCache ────────────────────────────────
def r_network():
    rel = 'net/ptcrys/blockoffensive/client/shop/ShopDropClientState.java'
    t = load(rel)
    t, _ = sub(t, '''        NetworkPacketRegister.getChannelFromCache(ShopNearbyDropsRequestC2SPacket.class)
                .sendToServer(new ShopNearbyDropsRequestC2SPacket(NEXT_LIST_REQUEST.incrementAndGet()));''',
               '''        NetworkPacketRegister.sendToServer(new ShopNearbyDropsRequestC2SPacket(NEXT_LIST_REQUEST.incrementAndGet()));''',
               '%s: requestRefresh' % rel, expect=1)
    t, _ = sub(t, '''        NetworkPacketRegister.getChannelFromCache(ShopDropPickupC2SPacket.class)
                .sendToServer(new ShopDropPickupC2SPacket(UUID.randomUUID(), entityId));''',
               '''        NetworkPacketRegister.sendToServer(new ShopDropPickupC2SPacket(UUID.randomUUID(), entityId));''',
               '%s: requestPickup' % rel, expect=1)
    put(rel, t)

    rel = 'net/ptcrys/blockoffensive/client/screen/CSGameShopScreen.java'
    t = load(rel)
    t, _ = sub(t, 'NetworkPacketRegister.getChannelFromCache(ShopActionC2SPacket.class).sendToServer(new ShopActionC2SPacket(',
               'NetworkPacketRegister.sendToServer(new ShopActionC2SPacket(',
               '%s: transmitShopAction' % rel, expect=1)
    t, _ = sub(t, '''    @Override
    public void renderBackground(GuiGraphics graphics) {''',
               '''    @Override
    public void renderBackground(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {''',
               '%s: renderBackground 四参' % rel, expect=1)
    put(rel, t)


# ── 9. 界面杂项 ─────────────────────────────────────────────────────
def r_screens():
    rel = 'net/ptcrys/blockoffensive/client/screen/TeamChatScreen.java'
    t = load(rel)
    t, _ = sub(t, '''    public boolean handleChatInput(String pInput, boolean pAddToRecentChat) {''',
               '''    public void handleChatInput(String pInput, boolean pAddToRecentChat) {''',
               '%s: handleChatInput 返回 void' % rel, expect=1)
    t, _ = sub(t, '''                super.handleChatInput(pInput, pAddToRecentChat);
                return minecraft.screen == this;''',
               '''                super.handleChatInput(pInput, pAddToRecentChat);
                return;''', '%s: 早退 return' % rel, expect=1)
    t, _ = sub(t, '''            FPSMClient.getGlobalData().getCurrentClientTeam().ifPresent(team -> team.sendMessage(teamMessage));
        }
        return minecraft.screen == this;
    }''', '''            FPSMClient.getGlobalData().getCurrentClientTeam().ifPresent(team -> team.sendMessage(teamMessage));
        }
    }''', '%s: 尾部 return' % rel, expect=1)
    put(rel, t)

    for rel in ('net/ptcrys/blockoffensive/client/screen/MvpDirSelectScreen.java',
                'net/ptcrys/blockoffensive/client/screen/MvpMusicScreen.java'):
        t = load(rel)
        t, _ = sub(t, 'this.renderBackground(graphics);',
                   'this.renderBackground(graphics, mouseX, mouseY, partialTick);',
                   '%s: renderBackground 调用' % rel, expect=1)
        put(rel, t)


# ── 10. 事件签名 ────────────────────────────────────────────────────
def r_events():
    rel = 'net/ptcrys/blockoffensive/intro/IntroRuntimeController.java'
    t = load(rel)
    t, _ = sub(t, '''    public static void onServerTick(ServerTickEvent.Post event) {
        if (event.side != LogicalSide.SERVER) {
            return;
        }
        if (!ACTIVE.isEmpty()) {''',
               '''    public static void onServerTick(ServerTickEvent.Post event) {
        // 1.21.1：TickEvent 拆成 .Pre/.Post 后不再带 side；ServerTickEvent 本来就只在服务端发。
        if (!ACTIVE.isEmpty()) {''', '%s: 去掉 side 守卫' % rel, expect=1)
    t, _ = sub(t, '''    public static void onInteract(PlayerInteractEvent event) {
        if (event.getEntity() instanceof ServerPlayer player && PLAYER_TO_SEQUENCE.containsKey(player.getUUID())) {
            event.setCanceled(true);
        }
    }''', '''    public static void onInteract(PlayerInteractEvent event) {
        // 1.21.1：PlayerInteractEvent 基类不再可取消（也没有 setUseItem/setUseBlock），
        // 只有 RightClickBlock / RightClickItem / LeftClickBlock 三个子类能拦；逐个分派。
        if (!(event.getEntity() instanceof ServerPlayer player) || !PLAYER_TO_SEQUENCE.containsKey(player.getUUID())) {
            return;
        }
        if (event instanceof PlayerInteractEvent.LeftClickBlock left) {
            left.setUseBlock(TriState.FALSE);
            left.setUseItem(TriState.FALSE);
        } else if (event instanceof PlayerInteractEvent.RightClickBlock right) {
            right.setUseBlock(TriState.FALSE);
            right.setUseItem(TriState.FALSE);
        } else if (event instanceof PlayerInteractEvent.RightClickItem item) {
            item.setCanceled(true);
        }
    }''', '%s: onInteract 子类分派' % rel, expect=1)
    t = add_import(t, 'net.neoforged.neoforge.common.util.TriState')
    put(rel, t)

    rel = 'net/ptcrys/blockoffensive/map/CSGameEvents.java'
    t = load(rel)
    t, _ = sub(t, '''        if (event.player.level().isClientSide()) return;
        if (!(event.player instanceof ServerPlayer player)) return;''',
               '''        if (event.getEntity().level().isClientSide()) return;
        if (!(event.getEntity() instanceof ServerPlayer player)) return;''',
               '%s: event.player -> getEntity()' % rel, expect=1)
    t, _ = sub(t, '''    public static void onGunReload(FPSMGunReloadEvent event) {
        if (event.isCanceled()) return;
''', '''    public static void onGunReload(FPSMGunReloadEvent event) {
        // 1.21.1：移植版 FPSMGunReloadEvent extends Event 且未实现 ICancellableEvent，
        // 没有 isCanceled()；上游该守卫失去对应物（见 PORT-NOTES.md）。
''', '%s: 去掉 isCanceled 守卫' % rel, expect=1)
    put(rel, t)

    rel = 'net/ptcrys/blockoffensive/spectator/BOSpecManager.java'
    t = load(rel)
    t, _ = sub(t, '''        if (event.side.isClient()) return;
        if (!(event.player instanceof ServerPlayer spectator)) return;''',
               '''        if (event.getEntity().level().isClientSide()) return;
        if (!(event.getEntity() instanceof ServerPlayer spectator)) return;''',
               '%s: side/player -> getEntity()' % rel, expect=1)
    put(rel, t)

    rel = 'net/ptcrys/blockoffensive/intro/client/IntroClientController.java'
    t = load(rel)
    t, _ = sub(t, 'level.addPlayer(PREVIEW_ENTITY_ID_BASE - i, player);',
               'level.addEntity(player); // 1.21.1：ClientLevel.addPlayer(id, player) 已删，改 addEntity（id 由 level 分配）',
               '%s: addPlayer -> addEntity' % rel, expect=1)
    put(rel, t)


# ── 11. gametest ────────────────────────────────────────────────────
def r_gametests():
    rel = 'net/ptcrys/blockoffensive/gametest/DeathmatchLifecycleGameTests.java'
    t = load(rel)
    t, _ = sub(t, 'import net.minecraft.network.protocol.game.ClientboundCustomPayloadPacket;',
               'import net.minecraft.network.protocol.common.ClientboundCustomPayloadPacket;',
               '%s: ClientboundCustomPayloadPacket 换包' % rel, expect=1)
    t, _ = sub(t, 'import net.ptcrys.fpsmatch.common.packet.register.NetworkPacketRegister.PayloadDirection;',
               'import net.ptcrys.fpsmatch.common.packet.register.ReflectivePayload;',
               '%s: 换 import' % rel, expect=1)
    t, _ = sub(t, 'List<Integer> packets = new ArrayList<>();',
               'List<Class<?>> packets = new ArrayList<>();', '%s: packets 类型' % rel, expect=1)
    t, _ = sub(t, '''                    if (packet instanceof ClientboundCustomPayloadPacket payload && payload.getIdentifier().toString().equals("fpsmatch:main")) {
                        FriendlyByteBuf data = new FriendlyByteBuf(payload.getData().copy());
                        try {
                            packets.add(data.readVarInt());
                        } finally {
                            data.release();
                        }
                    }''',
               '''                    // 1.21.1：SimpleChannel 的「单通道 + varint 鉴别码」换成了 per-payload 类型，
                    // 所以直接记录载荷承载的上游包类（ReflectivePayload.body()）来判定顺序。
                    if (packet instanceof ClientboundCustomPayloadPacket wrapped
                            && wrapped.payload() instanceof ReflectivePayload reflective) {
                        packets.add(reflective.body().getClass());
                    }''', '%s: 收集载荷包类' % rel, expect=1)
    t, _ = sub(t, 'player.connection = new ServerGamePacketListenerImpl(helper.getLevel().getServer(), connection, player);',
               'player.connection = new ServerGamePacketListenerImpl(helper.getLevel().getServer(), connection, player,\n                    CommonListenerCookie.createInitial(player.getGameProfile(), false));',
               '%s: 构造器补 CommonListenerCookie' % rel, expect=1)
    t, _ = sub(t, '''            int resetType = packetType(new FPSMatchStatsResetS2CPacket());
            int mapType = packetType(new FPSMatchGameTypeS2CPacket(fixture.map.getMapName(), "csdm", false, false));
            int teamType = packetType(FPSMAddTeamS2CPacket.of(fixture.map.getCT()));
            int statsType = packetType(TeamPlayerStatsS2CPacket.of(fixture.map.getCT(), fixture.map.getMapTeams().getPlayerData(player).orElseThrow()));''',
               '''            Class<?> resetType = packetType(new FPSMatchStatsResetS2CPacket());
            Class<?> mapType = packetType(new FPSMatchGameTypeS2CPacket(fixture.map.getMapName(), "csdm", false, false));
            Class<?> teamType = packetType(FPSMAddTeamS2CPacket.of(fixture.map.getCT()));
            Class<?> statsType = packetType(TeamPlayerStatsS2CPacket.of(fixture.map.getCT(), fixture.map.getMapTeams().getPlayerData(player).orElseThrow()));''',
               '%s: 类型变量' % rel, expect=1)
    t, _ = sub(t, '''    private static int packetType(Object message) {
        ClientboundCustomPayloadPacket packet = (ClientboundCustomPayloadPacket) FPSMatch.INSTANCE.toVanillaPacket(message, PayloadDirection.TO_CLIENT);
        FriendlyByteBuf data = new FriendlyByteBuf(packet.getData().copy());
        try {
            return data.readVarInt();
        } finally {
            data.release();
        }
    }''', '''    /** 1.21.1：没有 FPSMatch.INSTANCE.toVanillaPacket，也不需要——直接比包类。 */
    private static Class<?> packetType(Object message) {
        return message.getClass();
    }''', '%s: packetType 重写' % rel, expect=1)
    t = add_import(t, 'net.minecraft.server.network.CommonListenerCookie')
    put(rel, t)

    rel = 'net/ptcrys/blockoffensive/gametest/ShopDropGameTests.java'
    t = load(rel)
    t, _ = sub(t, 'vanilla.setThrower(UUID.randomUUID()); // public drop: thrower != restrictive owner',
               '// 1.21.1：ItemEntity#setThrower 收 Entity（不再是 UUID），且本模组拾取判定只读 target UUID，\n        // 不设 target 即等于「公开掉落」。',
               '%s: setThrower' % rel, expect=1)
    t, _ = sub(t, '''        helper.assertTrue(net.ptcrys.fpsmatch.common.packet.register.NetworkPacketRegister.getChannelFromCache(
                net.ptcrys.fpsmatch.common.packet.shop.ShopActionResultS2CPacket.class) != null,
                "shop action result must be registered on the server before purchases");''',
               '''        // 1.21.1：移植版 NetworkPacketRegister 用私有静态 TYPES 映射，没有 getChannelFromCache，
        // 因此改为断言 reflective payload 契约（注册时若违约会直接抛异常）。
        Class<?> packetClass = net.ptcrys.fpsmatch.common.packet.shop.ShopActionResultS2CPacket.class;
        helper.assertTrue(java.lang.reflect.Modifier.isStatic(
                        packetClass.getMethod("encode", packetClass, FriendlyByteBuf.class).getModifiers())
                        && java.lang.reflect.Modifier.isStatic(
                        packetClass.getMethod("decode", FriendlyByteBuf.class).getModifiers()),
                "shop action result must satisfy the reflective payload contract before purchases");''',
               '%s: 注册断言改写' % rel, expect=1)
    t = add_import(t, 'net.minecraft.network.FriendlyByteBuf')
    put(rel, t)

    rel = 'net/ptcrys/blockoffensive/gametest/ShopRefundGameTests.java'
    t = load(rel)
    t, _ = sub(t, 'legacy.codec.encodeStart(JsonOps.INSTANCE, legacy).getOrThrow(false, message -> {});',
               'legacy.codec.encodeStart(JsonOps.INSTANCE, legacy).getOrThrow(message -> new IllegalStateException(message));',
               '%s: encodeStart getOrThrow' % rel, expect=1)
    t, _ = sub(t, 'legacy.codec.parse(JsonOps.INSTANCE, saved).getOrThrow(false, message -> {});',
               'legacy.codec.parse(JsonOps.INSTANCE, saved).getOrThrow(message -> new IllegalStateException(message));',
               '%s: parse getOrThrow' % rel, expect=1)
    put(rel, t)



def _already_applied():
    """幂等门禁：本脚本的全部改动都已落地时整体跳过（部分落地则仍走断言路径报错）。"""
    checks = [
        ('client/screen/hud/CSGameHud.java', 'VanillaGuiLayers.VEHICLE_HEALTH'),
        ('client/screen/hud/CSMvpHud.java', '.getSkin().texture()'),
        ('client/shop/ShopPlayerPreview.java', 'PlayerSkin getSkin()'),
        ('entity/CompositionC4Entity.java', 'defineSynchedData(SynchedEntityData.Builder builder)'),
        ('client/mvp/MvpLocalMusicManager.java', 'JOrbisAudioStream'),
        ('client/spec/KillCamManager.java', 'gg.guiWidth()'),
        ('item/CompositionC4.java', 'TriState.TRUE'),
        ('intro/IntroRuntimeController.java', 'instanceof PlayerInteractEvent.LeftClickBlock'),
        ('gametest/ShopRefundGameTests.java', 'getOrThrow(message -> new IllegalStateException(message))'),
    ]
    for rel, marker in checks:
        p = os.path.join(ROOT, 'net/ptcrys/blockoffensive', rel)
        if marker not in open(p, encoding='utf-8').read():
            return False
    return True


def main():
    dry = '--dry' in sys.argv
    if _already_applied():
        print('== fix_h 命中 ==\n  已全部应用，跳过（幂等门禁）')
        return
    r_gui()
    r_skin()
    r_killcam()
    r_audio()
    r_entity()
    r_c4_item()
    r_misc_server()
    r_network()
    r_screens()
    r_events()
    r_gametests()

    g = globals()
    print('== fix_h 命中 ==')
    for s in STATS:
        print('  ' + s)
    print('  涉及文件 %d 个' % len(CHANGED))
    for c in sorted(CHANGED):
        print('    ' + c)
    if not dry:
        for rel in CHANGED:
            open(os.path.join(ROOT, rel), 'w', encoding='utf-8').write(FILES[rel])


if __name__ == '__main__':
    main()
