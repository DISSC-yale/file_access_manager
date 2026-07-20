import re
import subprocess
from typing import List


def insert_cli_help(commands: List[List[str]], content: str, header: str = "## Command Line"):
    section = [header]
    for command in commands:
        command_string = " ".join(command[1:])
        output = subprocess.run(command + ["--help"], check=False, capture_output=True)
        if output.stdout == b"" and output.stderr != b"":
            msg = f"command {command_string} failed: {output.stderr.decode('utf-8')}"
            raise RuntimeError(msg)
        help = output.stdout.decode("utf-8").replace("\r\n\r\n", "\r\n")
        section.append(f"```none title='{command_string}'\n{help}```")
    section_content = "\n\n".join(section) + "\n"
    return (
        re.compile(f"{header}[^#]*").sub(section_content, content)
        if header in content
        else content + "\n" + section_content
    )


if __name__ == "__main__":
    commands_map = {
        "docs/functions/Access.md": [["manage-access"], ["manage-access", "pending"], ["manage-access", "check"]],
        "docs/functions/Locations.md": [["manage-access", "locations"]],
        "docs/functions/Projects.md": [["manage-access", "init"]],
    }
    for file, commands in commands_map.items():
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
        with open(file, "w", encoding="utf-8") as f:
            f.write(insert_cli_help(commands, content))
