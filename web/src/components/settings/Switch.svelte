<script lang="ts">
  // A switch of the settings, its name at the left: coral when it is on.
  let {
    label,
    checked,
    disabled = false,
    onchange,
  }: {
    label: string;
    checked: boolean;
    disabled?: boolean;
    onchange: (checked: boolean) => void;
  } = $props();
</script>

<button
  type="button"
  role="switch"
  aria-checked={checked}
  {disabled}
  class="flex min-h-[34px] w-full cursor-pointer items-center justify-between gap-4 text-left text-[14px] font-medium text-ink disabled:cursor-default"
  onclick={() => onchange(!checked)}
>
  {label}
  <span
    class={[
      "relative h-[19px] w-8 shrink-0 rounded-full transition-colors duration-150",
      checked ? "bg-accent" : "bg-line-strong",
    ]}
    aria-hidden="true"
  >
    <span
      class={[
        "absolute top-[3px] size-[13px] rounded-full transition-[left,background-color] duration-150",
        checked ? "left-4 bg-on-accent" : "left-[3px] bg-faint",
      ]}
    ></span>
  </span>
</button>
