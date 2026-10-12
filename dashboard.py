import subprocess
import threading
import time
from rich.live import Live
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from datetime import datetime

# Track request counts and last seen time per server
stats = {
    "web1": {"count": 0, "last": "—"},
    "web2": {"count": 0, "last": "—"},
    "web3": {"count": 0, "last": "—"},
}

lock = threading.Lock()

def stream_logs(container: str):
    """Stream docker logs for a container and count traffic hits."""
    try:
        proc = subprocess.Popen(
            ["docker", "logs", "-f", "--tail", "0", container],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        for line in proc.stdout:
            if "Traffic received on" in line:
                with lock:
                    stats[container]["count"] += 1
                    stats[container]["last"] = datetime.now().strftime("%H:%M:%S")
    except Exception as e:
        print(f"[{container}] Error: {e}")


def build_table() -> Panel:
    """Build a rich table with current stats."""
    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="bright_blue",
        expand=True
    )

    table.add_column("🖥️  Server",    style="bold white",  justify="center", min_width=12)
    table.add_column("📦 Container", style="dim white",   justify="center", min_width=18)
    table.add_column("📊 Requests",  style="bold green",  justify="center", min_width=12)
    table.add_column("🕐 Last Hit",  style="yellow",      justify="center", min_width=12)

    total = 0
    colors = ["bright_cyan", "bright_magenta", "bright_yellow"]

    with lock:
        for i, (name, data) in enumerate(stats.items()):
            count = data["count"]
            total += count
            bar = "█" * min(count, 30) + " " + str(count)
            table.add_row(
                Text(name.upper(), style=f"bold {colors[i]}"),
                name,
                bar,
                data["last"]
            )

    table.add_section()
    table.add_row(
        Text("TOTAL", style="bold white"),
        "—",
        Text(str(total), style="bold green"),
        "—"
    )

    return Panel(
        table,
        title=f"[bold cyan]⚡ Live Load Balancer Dashboard[/]  [dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]",
        subtitle="[dim]Monitoring web1 · web2 · web3  |  Ctrl+C to exit[/]",
        border_style="cyan"
    )


if __name__ == "__main__":
    console = Console()
    console.print("\n[bold cyan]Starting Live Traffic Dashboard...[/]\n")

    # Start a background thread per container
    for container in stats:
        t = threading.Thread(target=stream_logs, args=(container,), daemon=True)
        t.start()

    # Live refreshing display
    with Live(build_table(), refresh_per_second=2, screen=False) as live:
        try:
            while True:
                time.sleep(0.5)
                live.update(build_table())
        except KeyboardInterrupt:
            console.print("\n[bold red]Dashboard stopped.[/]")
