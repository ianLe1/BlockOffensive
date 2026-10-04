package net.ptcrys.blockoffensive.net.spec;

import net.ptcrys.blockoffensive.client.data.CSClientData;

import net.minecraft.network.FriendlyByteBuf;
import net.ptcrys.fpsmatch.common.packet.register.PayloadContext;

import java.util.function.Supplier;

public record BombFuseS2CPacket(int fuseTime, int totalFuseTime) {

    public static void encode(BombFuseS2CPacket packet, FriendlyByteBuf buf) {
        buf.writeInt(packet.fuseTime());
        buf.writeInt(packet.totalFuseTime());
    }

    public static BombFuseS2CPacket decode(FriendlyByteBuf buf) {
        int fuseTime = buf.readInt();
        int totalFuseTime = buf.readInt();
        return new BombFuseS2CPacket(fuseTime, totalFuseTime);
    }

    public void handle(Supplier<PayloadContext> ctx) {
        ctx.get().enqueueWork(() -> {
            CSClientData.bombFuse = fuseTime;
            CSClientData.bombTotalFuse = totalFuseTime;
        });
        ctx.get().setPacketHandled(true);
    }
}
