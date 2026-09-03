import asyncio
import logging
import click
from app.graph import graph_client
from app.config import settings
from app.state import init_db, set_delta_token
from app.subscriptions import create_subscription
from app.sync import process_delta

@click.group()
def cli():
    pass

@cli.command()
def test_token():
    try:
        # Just instantiate GraphClient and try to get token
        _ = graph_client._get_token()
        click.echo("Token acquisition succeeded.")
    except Exception as e:
        click.echo(f"Token acquisition failed: {e}")

@cli.command()
@click.option('--hostname', required=True)
@click.option('--site-path', required=True)
def discover_site(hostname: str, site_path: str):
    async def _run():
        path = site_path.strip("/")
        url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:/{path}"
        resp = await graph_client.get(url)
        click.echo(resp.text)
    asyncio.run(_run())

@cli.command()
@click.option('--site-id', required=True)
def list_site_lists(site_id: str):
    async def _run():
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists"
        resp = await graph_client.get(url)
        click.echo(resp.text)
    asyncio.run(_run())

@cli.command()
@click.option('--site-id', required=True)
def list_site_drives(site_id: str):
    async def _run():
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        resp = await graph_client.get(url)
        click.echo(resp.text)
    asyncio.run(_run())

@cli.command()
@click.option('--user-id', required=True)
def list_user_drives(user_id: str):
    async def _run():
        url = f"https://graph.microsoft.com/v1.0/users/{user_id}/drives"
        resp = await graph_client.get(url)
        click.echo(resp.text)
    asyncio.run(_run())

@cli.command()
def random_client_state():
    import secrets
    click.echo(secrets.token_urlsafe(32))

@cli.command()
def check_source_root():
    async def _run():
        url = f"https://graph.microsoft.com/v1.0/drives/{settings.source_drive_id}/root:/{settings.source_root_path}"
        resp = await graph_client.get(url)
        click.echo(resp.text)
    asyncio.run(_run())

@cli.command()
def check_dest_root():
    async def _run():
        url = f"https://graph.microsoft.com/v1.0/drives/{settings.dest_drive_id}/root:/{settings.dest_root_path}"
        resp = await graph_client.get(url)
        click.echo(resp.text)
    asyncio.run(_run())

@cli.command()
def init_delta():
    async def _run():
        url = f"https://graph.microsoft.com/v1.0/drives/{settings.source_drive_id}/root/delta?token=latest"
        resp = await graph_client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            if "@odata.deltaLink" in data:
                set_delta_token(data["@odata.deltaLink"])
                click.echo("Delta link initialized successfully.")
            else:
                click.echo("Delta link not found in response.")
        else:
            click.echo(f"Failed to init delta: {resp.text}")
    asyncio.run(_run())

@cli.command(name="create-subscription")
def create_sub():
    asyncio.run(create_subscription())

@cli.command(name="sync-once")
def sync_once():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s"
    )
    click.echo("Starting sync...")
    asyncio.run(process_delta())
    click.echo("Sync complete.")

if __name__ == "__main__":
    cli()
