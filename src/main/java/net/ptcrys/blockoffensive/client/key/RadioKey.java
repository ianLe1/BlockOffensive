package net.ptcrys.blockoffensive.client.key;

import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.ptcrys.blockoffensive.client.screen.RadialMenuScreen;
import net.ptcrys.fpsmatch.compat.gun.GunCompatManager;

import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.client.event.InputEvent;
import net.neoforged.neoforge.client.settings.KeyConflictContext;
import net.neoforged.neoforge.client.settings.KeyModifier;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.Mod;

import com.mojang.blaze3d.platform.InputConstants;
import org.lwjgl.glfw.GLFW;

/**
 * Z 键标记轮盘：
 */
@OnlyIn(Dist.CLIENT)
@EventBusSubscriber(value = Dist.CLIENT)
public class RadioKey {

    public static final KeyMapping RADIO_TACTICAL_KEY = new KeyMapping("key.blockoffensive.radio_tactical.desc",
            KeyConflictContext.IN_GAME, KeyModifier.NONE, InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_Z,
            "key.category.blockoffensive");

    private static final long HOLD_THRESHOLD_NANOS = 180_000_000L;
    private static long pressStartedAtNanos;
    private static boolean pressPending;
    private static boolean radialMenuOpened;

    @SubscribeEvent
    public static void onKeyInput(InputEvent.Key event) {
        if (event.getAction() == GLFW.GLFW_PRESS) {
            if (!RADIO_TACTICAL_KEY.consumeClick()) {
                return;
            }
            Minecraft mc = Minecraft.getInstance();
            if (!GunCompatManager.isInGame() || mc.screen != null || mc.player == null) {
                return;
            }
            pressStartedAtNanos = System.nanoTime();
            pressPending = true;
            radialMenuOpened = false;
            return;
        }

        if (event.getAction() != GLFW.GLFW_RELEASE || !RADIO_TACTICAL_KEY.matches(event.getKey(), event.getScanCode()) || !pressPending) {
            return;
        }

        boolean wasRadialMenuOpened = radialMenuOpened;
        clearPressState();
        Minecraft mc = Minecraft.getInstance();
        if (!wasRadialMenuOpened && mc.screen == null && mc.player != null && GunCompatManager.isInGame()) {
            RadialMenuScreen.sendQuickPing();
        }
    }

    @SubscribeEvent
    public static void onClientTick(ClientTickEvent.Post event) {
        if (!pressPending || radialMenuOpened) {
            return;
        }

        Minecraft mc = Minecraft.getInstance();
        if (!RADIO_TACTICAL_KEY.isDown() || !GunCompatManager.isInGame() || mc.screen != null || mc.player == null) {
            clearPressState();
            return;
        }
        if (System.nanoTime() - pressStartedAtNanos >= HOLD_THRESHOLD_NANOS) {
            radialMenuOpened = true;
            mc.setScreen(new RadialMenuScreen());
        }
    }

    private static void clearPressState() {
        pressStartedAtNanos = 0L;
        pressPending = false;
        radialMenuOpened = false;
    }
}
