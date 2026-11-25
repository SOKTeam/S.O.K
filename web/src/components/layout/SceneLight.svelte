<script lang="ts">
  import { light } from "../../lib/light.svelte";

  // The light of the scene, painted by the window behind everything (as the
  // LightColumn of the desktop app): a halo of the color a screen sets.
  let { strength = 1 }: { strength?: number } = $props();
</script>

<div class="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
  <div
    class="absolute -top-[330px] -right-[280px] size-[1100px] rounded-full transition-[background] duration-500"
    style:background={light.color
      ? `radial-gradient(closest-side, rgba(${light.color}, calc(var(--halo) * ${strength})), transparent 72%)`
      : "none"}
  ></div>
</div>
