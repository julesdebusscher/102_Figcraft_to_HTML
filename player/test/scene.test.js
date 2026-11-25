// Pure helpers of scene.js (the DOM parts are checked in a browser).
test("mask_css_uses_the_mask_box_in_px", function () {
  var m = FCP.maskCss({ maskSrc: "data:image/svg+xml;base64,PHN2Zy8+", maskBox: [9, 7, 106.5, 67] });
  assertEq(m.image, 'url("data:image/svg+xml;base64,PHN2Zy8+")');
  assertEq(m.position, "9px 7px");
  assertEq(m.size, "106.5px 67px");
});
test("mask_css_without_box_fills_the_layer_and_quotes_are_escaped", function () {
  var m = FCP.maskCss({ maskSrc: 'assets/a"b.svg' });
  assertEq(m.image, 'url("assets/a%22b.svg")');
  assertEq(m.position, "0px 0px");
  assertEq(m.size, "100% 100%");
  assertEq(FCP.maskCss({}), null);
});
test("live_text_colour_follows_its_bound_variable", function () {
  var lt = { var: "t", colorVar: "c", style: { color: "#000000" } };
  assertEq(FCP.liveTextColor({ vars: { c: "rgba(255, 0, 0, 1)" } }, lt), "rgba(255, 0, 0, 1)");
  assertEq(FCP.liveTextColor({ vars: {} }, lt), "#000000");                 // unknown value: fallback
  assertEq(FCP.liveTextColor({ vars: { c: "rgba(1, 2, 3, 1)" } }, { var: "t", style: { color: "#111111" } }), "#111111");
  assertEq(FCP.liveTextColor({ vars: {} }, { var: "t", style: {} }), "");
});
