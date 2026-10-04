package net.ptcrys.blockoffensive.intro;

import net.ptcrys.blockoffensive.BlockOffensive;

import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvent;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.minecraft.core.registries.BuiltInRegistries;
import net.neoforged.neoforge.registries.DeferredHolder;

public final class IntroSoundEvents {

    public static final DeferredRegister<SoundEvent> SOUND_EVENTS = DeferredRegister.create(BuiltInRegistries.SOUND_EVENT, BlockOffensive.MODID);
    public static final DeferredHolder<SoundEvent, SoundEvent> INTRO_CT = register("intro.ct");
    public static final DeferredHolder<SoundEvent, SoundEvent> INTRO_T = register("intro.t");

    private IntroSoundEvents() {}

    public static SoundEvent forSide(IntroTeamSide side) {
        return (side == IntroTeamSide.T ? INTRO_T : INTRO_CT).get();
    }

    public static ResourceLocation idForSide(IntroTeamSide side) {
        return ResourceLocation.tryBuild(BlockOffensive.MODID, side == IntroTeamSide.T ? "intro.t" : "intro.ct");
    }

    private static DeferredHolder<SoundEvent, SoundEvent> register(String name) {
        return SOUND_EVENTS.register(name, () -> SoundEvent.createVariableRangeEvent(ResourceLocation.tryBuild(BlockOffensive.MODID, name)));
    }
}
