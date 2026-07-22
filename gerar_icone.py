# -*- coding: utf-8 -*-
"""
Gera um icone .ico profissional (varios tamanhos) a partir do logo PNG.

Por que varios tamanhos: o Windows usa medidas diferentes conforme o lugar —
16x16 na barra de titulo, 32x32 na barra de tarefas, 48x48 e 256x256 no
Explorer e em telas de alta resolucao. Um .ico com apenas um tamanho obriga
o Windows a redimensionar, e o resultado costuma ficar borrado.

USO:
    python gerar_icone.py                      (usa T2M_logo-03.png da pasta atual)
    python gerar_icone.py meu_logo.png         (usa outro arquivo)
    python gerar_icone.py entrada.png saida.ico
"""
import os
import sys

TAMANHOS = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main():
    entrada = sys.argv[1] if len(sys.argv) > 1 else "T2M_logo-03.png"
    saida = sys.argv[2] if len(sys.argv) > 2 else "icon2.ico"

    if not os.path.exists(entrada):
        print(f"[X] Arquivo nao encontrado: {entrada}")
        print("    Rode este script na pasta onde esta o logo, ou informe o caminho.")
        return 1

    try:
        from PIL import Image
    except ImportError:
        print("[X] Biblioteca Pillow nao instalada.")
        print("    Instale com:  pip install pillow")
        return 1

    try:
        img = Image.open(entrada).convert("RGBA")
        print(f">>> Logo carregado: {entrada}  ({img.width}x{img.height})")

        # Deixa a imagem quadrada, centralizando sobre fundo transparente.
        # Sem isso, um logo retangular fica esticado e distorcido no icone.
        lado = max(img.width, img.height)
        if img.width != img.height:
            quadrada = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
            quadrada.paste(img, ((lado - img.width) // 2, (lado - img.height) // 2))
            img = quadrada
            print(f">>> Ajustado para quadrado {lado}x{lado} (fundo transparente)")

        img.save(saida, format="ICO", sizes=TAMANHOS)
        tam_kb = os.path.getsize(saida) / 1024
        print(f">>> Icone gerado: {saida}  ({tam_kb:.1f} KB)")
        print(f">>> Tamanhos embutidos: {', '.join(f'{w}x{h}' for w, h in TAMANHOS)}")
        return 0

    except Exception as e:
        print(f"[X] Falha ao gerar o icone: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
