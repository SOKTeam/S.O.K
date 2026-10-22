<script lang="ts">
  import type { Snippet } from "svelte";

  // A titled card of a page.
  let {
    title,
    text,
    id,
    children,
  }: { title: string; text?: string; id?: string; children: Snippet } = $props();
</script>

<section {id} class="scroll-mt-6">
  <h2 class="text-lg font-semibold">{title}</h2>
  {#if text}
    <p class="mt-1 text-sm text-muted">{text}</p>
  {/if}
  <div class="mt-3 rounded-xl border border-line bg-card">
    {@render children()}
  </div>
</section>
