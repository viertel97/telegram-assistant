from datetime import datetime

from github import Github
from quarter_lib.akeyless import get_secrets

github_token = get_secrets(
    ["github/pat_obsidian"]
)

g = Github(github_token)


def add_todoist_dump_to_github(data):
    metadata = "---\n---\n\n"
    today = datetime.today().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_content = generate_file_content(f"Todoist-Dump {timestamp} ", data)
    repo = g.get_repo("viertel97/obsidian")

    repo.create_file(path="0300_Spaces/Social Circle/Todoist-Dumps/" + today + ".md",
                     message=f"obsidian-refresher: {datetime.now()}", content=metadata + file_content)
    print(f"Created {today}.md")


def generate_file_content(summary, description):
    return_string = f"# {summary}\n\n"
    if description:
        return_string += f"{description}\n\n"
    return return_string
