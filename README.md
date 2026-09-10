# Jogo da Cobrinha em Python

Um jogo da cobrinha com interface gráfica em uma janela Pygame. O menu inicial
possui ambientação escura,
tipografia serifada, destaque dourado e navegação por teclado, inspirado na
composição de menus clássicos de RPG sem reproduzir logotipos ou artes de
terceiros.

## Como executar

No Windows, Linux ou macOS:

```text
pip install -r requirements.txt
python snake.py
```

No menu inicial, escolha **Iniciar jogo**, **Records** ou **Opções**. Antes de
cada partida o tabuleiro aparece congelado e aguarda qualquer tecla. Use
**W/A/S/D** ou as setas para mover e **Q** para sair.

A música `menu_theme.mp3` toca em loop enquanto o menu está aberto, e
`game_theme.mp3` acompanha as partidas. O efeito `menu_select.mp3` é
reproduzido ao navegar ou selecionar uma opção. Todos os áudios usam o mixer
do Pygame.

Todos os resultados são salvos em `highscore.json`, em ordem dos mais recentes,
e as preferências (resolução e tela cheia) em `settings.json`. A tela de
Records ordena as partidas da maior pontuação para a menor e preserva o nome
completo de cada jogador.

O menu **Gráficos simples** apresenta os prós e contras de ASCII, Unicode e
cores, além de orientar a evolução para sprites, fundos, animações e efeitos.
O Canvas mantém a renderização separada da lógica para permitir essas melhorias.

## Organização para estudo

- `SnakeApp`: controla a janela, menus, renderização, movimento e pontuação.
- `load_records` e `save_records`: cuidam do histórico de partidas.
- `load_settings` e `save_settings`: cuidam das preferências, incluindo o
  campo `theme`, reservado para a futura mudança de temas.
