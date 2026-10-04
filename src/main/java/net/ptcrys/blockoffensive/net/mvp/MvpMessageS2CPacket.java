package net.ptcrys.blockoffensive.net.mvp;

import net.minecraft.network.chat.ComponentSerialization;
import net.minecraft.world.item.ItemStack;
import net.ptcrys.blockoffensive.client.screen.hud.CSGameHud;
import net.ptcrys.blockoffensive.data.MvpReason;

import net.minecraft.network.FriendlyByteBuf;
import net.ptcrys.fpsmatch.common.packet.register.PayloadContext;

import java.util.UUID;
import java.util.function.Supplier;

public class MvpMessageS2CPacket {

    private final MvpReason mvpReason;

    public MvpMessageS2CPacket(MvpReason mvpReason) {
        this.mvpReason = mvpReason;
    }

    public static void encode(MvpMessageS2CPacket packet, FriendlyByteBuf buf) {
        // A round can legitimately end without an MVP player; preserve the banner without inventing an identity.
        buf.writeBoolean(packet.mvpReason.uuid != null);
        if (packet.mvpReason.uuid != null) {
            buf.writeUUID(packet.mvpReason.uuid);
        }
        buf.writeBoolean(packet.mvpReason.isCtWinner());
        ComponentSerialization.TRUSTED_CONTEXT_FREE_STREAM_CODEC.encode(buf, packet.mvpReason.getTeamName());
        ComponentSerialization.TRUSTED_CONTEXT_FREE_STREAM_CODEC.encode(buf, packet.mvpReason.getPlayerName());
        ComponentSerialization.TRUSTED_CONTEXT_FREE_STREAM_CODEC.encode(buf, packet.mvpReason.getMvpReason());
        ComponentSerialization.TRUSTED_CONTEXT_FREE_STREAM_CODEC.encode(buf, packet.mvpReason.getExtraInfo1());
        ComponentSerialization.TRUSTED_CONTEXT_FREE_STREAM_CODEC.encode(buf, packet.mvpReason.getExtraInfo2());
    }

    public static MvpMessageS2CPacket decode(FriendlyByteBuf buf) {
        UUID uuid = buf.readBoolean() ? buf.readUUID() : null;
        return new MvpMessageS2CPacket(new MvpReason.Builder(uuid)
                .setCtWinner(buf.readBoolean())
                .setTeamName(ComponentSerialization.TRUSTED_CONTEXT_FREE_STREAM_CODEC.decode(buf).copy())
                .setPlayerName(ComponentSerialization.TRUSTED_CONTEXT_FREE_STREAM_CODEC.decode(buf).copy())
                .setMvpReason(ComponentSerialization.TRUSTED_CONTEXT_FREE_STREAM_CODEC.decode(buf).copy())
                .setExtraInfo1(ComponentSerialization.TRUSTED_CONTEXT_FREE_STREAM_CODEC.decode(buf).copy())
                .setExtraInfo2(ComponentSerialization.TRUSTED_CONTEXT_FREE_STREAM_CODEC.decode(buf).copy())
                .build());
    }

    public void handle(Supplier<PayloadContext> ctx) {
        ctx.get().enqueueWork(() -> {
            CSGameHud.getInstance().getMvpHud().triggerAnimation(this.mvpReason);
            // 本地 MVP 音乐：本机玩家是 MVP 时播放本地 mvp_music.ogg；其他玩家 MVP 时静默
            net.ptcrys.blockoffensive.client.mvp.MvpLocalMusicManager.onMvpEvent(this.mvpReason);
        });
        ctx.get().setPacketHandled(true);
    }
}
