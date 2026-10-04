package net.ptcrys.blockoffensive.net.shop;

import net.minecraft.network.chat.ComponentSerialization;
import net.ptcrys.blockoffensive.client.shop.ShopDropClientState;
import net.ptcrys.blockoffensive.server.shop.ShopDropPickupService;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.ItemStack;
import net.neoforged.api.distmarker.Dist;
import net.ptcrys.blockoffensive.net.ClientPacketExecutor;
import net.ptcrys.fpsmatch.common.packet.register.PayloadContext;

import java.util.UUID;
import java.util.function.Supplier;

/** Authoritative result for a shop drop pickup request. */
public record ShopDropPickupResultS2CPacket(
                                            UUID requestId,
                                            UUID entityId,
                                            ShopDropPickupService.Result result,
                                            ShopDropPickupService.FailureReason reason,
                                            ItemStack authoritativeStack) {

    public ShopDropPickupResultS2CPacket {
        if (result == null) {
            result = ShopDropPickupService.Result.REJECTED;
        }
        if (reason == null) {
            reason = ShopDropPickupService.FailureReason.INVALID_REQUEST;
        }
        if (authoritativeStack == null) {
            authoritativeStack = ItemStack.EMPTY;
        }
    }

    public static void encode(ShopDropPickupResultS2CPacket packet, FriendlyByteBuf buffer) {
        buffer.writeUUID(packet.requestId());
        buffer.writeUUID(packet.entityId());
        buffer.writeEnum(packet.result());
        buffer.writeEnum(packet.reason());
        buffer.writeJsonWithCodec(ItemStack.CODEC, packet.authoritativeStack());
    }

    public static ShopDropPickupResultS2CPacket decode(FriendlyByteBuf buffer) {
        return new ShopDropPickupResultS2CPacket(
                buffer.readUUID(),
                buffer.readUUID(),
                buffer.readEnum(ShopDropPickupService.Result.class),
                buffer.readEnum(ShopDropPickupService.FailureReason.class),
                buffer.readJsonWithCodec(ItemStack.CODEC));
    }

    public void handle(Supplier<PayloadContext> contextSupplier) {
        ClientPacketExecutor.execute(contextSupplier, this);
    }

    /** User-facing text is deliberately derived from the server result code. */
    public Component message() {
        return Component.translatable("blockoffensive.shop.drop." + reason().name().toLowerCase(java.util.Locale.ROOT));
    }
}
