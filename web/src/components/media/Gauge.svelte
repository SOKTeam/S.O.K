<script lang="ts">
  // The confidence of a match in 5 notches, coral on a hairline track.
  let { notches }: { notches: number } = $props();
</script>

<span class="flex gap-[2.5px]" aria-hidden="true">
  {#each [0, 1, 2, 3, 4] as i (i)}
    <i class={["block h-3 w-[2.5px] rounded-[1px]", i < notches ? "bg-accent" : "bg-line-strong"]}
    ></i>
  {/each}
</span>
