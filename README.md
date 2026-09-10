# Jogo da Cobrinha em Python

Um jogo da cobrinha com interface gráfica em uma janela Tkinter, usando somente
a biblioteca padrão do Python.

## Como executar

No Windows, Linux ou macOS:

```text
python snake.py
```

No menu inicial, escolha **Iniciar jogo**, **Records** ou **Opções**. Antes de
cada partida o tabuleiro aparece congelado e aguarda qualquer tecla. Use
**W/A/S/D** ou as setas para mover e **Q** para sair.

Todos os resultados são salvos em `highscore.json`, em ordem dos mais recentes,
e as preferências (resolução e tela cheia) em `settings.json`.

O menu **Gráficos simples** apresenta os prós e contras de ASCII, Unicode e
cores, além de orientar a evolução para sprites, animações e efeitos. O Canvas
mantém a renderização separada da lógica para permitir temas futuros.

## Organização para estudo

- `SnakeApp`: controla a janela, menus, renderização, movimento e pontuação.
- `load_records` e `save_records`: cuidam do histórico de partidas.
- `load_settings` e `save_settings`: cuidam das preferências, incluindo o
  campo `theme`, reservado para a futura mudança de temas.
