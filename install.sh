#!/bin/bash

echo "🚀 Iniciando a instalação do Assistente TIC..."

# 1. Detecta o gerenciador de pacotes e instala as dependências
if command -v apt &> /dev/null; then
    echo "📦 Sistema baseado em Debian/Ubuntu detectado."
    sudo apt update
    sudo apt install -y python3 zenity libnotify-bin
elif command -v pacman &> /dev/null; then
    echo "📦 Sistema baseado em Arch detectado."
    sudo pacman -Sy --noconfirm python zenity libnotify
elif command -v dnf &> /dev/null; then
    echo "📦 Sistema baseado em RedHat/Fedora detectado."
    sudo dnf install -y python3 zenity libnotify
else
    echo "⚠️ Gerenciador de pacotes não reconhecido. Por favor, instale 'zenity' e 'libnotify' manualmente."
fi

# 2. Prepara o ambiente do usuário
BASE_DIR="$HOME/.local/share/assistente-tic"
mkdir -p "$BASE_DIR"

# 3. Copia o script Python para a pasta do sistema
# (Assumindo que o install.sh e o assistente.py estão na mesma pasta)
cp assistente.py "$BASE_DIR/assistente.py"
chmod +x "$BASE_DIR/assistente.py"

# 4. Cria os atalhos no terminal (Aliases) para o usuário
BASHRC_FILE="$HOME/.bashrc"
ZSHRC_FILE="$HOME/.zshrc"

# Cria os comandos fáceis
ALIAS_MENU="alias demandas='python3 $BASE_DIR/assistente.py --menu'"
ALIAS_START="alias assistente-start='nohup python3 $BASE_DIR/assistente.py > /dev/null 2>&1 & echo \"Assistente iniciado em segundo plano!\"'"
ALIAS_STOP="alias assistente-stop='pkill -f assistente.py && echo \"Assistente parado!\"'"

# Função para injetar no arquivo
injetar_alias() {
    local arquivo=$1
    if [ -f "$arquivo" ]; then
        grep -q "alias demandas" "$arquivo" || echo "$ALIAS_MENU" >> "$arquivo"
        grep -q "alias assistente-start" "$arquivo" || echo "$ALIAS_START" >> "$arquivo"
        grep -q "alias assistente-stop" "$arquivo" || echo "$ALIAS_STOP" >> "$arquivo"
    fi
}

injetar_alias "$BASHRC_FILE"
injetar_alias "$ZSHRC_FILE"

echo "✅ Instalação concluída com sucesso!"
echo "👉 Para iniciar o assistente em segundo plano, digite: assistente-start"
echo "👉 Para abrir o menu a qualquer momento, digite: demandas"
echo "👉 Para parar o assistente a qualquer momento, digite: assistente-stop"
echo "⚠️  ATENÇÃO: Feche este terminal e abra um novo para os comandos funcionarem."