<script lang="ts">
  // The tabs of a page, underlined: the filters of a tab, the parts of the
  // settings and of the history.
  let {
    tabs,
    current,
    onselect,
  }: {
    tabs: { value: string; label: string; count?: number }[];
    current: string;
    onselect: (value: string) => void;
  } = $props();
</script>

<div class="flex flex-wrap gap-x-6 border-b border-line" role="tablist">
  {#each tabs as tab (tab.value)}
    <button
      type="button"
      role="tab"
      aria-selected={current === tab.value}
      class={[
        "-mb-px border-b-2 pb-2.5 text-sm",
        current === tab.value
          ? "border-accent font-semibold text-fg"
          : "border-transparent text-muted hover:text-fg",
      ]}
      onclick={() => onselect(tab.value)}
    >
      {tab.label}
      {#if tab.count !== undefined}
        <span class="ml-1 font-normal text-muted tabular-nums">{tab.count}</span>
      {/if}
    </button>
  {/each}
</div>
