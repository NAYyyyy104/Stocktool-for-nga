const { spawn } = require("child_process");
const path = require("path");

const electronBinary = require("electron");
const appRoot = path.resolve(__dirname, "..");

const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;

const devArg = process.argv.find((arg) => arg.startsWith("--dev-url="));
if (devArg) {
  env.CGP_WEB_URL = devArg.slice("--dev-url=".length);
}

const child = spawn(electronBinary, [appRoot], {
  stdio: "inherit",
  env
});

child.on("exit", (code) => {
  process.exit(code == null ? 0 : code);
});

child.on("error", (err) => {
  console.error("[cgp] failed to start electron:", err.message || err);
  process.exit(1);
});
