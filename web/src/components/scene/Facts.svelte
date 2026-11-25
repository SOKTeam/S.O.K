<script lang="ts">
  // A sheet of facts joined by a dotted line, as on the scene of the desktop
  // app: "Taille ........ 18,4 Go". A tone colors the value.
  export interface Fact {
    label: string;
    value: string;
    tone?: "caution" | "faint";
  }

  let { facts }: { facts: Fact[] } = $props();
</script>

<dl class="grid w-full gap-[9px]">
  {#each facts as fact, i (i)}
    <div class="flex items-baseline gap-2 text-[14px] text-muted">
      <dt class="shrink-0">{fact.label}</dt>
      <span class="flex-1 -translate-y-1 border-b border-dotted border-line-strong"></span>
      <dd
        class={[
          "shrink-0 font-mono text-[13px]",
          fact.tone === "caution"
            ? "text-caution"
            : fact.tone === "faint"
              ? "text-faint"
              : "text-ink",
        ]}
      >
        {fact.value}
      </dd>
    </div>
  {/each}
</dl>
