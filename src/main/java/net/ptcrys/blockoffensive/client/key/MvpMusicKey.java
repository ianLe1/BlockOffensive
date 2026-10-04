package net.ptcrys.blockoffensive.client.key;

import net.neoforged.fml.common.EventBusSubscriber;
import net.ptcrys.blockoffensive.client.screen.MvpMusicScreen;

import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.neoforge.client.event.InputEvent;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.Mod;

import org.lwjgl.glfw.GLFW;

/**
 * MVP 本地音乐设置键（默认 F9）：打开音乐设置页。
 */
@EventBusSubscriber(bus = EventBusSubscriber.Bus.GAME, value = Dist.CLIENT)
public class MvpMusicKey {

    public static final KeyMapping KEY_MVP_MUSIC = new KeyMapping(
            "key.blockoffensive.mvp_music.desc", GLFW.GLFW_KEY_F9, "key.category.blockoffensive");

    @SubscribeEvent
    public static void onKeyInput(InputEvent.Key event) {
        if (event.getAction() != GLFW.GLFW_PRESS) {
            return;
        }
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.screen != null) {
            return;
        }
        if (KEY_MVP_MUSIC.consumeClick()) {
            mc.setScreen(new MvpMusicScreen());
        }
    }
}
