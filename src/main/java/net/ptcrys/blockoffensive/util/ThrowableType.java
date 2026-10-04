package net.ptcrys.blockoffensive.util;

import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.network.chat.Style;
import net.minecraft.network.chat.TextColor;

public enum ThrowableType {

    FLASH_BANG(Component.translatable("blockoffensive.throwable.flash_bang.throw.message")
            .withStyle(Style.EMPTY.withColor(TextColor.parseColor("#5E89C4").result().orElseThrow()))),

    GRENADE(Component.translatable("blockoffensive.throwable.grenade.throw.message")
            .withStyle(Style.EMPTY.withColor(TextColor.parseColor("#CD584D").result().orElseThrow()))),

    INCENDIARY_GRENADE(Component.translatable("blockoffensive.throwable.incendiary_grenade.throw.message")
            .withStyle(Style.EMPTY.withColor(TextColor.parseColor("#B6B158").result().orElseThrow()))),

    SMOKE(Component.translatable("blockoffensive.throwable.smoke.throw.message")
            .withStyle(Style.EMPTY.withColor(TextColor.parseColor("#ABF99D").result().orElseThrow()))),

    DECOY(Component.translatable("blockoffensive.throwable.decoy.throw.message")
            .withStyle(Style.EMPTY.withColor(TextColor.parseColor("#FFD390").result().orElseThrow()))),

    UNKNOWN(Component.empty());

    private final MutableComponent chat;

    ThrowableType(MutableComponent chat) {
        this.chat = chat;
    }

    public MutableComponent getChat() {
        return chat;
    }
}
