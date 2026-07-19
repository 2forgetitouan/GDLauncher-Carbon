// spawn cargo new command and catch the output
const path = require("path");
const fs = require("fs");
const { spawnSync } = require("child_process");

const iridium_path = path.join(__dirname, "crates", "iridium");
const lib_path = path.join(iridium_path, "src", "lib.rs");

const stub = "pub fn startup_check() {}\n";

let dir_ok = false;

try {
  const stat = fs.statSync(iridium_path);
  if (stat.isDirectory() && fs.readdirSync(iridium_path).length) {
    dir_ok = true;
  }
} catch {
  // ignore
}

if (!dir_ok) {
  const result = spawnSync("cargo", ["init", "--lib", "iridium"], {
    cwd: path.join(__dirname, "crates"),
  });

  if (result.status === 0) {
    console.log("Iridium generated.");
  } else {
    console.log("Uh oh. Cargo new failed. Not good.");
  }
}

// Always ensure the stub has the required exports
fs.writeFileSync(lib_path, stub);
console.log("Iridium stub written.");
