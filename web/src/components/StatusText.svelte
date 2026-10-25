<script lang="ts">
  import { t } from "../lib/i18n.svelte";
  import type { RowStatus } from "../lib/scan.svelte";

  // The status of a row, as text: in color only when it asks for something.
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
    "text-[13px] font-medium",
    status === "ambiguous" && "text-warn",
    status === "missing" && "text-error",
    status === "pending" && "text-muted",
  ]}
>
  {text(status)}
</span>
