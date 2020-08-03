import requests
import re
from bs4 import BeautifulSoup
import argparse
import os
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF, renderPM
from PyPDF2 import PdfFileMerger
import img2pdf

# pip install svglib
# pip install pypdf2
# pip install img2pdf



# https://musescore.com/static/musescore/scoredata/gen/9/8/3/6087389/3efafd0eb10f19468d8f3d8f23931d77016b6a03/score_0.svg?no-cache=158703369
regex_in_quote = '"([^"]*)"' # im not sure what kind of magic this is

regex_img_link = f'"thumbnailUrl": {regex_in_quote}'
regex_name_ = '"name": "([^"]*)"'
regex_page_type = '"@type": "([^"]*)"'


regex_pages_count = '"pages":([0-9]*)'
regex_midi_file = f'"midi":{regex_in_quote}'
regex_mp3_file = f'"mp3":{regex_in_quote}'


cwd = os.getcwd()

parser = argparse.ArgumentParser()
parser.add_argument(action='store', dest='link', nargs='*')
args = parser.parse_args()

args.link = ' '.join(args.link)
#args.link = 'https://musescore.com/user/28844194/scores/6077997'

user_input = args.link

if not user_input:
	user_input = input('Musescore score link: ')

def replace_number_for_page(l, page):

	split_key = '/score_'
	dot = '.'

	l_split = l.split(split_key)
	l_split[1] = l_split[1].split(dot)

	l_split[1][0] = str(page)
	l_split[1] = dot.join(l_split[1])

	return split_key.join(l_split) # this return removes the annoying query at the end so my file will be properly saved as .svg

def remove_special_char(s):
	return re.sub('[^A-Za-z0-9.]+', '_', s) # remove all the special characters except for `.` and replace them with `_`

def download_files(url, _name):
	file = requests.get(url)
	file_name = url.split(r'/')[-1].replace('score', _name)

	directory = fr'{cwd}\{remove_special_char(file_name)}'
	open(directory, 'wb+').write(file.content)

	return directory

def get_file_extension(name):
	return name[-4:].replace('.','') # 4 last characters get their `.` removed


print('Parsing!')
response = requests.get(user_input)
soup = BeautifulSoup(response.text, 'html.parser')

# find the `source` pdf file, which is for some reasons a `.svg` or `.png`
target_group_too_vague_and_painful = soup.find_all('script')
#print(user_input.replace('/', '\\/'))
for i in target_group_too_vague_and_painful:
	try:
		if 'MusicComposition' in re.findall(regex_page_type, str(i)):# ==  and user_input.replace('/', '\\/') in fr'{i}':
			target = str(i)
			#print(target)
		# break # it will always choose the first block cuz my code is confusing
	except:
		pass

try:
	first_img_url = soup.find('link', {'type':'image/svg+xml'})['href'].split('?no-cache')[0]
	if len(first_img_url) == 0 or first_img_url == 'https://musescore.com/static/public/img/product_icons/musescore/favicon.svg': raise Exception
except:
	first_img_url = re.findall(regex_img_link, target)[0].replace('\\/', '/').split('?no-cache')[0]

#first_img_url = soup.find('link', {'type':'image/svg+xml'})['href'].split('?no-cache')[0]
#print(first_img_url)
name_ = re.findall(regex_name_, target)[0]
print(name_)

# the format for thumbnails are all differnt in different class. this 'script' has svg while 'class:js-store' is in png
target = str(soup.find_all('div', {'class': 'js-store'})).replace('&quot;', '"')
page_number = int(re.findall(regex_pages_count, target)[0])
midi_link = re.findall(regex_midi_file, target)[0].split('?revision=')[0]
mp3_link = re.findall(regex_mp3_file, target)[0].split('?revision=')[0]

#print(page_number)
# target = soup.find('link', {'type':'image/svg+xml'})['href']
# print(target)
# print(first_img_url)
# print(replace_number_for_page(first_img_url, 0))


#download all pages
print('Downloading images!')
raw_img_list = []
for i in range(0,page_number): # despite counting 10, the starting index is 0 for their website, so there are only 9, but the range() got it all
	print(f'{i+1} out of {page_number}', end='\r', flush=True)
	directory = download_files(replace_number_for_page(first_img_url, i), name_) # replace_...() will raise the url number
	raw_img_list.append(fr'{directory}')

print('Converting to PDF!', end='\n', flush=False)
if get_file_extension(raw_img_list[0]) == 'png':
	# despite having the thumbnail as '.png', for some reasons, many pro users have '.svg' file as preload
	with open(f"{name_}.pdf","wb") as f:
		f.write(img2pdf.convert(raw_img_list))

if get_file_extension(raw_img_list[0]) == 'svg':
	pdf_list = []
	for index, svg in enumerate(raw_img_list):
		print(f'{index+1} out of {page_number}', end='\r', flush=True)
		pdf_name = f'output{index}.pdf'
		pdf_list.append(pdf_name)
	
		drawing = svg2rlg(svg)
		renderPDF.drawToFile(drawing, pdf_name)
	
	print('Merging!', end='\n', flush=True)
	merger = PdfFileMerger()
	
	for pdf in pdf_list:
		merger.append(pdf)
	
	merger.write(f'{name_}.pdf')
	merger.close()

print('Cleaning up!', flush=False)
download_files(midi_link, name_)
download_files(mp3_link, name_)
try:
	for i in raw_img_list:
		os.remove(i)
	for i in pdf_list:
		os.remove(i)
except:
	pass

print('\nDone!', flush=False)

