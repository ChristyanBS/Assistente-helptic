#!/usr/bin/env python3
import sys
import os
import json
import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Configuração de Caminhos
BASE_DIR = Path.home() / ".local/share/assistente-tic"
BASE_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = BASE_DIR / 'config.json'
TASKS_FILE = BASE_DIR / 'tarefas.json'
HISTORY_FILE = BASE_DIR / 'historico.json'
TIMERS_FILE = BASE_DIR / 'temporizadores.json'

def tocar_som():
    # Tenta tocar um som de notificação padrão do Linux de forma silenciosa e em segundo plano
    comandos_som = [
        ["paplay", "/usr/share/sounds/freedesktop/stereo/message-new-instant.oga"],
        ["canberra-gtk-play", "-i", "message"],
        ["aplay", "/usr/share/sounds/alsa/Front_Center.wav"]
    ]
    
    for cmd in comandos_som:
        try:
            # Popen roda em segundo plano sem travar o script
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            break # Se o primeiro funcionar, ele não tenta os outros
        except FileNotFoundError:
            continue

def carregar_json(caminho, default):
    if not caminho.exists():
        return default
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return json.loads(content) if content else default
    except:
        return default

def salvar_json(caminho, dados):
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def menu_principal():
    comando = [
        "zenity", "--list", 
        "--title", "Menu Principal - TIC",
        "--text", "O que você deseja fazer agora?",
        "--hide-header",
        "--width", "350", "--height", "260",
        "--column", "Opção",
        "Adicionar Nova Demanda",
        "Ver/Concluir Demandas",
        "⏱️ Gerenciar Temporizadores", # <--- Mudou aqui
        "Configurações de Tempo"
    ]
    escolha = subprocess.run(comando, capture_output=True, text=True).stdout.strip()
    
    if "Adicionar" in escolha:
        perguntar_nova_demanda()
    elif "Ver" in escolha:
        gerenciar_demandas()
    elif "Temporizadores" in escolha:
        menu_temporizadores() # <--- E mudou aqui
    elif "Configurações" in escolha:
        configurar_assistente()

def configurar_assistente():
    config = carregar_json(CONFIG_FILE, {"intervalo_perguntar_minutos": 120, "intervalo_lembrar_minutos": 60})
    
    # Texto explicativo mostrando a configuração atual
    texto_atual = (f"Valores Atuais:\n"
                   f"• Perguntar: a cada {config['intervalo_perguntar_minutos']} min\n"
                   f"• Lembrar: a cada {config['intervalo_lembrar_minutos']} min\n\n"
                   f"Digite os novos valores (apenas números):")
    
    form = subprocess.run([
        "zenity", "--forms", "--title", "Configurações do Assistente",
        "--text", texto_atual,
        "--add-entry", "Minutos entre Perguntas",
        "--add-entry", "Minutos entre Lembretes",
        "--separator", ","
    ], capture_output=True, text=True).stdout.strip()

    if form:
        try:
            perg, lemb = form.split(",")
            
            # Atualiza apenas se o usuário tiver digitado algo
            if perg.strip():
                config["intervalo_perguntar_minutos"] = int(perg)
            if lemb.strip():
                config["intervalo_lembrar_minutos"] = int(lemb)
                
            salvar_json(CONFIG_FILE, config)
            subprocess.run(["notify-send", "-i", "dialog-information", "Assistente TIC", "Configurações Atualizadas!"])
        except ValueError:
            # Caso você digite uma letra por engano
            subprocess.run(["zenity", "--error", "--text", "Erro: Por favor, digite apenas números inteiros."])

def menu_temporizadores():
    comando = [
        "zenity", "--list", "--title", "Gerenciar Temporizadores",
        "--text", "Escolha uma opção:", "--hide-header",
        "--width", "550", "--height", "260",
        "--column", "Opção",
        "⏳ Criar Temporizador Único (Ex: Foco 30m)",
        "🔁 Criar Temporizador Recorrente (Ex: Água 60m)",
        "❌ Cancelar um Temporizador Ativo"
    ]
    escolha = subprocess.run(comando, capture_output=True, text=True).stdout.strip()

    if "Único" in escolha:
        criar_temporizador(recorrente=False)
    elif "Recorrente" in escolha:
        criar_temporizador(recorrente=True)
    elif "Cancelar" in escolha:
        cancelar_temporizador()

def criar_temporizador(recorrente):
    tipo_texto = "Recorrente (repetirá sempre)" if recorrente else "Único (toca uma vez)"
    
    motivo = subprocess.run([
        "zenity", "--entry", "--title", f"Novo Temporizador {tipo_texto}",
        "--text", "Qual o motivo deste alarme?\n(ex: Beber Água, Revisar chamados)",
        "--width", "350"
    ], capture_output=True, text=True).stdout.strip()
    if not motivo: return

    tempo_str = subprocess.run([
        "zenity", "--entry", "--title", "Intervalo de Tempo",
        "--text", f"A cada quantos minutos eu aviso sobre '{motivo}'?" if recorrente else f"Quantos minutos para avisar sobre '{motivo}'?",
        "--width", "350"
    ], capture_output=True, text=True).stdout.strip()

    if not tempo_str or not tempo_str.isdigit():
        subprocess.run(["zenity", "--error", "--text", "Digite apenas números inteiros!"])
        return

    minutos = int(tempo_str)
    
    # Salva no arquivo para o assistente em background gerenciar
    timers = carregar_json(TIMERS_FILE, [])
    timers.append({
        "id": int(time.time()),
        "motivo": motivo,
        "minutos": minutos,
        "recorrente": recorrente,
        "proximo_alerta": (datetime.now() + timedelta(minutes=minutos)).isoformat()
    })
    salvar_json(TIMERS_FILE, timers)
    
    msg = f"Avisarei sobre '{motivo}' a cada {minutos} min!" if recorrente else f"Avisarei sobre '{motivo}' em {minutos} min!"
    subprocess.run(["notify-send", "-i", "timer", "Temporizador Criado", msg])

def cancelar_temporizador():
    timers = carregar_json(TIMERS_FILE, [])
    if not timers:
        subprocess.run(["zenity", "--info", "--text", "Não há nenhum temporizador ativo rodando no momento."])
        return

    lista_zenity = []
    for t in timers:
        tipo = "🔁 Recorrente" if t.get('recorrente') else "⏳ Único"
        lista_zenity.extend([str(t['id']), tipo, t['motivo'], f"{t['minutos']} min"])

    escolha = subprocess.run([
        "zenity", "--list", "--column", "ID", "--column", "Tipo", "--column", "Motivo", "--column", "Intervalo",
        "--title", "Cancelar Temporizador", "--text", "Selecione qual alarme você deseja parar:",
        "--width", "550", "--height", "300",
        *lista_zenity
    ], capture_output=True, text=True).stdout.strip()

    if escolha:
        timers_filtrados = [t for t in timers if str(t['id']) != escolha]
        salvar_json(TIMERS_FILE, timers_filtrados)
        subprocess.run(["notify-send", "-i", "dialog-information", "Assistente TIC", "Temporizador cancelado com sucesso!"])

def perguntar_nova_demanda():
    # 1. Categoria (Tela melhorada e traduzida)
    categoria = subprocess.run([
        "zenity", "--list", "--radiolist", 
        "--title", "Assistente TIC - Categoria",
        "--text", "Selecione em qual categoria essa demanda se encaixa:",
        "--hide-header", # Esconde aquelas palavras "Check" e "Tipo"
        "--width", "350", "--height", "220", # Define um tamanho fixo mais bonito
        "--column", "Check", "--column", "Tipo",
        "TRUE", "Trabalho (TIC/HELPDESK)", "FALSE", "Pessoal"
    ], capture_output=True, text=True).stdout.strip()
    
    if not categoria: return

    # 2. Descrição (Caixa única, limpa e com bom espaço)
    desc = subprocess.run([
        "zenity", "--entry", "--title", "Nova Demanda",
        "--text", f"Qual a nova demanda para {categoria}?",
        "--width", "400"
    ], capture_output=True, text=True).stdout.strip()

    if not desc: return # Sai se o usuário cancelar ou deixar vazio

    # 3. Pergunta se tem prazo (Botões Sim/Não)
    quer_prazo = subprocess.run([
        "zenity", "--question", "--title", "Prazo da Demanda",
        "--text", "Essa tarefa tem alguma data de entrega específica?",
        "--ok-label", "Sim, abrir calendário",
        "--cancel-label", "Não, sem prazo",
        "--width", "350"
    ])

    data = "Sem prazo"
    
    # returncode 0 significa que o usuário clicou em "Sim"
    if quer_prazo.returncode == 0:
        # 4. Abre o calendário nativo
        calendario = subprocess.run([
            "zenity", "--calendar", "--title", "Escolha a Data",
            "--text", "Selecione o prazo final:",
            "--date-format", "%d/%m/%Y"
        ], capture_output=True, text=True).stdout.strip()
        
        if calendario:
            data = calendario

    # 5. Salva a tarefa no JSON
    tarefas = carregar_json(TASKS_FILE, [])
    tarefas.append({
        "id": int(time.time()),
        "categoria": categoria,
        "descricao": desc,
        "prazo": data,
        "concluida": False,
        "data_criacao": datetime.now().isoformat()
    })
    salvar_json(TASKS_FILE, tarefas)
    subprocess.run(["notify-send", "-i", "dialog-information", "Assistente TIC", "Tarefa adicionada!"])

def gerenciar_demandas():
    tarefas = carregar_json(TASKS_FILE, [])
    if not tarefas:
        subprocess.run(["zenity", "--info", "--text", "Nenhuma tarefa pendente."])
        return

    lista_zenity = []
    for t in tarefas:
        # Garante compatibilidade com tarefas antigas que não tinham esses campos
        status = "✅" if t.get('concluida') else "⏳"
        cat = t.get('categoria', 'Geral')
        prazo = t.get('prazo', 'S/ Prazo')
        lista_zenity.extend([str(t.get('id', 0)), status, cat, t['descricao'], prazo])

    escolha = subprocess.run([
        "zenity", "--list", "--column", "ID", "--column", "Status", "--column", "Cat", "--column", "Tarefa", "--column", "Prazo",
        "--title", "Gerenciador de Demandas", "--width", "700", "--height", "400",
        "--text", "Selecione uma tarefa para concluir ou remover:",
        *lista_zenity
    ], capture_output=True, text=True).stdout.strip()

    if escolha:
        novas_tarefas = []
        historico = carregar_json(HISTORY_FILE, [])
        
        for t in tarefas:
            if str(t.get('id')) == escolha:
                t['concluida'] = True
                t['data_conclusao'] = datetime.now().isoformat()
                historico.append(t)
                subprocess.run(["notify-send", "Tarefa Concluída e Arquivada!"])
            else:
                novas_tarefas.append(t)
        
        salvar_json(TASKS_FILE, novas_tarefas)
        salvar_json(HISTORY_FILE, historico)

def alerta_intrusivo():
    tarefas = carregar_json(TASKS_FILE, [])
    pendentes = [t for t in tarefas if not t.get('concluida')]
    
    # Mensagens Padrão de Aviso do Setor de TIC
    avisos_padrao = (
        "⚠️ <b>IMPORTANTE: FIQUE DE OLHO NO DISCORD, EMAIL E STI.</b>\n"
        "💬 <b>ATENÇÃO:</b> Verifique sempre as comunicações no Discord.\n"
        "──────────────────────────────────────\n\n"
    )
    
    if pendentes:
        tocar_som() # <--- CHAMA O SOM AQUI
        texto = avisos_padrao + "<b>SUAS PENDÊNCIAS:</b>\n\n"
        for t in pendentes:
            prazo = t.get('prazo', 'Sem prazo')
            
            # Formatação inteligente: Se não tem prazo, não polui a tela mostrando "(Prazo: Sem prazo)"
            if prazo == "Sem prazo":
                texto += f"🔴 <b>[{t.get('categoria')}]</b>: {t['descricao']}\n"
            else:
                texto += f"🔴 <b>[{t.get('categoria')}]</b>: {t['descricao']}  <i>(Prazo: {prazo})</i>\n"
        
        # Alerta que exige interação
        subprocess.run([
            "zenity", "--warning", "--title", "CENTRAL DE PENDÊNCIAS TIC/HELPDESK",
            "--text", texto,
            "--width", "550" # Aumentei a largura para os textos padrão caberem bem
        ])

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--menu":
        menu_principal()
        return 

    ultima_pergunta = datetime.now() - timedelta(days=1)
    ultimo_lembrete = datetime.now() - timedelta(days=1)

    print("🚀 Assistente TIC 2.0 em segundo plano...")

    while True:
        config = carregar_json(CONFIG_FILE, {"intervalo_perguntar_minutos": 120, "intervalo_lembrar_minutos": 60})
        agora = datetime.now()

        if agora - ultima_pergunta >= timedelta(minutes=config["intervalo_perguntar_minutos"]):
            tocar_som() 
            tem_demanda = subprocess.run([
                "zenity", "--question", "--title", "Assistente TIC",
                "--text", "Surgiu alguma nova demanda para registrar agora?",
                "--ok-label", "Sim, registrar", "--cancel-label", "Não, tudo tranquilo",
                "--width", "350"
            ])
            if tem_demanda.returncode == 0:
                perguntar_nova_demanda()
            ultima_pergunta = datetime.now()

        if agora - ultimo_lembrete >= timedelta(minutes=config["intervalo_lembrar_minutos"]):
            alerta_intrusivo()
            ultimo_lembrete = datetime.now()

        # ==========================================
        # NOVO: MOTOR DE TEMPORIZADORES (ÚNICOS E RECORRENTES)
        # ==========================================
        timers = carregar_json(TIMERS_FILE, [])
        timers_ativos = []
        timers_modificados = False

        for t in timers:
            proximo = datetime.fromisoformat(t['proximo_alerta'])
            
            # Se a hora de agora passou a hora do alarme
            if agora >= proximo:
                tocar_som()
                # Mostra o pop-up solto na tela (sem travar o script)
                subprocess.Popen([
                    "zenity", "--warning", "--title", "⏰ TEMPO ESGOTADO",
                    "--text", f"<b>{t['motivo']}</b>\n\nTempo finalizado!", "--width", "400"
                ])
                
                # Se for recorrente, adiciona os minutos de novo para o próximo ciclo
                if t.get('recorrente'):
                    t['proximo_alerta'] = (agora + timedelta(minutes=t['minutos'])).isoformat()
                    timers_ativos.append(t)
                    timers_modificados = True
                else:
                    # Se for único, ele morre aqui e não entra na lista de ativos
                    timers_modificados = True
            else:
                timers_ativos.append(t)

        if timers_modificados:
            salvar_json(TIMERS_FILE, timers_ativos)
        # ==========================================

        time.sleep(30)

if __name__ == "__main__":
    main()