<script lang="ts">
  // A switch on a row of a card, with an optional text under its label.
  let {
    label,
    text,
    checked,
    onchange,
  }: {
    label: string;
    text?: string;
    checked: boolean;
    onchange: (checked: boolean) => void;
  } = $props();
</script>

<label class="flex min-h-12 cursor-pointer items-center justify-between gap-4 px-4 py-2.5 text-sm">
  <span>
    <span class="font-medium">{label}</span>
    {#if text}
      <span class="mt-0.5 block text-[13px] text-muted">{text}</span>
    {/if}
  </span>
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    aria-label={label}
    onclick={() => onchange(!checked)}
    class={[
      "relative h-6 w-10 shrink-0 rounded-full transition-colors",
      checked ? "bg-accent" : "bg-track",
    ]}
  >
    <span
      class={[
        "absolute top-0.5 left-0.5 size-5 rounded-full shadow transition-transform",
        checked ? "translate-x-4 bg-accent-fg" : "bg-white",
      ]}
    ></span>
  </button>
</label>
