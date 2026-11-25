<script lang="ts">
  import { posterUrl } from "../../lib/rows";

  // The poster of a row, 36×54, with the round mark of the selection at its
  // top-left corner: shown on hover (or always in the selection mode), filled
  // coral when chosen, the poster then ringed in coral.
  let {
    poster,
    chosen = false,
    marks = false,
    selectable = true,
    square = false,
    tile = false,
    book = false,
    label,
    onmark,
  }: {
    poster: string | null;
    chosen?: boolean;
    /** The selection mode: every mark shows. */
    marks?: boolean;
    selectable?: boolean;
    square?: boolean;
    /** A cover of the music grid: as wide as its tile, the mark inside. */
    tile?: boolean;
    /** A book: the corners of a spine on the left, and its shade. */
    book?: boolean;
    label: string;
    onmark?: (event: MouseEvent) => void;
  } = $props();

  const url = $derived(posterUrl(poster));
</script>

<div
  class={[
    "group/thumb relative shrink-0",
    tile ? "aspect-square w-full" : square ? "size-11" : "h-[54px] w-9",
  ]}
>
  <div
    class={[
      "size-full bg-raised bg-cover bg-center",
      tile ? "rounded-[10px]" : book ? "relative rounded-[3px_6px_6px_3px]" : "rounded",
      chosen
        ? "shadow-[0_0_0_2px_var(--color-bg),0_0_0_4px_var(--color-accent)]"
        : tile
          ? "shadow-[0_14px_28px_rgb(0_0_0/0.35),inset_0_1px_0_rgb(255_255_255/0.2)]"
          : "shadow-[inset_0_0_0_1px_rgb(255_255_255/0.1)]",
    ]}
    style:background-image={url ? `url("${url}")` : undefined}
  >
    {#if book}
      <span
        class="absolute inset-y-0 left-0 w-[12%] rounded-l-[3px] bg-linear-to-r from-black/35 to-transparent"
      ></span>
    {/if}
  </div>
  {#if selectable}
    <button
      type="button"
      aria-label={label}
      aria-pressed={chosen}
      onclick={(event) => {
        event.stopPropagation();
        onmark?.(event);
      }}
      class={[
        "absolute size-[18px] cursor-pointer",
        tile ? "top-2 left-2" : "-top-1.5 -left-1.5",
        " rounded-full transition-[opacity,transform] duration-150",
        chosen
          ? "bg-accent opacity-100 shadow-[0_0_0_2px_var(--color-bg)]"
          : "bg-black/55 shadow-[inset_0_0_0_1.5px_rgb(255_255_255/0.85)]",
        chosen || marks
          ? "scale-100 opacity-100"
          : "scale-90 opacity-0 group-hover/thumb:scale-100 group-hover/thumb:opacity-100 focus-visible:opacity-100",
      ]}
    >
      {#if chosen}
        <span
          class="absolute top-[5.5px] left-[5px] h-1 w-[7px] -rotate-45 border-b-[1.8px] border-l-[1.8px] border-on-accent"
        ></span>
      {/if}
    </button>
  {/if}
</div>
