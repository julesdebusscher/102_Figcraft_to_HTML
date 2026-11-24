#!/bin/sh
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
  python3 -m figcraft_export launch 
else
  echo "Python 3 est introuvable."
fi
printf "Appuyez sur Entrée pour fermer..."; read _
