package net.ptcrys.blockoffensive.net.bomb;

import net.ptcrys.blockoffensive.BlockOffensive;
import net.ptcrys.blockoffensive.client.key.DismantleBombKey;

import net.minecraft.network.FriendlyByteBuf;
import net.ptcrys.fpsmatch.common.packet.register.NetworkPacketRegister;
import net.ptcrys.fpsmatch.common.packet.register.PayloadContext;

import java.util.function.Supplier;

public record BombActionS2CPacket() {

    public static void encode(BombActionS2CPacket packet, FriendlyByteBuf buf) {}

    public static BombActionS2CPacket decode(FriendlyByteBuf buf) {
        return new BombActionS2CPacket();
    }

    public void handle(Supplier<PayloadContext> ctx) {
        ctx.get().enqueueWork(() -> {
            NetworkPacketRegister.sendToServer(new BombActionC2SPacket(DismantleBombKey.DISMANTLE_BOMB_KEY.isDown()));
        });
        ctx.get().setPacketHandled(true);
    }
}
