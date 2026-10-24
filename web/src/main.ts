import { mount } from "svelte";

import App from "./App.svelte";
import "./app.css";
import { startTheme } from "./lib/theme.svelte";

// The theme before the first page, so it never flashes white.
startTheme();
mount(App, { target: document.getElementById("app")! });
