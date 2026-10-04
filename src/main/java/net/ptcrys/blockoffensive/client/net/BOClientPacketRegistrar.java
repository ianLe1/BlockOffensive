package net.ptcrys.blockoffensive.client.net;

import net.ptcrys.blockoffensive.client.screen.hud.CSSpectatorRoster;
import net.ptcrys.blockoffensive.client.screen.hud.CSVoteHud;
import net.ptcrys.blockoffensive.client.shop.ShopDropClientState;
import net.ptcrys.blockoffensive.intro.client.IntroClientController;
import net.ptcrys.blockoffensive.intro.net.IntroSequenceS2CPacket;
import net.ptcrys.blockoffensive.net.CSScoreboardSync;
import net.ptcrys.blockoffensive.net.ClientPacketRegistry;
import net.ptcrys.blockoffensive.net.shop.ShopDropPickupResultS2CPacket;
import net.ptcrys.blockoffensive.net.shop.ShopNearbyDropsS2CPacket;
import net.ptcrys.blockoffensive.net.spec.SpectatorRosterS2CPacket;
import net.ptcrys.blockoffensive.net.vote.VoteSyncS2CPacket;

/**
 * BlockOffensive 的客户端包处理器清单。
 *
 * <p><b>只允许在客户端加载</b>：本类直接引用 {@code net.minecraft.client.*} 侧的实现类，
 * 由 {@code BOClientBootstrap#onClientSetup}（MOD 总线 + {@code value = Dist.CLIENT}）调用，
 * 服务端永远不会触碰它。这正是替代旧 {@code DistExecutor.unsafeRunWhenOn} 的要点。
 */
public final class BOClientPacketRegistrar {

    private static final BOClientPacketRegistrar INSTANCE = new BOClientPacketRegistrar();

    private BOClientPacketRegistrar() {}

    public static void register() {
        ClientPacketRegistry.register(SpectatorRosterS2CPacket.class,
                packet -> CSSpectatorRoster.getInstance().accept(packet));
        ClientPacketRegistry.register(VoteSyncS2CPacket.class,
                packet -> CSVoteHud.getInstance().accept(packet));
        ClientPacketRegistry.register(ShopNearbyDropsS2CPacket.class, ShopDropClientState::acceptNearby);
        ClientPacketRegistry.register(ShopDropPickupResultS2CPacket.class, ShopDropClientState::acceptResult);
        ClientPacketRegistry.register(IntroSequenceS2CPacket.class, IntroClientController::accept);
        ClientPacketRegistry.register(CSScoreboardSync.class, CSScoreboardSync::apply);
    }

    /** 供调试/自检引用的单例，确保 register() 的副作用可被显式触发。 */
    public static BOClientPacketRegistrar getInstance() {
        return INSTANCE;
    }
}
