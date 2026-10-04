package net.ptcrys.blockoffensive.net.spec;

import net.ptcrys.blockoffensive.spectator.BOSpecManager;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.server.level.ServerPlayer;
import net.ptcrys.fpsmatch.common.packet.register.PayloadContext;

import java.util.function.Supplier;

public class RequestAttachTeammateC2SPacket {

    public RequestAttachTeammateC2SPacket() {}

    public static void encode(RequestAttachTeammateC2SPacket pkt, FriendlyByteBuf buf) {}

    public static RequestAttachTeammateC2SPacket decode(FriendlyByteBuf buf) {
        return new RequestAttachTeammateC2SPacket();
    }

    public void handle(Supplier<PayloadContext> ctxSup) {
        PayloadContext ctx = ctxSup.get();
        ctx.enqueueWork(() -> {
            ServerPlayer sp = ctx.getSender();
            if (sp != null && sp.isSpectator()) {
                BOSpecManager.requestAttachTeammate(sp);
            }
        });
        ctx.setPacketHandled(true);
    }
}
