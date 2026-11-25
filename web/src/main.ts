import { mount } from "svelte";

import App from "./App.svelte";
import "./app.css";
import { startScreen } from "./lib/screen.svelte";
import { startTheme } from "./lib/theme.svelte";

// The theme before the first page, so it never flashes white.
startTheme();
startScreen();
mount(App, { target: document.getElementById("app")! });
