# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from pathlib import Path

import click
import requests
import sqlalchemy
import xlsxwriter
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, delete, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.session import Session, sessionmaker
from unidecode import unidecode

from models import Base, JobModel


APP_DIR = Path(__file__).parent
log = logging.getLogger()


@click.command()
@click.option(
    "--keyword",
    default="python fejlesztő",
    help="the search term. can be multiple words",
)
@click.option(
    "--output",
    default="profession_hu_jobs__"
    + str(datetime.now()).replace(" ", "_").replace(":", "_").replace(".", "_"),
    help="output file name",
)
@click.option("--pages-to-check", default=50, help="number of pages to check")
@click.option(
    "--save-to-xlsx", default=False, show_default=True, help="save to excel sheet"
)
def main(output, pages_to_check, save_to_xlsx, keyword):
    my_jobs_data = search_and_process(pages_to_check, keyword)
    if save_to_xlsx:
        export_to_xlsx(my_jobs_data, output)
    save_to_db(my_jobs_data, output, keyword)


def search_and_process(pages, keyword):
    keyword = "".join([c if c != " " else "%20" for c in keyword])
    page_number = 1

    positions = []
    urls = []
    companies = []
    addresses = []
    salaries = []
    added_ats = []

    print("collecting data: ", end="", flush=True)
    log.info("data collection started")

    while page_number <= pages:
        url = f"https://www.profession.hu/allasok/{page_number},0,0,{keyword}%401%401?keywordsearch"
        log.info(f"url: {unidecode(url)}")

        print(".", end="", flush=True)
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        all_cards = soup.find_all(class_="card")

        for card in all_cards:
            try:
                position = card.find(class_="job-card__title").get_text().strip()
                url = card.select("h2 a")

                company = (
                    card.find(class_="job-card__company-name")
                    .get_text()
                    .strip()
                    .replace('"', "")
                )

                address = (
                    card.find(class_="job-card__company-address").get_text().strip()
                )

                salary = card.select(".bonus_salary > dd:nth-child(2)")
                if salary:
                    salary = salary[0].text
                else:
                    salary = ""

                added_at = (
                    str(datetime.now())
                    .replace(" ", "_")
                    .replace(":", "_")
                    .replace(".", "_")
                )

                if company.lower() not in [
                    "randstad hungary kft.",
                    "tech people hungary kft.",
                ]:
                    positions.append(position.splitlines()[0])
                    urls.append(url[0]["href"])
                    companies.append(company)
                    addresses.append(address)
                    salaries.append(salary)
                    added_ats.append(added_at)

            except:
                continue

        page_number += 1
        log.info("page parsed")

    jobs_data = {
        "positions": positions,
        "urls": urls,
        "companies": companies,
        "addresses": addresses,
        "salaries": salaries,
        "added_ats": added_ats,
    }

    return jobs_data


def export_to_xlsx(jobs_data, output):
    log.info("export to xlsx started")
    out_file = f"{output}.xlsx"

    print(f"creating excel file: {out_file} ->", end=" ")
    headers = ["position", "company", "address", "salary", "url"]

    wb = xlsxwriter.Workbook(out_file)
    ws = wb.add_worksheet()
    ws.set_column("A:C", 35)
    ws.set_column("D:E", 12)
    ws.set_default_row(20)
    ws.set_zoom(100)
    row = 1

    cf = wb.add_format()
    cf.set_font_size(10)
    cf.set_align("vcenter")
    cf.set_bold(True)

    for i in range(len(headers)):
        ws.write_string(0, i, headers[i], cf)

    for x in range(len(jobs_data["positions"])):
        cf = wb.add_format()
        cf.set_font_size(9)
        cf.set_align("vcenter")

        ws.write_string(row, 0, jobs_data["positions"][x], cf)
        ws.write_string(row, 1, jobs_data["companies"][x], cf)
        ws.write_string(row, 2, jobs_data["addresses"][x], cf)
        ws.write_string(row, 3, jobs_data["salaries"][x], cf)
        ws.write_url(row, 4, jobs_data["urls"][x], cf, string=jobs_data["urls"][x])
        row += 1
    wb.close()
    log.info("export to xlsx done")


def save_to_db(jobs_data, output, keyword):
    my_sqlops = SqlOps(jobs_data, keyword)
    my_sqlops.sql_add()


class SqlOps(object):
    def __init__(
        self,
        jobs_data,
        keyword,
    ):
        self.conn_string = f"sqlite:///{keyword}.sqlite3"
        self.engine = create_engine(self.conn_string)
        self.jobs_data = jobs_data

    def sql_add(self):
        Base.metadata.create_all(self.engine)

        new_jobs = []
        rollback = False
        for i in range(0, len(self.jobs_data["positions"])):
            try:

                Session = sessionmaker(bind=self.engine)
                session = Session()

                job = JobModel(
                    position=self.jobs_data["positions"][i],
                    company=self.jobs_data["companies"][i],
                    address=self.jobs_data["addresses"][i],
                    salary=self.jobs_data["salaries"][i],
                    url=self.jobs_data["urls"][i],
                    added_at=self.jobs_data["added_ats"][i],
                )
                session.add(job)
                session.commit()
            except IntegrityError as e:
                log.error(e)
                session.rollback()
                rollback = True
            finally:
                session.close()

            if not rollback:
                new_jobs.append(
                    [
                        self.jobs_data["positions"][i],
                        self.jobs_data["companies"][i],
                        self.jobs_data["addresses"][i],
                        self.jobs_data["salaries"][i],
                        self.jobs_data["urls"][i],
                        self.jobs_data["added_ats"][i],
                    ]
                )

        print("\nnew jobs:")
        for new_job in new_jobs:
            print("new job:", new_job)


if __name__ == "__main__":
    handler = logging.FileHandler(APP_DIR / "scraper.log")
    formatter = logging.Formatter("%(asctime)s %(name)-12s %(levelname)-8s %(message)s")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    main()
