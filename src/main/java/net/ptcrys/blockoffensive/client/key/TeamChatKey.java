package net.ptcrys.blockoffensive.client.key;

import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.ptcrys.blockoffensive.client.screen.TeamChatScreen;

import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.client.settings.KeyConflictContext;
import net.neoforged.neoforge.client.settings.KeyModifier;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.Mod;

import com.mojang.blaze3d.platform.InputConstants;
import org.lwjgl.glfw.GLFW;

@OnlyIn(Dist.CLIENT)
@EventBusSubscriber(value = Dist.CLIENT)
public class TeamChatKey {

    public static final KeyMapping TEAM_CHAT_KEY = new KeyMapping("key.blockoffensive.team_chat.desc",
            KeyConflictContext.IN_GAME,
            KeyModifier.NONE,
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_U,
            "key.category.blockoffensive");

    @SubscribeEvent
    public static void onTeamChatPress(ClientTickEvent.Post event) {
                Minecraft minecraft = Minecraft.getInstance();
        if (TeamChatInputEdge.consumeAndShouldOpen(TEAM_CHAT_KEY::consumeClick, () -> minecraft.screen != null)) {
            minecraft.setScreen(new TeamChatScreen());
        }
    }
}
