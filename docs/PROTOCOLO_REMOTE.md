# Protocolo do remoto — BLE e RFCOMM

Contrato de fio entre o telemóvel e o PC. O lado do PC está escrito e testado; o
lado do Android é do Fortune.

Duas transports, **o mesmo corpo de mensagem**. O que muda entre eles é só o
framing (ver abaixo) — os comandos, os campos e a autenticação são os mesmos, e
o PC entrega ambos ao mesmo `_handle`.

---

## 1. Identidade

| | |
|---|---|
| UUID do serviço | `D9905F51-F497-49A4-88DF-784D82249EFD` |
| BLE — RX (telefone → PC) | `4C7F582E-BD6F-40ED-B181-AE537DD154ED` |
| BLE — TX (PC → telefone) | `64DB3D43-0354-4142-8EBE-EDE62429DD8A` |
| RFCOMM | mesmo UUID do serviço |

É o mesmo valor de UUID nos dois. Os namespaces do GATT e do SDP do RFCOMM não se
cruzam, e usar o mesmo dá ao telemóvel uma só identidade para "isto é um Maouse".

**Codificação de texto:** UTF-8. O JSON do Maouse sai com `ensure_ascii=False`, ou
seja com acentos críticos em vez de `\uXXXX` — ler como latin-1 mostra lixo.

---

## 2. Framing — a parte que difere

### BLE (Linux) — 2 bytes big-endian, por fragmento

```
[tam:2][até 18 bytes de corpo][tam:2][mais corpo]...
```

`tam` é o tamanho da **mensagem inteira**, em **2 bytes big-endian**, repetido à
frente de *cada* fragmento. Corpo máximo **18 bytes** (MTU 23 − 3 do link layer − 2
do cabeçalho). Teto de 64 KB por mensagem.

A mesma mensagem de 31 bytes, em BLE, sai em duas escritas:

```
00 1f  7b 22 63 6d 64 22 3a 22 63 6c 69 63 6b 22 2c 22 62 75     ← frag 1, 18 bytes
00 1f  74 74 6f 6e 22 3a 22 6c 65 66 74 22 7d                    ← frag 2, 13 bytes
└─ 0x1f = 31, o total, nos dois
```

Repetir o total em cada fragmento é redundante, mas é o que permite recuperar a
perda do *primeiro* fragmento. O telefone **não** negocia MTU; 18 é o pior caso.

### As duas, lado a lado

| | BLE | RFCOMM |
|---|---|---|
| Tamanho em | 2 bytes | 4 bytes |
| Ordem dos bytes | **big-endian** | **big-endian** |
| Repetido | em cada fragmento | **uma vez** por mensagem |
| Corpo por pedaço | 18 bytes | o que der (o SO reparte) |
| Teto por mensagem | 64 KB | 64 KB |
| Corpo | idêntico — JSON UTF-8, `move` binário opcional | idêntico |

O único dos quatro que muda entre transports, além do tamanho do campo: **no
RFCOMM o tamanho escreve-se uma vez e nunca mais.**

### RFCOMM (Windows) — 4 bytes big-endian, uma vez

```
[tam:4][a mensagem inteira]
```

`tam` é o tamanho da mensagem, em **4 bytes big-endian** (*network byte order*, o
mesmo `htonl`/`ntohl` do TCP). **Uma vez por mensagem**, não por pedaço. Teto de
64 KB por mensagem.

Exemplo real, para `{"cmd":"click","button":"left"}` (31 bytes):

```
00 00 00 1f  7b 22 63 6d 64 22 3a 22 63 6c 69 63 6b 22 2c 22 62 75 74 74 6f 6e 22 3a 22 6c 65 66 74 22 7d
└── tam ──┘  └────────────────── 31 bytes de corpo ───────────────────────────────────────────────────┘
```

Little-endian daria `1f 00 00 00` e o PC lê `0x1f000000` — 500 MB — e descarta a
ligação. Não é um comando perdido, é a sessão morta.

> **Atenção, Fortune.** O RFCOMM é um stream e o `split_frame` do BLE **não** pode
> ser reutilizado. Se escreveres `[tam:2]` antes de cada pedaço, o PC lê o
> cabeçalho da mensagem seguinte como se fosse corpo e os comandos corrompem-se —
> a falha aparece como "o rato não obedece". RFCOMM é só `[tam:4]` + mensagem, e
> o sistema operativo pode parti-la onde quiser; o PC sabe repor as fronteiras.

---

## 3. Corpo da mensagem

JSON UTF-8, sem espaços:

```json
{"cmd":"click","button":"left"}
```

### Excepção: `move` em binário

O caminho quente é binário, porque com MTU 23 o JSON são 32 bytes e seriam duas
escritas ATT por gesto — o que esgota a ligação antes de metade dos comandos:

```
[0x01][dx:int16 big-endian][dy:int16 big-endian]
```

São 5 bytes e uma escrita. `dx`/`dy` vão em **décimos de píxel** (`int16`), o que
preserva a parte fraccionária para o cursor não tremer.

Sobrevive em JSON quando os valores não cabem em `int16` — nesse caso o PC
reconverte. Podes mandar JSON sempre; mandar binário é a optimização.

---

## 4. Comandos

Todos vão em `{"cmd": ..., ...}`.

| `cmd` | Campos | O que faz |
|---|---|---|
| `move` | `dx`, `dy` (int) |move relativo, em píxeis de ecrã |
| `move_to` | `x`, `y` (float 0..1) | absoluto, normalizado ao ecrã |
| `click` | `button` (padrão `left`), `count` (1–4, padrão 1) | clique |
| `press` | `button` (padrão `left`) | botão para baixo |
| `release` | `button` (padrão `left`) | botão para cima |
| `scroll` | `dx`, `dy` (int) | ticks; `dy` vertical, `dx` horizontal |
| `key` | `key` (string) | uma tecla |
| `combo` | `mods` (lista), `key` (string) | combinação |
| `text` | `text` (string) | escreve letra a letra |
| `media` | `action` | ver lista abaixo |
| `gesture` | `event`, `x`, `y` | gesto da câmara |

`button`: `left`, `right`, `middle`.
`media.action`: `volume_up`, `volume_down`, `mute`, `play_pause`, `next`, `prev`, `stop`.

`move_to` recebe **0..1**, não píxeis. O PC multiplica pelas dimensões do ecrã e
tem em conta a origem do desktop virtual, para um monitor à esquerda não fazer o
toque cair no monitor principal.

Um `cmd` desconhecido dá `{"ok":false,"error":"cmd_desconhecido:..."}`.

---

## 5. Autenticação

**O primeiro frame tem de ser o `auth`.** Qualquer outro comando antes de
autenticar é recusado com `error: "auth_required"` e a sessão morre.

```json
{"cmd":"auth","code":"123456"}
```

`code` são 6 dígitos. `token` é o nome antigo e ainda é aceite — um build já
instalado no telemóvel manda o que manda, e obrigar a reinstalar a app para
experimentar seria azar.

Resposta boa:

```json
{"cmd":"auth","ok":true,"w":1920,"h":1080}
```

`w`/`h` são as dimensões do ecrã — de onde vem a referência para `move_to`.

Resposta má:

```json
{"cmd":"auth","ok":false,"error":"auth_required"}
```

E, se já houve tentativas a mais:

```json
{"cmd":"auth","ok":false,"error":"auth_locked","retry_after":42}
```

**O limite é partilhado entre os três transportes.** Cinco falhas em 60 s dão 300 s
de bloqueio, contadas **pelo endereço do telefone** e não pela ligação — fechar e
voltar a ligar não zera o contador. Se o RFCOMM ou o BLE tivessem contadores
próprios, um atacante passava a limpo só de mudar de tecnologia.

---

## 6. Respostas

| Situação | Corpo |
|---|---|
| comando ok | `{"ok":true,"note":"MOVE"}` |
| comando erro | `{"ok":false,"error":"..."}` |
| `ping` | `{"ok":true,"pong":true}` |
| `auth` ok | `{"cmd":"auth","ok":true,"w":…,"h":…}` |

`note` é só para o log do PC. O telefone não precisa de fazer nada com ele.

---

## 7. O que falta do lado do Android

1. Descoberta e ligação em cada transport.
2. `auth` antes de tudo o resto.
3. No RFCOMM, escrever `4 bytes de tamanho` **big-endian** + a mensagem, **sem**
   repetir o tamanho. No BLE, `2 bytes de tamanho` **big-endian** + até 18 bytes,
   repetidos em cada fragmento.
4. Cliente RFCOMM — o Android tem isso nativo.

## 8. Em aberto

- **Lease Pro no Bluetooth.** O WiFi exige uma lease; o BLE e o RFCOMM ainda não.
  Hoje um telemóvel Free autentica-se e controla o rato por Bluetooth. É receita,
  não bugs.
- **Cliques por testar em dispositivo real.** O transporte está provado por
  testes; o que nunca correu foi um telemóvel de verdade.
- **Não há loopback RFCOMM no Windows.** Tentar ligar o `StreamSocket` ao serviço
  anunciado pelo *próprio* adaptador rebenta o stack — `0xC0000005`, sem HRESULT,
  logo não é apanhável — por isso a travessia de um socket real só se prova com
  um telemóvel emparelhado. O caminho que funciona passa sempre por um
  `RfcommDeviceService` de um dispositivo *emparelhado*
  (`GetRfcommServicesForIdAsync` é quem filtra pelo UUID), seguido de
  `ConnectAsync(s.ConnectionHostName(), s.ServiceId().AsString())`. Ligar a um
  endereço + UUID avulso, sem passar pelo serviço emparelhado, não é caminho
  suportado.