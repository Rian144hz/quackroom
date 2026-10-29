# Quackroom — Documento de Design

> Terror cooperativo com patos. **Faça barulho. Se tiver coragem.**
> Lema interno: *TEIUQ* — o contrário de ficar em silêncio.

Status: design aprovado em 2026-10-28 · em desenvolvimento · Godot 4.7.2

---

## 1. Visão

| | |
|---|---|
| **Gênero** | Terror cooperativo com comédia, furtivo, baseado em som |
| **Jogadores** | 1 a 4, online (solo funciona, mas o jogo é pensado para grupo) |
| **Câmera** | 3D em terceira pessoa |
| **Plataforma** | PC (Linux/Windows) — itch.io primeiro, Steam depois |
| **Engine** | Godot 4.7.2 + GDScript |
| **Duração da partida** | 10–15 minutos |

**Objetivo do projeto:** aprender a fazer jogos fazendo um jogo de verdade, e lançar.

### O diferencial

Em jogos de terror baseados em som, a regra costuma ser *fique quieto*. No Quackroom é o contrário:
**você só enxerga quando faz barulho.** O quack é um sonar — revela o caminho, chama os
patinhos e acorda o dono da casa. O grupo precisa decidir quem grasna e vira isca.

---

## 2. Premissa

Uma ninhada de patinhos se perdeu dentro de uma casa. Os patos adultos entram pela portinha de
cachorro para resgatá-los. A casa está no escuro total e, na escala de um pato, **cada cômodo é
gigante**: o sofá é um prédio, embaixo da cama é uma caverna.

O dono da casa é **sonâmbulo**: anda de olhos fechados guiado pelo som. Se acordar, acende a luz
— e aí já era.

---

## 3. Regras do jogo

### Regra de ouro

**Todo som revela e todo som acorda.** Quack, passo, panela caindo: tudo acende os contornos ao
redor e enche a barra de sono do dono.

### Controles

| Ação | Tecla | Efeito |
|---|---|---|
| Andar | WASD | Pato olha para onde a câmera aponta; A/D andam de lado |
| Câmera | Mouse | Gira em volta do pato |
| Correr | Shift | Mais rápido, mais barulho |
| Agachar | Ctrl | Quase silencioso, passa embaixo de móveis |
| Pular / planar | Espaço | Pulinho; segurando, plana devagar na descida |
| Quack curto | Clique rápido | Sonar pequeno, pouco barulho |
| Quack forte | Segurar o clique | Sonar grande, muito barulho |

### Sonar

- A onda sai do pato, se espalha e acende os contornos por ~3 s.
- **Todos por perto veem** — o quack de um amigo ilumina para você também.
- O piso muda o alcance: **azulejo** ecoa (vai longe), **carpete** abafa (vai curto).

### O que aparece no escuro

- **Você e seus amigos:** contorno bem fraquinho (cada um sabe onde está o grupo).
- **Casa, sonâmbulo e patinhos:** só aparecem quando uma onda de sonar passa.

### Patinhos

- 4 a 6 por partida, escondidos nos cômodos; de vez em quando dão um "piu" (mini sonar fraco).
- **Seguem o último quack que ouviram**, em fila atrás do pato que grasnou.
- Fila maior = mais barulho.

### O sonâmbulo

- Rotina entre quarto, cozinha e banheiro; ouviu um som → vai até lá.
- **Barra de sono compartilhada:** sobe com barulho perto dele, desce devagar no silêncio.
  Estágios: *profundo → inquieto* (mais rápido, resmunga) *→ quase acordado* (tateia) *→ ACORDOU*.
- Esbarrou num pato → prende numa **caixa de papelão**. Amigos soltam (3 s, faz barulho).

### Vitória e derrota

- **Vitória:** levar pelo menos metade dos patinhos ao ninho (portinha). Estrelas por patinhos
  salvos, tempo e quão perto o dono chegou de acordar.
- **Derrota:** o dono acorda (acende a luz) **ou** todos os patos presos.

### Cômodos e regras de som

| Cômodo | Piso | Particularidade |
|---|---|---|
| Sala | Carpete | Sofá alto, esconderijos |
| Cozinha | Azulejo | Panelas que caem se esbarrar |
| Banheiro | Azulejo | Eco forte |
| Quarto | Carpete | Onde o dono dorme / começa a rotina |

---

## 4. Arquitetura

### Rede: o host manda

Um jogador hospeda; o computador dele é a **autoridade** de tudo o que é compartilhado
(sonâmbulo, barra de sono, patinhos, objetos). Os outros enviam só **os próprios movimentos e
quacks**. Sem servidor pago.

- Desenvolvimento: ENet por IP (testar com várias cópias no mesmo PC).
- Lançamento: rede da Steam (GodotSteam), trocando só a camada de conexão.

### O coração: um único evento de som

Tudo que faz barulho chama `emitir_som(posicao, volume, origem)` no autoload `SomBus`:

1. **Onda visual do sonar** — na tela de todos.
2. **Audição do sonâmbulo + barra de sono** — só no host.
3. **Patinhos** (só quacks) — só no host.

O piso multiplica o volume antes disso.

### Visual do sonar

Um shader de pós-processamento deixa tudo preto e acende as bordas conforme as ondas passam
(até 16 ondas ao mesmo tempo). Precisa rodar bem em vídeo integrado.

### A casa

Cômodos são cenas prontas com encaixes de porta. **Na demo a planta é fixa.** Depois da demo: o
host sorteia uma *seed* e todos montam a mesma casa a partir dela.

### Personagens

| Quem | Como funciona |
|---|---|
| Pato (jogador) | `CharacterBody3D`, câmera em `SpringArm3D`, animações escolhidas pela velocidade |
| Sonâmbulo | Máquina de estados: Rotina → Investigar som → Agarrar → Acordar; `NavigationAgent3D` |
| Patinhos | Escondido → Seguindo → Salvo; cada um segue quem está à frente na fila |

### Escala do mundo

1 unidade = 1 metro. O pato tem ~0,5 m; a casa tem tamanho real (assento do sofá a 0,45 m) —
por isso tudo parece gigante.

---

## 5. Escopo da primeira demo

**Objetivo:** 2–4 amigos jogam juntos pelo IP uma partida completa, rodando liso num PC com vídeo
integrado (Ryzen 5 5625U, 8 GB).

**Entra:** pato em 3ª pessoa com animações · sonar · sonâmbulo completo · patinhos e
vitória/derrota · casa fixa de 4 cômodos · online por IP · menu hospedar/entrar · tela de fim.

**Fica para depois:** casa sorteada por seed · Steam · cosméticos/skins (o pato da demo usa a
fantasia de Halloween) · configurações · salvar progresso · trilha sonora completa.

### Ordem de construção

1. **Base** — projeto Godot, pastas, testes automáticos, pato importado.
2. **Pato + online básico** — pato em 3ª pessoa; depois dois patos se vendo pela rede.
3. **Sonar** — escuridão, shader, `SomBus`, quack curto/forte, pisos.
4. **Sonâmbulo** — rotina, audição, barra de sono, caixa, derrota.
5. **Patinhos** — esconder, seguir, ninho, vitória.
6. **Casa** — 4 cômodos modulares.
7. **Demo** — menus, polimento, build para o itch.io.

### Critérios de sucesso da demo

- Uma partida do início ao fim com 2 jogadores conectados por IP, sem dessincronizar.
- 60 fps no PC de referência.
- Testes automáticos da lógica passando (`jogo/testes/`).

---

## 6. Testes

- **Automáticos (headless):** lógica pura — escolha de animação, direção de movimento, queda do
  volume com a distância, barra de sono, quem os patinhos seguem.
  Rodar: `godot --headless --path jogo --script res://testes/rodar_testes.gd`
- **Manuais:** jogar cada etapa; online abrindo 2–4 cópias do jogo no mesmo PC.

---

## 7. Arte e marketing

- Pato: `arte/pato/` — modelo gerado por script no Blender (`gerar_pato.py`), esqueleto e
  animações (`animar_pato.py`), exportado para `jogo/personagens/pato/pato.glb`.
- Animações: parado, andar (4 direções), agachar, pular, grasnar.
- Vídeo de divulgação: `marketing/tiktok/` (vídeo, trilha e narração gerados por script).
