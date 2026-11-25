<script lang="ts">
  import { t } from "../../lib/i18n.svelte";

  // The rhythm of the automatic sorting, on a dial of an hour: a tick per
  // minute, the looks at the folders marked, the last one in coral, and in
  // the middle the minutes before the next one.
  let {
    enabled,
    minutes,
    lastCheck,
    now,
  }: {
    enabled: boolean;
    minutes: number;
    /** The last look at the folders, null before the first. */
    lastCheck: Date | null;
    now: Date;
  } = $props();

  const last = $derived(lastCheck ? lastCheck.getMinutes() : null);

  /** The minutes of the hour of the looks, before and after the last one. */
  const passes = $derived.by(() => {
    const marks = new Set<number>();
    if (last === null || minutes > 60) return marks;
    for (let at = last; at < last + 60; at += minutes) marks.add(at % 60);
    return marks;
  });

  const left = $derived.by(() => {
    if (!lastCheck) return null;
    const gone = (now.getTime() - lastCheck.getTime()) / 60_000;
    return Math.max(1, Math.ceil(minutes - gone));
  });
</script>

<div
  class="relative mt-1.5 size-[240px] shrink-0 self-center rounded-full shadow-[inset_0_0_0_1px_var(--color-line-strong)]"
  aria-hidden="true"
>
  {#each { length: 60 } as _, i (i)}
    {@const did = enabled && i === last}
    <i
      class={[
        "absolute top-1/2 left-1/2 -ml-px w-0.5 rounded-[1px]",
        did ? "-mt-2 h-4 bg-accent" : "-mt-[5px] h-2.5",
        !did && (enabled && passes.has(i) ? "bg-muted" : "bg-line-strong"),
      ]}
      style:transform={`rotate(${i * 6}deg) translateY(-112px)`}
    ></i>
  {/each}
  <div class="absolute inset-0 flex flex-col items-center justify-center px-10 text-center">
    {#if !enabled}
      <b class="text-[34px] leading-none font-[650] tracking-[-0.04em]"
        >{t("web_notify_off", "Off")}</b
      >
      <span class="mt-2 text-[13px] text-muted"
        >{t("web_sort_stopped", "nothing is sorted on its own")}</span
      >
    {:else if left === null}
      <b class="text-[46px] leading-none font-[650] tracking-[-0.04em]">{minutes} min</b>
      <span class="mt-1.5 text-[13px] text-muted">{t("web_sort_between", "between two looks")}</span
      >
    {:else}
      <b class="text-[46px] leading-none font-[650] tracking-[-0.04em]">{left} min</b>
      <span class="mt-1.5 text-[13px] text-muted">
        {t("web_sort_before_next", "before the next look")}
      </span>
    {/if}
  </div>
</div>
