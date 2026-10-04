package net.ptcrys.blockoffensive.net;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;

/**
 * 客户端包处理器表。
 *
 * <p>NeoForge 1.21 删除了 {@code DistExecutor}，服务端侧不能再通过它「延迟到客户端才解析」，
 * 因此把「包类 → 客户端处理器」的映射集中到这张表：包类本体（common 侧）只做
 * {@link ClientPacketExecutor#execute}，真正的客户端类只在注册表里出现，
 * 而注册表由客户端初始化时（{@code BOClientBootstrap}）装载，服务端永远不会加载它。
 *
 * <p>与 fpsmatch 的 {@code net.ptcrys.fpsmatch.common.packet.ClientPacketRegistry} 同构，
 * 但独立一份，避免两个模组互相依赖。
 */
public final class ClientPacketRegistry {

    private static final Map<Class<?>, Consumer<Object>> HANDLERS = new ConcurrentHashMap<>();

    private ClientPacketRegistry() {}

    @SuppressWarnings("unchecked")
    public static <T> void register(Class<T> type, Consumer<T> handler) {
        HANDLERS.put(type, (Consumer<Object>) handler);
    }

    /** 把一个客户端包交给注册的处理器；未注册即为移植漏配，直接抛出。 */
    public static void handle(Object packet) {
        Consumer<Object> handler = HANDLERS.get(packet.getClass());
        if (handler == null) {
            throw new IllegalStateException(
                    "No client packet handler registered for " + packet.getClass().getName());
        }
        handler.accept(packet);
    }
}
