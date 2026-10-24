<script lang="ts">
  import type { Snippet } from "svelte";

  // The card of the setup and login pages, centered on the page.
  let { title, text, children }: { title: string; text?: string; children: Snippet } = $props();
</script>

<main class="flex min-h-full items-center justify-center p-6">
  <div class="w-full max-w-sm rounded-2xl border border-line bg-card p-8 shadow-sm">
    <div class="mb-6 flex flex-col items-center gap-3 text-center">
      <img src="/favicon.svg" alt="" class="size-14" />
      <p class="text-xs font-semibold tracking-widest text-muted uppercase">S.O.K Server</p>
      <h1 class="text-2xl font-bold">{title}</h1>
      {#if text}
        <p class="text-sm text-muted">{text}</p>
      {/if}
    </div>
    {@render children()}
  </div>
</main>
