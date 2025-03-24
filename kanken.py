import os, re
import requests
import bs4
import pandas as pd

def load_html(name, link):
	response = requests.get(link)
	if response.status_code != 200:
		print("{}のページの取得に失敗しました:{}".format(name, response.status_code))
		exit()
	soup = bs4.BeautifulSoup(response.text, 'html.parser')
	return soup

kaneken_url = "https://kanken.jitenon.jp/"
save_dir = "kaneken"

os.makedirs(save_dir, exist_ok=True)

# BeautifulSoupでHTMLを解析
soup_main = load_html("漢検メイン", kaneken_url)
grade_tabel = soup_main.find('table', {'class': 'index02'})

rows = grade_tabel.find_all('tr')
grade_names, grade_links = [], []
for row in rows:
	cells = row.find_all('a')
	grade_links += [cell.get('href') for cell in cells]
	grade_names += [cell.text for cell in cells]

table = str.maketrans({'\u3000': ' ', '\t': ''})

c = 0
# 1級から10級までのページをループで回す
for grade_name, grade_link in zip(grade_names, grade_links):
	"""if c < 6:
		c += 1
		continue"""
	print(grade_name, grade_link)

	soup_grade = load_html(grade_name, grade_link)
	chapter_tabels = soup_grade.find_all('div', {'class': 'kyumidashiall'})
	chapter_names, chapter_links = [], []
	# 各級の章立てとそののリンクを取得
	for chapter_tabel in chapter_tabels:
		cells = chapter_tabel.find_all("a")
		chapter_links += [cell.get('href') for cell in cells]
		chapter_names += [cell.text for cell in cells]

	# 各級の問題と問題へのリンクをループで回す
	new_grade_table = []
	columns = ['問題タイプ', '問題番号', '問題文', '解答']
	for chapter_name, chapter_link in zip(chapter_names, chapter_links):
		"""
		csvにするのが難しそうなリスト
			漢字の識別
			対義語・類義語
			
			漢字の画数
			じゅく語作り、熟語作り
		"""

		"""if "busyu" not in chapter_link:
			continue"""
		print(grade_name, chapter_name, chapter_link)

		soup_chapter = load_html(chapter_name, chapter_link)
		mondai_tabels = soup_chapter.find_all('table', class_=re.compile(r'^(yomi|yoji|okuri|quiz|sanji|onaji|onkun|busyu)'))
		#mondai_tabels = soup_chapter.find_all('table', class_=re.compile(r'^(okuri)'))
		for mondai_tabel in mondai_tabels:
			if "yomi" in mondai_tabel.get("class")[0] or re.search(r'yoji1z?', mondai_tabel.get("class")[0]):
				mondai_name = mondai_tabel.find("tr").text.strip()
				q_and_a = [mondai.text for mondai in mondai_tabel.find_all("td")]
				new_grade_table.append([chapter_name, mondai_name, q_and_a[0], q_and_a[2]])
				print(len(new_grade_table), new_grade_table[-1])
			elif re.search(r'okuri[678]', mondai_tabel.get("class")[0]):
				contents = mondai_tabel.find_all("tr")
				new_grade_table.append([chapter_name] + contents[0].text.strip().split()[1:] + contents[1].text.strip().split())
				print(len(new_grade_table), new_grade_table[-1])
			elif 'okuri' in mondai_tabel.get("class")[0]:
				mondai_q_a = [mondai.text.strip().split() for i, mondai in enumerate(mondai_tabel.find_all("tr"))]
				new_grade_table += [[chapter_name] + mqa[:2] + ["、".join(mqa[2:])] for mqa in mondai_q_a]
				print(len(new_grade_table), new_grade_table[-1])
			elif 'quiz' in mondai_tabel.get("class")[0]:
				# 対応済み：yomi, kaki, kousei, okuri, goji
				if "yomi" in chapter_link or "kaki" in chapter_link or "kousei" in chapter_link or "okuri" in chapter_link or "goji" in chapter_link:
					chap_q_and_a = [chapter_name]
					for content in mondai_tabel.find_all("tr"):
						chap_q_and_a += content.text.strip().translate(table).split("\n")
					new_grade_table.append(chap_q_and_a)
				elif "yoji" in chapter_link or re.search(r'mondai-busyu02z?-\d+', chapter_link): # yoji or busyu2, busyu2z
					for i, content in enumerate(mondai_tabel.find_all("tr")[1:]):
						ans = content.text.replace("　　", "").replace("　", "").strip().split()
						new_grade_table.append([chapter_name, "問{}".format(i+1)] + [ans[0], "".join(ans[1:])])
				elif "busyu" in chapter_link: # 3, 4
					contents = mondai_tabel.find_all("tr")
					new_grade_table.append([chapter_name, contents[0].text.strip(), "、".join(contents[1].text.strip().split()), contents[2].text.strip()])
				elif re.search(r'mondai-douon02z?-\d+', chapter_link): # 2, 2z
					q_and_a = []
					for content in mondai_tabel.find_all("tr"):
						q_and_a += content.text.strip().split()
					new_grade_table.append([chapter_name, q_and_a[0], "".join(q_and_a[1::2]), "、".join(q_and_a[2::2])])
				elif "douon" in chapter_link:
					contents = mondai_tabel.find_all("tr")
					mondai_index = contents[0].text.strip()
					ans_option = contents[-1].text.strip().split()
					for i in range(1, len(contents)-1):
						content = contents[i].text.strip().split()
						new_grade_table.append([chapter_name, mondai_index, "{}: {}".format(content[0], "、".join(ans_option)), content[1]])
				print(len(new_grade_table), new_grade_table[-1])
			elif 'sanji' in mondai_tabel.get("class")[0]:
				for content in mondai_tabel.find_all("tr")[1:]:
					ans = content.text.strip().split()[2:]
					new_grade_table.append([chapter_name] + content.text.strip().split()[:2] + ["".join(ans)])
					print(len(new_grade_table), new_grade_table[-1])
			elif "onaji" in mondai_tabel.get("class")[0]:
				contents = mondai_tabel.find_all("tr")
				mondai_index = contents[0].text.strip()
				mondai = contents[1].text.strip().split()[0] + contents[2].text.strip().split()[0]
				answer = "{}、{}".format(contents[1].text.strip().split()[1], contents[2].text.strip().split()[1])
				new_grade_table.append([chapter_name, mondai_index, mondai, answer])
				print(len(new_grade_table), new_grade_table[-1])
			elif "onkun" in mondai_tabel.get("class")[0] and "list" not in mondai_tabel.get("class")[0]:
				for content in mondai_tabel.find_all("tr"):
					new_grade_table.append([chapter_name] + content.text.strip().split())
				print(len(new_grade_table), new_grade_table[-1])
			elif "yoji5mondai" == mondai_tabel.get("class")[0]:
				for content in mondai_tabel.find_all("tr"):
					m_q_a = content.text.strip().split()
					new_grade_table.append([chapter_name, m_q_a[0], m_q_a[1], "".join(m_q_a[2:])])
					print(len(new_grade_table), new_grade_table[-1])
			elif re.search(r"busyu[56]mondai", mondai_tabel.get("class")[0]):
				contents = mondai_tabel.find_all("tr")
				mondai_index = contents[0].text.strip()
				mondai = contents[1].text.strip().split()[0]
				ans = "：".join(contents[1].text.strip().split()[1:])
				ans += "、" + "：".join(contents[2].text.strip().split())
				new_grade_table.append([chapter_name, mondai_index, mondai, ans])
				print(len(new_grade_table), new_grade_table[-1])

	df = pd.DataFrame(new_grade_table, columns=columns)
	print(df.shape)
	df.to_csv(os.path.join(save_dir, '{}.csv'.format(grade_name)), index=False, encoding='utf-8')

