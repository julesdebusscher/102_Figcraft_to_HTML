// Pure view-fit rule (no DOM): how a frame is shown in the stage.
(function () {
  // Frames taller than 1.5x the stage (at fit-to-width scale) scroll; the rest are contained.
  FCP.viewFor = function (frameW, frameH, stageW, stageH) {
    var ws = Math.min(1, stageW / frameW);
    if (frameH * ws > 1.5 * stageH) return { scale: ws, tall: true };
    return { scale: Math.min(stageW / frameW, stageH / frameH), tall: false };
  };
})();
