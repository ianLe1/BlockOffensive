package net.ptcrys.blockoffensive.entity;

import net.ptcrys.blockoffensive.BlockOffensive;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.minecraft.core.registries.BuiltInRegistries;
import net.neoforged.neoforge.registries.DeferredHolder;

public class BOEntityRegister {

    public static final DeferredRegister<EntityType<?>> ENTITY_TYPES = DeferredRegister.create(BuiltInRegistries.ENTITY_TYPE, BlockOffensive.MODID);
    public static final DeferredHolder<EntityType<?>, EntityType<CompositionC4Entity>> C4 = ENTITY_TYPES.register("c4", () -> EntityType.Builder.<CompositionC4Entity>of(CompositionC4Entity::new, MobCategory.MISC)
            .sized(0.25f, 0.25f).build("c4"));
}
