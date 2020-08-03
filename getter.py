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

cwd = os.getcwd() # this could be unneeded

parser = argparse.ArgumentParser()
parser.add_argument(action='store', dest='link', nargs='*')
args = parser.parse_args()

args.link = ' '.join(args.link)
#args.link = 'https://musescore.com/user/28844194/scores/6077997'

user_input = args.link

if not user_input:
	user_input = input('Musescore score link: ')

def replace_number_for_page(l, page):
	# https://musescore.com/static/musescore/scoredata/gen/9/8/3/6087389/3efafd0eb10f19468d8f3d8f23931d77016b6a03/score_0.svg
	split_key = '/score_'
	dot = '.'

	l_split = l.split(split_key)
	l_split[1] = l_split[1].split(dot)

	l_split[1][0] = str(page)
	l_split[1] = dot.join(l_split[1])

	return split_key.join(l_split) 

def remove_special_char(s):
	return re.sub('[^A-Za-z0-9.]+', '_', s) # remove all the special characters except for `.` and replace them with `_`

def download_files(url, _name):
	# https://musescore.com/static/musescore/scoredata/gen/9/8/3/6087389/3efafd0eb10f19468d8f3d8f23931d77016b6a03/score_0.svg
	file = requests.get(url)
	# this will save the last bit of the directory and replace it with `_name` because if you run this multiple times, I am sure other files will be rewritten
	file_name = url.split(r'/')[-1].replace('score', _name)
	
	# there is no needs for remove_...() but idk to be sure I guess?
	directory = fr'{cwd}\{remove_special_char(file_name)}'
	open(directory, 'wb+').write(file.content)
	
	# this return will be needed to indentify the downloaded files. i don't want to use `global`
	return directory

def get_file_extension(name):
	# score_0.svg
	return name[-4:].replace('.','') # 4 last characters get their `.` removed

print('Parsing!')
response = requests.get(user_input)
soup = BeautifulSoup(response.text, 'html.parser')

# <script> are usually at the end, they include the link informations, score information, and comments
target_group_too_vague_and_painful = soup.find_all('script')

for i in target_group_too_vague_and_painful:
	try:
		if 'MusicComposition' in re.findall(regex_page_type, str(i)): # the <script> we want is the score information, that part contains that string right there
										# the others dont
			target = str(i)
	except:
		pass

# there are two cases for the img_url, the first one is the svg file. the second one could also find the svg file if it's obvious. at the same time, it could find the png file
# therefore, if the first one confirm that there is an svg file then oll korrect. if there isn't, it is sure to have png for all the imgs, which is really bad to look at
try:
	first_img_url = soup.find('link', {'type':'image/svg+xml'})['href'].split('?no-cache')[0]
	if len(first_img_url) == 0 or first_img_url == 'https://musescore.com/static/public/img/product_icons/musescore/favicon.svg': raise Exception
except:
	first_img_url = re.findall(regex_img_link, target)[0].replace('\\/', '/').split('?no-cache')[0]
	
# i hate how i name this `name_`
name_ = re.findall(regex_name_, target)[0]
print(name_)

# this one look at a different body so all of the info here is groupped different from the other
target = str(soup.find_all('div', {'class': 'js-store'})).replace('&quot;', '"')
page_number = int(re.findall(regex_pages_count, target)[0])
midi_link = re.findall(regex_midi_file, target)[0].split('?revision=')[0]
mp3_link = re.findall(regex_mp3_file, target)[0].split('?revision=')[0]

#download all pages
print('Downloading images!')
raw_img_list = []
for i in range(0,page_number): # despite counting 10, the starting index is 0 for their website, so there are only 9, but the range() got it all
	print(f'{i+1} out of {page_number}', end='\r', flush=True)
	directory = download_files(replace_number_for_page(first_img_url, i), name_) # replace_...() will raise the img number in the url
	raw_img_list.append(fr'{directory}')

print('Converting to PDF!', end='\n', flush=False)
# here are the two cases, i have to use different libraries cuz I cant figure hwo to use one for all. anyway, the svg is tricky so many differnt libraries is needed
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

# the clean up part will download the midi and mp3 file then remove all of the imgs that are downloaded in the downloading part cuz they neede to stay in the disk to be  converted
# there is another way to make it more efficient is accessing directly from the memory but I've not got there yet. hate all of those pointers
print('Cleaning up!', flush=False)
download_files(midi_link, name_)
download_files(mp3_link, name_)
try: # order matters here cuz if it's png then there is no pdf_list. try/except is needed to avoid this but it coudl also be avoided either way
	for i in raw_img_list:
		os.remove(i)
	for i in pdf_list:
		os.remove(i)
except:
	pass

print('\nDone!', flush=False)

