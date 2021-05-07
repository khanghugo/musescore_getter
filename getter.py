import requests
from bs4 import BeautifulSoup
import re
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from PyPDF2 import PdfFileMerger
import img2pdf
import os
import argparse


class Parser:
    def __init__(self, url):
        self.url = url
        self.site_request = self.get_request()

        # one is for the site, one is for the file
        if "scoredata" not in self.url:
            self.html_soup = self.parse()
            self.score_general_info = self.find_score_general_info()
            self.base_url = self.find_base_url()
            self.score_info = self.find_score_file_info()

        else:
            self.content_disposition = self.find_content_disposition()
            self.file_name = self.find_file_name()
            self.file_content = self.site_request.content

    def get_request(self):
        return requests.get(self.url)

    def parse(self):
        return BeautifulSoup(self.site_request.text, 'html.parser')

    def find_score_general_info(self):
        return [str(elements) for elements in self.html_soup.find_all('script') if 'MusicComposition' in re.findall(
            '"@type": "([^"]*)"', str(elements))][0]
        # i am sure it will return only one item in this list, but all okay because there is only one item that match

    def find_base_url(self):
        return re.findall('"thumbnailUrl": "([^"]*)"',
                          self.score_general_info)[0].replace("\\", '').split('score_')[0]

    def is_svg(self):
        svg_link = self.html_soup.find('link', {'type': 'image/svg+xml'})['href'].split('?no-cache')[0]
        if len(svg_link) == 0 or svg_link == \
                "https://musescore.com/static/public/img/product_icons/musescore/favicon.svg":
            return False
        return True

    def find_score_file_info(self):
        name = re.findall('"name": "([^"]*)"', self.score_general_info)[0]

        if self.is_svg():
            img = self.base_url + "score_0.svg"
        else:
            img = self.base_url + "score_0.png"

        page_count = int(re.findall(
            '"pages":([0-9]*)',
            str(self.html_soup.find_all('div', {'class': 'js-store'})).replace('&quot;', '"'))[0]
                         )  # this is a bit too much?

        midi = self.base_url + "score.mid"
        mp3 = self.base_url + "score.mp3"
        mxl = self.base_url + "score.mxl"

        # img is passed at the end so the downloadfile will exclude it later
        return [name, page_count, midi, mxl, mp3, img]

    def find_content_disposition(self):
        return self.site_request.headers.get('content-disposition')

    def find_file_name(self):
        if self.content_disposition:
            # there is a weird inconsistency in the headers.
            # all of the time, it is `filename="something"` but sometimes there is no quotation marks
            return re.findall('(?<=filename=).*', self.content_disposition)[0].replace('"', '')
        else:
            # for some reasons, svg doesnt have content dispositons, probablr the same for png i guess?
            # 'https://musescore.com/static/musescore/scoredata/gen/2/2/1/
            # 6248122/ff4b96202e32a0a90206fb5fa856031468e402fc/score_0.svg'
            return self.url.split('/')[-1]


class DownloadFile:
    def __init__(self, info_list):
        # [name, page_count, midi, mxl, mp3, img]
        self.name = info_list[0]
        self.page_count = info_list[1]

        self.img_first_file = info_list[-1]  # this is just one file
        self.img_file = []
        self.normal_file_url = info_list[2:5]
        self.img_file_url = list(self.img_url())  # this is multiple files

        self.start_dl()

    def dl_file(self, file_url):
        file_class = Parser(file_url)
        file_name = file_class.file_name
        open(file_name, 'wb+').write(file_class.file_content)

        return file_name  # we can be verbose with this return

    def img_nbr_changer(self, num):
        split_1 = self.img_first_file.split('/score_')
        split_2 = split_1[1].split('.')
        # split2[0] is the number
        split_2[0] = str(num)
        split_1[1] = '.'.join(split_2)
        return '/score_'.join(split_1)

    def img_url(self):
        for i in range(0, self.page_count):  # start from 10 pages have score_9 max cuz index matters
            yield self.img_nbr_changer(i)

    def start_dl(self):
        for i in self.normal_file_url:
            print(self.dl_file(i))

        print('Downloading images!')
        for index, i in enumerate(self.img_file_url):
            print(f'{index + 1} out of {self.page_count}', end='\r', flush=True)
            self.img_file.append(self.dl_file(i))


class Merger:
    def __init__(self, img_list, page_count, name):
        self.img_list = img_list
        self.img_ext = self.get_file_ext()
        self.svg_pdf_list = []
        self.page_count = page_count
        self.name = name

        self.start_pdf()

    def get_file_ext(self):
        return self.img_list[0].split('.')[1]

    def svg_to_pdf(self):
        for index, svg in enumerate(self.img_list):
            print(f'{index + 1} out of {self.page_count}', end='\r', flush=True)

            pdf_name = f'output{index}.pdf'
            self.svg_pdf_list.append(pdf_name)

            drawing = svg2rlg(svg)
            renderPDF.drawToFile(drawing, pdf_name)

        merger = PdfFileMerger()

        for pdf in self.svg_pdf_list:
            merger.append(pdf)

        merger.write(f'{self.name}.pdf')
        merger.close()

    def png_to_pdf(self):
        with open(f"{self.name}.pdf", "wb") as f:
            f.write(img2pdf.convert(self.img_list))

    def clean_up(self):
        for dead_1 in self.img_list:
            os.remove(dead_1)

        for dead_2 in self.svg_pdf_list:
            os.remove(dead_2)

    def start_pdf(self):
        if self.img_ext == 'png':
            self.png_to_pdf()

        if self.img_ext == 'svg':
            self.svg_to_pdf()

        print('Cleaning up!')
        self.clean_up()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(action='store', dest='link')
    args = parser.parse_args()

    musescore_url = str()
    if not args.link:
        musescore_url = input("Musescore link: ")
    else:
        musescore_url = args.link

    print('Parsing!')
    info_list = Parser(musescore_url).score_info

    print('Downloading!')
    dl_class = DownloadFile(info_list)
    img_list = dl_class.img_file
    name = dl_class.name
    page_count = dl_class.page_count

    print('\nMerging!')
    Merger(img_list, page_count, name)


if __name__ == "__main__":
    main()
