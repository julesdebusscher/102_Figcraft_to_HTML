import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from figcraft_export import summary, writer

ROOT = Path(__file__).resolve().parent.parent.parent
PLAYER = ROOT / "player"
NAME = 'Écran / 🚀 "test"'


def proto(title="Mon proto", screens=1, approximated=(), skipped=()):
    scr = {str(i): {"name": NAME if i == 1 else "S%d" % i, "width": 10, "height": 10, "background": "#fff",
                    "root": str(i), "overflow": "none"} for i in range(1, screens + 1)}
    return {"version": 1, "title": title, "start": "1", "panel": [{"section": None, "screens": list(scr)}],
            "pageName": "Page", "screens": scr, "nodes": {}, "variables": {"collections": {}, "vars": {}},
            "report": {"approximated": list(approximated), "skipped": list(skipped)}}


ASSETS = [{"path": "assets/1.svg", "data": b"<svg/>"}, {"path": "assets/2.png", "data": b"\x89PNG"}]


def parse_data_js(text):
    prefix = "window.FIGCRAFT_PROTOTYPE = "
    assert text.startswith(prefix) and text.endswith(";\n"), text[:80]
    return json.loads(text[len(prefix):-2])


class DataJsTests(unittest.TestCase):
    def test_data_js_escapes_script_close(self):
        p = proto(title="a</script><script>alert(1)</script>")
        js = writer.to_data_js(p)
        self.assertNotIn("</", js)
        self.assertEqual(parse_data_js(js)["title"], p["title"])

    def test_data_js_escapes_line_separators(self):
        p = proto(title="a\u2028b\u2029c")
        js = writer.to_data_js(p)
        self.assertNotIn("\u2028", js)
        self.assertEqual(parse_data_js(js)["title"], p["title"])

    def test_data_js_keeps_unicode_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = writer.write(Path(tmp), proto(), ASSETS, PLAYER)
            text = (folder / "data.js").read_text(encoding="utf-8")
            self.assertIn(NAME.replace('"', '\\"'), text)   # not \\u-escaped
            self.assertEqual(parse_data_js(text)["screens"]["1"]["name"], NAME)


class MaskTests(unittest.TestCase):
    def masked(self):
        p = proto()
        p["nodes"] = {
            "g": {"id": "g", "css": {"maskSrc": "assets/m.svg", "maskBox": [0, 0, 10, 10]}, "paint": None, "alts": []},
            "h": {"id": "h", "css": {"maskSrc": "assets/shared.png"}, "paint": None, "alts": []},
            "k": {"id": "k", "css": {}, "paint": None, "alts": [{"when": {}, "paint": {"src": "assets/shared.png"}}]},
        }
        assets = [{"path": "assets/m.svg", "data": b"<svg/>"}, {"path": "assets/shared.png", "data": b"\x89PNG"},
                  {"path": "assets/1.svg", "data": b"<svg/>"}]
        return p, assets

    def test_mask_sources_inlined_as_data_uris(self):
        p, assets = self.masked()
        kept = writer.inline_masks(p, assets)
        self.assertEqual(p["nodes"]["g"]["css"]["maskSrc"], "data:image/svg+xml;base64,PHN2Zy8+")
        self.assertEqual(p["nodes"]["h"]["css"]["maskSrc"], "data:image/png;base64,iVBORw==")
        # the mask-only file is no longer needed; a file a paint still uses is kept
        self.assertEqual([a["path"] for a in kept], ["assets/shared.png", "assets/1.svg"])
        self.assertEqual(writer.inline_masks(p, kept), kept)     # idempotent

    def test_written_export_has_no_mask_file_and_data_js_carries_it(self):
        p, assets = self.masked()
        with tempfile.TemporaryDirectory() as tmp:
            folder = writer.write(Path(tmp), p, assets, PLAYER)
            self.assertFalse((folder / "assets" / "m.svg").exists())
            self.assertTrue((folder / "assets" / "shared.png").exists())
            data = parse_data_js((folder / "data.js").read_text(encoding="utf-8"))
            self.assertTrue(data["nodes"]["g"]["css"]["maskSrc"].startswith("data:image/svg+xml;base64,"))


class PlayerJsTests(unittest.TestCase):
    def test_player_js_concatenates_src_in_order(self):
        js = writer.player_js(PLAYER)
        order = [l.strip() for l in (PLAYER / "src" / "ORDER").read_text(encoding="utf-8").splitlines() if l.strip()]
        pos = [js.index((PLAYER / "src" / f).read_text(encoding="utf-8")) for f in order]
        self.assertEqual(pos, sorted(pos))

    def test_prebuilt_player_js_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "player.js").write_text("// built\n", encoding="utf-8")
            self.assertEqual(writer.player_js(Path(tmp)), "// built\n")


class WriteTests(unittest.TestCase):
    def test_layout_has_index_player_css_data_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = writer.write(Path(tmp), proto(), ASSETS, PLAYER)
            self.assertEqual(folder, Path(tmp) / "mon-proto")
            self.assertEqual(sorted(p.name for p in folder.iterdir()),
                             ["assets", "data.js", "index.html", "player.css", "player.js"])
            self.assertEqual((folder / "assets" / "2.png").read_bytes(), b"\x89PNG")
            html = (folder / "index.html").read_text(encoding="utf-8")
            for tag in ('<script src="data.js"></script>', '<script src="player.js"></script>',
                        'href="player.css"', "<title>Mon proto</title>"):
                self.assertIn(tag, html)
            for bad in ('type="module"', "fetch(", "XMLHttpRequest"):
                self.assertNotIn(bad, html + (folder / "player.js").read_text(encoding="utf-8"))

    def test_title_is_html_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = writer.write(Path(tmp), proto(title='<b>&"x"'), ASSETS, PLAYER)
            html = (folder / "index.html").read_text(encoding="utf-8")
            self.assertIn("<title>&lt;b&gt;&amp;&quot;x&quot;</title>", html)

    def test_write_into_path_with_spaces_and_accents(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "Mes prototypes" / "Élodie"
            out.mkdir(parents=True)
            folder = writer.write(out, proto(title=NAME), ASSETS, PLAYER)
            self.assertEqual(folder.parent, out)
            self.assertTrue((folder / "index.html").is_file())
            self.assertEqual(parse_data_js((folder / "data.js").read_text(encoding="utf-8"))["title"], NAME)

    def test_refuses_non_empty_foreign_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            foreign = Path(tmp) / "mon-proto"
            foreign.mkdir()
            (foreign / "notes.txt").write_text("à garder", encoding="utf-8")
            with self.assertRaises(writer.WriteError) as cm:
                writer.write(Path(tmp), proto(), ASSETS, PLAYER)
            self.assertIn("mon-proto", str(cm.exception))
            self.assertEqual(sorted(p.name for p in foreign.iterdir()), ["notes.txt"])
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["mon-proto"])

    def test_empty_existing_folder_is_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "mon-proto").mkdir()
            folder = writer.write(Path(tmp), proto(), ASSETS, PLAYER)
            self.assertTrue((folder / "data.js").is_file())

    def test_replaces_previous_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = writer.write(Path(tmp), proto(), ASSETS + [{"path": "assets/old.svg", "data": b"x"}], PLAYER)
            second = writer.write(Path(tmp), proto(screens=2), ASSETS, PLAYER)
            self.assertEqual(first, second)
            self.assertFalse((second / "assets" / "old.svg").exists())
            self.assertEqual(len(parse_data_js((second / "data.js").read_text(encoding="utf-8"))["screens"]), 2)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["mon-proto"])

    def test_partial_folder_removed_on_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = ASSETS + [{"path": "assets/3.svg", "data": None}]
            with self.assertRaises(Exception):
                writer.write(Path(tmp), proto(), bad, PLAYER)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_failed_replace_keeps_previous_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = writer.write(Path(tmp), proto(), ASSETS, PLAYER)
            with mock.patch.object(writer, "_write_bytes", side_effect=OSError("disque plein")):
                with self.assertRaises(OSError):
                    writer.write(Path(tmp), proto(screens=2), ASSETS, PLAYER)
            self.assertEqual(len(parse_data_js((first / "data.js").read_text(encoding="utf-8"))["screens"]), 1)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["mon-proto"])

    def test_replace_is_atomic_and_old_comes_back_if_the_swap_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer.write(Path(tmp), proto(), ASSETS, PLAYER)
            real = writer._rename

            def flaky(src, dst):
                if Path(src).name.startswith(".mon-proto.export-"):
                    raise OSError("renommage refusé")
                return real(src, dst)

            with mock.patch.object(writer, "_rename", flaky):
                with self.assertRaises(OSError):
                    writer.write(Path(tmp), proto(screens=2), ASSETS, PLAYER)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["mon-proto"])
            self.assertEqual(len(parse_data_js((Path(tmp) / "mon-proto" / "data.js").read_text(encoding="utf-8"))["screens"]), 1)
            writer.write(Path(tmp), proto(screens=2), ASSETS, PLAYER)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["mon-proto"])   # no .old- left

    def test_failed_rename_back_says_where_the_previous_export_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer.write(Path(tmp), proto(), ASSETS, PLAYER)
            real = writer._rename

            def flaky(src, dst):
                if Path(src).name.startswith((".mon-proto.export-", ".mon-proto.old-")):
                    raise OSError("renommage refusé")
                return real(src, dst)

            with mock.patch.object(writer, "_rename", flaky):
                with self.assertRaises(writer.WriteError) as cm:
                    writer.write(Path(tmp), proto(screens=2), ASSETS, PLAYER)
            olds = [p for p in Path(tmp).iterdir() if p.name.startswith(".mon-proto.old-")]
            self.assertEqual(len(olds), 1)
            self.assertTrue((olds[0] / "data.js").is_file())
            self.assertIn(str(olds[0]), str(cm.exception))
            self.assertIn("prochain export", str(cm.exception))

    def test_leftovers_of_an_earlier_run_are_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in (".mon-proto.export-123", ".mon-proto.old-456"):
                (Path(tmp) / name).mkdir()
                (Path(tmp) / name / "data.js").write_text("x", encoding="utf-8")
            (Path(tmp) / ".autre.export-1").mkdir()
            writer.write(Path(tmp), proto(), ASSETS, PLAYER)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), [".autre.export-1", "mon-proto"])

    def test_folder_whose_data_js_is_not_ours_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / "mon-proto"
            other.mkdir()
            (other / "data.js").write_text("var config = {};\n", encoding="utf-8")
            with self.assertRaises(writer.WriteError):
                writer.write(Path(tmp), proto(), ASSETS, PLAYER)
            self.assertEqual((other / "data.js").read_text(encoding="utf-8"), "var config = {};\n")

    def test_asset_path_cannot_escape_the_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            out.mkdir()
            with self.assertRaises(writer.WriteError):
                writer.write(out, proto(), [{"path": "assets/../../evil.svg", "data": b"x"}], PLAYER)
            self.assertFalse((Path(tmp) / "evil.svg").exists())
            self.assertEqual(list(out.iterdir()), [])

    def test_slug_from_title_safe(self):
        self.assertEqual(writer.slug("Mon proto / v2"), "mon-proto-v2")
        self.assertEqual(writer.slug(""), "prototype")
        self.assertEqual(writer.slug("  ///  "), "prototype")
        self.assertEqual(writer.slug(NAME), "ecran-test")
        self.assertEqual(writer.slug("CON"), "con-prototype")      # Windows reserved name
        self.assertLessEqual(len(writer.slug("x" * 300)), 60)


class SummaryTests(unittest.TestCase):
    def test_summary_in_french_with_truncation(self):
        p = proto(screens=3, approximated=["approx %d" % i for i in range(7)], skipped=["skip 1"])
        text = summary.text(p, ASSETS, ["skip 1", "remarque"], True, Path("C:/Users/Élodie/Mes prototypes/mon-proto"))
        self.assertIn("3 écrans exportés (", text)
        self.assertIn("Mo) dans « C:", text)
        self.assertIn("Élodie", text)
        self.assertIn("approx 4", text)
        self.assertNotIn("approx 5", text)
        self.assertIn("… et 2 autres", text)
        self.assertIn("skip 1", text)
        self.assertIn("remarque", text)
        self.assertEqual(text.count("skip 1"), 1)
        self.assertNotIn("Attention", text)
        self.assertIn("Le document FigCraft est inchangé (vérifié).", text)
        self.assertIn("FigCraft peut afficher le document comme modifié : son contenu est inchangé (vérifié).", text)

    def test_summary_singular_and_digest_warning(self):
        text = summary.text(proto(), ASSETS, [], False, Path("x"))
        self.assertIn("1 écran exporté (", text)
        self.assertIn("Attention : le document FigCraft a peut-être été modifié", text)
        self.assertNotIn("inchangé", text)
        self.assertNotIn("peut afficher", text)
        self.assertEqual(summary.mo(1400000), "1,4 Mo")
        self.assertEqual(summary.mo(920000), "0,92 Mo")

    def test_summary_lists_largest_assets_over_10_mb(self):
        big = [{"path": "assets/%d.png" % i, "data": b"x" * (i * 1000000)} for i in range(1, 8)]
        text = summary.text(proto(), big, [], True, Path("x"))
        self.assertIn("Fichiers les plus lourds", text)
        self.assertIn("assets/7.png", text)
        self.assertIn("assets/3.png", text)
        self.assertNotIn("assets/2.png", text)
        self.assertNotIn("Fichiers les plus lourds", summary.text(proto(), ASSETS, [], True, Path("x")))

    def test_steps_left_tells_how_many_and_ctrl_z(self):
        text = summary.steps_left(3)
        self.assertIn("3 modifications temporaires", text)
        self.assertIn("Cmd/Ctrl+Z", text)
        self.assertIn("1 modification temporaire ", summary.steps_left(1))


if __name__ == "__main__":
    unittest.main()
