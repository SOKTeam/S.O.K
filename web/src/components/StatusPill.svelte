<script lang="ts">
  import { t } from "../lib/i18n.svelte";
  import type { RowStatus } from "../lib/scan.svelte";

  let { status }: { status: RowStatus } = $props();

  function text(status: RowStatus): string {
    switch (status) {
      case "ok":
        return t("status_ready", "Ready");
      case "ambiguous":
        return t("status_ambiguous", "Pick one");
      case "missing":
        return t("status_missing", "Missing");
      case "pending":
        return t("web_status_pending", "Not searched");
    }
  }
</script>

<span
  class={[
    "w-24 shrink-0 rounded-full px-2 py-0.5 text-center text-xs font-semibold",
    status === "ok" && "bg-ok/15 text-ok",
    status === "ambiguous" && "bg-warn/15 text-warn",
    status === "missing" && "bg-error/15 text-error",
    status === "pending" && "bg-hover text-muted",
  ]}
>
  {text(status)}
</span>
