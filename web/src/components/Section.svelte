<script lang="ts">
  import type { Snippet } from "svelte";

  // A section of a page: its title in small capitals, a text, and its card.
  let {
    title,
    text,
    id,
    children,
  }: { title: string; text?: string; id?: string; children: Snippet } = $props();
</script>

<section {id} class="scroll-mt-6">
  <h2 class="label px-1">{title}</h2>
  {#if text}
    <p class="mt-1 px-1 text-sm text-muted">{text}</p>
  {/if}
  <div class="mt-2.5 overflow-hidden rounded-xl border border-line bg-card">
    {@render children()}
  </div>
</section>
