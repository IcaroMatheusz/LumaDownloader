<div align="center">
  <img src="assets/luma.png" width="96" alt="Luma Downloader">
  <h1>Luma Downloader</h1>
  <p>Uma biblioteca desktop para organizar downloads de vídeo, áudio e playlists.</p>
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

## Instalar uma versão publicada

1. Abra a página **Releases** deste repositório.
2. Baixe `Luma-Downloader-Setup-<versão>.exe`.
3. Execute o instalador e siga as etapas na tela.

O instalador é destinado ao Windows 64 bits. Builds sem assinatura digital podem ser bloqueados pelo Smart App Control ou exibir avisos do Windows. Publicar um arquivo no GitHub não o torna confiável para o Windows; distribuição ampla requer assinatura com certificado confiável. Consulte [Smart App Control: assinatura de código](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control).

Se a Release também oferecer uma versão portátil ZIP, extraia **todo o arquivo** para uma pasta e execute `Luma Downloader.exe` dentro dela. Não mova o executável para fora dessa pasta.

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

### Publicar uma Release no GitHub

1. Atualize a versão em `package.json` e `package-lock.json`.
2. Faça o commit dessas alterações na branch `main`.
3. Crie uma tag para o commit, por exemplo `v2.8.0`:

   ```powershell
   git push origin main
   git tag -a v2.8.0 -m "Luma Downloader 2.8.0"
   git push origin v2.8.0
   ```

4. Gere o instalador usando `npm run dist`.
5. No GitHub, abra **Releases** → **Draft a new release**, selecione a tag criada e anexe `electron-dist/Luma-Downloader-Setup-2.8.0.exe`.
6. Revise as notas e publique a Release.

As Releases e seus anexos são associados a uma tag do repositório. Veja a documentação oficial: [About releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases) e [Managing releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).

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
