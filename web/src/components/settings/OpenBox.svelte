<script lang="ts">
  import type { Snippet } from "svelte";

  // What an open line sets, on a panel under it: a text, the fields, then
  // the keys (Enregistrer, Tester…).
  let { text = "", children }: { text?: string; children: Snippet } = $props();
</script>

<div
  class="mt-1 mb-2 rounded-xl bg-surface px-4 py-3.5 shadow-[inset_0_1px_0_var(--color-hi),0_0_0_1px_var(--color-line)]"
>
  {#if text}<p class="mb-2.5 text-[13px] leading-[1.5] text-faint">{text}</p>{/if}
  {@render children()}
</div>
