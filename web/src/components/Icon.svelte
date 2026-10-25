<script lang="ts">
  import { ICONS } from "../lib/icons";

  let { name, class: className = "size-5" }: { name: string; class?: string } = $props();

  const icon = $derived(ICONS[name]);
</script>

<svg viewBox={icon.viewBox} fill="none" class={className} aria-hidden="true">
  {@html icon.body}
</svg>
