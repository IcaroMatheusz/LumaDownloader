<div align="center">
  <img src="assets/luma.png" width="96" alt="Luma Downloader">
  <h1>Luma Downloader</h1>
  <p>Uma biblioteca desktop para organizar downloads de vídeos, áudios e playlists.</p>
  <p><strong>Windows · Electron · yt-dlp</strong></p>
</div>

---

## Sobre

O Luma Downloader é um aplicativo desktop para Windows. A interface é feita com Electron, HTML e CSS; o mecanismo de extração usa `yt-dlp` em um processo Python separado.

Use o aplicativo somente para salvar conteúdo que você tem autorização para baixar. O Luma não remove DRM nem contorna autenticação, restrições de acesso ou controles impostos pelos sites.

## Recursos

- Interface adaptável com temas claro e escuro, animações e ícones Lucide.
- Fila automática ou manual, com pausa, retomada, cancelamento e remoção.
- Downloads de vídeo, áudio e playlists, incluindo seleção de faixas individuais.
- Miniaturas, qualidade, formato, progresso, velocidade, estimativa e tamanho.
- Histórico local de itens concluídos e com falha.
- Pastas distintas para vídeos e áudios, notificações e ação para revelar o arquivo no Explorador.
- Orientação para configurar o FFmpeg quando ele for necessário.

## Instalação

Baixe o instalador disponibilizado pelo projeto e execute o arquivo `.exe`. Siga as etapas exibidas pelo instalador.

O instalador é destinado ao Windows 64 bits. Builds sem assinatura digital podem ser bloqueados pelo Smart App Control ou exibir avisos do Windows. Para distribuição ampla, o instalador e os executáveis devem ser assinados com um certificado confiável. Consulte [Smart App Control: assinatura de código](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control).

Se houver uma versão portátil ZIP, extraia **todo o arquivo** para uma pasta e execute `Luma Downloader.exe` dentro dela. Não mova o executável para fora dessa pasta.

## Desenvolvimento no Windows

### Pré-requisitos

- Windows 10/11 de 64 bits.
- Node.js LTS e npm.
- Python 3.12 ou superior disponível pelo comando `py` ou `python`.
- PowerShell.

### Preparar e iniciar

No PowerShell, a partir da pasta do projeto:

```powershell
npm ci
npm run build:backend
npm start
```

Na primeira compilação, o script cria um ambiente Python local e instala as dependências listadas em `requirements.txt`. É necessário acesso à internet para instalar dependências.

### Gerar instalador e versão portátil

```powershell
npm run dist
```

O instalador NSIS `.exe` será criado em `electron-dist`. Para gerar os arquivos portáteis descompactados:

```powershell
npm run portable
```

A pasta `electron-dist/win-unpacked` contém o aplicativo e seus recursos. Para distribuir a versão portátil, compacte **todo o conteúdo** dessa pasta em um ZIP. Não distribua apenas o executável principal: o backend e os recursos Electron precisam permanecer ao lado dele.

## Estrutura

```text
electron/          Processo principal e ponte IPC segura
ui/                Interface Electron e ícones Lucide
assets/            Logo e ícone do aplicativo
backend_service.py Serviço Python que integra o yt-dlp
build-backend.ps1  Compilação do backend em executável Windows
```

## FFmpeg

O FFmpeg é necessário para converter áudio (por exemplo, MP3) e combinar alguns fluxos de vídeo. Obtenha informações e links para downloads na página oficial: [ffmpeg.org/download.html](https://ffmpeg.org/download.html). Depois, configure o local do `ffmpeg.exe` nas opções do Luma.

## Licença

Este repositório ainda não define uma licença para o código do Luma. Antes de torná-lo público, escolha e adicione uma licença se quiser conceder permissões de uso, cópia ou distribuição. As bibliotecas de terceiros mantêm suas próprias licenças.

Os ícones Lucide usados pela interface são distribuídos sob ISC; os avisos e textos de licença correspondentes estão em [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
