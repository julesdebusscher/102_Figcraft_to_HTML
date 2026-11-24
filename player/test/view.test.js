test("viewFor: phone in a wide stage is contained", function () {
  var v = FCP.viewFor(390, 844, 590, 705);
  assertTrue(!v.tall, "not tall");
  assertClose(v.scale, 705 / 844, 1e-9);
});
test("viewFor: tall design-system page fits width and scrolls", function () {
  var v = FCP.viewFor(1440, 3000, 590, 705);
  assertTrue(v.tall, "tall");
  assertClose(v.scale, 590 / 1440, 1e-9);
  assertClose(v.scale, 0.4097, 1e-4);
});
test("viewFor: 1440x900 is contained", function () {
  var v = FCP.viewFor(1440, 900, 590, 705);
  assertTrue(!v.tall, "not tall");
  assertClose(v.scale, 590 / 1440, 1e-9);
});
