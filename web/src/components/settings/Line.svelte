<script lang="ts">
  import type { Snippet } from "svelte";

  // A line of the settings: its name, a dotted line, its value at the right,
  // as on the Settings of the desktop app. With onclick, the whole line is a
  // key that opens what it sets, under it (open).
  let {
    label,
    value = "",
    tone = "mono",
    open = false,
    onclick,
    children,
  }: {
    label: string;
    value?: string;
    /** mono: a path or a model; ui: a word; muted: a state; caution: to set. */
    tone?: "mono" | "ui" | "muted" | "caution";
    open?: boolean;
    onclick?: () => void;
    /** Instead of the value: words to choose, a field… */
    children?: Snippet;
  } = $props();

  const valueClass = $derived(
    {
      mono: "font-mono text-[13px] text-ink",
      ui: "text-[13.5px] text-ink",
      muted: "text-[13.5px] text-muted",
      caution: "text-[13.5px] text-caution",
    }[tone],
  );
</script>

{#snippet body()}
  <span class={["shrink-0", open ? "text-ink" : ""]}>{label}</span>
  <span class="min-w-5 flex-1 translate-y-[3px] border-b border-dotted border-line-strong"></span>
  {#if children}
    {@render children()}
  {:else}
    <span class={["min-w-0 truncate whitespace-nowrap", valueClass]} title={value}>{value}</span>
  {/if}
{/snippet}

{#if onclick}
  <button
    type="button"
    class="group flex min-h-[30px] w-full cursor-pointer items-center gap-2.5 text-left text-[14px] text-muted hover:[&>span:first-child]:text-ink"
    aria-expanded={open}
    {onclick}
  >
    {@render body()}
  </button>
{:else}
  <div class="flex min-h-[30px] items-center gap-2.5 text-[14px] text-muted">
    {@render body()}
  </div>
{/if}
