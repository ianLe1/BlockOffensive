package net.ptcrys.blockoffensive.item;

import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.common.util.TriState;
import net.ptcrys.blockoffensive.entity.CompositionC4Entity;
import net.ptcrys.blockoffensive.event.CSGameMapEvent;
import net.ptcrys.blockoffensive.map.CSGameMap;
import net.ptcrys.blockoffensive.sound.BOSoundRegister;
import net.ptcrys.blockoffensive.util.BOUtil;
import net.ptcrys.fpsmatch.FPSMatch;
import net.ptcrys.fpsmatch.common.capability.team.ShopCapability;
import net.ptcrys.fpsmatch.common.packet.FPSMSoundPlayS2CPacket;
import net.ptcrys.fpsmatch.core.FPSMCore;
import net.ptcrys.fpsmatch.core.item.BlastBombItem;
import net.ptcrys.fpsmatch.core.map.BaseMap;
import net.ptcrys.fpsmatch.core.team.ServerTeam;

import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.TextColor;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.HumanoidArm;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.UseAnim;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.Level;
import net.neoforged.neoforge.client.extensions.common.IClientItemExtensions;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.entity.player.PlayerInteractEvent;
import net.neoforged.bus.api.Event;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.Mod;

import com.mojang.blaze3d.vertex.PoseStack;
import org.jetbrains.annotations.NotNull;
import org.joml.Vector3f;

import java.util.Optional;
import java.util.function.Consumer;

@EventBusSubscriber(modid = "blockoffensive", bus = EventBusSubscriber.Bus.GAME)
public class CompositionC4 extends Item implements BlastBombItem {

    @SubscribeEvent
    public static void onRightClickBlock(PlayerInteractEvent.RightClickBlock event) {
        Player player = event.getEntity();
        ItemStack stack = player.getItemInHand(event.getHand());

        if (stack.getItem() instanceof CompositionC4) {
            event.setUseItem(TriState.TRUE);
            event.setUseBlock(TriState.FALSE);
        }
    }

    public CompositionC4(Properties pProperties) {
        super(pProperties);
    }

    @Override
    public void initializeClient(Consumer<IClientItemExtensions> consumer) {
        consumer.accept(new IClientItemExtensions() {

            // 1.21.1：HumanoidModel.ArmPose 成了 final enum（IExtensibleEnum），
            // ArmPose.create(...) 被删；自定义姿势要走 NeoForge 枚举扩展（enumextensions.json
            // + EnumProxy）。本移植版退化为 BLOCK（双手持物近似姿势），见 PORT-NOTES.md。
            private static final HumanoidModel.ArmPose ITEM_C4 = HumanoidModel.ArmPose.BLOCK;

            @Override
            public HumanoidModel.ArmPose getArmPose(LivingEntity entityLiving, InteractionHand hand, ItemStack itemStack) {
                if (!itemStack.isEmpty()) {
                    if (entityLiving.getUsedItemHand() == hand && entityLiving.getUseItemRemainingTicks() > 0) {
                        return ITEM_C4;
                    }
                }
                return HumanoidModel.ArmPose.EMPTY;
            }

            @Override
            public boolean applyForgeHandTransform(PoseStack poseStack, LocalPlayer player, HumanoidArm arm, ItemStack itemInHand, float partialTick, float equipProcess, float swingProcess) {
                int i = arm == HumanoidArm.RIGHT ? 1 : -1;
                poseStack.translate(i * 0.36F, -0.52F, -0.72F);
                if (player.getUseItem() == itemInHand && player.isUsingItem()) {
                    poseStack.translate(0.0, -0.05, 0.0);
                }
                return true;
            }
        });
    }

    public void inventoryTick(@NotNull ItemStack pStack, @NotNull Level pLevel, @NotNull Entity pEntity, int pSlotId, boolean pIsSelected) {
        if (pLevel instanceof ServerLevel serverLevel && pEntity instanceof ServerPlayer player) {
            int i = player.getInventory().countItem(BOItemRegister.C4.get());
            if (i > 0) {
                double yawRad = Math.toRadians(player.getYRot());
                double distance = -0.5;
                double xOffset = -Math.sin(yawRad) * distance;
                double zOffset = Math.cos(yawRad) * distance;
                serverLevel.sendParticles(new DustParticleOptions(new Vector3f(1, 0.1f, 0.1f), 1), player.getX() + xOffset, player.getY() + 1, player.getZ() + zOffset, 1, 0, 0, 0, 1);
            }
        }
    }

    @Override
    public @NotNull InteractionResultHolder<ItemStack> use(@NotNull Level level, @NotNull Player player, @NotNull InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);
        if (level.isClientSide) return InteractionResultHolder.success(stack);

        FPSMCore core = FPSMCore.getInstance();
        Optional<BaseMap> optional = core.getMapByPlayer(player);

        if (optional.isEmpty()) {
            player.displayClientMessage(Component.translatable("blockoffensive.item.c4.use.fail.noMap"), true);
            return InteractionResultHolder.pass(stack);
        }
        BaseMap baseMap = optional.get();

        if (!(baseMap instanceof CSGameMap map)) {
            player.displayClientMessage(Component.translatable("blockoffensive.item.c4.use.fail.noMap"), true);
            return InteractionResultHolder.pass(stack);
        }

        if (!baseMap.isStart()) {
            player.displayClientMessage(Component.translatable("blockoffensive.item.c4.use.fail.map.notStart"), true);
            return InteractionResultHolder.pass(stack);
        }

        ServerTeam team = baseMap.getMapTeams().getTeamByPlayer(player).orElse(null);
        if (team == null) {
            player.displayClientMessage(Component.translatable("blockoffensive.item.c4.use.fail.team.notInTeam"), true);
            return InteractionResultHolder.pass(stack);
        }

        boolean canPlace = map.canPlantBomb(player);
        boolean inBombArea = map.checkPlayerIsInBombArea(player);

        if (canPlace && inBombArea) {
            player.startUsingItem(hand);
            playClickSound(level, player, team);
            team.sendMessage(BOUtil.buildTeamChatMessage(player, team, Component.translatable("blockoffensive.place.message.c4"), Component.empty(), TextColor.parseColor(team.name.equals("ct") ? "#96C8FA" : "#EAC055").result().orElseThrow()));
            return InteractionResultHolder.consume(stack);
        }

        if (!canPlace) {
            player.displayClientMessage(Component.translatable("blockoffensive.item.c4.use.fail"), true);
        } else if (map.getBombAreaData().isEmpty()) {
            player.displayClientMessage(Component.translatable("blockoffensive.item.c4.use.fail.noArea"), true);
        } else {
            player.displayClientMessage(Component.translatable("blockoffensive.item.c4.use.fail.notInArea"), true);
        }
        return InteractionResultHolder.pass(stack);
    }

    public @NotNull InteractionResult useOn(UseOnContext context) {
        Player player = context.getPlayer();
        Level level = context.getLevel();

        if (player == null) return InteractionResult.PASS;

        if (level.isClientSide) {
            return InteractionResult.SUCCESS;
        }

        InteractionResultHolder<ItemStack> result = this.use(level, player, context.getHand());

        if (result.getResult() == InteractionResult.CONSUME) {
            return InteractionResult.SUCCESS;
        }

        return InteractionResult.PASS;
    }

    private void playClickSound(Level level, LivingEntity entity, ServerTeam team) {
        level.playSound(null, entity.getX(), entity.getY(), entity.getZ(),
                BOSoundRegister.CLICK.get(), SoundSource.PLAYERS, 3.0F, 1.0F);
        team.getOnline().forEach(player -> {
            FPSMatch.sendToPlayer(player, new FPSMSoundPlayS2CPacket(BOSoundRegister.T_PLANTINGBOMB.get().getLocation()));
        });
    }

    @Override
    public void onUseTick(@NotNull Level level, @NotNull LivingEntity entity,
                          @NotNull ItemStack stack, int remainingTicks) {
        if (!(level.isClientSide())) return;

        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || !entity.getUUID().equals(mc.player.getUUID())) return;
        // 禁用移动控制
        disableMovementKeys();

        if (remainingTicks != 80 && remainingTicks % 8 == 0) {
            level.playLocalSound(entity.getX(), entity.getY(), entity.getZ(), BOSoundRegister.CLICK.get(), SoundSource.PLAYERS, 3.0F, 1.0F, false);
        }
    }

    // 1.21.1: 签名里不能出现客户端类。本类带 @EventBusSubscriber，AutomaticEventSubscriber
    // 会对它调 Class#getDeclaredMethods()（会解析每个声明方法的描述符），而 RuntimeDistCleaner
    // 在 DEDICATED_SERVER 下拒绝加载 net.minecraft.client.Minecraft ⇒ "Attempted to load class
    // net/minecraft/client/Minecraft for invalid dist"。方法体里用 Minecraft 是安全的，
    // 只有签名不行，所以这里把参数去掉、改成方法体内取实例。
    private void disableMovementKeys() {
        Minecraft mc = Minecraft.getInstance();
        mc.options.keyUp.setDown(false);
        mc.options.keyLeft.setDown(false);
        mc.options.keyDown.setDown(false);
        mc.options.keyRight.setDown(false);
        mc.options.keyJump.setDown(false);
    }

    @Override
    public @NotNull ItemStack finishUsingItem(@NotNull ItemStack stack, @NotNull Level level,
                                              @NotNull LivingEntity entity) {
        if (!(entity instanceof ServerPlayer player)) return stack;

        FPSMCore core = FPSMCore.getInstance();
        Optional<BaseMap> optional = core.getMapByPlayer(player);

        if (optional.isEmpty()) return stack;
        BaseMap baseMap = optional.get();

        if (!(baseMap instanceof CSGameMap map)) return stack;

        if (!map.canPlantBomb(player) || !map.checkPlayerIsInBombArea(player)) {
            player.displayClientMessage(Component.translatable("blockoffensive.item.c4.use.fail"), true);
            return stack;
        }

        // 放置C4实体
        CompositionC4Entity c4 = new CompositionC4Entity(
                level, player.getX(), player.getY() + 0.25, player.getZ(), player, map);
        if (!level.addFreshEntity(c4)) {
            map.setBombEntity(null);
            return stack;
        }
        map.recordBombPlanted(player);

        // 播放放置音效
        level.playSound(null, player.getX(), player.getY(), player.getZ(),
                BOSoundRegister.PLANTED.get(), SoundSource.PLAYERS, 3.0F, 1.0F);

        // 经济奖励
        baseMap.getMapTeams().getTeamByPlayer(player)
                .flatMap(team -> team.getCapabilityMap().get(ShopCapability.class)
                        .flatMap(ShopCapability::getShopSafe))
                .ifPresent(shop -> {
                    shop.getPlayerShopData(player.getUUID()).addMoney(300);
                    shop.syncShopMoneyData(player.getUUID());
                });

        // 通知所有玩家
        Component message = Component.translatable("blockoffensive.item.c4.planted").withStyle(ChatFormatting.RED);
        baseMap.getMapTeams().getJoinedPlayers().forEach(data -> data.getPlayer().ifPresent(p -> p.displayClientMessage(message, false)));

        map.getMapTeams().getTeamByPlayer(player).ifPresent(team -> {
            NeoForge.EVENT_BUS.post(new CSGameMapEvent.PlayerEvent.PlacedC4Event(map, team, player, c4));
        });

        return ItemStack.EMPTY;
    }

    @Override
    public @NotNull UseAnim getUseAnimation(@NotNull ItemStack stack) {
        return UseAnim.CUSTOM;
    }

    @Override
    public int getUseDuration(@NotNull ItemStack stack, @NotNull LivingEntity entity) {
        return 80;
    }
}
