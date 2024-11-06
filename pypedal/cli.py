"""
Command line interface for pypedal
"""
import click

@click.group()
@click.version_option()
def main():
    """pypedal - A Python-based command line tool"""
    pass

@main.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output file path')
def process(input_file, output):
    """Process the input file"""
    click.echo(f"Processing {input_file}")
    if output:
        click.echo(f"Output will be saved to {output}")

@main.command()
@click.option('--debug/--no-debug', default=False, help='Enable debug mode')
def info(debug):
    """Show system information"""
    click.echo("System Information:")
    if debug:
        click.echo("Debug mode enabled")

if __name__ == '__main__':
    main()
