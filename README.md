# Jogo da Cobrinha em Python

Um jogo da cobrinha simples para terminal, feito somente com a biblioteca
padrão do Python.

## Como executar

No Windows, Linux ou macOS:

```text
python snake.py
```

Use **W/A/S/D** ou as setas para mover e **Q** para sair. A cobra é `@` na
cabeça, `o` no corpo e a comida é `*`.

O melhor resultado é salvo em `highscore.json`. O nome só é solicitado quando
a pontuação da partida supera o recorde anterior.

## Organização para estudo

- `Keyboard`: abstrai a leitura de teclas para Windows e sistemas Unix.
- `draw`: concentra toda a renderização; pode ser substituída por uma interface
  com `tkinter`, `pygame` ou outra biblioteca sem alterar as regras do jogo.
- `play`: contém o laço principal, movimento, colisões e pontuação.
- `load_high_score` e `save_high_score`: cuidam da persistência do recorde.
