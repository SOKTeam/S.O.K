<script lang="ts">
  import { fade } from "svelte/transition";

  import { light } from "../../lib/light.svelte";

  // The light of the scene, painted by the window behind everything (as the
  // LightColumn of the desktop app): a halo of the color a screen sets. A
  // new color fades in over the old one (a gradient cannot be animated).
  let { strength = 1 }: { strength?: number } = $props();

  const duration = matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 500;
</script>

<div class="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
  {#each light.color ? [light.color] : [] as color (color)}
    <div
      class="absolute -top-[330px] -right-[280px] size-[1100px] rounded-full"
      style:background={`radial-gradient(closest-side, rgba(${color}, calc(var(--halo) * ${strength})), transparent 72%)`}
      transition:fade={{ duration }}
    ></div>
  {/each}
</div>
