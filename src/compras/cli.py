"""Linha de comando: `compras --help`."""
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from compras.config import obter_configuracao
from compras.banco.conexao import Sessao, criar_tabelas
from compras.nota.leitor import ler_nota
from compras.servicos import consultas
from compras.servicos.importar import NotaJaImportada, salvar_nota

app = typer.Typer(help="Gerenciador de compras de mercado")
console = Console()


def _avisar_divergencias(nota) -> None:
    if nota.economia:
        console.print(f"[cyan]Economia informada na nota: R$ {nota.economia:.2f}[/cyan]")
    if nota.confere_total():
        console.print("[green]Soma dos itens confere com o total da nota.[/green]")
        return
    console.print(f"[yellow]Atenção: a soma dos itens difere do total da nota em "
                  f"R$ {nota.diferenca():.2f}.[/yellow]")
    console.print(f"[yellow]  Soma dos itens: R$ {nota.soma_itens():.2f} | desconto: "
                  f"R$ {nota.desconto:.2f} | total da nota: R$ {nota.valor_total:.2f}[/yellow]")
    if nota.itens_faltando():
        console.print(f"[yellow]  Itens não lidos: {nota.itens_faltando()}[/yellow]")
    if nota.duvidas:
        console.print("[yellow]  Confira no cupom (as leituras discordaram):[/yellow]")
        for d in nota.duvidas:
            inteira = f"R$ {d.leitura_inteira}" if d.leitura_inteira is not None else "não lido"
            console.print(f"[yellow]    item {d.numero_item} {d.descricao}: "
                          f"{inteira} ou R$ {d.leitura_zoom}?[/yellow]")
    for item in nota.itens_inconsistentes():
        console.print(f"[yellow]  - {item.descricao}: {item.quantidade} x "
                      f"{item.valor_unitario} != {item.valor_total}[/yellow]")


def reais(valor) -> str:
    """1234.5 -> '1.234,50'"""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def quantidade(valor, unidade: str) -> str:
    unidade = (unidade or "UN").upper()
    if unidade in ("KG", "L"):
        return f"{valor:.3f}".replace(".", ",") + f" {unidade.lower()}"
    return f"{int(valor) if valor == int(valor) else valor} {unidade.lower()}"


@app.command("iniciar-banco")
def iniciar_banco():
    """Cria as tabelas no PostgreSQL."""
    criar_tabelas()
    console.print("[green]Tabelas criadas.[/green]")


@app.command()
def ler(imagem: Path, provedor: str = typer.Option(None, help="claude | gemini | openai")):
    """Lê a foto da nota e mostra o resultado, sem salvar."""
    with console.status(f"Lendo a nota com {provedor or obter_configuracao().provedor_visao}... "
                        "(modelo local pode levar até 1 min)") as status:
        inicio = time.perf_counter()
        nota = ler_nota(imagem, provedor, ao_progredir=status.update)
    console.print(f"[dim]Lida em {time.perf_counter() - inicio:.1f}s[/dim]")
    console.print_json(nota.model_dump_json())
    _avisar_divergencias(nota)


@app.command()
def importar(imagem: Path, provedor: str = typer.Option(None, help="claude | gemini | openai")):
    """Lê a foto da nota e grava no banco."""
    with console.status(f"Lendo a nota com {provedor or obter_configuracao().provedor_visao}... "
                        "(modelo local pode levar até 1 min)") as status:
        inicio = time.perf_counter()
        nota = ler_nota(imagem, provedor, ao_progredir=status.update)
    console.print(f"[dim]Lida em {time.perf_counter() - inicio:.1f}s[/dim]")
    _avisar_divergencias(nota)
    with Sessao() as sessao:
        try:
            compra = salvar_nota(sessao, nota, provedor=provedor, imagem=str(imagem))
        except NotaJaImportada:
            console.print("[red]Essa nota já foi importada.[/red]")
            raise typer.Exit(1)
    console.print(f"[green]Compra #{compra.id} salva com {len(nota.itens)} itens "
                  f"(R$ {nota.valor_total}).[/green]")


@app.command()
def sefaz(
    entrada: str = typer.Argument(
        ..., help="Foto do QR code, link do QR code ou página .html já salva em notas/sefaz"),
    salvar: bool = typer.Option(False, "--salvar", help="Grava a nota no banco"),
    provedor: str = typer.Option(None, help="Modelo usado só para categorias/plano B"),
    sem_modelo: bool = typer.Option(False, "--sem-modelo",
                                    help="Não usa IA: categorias por palavras-chave"),
):
    """Importa a nota pela SEFAZ (valores exatos). Você resolve o captcha no navegador."""
    from compras.sefaz.importar import importar_da_sefaz
    from compras.sefaz.parser import LayoutDesconhecido
    from compras.sefaz.qrcode import QRCodeNaoEncontrado

    try:
        nota, arquivo = importar_da_sefaz(entrada, provedor,
                                          avisar=lambda m: console.print(f"[cyan]{m}[/cyan]"),
                                          usar_modelo=not sem_modelo)
    except (QRCodeNaoEncontrado, LayoutDesconhecido) as erro:
        console.print(f"[red]{erro}[/red]")
        raise typer.Exit(1)
    console.print_json(nota.model_dump_json())
    console.print(f"[dim]Página da SEFAZ salva em {arquivo}[/dim]")
    _avisar_divergencias(nota)
    if salvar:
        with Sessao() as sessao:
            try:
                compra = salvar_nota(sessao, nota, origem="sefaz", provedor=provedor)
            except NotaJaImportada:
                console.print("[red]Essa nota já foi importada.[/red]")
                raise typer.Exit(1)
        console.print(f"[green]Compra #{compra.id} salva ({len(nota.itens)} itens, "
                      f"R$ {nota.valor_total}).[/green]")


@app.command("importar-salvas")
def importar_salvas(
    pasta: Path = typer.Argument(Path("notas/sefaz"), help="Pasta com as páginas .html"),
    provedor: str = typer.Option(None),
    sem_modelo: bool = typer.Option(False, "--sem-modelo",
                                    help="Não usa IA: categorias por palavras-chave"),
):
    """Grava no banco todas as páginas da SEFAZ já baixadas (pula as já importadas)."""
    from compras.sefaz.importar import importar_da_sefaz

    arquivos = sorted(pasta.glob("*.html"))
    if not arquivos:
        console.print(f"[yellow]Nenhum .html em {pasta}[/yellow]")
        raise typer.Exit()
    novas = 0
    for arquivo in arquivos:
        try:
            with console.status(f"{arquivo.name}: lendo e classificando..."):
                nota, _ = importar_da_sefaz(
                    str(arquivo), provedor, usar_modelo=not sem_modelo,
                    avisar=lambda m: console.print(f"[dim]  {m}[/dim]")
                    if m.startswith(("Categorias", "Modelo")) else None)
        except Exception as erro:
            console.print(f"[red]{arquivo.name}: {erro}[/red]")
            continue
        with Sessao() as sessao:
            try:
                compra = salvar_nota(sessao, nota, origem="sefaz", provedor=provedor)
            except NotaJaImportada:
                console.print(f"[dim]{arquivo.name}: já importada[/dim]")
                continue
        novas += 1
        situacao = "ok" if nota.confere_total() else f"diferença R$ {nota.diferenca():.2f}"
        console.print(f"[green]{arquivo.name}: compra #{compra.id}, {len(nota.itens)} itens, "
                      f"R$ {nota.valor_total} ({situacao})[/green]")
    console.print(f"{novas} nota(s) nova(s) importada(s).")


@app.command()
def recategorizar(
    sem_modelo: bool = typer.Option(False, "--sem-modelo",
                                    help="Não usa IA: só palavras-chave"),
    provedor: str = typer.Option(None),
    mostrar: bool = typer.Option(True, "--mostrar/--quieto"),
):
    """Reclassifica todos os itens do banco (LM primeiro, palavras-chave de reserva)."""
    from sqlalchemy import select

    from compras.banco.modelos import ItemCompra
    from compras.nota.categorizar import categorizar_detalhado
    from compras.nota.esquema import ItemNota
    from compras.visao.fabrica import obter_provedor

    modelo = None if sem_modelo else obter_provedor(provedor)
    tabela = Table("Produto", "Antes", "Depois", "Por")
    with Sessao() as sessao:
        registros = sessao.scalars(select(ItemCompra)).all()
        # classifica cada descrição uma vez só (o mesmo produto aparece em várias notas)
        descricoes = sorted({r.descricao for r in registros})
        provisorios = [ItemNota(descricao=d, quantidade=1, valor_unitario=0, valor_total=0)
                       for d in descricoes]
        with console.status(f"Classificando {len(descricoes)} produtos distintos..."):
            resultado = categorizar_detalhado(provisorios, modelo)
        nova = {i.descricao: (i.categoria, o)
                for i, o in zip(resultado.itens, resultado.origens)}

        mudaram = 0
        for registro in registros:
            categoria, origem = nova[registro.descricao]
            if categoria != registro.categoria:
                tabela.add_row(registro.descricao, registro.categoria, categoria, origem)
                registro.categoria = categoria
                mudaram += 1
        sessao.commit()
    if mostrar and mudaram:
        console.print(tabela)
    console.print(f"[cyan]{resultado.resumo()}[/cyan]")
    console.print(f"{mudaram} item(ns) recategorizado(s) de {len(registros)}.")


@app.command("listar-categorias")
def listar_categorias(categoria: str = typer.Argument(None, help="Filtra uma categoria")):
    """Lista os produtos distintos de cada categoria, para revisar a classificação."""
    from sqlalchemy import select

    from compras.banco.modelos import ItemCompra

    with Sessao() as sessao:
        consulta = select(ItemCompra.categoria, ItemCompra.descricao).distinct()
        if categoria:
            consulta = consulta.where(ItemCompra.categoria == categoria)
        linhas = sessao.execute(consulta.order_by(ItemCompra.categoria,
                                                  ItemCompra.descricao)).all()
    tabela = Table("Categoria", "Produto")
    anterior = None
    for cat, descricao in linhas:
        if anterior and cat != anterior:
            tabela.add_section()
        tabela.add_row(cat if cat != anterior else "", descricao)
        anterior = cat
    console.print(tabela)


@app.command()
def gastos():
    """Gasto total por mês."""
    with Sessao() as sessao:
        linhas = consultas.gasto_por_mes(sessao)
    if not linhas:
        console.print("[yellow]Nenhuma compra no banco ainda.[/yellow]")
        return
    tabela = Table("Mês", "Total (R$)")
    for ano, mes, total in linhas:
        tabela.add_row(f"{int(mes):02d}/{int(ano)}", reais(total))
    console.print(tabela)


@app.command()
def categorias(ano: int, mes: int):
    """Gasto por categoria em um mês."""
    with Sessao() as sessao:
        linhas = consultas.gasto_por_categoria(sessao, ano, mes)
    if not linhas:
        console.print(f"[yellow]Nenhuma compra em {mes:02d}/{ano}. "
                      f"Rode `compras gastos` para ver os meses com compras.[/yellow]")
        return
    total_mes = sum(total for _, total in linhas)
    tabela = Table("Categoria", "Total (R$)", "%", title=f"{mes:02d}/{ano}")
    for categoria, total in linhas:
        tabela.add_row(categoria, reais(total), f"{100 * total / total_mes:.0f}%")
    tabela.add_section()
    tabela.add_row("[bold]total[/bold]", f"[bold]{reais(total_mes)}[/bold]", "")
    console.print(tabela)


@app.command()
def top(limite: int = 10):
    """Produtos com que mais gasto."""
    with Sessao() as sessao:
        linhas = consultas.produtos_que_mais_gasto(sessao, limite)
    tabela = Table("Produto", "Qtd", "Total (R$)")
    for descricao, unidade, qtd, total in linhas:
        tabela.add_row(descricao, quantidade(qtd, unidade), reais(total))
    console.print(tabela)


@app.command()
def api(
    host: str = typer.Option("0.0.0.0", help="0.0.0.0 = acessível pelo celular na mesma rede"),
    porta: int = typer.Option(8000),
    recarregar: bool = typer.Option(False, "--recarregar", help="Reinicia ao salvar arquivos"),
):
    """Sobe a API. Documentação interativa em http://localhost:8000/docs"""
    import socket

    import uvicorn

    try:  # descobre o IP do Mac na rede local (não envia nada, só consulta a rota)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
    except OSError:
        ip = "IP-do-Mac"
    console.print(f"[green]API em http://localhost:{porta}/docs[/green]  "
                  f"(no celular, mesma rede Wi-Fi: http://{ip}:{porta})")
    uvicorn.run("compras.api.app:app", host=host, port=porta, reload=recarregar)


if __name__ == "__main__":
    app()
