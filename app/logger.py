import click

def server_log(message: str, level: str = "info") -> None:
    """
    Exibe um log no console com o prefixo SERVER: e cores baseadas no nível.
    
    Args:
        message: A mensagem a ser exibida.
        level: O nível do log (info, warning, error). Default é "info".
    """
    # Define as cores para cada nível
    colors = {
        "info": "cyan",
        "warning": "yellow",
        "error": "red"
    }
    
    # Seleciona a cor baseada no nível (default info se não existir)
    color = colors.get(level.lower(), "cyan")
    
    # Formata o prefixo com a cor e negrito
    prefix = click.style("SERVER:", fg=color, bold=True)
    
    # Exibe a mensagem
    click.echo(f"{prefix}   {message}")
