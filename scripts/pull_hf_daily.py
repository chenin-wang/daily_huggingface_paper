"""
pull_hf_daily.py

This script pulls the daily papers from Hugging Face's papers page, downloads their PDFs,
and saves their information in a JSON file.
"""

# Standard library imports
import json
import os
import re
from typing import List, Dict
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

from typing import Optional,Tuple
from concurrent.futures import ThreadPoolExecutor,as_completed
HF_BASE_URL = "https://huggingface.co"
HF_PAPERS_URL = "https://huggingface.co/papers/date"
def get_previous_weekday():
    today = datetime.now()
    previous_day = today-timedelta(days=1)
    
    return previous_day.strftime("%Y-%m-%d")

def download_pdf(arxiv_link: str, save_path: str) -> Tuple[str, bool]:
    """
    Downloads the PDF of a paper from arXiv given its ID.

    Args:
        arxiv_link (str): The arXiv ID of the paper.
        save_path (str): The path where the PDF will be saved.

    Returns:
        Tuple[str, bool]: (arxiv_id, True) if successful, (arxiv_id, False) otherwise.
    """
    try:
        # 添加请求头，模拟浏览器行为
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        print(f"Downloading PDF from {arxiv_link}")
        response = requests.get(arxiv_link, headers=headers, timeout=60)
        response.raise_for_status()  # 抛出HTTP错误状态码
        
        with open(save_path, "wb") as f:
            f.write(response.content)
        return (arxiv_link, True)
    except requests.exceptions.HTTPError as e:
        print(f"HTTP错误: {e}")
    except requests.exceptions.ConnectionError:
        print("连接错误，可能是网络问题或无法访问arxiv.org")
    except requests.exceptions.Timeout:
        print("请求超时")
    except IOError as e:
        print(f"文件写入错误: {e}")
    except Exception as e:
        print(f"发生未知错误: {e}")
    return (arxiv_link, False)


def pull_hf_daily(date: Optional[str] = None) -> None:
    """
    Pulls the daily papers from Hugging Face's papers page, downloads their PDFs,
    and saves their information in a JSON file.
    """
    if date is None:
        date = get_previous_weekday()
    hf_papers_url=f"{HF_PAPERS_URL}/{date}"
    response = requests.get(hf_papers_url,timeout=60)
    if response.status_code != 200:
        print(f"Failed to retrieve papers from {hf_papers_url}")
        return
    print(f"Successfully retrieved papers from {hf_papers_url}")
    soup = BeautifulSoup(response.content, "html.parser")
    today_papers_list = soup.find_all("article")
    print(f"{date} number of papers: {len(today_papers_list)}")

    papers: List[Dict[str, str]] = []
    seen_ids = set()  # Set to track seen arXiv IDs
    temp_pdf_dir = "temp_pdfs"
    os.makedirs(
        temp_pdf_dir, exist_ok=True
    )  # Create temp_pdfs directory if it doesn't exist

    # Locate the relevant elements
    for paper in today_papers_list:
        link = paper.a.get("href")
        hf_paper_url = HF_BASE_URL+link
        print(hf_paper_url)
        content = requests.get(hf_paper_url,timeout=60)
        if content.status_code != 200:
            print(f"Failed to retrieve paper from {hf_paper_url}")
            continue
        soup = BeautifulSoup(content.text, "html.parser")
        
        title = soup.find("h1", class_="mb-2 text-2xl font-semibold sm:text-3xl lg:pr-6 lg:text-3xl xl:pr-10 2xl:text-4xl").text.replace("\n ","")
        abstract = soup.find("p", class_="text-gray-600").text
        arxiv_id_match = re.search(r"/papers/(\d+\.\d+)", link)
        if arxiv_id_match:
            arxiv_id = arxiv_id_match.group(1)
        else:
            print(f"Could not extract arXiv ID from link: {link}")
            continue

        # Check for duplicates using arXiv ID
        if arxiv_id in seen_ids:
            print(f"Duplicate paper detected with ID {arxiv_id}, skipping.")
            continue
        seen_ids.add(arxiv_id)  # Add ID to set of seen IDs

        # Create the full link to the paper
        arxiv_link = f"https://arxiv.org/pdf/{arxiv_id}"
        # Attempt to download the PDF
        pdf_path = os.path.join(temp_pdf_dir, f"{arxiv_id}.pdf")
        papers.append(
                    {
                        "title": title,
                        "arxiv_id": arxiv_id,
                        "arxiv_link": arxiv_link,
                        "hf_link": hf_paper_url,
                        "pdf_path": pdf_path,
                        "abstract": abstract,
                    }
                )
    # multi thread
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(download_pdf, paper["arxiv_link"], paper["pdf_path"]) for paper in papers]
        for future in as_completed(futures):
            arxiv_link, success = future.result()
            if success:
                print(f"Successfully downloaded PDF for arxiv link: {arxiv_link}")
            else:
                papers = [paper for paper in papers if paper["arxiv_link"] != arxiv_link]
                print(f"Failed to download PDF for arxiv link: {arxiv_link}")

    date = datetime.now().strftime("%Y-%m-%d")
    data_dir = "data"
    print(f"Ensuring data directory exists: {data_dir}")
    os.makedirs(data_dir, exist_ok=True)  # Create 'data' directory if it doesn't exist
    data_file_path = os.path.join(data_dir, f"{date}_papers.json")

    print(f"Writing data to {data_file_path}")
    with open(data_file_path, "w") as f:
        json.dump(papers, f, indent=2)
    print(f"Saved {len(papers)} papers' information and PDFs")

if __name__ == "__main__":
    date = ""
    if date =="":
        date = get_previous_weekday()
    pull_hf_daily(date)
