<script lang="ts">
  import { posterUrl } from "../../lib/rows";

  // Covers fanned out, always centered: 150px wide, 60px apart (the
  // selection and the Analysis of the mockups). Music covers are square.
  let { posters, square = false }: { posters: string[]; square?: boolean } = $props();

  const shown = $derived(posters.slice(0, 4));
</script>

<div class="relative h-[240px] shrink-0" style:width="{150 + (shown.length - 1) * 60}px">
  {#each shown as poster, i (i)}
    <img
      src={posterUrl(poster)}
      alt=""
      class={[
        "absolute top-0 w-[150px] rounded-xl bg-raised object-cover shadow-[0_30px_60px_rgb(0_0_0/0.6),inset_0_1px_0_rgb(255_255_255/0.25)]",
        square ? "top-[75px] h-[150px]" : "h-[225px]",
      ]}
      style:left="{i * 60}px"
      style:z-index={10 - i}
    />
  {/each}
</div>
