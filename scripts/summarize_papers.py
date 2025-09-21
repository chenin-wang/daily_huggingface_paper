"""
summarize_papers.py

This script summarizes the daily papers pulled from Hugging Face's papers page,
updates the README with the summaries, and cleans up temporary files.
"""

# Standard library imports
import json
import os
import time
from datetime import datetime
from typing import List, Dict

# Third party imports
import google.generativeai as genai

# Configure the Gemini API
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def summarize_paper(title: str, abstract: str, pdf_path: str, model_name: str) -> str:
    """
    Summarizes a research paper using the Gemini API.

    Args:
    - title (str): The title of the paper.
    - abstract (str): The abstract of the paper.
    - pdf_path (str): The path to the PDF of the paper.

    Returns:
    - str: The summary of the paper.
    """

    model = genai.GenerativeModel(model_name=model_name)

    # Upload the PDF to Gemini
    pdf_file = genai.upload_file(path=pdf_path, display_name=f"paper_{title}")

    # Load the prompt template
    with open("templates/prompt_template.md", "r") as f:
        prompt_template = f.read()

    prompt = prompt_template.replace("{title}", title).replace("{abstract}", abstract)

    response = model.generate_content([pdf_file, prompt])

    return response.text


def update_readme(summaries: List[Dict[str, str]]) -> None:
    """
    Updates the README file with the summaries of the papers.

    Args:
    - summaries (List[Dict[str, str]]): A list of dictionaries containing paper information and summaries.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    new_content = f"\n\n# Papers for {date_str}\n\n"
    for summary in summaries:
        # Replace line breaks with spaces
        summary["summary"] = summary["summary"].replace("\n", " ")
        new_content += f"## [{summary['title']}]({summary['arxiv_link']})\n"
        new_content += f"summary:{summary['summary']}\n\n"

    day = date_str.split("-")[2]

    # Write the new content to the archive
    # Create the archive directory if it doesn't exist
    year = date_str.split("-")[0]
    month = date_str.split("-")[1]
    os.makedirs(f"archive/{year}/{month}", exist_ok=True)
    with open(f"archive/{year}/{month}/{day}.md", "w") as f:
        f.write(new_content)

    # Update the README with the new content
    # Load the existing README
    with open("README.md", "r") as f:
        existing_content = f.read()

    # Load the intro template
    with open("templates/README_intro.md", "r") as f:
        intro_content = f.read()

    # Add the date to the intro
    date_str_readme = date_str.replace("-", "--")
    intro_content = intro_content.replace("{DATE}", f"{date_str_readme} \n \n")

    # Remove the existing header
    front_content = existing_content.split("## Papers for")[0]
    existing_content = existing_content.replace(front_content, "")

    # Combine the intro, new content, and existing content
    updated_content = intro_content + new_content + "\n\n" +  existing_content

    # Write the updated content to the README
    with open("README.md", "w") as f:
        f.write(updated_content)


def main() -> None:
    """
    Main function to summarize papers, update the README, and clean up temporary files.
    """
    date = datetime.now().strftime("%Y-%m-%d")
    with open(f"data/{date}_papers.json", "r") as f:
        papers = json.load(f)

    summaries = []
    for paper in papers:
        try:
            summary = summarize_paper(
                title=  paper["title"],
                abstract=paper["abstract"],
                pdf_path=paper["pdf_path"],
                model_name="gemini-2.5-pro"
            )
            summaries.append({**paper, "summary": summary})
            time.sleep(60) # Sleep for 1 minute to avoid rate limiting
        except Exception:
            try:
                print(f"Failed to summarize paper {paper['title']}. Trying with a different model.")
                summary = summarize_paper(
                    title=paper["title"],
                    abstract=paper["abstract"],
                    pdf_path=paper["pdf_path"],
                    model_name="gemini-2.5-flash"
                )
                summaries.append({**paper, "summary": summary})
            except Exception as e:
                print(f"Failed to summarize paper {paper['title']} with both models. Due to {e}")
                continue

    update_readme(summaries)

    # Clean up temporary PDF files
    for paper in papers:
        if os.path.exists(paper["pdf_path"]):
            os.remove(paper["pdf_path"])


if __name__ == "__main__":
    main()
