<script lang="ts">
  // The S.O.K cube, as drawn in the navigation of the desktop app: the logo's
  // paths with its coral front edge. Never redrawn or distorted.
  let { size = 22 }: { size?: number } = $props();
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 512 508"
  fill="none"
  stroke="currentColor"
  stroke-width="40"
  stroke-linejoin="round"
  stroke-linecap="round"
  aria-hidden="true"
>
  <path d="M124 121 256 62 442 146 256 229 70 146 70 360 256 446 442 360 442 146" />
  <path d="M256 284V446" stroke="#fb6048" />
</svg>
