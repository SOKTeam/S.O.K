<script lang="ts">
  import type { Snippet } from "svelte";

  // A screen of the art direction: what to sort on the left, the lit scene
  // on the right (36% of the width, between 320 and 520px), as the batch
  // pages of the desktop app.
  let {
    children,
    scene,
    pane = $bindable(),
    onscroll,
  }: {
    children: Snippet;
    scene: Snippet;
    /** The list, which scrolls: the Settings follow the block read. */
    pane?: HTMLElement;
    onscroll?: () => void;
  } = $props();
</script>

<div class="flex h-full min-h-0">
  <section
    bind:this={pane}
    {onscroll}
    class="flex min-w-0 flex-1 flex-col overflow-y-auto pt-[26px] pr-7 pb-6 pl-9"
  >
    {@render children()}
  </section>
  <aside
    class="relative flex w-[clamp(320px,36%,520px)] shrink-0 flex-col items-center overflow-y-auto border-l border-line px-12 pt-[50px] pb-[30px]"
  >
    {@render scene()}
  </aside>
</div>
