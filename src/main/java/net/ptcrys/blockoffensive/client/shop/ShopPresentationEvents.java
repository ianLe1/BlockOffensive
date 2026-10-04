package net.ptcrys.blockoffensive.client.shop;

import net.neoforged.fml.common.EventBusSubscriber;
import net.ptcrys.blockoffensive.client.screen.CSGameShopScreen;

import net.minecraft.client.Minecraft;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.neoforge.client.event.RenderGuiLayerEvent;
import net.neoforged.neoforge.client.event.RenderHandEvent;
import net.neoforged.neoforge.client.gui.VanillaGuiLayers;
import net.neoforged.bus.api.EventPriority;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.Mod;

@EventBusSubscriber(modid = "blockoffensive", value = Dist.CLIENT)
public final class ShopPresentationEvents {

    private ShopPresentationEvents() {}

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void hideFirstPersonHands(RenderHandEvent event) {
        if (Minecraft.getInstance().screen instanceof CSGameShopScreen) event.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void hideCrosshair(RenderGuiLayerEvent.Pre event) {
        if (Minecraft.getInstance().screen instanceof CSGameShopScreen && event.getName().equals(VanillaGuiLayers.CROSSHAIR)) event.setCanceled(true);
    }
}
