#!/usr/bin/env bash
set -e

clear

if [ -z "$1" ]; then
    echo ""
    echo "  Uso: ./jugar.sh [nombre_del_juego]"
    echo "  Ejemplo: ./jugar.sh snake"
    echo "  Ejemplo: ./jugar.sh tetris"
    echo ""
    exit 1
fi

JUEGO="$1"
ARCHIVO_BRICK="games/${JUEGO}.brick"
ARCHIVO_JSON="games/${JUEGO}.json"

if [ ! -f "$ARCHIVO_BRICK" ]; then
    echo "Error: No existe el archivo $ARCHIVO_BRICK"
    exit 1
fi

echo "Compilando el juego: ${JUEGO}..."
echo "----------------------------------"

if ! python3 compiler.py "$ARCHIVO_BRICK"; then
    echo ""
    echo "!!! Ocurrió un error durante la compilación. !!!"
    exit 1
fi

echo ""
echo "Compilación exitosa. Iniciando el juego..."
echo "----------------------------------"

python3 runtime.py "$ARCHIVO_JSON"

echo ""
echo "El juego ha finalizado."
