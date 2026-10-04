package net.ptcrys.blockoffensive.client.key;

import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.ptcrys.blockoffensive.BlockOffensive;
import net.ptcrys.blockoffensive.client.screen.hud.CSVoteHud;
import net.ptcrys.blockoffensive.net.vote.VoteCastC2SPacket;

import net.minecraft.client.KeyMapping;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.client.settings.KeyConflictContext;
import net.neoforged.neoforge.client.settings.KeyModifier;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.Mod;

import com.mojang.blaze3d.platform.InputConstants;
import net.ptcrys.fpsmatch.common.packet.register.NetworkPacketRegister;
import org.lwjgl.glfw.GLFW;

/**
 * 投票按键：Y=同意 / N=反对。仅在有进行中的投票时生效，避免与其他操作冲突。
 * 与聊天命令 .a/.da 等价，二者可并存。
 */
@OnlyIn(Dist.CLIENT)
@EventBusSubscriber(value = Dist.CLIENT)
public class VoteKey {

    public static final KeyMapping VOTE_AGREE_KEY = new KeyMapping("key.blockoffensive.vote_agree.desc",
            KeyConflictContext.IN_GAME,
            KeyModifier.NONE,
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_Y,
            "key.category.blockoffensive");

    public static final KeyMapping VOTE_DISAGREE_KEY = new KeyMapping("key.blockoffensive.vote_disagree.desc",
            KeyConflictContext.IN_GAME,
            KeyModifier.NONE,
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_N,
            "key.category.blockoffensive");

    @SubscribeEvent
    public static void onVoteKeyPress(ClientTickEvent.Post event) {
                if (!CSVoteHud.getInstance().isActive()) {
            // 排空按键，避免投票结束后残留触发
            while (VOTE_AGREE_KEY.consumeClick()) { /* drain */ }
            while (VOTE_DISAGREE_KEY.consumeClick()) { /* drain */ }
            return;
        }
        if (VOTE_AGREE_KEY.consumeClick()) {
            NetworkPacketRegister.sendToServer(new VoteCastC2SPacket(true));
        }
        if (VOTE_DISAGREE_KEY.consumeClick()) {
            NetworkPacketRegister.sendToServer(new VoteCastC2SPacket(false));
        }
    }
}
