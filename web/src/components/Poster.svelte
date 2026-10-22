<script lang="ts">
  import { posterUrl } from "../lib/rows";

  // The poster or cover of a result, or a gray box without one.
  let { poster, class: className = "h-12 w-8" }: { poster: string | null; class?: string } =
    $props();

  let failed = $state(false);
  const url = $derived(posterUrl(poster));
</script>

{#if url && !failed}
  <img
    src={url}
    alt=""
    loading="lazy"
    class={["shrink-0 rounded bg-hover object-cover", className]}
    onerror={() => (failed = true)}
  />
{:else}
  <div class={["shrink-0 rounded bg-hover", className]}></div>
{/if}
