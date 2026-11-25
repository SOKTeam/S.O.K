<script lang="ts">
  import type { Snippet } from "svelte";

  import { t } from "../../lib/i18n.svelte";
  import { screen } from "../../lib/screen.svelte";

  // A screen of the art direction: what to sort on the left, the lit scene
  // on the right (36% of the width, between 320 and 520px), as the batch
  // pages of the desktop app. Under 1000px the list takes the width and the
  // scene slides over it when it is open (62% with a shadow, the whole
  // width on a phone), with "← List" and a swipe to the right to close it;
  // a sheet (the folder browser) rises from the bottom on a phone.
  let {
    children,
    scene,
    pane = $bindable(),
    onscroll,
    open = false,
    onclose,
    sheet = false,
  }: {
    children: Snippet;
    scene: Snippet;
    /** The list, which scrolls: the Settings follow the block read. */
    pane?: HTMLElement;
    onscroll?: () => void;
    /** Under 1000px, whether the scene is over the list. */
    open?: boolean;
    onclose?: () => void;
    /** On a phone, the scene is a sheet from the bottom. */
    sheet?: boolean;
  } = $props();

  const over = $derived(screen.narrow);
  const asSheet = $derived(sheet && screen.phone);

  // A swipe to the right closes the scene.
  let touch: { x: number; y: number } | null = null;
  function touchstart(event: TouchEvent) {
    touch = { x: event.touches[0].clientX, y: event.touches[0].clientY };
  }
  function touchend(event: TouchEvent) {
    if (!touch || asSheet) return;
    const dx = event.changedTouches[0].clientX - touch.x;
    const dy = Math.abs(event.changedTouches[0].clientY - touch.y);
    touch = null;
    if (dx > 70 && dy < 50) onclose?.();
  }

  $effect(() => {
    if (!over || !open) return;
    const leave = (event: KeyboardEvent) => event.key === "Escape" && onclose?.();
    window.addEventListener("keydown", leave);
    return () => window.removeEventListener("keydown", leave);
  });
</script>

<div class="flex h-full min-h-0">
  <section
    bind:this={pane}
    {onscroll}
    class="flex min-w-0 flex-1 flex-col overflow-y-auto pt-[26px] pr-7 pb-6 pl-9 max-[999px]:pr-8 max-[999px]:pl-8 max-[699px]:px-5 max-[699px]:pt-3 max-[699px]:pb-0"
  >
    {@render children()}
  </section>
  {#if over && open && (asSheet || !screen.phone)}
    <button
      type="button"
      class="fixed inset-0 z-30 cursor-default bg-black/35"
      aria-label={t("web_close", "Close")}
      tabindex="-1"
      onclick={onclose}
    ></button>
  {/if}
  <aside
    class={[
      "flex shrink-0 flex-col items-center overflow-y-auto",
      over
        ? [
            "fixed z-40 transition-transform duration-[260ms] ease-[cubic-bezier(.32,.72,0,1)]",
            asSheet
              ? "inset-x-0 bottom-0 h-[min(500px,86dvh)] rounded-t-[22px] bg-surface px-5 pt-2.5 pb-[max(20px,env(safe-area-inset-bottom))] shadow-[inset_0_1px_0_var(--color-hi),0_-1px_0_var(--color-line),0_-30px_60px_var(--drop)]"
              : "inset-y-0 right-0 bg-bg px-6 pt-0 pb-[max(30px,env(safe-area-inset-bottom))] shadow-[-1px_0_0_var(--color-line),-40px_0_80px_var(--drop)] max-[699px]:w-full min-[700px]:w-[62%] min-[700px]:px-10",
            open ? "translate-0" : asSheet ? "translate-y-full" : "translate-x-full",
            !open && "invisible",
          ]
        : "relative w-[clamp(320px,36%,520px)] border-l border-line px-12 pt-[50px] pb-[30px]",
    ]}
    aria-hidden={over && !open ? "true" : undefined}
    ontouchstart={touchstart}
    ontouchend={touchend}
  >
    {#if over && asSheet}
      <span class="mb-3.5 h-[5px] w-[38px] shrink-0 rounded-full bg-line-strong" aria-hidden="true"
      ></span>
    {:else if over}
      <div
        class="sticky top-0 z-10 -mx-6 mb-3 flex h-12 w-[calc(100%+3rem)] shrink-0 items-center bg-bg/85 px-6 backdrop-blur-sm min-[700px]:-mx-10 min-[700px]:w-[calc(100%+5rem)] min-[700px]:px-10"
      >
        <button
          type="button"
          class="cursor-pointer text-[15px] font-semibold text-muted hover:text-ink"
          onclick={onclose}
        >
          ← {t("web_list", "List")}
        </button>
      </div>
    {/if}
    {@render scene()}
  </aside>
</div>
