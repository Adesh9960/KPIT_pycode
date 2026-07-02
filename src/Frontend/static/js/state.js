// Shared mutable UI/session state used across modules.
// Exposed as a single object (not individual `let` exports) because ES module
// import bindings are read-only in the importing module -- mutating a shared
// object's properties is the standard workaround.

export const state = {
    currentMode: "live",
    techUnlocked: false,
    progUnlocked: false,
    lastSpeed: 0,
};
