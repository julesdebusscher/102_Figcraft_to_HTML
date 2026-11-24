"""French end-of-export summary."""
from . import writer

SHOWN = 5
BIG = 10 * 1000 * 1000
DIGEST_OK = "Le document FigCraft est inchangé (vérifié)."
DIGEST_WARNING = ("Attention : le document FigCraft a peut-être été modifié pendant l'export. "
                  "Vérifiez-le avant de l'enregistrer (Cmd/Ctrl+Z annule les dernières modifications).")


def mo(n):
    """Bytes -> '1,4 Mo' (French decimal comma)."""
    v = n / 1000000.0
    return (("%.1f Mo" if v >= 1 else "%.2f Mo") % v).replace(".", ",")


def _plural(n, one, many):
    return one if n == 1 else many


def _block(title, items):
    if not items:
        return []
    lines = ["%s (%d) :" % (title, len(items))]
    lines += ["  - %s" % m for m in items[:SHOWN]]
    if len(items) > SHOWN:
        k = len(items) - SHOWN
        lines.append("  … et %d %s" % (k, _plural(k, "autre", "autres")))
    return lines


def steps_left(n):
    """When a user step blocked our undos: how many of ours remain and how to remove them."""
    return ("%d %s de l'export %s dans l'historique de FigCraft, sous votre propre modification : "
            "annulez votre modification puis %s avec Cmd/Ctrl+Z (%s « Export HTML (temporaire) »)."
            % (n, _plural(n, "modification temporaire", "modifications temporaires"),
               _plural(n, "reste", "restent"), _plural(n, "celle-ci", "celles-ci"),
               _plural(n, "étape", "étapes")))


def text(proto, assets, warnings, digest_ok, folder=None):
    sizes = [(len(a["data"]), a["path"]) for a in assets]
    total = sum(s for s, _ in sizes) + len(writer.to_data_js(proto).encode("utf-8"))
    n = len(proto.get("screens") or {})
    lines = ["%d %s (%s) dans « %s »." % (n, _plural(n, "écran exporté", "écrans exportés"), mo(total), folder)]
    if total > BIG:
        lines.append("Taille totale : %s. Fichiers les plus lourds :" % mo(total))
        lines += ["  - %s (%s)" % (p, mo(s)) for s, p in sorted(sizes, key=lambda x: (-x[0], x[1]))[:SHOWN]]
    report = proto.get("report") or {}
    approx, skipped = list(report.get("approximated") or []), list(report.get("skipped") or [])
    notes = [w for w in warnings or [] if w not in skipped and w not in approx]
    lines += _block("Rendu approximé", approx)
    lines += _block("Ignoré", skipped)
    lines += _block("Remarques", notes)
    lines.append(DIGEST_OK if digest_ok else DIGEST_WARNING)
    return "\n".join(lines)
