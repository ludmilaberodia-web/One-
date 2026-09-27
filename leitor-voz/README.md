# Leitor de Voz

App (PWA) para **ouvir** PDFs, EPUBs e livros do Kindle com voz natural enquanto você corre, dirige ou cuida da casa. Roda no navegador do celular e pode ser instalado na tela inicial como um app.

## O que faz

- **Formatos:** PDF (com texto), EPUB, Kindle **sem DRM** (MOBI/AZW3/PRC), `My Clippings.txt` do Kindle (destaques), TXT, HTML, DOCX.
- **Vozes:**
  - **Aparelho** — grátis e offline (Web Speech API). Escolhe automaticamente a melhor voz instalada (Premium/Enhanced/Natural/Google).
  - **OpenAI** (`gpt-4o-mini-tts`, vozes *marin*, *cedar*, *coral*…) — narração neural com estilo configurável.
  - **ElevenLabs** (`eleven_multilingual_v2`) — a mais humana; usa o texto vizinho para manter a entonação entre trechos.
- **Uso em movimento:** controles na tela de bloqueio e nos botões do fone/volante (Media Session), **modo direção** com botões enormes, timer para dormir (15/30/45/60 min ou fim do capítulo), velocidade 0,6–2,5×, voltar/avançar 15 s.
- **Artigos científicos:** remove citações inline (`[12]`, `(Smith et al., 2021)`), URLs e DOIs; opção de **parar na seção “Referências”**; remove cabeçalhos/rodapés repetidos e números de página do PDF; junta hifenização de fim de linha.
- **Continuidade:** salva a posição de cada livro; toque em qualquer frase para ir até ela; sem internet, cai para a voz do aparelho em vez de ficar em silêncio.
- **Privacidade:** arquivos e chaves ficam só no aparelho (IndexedDB/localStorage). Com a voz do aparelho, nada sai do celular. Com voz na nuvem, só o trecho sendo lido vai ao provedor escolhido.
- **Android:** depois de instalado, aparece no menu **Compartilhar** — compartilhe um PDF do Drive/WhatsApp/Arquivos direto para o Leitor.

## Limitações importantes (leia antes de usar dirigindo/correndo)

1. **Tela bloqueada:** a voz do **aparelho** normalmente é interrompida pelo navegador quando a tela apaga (especialmente no iPhone). Para ouvir com o celular no bolso, use **OpenAI ou ElevenLabs** — elas tocam como áudio comum e continuam em segundo plano. Com a voz do aparelho, deixe “Manter tela ligada” ativo.
2. **Livros comprados na Amazon têm DRM** (AZW/KFX) e não podem ser lidos por nenhum app de terceiros legalmente. Alternativas: use o **Assistive Reader** do próprio app Kindle (Android/iOS) para ouvir livros Kindle; ou leia aqui versões sem DRM (EPUB/PDF de editoras, artigos, Open Access, livros que você mesmo enviou ao Kindle).
3. **PDF escaneado** (imagem) não tem texto — precisa de OCR antes.
4. **Custos das vozes neurais** (cobrados na sua conta do provedor; confira os preços atuais): OpenAI `gpt-4o-mini-tts` ≈ US$ 0,015/min de áudio — um artigo de 10 páginas (~25 min) sai por ~US$ 0,40; um livro de 10 h, ~US$ 9. ElevenLabs é mais cara (créditos por caractere, conforme o plano).

## Como publicar (uma vez)

O workflow `.github/workflows/leitor-voz-pages.yml` publica a pasta `leitor-voz/` no GitHub Pages.

1. No GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Rode o workflow (aba **Actions → Publicar Leitor de Voz → Run workflow**) ou faça um push.
3. Abra o endereço `https://<usuário>.github.io/<repositório>/` no celular:
   - **iPhone (Safari):** Compartilhar → *Adicionar à Tela de Início*.
   - **Android (Chrome):** menu ⋮ → *Instalar app*.

> GitHub Pages em repositório **privado** exige plano pago. Alternativas gratuitas: tornar o repositório público (o app não contém dados seus), ou arrastar a pasta `leitor-voz/` para Netlify Drop / Cloudflare Pages.

Para testar no computador: `cd leitor-voz && python3 -m http.server 8000` e abra `http://localhost:8000`.

## Configurar a voz mais natural

- **OpenAI:** crie uma chave em platform.openai.com → API keys, cole em **Ajustes → OpenAI**. Recomendado: voz **marin** ou **cedar**, modelo `gpt-4o-mini-tts`. O campo “Estilo de narração” aceita instruções livres (ex.: “ritmo mais rápido, tom de aula”).
- **ElevenLabs:** chave em elevenlabs.io → Profile → API Keys; escolha uma voz em português na Voice Library e cole o **Voice ID**.
- **Voz do aparelho no iPhone:** Ajustes → Acessibilidade → Conteúdo Falado → Vozes → Português (Brasil) → baixe **Luciana (Premium ou Aprimorada)**.
- **Voz do aparelho no Android:** Configurações → Acessibilidade → Saída de conversão de texto em voz → Serviços de voz do Google → instale a voz em português de alta qualidade.

## Estrutura

```
leitor-voz/
├── index.html            # telas: biblioteca, leitor, ajustes
├── css/styles.css        # tema claro/escuro, modo direção
├── js/app.js             # interface, Media Session, wake lock, timer
├── js/player.js          # fila de leitura, pré-carregamento, fallback offline
├── js/voices.js          # motores: aparelho, OpenAI, ElevenLabs
├── js/parsers.js         # PDF, EPUB, MOBI/AZW3, DOCX, TXT, destaques do Kindle
├── js/segment.js         # limpeza (citações/referências) e divisão em frases
├── js/db.js              # biblioteca local (IndexedDB)
├── sw.js                 # offline + recebimento via "Compartilhar"
└── vendor/               # pdf.js 4.10 (Apache-2.0), JSZip 3.10 (MIT)
```
