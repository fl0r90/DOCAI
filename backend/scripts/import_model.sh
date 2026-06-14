#!/bin/bash
# import_model.sh - Importa modele brute (.gguf) sau structura Ollama

IMPORT_NAME=$1
SOURCE_DIR="/app/ollama_models/import/$IMPORT_NAME"
TARGET_DIR="/app/ollama_models"

if [ -z "$IMPORT_NAME" ]; then
    echo "Eroare: Specificați numele folderului din import/"
    exit 1
fi

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Eroare: Folderul $SOURCE_DIR nu a fost găsit."
    exit 1
fi

echo "[*] Incepere import model: $IMPORT_NAME..."

# Căutăm fișiere .gguf în folder
GGUF_FILE=$(ls "$SOURCE_DIR" | grep ".gguf" | head -n 1)

if [ -n "$GGUF_FILE" ]; then
    echo "[+] Detectat fișier GGUF: $GGUF_FILE"
    echo "[*] Mutare fișier în stocarea principală..."
    mv "$SOURCE_DIR/$GGUF_FILE" "$TARGET_DIR/$GGUF_FILE"
    
    MODEL_NAME=$(echo "$IMPORT_NAME" | tr '[:upper:]' '[:lower:]')
    
    echo "[*] Inregistrare model în Ollama ($MODEL_NAME)..."
    # Rulăm comanda direct în containerul LLM pentru siguranță maximă
    docker exec v2-llm-1 sh -c "echo 'FROM /root/.ollama/$GGUF_FILE' > /root/.ollama/Modelfile_temp && ollama create $MODEL_NAME -f /root/.ollama/Modelfile_temp"
    
    echo "[OK] Modelul $MODEL_NAME a fost înregistrat în Ollama."
else
    # Logica pentru structura Ollama (blobs/manifests)
    if [ -d "$SOURCE_DIR/blobs" ] || [ -d "$SOURCE_DIR/manifests" ]; then
        echo "[+] Detectată structură Ollama. Se contopește..."
        cp -rv "$SOURCE_DIR"/* "$TARGET_DIR/"
        echo "[OK] Structura Ollama a fost importată."
    else
        echo "[!] Nu s-a detectat fișier GGUF sau structură Ollama."
        cp -rv "$SOURCE_DIR"/* "$TARGET_DIR/"
    fi
fi

# Curățăm folderul de import
rmdir "$SOURCE_DIR" 2>/dev/null || true
