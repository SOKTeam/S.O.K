<script lang="ts" generics="T extends string">
  // Words to choose one of, the chosen one in ink: "Lien dur  Copie
  // Déplacer". A radio group.
  let {
    label,
    options,
    value,
    onchoose,
  }: {
    label: string;
    options: { value: T; label: string }[];
    value: T;
    onchoose: (value: T) => void;
  } = $props();
</script>

<span
  class="flex flex-wrap justify-end gap-x-3.5 text-[13.5px]"
  role="radiogroup"
  aria-label={label}
>
  {#each options as option (option.value)}
    <button
      type="button"
      role="radio"
      aria-checked={option.value === value}
      class={[
        "cursor-pointer",
        option.value === value ? "font-medium text-ink" : "text-faint hover:text-muted",
      ]}
      onclick={() => option.value !== value && onchoose(option.value)}
    >
      {option.label}
    </button>
  {/each}
</span>
