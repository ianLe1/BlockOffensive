package net.ptcrys.blockoffensive.net;

import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.loading.FMLEnvironment;
import net.ptcrys.fpsmatch.common.packet.register.PayloadContext;

import java.util.function.Supplier;

/**
 * NeoForge 1.21 下 {@code DistExecutor} 的替代品（fpsmatch 移植版已验证的套路）。
 *
 * <p>旧写法 {@code DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> X.handle(packet))}
 * 的语义是「在客户端线程上执行，且服务端不解析 X」。新写法读 {@code FMLEnvironment.dist}
 * 这个普通静态字段（不触发客户端类加载），再把分派交给 {@link ClientPacketRegistry}。
 */
public final class ClientPacketExecutor {

    private ClientPacketExecutor() {}

    public static void execute(Supplier<PayloadContext> ctxSupplier, Object packet) {
        PayloadContext context = ctxSupplier.get();
        context.enqueueWork(() -> {
            if (FMLEnvironment.dist == Dist.CLIENT) {
                ClientPacketRegistry.handle(packet);
            }
        });
        context.setPacketHandled(true);
    }
}
