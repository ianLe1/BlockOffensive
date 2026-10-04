package net.ptcrys.blockoffensive;

import net.neoforged.fml.ModContainer;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.ptcrys.blockoffensive.command.CSCommand;
import net.ptcrys.blockoffensive.compat.BOImpl;
import net.ptcrys.blockoffensive.entity.BOEntityRegister;
import net.ptcrys.blockoffensive.intro.IntroSoundEvents;
import net.ptcrys.blockoffensive.item.BOItemRegister;
import net.ptcrys.blockoffensive.map.team.capability.ColoredPlayerCapability;
import net.ptcrys.blockoffensive.net.*;
import net.ptcrys.blockoffensive.net.spec.*;
import net.ptcrys.blockoffensive.sound.BOSoundRegister;
import net.ptcrys.blockoffensive.util.BOUtil;
import net.ptcrys.blockoffensive.util.ThrowableType;
import net.ptcrys.fpsmatch.common.item.FPSMItemRegister;
import net.ptcrys.fpsmatch.common.packet.register.NetworkPacketRegister;
import net.ptcrys.fpsmatch.common.sound.FPSMSoundRegister;
import net.ptcrys.fpsmatch.compat.gun.GunTabTypeEnum;
import net.ptcrys.fpsmatch.compat.impl.FPSMImpl;

import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvents;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.config.ModConfig;
import net.neoforged.fml.event.lifecycle.FMLCommonSetupEvent;
import net.neoforged.fml.event.lifecycle.InterModEnqueueEvent;
import net.neoforged.fml.loading.FMLEnvironment;

@Mod(BlockOffensive.MODID)
public class BlockOffensive {

    public static final String MODID = "blockoffensive";
    private static final NetworkPacketRegister PACKET_REGISTER = new NetworkPacketRegister(
            ResourceLocation.tryBuild(MODID, "main"), BOPacketRegistration.PROTOCOL_VERSION);

    public BlockOffensive(IEventBus modEventBus, ModContainer modContainer) {
        modEventBus.addListener(this::commonSetup);
        modEventBus.addListener(this::onRegisterPackets);
        // InterModEnqueueEvent 是 MOD 生命周期事件，只会在 mod 事件总线上触发，
        // 必须通过 modEventBus.addListener 注册，而不是挂到游戏总线 NeoForge.EVENT_BUS。
        modEventBus.addListener(this::onEnqueue);
        NeoForge.EVENT_BUS.register(this);
        BOItemRegister.ITEMS.register(modEventBus);
        BOItemRegister.TABS.register(modEventBus);
        BOEntityRegister.ENTITY_TYPES.register(modEventBus);
        BOSoundRegister.SOUNDS.register(modEventBus);
        IntroSoundEvents.SOUND_EVENTS.register(modEventBus);
        modContainer.registerConfig(ModConfig.Type.CLIENT, BOConfig.clientSpec);
        modContainer.registerConfig(ModConfig.Type.COMMON, BOConfig.commonSpec);
    }

    @SubscribeEvent
    public void onRegisterCommands(RegisterCommandsEvent event) {
        CSCommand.onRegisterCommands(event);
    }

    /**
     * NeoForge 1.21：网络包注册迁移到 RegisterPayloadHandlersEvent（模组总线）。
     * 注册器由事件提供，必须在注册任何包之前 bind。
     */
    private void onRegisterPackets(final RegisterPayloadHandlersEvent event) {
        PACKET_REGISTER.bind(event.registrar(BOPacketRegistration.PROTOCOL_VERSION));
        BOPacketRegistration.register(PACKET_REGISTER);
    }

    private void commonSetup(final FMLCommonSetupEvent event) {
        event.enqueueWork(() -> {
            ColoredPlayerCapability.register();

            FPSMSoundRegister.registerGunPickupSound(GunTabTypeEnum.PISTOL, BOSoundRegister.WEAPON_PISTOL_PICKUP.get());
            FPSMSoundRegister.registerGunPickupSound(GunTabTypeEnum.RIFLE, BOSoundRegister.WEAPON_RIFLE_PICKUP.get());
            FPSMSoundRegister.registerGunPickupSound(GunTabTypeEnum.SHOTGUN, BOSoundRegister.WEAPON_SHOTGUN_PICKUP.get());
            FPSMSoundRegister.registerGunPickupSound(GunTabTypeEnum.SMG, BOSoundRegister.WEAPON_SMG_PICKUP.get());
            FPSMSoundRegister.registerGunPickupSound(GunTabTypeEnum.SNIPER, BOSoundRegister.WEAPON_SNIPER_PICKUP.get());
            FPSMSoundRegister.registerGunPickupSound(GunTabTypeEnum.MG, BOSoundRegister.WEAPON_PICKUP.get());
            FPSMSoundRegister.registerGunPickupSound(GunTabTypeEnum.RPG, BOSoundRegister.WEAPON_PICKUP.get());

            FPSMSoundRegister.registerGunDropSound(GunTabTypeEnum.PISTOL, BOSoundRegister.WEAPON_PISTOL_IMPACT.get());
            FPSMSoundRegister.registerGunDropSound(GunTabTypeEnum.SNIPER, BOSoundRegister.WEAPON_SNIPER_IMPACT.get());
            FPSMSoundRegister.registerGunDropSound(GunTabTypeEnum.RIFLE, BOSoundRegister.WEAPON_RIFLE_IMPACT.get());
            FPSMSoundRegister.registerGunDropSound(GunTabTypeEnum.SMG, BOSoundRegister.WEAPON_SMG_IMPACT.get());
            FPSMSoundRegister.registerGunDropSound(GunTabTypeEnum.SHOTGUN, BOSoundRegister.WEAPON_SHOTGUN_IMPACT.get());
            FPSMSoundRegister.registerGunDropSound(GunTabTypeEnum.MG, BOSoundRegister.WEAPON_HEAVY_IMPACT.get());
            FPSMSoundRegister.registerGunDropSound(GunTabTypeEnum.RPG, BOSoundRegister.WEAPON_HEAVY_IMPACT.get());

            FPSMSoundRegister.registerKnifeDropSound(BOSoundRegister.WEAPON_KNIFE_IMPACT.get());
            FPSMSoundRegister.registerItemPickupSound(BOItemRegister.C4.get(), SoundEvents.EXPERIENCE_ORB_PICKUP);
            FPSMSoundRegister.registerItemDropSound(BOItemRegister.C4.get(), BOSoundRegister.WEAPON_C4_IMPACT.get());

            BOUtil.registerThrowable(ThrowableType.SMOKE, FPSMItemRegister.SMOKE_SHELL.get());
            BOUtil.registerThrowable(ThrowableType.GRENADE, FPSMItemRegister.GRENADE.get());
            BOUtil.registerThrowable(ThrowableType.INCENDIARY_GRENADE, FPSMItemRegister.T_INCENDIARY_GRENADE.get());
            BOUtil.registerThrowable(ThrowableType.INCENDIARY_GRENADE, FPSMItemRegister.CT_INCENDIARY_GRENADE.get());
            BOUtil.registerThrowable(ThrowableType.FLASH_BANG, FPSMItemRegister.FLASH_BOMB.get());

            // 兼容层注册（各模组兼容层在此统一注册）
            registerCompat();
        });
    }

    /**
     * 统一注册所有模组兼容层。
     * 由 {@code commonSetup} 在 enqueueWork 中调用，确保在主线程执行。
     */
    private static void registerCompat() {
        // 1.21.1 移植：PhysicsMod / CS Grenade / HitIndication 兼容层已裁剪，
        // 依赖模组不在本整合包内（上游调用点原本就裹在 isXxxLoaded() 守卫里）。见 PORT-NOTES.md。
    }

    // 1.21.1: InterModEnqueueEvent 是 mod 总线事件（IModBusEvent）。本类在 :48 把 this
    // 注册到游戏总线（NeoForge.EVENT_BUS.register(this)），NeoForge 会逐方法校验总线归属，
    // 留着 @SubscribeEvent 会抛 "IModBusEvent events are not allowed on the common NeoForge bus"。
    // 它本来就由 :47 的 modEventBus.addListener(this::onEnqueue) 登记，删注解行为等价。
    public void onEnqueue(final InterModEnqueueEvent event) {
        event.enqueueWork(() -> {
            if (FMLEnvironment.dist != Dist.CLIENT) {
                return;
            }
            try {
                if (FPSMImpl.findClothConfig()) {
                    Class<?> integration = Class.forName(
                            "net.ptcrys.blockoffensive.compat.BOMenuIntegration");
                    integration.getMethod("registerModsPage").invoke(null);
                } else {
                    Class<?> clothScreenClass = Class.forName(
                            "com.tacz.guns.client.gui.compat.ClothConfigScreen");
                    clothScreenClass.getMethod("registerNoClothConfigPage").invoke(null);
                }
            } catch (ReflectiveOperationException | LinkageError ignored) {
                // Optional client configuration integration is unavailable.
            }
        });
    }
}
