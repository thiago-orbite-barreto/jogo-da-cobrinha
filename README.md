# Jogo da Cobrinha em Python

Um jogo da cobrinha simples para terminal, feito somente com a biblioteca
padrão do Python, com menu inicial, histórico de Records e opções de resolução.

## Como executar

No Windows, Linux ou macOS:

```text
python snake.py
```

No menu inicial, escolha **Iniciar jogo**, **Records** ou **Opções**. Antes de
cada partida o tabuleiro aparece congelado e aguarda qualquer tecla. Use
**W/A/S/D** ou as setas para mover e **Q** para sair. A cobra é `@` na cabeça,
`o` no corpo e a comida é `*`.

Todos os resultados são salvos em `highscore.json`, em ordem dos mais recentes,
e as preferências (resolução e tela cheia) em `settings.json`. A tela cheia é
um modo de ocupação da área disponível do terminal; o redimensionamento da
janela continua sendo responsabilidade do sistema operacional.

O menu **Gráficos simples** documenta as opções ASCII, Unicode e cores ANSI,
com seus prós e contras. A função `draw` mantém a renderização isolada para que
temas, sprites, animações ou uma biblioteca como tkinter/pygame possam ser
adicionados depois sem reescrever as regras.

## Organização para estudo

- `Keyboard`: abstrai a leitura de teclas para Windows e sistemas Unix.
- `draw`: concentra toda a renderização; pode ser substituída por uma interface
  com `tkinter`, `pygame` ou outra biblioteca sem alterar as regras do jogo.
- `play`: contém o laço principal, movimento, colisões e pontuação.
- `load_records` e `save_records`: cuidam do histórico de partidas.
- `load_settings` e `save_settings`: cuidam das preferências, incluindo o
  campo `theme`, reservado para a futura mudança de temas.
